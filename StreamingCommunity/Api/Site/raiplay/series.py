# 21.05.24

import os
from typing import Tuple


# External library
from rich.console import Console
from rich.prompt import Prompt


# Internal utilities
from StreamingCommunity.Util.headers import get_headers, get_userAgent
from StreamingCommunity.Util.os import get_wvd_path
from StreamingCommunity.Util.message import start_message



# Logic class
from .util.ScrapeSerie import GetSerieInfo
from .util.get_license import generate_license_url
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
from StreamingCommunity import HLS_Downloader, DASH_Downloader
from StreamingCommunity.Api.Player.mediapolisvod import VideoSource


# Variable
msg = Prompt()
console = Console()


def download_video(index_season_selected: int, index_episode_selected: int, scrape_serie: GetSerieInfo) -> Tuple[str,bool]:
    """
    Downloads a specific episode from the specified season.

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

    # Define filename and path
    mp4_name = f"{map_episode_title(scrape_serie.series_name, index_season_selected, index_episode_selected, obj_episode.name)}.mp4"
    mp4_path = os.path.join(site_constant.SERIES_FOLDER, scrape_serie.series_name, f"S{index_season_selected}")

    # Get streaming URL
    master_playlist = VideoSource.extract_m3u8_url(obj_episode.url)

    # HLS
    if ".mpd" not in master_playlist:
        r_proc = HLS_Downloader(
            m3u8_url=master_playlist,
            output_path=os.path.join(mp4_path, mp4_name)
        ).start()
    # Get streaming URL
    master_playlist = VideoSource.extract_m3u8_url(obj_episode.url)

    # HLS
    if ".mpd" not in master_playlist:
        r_proc = HLS_Downloader(
            m3u8_url=master_playlist,
            output_path=os.path.join(mp4_path, mp4_name)
        ).start()

    # MPD
    else:
        full_license_url = generate_license_url(obj_episode.mpd_id)
        license_headers = {
            'nv-authorizations': full_license_url.split("?")[1].split("=")[1],
            'user-agent': get_userAgent(),
        }

        dash_process = DASH_Downloader(
            cdm_device=get_wvd_path(),
            license_url=full_license_url.split("?")[0],
            mpd_url=master_playlist,
            output_path=os.path.join(mp4_path, mp4_name),
        )
        dash_process.parse_manifest(custom_headers=get_headers())
        
        if dash_process.download_and_decrypt(custom_headers=license_headers):
            dash_process.finalize_output()

        # Get final output path and status
        r_proc = dash_process.get_status()

    if r_proc['error'] is not None:
        try: 
            os.remove(r_proc['path'])
        except Exception: 
            pass

    return r_proc['path'], r_proc['stopped']


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
    start_message()

    # Extract program name from path_id
    program_name = None
    if select_season.path_id:
        parts = select_season.path_id.strip('/').split('/')
        if len(parts) >= 2:
            program_name = parts[-1].split('.')[0]

    # Init scraper
    scrape_serie = GetSerieInfo(program_name)

    # Get seasons info
    scrape_serie.collect_info_title()
    seasons_count = len(scrape_serie.seasons_manager)
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
    for season_number in list_season_select:
        if len(list_season_select) > 1 or index_season_selected == "*":
            download_episode(season_number, scrape_serie, download_all=True)
        else:
            download_episode(season_number, scrape_serie, download_all=False, episode_selection=episode_selection)
