import os
import re
from dataclasses import dataclass
from enum import Enum
from functools import wraps
from pathlib import Path
from typing import Annotated, List, Tuple

import questionary
import typer
from rich.panel import Panel

from tvfmt import utils
from tvfmt.api import TraktAPI, TvEpisode, TvShow, TvSeason
from tvfmt.globals import console
from tvfmt.config import cli_config, CliConfigKey

app = typer.Typer()


def exit_on_null(message: str = ""):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            if result in (None, []):
                error(message)
            return result

        return wrapper

    return decorator


@exit_on_null("TRAKT_API_KEY not set in config or as an environment variable.")
def get_api_key():
    trakt_api_key = os.environ.get("TRAKT_API_KEY")
    if not trakt_api_key:
        trakt_api_key = cli_config.get(CliConfigKey.TRAKT_API_KEY)
    return trakt_api_key


def error(message: str):
    console.print(
        Panel(
            message,
            title="Error",
            border_style="red",
            title_align="left",
        )
    )
    raise typer.Exit(1)


@dataclass
class PathChange:
    old: Path
    new: Path
    is_file: bool = True

    def __str__(self):
        old_name = self.short_name(self.old, 40)
        new_name = self.short_name(self.new, 40)
        return f"[red]{old_name}[/red] → [green]{new_name}[/green]"

    def paths(self):
        return self.old, self.new

    @staticmethod
    def short_name(path: Path, max_len: int) -> str:
        new_name = path.name
        if len(new_name) > max_len:
            new_suffix = "[...]" + path.suffix
            new_name = new_name[: max_len - len(new_suffix)] + new_suffix
        return new_name


class TvFormatter:
    def __init__(self, api: TraktAPI):
        self.api = api

    @exit_on_null("Unable to find TV Show matching given name.")
    def get_tv_show(self, show_name: str, auto: bool) -> TvShow:
        if not show_name:
            show_name = questionary.text("Search Tv Shows").ask()
        tv_shows = self.api.search_tv_shows(query=show_name, limit=5)
        if tv_shows:
            tv_show = (
                questionary.select("Tv Show", utils.as_choices(tv_shows))
                .skip_if(auto, default=tv_shows[0])
                .ask()
            )
            return tv_show

    @exit_on_null("Invalid season number given.")
    def get_tv_season(self, show_id: int, season_num: int) -> TvSeason:
        seasons = self.api.get_show_seasons(show_id)
        if season_num and 0 < season_num <= len(seasons):
            return seasons[season_num - 1]
        else:
            return questionary.select("Season", utils.as_choices(seasons)).ask()

    @exit_on_null("Unable to find episodes for given season.")
    def get_tv_episodes(self, show_id: int, season_num: int) -> List[TvEpisode]:
        return self.api.get_season_episodes(show_id, season_num)

    @exit_on_null("Unable to parse files in given directory.")
    def get_file_changes(
        self, files: List[Path], show_name: str, episodes: List[TvEpisode]
    ) -> List[PathChange]:
        changes = []
        for f in files:
            filename_info = self.parse_episode_file(f.name)
            if filename_info:
                season_num, episode_num = filename_info
                episode_name = utils.find_by_attr(episodes, "number", episode_num)
                new_name = self.format_filename(
                    show_name, season_num, episode_num, episode_name, f.suffix
                )
                changes.append(PathChange(f, f.parent / new_name))
        return changes

    @staticmethod
    def confirm_changes(changes: List[PathChange], path: Path) -> bool:
        changes_display = "\n".join(
            [
                f"({i + 1}) {change}"
                for i, change in enumerate(changes)
                if change.is_file
            ]
        )
        title = f"[cyan]{utils.short_path(path.absolute())}[/cyan]"
        console.print(Panel(changes_display, title=title, border_style="bold yellow"))
        confirm = questionary.confirm("Commit changes").ask()
        return confirm

    @staticmethod
    def parse_episode_file(filename: str) -> Tuple[int, int]:
        pattern = r"[Ss]\d{2}[Ee]\d{2}"
        match = re.findall(pattern, filename)
        if match:
            season_num = int(match[0][1:3])
            episode_num = int(match[0][4:])
            return season_num, episode_num

    @staticmethod
    def format_filename(
        show_name: str, season_num: int, episode_num: int, episode_name: str, ext: str
    ) -> str:
        # avoid :'s in filenames
        return f"{show_name.replace(':','')} S{season_num:02}E{episode_num:02} {episode_name}{ext}"

    def run(self, path: Path, show: str, season: int, auto: bool, user_confirm: bool):
        if not (path.exists() and path.is_dir()):
            error(
                f"Invalid value for PATH: Directory '{utils.short_path(path)}' doesn't exist."
            )
        tv_show = self.get_tv_show(show, auto)
        tv_season = self.get_tv_season(tv_show.id, season)
        tv_episodes = self.get_tv_episodes(tv_show.id, tv_season.number)
        files = utils.get_files(path)
        changes = self.get_file_changes(files, tv_show.name, tv_episodes)
        if user_confirm:
            if self.confirm_changes(changes, path):
                utils.rename_files([c.paths() for c in changes])
        console.print("Done!", style="bold green")


@app.command("config")
def config(
    open_file: Annotated[bool, typer.Option("--open", "-o")] = False,
    set_key: Annotated[
        Tuple[CliConfigKey, str], typer.Option("--set", "-s", metavar="<KEY, VALUE>")
    ] = (
        None,
        None,
    ),
    get_key: Annotated[
        CliConfigKey, typer.Option("--get", "-g", metavar="<KEY>")
    ] = None,
):
    if open_file:
        typer.launch(str(cli_config.get_file()))
    elif get_key:
        console.print(f"{get_key.value} = {cli_config.get(get_key)}")
    elif set_key != (None, None):
        key, value = set_key
        if cli_config.set(key, value):
            console.print(f"Set {key.value}: {value}")
    else:
        console.print(
            Panel(
                str(cli_config),
                title=f"{cli_config.get_file()}",
                border_style="bold yellow",
            )
        )


@app.command("run")
def cli(
    path: Annotated[Path, typer.Argument(metavar="PATH")] = ".",
    show: Annotated[str, typer.Option(help="Name of TV Show")] = None,
    season: Annotated[int, typer.Option(help="Season number")] = None,
    auto: Annotated[
        bool, typer.Option(help="Auto-select closest match to given show name")
    ] = cli_config.get(CliConfigKey.AUTO),
    confirm: Annotated[
        bool, typer.Option(help="Confirm changes before renaming files")
    ] = cli_config.get(CliConfigKey.CONFIRM),
    api_key: Annotated[str, typer.Option()] = get_api_key(),
):
    api = TraktAPI(trakt_api_key=api_key)
    tvfmt = TvFormatter(api)
    tvfmt.run(path, show, season, auto, confirm)
