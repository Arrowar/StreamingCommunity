# 17.09.24

import os
import logging


# External libraries
from bs4 import BeautifulSoup
from rich.console import Console


# Internal utilities
from StreamingCommunity.utils import os_manager, config_manager, start_message
from StreamingCommunity.utils.http_client import create_client, get_headers
from StreamingCommunity.services._base import site_constants, Entries


# Downloader
from StreamingCommunity.core.downloader import HLS_Downloader


# Player
from StreamingCommunity.player.supervideo import VideoSource


# Variable
console = Console()
extension_output = config_manager.config.get("M3U8_CONVERSION", "extension")


def download_film(select_title: Entries) -> str:
    """
    Downloads a film using the provided Entries information.

    Parameters:
        - select_title (Entries): Class with info about film title.

    Return:
        - str: output path
    """
    start_message()
    console.print(f"[bold yellow]Download: [red]{site_constants.SITE_NAME}[/red] → [cyan]{select_title.name} \n")

    imdb_id = select_title.imdb_id
    if not imdb_id:
        logging.error(f"No IMDB ID found for {select_title.name}")
        return None

    try:
        url = f"https://mostraguarda.stream/set-movie-a/{imdb_id}"
        response = create_client(headers=get_headers()).get(url)
        response.raise_for_status()

    except Exception as e:
        logging.error(f"Not found in the server. Title: {select_title.name}, error: {e}")
        raise

    if "not found" in str(response.text):
        logging.error(f"Can't find in the server: {select_title.name}.")
        return None

    # Extract supervideo url
    soup = BeautifulSoup(response.text, "html.parser")
    player_links = soup.find("ul", class_="_player-mirrors").find_all("li")
    if not player_links:
        logging.error(f"No player links found for {select_title.name}")
        return None
    
    supervideo_url = None
    for li in player_links:
        data_link = li.get("data-link")
        if data_link and "supervideo" in data_link:
            supervideo_url = "https:" + data_link if data_link.startswith("//") else data_link
            break
    
    if not supervideo_url:
        logging.error(f"No supervideo link found for {select_title.name}")
        return None

    # Set domain and media ID for the video source
    video_source = VideoSource(supervideo_url)

    # Define output path
    title_name = os_manager.get_sanitize_file(select_title.name, select_title.year) + f".{extension_output}"
    mp4_path = os.path.join(site_constants.MOVIE_FOLDER, title_name.replace(f".{extension_output}", ""))

    # Get m3u8 master playlist
    master_playlist = video_source.get_playlist()

    # Download the film using the m3u8 playlist, and output filename
    path, kill_handler = HLS_Downloader(
        m3u8_url=master_playlist,
        output_path=os.path.join(mp4_path, title_name)
    ).start()
    return path, kill_handler