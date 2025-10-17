# 29.04.25

import os


# External library
from rich.console import Console


# Internal utilities
from StreamingCommunity.Util.os import os_manager
from StreamingCommunity.Util.config_json import config_manager
from StreamingCommunity.Util.message import start_message


# Logic class
from StreamingCommunity.Api.Template.config_loader import site_constant
from StreamingCommunity.Api.Template.Class.SearchType import MediaItem


# Player
from StreamingCommunity import HLS_Downloader
from StreamingCommunity.Api.Player.hdplayer import VideoSource


# Variable
console = Console()
extension_output = config_manager.get("M3U8_CONVERSION", "extension")


def download_film(select_title: MediaItem) -> str:
    """
    Downloads a film using the provided film ID, title name, and domain.

    Parameters:
        - domain (str): The domain of the site
        - version (str): Version of site.

    Return:
        - str: output path
    """
    start_message()
    console.print(f"\n[bold yellow]Download:[/bold yellow] [red]{site_constant.SITE_NAME}[/red] → [cyan]{select_title.name}[/cyan] \n")

    # Get master playlists
    video_source = VideoSource()
    master_playlist = video_source.get_m3u8_url(select_title.url)

    # Define the filename and path for the downloaded film
    title_name = os_manager.get_sanitize_file(select_title.name, select_title.date) + extension_output
    mp4_path = os.path.join(site_constant.MOVIE_FOLDER, title_name.replace(extension_output, ""))

    # Download the film using the m3u8 playlist, and output filename
    hls_process = HLS_Downloader(
        m3u8_url=master_playlist,
        output_path=os.path.join(mp4_path, title_name)
    ).start()

    if hls_process['error'] is not None:
        try: 
            os.remove(hls_process['path'])
        except Exception: 
            pass

    return hls_process['path']