# 16.03.25

import os
import time
from urllib.parse import urlparse, parse_qs


# External library
from rich.console import Console


# Internal utilities
from StreamingCommunity.utils import config_manager, os_manager, start_message
from StreamingCommunity.services._base import site_constants, MediaItem
from StreamingCommunity.core.downloader import DASH_Downloader


# Logic
from .util.get_license import get_playback_session, CrunchyrollClient


# Variable
console = Console()
extension_output = config_manager.config.get("M3U8_CONVERSION", "extension")


def download_film(select_title: MediaItem) -> str:
    """
    Downloads a film.

    Parameters:
        - select_title (MediaItem): The selected media item.

    Return:
        - str: output path if successful, otherwise None
    """
    start_message()
    console.print(f"\n[yellow]Download: [red]{site_constants.SITE_NAME} → [cyan]{select_title.name} \n")

    # Initialize Crunchyroll client
    client = CrunchyrollClient()

    # Define filename and path
    mp4_name = f"{os_manager.get_sanitize_file(select_title.name, select_title.date)}.{extension_output}"
    mp4_path = os.path.join(site_constants.MOVIE_FOLDER, mp4_name.replace(f".{extension_output}", ""))

    # Extract media ID
    url_id = select_title.get('url').split('/')[-1]
    
    # Get playback session
    mpd_url, mpd_headers, mpd_list_sub, token, audio_locale = get_playback_session(client, url_id, None)
    
    # Parse playback token from URL
    parsed_url = urlparse(mpd_url)
    query_params = parse_qs(parsed_url.query)
    playback_guid = query_params.get('playbackGuid', [token])[0] if query_params.get('playbackGuid') else token

    # Creaate headers for license request
    license_headers = mpd_headers.copy()
    license_headers.update({
        "x-cr-content-id": url_id,
        "x-cr-video-token": playback_guid,
    })

    # Download the film
    out_path, need_stop = DASH_Downloader(
        mpd_url=mpd_url,
        mpd_headers=mpd_headers,
        license_url='https://www.crunchyroll.com/license/v1/license/widevine',
        license_headers=license_headers,
        mpd_sub_list=mpd_list_sub,
        output_path=os.path.join(mp4_path, mp4_name),
    ).start()

    # Small delay
    time.sleep(1)
    return out_path, need_stop