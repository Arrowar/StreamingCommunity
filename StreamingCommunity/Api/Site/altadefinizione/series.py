# 16.03.25

import os
from typing import Tuple


# External library
from rich.console import Console
from rich.prompt import Prompt


# Internal utilities
from StreamingCommunity.Util.message import start_message
from StreamingCommunity.TelegramHelp.telegram_bot import get_bot_instance, TelegramSession


# Logic class
from .util.ScrapeSerie import GetSerieInfo
from StreamingCommunity.Api.Template.Util import (
    manage_selection, 
    map_episode_title,
    validate_selection, 
    validate_episode_selection, 
    display_episodes_list
)
from StreamingCommunity.Api.Template.config_loader import site_constant
from StreamingCommunity.Api.Template.Class.SearchType import MediaItem


# Player
from StreamingCommunity import HLS_Downloader
from StreamingCommunity.Api.Player.supervideo import VideoSource


# Variable
msg = Prompt()
console = Console()


def download_video(index_season_selected: int, index_episode_selected: int, scrape_serie: GetSerieInfo) -> Tuple[str,bool]:
    """
    Downloads a specific episode from a specified season.

    Parameters:
        - index_season_selected (int): Season number
        - index_episode_selected (int): Episode index
        - scrape_serie (GetSerieInfo): Scraper object with series information

    Returns:
        - str: Path to downloaded file
        - bool: Whether download was stopped
    """
    start_message()

    # Get episode information
    obj_episode = scrape_serie.selectEpisode(index_season_selected, index_episode_selected-1)
    console.print(f"\n[bold yellow]Download:[/bold yellow] [red]{site_constant.SITE_NAME}[/red] → [cyan]{scrape_serie.series_name}[/cyan] \\ [bold magenta]{obj_episode.name}[/bold magenta] ([cyan]S{index_season_selected}E{index_episode_selected}[/cyan]) \n")

    # Telegram integration
    if site_constant.TELEGRAM_BOT:
        bot = get_bot_instance()

        # Invio a telegram
        bot.send_message(
            f"Download in corso\nSerie: {scrape_serie.series_name}\nStagione: {index_season_selected}\nEpisodio: {index_episode_selected}\nTitolo: {obj_episode.name}",
            None
        )

    # Get script_id and update it
    script_id = TelegramSession.get_session()
    if script_id != "unknown":
        TelegramSession.updateScriptId(script_id, f"{scrape_serie.series_name} - S{index_season_selected} - E{index_episode_selected} - {obj_episode.name}")

    # Define filename and path for the downloaded video
    mp4_name = f"{map_episode_title(scrape_serie.series_name, index_season_selected, index_episode_selected, obj_episode.name)}.mp4"
    mp4_path = os.path.join(site_constant.SERIES_FOLDER, scrape_serie.series_name, f"S{index_season_selected}")

    # Retrieve scws and if available master playlist
    video_source = VideoSource(obj_episode.url)
    video_source.make_request(obj_episode.url)
    master_playlist = video_source.get_playlist()

    # Download the episode
    hls_process = HLS_Downloader(
        m3u8_url=master_playlist,
        output_path=os.path.join(mp4_path, mp4_name)
    ).start()

    if hls_process['error'] is not None:
        try: 
            os.remove(hls_process['path'])
        except Exception: 
            pass

    return hls_process['path'], hls_process['stopped']
    

