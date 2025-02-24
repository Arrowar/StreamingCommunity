# 09.06.24

import sys
import logging


# External libraries
import httpx
from bs4 import BeautifulSoup


# Internal utilities
from StreamingCommunity.Util.console import console
from StreamingCommunity.Util._jsonConfig import config_manager
from StreamingCommunity.Util.headers import get_userAgent
from StreamingCommunity.Util.table import TVShowManager


# Logic class
from StreamingCommunity.Api.Template.config_loader import site_constant
from StreamingCommunity.Api.Template.Util import search_domain
from StreamingCommunity.Api.Template.Class.SearchType import MediaManager


# Variable
media_search_manager = MediaManager()
table_show_manager = TVShowManager()
max_timeout = config_manager.get_int("REQUESTS", "timeout")
disable_searchDomain = config_manager.get_bool("DEFAULT", "disable_searchDomain")


def title_search(word_to_search: str) -> int:
    """
    Search for titles based on a search query.

    Parameters:
        - title_search (str): The title to search for.

    Returns:
        - int: The number of titles found.
    """
    media_search_manager.clear()
    table_show_manager.clear()

    # Find new domain if prev dont work
    domain_to_use = site_constant.DOMAIN_NOW
    
    if not disable_searchDomain:
        domain_to_use, base_url = search_domain(site_constant.SITE_NAME, site_constant.FULL_URL)

    if domain_to_use is None or base_url is None:
        console.print("[bold red]❌ Error: Unable to determine valid domain or base URL.[/bold red]")
        console.print("[yellow]The service might be temporarily unavailable or the domain may have changed.[/yellow]")
        sys.exit(1)

    search_url = f"{site_constant.FULL_URL}/search/?&q={word_to_search}&quick=1&type=videobox_video&nodes=11"
    console.print(f"[cyan]Search url: [yellow]{search_url}")

    try:
        response = httpx.get(
            url=search_url,
            headers={'user-agent': get_userAgent()},
            timeout=max_timeout,
            verify=site_constant.VERIFY,
            follow_redirects=True
        )
        response.raise_for_status()

    except Exception as e:
        console.print(f"Site: {site_constant.SITE_NAME}, request search error: {e}")

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
                    'type': title_type
                }

                media_search_manager.add_media(title_info)
                    
            except Exception as e:
                print(f"Error parsing a film entry: {e}")

        return media_search_manager.get_length()
    
    else:
        logging.error("No table content found.")
        return -999