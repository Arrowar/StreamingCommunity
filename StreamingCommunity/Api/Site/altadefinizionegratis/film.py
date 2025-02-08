# 26.05.24

import os


# Internal utilities
from StreamingCommunity.Util.console import console
from StreamingCommunity.Util.os import os_manager
from StreamingCommunity.Util.message import start_message
from StreamingCommunity.Lib.Downloader import HLS_Downloader
from StreamingCommunity.TelegramHelp.telegram_bot import TelegramSession, get_bot_instance

# Logic class
from StreamingCommunity.Api.Template.Class.SearchType import MediaItem


# Player
from StreamingCommunity.Api.Player.supervideo import VideoSource


# Config
from .costant import MOVIE_FOLDER, TELEGRAM_BOT


def download_film(select_title: MediaItem) -> str:
    """
    Downloads a film using the provided film ID, title name, and domain.

    Parameters:
        - title_name (str): The name of the film title.
        - url (str): The url of the video

    Return:
        - str: output path
    """
    if TELEGRAM_BOT:
        bot = get_bot_instance()
        bot.send_message(f"Download in corso:\n{select_title.name}", None)

        # Get script_id
        script_id = TelegramSession.get_session()
        if script_id != "unknown":
            TelegramSession.updateScriptId(script_id, select_title.name)

    # Start message and display film information
    start_message()
    console.print(f"[yellow]Download:  [red]{select_title.name} \n")
    console.print(f"[cyan]You can safely stop the download with [bold]Ctrl+c[bold] [cyan] \n")

    # Set domain and media ID for the video source
    video_source = VideoSource(select_title.url)

    # Define output path
    title_name = os_manager.get_sanitize_file(select_title.name) + ".mp4"
    mp4_path = os.path.join(MOVIE_FOLDER, title_name.replace(".mp4", ""))

    # Get m3u8 master playlist
    master_playlist = video_source.get_playlist()

    # Download the film using the m3u8 playlist, and output filename
    r_proc = HLS_Downloader(
        m3u8_url=master_playlist,
        output_path=os.path.join(mp4_path, title_name)
    ).start()

    if TELEGRAM_BOT:

        # Delete script_id
        script_id = TelegramSession.get_session()
        if script_id != "unknown":
            TelegramSession.deleteScriptId(script_id)

    if "error" in r_proc.keys():
        try:
            os.remove(r_proc['path'])
        except:
            pass

    return r_proc['path']