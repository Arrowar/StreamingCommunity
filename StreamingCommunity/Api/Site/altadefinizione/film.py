# 16.03.25

import os
import re


# External library
from bs4 import BeautifulSoup
from rich.console import Console


# Internal utilities
from StreamingCommunity.Util.os import os_manager
from StreamingCommunity.Util.headers import get_headers
from StreamingCommunity.Util.http_client import create_client
from StreamingCommunity.Util.message import start_message
from StreamingCommunity.Util.config_json import config_manager
from StreamingCommunity.TelegramHelp.telegram_bot import TelegramSession


# Logic class
from StreamingCommunity.Api.Template.config_loader import site_constant
from StreamingCommunity.Api.Template.Class.SearchType import MediaItem


# Player
from StreamingCommunity import HLS_Downloader
from StreamingCommunity.Api.Player.supervideo import VideoSource


# Variable
console = Console()
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
    
    # Extract mostraguarda URL
    try:
        response = create_client(headers=get_headers()).get(select_title.url)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')
        iframes = soup.find_all('iframe')
        mostraguarda = iframes[0]['src']
    
    except Exception as e:
        console.print(f"[red]Site: {site_constant.SITE_NAME}, request error: {e}, get mostraguarda")
        return None

    # Extract supervideo URL
    supervideo_url = None
    try:
        response = create_client(headers=get_headers()).get(mostraguarda)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')
        pattern = r'//supervideo\.[^/]+/[a-z]/[a-zA-Z0-9]+'
        supervideo_match = re.search(pattern, response.text)
        supervideo_url = 'https:' + supervideo_match.group(0)

    except Exception as e:
        console.print(f"[red]Site: {site_constant.SITE_NAME}, request error: {e}, get supervideo URL")
        console.print("[yellow]This content will be available soon![/yellow]")
        return None
    
    # Init class
    video_source = VideoSource(supervideo_url)
    master_playlist = video_source.get_playlist()

    # Define the filename and path for the downloaded film
    title_name = os_manager.get_sanitize_file(select_title.name, select_title.date) + extension_output
    mp4_path = os.path.join(site_constant.MOVIE_FOLDER, title_name.replace(extension_output, ""))

    # Download the film using the m3u8 playlist, and output filename
    hls_process = HLS_Downloader(
        m3u8_url=master_playlist,
        output_path=os.path.join(mp4_path, title_name)
    ).start()

    if site_constant.TELEGRAM_BOT:

        # Delete script_id
        script_id = TelegramSession.get_session()
        if script_id != "unknown":
            TelegramSession.deleteScriptId(script_id)

    if hls_process['error'] is not None:
        try: 
            os.remove(hls_process['path'])
        except Exception: 
            pass

    return hls_process['path']