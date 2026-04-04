"""
Readme Development Metrics With waka time progress
"""

from asyncio import run
from datetime import datetime
from typing import Dict
from urllib.parse import quote

from humanize import intword, naturalsize, intcomma

from manager_download import init_download_manager, DownloadManager as DM
from manager_environment import EnvironmentManager as EM
from manager_github import init_github_manager, GitHubManager as GHM
from manager_file import init_localization_manager, FileManager as FM
from manager_debug import init_debug_manager, DebugManager as DBM
from graphics_chart_drawer import create_loc_graph, GRAPH_PATH
from yearly_commit_calculator import calculate_commit_data
from graphics_list_formatter import (
    make_list,
    make_commit_day_time_list,
    make_language_per_repo_list,
)


async def get_waka_time_stats(repositories: Dict, commit_dates: Dict) -> str:
    """
    Collects user info from WakaTime.
    Outputs clean text blocks: Programming Languages, Time of Day, Day of Week.
    
    :param repositories: User repositories list.
    :param commit_dates: User commit data list.
    :returns: String representation of the info.
    """
    DBM.i("Adding WakaTime stats...")
    stats = str()

    data = await DM.get_remote_json("waka_latest")
    if data is None:
        DBM.p("WakaTime data unavailable!")
        return stats

    no_activity = FM.t("No Activity Tracked This Week")

    # ----------------------------
    # 1. Programming Languages first
    # ----------------------------
    lang_list = no_activity if len(data["data"]["languages"]) == 0 else make_list(data["data"]["languages"])
    stats += f"Programming Languages: \n{lang_list}\n\n"

    # ----------------------------
    # 2. Time of Day
    # ----------------------------
    if EM.SHOW_COMMIT or EM.SHOW_DAYS_OF_WEEK:
        DBM.i("Adding user commit day time info...")
        stats += f"{await make_commit_day_time_list(data['data']['timezone'], repositories, commit_dates)}\n\n"

    # ----------------------------
    # 3. Day of Week (optional)
    # ----------------------------
    if EM.SHOW_DAYS_OF_WEEK and not EM.SHOW_COMMIT:
        stats += f"{await make_commit_day_time_list(data['data']['timezone'], repositories, commit_dates)}\n\n"

    DBM.g("WakaTime stats added!")
    return stats

async def get_short_github_info() -> str:
    """
    Collects user info from GitHub public profile.
    Plain text only, no emojis.
    """
    DBM.i("Adding short GitHub info...")
    stats = f"**{FM.t('My GitHub Data')}** \n\n"

    # Disk usage
    if GHM.USER.disk_usage is None:
        disk_usage = FM.t("Used in GitHub's Storage") % "?"
        DBM.p("Please add new github personal access token with user permission!")
    else:
        disk_usage = FM.t("Used in GitHub's Storage") % naturalsize(GHM.USER.disk_usage)
    stats += f"{disk_usage}\n"

    # Contributions
    data = await DM.get_remote_json("github_stats")
    if data and len(data["years"]) > 0:
        contributions = FM.t("Contributions in the year") % (
            intcomma(data["years"][0]["total"]),
            data["years"][0]["year"],
        )
        stats += f"{contributions}\n"

    # Hireable
    opted_to_hire = GHM.USER.hireable
    stats += f"{FM.t('Opted to Hire') if opted_to_hire else FM.t('Not Opted to Hire')}\n"

    # Repositories
    public_repo = GHM.USER.public_repos
    stats += f"{FM.t('public repositories') % public_repo if public_repo != 1 else FM.t('public repository') % public_repo}\n"
    private_repo = GHM.USER.owned_private_repos if GHM.USER.owned_private_repos is not None else 0
    stats += f"{FM.t('private repositories') % private_repo if private_repo != 1 else FM.t('private repository') % private_repo}\n"

    DBM.g("Short GitHub info added!")
    return stats


async def collect_user_repositories() -> Dict:
    """
    Collects information about all the user repositories available.

    :returns: Complete list of user repositories.
    """
    DBM.i("Getting user repositories list...")
    if EM.MAX_REPOS > 0:
        DBM.i(f"\tMAX_REPOS enabled: {EM.MAX_REPOS}")
    repositories = await DM.get_remote_graphql(
        "user_repository_list",
        username=GHM.USER.login,
        id=GHM.USER.node_id,
        _max_nodes=(EM.MAX_REPOS if EM.MAX_REPOS > 0 else None),
    )
    if EM.MAX_REPOS > 0:
        DBM.i(f"\tFetched {len(repositories)} repos out of MAX_REPOS={EM.MAX_REPOS}")
    if EM.MAX_REPOS > 0 and len(repositories) >= EM.MAX_REPOS:
        DBM.w(f"\tMAX_REPOS cap reached ({EM.MAX_REPOS}); skipping contributed repos.")
        return repositories[: EM.MAX_REPOS]
    repo_names = [repo["name"] for repo in repositories]
    DBM.g("\tUser repository list collected!")

    remaining = (EM.MAX_REPOS - len(repositories)) if EM.MAX_REPOS > 0 else None
    contributed = await DM.get_remote_graphql("repos_contributed_to", username=GHM.USER.login, _max_nodes=remaining)

    contributed_nodes = [repo for repo in contributed if repo is not None and repo["name"] not in repo_names and not repo["isFork"]]
    DBM.g("\tUser contributed to repository list collected!")

    combined = repositories + contributed_nodes
    if EM.MAX_REPOS > 0:
        if len(combined) < EM.MAX_REPOS:
            DBM.i(f"\tFetched repos < MAX_REPOS ({len(combined)} < {EM.MAX_REPOS}).")
        else:
            DBM.i(f"\tMAX_REPOS reached ({EM.MAX_REPOS}).")
        return combined[: EM.MAX_REPOS]
    return combined


