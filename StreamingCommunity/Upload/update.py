# 01.03.2023

import os
import sys
import time
import asyncio
import importlib.metadata


# External library
import httpx
from rich.console import Console


# Internal utilities
from .version import __version__ as source_code_version, __author__, __title__
from StreamingCommunity.Util.config_json import config_manager
from StreamingCommunity.Util.headers import get_userAgent



# Variable
if getattr(sys, 'frozen', False):  # Modalità PyInstaller
    base_path = os.path.join(sys._MEIPASS, "StreamingCommunity")
else:
    base_path = os.path.dirname(__file__)
console = Console()

async def fetch_github_data(client, url):
    """Helper function to fetch data from GitHub API"""
    response = await client.get(
        url=url,
        headers={'user-agent': get_userAgent()},
        timeout=config_manager.get_int("REQUESTS", "timeout"),
        follow_redirects=True
    )
    return response.json()

async def async_github_requests():
    """Make concurrent GitHub API requests"""
    async with httpx.AsyncClient() as client:
        tasks = [
            fetch_github_data(client, f"https://api.github.com/repos/{__author__}/{__title__}"),
            fetch_github_data(client, f"https://api.github.com/repos/{__author__}/{__title__}/releases"),
            fetch_github_data(client, f"https://api.github.com/repos/{__author__}/{__title__}/commits")
        ]
        return await asyncio.gather(*tasks)

def update():
    """
    Check for updates on GitHub and display relevant information.
    """
    try:
        # Run async requests concurrently
        response_reposity, response_releases, response_commits = asyncio.run(async_github_requests())
        
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

    # Get the current version (installed version)
    try:
        current_version = importlib.metadata.version(__title__)
    except importlib.metadata.PackageNotFoundError:
        current_version = source_code_version

    # Get commit details
    latest_commit = response_commits[0] if response_commits else None
    if latest_commit:
        latest_commit_message = latest_commit.get('commit', {}).get('message', 'No commit message')
    else:
        latest_commit_message = 'No commit history available'
    
    if str(current_version).replace('v', '') != str(last_version).replace('v', ''):
        console.print(f"\n[cyan]New version available: [yellow]{last_version}")

    console.print(f"\n[red]{__title__} has been downloaded [yellow]{total_download_count} [red]times, but only [yellow]{percentual_stars}% [red]of users have starred it.\n\
        [green]Current installed version: [yellow]{current_version} [green]last commit: [white]''[yellow]{latest_commit_message.splitlines()[0]}[white]''\n\
        [cyan]Help the repository grow today by leaving a [yellow]star [cyan]and [yellow]sharing [cyan]it with others online!")
    
    time.sleep(1)