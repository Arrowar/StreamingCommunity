# 09.06.24

import logging


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


def title_search(query: str) -> int:
    """
    Search for titles based on a search query.

    Parameters:
        - query (str): The query to search for.

    Returns:
        - int: The number of titles found.
    """
    media_search_manager.clear()
    table_show_manager.clear()

    search_url = f"{site_constant.FULL_URL}/search/?&q={query}&quick=1&type=videobox_video&nodes=11"
    console.print(f"[cyan]Search url: [yellow]{search_url}")

    try:
        response = httpx.get(
            search_url, 
            headers={'user-agent': get_userAgent()}, 
            timeout=max_timeout, 
            follow_redirects=True
        )
        response.raise_for_status()

    except Exception as e:
        console.print(f"[red]Site: {site_constant.SITE_NAME}, request search error: {e}")
        return 0

    # Create soup and find table
    soup = BeautifulSoup(response.text, "html.parser")
    table_content = soup.find('ol', class_="ipsStream")

    if table_content:
        for title_div in table_content.find_all('li', class_='ipsStreamItem'):
            try:

                title_type = title_div.find("p", class_="ipsType_reset").find_all("a")[-1].get_text(strip=True)
                name = title_div.find("span", class_="ipsContained").find("a").get_text(strip=True)
                link = title_div.find("span", class_="ipsContained").find("a").get("href")

                title_info = {
                    'name': name,
                    'url': link,
                    'type': title_type,
                    'image': title_div.find("div", class_="ipsColumn").find("img").get("src")
                }

                media_search_manager.add_media(title_info)
                    
            except Exception as e:
                print(f"Error parsing a film entry: {e}")

        return media_search_manager.get_length()
    
    else:
        logging.error("No table content found.")
        return -999