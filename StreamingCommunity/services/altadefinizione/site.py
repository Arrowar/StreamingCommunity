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

    # Collect data from new structure
    try:
        dle_content = soup.find("div", id="dle-content")
        movies = dle_content.find_all("div", class_="movie")
    except Exception as e:
        console.print(f"[red]Site: {site_constants.SITE_NAME}, parsing search results error: {e}")
        return 0

    for movie in movies:
        try:
            # Title and URL
            title_tag = movie.find("h2", class_="movie-title")
            if not title_tag:
                continue
                
            a_tag = title_tag.find("a")
            if not a_tag:
                continue
                
            title = a_tag.get_text(strip=True)
            url = a_tag.get("href")

            # Image
            img_tag = movie.find("img", class_="layer-image")
            image_url = None
            if img_tag:
                img_src = img_tag.get("src") or img_tag.get("data-src")
                if img_src:
                    if img_src.startswith("/"):
                        image_url = f"{site_constants.FULL_URL}{img_src}"
                    else:
                        image_url = img_src

            # Type - check if URL contains "serie-tv"
            tipo = "tv" if "/serie-tv/" in url else "film"

            media_dict = {
                'url': url,
                'name': title,
                'type': tipo,
                'image': image_url
            }
            media_search_manager.add_media(media_dict)
            
        except Exception as e:
            console.print(f"[yellow]Warning: Error parsing movie item: {e}")
            continue

    # Return the number of titles found
    return media_search_manager.get_length()