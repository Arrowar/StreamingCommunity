# 16.03.25

import os
from urllib.parse import urlparse, parse_qs


# External library
from rich.console import Console


# Internal utilities
from StreamingCommunity.Util.os import os_manager
from StreamingCommunity.Util.message import start_message
from StreamingCommunity.Util.config_json import config_manager
from StreamingCommunity.Util.os import get_wvd_path
from StreamingCommunity.Lib.Downloader.DASH.downloader import DASH_Download


# Logic class
from StreamingCommunity.Api.Template.config_loader import site_constant
from StreamingCommunity.Api.Template.Class.SearchType import MediaItem


# Player
from .util.get_license import get_playback_session, get_auth_token, generate_device_id


# Variable
console = Console()
max_timeout = config_manager.get_int("REQUESTS", "timeout")


def download_film(select_title: MediaItem) -> str:
    """
    Downloads a film using the provided film ID, title name, and domain.

    Parameters:
        - select_title (MediaItem): The selected media item.

    Return:
        - str: output path if successful, otherwise None
    """
    start_message()
    console.print(f"[bold yellow]Download:[/bold yellow] [red]{site_constant.SITE_NAME}[/red] → [cyan]{select_title.name}[/cyan] \n")

    # Define filename and path for the downloaded video
    mp4_name = os_manager.get_sanitize_file(select_title.name) + ".mp4"
    mp4_path = os.path.join(site_constant.MOVIE_FOLDER, mp4_name.replace(".mp4", ""))

    # Generate mpd and license URLs
    url_id = select_title.get('url').split('/')[-1]
    device_id = generate_device_id()
    mpd_url, mpd_headers = get_playback_session(get_auth_token(device_id), device_id, url_id)
    parsed_url = urlparse(mpd_url)
    query_params = parse_qs(parsed_url.query)

    # Download the episode
    r_proc = DASH_Download(
        cdm_device=get_wvd_path(),
        license_url='https://www.crunchyroll.com/license/v1/license/widevine',
        mpd_url=mpd_url,
        output_path=os.path.join(mp4_path, mp4_name),
    )
    r_proc.parse_manifest(custom_headers=mpd_headers)

    # Create headers for license request
    license_headers = mpd_headers.copy()
    license_headers.update({
        "x-cr-content-id": url_id,
        "x-cr-video-token": query_params['playbackGuid'][0],
    })

    if r_proc.download_and_decrypt(custom_headers=license_headers):
        r_proc.finalize_output()

    # Get final output path and status
    status = r_proc.get_status()

    if status['error'] is not None and status['path']:
        try: os.remove(status['path'])
        except Exception: pass

    return status['path'], status['stopped']