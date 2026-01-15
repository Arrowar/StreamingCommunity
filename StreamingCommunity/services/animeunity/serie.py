# 11.03.24

import os
from typing import Tuple


# External library
from rich.console import Console
from rich.prompt import Prompt


# Internal utilities
from StreamingCommunity.utils import os_manager, start_message
from StreamingCommunity.services._base import site_constants, MediaItem
from StreamingCommunity.services._base.episode_manager import manage_selection, dynamic_format_number
from StreamingCommunity.core.downloader import MP4_Downloader, HLS_Downloader


# Logis
from .util.ScrapeSerie import ScrapeSerieAnime
from StreamingCommunity.player.vixcloud import VideoSourceAnime


# Variable
console = Console()
msg = Prompt()
KILL_HANDLER = False
DOWNOAD_HLS = False


def download_episode(index_select: int, scrape_serie: ScrapeSerieAnime, video_source: VideoSourceAnime) -> Tuple[str,bool]:
    """
    Downloads the selected episode.

    Parameters:
        - index_select (int): Index of the episode to download.

    Return:
        - str: output path
        - bool: kill handler status
    """
    start_message()

    # Get episode information
    obj_episode = scrape_serie.selectEpisode(1, index_select)
    console.print(f"\n[yellow]Download: [red]{site_constants.SITE_NAME} → [cyan]{scrape_serie.series_name} ([cyan]E{obj_episode.number}) \n")

    # Collect mp4 url
    video_source.get_embed(obj_episode.id, not DOWNOAD_HLS)

    # Create output path
    mp4_name = f"{scrape_serie.series_name}_EP_{dynamic_format_number(str(obj_episode.number))}.mp4"

    if scrape_serie.is_series:
        mp4_path = os_manager.get_sanitize_path(os.path.join(site_constants.ANIME_FOLDER, scrape_serie.series_name))
    else:
        mp4_path = os_manager.get_sanitize_path(os.path.join(site_constants.MOVIE_FOLDER, scrape_serie.series_name))

    # Create output folder
    os_manager.create_path(mp4_path)

    # Start downloading
    if not DOWNOAD_HLS:
        path, kill_handler = MP4_Downloader(
            url=str(video_source.src_mp4).strip(),
            path=os.path.join(mp4_path, mp4_name)
        )
        return path, kill_handler
    
    else:
        path, kill_handler = HLS_Downloader(
            m3u8_url=video_source.master_playlist,
            output_path=os.path.join(mp4_path, mp4_name)
        ).start()
        return path, kill_handler


def download_series(select_title: MediaItem, season_selection: str = None, episode_selection: str = None):
    """
    Function to download episodes of a TV series.

    Parameters:
        - select_title (MediaItem): The selected media item
        - season_selection (str, optional): Season selection input that bypasses manual input (usually '1' for anime)
        - episode_selection (str, optional): Episode selection input that bypasses manual input
    """
    start_message()
    scrape_serie = ScrapeSerieAnime(site_constants.FULL_URL)
    video_source = VideoSourceAnime(site_constants.FULL_URL)

    # Set up video source (only configure scrape_serie now)
    scrape_serie.setup(None, select_title.id, select_title.slug)

    # Get episode information
    episoded_count = scrape_serie.get_count_episodes()
    console.print(f"\n[green]Episodes count: [red]{episoded_count}")
    
    # Display episodes list and get user selection
    if episode_selection is None:
        last_command = msg.ask("\n[cyan]Insert media [red]index [yellow]or [red]* [cyan]to download all media [yellow]or [red]1-2 [cyan]or [red]3-* [cyan]for a range of media")
    else:
        last_command = episode_selection
        console.print(f"\n[cyan]Using provided episode selection: [yellow]{episode_selection}")

    # Manage user selection
    list_episode_select = manage_selection(last_command, episoded_count)

    # Download selected episodes
    if len(list_episode_select) == 1 and last_command != "*":
        path, _ = download_episode(list_episode_select[0]-1, scrape_serie, video_source)
        return path

    # Download all other episodes selected
    else:
        kill_handler = False
        for i_episode in list_episode_select:
            if kill_handler:
                break
            _, kill_handler = download_episode(i_episode-1, scrape_serie, video_source)