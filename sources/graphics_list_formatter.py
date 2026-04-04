from datetime import datetime
from typing import Dict, List
from pytz import timezone, utc


def make_graph(percent: float) -> str:
    """
    Make a simple text progress bar (25 characters).
    """
    done_block = "█"
    empty_block = "░"
    percent_quart = round(percent / 4)
    return f"{done_block * percent_quart}{empty_block * (25 - percent_quart)}"


def make_list(
    data: List[Dict] = None,
    names: List[str] = None,
    texts: List[str] = None,
    percents: List[float] = None,
    top_num: int = 5,
    sort: bool = True,
) -> str:
    """
    Make list of text progress bars with supportive info.
    """
    if data is not None:
        names = [v for item in data for k, v in item.items() if k == "name"] if names is None else names
        texts = [v for item in data for k, v in item.items() if k == "text"] if texts is None else texts
        percents = [v for item in data for k, v in item.items() if k == "percent"] if percents is None else percents

    data = list(zip(names, texts, percents))
    top_data = sorted(data[:top_num], key=lambda r: r[2], reverse=True) if sort else data[:top_num]
    return "\n".join(f"{n:<25} {t:<20} {make_graph(p)} {p:05.2f} %" for n, t, p in top_data)


async def make_commit_day_time_list(time_zone: str, repositories: Dict, commit_dates: Dict) -> str:
    """
    Simple text output for commits by time of day and day of week.
    """
    stats = ""
    day_times = [0] * 4  # Morning, Daytime, Evening, Night
    week_days = [0] * 7  # Monday-Sunday

    for repo in repositories:
        if repo["name"] not in commit_dates:
            continue
        for committed_date in [c for branch in commit_dates[repo["name"]].values() for c in branch.values()]:
            local_date = datetime.strptime(committed_date, "%Y-%m-%dT%H:%M:%SZ")
            local_date = local_date.replace(tzinfo=utc).astimezone(timezone(time_zone))
            day_times[local_date.hour // 6] += 1
            week_days[local_date.isoweekday() - 1] += 1

    # Time of Day
    dt_labels = ["Morning", "Daytime", "Evening", "Night"]
    dt_total = sum(day_times)
    stats += "```text\n"
    for label, count in zip(dt_labels, day_times):
        perc = round(count / dt_total * 100, 2) if dt_total > 0 else 0
        stats += f"{label:<20} {count:<5} commits {make_graph(perc)} {perc:05.2f} %\n"
    stats += "```\n\n"

    # Day of Week
    wd_labels = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    wd_total = sum(week_days)
    stats += "```text\n"
    for label, count in zip(wd_labels, week_days):
        perc = round(count / wd_total * 100, 2) if wd_total > 0 else 0
        stats += f"{label:<20} {count:<5} commits {make_graph(perc)} {perc:05.2f} %\n"
    stats += "```\n"

    return stats


def make_language_per_repo_list(repositories: Dict) -> str:
    """
    Simple text list of languages per repo.
    """
    language_count = {}
    for repo in repositories:
        if repo["primaryLanguage"]:
            lang = repo["primaryLanguage"]["name"]
            language_count[lang] = language_count.get(lang, 0) + 1

    if not language_count:
        return "No Activity Tracked This Week\n\n"

    stats = "Programming Languages:\n\n```text\n"
    for lang, count in language_count.items():
        stats += f"{lang:<20} {count} repo{'s' if count != 1 else ''}\n"
    stats += "```\n\n"
    return stats
