# 21.05.24

import os
from typing import Tuple


# External library
from rich.console import Console
from rich.prompt import Prompt


# Internal utilities
from StreamingCommunity.utils import config_manager, start_message
from StreamingCommunity.utils.http_client import get_userAgent
from StreamingCommunity.services._base import site_constants, MediaItem
from StreamingCommunity.services._base.episode_manager import map_episode_title
from StreamingCommunity.services._base.season_manager import process_season_selection, process_episode_download
from StreamingCommunity.core.downloader import DASH_Downloader, HLS_Downloader
from StreamingCommunity.player.mediapolisvod import VideoSource


# Logic
from .util.ScrapeSerie import GetSerieInfo
from .util.get_license import generate_license_url
from .util.fix_mpd import fix_manifest_url



# Variable
msg = Prompt()
console = Console()
extension_output = config_manager.config.get("M3U8_CONVERSION", "extension")


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
    console.print(f"\n[yellow]Download: [red]{site_constants.SITE_NAME} → [cyan]{scrape_serie.series_name} [white]\\ [magenta]{obj_episode.name} ([cyan]S{index_season_selected}E{index_episode_selected}) \n")

    # Define filename and path
    mp4_name = f"{map_episode_title(scrape_serie.series_name, index_season_selected, index_episode_selected, obj_episode.name)}.{extension_output}"
    mp4_path = os.path.join(site_constants.SERIES_FOLDER, scrape_serie.series_name, f"S{index_season_selected}")

    # Get streaming URL
    master_playlist = VideoSource.extract_m3u8_url(obj_episode.url)

    # HLS
    if ".mpd" not in master_playlist:
        return HLS_Downloader(
            m3u8_url=fix_manifest_url(master_playlist),
            output_path=os.path.join(mp4_path, mp4_name)
        ).start()

    # MPD
    else:
        full_license_url = generate_license_url(obj_episode.mpd_id)
        license_headers = {
            'nv-authorizations': full_license_url.split("?")[1].split("=")[1],
            'user-agent': get_userAgent(),
        }

        return DASH_Downloader(
            mpd_url=master_playlist,
            license_url=full_license_url.split("?")[0],
            license_headers=license_headers,
            output_path=os.path.join(mp4_path, mp4_name),
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
    scrape_serie = GetSerieInfo(select_season.path_id)

    scrape_serie.collect_info_title()
    seasons_count = len(scrape_serie.seasons_manager)

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