# 21.05.24

import os
from typing import Tuple


# External library
from rich.console import Console


# Internal utilities
from StreamingCommunity.Util.os import os_manager, get_wvd_path
from StreamingCommunity.Util.message import start_message
from StreamingCommunity.Util.headers import get_headers


# Logic class
from StreamingCommunity.Api.Template.config_loader import site_constant
from StreamingCommunity.Api.Template.Class.SearchType import MediaItem
from StreamingCommunity.Api.Template.Util import assert_item_is_movie


# Player
from .util.fix_mpd import get_manifest
from StreamingCommunity import DASH_Downloader
from .util.get_license import get_bearer_token, get_playback_url, get_tracking_info, generate_license_url


# Variable
console = Console()


def download_film(select_title: MediaItem) -> Tuple[str, bool]:
    """
    Downloads a film using the provided film ID, title name, and domain.

    Parameters:
        - select_title (MediaItem): The selected media item.

    Return:
        - str: output path if successful, otherwise None
    """
    if not assert_item_is_movie(select_title):
        console.print("[red]Selected item is not a film.")
        return None, False

    start_message()
    console.print(f"[bold yellow]Download:[/bold yellow] [red]{site_constant.SITE_NAME}[/red] → [cyan]{select_title.name}[/cyan] \n")

    # Define the filename and path for the downloaded film
    title_name = os_manager.get_sanitize_file(select_title.name) + ".mp4"
    mp4_path = os.path.join(site_constant.MOVIE_FOLDER, title_name.replace(".mp4", ""))

    # Generate mpd and license URLs
    bearer = get_bearer_token()

    # Extract ID from the episode URL
    episode_id = select_title.url.split('_')[-1]
    if "http" in episode_id:
        try: episode_id = select_title.url.split('/')[-1]
        except Exception:
            console.print(f"[red]Error:[/red] Failed to parse episode ID from URL: {select_title.url}")
            return None, True

    playback_json = get_playback_url(bearer, episode_id)
    tracking_info = get_tracking_info(bearer, playback_json)[0]

    license_url = generate_license_url(bearer, tracking_info)
    mpd_url = get_manifest(tracking_info['video_src'])

    # Download the episode
    r_proc =  DASH_Downloader(
        cdm_device=get_wvd_path(),
        license_url=license_url,
        mpd_url=mpd_url,
        output_path=mp4_path,
    )
    r_proc.parse_manifest(custom_headers=get_headers())

    if r_proc.download_and_decrypt():
        r_proc.finalize_output()

    # Get final output path and status
    status = r_proc.get_status()

    if status['error'] is not None and status['path']:
        try: os.remove(status['path'])
        except Exception: pass

    return status['path'], status['stopped']
