# 16.03.25

import os
import re


# External library
from bs4 import BeautifulSoup
from rich.console import Console
from rich.prompt import Prompt


# Internal utilities
from StreamingCommunity.utils import os_manager, start_message, config_manager
from StreamingCommunity.utils.http_client import create_client, get_headers
from StreamingCommunity.services._base import site_constants, MediaItem
from StreamingCommunity.services._base.tv_display_manager import map_episode_title
from StreamingCommunity.services._base.tv_download_manager import process_season_selection, process_episode_download


# Downloader
from StreamingCommunity.core.downloader import HLS_Downloader


# Player
from StreamingCommunity.player.supervideo import VideoSource


# Logic
from .scrapper import GetSerieInfo


# Variable
console = Console()
msg = Prompt()
extension_output = config_manager.config.get("M3U8_CONVERSION", "extension")


def download_film(select_title: MediaItem) -> str:
    """
    Downloads a film using the provided MediaItem information.
    """
    start_message()
    console.print(f"\n[yellow]Download: [red]{site_constants.SITE_NAME} → [cyan]{select_title.name} \n")
    
    # Extract mostraguarda URL
    try:
        response = create_client(headers=get_headers()).get(select_title.url)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')
        iframes = soup.find_all('iframe')
        mostraguarda = iframes[0]['src']
    
    except Exception as e:
        console.print(f"[red]Site: {site_constants.SITE_NAME}, request error: {e}, get mostraguarda")
        return None

    # Extract supervideo URL
    supervideo_url = None
    try:
        response = create_client(headers=get_headers()).get(mostraguarda)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')
        pattern = r'//supervideo\.[^/]+/[a-z]/[a-zA-Z0-9]+'
        supervideo_match = re.search(pattern, response.text)
        supervideo_url = 'https:' + supervideo_match.group(0)

    except Exception as e:
        console.print(f"[red]Site: {site_constants.SITE_NAME}, request error: {e}, get supervideo URL")
        console.print("[yellow]This content will be available soon!")
        return None
    
    # Init class
    video_source = VideoSource(supervideo_url)
    master_playlist = video_source.get_playlist()

    # Define the filename and path for the downloaded film
    title_name = f"{os_manager.get_sanitize_file(select_title.name, select_title.year)}.{extension_output}"
    mp4_path = os.path.join(site_constants.MOVIE_FOLDER, title_name.replace(f".{extension_output}", ""))

    # Download the film using the m3u8 playlist, and output filename
    return HLS_Downloader(
        m3u8_url=master_playlist,
        output_path=os.path.join(mp4_path, title_name)
    ).start()


def download_episode(obj_episode, index_season_selected, index_episode_selected, scrape_serie):
    """
    Downloads a specific episode from the specified season.
    """
    start_message()
    console.print(f"\n[yellow]Download: [red]{site_constants.SITE_NAME} → [cyan]{scrape_serie.series_name} [white]\\ [magenta]{obj_episode.name} ([cyan]S{index_season_selected}E{index_episode_selected}) \n")

    # Define filename and path for the downloaded video
    mp4_name = f"{map_episode_title(scrape_serie.series_name, index_season_selected, index_episode_selected, obj_episode.name)}.{extension_output}"
    mp4_path = os.path.join(site_constants.SERIES_FOLDER, scrape_serie.series_name, f"S{index_season_selected}")

    # Retrieve scws and if available master playlist
    video_source = VideoSource(obj_episode.url)
    video_source.make_request(obj_episode.url)
    master_playlist = video_source.get_playlist()

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