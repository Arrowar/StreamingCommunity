# 22.12.25

import os
from typing import Tuple


# External library
from rich.console import Console
from rich.prompt import Prompt


# Internal utilities
from StreamingCommunity.Util import os_manager, config_manager, start_message
from StreamingCommunity.Api.Template import site_constants, MediaItem
from StreamingCommunity.Api.Template.episode_manager import (
    manage_selection,
    map_episode_title,
    validate_selection,
    validate_episode_selection,
    display_episodes_list,
    display_seasons_list
)
from StreamingCommunity.Lib.DASH.downloader import DASH_Downloader
from StreamingCommunity.Lib.HLS import HLS_Downloader



# Logic
from .util.ScrapeSerie import GetSerieInfo
from .util.get_license import get_playback_info, generate_license_headers,DiscoveryEUAPI


# Variables
msg = Prompt()
console = Console()
extension_output = config_manager.config.get("M3U8_CONVERSION", "extension")


def download_video(index_season_selected: int, index_episode_selected: int, scrape_serie: GetSerieInfo) -> Tuple[str, bool]:
    """
    Download a specific episode
    
    Parameters:
        index_season_selected (int): Season number
        index_episode_selected (int): Episode index
        scrape_serie (GetSerieInfo): Series scraper instance
        
    Returns:
        Tuple[str, bool]: (output_path, stopped_status)
    """
    start_message()
    
    # Get episode information
    obj_episode = scrape_serie.selectEpisode(index_season_selected, index_episode_selected - 1)
    
    # Get the real season number. Due to some seasons not having free episodes there's a mismatch between seasons and their index number.
    index_season_selected = scrape_serie.getRealNumberSeason(index_season_selected)

    console.print(f"\n[yellow]Download: [red]{site_constants.SITE_NAME} → [cyan]{scrape_serie.series_name} \\ [magenta]{obj_episode.name} ([cyan]S{index_season_selected}E{index_episode_selected}) \n")

    # Define output path
    mp4_name = f"{map_episode_title(scrape_serie.series_name, index_season_selected, index_episode_selected, obj_episode.name)}.{extension_output}"
    mp4_path = os_manager.get_sanitize_path(
        os.path.join(site_constants.SERIES_FOLDER, scrape_serie.series_name, f"S{index_season_selected}")
    )
    
    # Get playback information using video_id
    playback_info = get_playback_info(obj_episode.video_id)

    if (str(playback_info['type']).strip().lower() == 'dash' and playback_info['license_url'] is None) or (str(playback_info['type']).strip().lower() != 'hls' and str(playback_info['type']).strip().lower() != 'dash' ):
        console.print(f"[red]Unsupported streaming type. Playbackk info: {playback_info}")
        return None, False
    
    # Check the type of stream
    status = None
    if  playback_info['type'] == 'dash':
        license_headers = generate_license_headers(playback_info['license_token'])
    
        # Download the episode
        dash_process = DASH_Downloader(
            license_url=playback_info['license_url'],
            mpd_url=playback_info['mpd_url'],
            output_path=os.path.join(mp4_path, mp4_name),
        )
    
        dash_process.parse_manifest(custom_headers=license_headers)
    
        if dash_process.download_and_decrypt(custom_headers=license_headers):
            dash_process.finalize_output()
    
        # Get final status
        status = dash_process.get_status()
        
    elif playback_info['type'] == 'hls':
        
        api = DiscoveryEUAPI()
        headers = api.get_request_headers()
        
        # Download the episode
        status =  HLS_Downloader(
            m3u8_url=playback_info['mpd_url'], #mpd_url is just a typo: it is a hls
            headers=headers,
            output_path=os.path.join(mp4_path, mp4_name),
        ).start()

    if status['error'] is not None and status['path']:
        try:
            os.remove(status['path'])
        except Exception:
            pass
    
    return status['path'], status['stopped']


def download_episode(index_season_selected: int, scrape_serie: GetSerieInfo, download_all: bool = False, episode_selection: str = None) -> None:
    """
    Handle downloading episodes for a specific season
    
    Parameters:
        index_season_selected (int): Season number
        scrape_serie (GetSerieInfo): Series scraper instance
        download_all (bool): Whether to download all episodes
        episode_selection (str, optional): Pre-defined episode selection
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
    else:
        if episode_selection is not None:
            last_command = episode_selection
            console.print(f"\n[cyan]Using provided episode selection: [yellow]{episode_selection}")
        else:
            last_command = display_episodes_list(episodes)
        
        # Prompt user for episode selection
        list_episode_select = manage_selection(last_command, episodes_count)
        list_episode_select = validate_episode_selection(list_episode_select, episodes_count)
        
        # Download selected episodes
        for i_episode in list_episode_select:
            path, stopped = download_video(index_season_selected, i_episode, scrape_serie)
            if stopped:
                break


def download_series(select_season: MediaItem, season_selection: str = None, episode_selection: str = None) -> None:
    """
    Handle downloading a complete series
    
    Parameters:
        select_season (MediaItem): Series metadata from search
        season_selection (str, optional): Pre-defined season selection
        episode_selection (str, optional): Pre-defined episode selection
    """
    id_parts = select_season.id.split('|')
    
    # Initialize series scraper
    scrape_serie = GetSerieInfo(id_parts[1], id_parts[0])
    seasons_count = scrape_serie.getNumberSeason()
    
    if seasons_count == 0:
        console.print("[red]No seasons found for this series")
        return
    
    # Handle season selection
    if season_selection is None:
        index_season_selected = display_seasons_list(scrape_serie.seasons_manager)
    else:
        index_season_selected = season_selection
        console.print(f"\n[cyan]Using provided season selection: [yellow]{season_selection}")
    
    # Validate the selection
    list_season_select = manage_selection(index_season_selected, seasons_count)
    list_season_select = validate_selection(list_season_select, seasons_count)
    
    # Loop through selected seasons and download episodes
    for i_season in list_season_select:
        if len(list_season_select) > 1 or index_season_selected == "*":
            download_episode(i_season, scrape_serie, download_all=True)
        else:
            download_episode(i_season, scrape_serie, download_all=False, episode_selection=episode_selection)
