# 16.03.25

import os
import time
from urllib.parse import urlparse, parse_qs


# External library
from rich.console import Console
from rich.prompt import Prompt


# Internal utilities
from StreamingCommunity.utils import config_manager, os_manager, start_message
from StreamingCommunity.services._base import site_constants, MediaItem
from StreamingCommunity.services._base.tv_display_manager import map_episode_title
from StreamingCommunity.services._base.tv_download_manager import process_season_selection, process_episode_download


# Downloader
from StreamingCommunity.core.downloader import DASH_Downloader


# Logic
from .client import get_playback_session, CrunchyrollClient
from .scrapper import GetSerieInfo


# Variable
console = Console()
msg = Prompt()
extension_output = config_manager.config.get("M3U8_CONVERSION", "extension")


def download_film(select_title: MediaItem) -> str:
    """
    Downloads a film using the provided MediaItem information.
    """
    start_message()
    console.print(f"\n[yellow]Download: [red]{site_constants.SITE_NAME} → [cyan]{select_title.name} \n")

    # Initialize Crunchyroll client
    client = CrunchyrollClient()

    # Define filename and path
    mp4_name = f"{os_manager.get_sanitize_file(select_title.name, select_title.year)}.{extension_output}"
    mp4_path = os.path.join(site_constants.MOVIE_FOLDER, mp4_name.replace(f".{extension_output}", ""))

    # Extract media ID
    url_id = select_title.get('url').split('/')[-1]
    
    # Get playback session
    mpd_url, mpd_headers, mpd_list_sub, token, audio_locale = get_playback_session(client, url_id, None)
    
    # Parse playback token from URL
    parsed_url = urlparse(mpd_url)
    query_params = parse_qs(parsed_url.query)
    playback_guid = query_params.get('playbackGuid', [token])[0] if query_params.get('playbackGuid') else token

    # Creaate headers for license request
    license_headers = mpd_headers.copy()
    license_headers.update({
        "x-cr-content-id": url_id,
        "x-cr-video-token": playback_guid,
    })

    # Download the film
    out_path, need_stop = DASH_Downloader(
        mpd_url=mpd_url,
        mpd_headers=mpd_headers,
        license_url='https://www.crunchyroll.com/license/v1/license/widevine',
        license_headers=license_headers,
        mpd_sub_list=mpd_list_sub,
        output_path=os.path.join(mp4_path, mp4_name),
    ).start()

    # Small delay
    time.sleep(1)
    return out_path, need_stop


def download_episode(obj_episode, index_season_selected, index_episode_selected, scrape_serie, main_guid = None):
    """
    Downloads a specific episode from the specified season.
    """
    start_message()
    client = scrape_serie.client
    console.print(f"\n[yellow]Download: [red]{site_constants.SITE_NAME} → [cyan]{scrape_serie.series_name} [white]\\ [magenta]{obj_episode.name} ([cyan]S{index_season_selected}E{index_episode_selected}) \n")

    # Define filename and path for the downloaded video
    mp4_name = f"{map_episode_title(scrape_serie.series_name, index_season_selected, index_episode_selected, obj_episode.name)}.{extension_output}"
    mp4_path = os_manager.get_sanitize_path(os.path.join(site_constants.SERIES_FOLDER, scrape_serie.series_name, f"S{index_season_selected}"))

    # Get media ID and main_guid for complete subtitles
    url_id = obj_episode.url.split('/')[-1]
    main_guid = getattr(obj_episode, 'main_guid', None)
    
    # Get playback session
    mpd_url, mpd_headers, mpd_list_sub, token, audio_locale = get_playback_session(client, url_id, main_guid)
    
    # Parse playback token from URL
    parsed_url = urlparse(mpd_url)
    query_params = parse_qs(parsed_url.query)
    playback_guid = query_params.get('playbackGuid', [token])[0] if query_params.get('playbackGuid') else token

    # Create headers for license request
    license_headers = mpd_headers.copy()
    license_headers.update({
        "x-cr-content-id": url_id,
        "x-cr-video-token": playback_guid,
    })

    # Download the episode
    out_path, need_stop = DASH_Downloader(
        mpd_url=mpd_url,
        mpd_headers=mpd_headers,
        license_url='https://www.crunchyroll.com/license/v1/license/widevine',
        license_headers=license_headers,
        mpd_sub_list=mpd_list_sub,
        output_path=os.path.join(mp4_path, mp4_name)
    ).start()

    # Small delay between episodes to avoid rate limiting
    time.sleep(1)
    return out_path, need_stop

def download_series(select_season: MediaItem, season_selection: str = None, episode_selection: str = None) -> None:
    """
    Handle downloading a complete series.

    Parameters:
        - select_season (MediaItem): Series metadata from search
        - season_selection (str, optional): Pre-defined season selection
        - episode_selection (str, optional): Pre-defined episode selection
    """
    start_message()
    scrape_serie = GetSerieInfo(select_season.url.split("/")[-1])
    seasons_count = scrape_serie.getNumberSeason()

    # Create callback function for downloading episodes
    def download_episode_callback(season_number: int, download_all: bool, episode_selection: str = None):
        """Callback to handle episode downloads for a specific season"""
        
        # Create callback for downloading individual videos
        def download_video_callback(obj_episode, season_idx, episode_idx):
            return download_episode(obj_episode, season_idx, episode_idx, scrape_serie)
        
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