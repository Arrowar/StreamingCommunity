# 26.11.2025

import os
from typing import Tuple


# External library
from rich.console import Console
from rich.prompt import Prompt


# Internal utilities
from StreamingCommunity.utils import config_manager, start_message
from StreamingCommunity.services._base import site_constants, MediaItem
from StreamingCommunity.services._base.episode_manager import map_episode_title
from StreamingCommunity.core.downloader import HLS_Downloader


# Logic
from ..realtime.util.ScrapeSerie import GetSerieInfo
from ..realtime.util.get_license import get_bearer_token, get_playback_url
from ..realtime.series import download_series as DownSer, download_episode as DownEpi


# Variable
msg = Prompt()
console = Console()
extension_output = config_manager.config.get("M3U8_CONVERSION", "extension")


def download_video(index_season_selected: int, index_episode_selected: int, scrape_serie: GetSerieInfo) -> Tuple[str,bool]:
    """
    Downloads a specific episode from the specified season.

    Parameters:
        - index_season_selected (int): Season number
        - index_episode_selected (int): Episode index
        - scrape_serie (GetSerieInfo): Scraper object with series information

    Returns:
        - str: Path to downloaded file
        - bool: Whether download was stopped
    """
    start_message()

    # Get episode information
    obj_episode = scrape_serie.selectEpisode(index_season_selected, index_episode_selected-1)
    console.print(f"\n[yellow]Download: [red]{site_constants.SITE_NAME} → [cyan]{scrape_serie.series_name} \\ [magenta]{obj_episode.name} ([cyan]S{index_season_selected}E{index_episode_selected}) \n")

    # Define filename and path for the downloaded video
    mp4_name = f"{map_episode_title(scrape_serie.series_name, index_season_selected, index_episode_selected, obj_episode.name)}.{extension_output}"
    mp4_path = os.path.join(site_constants.SERIES_FOLDER, scrape_serie.series_name, f"S{index_season_selected}")

    # Get m3u8 playlist
    bearer_token = get_bearer_token()
    master_playlist = get_playback_url(obj_episode.id, bearer_token, False, obj_episode.channel)

    # Download the episode
    hls_process = HLS_Downloader(
        m3u8_url=master_playlist,
        output_path=os.path.join(mp4_path, mp4_name)
    ).start()

    if hls_process['error'] is not None:
        try: 
            os.remove(hls_process['path'])
        except Exception: 
            pass

    return hls_process['path'], hls_process['stopped']


def download_episode(index_season_selected: int, scrape_serie: GetSerieInfo, download_all: bool = False, episode_selection: str = None) -> None:
    DownEpi(index_season_selected, scrape_serie, download_all, episode_selection)

def download_series(select_season: MediaItem, season_selection: str = None, episode_selection: str = None) -> None:
    DownSer(select_season, season_selection, episode_selection)