# 25.07.25

from datetime import datetime


# External libraries
import httpx
from rich.console import Console


# Internal utilities
from StreamingCommunity.Util.config_json import config_manager
from StreamingCommunity.Util.table import TVShowManager
from StreamingCommunity.Api.Template.config_loader import site_constant
from StreamingCommunity.Api.Template.Class.SearchType import MediaManager


# Logic class
from .util.get_license import get_bearer_token


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
    class_mediaset_api = get_bearer_token()
    search_url = 'https://mediasetplay.api-graph.mediaset.it/'
    console.print(f"[cyan]Search url: [yellow]{search_url}")

    params = {
        'extensions': f'{{"persistedQuery":{{"version":1,"sha256Hash":"{class_mediaset_api.getHash256()}"}}}}',
        'variables': f'{{"first":10,"property":"search","query":"{query}","uxReference":"filteredSearch"}}',
    }
    try:
        response = httpx.get(
            search_url, 
            headers=class_mediaset_api.generate_request_headers(), 
            params=params,
            timeout=max_timeout, 
            follow_redirects=True
        )

        response.raise_for_status()
    except Exception as e:
        console.print(f"[red]Site: {site_constant.SITE_NAME}, request search error: {e}")
        return 0

    # Parse response
    resp_json = response.json()
    items = resp_json.get("data", {}).get("getSearchPage", {}).get("areaContainersConnection", {}).get("areaContainers", [])[0].get("areas", [])[0].get("sections", [])[0].get("collections", [])[0].get("itemsConnection", {}).get("items", [])

    # Process items
    for item in items:
        item_type = "tv" if item.get("__typename") == "SeriesItem" else "film"

        # Bastava un campo data ma no ...
        date = item.get("year")
        if not date:
            updated = item.get("updated")
            if updated:
                try:
                    date = datetime.fromisoformat(updated.replace("Z", "+00:00")).year
                except Exception:
                    try:
                        timestamp_ms = int(updated)
                        date = datetime.fromtimestamp(timestamp_ms / 1000).year
                    except Exception:
                        date = ""

        date = item.get('year', '')
        if not date and item.get('updated'):
            try:
                
                timestamp_ms = int(item.get('updated', 0))
                date = datetime.fromtimestamp(timestamp_ms / 1000).year
            except (ValueError, TypeError):
                date = ''

        media_search_manager.add_media({
            "url": item.get("cardLink", "").get("value", ""),
            "id": item.get("guid", ""),
            "name": item.get("cardTitle", "No Title"),
            "type": item_type,
            "image": None,
            "date": date,
        })

        return media_search_manager.get_length()