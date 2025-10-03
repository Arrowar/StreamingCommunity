# 13.06.24

import os
from typing import Tuple


# External library
from rich.console import Console
from rich.prompt import Prompt


# Internal utilities
from StreamingCommunity.Util.message import start_message


# Logic class
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
from .util.ScrapeSerie import GetSerieInfo
from StreamingCommunity import HLS_Downloader
from StreamingCommunity.Api.Player.supervideo import VideoSource


# Variable
msg = Prompt()
console = Console()


def download_video(index_season_selected: int, index_episode_selected: int, scape_info_serie: GetSerieInfo) -> Tuple[str,bool]:
    """
    Downloads a specific episode from a specified season.

    Parameters:
        - index_season_selected (int): Season number
        - index_episode_selected (int): Episode index
        - scape_info_serie (GetSerieInfo): Scraper object with series information

    Returns:
        - str: Path to downloaded file
        - bool: Whether download was stopped
    """
    start_message()

    # Get episode information
    obj_episode = scape_info_serie.selectEpisode(index_season_selected, index_episode_selected-1)
    index_season_selected = dynamic_format_number(str(index_season_selected))
    console.print(f"\n[bold yellow]Download:[/bold yellow] [red]{site_constant.SITE_NAME}[/red] → [cyan]{scape_info_serie.tv_name}[/cyan] \\ [bold magenta]{obj_episode.get('name')}[/bold magenta] ([cyan]S{index_season_selected}E{index_episode_selected}[/cyan]) \n")

    # Define filename and path for the downloaded video
    mp4_name = f"{map_episode_title(scape_info_serie.tv_name, index_season_selected, index_episode_selected, obj_episode.get('name'))}.mp4"
    mp4_path = os.path.join(site_constant.SERIES_FOLDER, scape_info_serie.tv_name, f"S{index_season_selected}")

    # Setup video source
    video_source = VideoSource(obj_episode.get('url'))

    # Get m3u8 master playlist
    master_playlist = video_source.get_playlist()
    
    # Download the film using the m3u8 playlist, and output filename
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


def download_episode(scape_info_serie: GetSerieInfo, index_season_selected: int, download_all: bool = False, episode_selection: str = None) -> None:
    """
    Handle downloading episodes for a specific season.

    Parameters:
        - scape_info_serie (GetSerieInfo): Scraper object with series information
        - index_season_selected (int): Season number
        - download_all (bool): Whether to download all episodes
        - episode_selection (str, optional): Pre-defined episode selection that bypasses manual input
    """
    # Get episodes for the selected season
    episodes = scape_info_serie.get_episode_number(index_season_selected)
    episodes_count = len(episodes)

    if episodes_count == 0:
        console.print(f"[red]No episodes found for season {index_season_selected}")
        return

    if download_all:
        
        # Download all episodes in the season
        for i_episode in range(1, episodes_count + 1):
            path, stopped = download_video(index_season_selected, i_episode, scape_info_serie)

            if stopped:
                break

        console.print(f"\n[red]End downloaded [yellow]season: [red]{index_season_selected}.")

    else:

        # Display episodes list and manage user selection
        if episode_selection is None:
            last_command = display_episodes_list(scape_info_serie.list_episodes)
        else:
            last_command = episode_selection
            console.print(f"\n[cyan]Using provided episode selection: [yellow]{episode_selection}")
        
        # Validate the selection
        list_episode_select = manage_selection(last_command, episodes_count)
        list_episode_select = validate_episode_selection(list_episode_select, episodes_count)

        # Download selected episodes
        for i_episode in list_episode_select:
            path, stopped = download_video(index_season_selected, i_episode, scape_info_serie)

            if stopped:
                break


def download_series(dict_serie: MediaItem, season_selection: str = None, episode_selection: str = None) -> None:
    """
    Handle downloading a complete series.

    Parameters:
        - dict_serie (MediaItem): Series metadata from search
        - season_selection (str, optional): Pre-defined season selection that bypasses manual input
        - episode_selection (str, optional): Pre-defined episode selection that bypasses manual input
    """
    start_message()

    # Create class
    scrape_serie = GetSerieInfo(dict_serie)

    # Get season count
    seasons_count = scrape_serie.get_seasons_number()
    
    # Prompt user for season selection and download episodes
    console.print(f"\n[green]Seasons found: [red]{seasons_count}")

    # If season_selection is provided, use it instead of asking for input
    if season_selection is None:
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
            download_episode(scrape_serie, i_season, download_all=True)
        else:

            # Otherwise, let the user select specific episodes for the single season
            download_episode(scrape_serie, i_season, download_all=False, episode_selection=episode_selection)