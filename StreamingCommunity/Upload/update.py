# 01.03.2023

import os
import sys
import time


# External library
import httpx
from rich.console import Console


# Internal utilities
from .version import __version__, __author__, __title__
from StreamingCommunity.Util.config_json import config_manager
from StreamingCommunity.Util.headers import get_userAgent



# Variable
if getattr(sys, 'frozen', False):  # Modalità PyInstaller
    base_path = os.path.join(sys._MEIPASS, "StreamingCommunity")
else:
    base_path = os.path.dirname(__file__)
console = Console()


def update():
    """
    Check for updates on GitHub and display relevant information.
    """
    try:
        response_reposity = httpx.get(
            url=f"https://api.github.com/repos/{__author__}/{__title__}", 
            headers={'user-agent': get_userAgent()}, 
            timeout=config_manager.get_int("REQUESTS", "timeout"), 
            follow_redirects=True
        ).json()

        response_releases = httpx.get(
            url=f"https://api.github.com/repos/{__author__}/{__title__}/releases",
            headers={'user-agent': get_userAgent()}, 
            timeout=config_manager.get_int("REQUESTS", "timeout"), 
            follow_redirects=True
        ).json()
        
    except Exception as e:
        console.print(f"[red]Error accessing GitHub API: {e}")
        return

    # Get stargazers count from the repository
    stargazers_count = response_reposity.get('stargazers_count', 0)

    # Calculate total download count from all releases
    total_download_count = sum(asset['download_count'] for release in response_releases for asset in release.get('assets', []))

    # Get latest version name
    if response_releases:
        last_version = response_releases[0].get('name', 'Unknown')
    else:
        last_version = 'Unknown'

    # Calculate percentual of stars based on download count
    if total_download_count > 0 and stargazers_count > 0:
        percentual_stars = round(stargazers_count / total_download_count * 100, 2)
    else:
        percentual_stars = 0

    # Check installed version
    if str(__version__).replace('v', '') != str(last_version).replace('v', '') :
        console.print(f"\n[red]New version available: [yellow]{last_version}")

    console.print(f"\n[red]{__title__} has been downloaded [yellow]{total_download_count} [red]times, but only [yellow]{percentual_stars}% [red]of users have starred it.\n\
        [cyan]Help the repository grow today by leaving a [yellow]star [cyan]and [yellow]sharing [cyan]it with others online!")
    
    time.sleep(3)
