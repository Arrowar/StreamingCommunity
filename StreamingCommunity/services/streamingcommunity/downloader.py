# 3.12.23

import os
from typing import Tuple


# External library
from rich.console import Console
from rich.prompt import Prompt


# Internal utilities
from StreamingCommunity.utils import os_manager, config_manager, tmdb_client, start_message
from StreamingCommunity.services._base import site_constants, MediaItem
from StreamingCommunity.services._base.tv_display_manager import map_episode_title
from StreamingCommunity.services._base.tv_download_manager import process_season_selection, process_episode_download


# Downloader
from StreamingCommunity.core.downloader import HLS_Downloader


# Player
from StreamingCommunity.player.vixcloud import VideoSource


# Logic
from .scrapper import GetSerieInfo


# Variable
console = Console()
msg = Prompt()
extension_output = config_manager.config.get("M3U8_CONVERSION", "extension")
use_other_api = config_manager.login.get("TMDB", "api_key") != ""


def download_film(select_title: MediaItem) -> str:
    """
    Downloads a film using the provided MediaItem information.
    """
    start_message()
    console.print(f"\n[yellow]Download: [red]{site_constants.SITE_NAME} → [cyan]{select_title.name} \n")

    # Prepare TMDB data 
    tmdb_data = None
    if use_other_api:
        result = tmdb_client.get_type_and_id_by_slug_year(select_title.slug, select_title.year, "movie", select_title.provider_language)
        
        if result and result.get('id') and result.get('type') == 'movie':
            tmdb_data = {'id': result.get('id')}

    # Init class
    video_source = VideoSource(f"{site_constants.FULL_URL}/{select_title.provider_language}", False, select_title.id, tmdb_data=tmdb_data)

    # Retrieve iframe only if not using TMDB API
    if tmdb_data is None:
        video_source.get_iframe(select_title.id)
    
    video_source.get_content()
    master_playlist = video_source.get_playlist()

    if master_playlist is None:
        console.print(f"[red]Site: {site_constants.SITE_NAME}, error: No master playlist found")
        return None

    # Define the filename and path for the downloaded film
    mp4_name = f"{os_manager.get_sanitize_file(select_title.name, select_title.year)}.{extension_output}"
    mp4_path = os.path.join(site_constants.MOVIE_FOLDER, mp4_name.replace(f".{extension_output}", ""))

    # Download the film using the m3u8 playlist, and output filename
    return HLS_Downloader(
        m3u8_url=master_playlist,
        output_path=os.path.join(mp4_path, mp4_name)
    ).start()


def download_episode(index_season_selected: int, index_episode_selected: int, scrape_serie: GetSerieInfo, video_source: VideoSource) -> Tuple[str,bool]:
    """
    Downloads a specific episode from the specified season.
    """
    start_message()
    obj_episode = scrape_serie.selectEpisode(index_season_selected, index_episode_selected-1)
    console.print(f"\n[yellow]Download: [red]{site_constants.SITE_NAME} → [cyan]{scrape_serie.series_name} [white]\\ [magenta]{obj_episode.name} ([cyan]S{index_season_selected}E{index_episode_selected}) \n")

    # Define filename and path for the downloaded video
    mp4_name = f"{map_episode_title(scrape_serie.series_name, index_season_selected, index_episode_selected, obj_episode.name)}.{extension_output}"
    mp4_path = os.path.join(site_constants.SERIES_FOLDER, scrape_serie.series_name, f"S{index_season_selected}")

    if use_other_api:
        series_slug = scrape_serie.series_name.lower().replace(' ', '-').replace("'", '')
        result = tmdb_client.get_type_and_id_by_slug_year(str(series_slug), int(scrape_serie.year), 'tv', scrape_serie.provider_language)
        
        if result and result.get('id') and result.get('type') == 'tv':
            tmdb_id = result.get('id')
            video_source.tmdb_id = tmdb_id
            video_source.season_number = index_season_selected
            video_source.episode_number = index_episode_selected
            
        else:
            console.print("[yellow]TMDB ID not found or not a TV show, falling back to original method")
            video_source.get_iframe(obj_episode.id)

    else:
        # Retrieve iframe using original method
        video_source.get_iframe(obj_episode.id)

    video_source.get_content()
    master_playlist = video_source.get_playlist()

    # Download the episode
    return HLS_Downloader(
        m3u8_url=master_playlist,
        output_path=os.path.join(mp4_path, mp4_name)
    ).start()


def download_series(select_season: MediaItem, season_selection: str = None, episode_selection: str = None) -> None:
    """
    Handle downloading a complete series.

    Parameters:
        - select_season (MediaItem): Series metadata from search
        - season_selection (str, optional): Pre-defined season selection that bypasses manual input
        - episode_selection (str, optional): Pre-defined episode selection that bypasses manual input
    """
    start_message()
    video_source = VideoSource(f"{site_constants.FULL_URL}/{select_season.provider_language}", True, select_season.id)
    scrape_serie = GetSerieInfo(f"{site_constants.FULL_URL}/{select_season.provider_language}", select_season.id, select_season.slug, select_season.year, select_season.provider_language)

    scrape_serie.getNumberSeason()
    seasons_count = len(scrape_serie.seasons_manager)

    # Create callback function for downloading episodes
    def download_episode_callback(season_number: int, download_all: bool, episode_selection: str = None):
        """Callback to handle episode downloads for a specific season"""
        
        # Create callback for downloading individual videos
        def download_video_callback(season_idx: int, episode_idx: int):
            return download_episode(season_idx, episode_idx, scrape_serie, video_source)
        
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