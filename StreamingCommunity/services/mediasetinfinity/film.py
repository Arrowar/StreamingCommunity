# 21.05.24

import os
import urllib.parse
from typing import Tuple


# External library
from rich.console import Console


# Internal utilities
from StreamingCommunity.utils import os_manager, config_manager, start_message
from StreamingCommunity.services._base import site_constants, MediaItem
from StreamingCommunity.core.downloader import DASH_Downloader


# Logic
from .util.fix_mpd import get_manifest
from .util.get_license import get_playback_url, get_tracking_info, generate_license_url



# Variable
console = Console()
extension_output = config_manager.config.get("M3U8_CONVERSION", "extension")


def download_film(select_title: MediaItem) -> Tuple[str, bool]:
    """
    Downloads a film using the provided film ID, title name, and domain.

    Parameters:
        - select_title (MediaItem): The selected media item.

    Return:
        - str: output path if successful, otherwise None
    """
    start_message()
    console.print(f"\n[yellow]Download: [red]{site_constants.SITE_NAME} → [cyan]{select_title.name} \n")

    # Define the filename and path for the downloaded film
    mp4_name = f"{os_manager.get_sanitize_file(select_title.name, select_title.date)}.{extension_output}"
    mp4_path = os.path.join(site_constants.MOVIE_FOLDER, mp4_name.replace(f".{extension_output}", ""))

    # Get playback URL and tracking info
    playback_json = get_playback_url(select_title.id)
    tracking_info = get_tracking_info(playback_json)['videos'][0]

    license_url, license_params = generate_license_url(tracking_info)
    if license_params:
        license_url = f"{license_url}?{urllib.parse.urlencode(license_params)}"

    # Download the episode
    return DASH_Downloader(
        mpd_url=get_manifest(tracking_info['url']),
        license_url=license_url,
        output_path=os.path.join(mp4_path, mp4_name),
    ).start()