# 16.03.25

# External libraries
from bs4 import BeautifulSoup
from rich.console import Console


# Internal utilities
from StreamingCommunity.utils.http_client import create_client, get_userAgent
from StreamingCommunity.services._base import site_constants, MediaManager
from StreamingCommunity.utils import TVShowManager


# Variable
console = Console()
media_search_manager = MediaManager()
table_show_manager = TVShowManager()


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

    search_url = f"{site_constants.FULL_URL}/?story={query}&do=search&subaction=search"
    console.print(f"[cyan]Search url: [yellow]{search_url}")

    try:
        response = create_client(headers={'user-agent': get_userAgent()}).get(search_url)
        response.raise_for_status()
    except Exception as e:
        console.print(f"[red]Site: {site_constants.SITE_NAME}, request search error: {e}")
        return 0

    # Create soup instance
    soup = BeautifulSoup(response.text, "html.parser")

    # Collect data from search results
    try:
        dle_content = soup.find("div", id="dle-content")
        if not dle_content:
            console.print("[yellow]Warning: dle-content div not found")
            return 0
            
        # Find all movie boxes
        boxes = dle_content.find_all("div", class_="box")
        
        if not boxes:
            console.print("[yellow]Warning: No movie boxes found")
            return 0
            
    except Exception as e:
        console.print(f"[red]Site: {site_constants.SITE_NAME}, parsing search results error: {e}")
        return 0

    for box in boxes:
        try:
            wrapper = box.find("div", class_="wrapperImage")
            if not wrapper:
                continue
            
            # Find the main link
            main_link = wrapper.find("a")
            if not main_link:
                continue
                
            url = main_link.get("href")
            if not url:
                continue
            
            # Get image
            img_tag = main_link.find("img")
            image_url = None
            if img_tag:
                img_src = img_tag.get("src") or img_tag.get("data-src")
                if img_src:
                    if img_src.startswith("/"):
                        image_url = f"{site_constants.FULL_URL}{img_src}"
                    else:
                        image_url = img_src
            
            # Get title from info section
            info_div = wrapper.find("div", class_="info")
            if not info_div:
                continue
                
            title_tag = info_div.find("h2", class_="titleFilm")
            if not title_tag:
                continue
                
            title_link = title_tag.find("a")
            if not title_link:
                continue
                
            title = title_link.get_text(strip=True)
            
            # Determine type based on URL
            tipo = "tv" if "/serie-tv/" in url else "film"

            media_dict = {
                'url': url,
                'name': title,
                'type': tipo,
                'image': image_url
            }
            media_search_manager.add_media(media_dict)
            
        except Exception as e:
            console.print(f"[yellow]Warning: Error parsing box item: {e}")
            continue

    # Return the number of titles found
    return media_search_manager.get_length()