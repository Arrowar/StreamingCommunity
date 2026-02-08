# 13.06.24

import os


# External library
from rich.console import Console
from rich.prompt import Prompt


# Internal utilities
from StreamingCommunity.utils import config_manager, start_message
from StreamingCommunity.services._base import site_constants, Entries
from StreamingCommunity.services._base.tv_display_manager import map_episode_title, dynamic_format_number
from StreamingCommunity.services._base.tv_download_manager import process_season_selection, process_episode_download


# Downloader
from StreamingCommunity.core.downloader import HLS_Downloader


# Player
from StreamingCommunity.player.supervideo import VideoSource


# Logic 
from .scrapper import GetSerieInfo


# Variable
msg = Prompt()
console = Console()
extension_output = config_manager.config.get("M3U8_CONVERSION", "extension")


def download_episode(obj_episode, index_season_selected, index_episode_selected, scrape_serie):
    """
    Downloads a specific episode from the specified season.
    """
    start_message()
    index_season_selected_formatted = dynamic_format_number(str(index_season_selected))
    console.print(f"\n[yellow]Download: [red]{site_constants.SITE_NAME} → [cyan]{scrape_serie.tv_name} [white]\\ [magenta]{obj_episode.name} ([cyan]S{index_season_selected_formatted}E{index_episode_selected}) \n")

    # Define filename and path for the downloaded video
    mp4_name = f"{map_episode_title(scrape_serie.tv_name, index_season_selected_formatted, index_episode_selected, obj_episode.name)}.{extension_output}"
    mp4_path = os.path.join(site_constants.SERIES_FOLDER, scrape_serie.tv_name, f"S{index_season_selected_formatted}")

    # Setup video source
    video_source = VideoSource(obj_episode.url)

    # Get m3u8 master playlist
    master_playlist = video_source.get_playlist()
    
    # Download the film using the m3u8 playlist, and output filename
    return HLS_Downloader(
        m3u8_url=master_playlist, 
        output_path=os.path.join(mp4_path, mp4_name)
    ).start()

def download_series(select_season: Entries, season_selection: str = None, episode_selection: str = None) -> None:
    """
    Handle downloading a complete series
    
    Parameters:
        select_season (Entries): Series metadata from search
        season_selection (str, optional): Pre-defined season selection
        episode_selection (str, optional): Pre-defined episode selection
    """
    start_message()
    scrape_serie = GetSerieInfo(select_season)
    
    # Get number of seasons
    seasons_count = scrape_serie.getNumberSeason()
    
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

    # Use the process_season_selection function
    process_season_selection(
        scrape_serie=scrape_serie,
        seasons_count=seasons_count,
        season_selection=season_selection,
        episode_selection=episode_selection,
        download_episode_callback=download_episode_callback
    )