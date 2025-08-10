# 21.05.24

import os
from typing import Tuple


# External library
import httpx
from rich.console import Console


# Internal utilities
from StreamingCommunity.Util.os import os_manager
from StreamingCommunity.Util.headers import get_headers
from StreamingCommunity.Util.message import start_message


# Logic class
from StreamingCommunity.Api.Template.config_loader import site_constant
from StreamingCommunity.Api.Template.Class.SearchType import MediaItem
from StreamingCommunity.Api.Template.Util import assert_item_is_movie


# Player
from StreamingCommunity import HLS_Downloader
from StreamingCommunity.Api.Player.mediapolisvod import VideoSource


# Variable
console = Console()


def download_film(select_title: MediaItem) -> Tuple[str, bool]:
    """
    Downloads a film using the provided MediaItem information.

    Parameters:
        - select_title (MediaItem): The media item containing film information

    Return:
        - str: Path to downloaded file
        - bool: Whether download was stopped
    """
    # If a TV item is passed to a film downloader while running as job, fail fast
    if not assert_item_is_movie(select_title):
        console.print("[red]Selected item is not a film.")
        return None, False

    start_message()
    console.print(f"[bold yellow]Download:[/bold yellow] [red]{site_constant.SITE_NAME}[/red] → [cyan]{select_title.name}[/cyan] \n")

    # Extract m3u8 URL from the film's URL
    response = httpx.get(select_title.url + ".json", headers=get_headers(), timeout=10)
    first_item_path =  "https://www.raiplay.it" + response.json().get("first_item_path")
    master_playlist = VideoSource.extract_m3u8_url(first_item_path)

    # Define the filename and path for the downloaded film
    title_name = os_manager.get_sanitize_file(select_title.name) + ".mp4"
    mp4_path = os.path.join(site_constant.MOVIE_FOLDER, title_name.replace(".mp4", ""))

    # Download the film using the m3u8 playlist, and output filename
    r_proc = HLS_Downloader(
        m3u8_url=master_playlist,
        output_path=os.path.join(mp4_path, title_name)
    ).start()

    if r_proc['error'] is not None:
        try: os.remove(r_proc['path'])
        except: pass

    return r_proc['path'], r_proc['stopped']
