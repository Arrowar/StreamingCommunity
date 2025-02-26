# 02.07.24

import os


# External libraries
import httpx
from bs4 import BeautifulSoup
from rich.console import Console


# Internal utilities
from StreamingCommunity.Util.os import os_manager
from StreamingCommunity.Util.message import start_message
from StreamingCommunity.Util.headers import get_userAgent
from StreamingCommunity.Lib.Downloader import TOR_downloader


# Logic class
from StreamingCommunity.Api.Template.config_loader import site_constant
from StreamingCommunity.Api.Template.Class.SearchType import MediaItem


# Variable
console = Console()


def download_title(select_title: MediaItem):
    """
    Downloads a media item and saves it as an MP4 file.

    Parameters:
        - select_title (MediaItem): The media item to be downloaded. This should be an instance of the MediaItem class, containing attributes like `name` and `url`.
    """
    start_message()
    console.print(f"[yellow]Download:  [red]{select_title.name} \n")
    print() 

    # Define output path
    title_name = os_manager.get_sanitize_file(select_title.name)
    mp4_path = os.path.join(site_constant.MOVIE_FOLDER, title_name.replace(".mp4", ""))
    
    # Create output folder
    os_manager.create_path(mp4_path)                                                                    

    # Make request to page with magnet
    response = httpx.get(
        url=f"{site_constant.FULL_URL}{select_title.url}",
        headers={
            'user-agent': get_userAgent()
        }, 
        follow_redirects=True
    )

    # Create soup and find table
    soup = BeautifulSoup(response.text, "html.parser")
    final_url = soup.find("a", class_="torrentdown1").get("href")

    # Tor manager
    manager = TOR_downloader()
    manager.add_magnet_link(final_url)
    manager.start_download()
    manager.move_downloaded_files(mp4_path)