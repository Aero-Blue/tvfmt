from dataclasses import dataclass
from typing import List
from urllib.parse import urljoin

import requests


@dataclass
class TvShow:
    name: str
    year: str
    id: int

    def __str__(self):
        return f"{self.name} ({self.year})"


@dataclass
class TvSeason:
    name: str
    episode_count: int
    number: int
    id: int

    def __str__(self):
        return f"{self.name} ({self.episode_count})"


@dataclass
class TvEpisode:
    name: str
    number: int
    id: int

    def __str__(self):
        return self.name


class TraktAPI:
    BASE_URL = "https://api.trakt.tv/"

    def __init__(self, trakt_api_key):
        self.headers = {"trakt-api-key": trakt_api_key}

    def search_tv_shows(self, query: str, limit: int) -> List[TvShow]:
        tv_shows = []
        if query:
            with self._get(f"search/show?query={query}") as resp:
                data = resp.json()
                for result in data[:limit]:
                    title = result.get("show", {}).get("title")
                    year = result.get("show", {}).get("year")
                    trakt = result.get("show", {}).get("ids", {}).get("trakt")
                    tv_shows.append(TvShow(title, year, trakt))
        return tv_shows

    def get_show_seasons(self, show_id: int) -> List[TvSeason]:
        seasons = []
        with self._get(f"shows/{show_id}/seasons?extended=full") as resp:
            data = resp.json()
            for result in data:
                title = result.get("title")
                episode_count = result.get("episode_count")
                number = result.get("number")
                trakt = result.get("ids", {}).get("trakt")
                if number > 0:  # Skip specials
                    seasons.append(TvSeason(title, episode_count, number, trakt))
        return seasons

    def get_season_episodes(self, show_id: int, season: int) -> List[TvEpisode]:
        episodes = []
        with self._get(f"shows/{show_id}/seasons/{season}/episodes") as resp:
            data = resp.json()
            for result in data:
                title = result.get("title")
                number = result.get("number")
                trakt = result.get("ids", {}).get("trakt")
                episodes.append(TvEpisode(title, number, trakt))
        return episodes

    def _get(self, path):
        return requests.get(urljoin(self.BASE_URL, path), headers=self.headers)
