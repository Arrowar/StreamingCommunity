# 19.06.24

from typing import Callable, Any, Optional


# External library
from rich.console import Console


# Internal utilities
from StreamingCommunity.services._base.episode_manager import manage_selection, validate_selection, validate_episode_selection, display_episodes_list, display_seasons_list


# Variable
console = Console()


def process_season_selection(scrape_serie: Any, seasons_count: int, season_selection: Optional[str], episode_selection: Optional[str], download_episode_callback: Callable) -> None:
    """
    Process season selection and trigger episode downloads.
    
    Parameters:
        - scrape_serie: Scraper object with series information
        - seasons_count (int): Total number of seasons
        - season_selection (str, optional): Pre-defined season selection
        - episode_selection (str, optional): Pre-defined episode selection
        - download_episode_callback (Callable): Function to call for downloading episodes
    """
    if seasons_count == 0:
        console.print("[red]No seasons found for this series")
        return

    # If season_selection is provided, use it instead of asking for input
    if season_selection is None:
        index_season_selected = display_seasons_list(scrape_serie.seasons_manager)
    else:
        index_season_selected = season_selection
        console.print(f"\n[cyan]Using provided season selection: [yellow]{season_selection}")
    
    # Validate the selection
    list_season_select = manage_selection(index_season_selected, seasons_count)
    list_season_select = validate_selection(list_season_select, seasons_count)
    
    # Loop through the selected seasons and download episodes
    for i_season in list_season_select:
        try:
            season = scrape_serie.seasons_manager.seasons[i_season - 1]
        except IndexError:
            console.print(f"[red]Season index {i_season} not found! Available seasons: {[s.number for s in scrape_serie.seasons_manager.seasons]}")
            continue
        
        season_number = season.number
        
        # Determine if we should download all episodes
        download_all = len(list_season_select) > 1 or index_season_selected == "*"
        
        # Call the download callback with appropriate parameters
        download_episode_callback(
            season_number=season_number,
            download_all=download_all,
            episode_selection=episode_selection if not download_all else None
        )


def process_episode_download(index_season_selected: int, scrape_serie: Any, download_video_callback: Callable, download_all: bool = False, episode_selection: Optional[str] = None) -> None:
    """
    Handle downloading episodes for a specific season.
    
    Parameters:
        - index_season_selected (int): Season number
        - scrape_serie: Scraper object with series information
        - download_video_callback (Callable): Function to call for downloading individual videos
        - download_all (bool): Whether to download all episodes
        - episode_selection (str, optional): Pre-defined episode selection
    """
    # Get episodes for the selected season
    episodes = scrape_serie.getEpisodeSeasons(index_season_selected)
    episodes_count = len(episodes)
    
    if episodes_count == 0:
        console.print(f"[red]No episodes found for season {index_season_selected}")
        return
    
    if download_all:
        # Download all episodes in the season
        for i_episode in range(1, episodes_count + 1):
            path, stopped = download_video_callback(index_season_selected, i_episode)
            
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
            path, stopped = download_video_callback(index_season_selected, i_episode)
            
            if stopped:
                break