# 16.03.25

import os


# External library
from bs4 import BeautifulSoup
from rich.console import Console


# Internal utilities
from StreamingCommunity.Util.os import os_manager
from StreamingCommunity.Util.headers import get_headers
from StreamingCommunity.Util.http_client import create_client_curl
from StreamingCommunity.Util.message import start_message
from StreamingCommunity.Util.config_json import config_manager


# Logic class
from StreamingCommunity.Api.Template.config_loader import site_constant
from StreamingCommunity.Api.Template.Class.SearchType import MediaItem


# Player
from StreamingCommunity import Mega_Downloader


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
    
    mega_link = None
    try:
        response = create_client_curl(headers=get_headers()).get(select_title.url)
        response.raise_for_status()

        # Parse HTML to find mega link
        soup = BeautifulSoup(response.text, 'html.parser')
        for a in soup.find_all("a", href=True):

            if "?!" in a["href"].lower().strip():
                mega_link = "https://mega.nz/file/" + a["href"].split("/")[-1].replace('?!', '')
                break

            if "/?file/" in a["href"].lower().strip():
                mega_link = "https://mega.nz/file/" + a["href"].split("/")[-1].replace('/?file/', '')
                break

    except Exception as e:
        console.print(f"[red]Site: {site_constant.SITE_NAME}, request error: {e}, get mostraguarda")
        return None

    # Define the filename and path for the downloaded film
    title_name = os_manager.get_sanitize_file(select_title.name, select_title.date) + extension_output
    mp4_path = os.path.join(site_constant.MOVIE_FOLDER, title_name.replace(extension_output, ""))

    # Download the film using the mega downloader
    mega = Mega_Downloader()
    m = mega.login()

    if mega_link is None:
        console.print(f"[red]Site: {site_constant.SITE_NAME}, error: Mega link not found for url: {select_title.url}[/red]")
        return None

    output_path = m.download_url(
        url=mega_link,
        dest_path=os.path.join(mp4_path, title_name)
    )
    return output_path