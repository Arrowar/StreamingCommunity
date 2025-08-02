# 16.03.25

import re
import logging


# External libraries
import httpx
from bs4 import BeautifulSoup


# Internal utilities
from StreamingCommunity.Util.headers import get_headers, get_userAgent
from StreamingCommunity.Util.config_json import config_manager
from StreamingCommunity.Api.Player.Helper.Vixcloud.util import SeasonManager


# Logic class
from .get_license import get_bearer_token, get_playback_url


# Variable
max_timeout = config_manager.get_int("REQUESTS", "timeout")


class GetSerieInfo:
    def __init__(self, url):
        """
        Initialize the GetSerieInfo class for scraping TV series information.
        
        Args:
            - url (str): The URL of the streaming site.
        """
        self.headers = get_headers()
        self.url = url
        self.seasons_manager = SeasonManager()
        self.subBrandId = None
        self.id_media = None
        self.current_url = None

    def _extract_subbrand_id(self, soup):
        """
        Extract subBrandId from the chapter link in the main page.
        Searches all <a> tags to see if one has 'capitoli_' in the href.
        """
        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]

            if "capitoli_" in href:
                match = re.search(r"sb(\d+)", href)
                if match:
                    return match.group(1)
                match = re.search(r",sb(\d+)", href)
                if match:
                    return match.group(1)
                
        return None

    def _find_video_href_and_id(self, soup):
        """
        Search for the first <a> with href containing '/video/' and return (current_url, id_media).
        Always builds the absolute URL.
        """
        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]
            if "/video/" in href:
                if href.startswith("http"):
                    current_url = href
                else:
                    current_url = "https://mediasetinfinity.mediaset.it" + href

                bearer = get_bearer_token()
                playback_json = get_playback_url(bearer, current_url.split('_')[-1])
                id_media = str(playback_json['url']).split("/s/")[1].split("/")[0]

                return current_url, id_media
        return None, None

    def _parse_entries(self, entries, single_season=False):
        """
        Populate seasons and episodes from the JSON entries.
        If single_season=True, creates only one season and adds all episodes there.
        """
        if not entries:
            self.series_name = ""
            return

        self.series_name = entries[0].get("mediasetprogram$auditelBrandName", "")

        if single_season:
            logging.info("Single season mode enabled.")
            season_num = 1
            season_name = "Stagione 1"
            current_season = self.seasons_manager.add_season({
                'number': season_num,
                'name': season_name
            })

            for idx, entry in enumerate(entries, 1):
                title = entry.get("title", "")
                video_page_url = entry.get("mediasetprogram$videoPageUrl", "")

                if video_page_url.startswith("//"):
                    episode_url = "https:" + video_page_url
                else:
                    episode_url = video_page_url
                    
                if current_season:
                    current_season.episodes.add({
                        'number': idx,
                        'name': title,
                        'url': episode_url,
                        'duration': int(entry.get("mediasetprogram$duration", 0) / 60)
                    })
        else:
            seasons_dict = {}

            logging.info("Multi season mode")
            for entry in entries:

                # Use JSON fields directly instead of regex
                season_num = entry.get("tvSeasonNumber")
                ep_num = entry.get("tvSeasonEpisodeNumber")

                # Extract numbers from title if season_num or ep_num are None
                if season_num is None or ep_num is None:
                    title = entry.get("title", "")

                    # Find all numbers in the title
                    numbers = [int(n) for n in re.findall(r"\d+", title)]
                    if len(numbers) == 2:
                        season_num, ep_num = numbers

                    elif len(numbers) == 1:
                        # If only one, use it as episode
                        ep_num = numbers[0]

                if season_num is None or ep_num is None:
                    continue

                season_name = entry.get("mediasetprogram$brandTitle") or f"Stagione {season_num}"

                if season_num not in seasons_dict:
                    current_season = self.seasons_manager.add_season({
                        'number': season_num,
                        'name': season_name
                    })
                    seasons_dict[season_num] = current_season

                else:
                    current_season = seasons_dict[season_num]

                video_page_url = entry.get("mediasetprogram$videoPageUrl", "")
                if video_page_url.startswith("//"):
                    episode_url = "https:" + video_page_url
                else:
                    episode_url = video_page_url

                if current_season:
                    current_season.episodes.add({
                        'number': ep_num,
                        'name': entry.get("title", ""),
                        'url': episode_url,
                        'duration': entry.get("mediasetprogram$duration")
                    })

    def collect_season(self) -> None:
        """
        Retrieve all episodes for all seasons using the Mediaset Infinity API.
        """
        response = httpx.get(self.url, headers=self.headers, follow_redirects=True, timeout=max_timeout)
        soup = BeautifulSoup(response.text, "html.parser")

        # Find current_url and id_media from the first <a> with /video/
        self.current_url, found_id_media = self._find_video_href_and_id(soup)
        if found_id_media:
            self.id_media = found_id_media

        self.subBrandId = self._extract_subbrand_id(soup)
        single_season = False
        if self.subBrandId is None:
            episodi_link = None
            for h2_tag in soup.find_all("h2", class_=True):
                a_tag = h2_tag.find("a", href=True)
                if a_tag and "/episodi_" in a_tag["href"]:
                    episodi_link = a_tag["href"]
                    break

            if episodi_link:
                match = re.search(r"sb(\d+)", episodi_link)
                if match:
                    self.subBrandId = match.group(1)

                single_season = True

            else:
                puntate_link = None
                for a_tag in soup.find_all("a", href=True):
                    href = a_tag["href"]
                    if "puntateintere" in href and "sb" in href:
                        puntate_link = href
                        break

                if puntate_link:
                    match = re.search(r"sb(\d+)", puntate_link)
                    if match:
                        self.subBrandId = match.group(1)

                    single_season = True
                else:
                    print("No /episodi_ or puntateintere link found.")

        # Step 2: JSON request
        params = {
            'byCustomValue': "{subBrandId}{" + str(self.subBrandId) + "}",
            'sort': ':publishInfo_lastPublished|asc,tvSeasonEpisodeNumber|asc',
            'range': '0-100',
        }

        json_url = f'https://feed.entertainment.tv.theplatform.eu/f/{self.id_media}/mediaset-prod-all-programs-v2'
        json_resp = httpx.get(json_url, headers={'user-agent': get_userAgent()}, params=params, timeout=max_timeout, follow_redirects=True)

        data = json_resp.json()
        entries = data.get("entries", [])

        # Use the unified parsing function
        self._parse_entries(entries, single_season=single_season)

    # ------------- FOR GUI -------------
    def getNumberSeason(self) -> int:
        """
        Get the total number of seasons available for the series.
        """
        if not self.seasons_manager.seasons:
            self.collect_season()
            
        return len(self.seasons_manager.seasons)
    
    def getEpisodeSeasons(self, season_number: int) -> list:
        """
        Get all episodes for a specific season.
        """
        if not self.seasons_manager.seasons:
            self.collect_season()
            
        # Get season directly by its number
        season = self.seasons_manager.get_season_by_number(season_number)
        return season.episodes.episodes if season else []
        
    def selectEpisode(self, season_number: int, episode_index: int) -> dict:
        """
        Get information for a specific episode in a specific season.
        """
        episodes = self.getEpisodeSeasons(season_number)
        if not episodes or episode_index < 0 or episode_index >= len(episodes):
            logging.error(f"Episode index {episode_index} is out of range for season {season_number}")
            return None
            
        return episodes[episode_index]