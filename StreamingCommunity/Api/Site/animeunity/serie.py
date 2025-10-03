# 11.03.24

import os
from typing import Tuple


# External library
from rich.console import Console
from rich.prompt import Prompt


# Internal utilities
from StreamingCommunity.Util.os import os_manager
from StreamingCommunity.Util.message import start_message
from StreamingCommunity.TelegramHelp.telegram_bot import TelegramSession, get_bot_instance


# Logic class
from .util.ScrapeSerie import ScrapeSerieAnime
from StreamingCommunity.Api.Template.config_loader import site_constant
from StreamingCommunity.Api.Template.Util import manage_selection, dynamic_format_number
from StreamingCommunity.Api.Template.Class.SearchType import MediaItem


# Player
from StreamingCommunity import MP4_downloader
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
    start_message()

    # Get episode information
    obj_episode = scrape_serie.selectEpisode(1, index_select)
    console.print(f"\n[bold yellow]Download:[/bold yellow] [red]{site_constant.SITE_NAME}[/red] → [cyan]{scrape_serie.series_name}[/cyan] ([cyan]E{obj_episode.number}[/cyan]) \n")

    if site_constant.TELEGRAM_BOT:
        bot = get_bot_instance()
        bot.send_message(f"Download in corso\nAnime: {scrape_serie.series_name}\nEpisodio: {obj_episode.number}", None)
        
        # Get script_id and update it
        script_id = TelegramSession.get_session()
        if script_id != "unknown":
            TelegramSession.updateScriptId(script_id, f"{scrape_serie.series_name} - E{obj_episode.number}")

    # Collect mp4 url
    video_source.get_embed(obj_episode.id)

    # Create output path
    mp4_name = f"{scrape_serie.series_name}_EP_{dynamic_format_number(str(obj_episode.number))}.mp4"

    if scrape_serie.is_series:
        mp4_path = os_manager.get_sanitize_path(os.path.join(site_constant.ANIME_FOLDER, scrape_serie.series_name))
    else:
        mp4_path = os_manager.get_sanitize_path(os.path.join(site_constant.MOVIE_FOLDER, scrape_serie.series_name))

    # Create output folder
    os_manager.create_path(mp4_path)

    # Start downloading
    path, kill_handler = MP4_downloader(
        url=str(video_source.src_mp4).strip(),
        path=os.path.join(mp4_path, mp4_name)
    )

    return path, kill_handler


def download_series(select_title: MediaItem, season_selection: str = None, episode_selection: str = None):
    """
    Function to download episodes of a TV series.

    Parameters:
        - select_title (MediaItem): The selected media item
        - season_selection (str, optional): Season selection input that bypasses manual input (usually '1' for anime)
        - episode_selection (str, optional): Episode selection input that bypasses manual input
    """
    start_message()

    if site_constant.TELEGRAM_BOT:
        bot = get_bot_instance()

    scrape_serie = ScrapeSerieAnime(site_constant.FULL_URL)
    video_source = VideoSourceAnime(site_constant.FULL_URL)

    # Set up video source (only configure scrape_serie now)
    scrape_serie.setup(None, select_title.id, select_title.slug)

    # Get episode information
    episoded_count = scrape_serie.get_count_episodes()
    console.print(f"[green]Episodes count:[/green] [red]{episoded_count}[/red]")
    
    # Telegram bot integration
    if episode_selection is None:
        if site_constant.TELEGRAM_BOT:
            console.print("\n[cyan]Insert media [red]index [yellow]or [red]* [cyan]to download all media [yellow]or [red]1-2 [cyan]or [red]3-* [cyan]for a range of media")
            bot.send_message(f"Episodi trovati: {episoded_count}", None)

            last_command = bot.ask(
                "select_title",
                "Menu di selezione degli episodi: \n\n" 
                "- Inserisci il numero dell'episodio (ad esempio, 1)\n" 
                "- Inserisci * per scaricare tutti gli episodi\n" 
                "- Inserisci un intervallo di episodi (ad esempio, 1-2) per scaricare da un episodio all'altro\n" 
                "- Inserisci (ad esempio, 3-*) per scaricare dall'episodio specificato fino alla fine della serie",
                None
            )
        else:
            # Prompt user to select an episode index
            last_command = msg.ask("\n[cyan]Insert media [red]index [yellow]or [red]* [cyan]to download all media [yellow]or [red]1-2 [cyan]or [red]3-* [cyan]for a range of media")
    else:
        last_command = episode_selection
        console.print(f"\n[cyan]Using provided episode selection: [yellow]{episode_selection}")

    # Manage user selection
    list_episode_select = manage_selection(last_command, episoded_count)

    # Download selected episodes
    if len(list_episode_select) == 1 and last_command != "*":
        path, _ = download_episode(list_episode_select[0]-1, scrape_serie, video_source)
        return path

    # Download all other episodes selected
    else:
        kill_handler = False
        for i_episode in list_episode_select:
            if kill_handler:
                break
            _, kill_handler = download_episode(i_episode-1, scrape_serie, video_source)

    if site_constant.TELEGRAM_BOT:
        bot.send_message("Finito di scaricare tutte le serie e episodi", None)

        # Get script_id
        script_id = TelegramSession.get_session()
        if script_id != "unknown":
            TelegramSession.deleteScriptId(script_id)