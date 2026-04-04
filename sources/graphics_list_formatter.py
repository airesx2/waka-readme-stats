from enum import Enum
from typing import Dict, Tuple, List
from datetime import datetime

from pytz import timezone, utc

from manager_environment import EnvironmentManager as EM
from manager_file import FileManager as FM


DAY_TIME_EMOJI = ["🌞", "🌆", "🌃", "🌙"]  # Emojis, representing different times of day.
DAY_TIME_NAMES = ["Morning", "Daytime", "Evening", "Night"]  # Localization identifiers for different times of day.
WEEK_DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]  # Localization identifiers for different days of week.


class Symbol(Enum):
    """
    Symbol version enum.
    Allows to retrieve symbols pairs by calling `Symbol.get_symbols(version)`.
    """

    VERSION_1 = "█", "░"
    VERSION_2 = "⣿", "⣀"
    VERSION_3 = "⬛", "⬜"

    @staticmethod
    def get_symbols(version: int) -> Tuple[str, str]:
        """
        Retrieves symbols pair for specified version.

        :param version: Required symbols version.
        :returns: Two strings for filled and empty symbol value in a tuple.
        """
        return Symbol[f"VERSION_{version}"].value


def make_graph(percent: float):
    """
    Make text progress bar.
    Length of the progress bar is 25 characters.

    :param percent: Completion percent of the progress bar.
    :return: The string progress bar representation.
    """
    done_block, empty_block = Symbol.get_symbols(EM.SYMBOL_VERSION)
    percent_quart = round(percent / 4)
    return f"{done_block * percent_quart}{empty_block * (25 - percent_quart)}"


def make_list(data: List = None, names: List[str] = None, texts: List[str] = None, percents: List[float] = None, top_num: int = 5, sort: bool = True) -> str:
    """
    Make list of text progress bars with supportive info.
    Each row has the following structure: [name of the measure] [quantity description (with words)] [progress bar] [total percentage].
    Name of the measure: up to 25 characters.
    Quantity description: how many _things_ were found, up to 20 characters.
    Progress bar: measure percentage, 25 characters.
    Total percentage: floating point percentage.

    :param data: list of dictionaries, each of them containing a measure (name, text and percent).
    :param names: list of names (names of measure), overloads data if defined.
    :param texts: list of texts (quantity descriptions), overloads data if defined.
    :param percents: list of percents (total percentages), overloads data if defined.
    :param top_num: how many measures to display, default: 5.
    :param sort: if measures should be sorted by total percentage, default: True.
    :returns: The string representation of the list.
    """
    if data is not None:
        names = [value for item in data for key, value in item.items() if key == "name"] if names is None else names
        texts = [value for item in data for key, value in item.items() if key == "text"] if texts is None else texts
        percents = [value for item in data for key, value in item.items() if key == "percent"] if percents is None else percents

    data = list(zip(names, texts, percents))
    top_data = sorted(data[:top_num], key=lambda record: record[2], reverse=True) if sort else data[:top_num]
    data_list = [f"{n[:25]}{' ' * (25 - len(n))}{t}{' ' * (20 - len(t))}{make_graph(p)}   {p:05.2f} % " for n, t, p in top_data]
    return "\n".join(data_list)


async def make_commit_day_time_list(time_zone: str, repositories: Dict, commit_dates: Dict) -> str:
    """
    Simple text output for commits by time of day and day of week.
    """
    stats = str()
    day_times = [0] * 4  # Morning, Daytime, Evening, Night
    week_days = [0] * 7  # Mon-Sun

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
        stats += f"{label:<20} {count:<5} commits   {perc:05.2f} %\n"
    stats += "```\n\n"

    # Day of Week
    wd_labels = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    wd_total = sum(week_days)
    stats += "```text\n"
    for label, count in zip(wd_labels, week_days):
        perc = round(count / wd_total * 100, 2) if wd_total > 0 else 0
        stats += f"{label:<20} {count:<5} commits   {perc:05.2f} %\n"
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

    stats = "**Programming Languages:**\n\n```text\n"
    for lang, count in language_count.items():
        stats += f"{lang:<20} {count} repo{'s' if count != 1 else ''}\n"
    stats += "```\n\n"
    return stats
