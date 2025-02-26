# 11.03.24

import os
import logging
from typing import Tuple


# External library
from rich.console import Console
from rich.prompt import Prompt


# Internal utilities
from StreamingCommunity.Util.os import os_manager
from StreamingCommunity.Util.message import start_message
from StreamingCommunity.Lib.Downloader import MP4_downloader
from StreamingCommunity.TelegramHelp.telegram_bot import TelegramSession, get_bot_instance


# Logic class
from .util.ScrapeSerie import ScrapeSerieAnime
from StreamingCommunity.Api.Template.config_loader import site_constant
from StreamingCommunity.Api.Template.Util import manage_selection, dynamic_format_number
from StreamingCommunity.Api.Template.Class.SearchType import MediaItem


# Player
from StreamingCommunity.Api.Player.vixcloud import VideoSourceAnime


# Variable
console = Console()
msg = Prompt()
KILL_HANDLER = bool(False)



def download_episode(index_select: int, scrape_serie: ScrapeSerieAnime, video_source: VideoSourceAnime) -> Tuple[str,bool]:
    """
    Downloads the selected episode.

    Parameters:
        - index_select (int): Index of the episode to download.

    Return:
        - str: output path
        - bool: kill handler status
    """
    if site_constant.TELEGRAM_BOT:
        bot = get_bot_instance()

    # Get information about the selected episode
    obj_episode = scrape_serie.get_info_episode(index_select)

    if obj_episode is not None:

        start_message()
        console.print(f"[yellow]Download:  [red]EP_{obj_episode.number} \n")
        console.print("[cyan]You can safely stop the download with [bold]Ctrl+c[bold] [cyan] \n")

        if site_constant.TELEGRAM_BOT:
            bot.send_message(f"Download in corso:\nTitolo:{scrape_serie.series_name}\nEpisodio: {obj_episode.number}", None)

            # Get script_id
            script_id = TelegramSession.get_session()
            if script_id != "unknown":
                TelegramSession.updateScriptId(script_id, f"{scrape_serie.series_name} - E{obj_episode.number}")

        # Collect mp4 url
        video_source.get_embed(obj_episode.id)

        # Create output path
        title_name = f"{scrape_serie.series_name}_EP_{dynamic_format_number(int(obj_episode.number))}.mp4"

        if scrape_serie.is_series:
            mp4_path = os_manager.get_sanitize_path(os.path.join(site_constant.ANIME_FOLDER, scrape_serie.series_name))

        else:
            mp4_path = os_manager.get_sanitize_path(os.path.join(site_constant.MOVIE_FOLDER, scrape_serie.series_name))

        # Create output folder
        os_manager.create_path(mp4_path)

        # Start downloading
        path, kill_handler = MP4_downloader(
            url=str(video_source.src_mp4).strip(),
            path=os.path.join(mp4_path, title_name)
        )

        return path, kill_handler

    else:
        logging.error(f"Skip index: {index_select} cant find info with api.")
        return None, True


def download_series(select_title: MediaItem):
    """
    Function to download episodes of a TV series.

    Parameters:
        - tv_id (int): The ID of the TV series.
        - tv_name (str): The name of the TV series.
    """
    start_message()

    if site_constant.TELEGRAM_BOT:
        bot = get_bot_instance()

    scrape_serie = ScrapeSerieAnime(site_constant.FULL_URL)
    video_source = VideoSourceAnime(site_constant.FULL_URL)

    # Set up video source
    scrape_serie.setup(None, select_title.id, select_title.slug)

    # Get the count of episodes for the TV series
    episoded_count = scrape_serie.get_count_episodes()
    console.print(f"[cyan]Episodes find: [red]{episoded_count}")

    if site_constant.TELEGRAM_BOT:
        console.print(f"\n[cyan]Insert media [red]index [yellow]or [red]* [cyan]to download all media [yellow]or [red]1-2 [cyan]or [red]3-* [cyan]for a range of media")
        bot.send_message(f"Episodi trovati: {episoded_count}", None)

        last_command = bot.ask(
            "select_title",
            f"Inserisci l'indice del media o * per scaricare tutti i media, oppure 1-2 o 3-* per un intervallo di media.",
            None
        )

    else:

        # Prompt user to select an episode index
        last_command = msg.ask("\n[cyan]Insert media [red]index [yellow]or [red]* [cyan]to download all media [yellow]or [red]1-2 [cyan]or [red]3-* [cyan]for a range of media")

    # Manage user selection
    list_episode_select = manage_selection(last_command, episoded_count)

    # Download selected episodes
    if len(list_episode_select) == 1 and last_command != "*":
        path, _ = download_episode(list_episode_select[0]-1, scrape_serie, video_source)[0]
        return path

    # Download all other episodes selecter
    else:
        kill_handler = False
        for i_episode in list_episode_select:
            if kill_handler:
                break
            _, kill_handler = download_episode(i_episode-1, scrape_serie, video_source)

    if site_constant.TELEGRAM_BOT:
        bot.send_message(f"Finito di scaricare tutte le serie e episodi", None)

        # Get script_id
        script_id = TelegramSession.get_session()
        if script_id != "unknown":
            TelegramSession.deleteScriptId(script_id)


def download_film(select_title: MediaItem):
    """
    Function to download a film.

    Parameters:
        - id_film (int): The ID of the film.
        - title_name (str): The title of the film.
    """

    # Init class
    scrape_serie = ScrapeSerieAnime(site_constant.FULL_URL)
    video_source = VideoSourceAnime(site_constant.FULL_URL)

    # Set up video source
    scrape_serie.setup(None, select_title.id, select_title.slug)
    scrape_serie.is_series = False

    # Start download
    download_episode(0, scrape_serie, video_source)