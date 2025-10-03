# 16.03.25

import sys


# External libraries
from curl_cffi import requests
from rich.console import Console


# Internal utilities
from StreamingCommunity.Util.config_json import config_manager
from StreamingCommunity.Util.headers import get_headers
from StreamingCommunity.Util.table import TVShowManager


# Logic class
from StreamingCommunity.Api.Template.config_loader import site_constant
from StreamingCommunity.Api.Template.Class.SearchType import MediaManager
from .util.get_license import get_auth_token, generate_device_id


# Variable
console = Console()
media_search_manager = MediaManager()
table_show_manager = TVShowManager()
max_timeout = config_manager.get_int("REQUESTS", "timeout")


def title_search(query: str) -> int:
    """
    Search for titles based on a search query.
      
    Parameters:
        - query (str): The query to search for.

    Returns:
        int: The number of titles found.
    """
    media_search_manager.clear()
    table_show_manager.clear()

    # Check if x_cr_tab_id or etp_rt is present
    if config_manager.get_dict("SITE_LOGIN", "crunchyroll")['x_cr_tab_id'] is None or config_manager.get_dict("SITE_LOGIN", "crunchyroll")['x_cr_tab_id'] == "" or config_manager.get_dict("SITE_LOGIN", "crunchyroll")['etp_rt'] is None or config_manager.get_dict("SITE_LOGIN", "crunchyroll")['etp_rt'] == "":
        console.print("[bold red] x_cr_tab_id or etp_rt is missing or empty.[/bold red]")
        sys.exit(0)

    # Build new Crunchyroll API search URL
    api_url = "https://www.crunchyroll.com/content/v2/discover/search"

    params = {
        "q": query,
        "n": 20,
        "type": "series,movie_listing",
        "ratings": "true",
        "preferred_audio_language": "it-IT",
        "locale": "it-IT"
    }

    headers = get_headers()
    headers['authorization'] = f"Bearer {get_auth_token(generate_device_id()).access_token}"

    console.print(f"[cyan]Search url: [yellow]{api_url}")

    try:
        response = requests.get(
            api_url,
            params=params,
            headers=headers,
            timeout=max_timeout,
            impersonate="chrome110"
        )
        response.raise_for_status()

    except Exception as e:
        console.print(f"[red]Site: {site_constant.SITE_NAME}, request search error: {e}")
        return 0

    data = response.json()
    found = 0

    # Parse results
    for block in data.get("data", []):
        if block.get("type") not in ("series", "movie_listing", "top_results"):
            continue

        for item in block.get("items", []):
            tipo = None

            if item.get("type") == "movie_listing":
                tipo = "film"
            elif item.get("type") == "series":
                meta = item.get("series_metadata", {})

                if meta.get("episode_count") == 1 and meta.get("season_count", 1) == 1 and meta.get("series_launch_year"):
                    tipo = "film" if "film" in item.get("description", "").lower() or "movie" in item.get("description", "").lower() else "tv"
                else:
                    tipo = "tv"

            else:
                continue

            url = ""
            if tipo == "tv":
                url = f"https://www.crunchyroll.com/series/{item.get('id')}"
            elif tipo == "film":
                url = f"https://www.crunchyroll.com/series/{item.get('id')}"
            else:
                continue

            title = item.get("title", "")

            media_search_manager.add_media({
                'url': url,
                'name': title,
                'type': tipo
            })
            found += 1

    return media_search_manager.get_length()