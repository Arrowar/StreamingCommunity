# 16.03.25

import os
from typing import Tuple
from urllib.parse import urlparse, parse_qs


# External library
from rich.console import Console
from rich.prompt import Prompt


# Internal utilities
from StreamingCommunity.Util.message import start_message
from StreamingCommunity.Util.os import os_manager, get_wvd_path


# Logic class
from .util.ScrapeSerie import GetSerieInfo, delete_stream_episode
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
from StreamingCommunity import DASH_Downloader
from .util.get_license import get_playback_session, get_auth_token, generate_device_id


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

    console.print(f"\n[bold yellow]Download:[/bold yellow] [red]{site_constant.SITE_NAME}[/red] → [cyan]{scrape_serie.series_name}[/cyan] \\ [bold magenta]{obj_episode.get('name')}[/bold magenta] ([cyan]S{index_season_selected}E{index_episode_selected}[/cyan]) \n")

    # Define filename and path for the downloaded video
    mp4_name = f"{map_episode_title(scrape_serie.series_name, index_season_selected, index_episode_selected, obj_episode.get('name'))}.mp4"
    mp4_path = os_manager.get_sanitize_path(os.path.join(site_constant.SERIES_FOLDER, scrape_serie.series_name, f"S{index_season_selected}"))

    # Generate mpd and license URLs
    url_id = obj_episode.get('url').split('/')[-1]
    device_id = generate_device_id()
    token_mpd = get_auth_token(device_id)
    
    mpd_url, mpd_headers, mpd_list_sub = get_playback_session(token_mpd, device_id, url_id)
    parsed_url = urlparse(mpd_url)
    query_params = parse_qs(parsed_url.query)

    # Download the episode
    dash_process = DASH_Downloader(
        cdm_device=get_wvd_path(),
        license_url='https://www.crunchyroll.com/license/v1/license/widevine',
        mpd_url=mpd_url,
        mpd_sub_list=mpd_list_sub,
        output_path=os.path.join(mp4_path, mp4_name),
    )
    dash_process.parse_manifest(custom_headers=mpd_headers)

    # Create headers for license request
    license_headers = mpd_headers.copy()
    license_headers.update({
        "x-cr-content-id": url_id,
        "x-cr-video-token": query_params['playbackGuid'][0],
    })

    if dash_process.download_and_decrypt(custom_headers=license_headers):
        dash_process.finalize_output()

    # Get final output path and status
    status = dash_process.get_status()

    if status['error'] is not None and status['path']:
        try: 
            os.remove(status['path'])
        except Exception: 
            pass

    # Delete episode stream
    delete_stream_episode(url_id, query_params['playbackGuid'][0], mpd_headers)

    return status['path'], status['stopped']

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
    scrape_serie = GetSerieInfo(select_season.url.split("/")[-1])

    # Get total number of seasons 
    seasons_count = scrape_serie.getNumberSeason()
    
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
            download_episode(i_season, scrape_serie, download_all=True)
            
        else:
            # Otherwise, let the user select specific episodes for the single season
            download_episode(i_season, scrape_serie, download_all=False, episode_selection=episode_selection)