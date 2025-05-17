# 16.03.25

import os
import re


# External library
import httpx
from bs4 import BeautifulSoup
from rich.console import Console


# Internal utilities
from StreamingCommunity.Util.os import os_manager
from StreamingCommunity.Util.message import start_message
from StreamingCommunity.Util.headers import get_headers
from StreamingCommunity.Util.config_json import config_manager
from StreamingCommunity.Lib.Downloader import HLS_Downloader
from StreamingCommunity.TelegramHelp.telegram_bot import get_bot_instance, TelegramSession


# Logic class
from StreamingCommunity.Api.Template.config_loader import site_constant
from StreamingCommunity.Api.Template.Class.SearchType import MediaItem


# Player
from StreamingCommunity.Api.Player.supervideo import VideoSource


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
    if site_constant.TELEGRAM_BOT:
        bot = get_bot_instance()
        bot.send_message(f"Download in corso:\n{select_title.name}", None)

        # Viene usato per lo screen
        console.print(f"## Download: [red]{select_title.name} ##")

        # Get script_id
        script_id = TelegramSession.get_session()
        if script_id != "unknown":
            TelegramSession.updateScriptId(script_id, select_title.name)

    start_message()
    console.print(f"[bold yellow]Download:[/bold yellow] [red]{site_constant.SITE_NAME}[/red] → [cyan]{select_title.name}[/cyan] \n")
    
    # Extract mostraguarda URL
    try:
        response = httpx.get(select_title.url, headers=get_headers(), timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        iframes = soup.find_all('iframe')
        mostraguarda = iframes[0]['src']
    
    except Exception as e:
        console.print(f"[red]Site: {site_constant.SITE_NAME}, request error: {e}, get mostraguarda")

    # Extract supervideo URL
    try:
        response = httpx.get(mostraguarda, headers=get_headers(), timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        pattern = r'//supervideo\.[^/]+/[a-z]/[a-zA-Z0-9]+'
        supervideo_match = re.search(pattern, response.text)
        supervideo_url = 'https:' + supervideo_match.group(0)

    except Exception as e:
        console.print(f"[red]Site: {site_constant.SITE_NAME}, request error: {e}, get supervideo URL")

    # Init class
    video_source = VideoSource(supervideo_url)
    master_playlist = video_source.get_playlist()

    # Define the filename and path for the downloaded film
    title_name = os_manager.get_sanitize_file(select_title.name) + ".mp4"
    mp4_path = os.path.join(site_constant.MOVIE_FOLDER, title_name.replace(".mp4", ""))

    # Download the film using the m3u8 playlist, and output filename
    r_proc = HLS_Downloader(
        m3u8_url=master_playlist,
        output_path=os.path.join(mp4_path, title_name)
    ).start()

    if site_constant.TELEGRAM_BOT:

        # Delete script_id
        script_id = TelegramSession.get_session()
        if script_id != "unknown":
            TelegramSession.deleteScriptId(script_id)

    if r_proc['error'] is not None:
        try: os.remove(r_proc['path'])
        except: pass

    return r_proc['path']