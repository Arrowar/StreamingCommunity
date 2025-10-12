# 16.03.25

import os
from urllib.parse import urlparse, parse_qs


# External library
from rich.console import Console


# Internal utilities
from StreamingCommunity.Util.message import start_message
from StreamingCommunity.Util.config_json import config_manager
from StreamingCommunity.Util.os import os_manager, get_wvd_path


# Logic class
from StreamingCommunity.Api.Template.config_loader import site_constant
from StreamingCommunity.Api.Template.Class.SearchType import MediaItem


# Player
from StreamingCommunity import DASH_Downloader
from .util.get_license import get_playback_session, CrunchyrollClient


# Variable
console = Console()
max_timeout = config_manager.get_int("REQUESTS", "timeout")
extension_output = config_manager.get("M3U8_CONVERSION", "extension")


def download_film(select_title: MediaItem) -> str:
    """
    Downloads a film using the provided film ID, title name, and domain.

    Parameters:
        - select_title (MediaItem): The selected media item.

    Return:
        - str: output path if successful, otherwise None
    """
    start_message()
    console.print(f"\n[bold yellow]Download:[/bold yellow] [red]{site_constant.SITE_NAME}[/red] → [cyan]{select_title.name}[/cyan] \n")

    # Initialize Crunchyroll client
    client = CrunchyrollClient()
    if not client.start():
        console.print("[bold red]Failed to authenticate with Crunchyroll.[/bold red]")
        return None, True

    # Define filename and path for the downloaded video
    mp4_name = os_manager.get_sanitize_file(select_title.name) + extension_output
    mp4_path = os.path.join(site_constant.MOVIE_FOLDER, mp4_name.replace(extension_output, ""))

    # Generate mpd and license URLs
    url_id = select_title.get('url').split('/')[-1]
    mpd_url, mpd_headers, mpd_list_sub = get_playback_session(client, url_id)
    parsed_url = urlparse(mpd_url)
    query_params = parse_qs(parsed_url.query)

    # Download the episode
    dash_process = DASH_Downloader(
        cdm_device=get_wvd_path(),
        license_url='https://www.crunchyroll.com/license/v1/license/widevine',
        mpd_url=mpd_url,
        mpd_sub_list=mpd_list_sub,
        output_path=os.path.join(mp4_path, mp4_name),
    )
    dash_process.parse_manifest(custom_headers=mpd_headers)

    # Create headers for license request
    license_headers = mpd_headers.copy()
    license_headers.update({
        "x-cr-content-id": url_id,
        "x-cr-video-token": query_params['playbackGuid'][0],
    })

    if dash_process.download_and_decrypt(custom_headers=license_headers):
        dash_process.finalize_output()

    # Get final output path and status
    status = dash_process.get_status()

    if status['error'] is not None and status['path']:
        try: 
            os.remove(status['path'])
        except Exception: 
            pass

    # Delete stream after download
    token = query_params['playbackGuid'][0]
    if token:
        client.delete_active_stream(url_id, token)

    return status['path'], status['stopped']