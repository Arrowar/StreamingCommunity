# 22.12.25

import os


# External library
from rich.console import Console
from rich.prompt import Prompt


# Internal utilities
from StreamingCommunity.utils import os_manager, config_manager, start_message
from StreamingCommunity.services._base import site_constants, MediaItem
from StreamingCommunity.services._base.tv_display_manager import map_episode_title
from StreamingCommunity.services._base.tv_download_manager import process_season_selection, process_episode_download


# Downloader
from StreamingCommunity.core.downloader import DASH_Downloader


# Logic
from .client import get_client
from .scrapper import GetSerieInfo


# Variables
msg = Prompt()
console = Console()
extension_output = config_manager.config.get("M3U8_CONVERSION", "extension")


def download_episode(obj_episode, index_season_selected, index_episode_selected, scrape_serie):
    """
    Downloads a specific episode from the specified season.
    """
    start_message()
    client = get_client()
    console.print(f"\n[yellow]Download: [red]{site_constants.SITE_NAME} [cyan]{scrape_serie.series_name} [white]\\ [magenta]{obj_episode.name} ([cyan]S{index_season_selected}E{index_episode_selected}) \n")
    
    # Define output path
    mp4_name = f"{map_episode_title(scrape_serie.series_name, index_season_selected, index_episode_selected, obj_episode.name)}.{extension_output}"
    mp4_path = os_manager.get_sanitize_path(
        os.path.join(site_constants.SERIES_FOLDER, scrape_serie.series_name, f"S{index_season_selected}")
    )
    
    # Get playback information using the new client
    playback_info = client.get_playback_info(obj_episode.id)
    
    return DASH_Downloader(
        mpd_url=playback_info['manifest'],
        license_url=playback_info['license'],
        output_path=os.path.join(mp4_path, mp4_name),
        drm_preference="playready"
    ).start()

def download_series(select_season: MediaItem, season_selection: str = None, episode_selection: str = None) -> None:
    """
    Handle downloading a complete series
    
    Parameters:
        select_season (MediaItem): Series metadata from search
        season_selection (str, optional): Pre-defined season selection
        episode_selection (str, optional): Pre-defined episode selection
    """
    start_message()
    
    # Initialize the series scraper with just the show ID
    scrape_serie = GetSerieInfo(select_season.id)
    
    # Create callback function for downloading episodes
    def download_episode_callback(season_number: int, download_all: bool, episode_selection: str = None):
        """Callback to handle episode downloads for a specific season"""
        
        # Create callback for downloading individual videos
        def download_video_callback(obj_episode, season_idx, episode_idx):
            return download_episode(obj_episode, season_idx, episode_idx, scrape_serie)
        
        # Use the process_episode_download function
        process_episode_download(
            index_season_selected=season_number,
            scrape_serie=scrape_serie,
            download_video_callback=download_video_callback,
            download_all=download_all,
            episode_selection=episode_selection
        )

    # Get total number of seasons
    seasons_count = scrape_serie.getNumberSeason()
    
    # Use the process_season_selection function
    process_season_selection(
        scrape_serie=scrape_serie,
        seasons_count=seasons_count,
        season_selection=season_selection,
        episode_selection=episode_selection,
        download_episode_callback=download_episode_callback
    )