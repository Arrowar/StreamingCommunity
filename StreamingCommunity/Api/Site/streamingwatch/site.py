# 29.04.25

import re


# External libraries
import httpx
from bs4 import BeautifulSoup
from rich.console import Console


# Internal utilities
from StreamingCommunity.Util.config_json import config_manager
from StreamingCommunity.Util.headers import get_userAgent
from StreamingCommunity.Util.table import TVShowManager


# Logic class
from StreamingCommunity.Api.Template.config_loader import site_constant
from StreamingCommunity.Api.Template.Class.SearchType import MediaManager


# Variable
console = Console()
media_search_manager = MediaManager()
table_show_manager = TVShowManager()
max_timeout = config_manager.get_int("REQUESTS", "timeout")


def extract_nonce(proxy) -> str:
    """Extract nonce value from the page script"""
    response = httpx.get(
        site_constant.FULL_URL, 
        headers={'user-agent': get_userAgent()}, 
        timeout=max_timeout,
        proxy=proxy
    )
    
    soup = BeautifulSoup(response.content, 'html.parser')
    script = soup.find('script', id='live-search-js-extra')
    if script:
        match = re.search(r'"admin_ajax_nonce":"([^"]+)"', script.text)
        if match:
            return match.group(1)
    return ""


def title_search(query: str, proxy: str) -> int:
    """
    Search for titles based on a search query.
      
    Parameters:
        - query (str): The query to search for.

    Returns:
        int: The number of titles found.
    """
    media_search_manager.clear()
    table_show_manager.clear()

    search_url = f"{site_constant.FULL_URL}/wp-admin/admin-ajax.php"
    console.print(f"[cyan]Search url: [yellow]{search_url}")

    try:
        _wpnonce = extract_nonce(proxy)
        
        if not _wpnonce:
            console.print("[red]Error: Failed to extract nonce")
            return 0

        data = {
            'action': 'data_fetch',
            'keyword': query,
            '_wpnonce': _wpnonce
        }

        response = httpx.post(
            search_url,
            headers={
                'origin': site_constant.FULL_URL,
                'user-agent': get_userAgent()
            },
            data=data,
            timeout=max_timeout,
            proxy=proxy
        )
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

    except Exception as e:
        if "WinError" in str(e) or "Errno" in str(e): console.print("\n[bold yellow]Please make sure you have enabled and configured a valid proxy.[/bold yellow]")
        console.print(f"[red]Site: {site_constant.SITE_NAME}, request search error: {e}")
        return 0

    for item in soup.find_all('div', class_='searchelement'):
        try:

            title = item.find_all("a")[-1].get_text(strip=True) if item.find_all("a") else 'N/A'
            url = item.find('a').get('href', '')
            year = item.find('div', id='search-cat-year')
            year = year.get_text(strip=True) if year else 'N/A'

            if any(keyword in year.lower() for keyword in ['stagione', 'episodio', 'ep.', 'season', 'episode']):
                continue

            media_search_manager.add_media({
                'name': title,
                'type': 'tv' if '/serie/' in url else 'Film',
                'date': year,
                'image': item.find('img').get('src', ''),
                'url': url
            })

        except Exception as e:
            print(f"Error parsing a film entry: {e}")
          
    # Return the number of titles found
    return media_search_manager.get_length()