# 17.09.24

import os
import sys
import logging


# External libraries
import httpx
from bs4 import BeautifulSoup


# Internal utilities
from StreamingCommunity.Util.console import console
from StreamingCommunity.Util.os import os_manager
from StreamingCommunity.Util.message import start_message
from StreamingCommunity.Util.headers import get_headers
from StreamingCommunity.Lib.Downloader import HLS_Downloader


# Player
from StreamingCommunity.Api.Player.supervideo import VideoSource


# Logic class
from StreamingCommunity.Api.Template.config_loader import site_constant
from StreamingCommunity.Lib.TMBD import Json_film


def download_film(movie_details: Json_film) -> str:
    """
    Downloads a film using the provided tmbd id.

    Parameters:
        - movie_details (Json_film): Class with info about film title.
    
    Return:
        - str: output path
    """

    # Start message and display film information
    start_message()
    console.print(f"[yellow]Download:  [red]{movie_details.title} \n")
    
    # Make request to main site
    try:
        url = f"https://{site_constant.SITE_NAME}.{site_constant.DOMAIN_NOW}/set-movie-a/{movie_details.imdb_id}"
        response = httpx.get(url, headers={'User-Agent': get_headers()})
        response.raise_for_status()

    except:
        logging.error(f"Not found in the server. Dict: {movie_details}")
        raise

    if "not found" in str(response.text):
        logging.error(f"Cant find in the server, Element: {movie_details}")
        raise

    # Extract supervideo url
    soup = BeautifulSoup(response.text, "html.parser")
    player_links = soup.find("ul", class_ = "_player-mirrors").find_all("li")
    supervideo_url = "https:" + player_links[0].get("data-link")

    # Set domain and media ID for the video source
    video_source = VideoSource(url=supervideo_url)
    
    # Define output path
    title_name = os_manager.get_sanitize_file(movie_details.title) + ".mp4"
    mp4_path = os.path.join(site_constant.MOVIE_FOLDER, title_name.replace(".mp4", ""))

    # Get m3u8 master playlist
    master_playlist = video_source.get_playlist()

    # Download the film using the m3u8 playlist, and output filename
    r_proc = HLS_Downloader(
        m3u8_url=master_playlist, 
        output_path=os.path.join(mp4_path, title_name)
    ).start()

    if "error" in r_proc.keys():
        try:
            os.remove(r_proc['path'])
        except:
            pass

    return r_proc['path']