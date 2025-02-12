# 13.06.24

import os
from typing import Tuple


# Internal utilities
from StreamingCommunity.Util.console import console, msg
from StreamingCommunity.Util.message import start_message
from StreamingCommunity.Lib.Downloader import HLS_Downloader


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
from StreamingCommunity.Api.Player.supervideo import VideoSource



def download_video(index_season_selected: int, index_episode_selected: int, scape_info_serie: GetSerieInfo) -> Tuple[str,bool]:
    """
    Download a single episode video.

    Parameters:
        - tv_name (str): Name of the TV series.
        - index_season_selected (int): Index of the selected season.
        - index_episode_selected (int): Index of the selected episode.

    Return:
        - str: output path
        - bool: kill handler status
    """
    start_message()
    index_season_selected = dynamic_format_number(index_season_selected)

    # Get info about episode
    obj_episode = scape_info_serie.list_episodes[index_episode_selected - 1]
    console.print(f"[yellow]Download: [red]{index_season_selected}:{index_episode_selected} {obj_episode.get('name')}\n")

    # Define filename and path for the downloaded video
    mp4_name = f"{map_episode_title(scape_info_serie.tv_name, index_season_selected, index_episode_selected, obj_episode.get('name'))}.mp4"
    mp4_path = os.path.join(site_constant.SERIES_FOLDER, scape_info_serie.tv_name, f"S{index_season_selected}")

    # Setup video source
    video_source = VideoSource(obj_episode.get('url'))

    # Get m3u8 master playlist
    master_playlist = video_source.get_playlist()
    
    # Download the film using the m3u8 playlist, and output filename
    r_proc = HLS_Downloader(
        m3u8_url=master_playlist, 
        output_path=os.path.join(mp4_path, mp4_name)
    ).start()

            
    if "error" in r_proc.keys():
        try:
            os.remove(r_proc['path'])
        except:
            pass

    return r_proc['path'], r_proc['stopped']


def download_episode(scape_info_serie: GetSerieInfo, index_season_selected: int, download_all: bool = False) -> None:
    """
    Download all episodes of a season.

    Parameters:
        - tv_name (str): Name of the TV series.
        - index_season_selected (int): Index of the selected season.
        - download_all (bool): Download all seasons episodes
    """

    # Start message and collect information about episodes
    start_message()
    list_dict_episode = scape_info_serie.get_episode_number(index_season_selected)
    episodes_count = len(list_dict_episode)

    if download_all:

        # Download all episodes without asking
        for i_episode in range(1, episodes_count + 1):
            path, stopped = download_video(index_season_selected, i_episode, scape_info_serie)

            if stopped:
                break

        console.print(f"\n[red]End downloaded [yellow]season: [red]{index_season_selected}.")

    else:

        # Display episodes list and manage user selection
        last_command = display_episodes_list(scape_info_serie.list_episodes)
        list_episode_select = manage_selection(last_command, episodes_count)

        try:
            list_episode_select = validate_episode_selection(list_episode_select, episodes_count)
        except ValueError as e:
            console.print(f"[red]{str(e)}")
            return

        # Download selected episodes
        for i_episode in list_episode_select:
            path, stopped = download_video(index_season_selected, i_episode, scape_info_serie)

            if stopped:
                break


def download_series(dict_serie: MediaItem) -> None:
    """
    Download all episodes of a TV series.

    Parameters:
        - dict_serie (MediaItem): obj with url name type and score
    """

    # Start message and set up video source
    start_message()

    # Init class
    scape_info_serie = GetSerieInfo(dict_serie)

    # Collect information about seasons
    seasons_count = scape_info_serie.get_seasons_number()

    # Prompt user for season selection and download episodes
    console.print(f"\n[green]Seasons found: [red]{seasons_count}")
    index_season_selected = msg.ask(
        "\n[cyan]Insert season number [yellow](e.g., 1), [red]* [cyan]to download all seasons, "
        "[yellow](e.g., 1-2) [cyan]for a range of seasons, or [yellow](e.g., 3-*) [cyan]to download from a specific season to the end"
    )
    
    # Manage and validate the selection
    list_season_select = manage_selection(index_season_selected, seasons_count)

    try:
        list_season_select = validate_selection(list_season_select, seasons_count)
    except ValueError as e:
        console.print(f"[red]{str(e)}")
        return

    # Loop through the selected seasons and download episodes
    for i_season in list_season_select:
        if len(list_season_select) > 1 or index_season_selected == "*":

            # Download all episodes if multiple seasons are selected or if '*' is used
            download_episode(scape_info_serie, i_season, download_all=True)
        else:

            # Otherwise, let the user select specific episodes for the single season
            download_episode(scape_info_serie, i_season, download_all=False)