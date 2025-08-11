# 25.07.25

import os

# External libraries
import httpx
from rich.console import Console


# Internal utilities
from StreamingCommunity.Util.config_json import config_manager
from StreamingCommunity.Util.os import get_wvd_path
from StreamingCommunity.Util.headers import get_headers
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

    # Check CDM file before usage
    cdm_device_path = get_wvd_path()
    if not cdm_device_path or not isinstance(cdm_device_path, (str, bytes, os.PathLike)) or not os.path.isfile(cdm_device_path):
        console.print(f"[bold red] CDM file not found or invalid path: {cdm_device_path}[/bold red]")
        return None

    search_url = 'https://api-ott-prod-fe.mediaset.net/PROD/play/reco/account/v2.0'
    console.print(f"[cyan]Search url: [yellow]{search_url}")

    params = {
        'uxReference': 'filteredSearch',
        'shortId': '',
        'query': query.strip(),
        'params': 'channel≈;variant≈',
        'contentId': '',
        'property': 'search',
        'tenant': 'play-prod-v2',
        'aresContext': '',
        'clientId': 'client_id',
        'page': '1',
        'hitsPerPage': '8',
    }

    headers = get_headers()
    headers['authorization'] = f'Bearer {get_bearer_token()}'

    try:
        response = httpx.get(
            search_url, 
            headers=headers, 
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
    blocks = resp_json.get('response', {}).get('blocks', [])
    items = []
    for block in blocks:
        if 'items' in block:
            items.extend(block['items'])
        elif 'results' in block and 'items' in block['results']:
            items.extend(block['results']['items'])
    
    # Process items
    for item in items:

        # Get the media type
        program_type = item.get('programType', '') or item.get('programtype', '')
        program_type = program_type.lower()
        
        if program_type in ('movie', 'film'):
            media_type = 'film'
            page_url = item.get('mediasetprogram$videoPageUrl', '')
        elif program_type in ('series', 'serie'):
            media_type = 'tv'
            page_url = item.get('mediasetprogram$pageUrl', '')
        else:
            continue

        if page_url and page_url.startswith('//'):
            page_url = f"https:{page_url}"

        media_search_manager.add_media({
            'id': item.get('guid', '') or item.get('_id', ''),
            'name': item.get('title', ''),
            'type': media_type,
            'url': page_url,
            'image': None,
        })

    return media_search_manager.get_length()