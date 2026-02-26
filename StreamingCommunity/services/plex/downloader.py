# 12.02.26

import os
from typing import Tuple


# External library
from rich.console import Console
from rich.prompt import Prompt


# Internal utilities
from StreamingCommunity.utils import os_manager, config_manager, start_message
from StreamingCommunity.services._base import site_constants, Entries
from StreamingCommunity.services._base.tv_display_manager import map_episode_title, map_season_name
from StreamingCommunity.services._base.tv_download_manager import process_season_selection, process_episode_download


# Downloader
from StreamingCommunity.core.downloader import DASH_Downloader, HLS_Downloader


# Logic
from .scrapper import GetSerieInfo
from .client import get_client, get_playback_info


# Variable
console = Console()
msg = Prompt()
extension_output = config_manager.config.get("PROCESS", "extension")


def download_film(select_title: Entries) -> Tuple[str, bool]:
    """
    Downloads a film.
    """
    start_message()
    console.print(f"\n[yellow]Download: [red]{site_constants.SITE_NAME} → [cyan]{select_title.name} \n")

    # Define the filename and path
    mp4_name = f"{os_manager.get_sanitize_file(select_title.name, select_title.year)}.{extension_output}"
    mp4_path = os.path.join(site_constants.MOVIE_FOLDER, mp4_name.replace(f".{extension_output}", ""))

    api = get_client()
    movie_info = GetSerieInfo.get_movie_info(select_title.slug)
    if not movie_info:
        console.print("[red]Errore: Impossibile recuperare info film.")
        return "", False

    # Attach media info to select_title to avoid raw_data
    select_title.media = movie_info.get("Media", [])
    playback_info = get_playback_info(select_title)
    
    if "error" in playback_info:
        console.print(f"[red]Errore: {playback_info['error']}")
        return "", False

    if playback_info["protocol"] == "DASH":
        return DASH_Downloader(
            mpd_url=playback_info["manifest_url"],
            license_url=playback_info["license_url"],
            license_headers=api.get_headers(),
            output_path=os.path.join(mp4_path, mp4_name),
        ).start()
    else:
        return HLS_Downloader(
            m3u8_url=playback_info["manifest_url"],
            output_path=os.path.join(mp4_path, mp4_name),
        ).start()


def download_episode(obj_episode, index_season_selected, index_episode_selected, scrape_serie):
    """
    Downloads a specific episode.
    """
    start_message()
    console.print(f"\n[yellow]Download: [red]{site_constants.SITE_NAME} → [cyan]{scrape_serie.series_name} [white]\\ [magenta]{obj_episode.name} ([cyan]S{index_season_selected}E{index_episode_selected}) \n")

    mp4_name = f"{map_episode_title(scrape_serie.series_name, index_season_selected, index_episode_selected, obj_episode.name)}.{extension_output}"
    mp4_path = os_manager.get_sanitize_path(os.path.join(site_constants.SERIES_FOLDER, scrape_serie.series_name, map_season_name(index_season_selected)))

    api = get_client()
    playback_info = get_playback_info(obj_episode)
    if "error" in playback_info:
        console.print(f"[red]Errore: {playback_info['error']}")
        return "", False

    if playback_info["protocol"] == "DASH":
        return DASH_Downloader(
            mpd_url=playback_info["manifest_url"],
            license_url=playback_info["license_url"],
            license_headers=api.get_headers(),
            output_path=os.path.join(mp4_path, mp4_name),
        ).start()
    else:
        return HLS_Downloader(
            m3u8_url=playback_info["manifest_url"],
            output_path=os.path.join(mp4_path, mp4_name),
        ).start()

def download_series(dict_serie: Entries, season_selection: str = None, episode_selection: str = None, scrape_serie = None) -> None:
    """
    Handle downloading a complete series.
    """
    start_message()
    if scrape_serie is None:
        scrape_serie = GetSerieInfo(dict_serie.url)
    
    seasons_count = scrape_serie.getNumberSeason()

    def download_episode_callback(season_number: int, download_all: bool, episode_selection: str = None):
        def download_video_callback(obj_episode, season_idx, episode_idx):
            return download_episode(obj_episode, season_idx, episode_idx, scrape_serie)
        
        process_episode_download(
            index_season_selected=season_number,
            scrape_serie=scrape_serie,
            download_video_callback=download_video_callback,
            download_all=download_all,
            episode_selection=episode_selection
        )

    process_season_selection(
        scrape_serie=scrape_serie,
        seasons_count=seasons_count,
        season_selection=season_selection,
        episode_selection=episode_selection,
        download_episode_callback=download_episode_callback
    )