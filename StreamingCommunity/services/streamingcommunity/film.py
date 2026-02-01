# 3.12.23

import os


# External library
from rich.console import Console


# Internal utilities
from StreamingCommunity.utils import os_manager, config_manager, tmdb_client, start_message
from StreamingCommunity.services._base import site_constants, MediaItem
from StreamingCommunity.core.downloader import HLS_Downloader


# Logic
from StreamingCommunity.player.vixcloud import VideoSource


# Variable
console = Console()
extension_output = config_manager.config.get("M3U8_CONVERSION", "extension")
use_other_api = config_manager.login.get("TMDB", "api_key") != ""


def download_film(select_title: MediaItem) -> str:
    """
    Downloads a film using the provided film ID, title name, and domain.

    Parameters:
        - select_title (MediaItem): Media item with title information

    Return:
        - str: output path
    """
    start_message()
    console.print(f"\n[yellow]Download: [red]{site_constants.SITE_NAME} → [cyan]{select_title.name} \n")

    # Prepare TMDB data 
    tmdb_data = None
    if use_other_api:
        result = tmdb_client.get_type_and_id_by_slug_year(select_title.slug, select_title.year, "movie", select_title.provider_language)
        
        if result and result.get('id') and result.get('type') == 'movie':
            tmdb_data = {'id': result.get('id')}

    # Init class
    video_source = VideoSource(f"{site_constants.FULL_URL}/{select_title.provider_language}", False, select_title.id, tmdb_data=tmdb_data)

    # Retrieve iframe only if not using TMDB API
    if tmdb_data is None:
        video_source.get_iframe(select_title.id)
    
    video_source.get_content()
    master_playlist = video_source.get_playlist()

    if master_playlist is None:
        console.print(f"[red]Site: {site_constants.SITE_NAME}, error: No master playlist found")
        return None

    # Define the filename and path for the downloaded film
    mp4_name = f"{os_manager.get_sanitize_file(select_title.name, select_title.year)}.{extension_output}"
    mp4_path = os.path.join(site_constants.MOVIE_FOLDER, mp4_name.replace(f".{extension_output}", ""))

    # Download the film using the m3u8 playlist, and output filename
    return HLS_Downloader(
        m3u8_url=master_playlist,
        output_path=os.path.join(mp4_path, mp4_name)
    ).start()