# 11.03.24

import os
from typing import Tuple



# External library
from rich.console import Console
from rich.prompt import Prompt


# Internal utilities
from StreamingCommunity.utils import os_manager, start_message
from StreamingCommunity.services._base import site_constants, MediaItem
from StreamingCommunity.services._base.tv_display_manager import manage_selection, dynamic_format_number


# Downloader
from StreamingCommunity.core.downloader import MP4_Downloader


# Player
from StreamingCommunity.player.sweetpixel import VideoSource


# Logic
from .scrapper import ScrapSerie


# Variable
console = Console()
msg = Prompt()


def download_film(select_title: MediaItem):
    """
    Downloads a film using the provided MediaItem information.
    """
    start_message()
    scrape_serie = ScrapSerie(select_title.url, site_constants.FULL_URL)
    episodes = scrape_serie.get_episodes() 

    # Get episode information
    episode_data = episodes[0]
    console.print(f"\n[yellow]Download: [red]{site_constants.SITE_NAME} ([cyan]{scrape_serie.get_name()}) \n")

    # Define filename and path for the downloaded video
    serie_name_with_year = os_manager.get_sanitize_file(scrape_serie.get_name(), select_title.year)
    mp4_name = f"{serie_name_with_year}.mp4"
    mp4_path = os.path.join(site_constants.ANIME_FOLDER, serie_name_with_year.replace('.mp4', ''))

    # Create output folder
    os_manager.create_path(mp4_path)

    # Get video source for the episode
    video_source = VideoSource(site_constants.FULL_URL, episode_data, scrape_serie.session_id, scrape_serie.csrf_token)
    mp4_link = video_source.get_playlist()

    # Start downloading
    path, kill_handler = MP4_Downloader(
        url=str(mp4_link).strip(),
        path=os.path.join(mp4_path, mp4_name)
    )

    return path, kill_handler


def download_episode(index_select: int, scrape_serie: ScrapSerie) -> Tuple[str,bool]:
    """
    Downloads a specific episode from the specified season.
    """
    start_message()
    episode_data = scrape_serie.selectEpisode(1, index_select)
    console.print(f"\n[yellow]Download: [red]{site_constants.SITE_NAME} → [cyan]{scrape_serie.get_name()} ([cyan]E{str(index_select+1)}) \n")

    # Define filename and path for the downloaded video
    mp4_name = f"{scrape_serie.get_name()}_EP_{dynamic_format_number(str(index_select+1))}.mp4"
    mp4_path = os.path.join(site_constants.ANIME_FOLDER, scrape_serie.get_name())

    # Create output folder
    os_manager.create_path(mp4_path)

    # Get video source for the episode
    video_source = VideoSource(site_constants.FULL_URL, episode_data, scrape_serie.session_id, scrape_serie.csrf_token)
    mp4_link = video_source.get_playlist()

    # Start downloading
    path, kill_handler = MP4_Downloader(
        url=str(mp4_link).strip(),
        path=os.path.join(mp4_path, mp4_name)
    )

    return path, kill_handler

def download_series(select_title: MediaItem, season_selection: str = None, episode_selection: str = None):
    """
    Handle downloading a complete series.

    Parameters:
        - select_season (MediaItem): Series metadata from search
        - season_selection (str, optional): Pre-defined season selection that bypasses manual input
        - episode_selection (str, optional): Pre-defined episode selection that bypasses manual input
    """
    start_message()

    # Create scrap instance
    scrape_serie = ScrapSerie(select_title.url, site_constants.FULL_URL)
    episodes = scrape_serie.get_episodes() 

    # Get episode count
    console.print(f"\n[green]Episodes count: [red]{len(episodes)}")

    # Display episodes list and get user selection
    if episode_selection is None:
        last_command = msg.ask("\n[cyan]Insert media [red]index [yellow]or [red]* [cyan]to download all media [yellow]or [red]1-2 [cyan]or [red]3-* [cyan]for a range of media")
    else:
        last_command = episode_selection
        console.print(f"\n[cyan]Using provided episode selection: [yellow]{episode_selection}")

    list_episode_select = manage_selection(last_command, len(episodes))

    # Download selected episodes
    if len(list_episode_select) == 1 and last_command != "*":
        path, _ = download_episode(list_episode_select[0]-1, scrape_serie)
        return path

    # Download all selected episodes
    else:
        kill_handler = False
        for i_episode in list_episode_select:
            if kill_handler:
                break
            _, kill_handler = download_episode(i_episode-1, scrape_serie)