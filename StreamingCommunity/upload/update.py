# 01.03.2023

import os
import sys
import importlib.metadata


# External library
import httpx
from rich.console import Console


# Internal utilities
from .version import __version__ as source_code_version, __author__, __title__
from StreamingCommunity.utils import config_manager
from StreamingCommunity.utils.http_client import get_userAgent


# Variable
if getattr(sys, 'frozen', False):  # Modalità PyInstaller
    base_path = os.path.join(sys._MEIPASS, "StreamingCommunity")
else:
    base_path = os.path.dirname(__file__)
console = Console()


def fetch_github_releases():
    """Fetch releases data from GitHub API (sync)"""
    response = httpx.get(
        f"https://api.github.com/repos/{__author__}/{__title__}/releases",
        headers={'user-agent': get_userAgent()},
        timeout=config_manager.config.get_int("REQUESTS", "timeout"),
        follow_redirects=True
    )
    return response.json()


def get_execution_mode():
    """Get the execution mode of the application"""
    if getattr(sys, 'frozen', False):
        return "installer"

    try:
        package_location = importlib.metadata.files(__title__)
        if any("site-packages" in str(path) for path in package_location):
            return "pip"
    except importlib.metadata.PackageNotFoundError:
        pass

    return "python"


def update():
    """Check for updates on GitHub and display relevant information."""
    try:
        response_releases = fetch_github_releases()
    except Exception as e:
        console.print(f"[red]Error accessing GitHub API: {e}")
        return

    # Calculate total download count from all releases
    total_download_count = sum(
        asset['download_count']
        for release in response_releases
        for asset in release.get('assets', [])
    )

    # Get latest version name
    if response_releases:
        last_version = response_releases[0].get('name', 'Unknown')
    else:
        last_version = 'Unknown'

    # Get the current version (installed version)
    try:
        current_version = importlib.metadata.version(__title__)
    except importlib.metadata.PackageNotFoundError:
        current_version = source_code_version

    console.print(
        f"\n[red]{__title__} has been downloaded: [yellow]{total_download_count}"
        f"\n[yellow]{get_execution_mode()} - [green]Current installed version: [yellow]{current_version} "
        f"\n"
        f"  [cyan]Help the repository grow today by leaving a [yellow]star [cyan]and [yellow]sharing "
        f"[cyan]it with others online!\n"
        f"      [magenta]If you'd like to support development and keep the program updated, consider leaving a "
        f"[yellow]donation[magenta]. Thank you!"
    )

    if str(current_version).lower().replace("v.", "").replace("v", "") != str(last_version).lower().replace("v.", "").replace("v", ""):
        console.print(f"\n[cyan]New version available: [yellow]{last_version}")