# 3.12.23

import os
from typing import Tuple


# External library
from rich.console import Console
from rich.prompt import Prompt


# Internal utilities
from StreamingCommunity.Util.message import start_message
from StreamingCommunity.Lib.Downloader import HLS_Downloader
from StreamingCommunity.TelegramHelp.telegram_bot import TelegramSession, get_bot_instance

# Logic class
from .util.ScrapeSerie import GetSerieInfo
from StreamingCommunity.Api.Template.Util import (
    manage_selection, 
    map_episode_title, 
    dynamic_format_number, 
    validate_selection, 
    validate_episode_selection, 
    display_episodes_list
)
from StreamingCommunity.Api.Template.config_loader import site_constant
from StreamingCommunity.Api.Template.Class.SearchType import MediaItem


# Player
from StreamingCommunity.Api.Player.vixcloud import VideoSource


# Variable
msg = Prompt()
console = Console()


def download_video(index_season_selected: int, index_episode_selected: int, scrape_serie: GetSerieInfo, video_source: VideoSource) -> Tuple[str,bool]:
    """
    Downloads a specific episode from the specified season.

    Parameters:
        - index_season_selected (int): Season number
        - index_episode_selected (int): Episode index
        - scrape_serie (GetSerieInfo): Scraper object with series information
        - video_source (VideoSource): Video source handler

    Returns:
        - str: Path to downloaded file
        - bool: Whether download was stopped
    """
    start_message()

    # Get episode information
    obj_episode = scrape_serie.selectEpisode(index_season_selected, index_episode_selected-1)
    console.print(f"[bold yellow]Download:[/bold yellow] [red]{site_constant.SITE_NAME}[/red] → [bold magenta]{obj_episode.name}[/bold magenta] ([cyan]S{index_season_selected}E{index_episode_selected}[/cyan]) \n")

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
    video_source.get_iframe(obj_episode.id)
    video_source.get_content()
    master_playlist = video_source.get_playlist()

    # Download the episode
    r_proc = HLS_Downloader(
        m3u8_url=master_playlist,
        output_path=os.path.join(mp4_path, mp4_name)
    ).start()

    if r_proc['error'] is not None:
        try: os.remove(r_proc['path'])
        except: pass

    return r_proc['path'], r_proc['stopped']


def download_episode(index_season_selected: int, scrape_serie: GetSerieInfo, video_source: VideoSource, download_all: bool = False, episode_selection: str = None) -> None:
    """
    Handle downloading episodes for a specific season.

    Parameters:
        - index_season_selected (int): Season number
        - scrape_serie (GetSerieInfo): Scraper object with series information
        - video_source (VideoSource): Video source object
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
        # Download all episodes in the season
        for i_episode in range(1, episodes_count + 1):
            path, stopped = download_video(index_season_selected, i_episode, scrape_serie, video_source)

            if stopped:
                break

        console.print(f"\n[red]End downloaded [yellow]season: [red]{index_season_selected}.")

    else:
        # Display episodes list and manage user selection
        if episode_selection is None:
            last_command = display_episodes_list(episodes)
        else:
            last_command = episode_selection
            console.print(f"\n[cyan]Using provided episode selection: [yellow]{episode_selection}")
        
        # Validate the selection
        list_episode_select = manage_selection(last_command, episodes_count)
        list_episode_select = validate_episode_selection(list_episode_select, episodes_count)

        # Download selected episodes if not stopped
        for i_episode in list_episode_select:
            path, stopped = download_video(index_season_selected, i_episode, scrape_serie, video_source)

            if stopped:
                break


def download_series(select_season: MediaItem, season_selection: str = None, episode_selection: str = None, proxy = None) -> None:
    """
    Handle downloading a complete series.

    Parameters:
        - select_season (MediaItem): Series metadata from search
        - season_selection (str, optional): Pre-defined season selection that bypasses manual input
        - episode_selection (str, optional): Pre-defined episode selection that bypasses manual input
    """
    start_message()

    # Init class
    video_source = VideoSource(f"{site_constant.FULL_URL}/it", True, select_season.id)
    scrape_serie = GetSerieInfo(f"{site_constant.FULL_URL}/it", select_season.id, select_season.slug, proxy)

    # Collect information about season
    scrape_serie.getNumberSeason()
    seasons_count = len(scrape_serie.seasons_manager)

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
        season = None
        for s in scrape_serie.seasons_manager.seasons:
            if s.number == i_season:
                season = s
                break
        season_number = season.number

        if len(list_season_select) > 1 or index_season_selected == "*":
            download_episode(season_number, scrape_serie, video_source, download_all=True)
            
        else:
            download_episode(season_number, scrape_serie, video_source, download_all=False, episode_selection=episode_selection)

    if site_constant.TELEGRAM_BOT:
        bot.send_message(f"Finito di scaricare tutte le serie e episodi", None)

        # Get script_id
        script_id = TelegramSession.get_session()
        if script_id != "unknown":
            TelegramSession.deleteScriptId(script_id)