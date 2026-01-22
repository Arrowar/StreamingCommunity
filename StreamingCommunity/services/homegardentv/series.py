# 26.11.25

import os
from typing import Tuple


# External library
from rich.console import Console
from rich.prompt import Prompt


# Internal utilities
from StreamingCommunity.utils import config_manager, start_message
from StreamingCommunity.services._base import site_constants, MediaItem
from StreamingCommunity.services._base.episode_manager import map_episode_title
from StreamingCommunity.services._base.season_manager import process_season_selection, process_episode_download
from StreamingCommunity.core.downloader import HLS_Downloader


# Logic
from ..realtime.util.ScrapeSerie import GetSerieInfo
from ..realtime.util.get_license import get_bearer_token, get_playback_url


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
    console.print(f"\n[yellow]Download: [red]{site_constants.SITE_NAME} → [cyan]{scrape_serie.series_name} [white]\\ [magenta]{obj_episode.name} ([cyan]S{index_season_selected}E{index_episode_selected}) \n")

    # Define filename and path for the downloaded video
    mp4_name = f"{map_episode_title(scrape_serie.series_name, index_season_selected, index_episode_selected, obj_episode.name)}.{extension_output}"
    mp4_path = os.path.join(site_constants.SERIES_FOLDER, scrape_serie.series_name, f"S{index_season_selected}")

    # Get m3u8 playlist
    bearer_token = get_bearer_token()
    master_playlist = get_playback_url(obj_episode.id, bearer_token, False, obj_episode.channel)

    # Download the episode
    return HLS_Downloader(
        m3u8_url=master_playlist,
        output_path=os.path.join(mp4_path, mp4_name)
    ).start()


def download_series(select_season: MediaItem, season_selection: str = None, episode_selection: str = None) -> None:
    """
    Handle downloading a complete series.

    Parameters:
        - select_season (MediaItem): Series metadata from search
        - season_selection (str, optional): Pre-defined season selection that bypasses manual input
        - episode_selection (str, optional): Pre-defined episode selection that bypasses manual input
    """
    start_message()
    scrape_serie = GetSerieInfo(select_season.url)

    scrape_serie.getNumberSeason()
    seasons_count = len(scrape_serie.seasons_manager)

    # Create callback function for downloading episodes
    def download_episode_callback(season_number: int, download_all: bool, episode_selection: str = None):
        """Callback to handle episode downloads for a specific season"""
        
        # Create callback for downloading individual videos
        def download_video_callback(season_idx: int, episode_idx: int):
            return download_video(season_idx, episode_idx, scrape_serie)
        
        # Use the process_episode_download function
        process_episode_download(
            index_season_selected=season_number,
            scrape_serie=scrape_serie,
            download_video_callback=download_video_callback,
            download_all=download_all,
            episode_selection=episode_selection
        )

    # Use the process_season_selection function
    process_season_selection(
        scrape_serie=scrape_serie,
        seasons_count=seasons_count,
        season_selection=season_selection,
        episode_selection=episode_selection,
        download_episode_callback=download_episode_callback
    )