# 03.07.24

import os


# External library
from rich.console import Console


# Internal utilities
from StreamingCommunity.Util.os import os_manager
from StreamingCommunity.Util.message import start_message
from StreamingCommunity.Lib.Downloader import MP4_downloader


# Logic class
from StreamingCommunity.Api.Template.config_loader import site_constant
from StreamingCommunity.Api.Template.Class.SearchType import MediaItem


# Player
from StreamingCommunity.Api.Player.mixdrop import VideoSource


# Variable
console = Console()


def download_film(select_title: MediaItem) -> str:
    """
    Downloads a film using the provided obj.

    Parameters:
        - select_title (MediaItem): The media item to be downloaded. This should be an instance of the MediaItem class, containing attributes like `name` and `url`.

    Return:
        - str: output path
    """
    start_message()
    console.print(f"[bold yellow]Download:[/bold yellow] [red]{site_constant.SITE_NAME}[/red] → [cyan]{select_title.name}[/cyan] \n")

    # Setup api manger
    video_source = VideoSource(select_title.url)
    src_mp4 = video_source.get_playlist()
    print(src_mp4)

    # Define output path
    title_name = os_manager.get_sanitize_file(select_title.name) +".mp4"
    mp4_path = os.path.join(site_constant.MOVIE_FOLDER, title_name.replace(".mp4", ""))

    # Start downloading
    path, kill_handler = MP4_downloader(
        url=src_mp4,
        path=mp4_path,
            headers_= {
            'Connection': 'keep-alive',
            'Origin': 'https://mixdrop.sb',
            'Range': 'bytes=0-',
            'Referer': 'https://mixdrop.sb/',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36 OPR/118.0.0.0',
        }
    )

    return path, kill_handler