def download_episode(index_season_selected: int, scrape_serie: GetSerieInfo, download_all: bool = False, episode_selection: str = None) -> None:
    """
    Handle downloading episodes for a specific season.

    Parameters:
        - index_season_selected (int): Season number
        - scrape_serie (GetSerieInfo): Scraper object with series information
        - download_all (bool): Whether to download all episodes
        - episode_selection (str, optional): Pre-defined episode selection that bypasses manual input
    """
    # Get episodes for the selected season
    episodes = scrape_serie.getEpisodeSeasons(index_season_selected)
    episodes_count = len(episodes)

    if episodes_count == 0:
        console.print(f"[red]No episodes found for season {index_season_selected}")
        return

    if download_all:
        for i_episode in range(1, episodes_count + 1):
            path, stopped = download_video(index_season_selected, i_episode, scrape_serie)

            if stopped:
                break

        console.print(f"\n[red]End downloaded [yellow]season: [red]{index_season_selected}.")

    else:
        if episode_selection is not None:
            last_command = episode_selection
            console.print(f"\n[cyan]Using provided episode selection: [yellow]{episode_selection}")

        else:
            last_command = display_episodes_list(episodes)
        
        # Prompt user for episode selection
        list_episode_select = manage_selection(last_command, episodes_count)
        list_episode_select = validate_episode_selection(list_episode_select, episodes_count)

        # Download selected episodes if not stopped
        for i_episode in list_episode_select:
            path, stopped = download_video(index_season_selected, i_episode, scrape_serie)

            if stopped:
                break

def download_series(select_season: MediaItem, season_selection: str = None, episode_selection: str = None) -> None:
    """
    Handle downloading a complete series.

    Parameters:
        - select_season (MediaItem): Series metadata from search
        - season_selection (str, optional): Pre-defined season selection that bypasses manual input
        - episode_selection (str, optional): Pre-defined episode selection that bypasses manual input
    """
    scrape_serie = GetSerieInfo(select_season.url)

    # Get total number of seasons 
    seasons_count = scrape_serie.getNumberSeason()
    
    if site_constant.TELEGRAM_BOT:
        bot = get_bot_instance()

    # Prompt user for season selection and download episodes
    console.print(f"\n[green]Seasons found: [red]{seasons_count}")

    # If season_selection is provided, use it instead of asking for input
    if season_selection is None:
        if site_constant.TELEGRAM_BOT:
            console.print("\n[cyan]Insert season number [yellow](e.g., 1), [red]* [cyan]to download all seasons, "
              "[yellow](e.g., 1-2) [cyan]for a range of seasons, or [yellow](e.g., 3-*) [cyan]to download from a specific season to the end")

            bot.send_message(f"Stagioni trovate: {seasons_count}", None)

            index_season_selected = bot.ask(
                "select_title_episode",
                "Menu di selezione delle stagioni\n\n"
                "- Inserisci il numero della stagione (ad esempio, 1)\n"
                "- Inserisci * per scaricare tutte le stagioni\n"
                "- Inserisci un intervallo di stagioni (ad esempio, 1-2) per scaricare da una stagione all'altra\n"
                "- Inserisci (ad esempio, 3-*) per scaricare dalla stagione specificata fino alla fine della serie",
                None
            )

        else:
            index_season_selected = msg.ask(
                "\n[cyan]Insert season number [yellow](e.g., 1), [red]* [cyan]to download all seasons, "
                "[yellow](e.g., 1-2) [cyan]for a range of seasons, or [yellow](e.g., 3-*) [cyan]to download from a specific season to the end"
            )
    else:
        index_season_selected = season_selection
        console.print(f"\n[cyan]Using provided season selection: [yellow]{season_selection}")

    # Validate the selection
    list_season_select = manage_selection(index_season_selected, seasons_count)
    list_season_select = validate_selection(list_season_select, seasons_count)
    
    # Loop through the selected seasons and download episodes
    for i_season in list_season_select:
        if len(list_season_select) > 1 or index_season_selected == "*":
            # Download all episodes if multiple seasons are selected or if '*' is used
            download_episode(i_season, scrape_serie, download_all=True)
        else:
            # Otherwise, let the user select specific episodes for the single season
            download_episode(i_season, scrape_serie, download_all=False, episode_selection=episode_selection)

    if site_constant.TELEGRAM_BOT:
        bot.send_message("Finito di scaricare tutte le serie e episodi", None)

        # Get script_id
        script_id = TelegramSession.get_session()
        if script_id != "unknown":
            TelegramSession.deleteScriptId(script_id)