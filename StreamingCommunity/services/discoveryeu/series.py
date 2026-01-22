# 22.12.25

import os
from typing import Tuple


# External library
from rich.console import Console
from rich.prompt import Prompt


# Internal utilities
from StreamingCommunity.utils import os_manager, config_manager, start_message
from StreamingCommunity.services._base import site_constants, MediaItem
from StreamingCommunity.services._base.episode_manager import map_episode_title
from StreamingCommunity.services._base.season_manager import process_season_selection, process_episode_download
from StreamingCommunity.core.downloader import DASH_Downloader, HLS_Downloader


# Logic
from .util.ScrapeSerie import GetSerieInfo
from .util.get_license import get_playback_info, generate_license_headers, DiscoveryEUAPI


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
    index_season_selected = scrape_serie.getRealNumberSeason(index_season_selected)
    console.print(f"\n[yellow]Download: [red]{site_constants.SITE_NAME} → [cyan]{scrape_serie.series_name} [white]\\ [magenta]{obj_episode.name} ([cyan]S{index_season_selected}E{index_episode_selected}) \n")

    # Define output path
    mp4_name = f"{map_episode_title(scrape_serie.series_name, index_season_selected, index_episode_selected, obj_episode.name)}.{extension_output}"
    mp4_path = os_manager.get_sanitize_path(
        os.path.join(site_constants.SERIES_FOLDER, scrape_serie.series_name, f"S{index_season_selected}")
    )
    
    # Get playback information using video_id
    playback_info = get_playback_info(obj_episode.video_id)

    if (str(playback_info['type']).strip().lower() == 'dash' and playback_info['license_url'] is None) or (str(playback_info['type']).strip().lower() != 'hls' and str(playback_info['type']).strip().lower() != 'dash' ):
        console.print(f"[red]Unsupported streaming type. Playback info: {playback_info}")
        return None, False
    
    # Check the type of stream
    if  playback_info['type'] == 'dash':
        license_headers = generate_license_headers(playback_info['license_token'])
    
        # Download the episode
        return DASH_Downloader(
            mpd_url=playback_info['mpd_url'],
            license_url=playback_info['license_url'],
            license_headers=license_headers,
            output_path=os.path.join(mp4_path, mp4_name),
        ).start()
        
    elif playback_info['type'] == 'hls':
        
        api = DiscoveryEUAPI()
        headers = api.get_request_headers()
        
        # Download the episode
        return HLS_Downloader(
            m3u8_url=playback_info['mpd_url'],
            headers=headers,
            output_path=os.path.join(mp4_path, mp4_name),
        ).start()


def download_series(select_season: MediaItem, season_selection: str = None, episode_selection: str = None) -> None:
    """
    Handle downloading a complete series
    
    Parameters:
        select_season (MediaItem): Series metadata from search
        season_selection (str, optional): Pre-defined season selection
        episode_selection (str, optional): Pre-defined episode selection
    """
    start_message()
    id_parts = select_season.id.split('|')
    scrape_serie = GetSerieInfo(id_parts[1], id_parts[0])
    seasons_count = scrape_serie.getNumberSeason()

    # Create callback function for downloading episodes
    def download_episode_callback(season_number: int, download_all: bool, episode_selection: str = None):
        """Callback to handle episode downloads for a specific season"""
        
        # Create callback for downloading individual videos
        def download_video_callback(season_idx: int, episode_idx: int):
            return download_video(season_idx, episode_idx, scrape_serie)
        
        # Use the process_episode_download function
        process_episode_download(
            index_season_selected=season_number,
            scrape_serie=scrape_serie,
            download_video_callback=download_video_callback,
            download_all=download_all,
            episode_selection=episode_selection
        )

    # Use the process_season_selection function
    process_season_selection(
        scrape_serie=scrape_serie,
        seasons_count=seasons_count,
        season_selection=season_selection,
        episode_selection=episode_selection,
        download_episode_callback=download_episode_callback
    )