async def get_stats() -> str:
    """
    Creates new README.md content from all the acquired statistics from all places.
    The readme includes data from wakatime, contributed lines of code number, GitHub profile info and last updated date.

    :returns: String representation of README.md contents.
    """
    DBM.i("Collecting stats for README...")

    stats = str()
    repositories = await collect_user_repositories()

    if EM.SHOW_LINES_OF_CODE or EM.SHOW_LOC_CHART or EM.SHOW_COMMIT or EM.SHOW_DAYS_OF_WEEK:  # calculate commit data if any one of these is enabled
        yearly_data, commit_data = await calculate_commit_data(repositories)
    else:
        yearly_data, commit_data = dict(), dict()
        DBM.w("User yearly data not needed, skipped.")

    if EM.SHOW_TOTAL_CODE_TIME:
        DBM.i("Adding total code time info...")
        data = await DM.get_remote_json("waka_all")
        if data is None:
            DBM.p("WakaTime data unavailable!")
        else:
            stats += f"![Code Time](http://img.shields.io/badge/{quote('Code Time')}-{quote(str(data['data']['text']))}-blue?style={quote(EM.BADGE_STYLE)})\n\n"

    if EM.SHOW_PROFILE_VIEWS:
        if EM.DEBUG_RUN or GHM.REMOTE is None:
            DBM.w("Profile views skipped in DEBUG_RUN mode.")
        else:
            DBM.i("Adding profile views info...")
            views_count = 0
            try:
                traffic = GHM.REMOTE.get_views_traffic(per="week")
            except Exception as e:
                DBM.w(f"Profile views unavailable, defaulting to 0: {e}")
            else:
                if isinstance(traffic, dict):
                    views_count = traffic.get("count")
                elif hasattr(traffic, "count"):
                    views_count = getattr(traffic, "count")
                elif isinstance(traffic, (list, tuple)):
                    first = traffic[0] if len(traffic) > 0 else None
                    if isinstance(first, dict):
                        views_count = first.get("count")
                    elif hasattr(first, "count"):
                        views_count = getattr(first, "count")
                    elif isinstance(first, list) and all(hasattr(v, "count") for v in first):
                        views_count = sum(getattr(v, "count") for v in first)
                    elif all(hasattr(v, "count") for v in traffic):
                        views_count = sum(getattr(v, "count") for v in traffic)

                if views_count is None:
                    DBM.w(f"Profile views returned unexpected type ({type(traffic)}), defaulting to 0.")
                    views_count = 0

            stats += f"![Profile Views](http://img.shields.io/badge/" f"{quote(FM.t('Profile Views'))}-{views_count}-blue?style={quote(EM.BADGE_STYLE)})\n\n"

    if EM.SHOW_LINES_OF_CODE:
        DBM.i("Adding lines of code info...")
        total_loc = sum([yearly_data[y][q][d]["add"] for y in yearly_data.keys() for q in yearly_data[y].keys() for d in yearly_data[y][q].keys()])
        data = f"{intword(total_loc, format='%.2f')} {FM.t('Lines of code')}"
        stats += (
            f"![Lines of code](https://img.shields.io/badge/"
            f"{quote(FM.t('From Hello World I have written'))}-{quote(data)}-blue?"
            f"style={quote(EM.BADGE_STYLE)})\n\n"
        )

    if EM.SHOW_SHORT_INFO:
        stats += await get_short_github_info()

    stats += await get_waka_time_stats(repositories, commit_data)

    if EM.SHOW_LANGUAGE_PER_REPO:
        DBM.i("Adding language per repository info...")
        stats += f"{make_language_per_repo_list(repositories)}\n\n"

    if EM.SHOW_LOC_CHART:
        await create_loc_graph(yearly_data, GRAPH_PATH)
        stats += f"**{FM.t('Timeline')}**\n\n{GHM.update_chart('Lines of Code', GRAPH_PATH)}"

    if EM.SHOW_UPDATED_DATE:
        DBM.i("Adding last updated time...")
        stats += f"\n Last Updated on {datetime.now().strftime(EM.UPDATED_DATE_FORMAT)} UTC"

    DBM.g("Stats for README collected!")
    return stats


async def main():
    """
    Application main function.
    Initializes all managers, collects user info and updates README.md if necessary.
    """
    init_github_manager()
    await init_download_manager(GHM.USER.login)
    init_localization_manager()
    DBM.i("Managers initialized.")

    stats = await get_stats()
    if not EM.DEBUG_RUN:
        GHM.update_readme(stats)
        GHM.commit_update()
    else:
        GHM.set_github_output(stats)
    await DM.close_remote_resources()


if __name__ == "__main__":
    init_debug_manager()
    start_time = datetime.now()
    DBM.g("Program execution started at $date.", date=start_time)
    run(main())
    end_time = datetime.now()
    DBM.g("Program execution finished at $date.", date=end_time)
    DBM.p("Program finished in $time.", time=end_time - start_time)
