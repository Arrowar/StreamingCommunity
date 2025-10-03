# 11.03.24

import os

# External library
from rich.console import Console


# Internal utilities
from StreamingCommunity.Util.os import os_manager
from StreamingCommunity.Util.message import start_message


# Logic class
from .util.ScrapeSerie import ScrapSerie
from StreamingCommunity.Api.Template.config_loader import site_constant
from StreamingCommunity.Api.Template.Class.SearchType import MediaItem


# Player
from StreamingCommunity import MP4_downloader
from StreamingCommunity.Api.Player.sweetpixel import VideoSource


# Variable
console = Console()


def download_film(select_title: MediaItem):
    """
    Function to download a film.

    Parameters:
        - id_film (int): The ID of the film.
        - title_name (str): The title of the film.
    """
    start_message()
    
    scrape_serie = ScrapSerie(select_title.url, site_constant.FULL_URL)
    episodes = scrape_serie.get_episodes() 

    # Get episode information
    episode_data = episodes[0]
    console.print(f"\n[bold yellow]Download:[/bold yellow] [red]{site_constant.SITE_NAME}[/red] ([cyan]{scrape_serie.get_name()}[/cyan]) \n")

    # Define filename and path for the downloaded video
    mp4_name = f"{scrape_serie.get_name()}.mp4"
    mp4_path = os.path.join(site_constant.ANIME_FOLDER, scrape_serie.get_name())

    # Create output folder
    os_manager.create_path(mp4_path)

    # Get video source for the episode
    video_source = VideoSource(site_constant.FULL_URL, episode_data, scrape_serie.session_id, scrape_serie.csrf_token)
    mp4_link = video_source.get_playlist()

    # Start downloading
    path, kill_handler = MP4_downloader(
        url=str(mp4_link).strip(),
        path=os.path.join(mp4_path, mp4_name)
    )

    return path, kill_handler