# 29.04.25

import re
import logging


# External libraries
import httpx
from bs4 import BeautifulSoup


# Internal utilities
from StreamingCommunity.Util.config_json import config_manager
from StreamingCommunity.Util.headers import get_userAgent


# Variable
MAX_TIMEOUT = config_manager.get_int("REQUESTS", "timeout")


class VideoSource:
    def __init__(self, url: str):
        """
        Sets up the video source with the provided URL.

        Parameters:
            - url (str): The URL of the video.
        """
        self.url = url
        self.iframe_url = None
        self.m3u8_url = None
        self.headers = {
            'accept': '*/*',
            'accept-language': 'en-US,en;q=0.9',
            'user-agent': get_userAgent(),
            'referer': url
        }

    def extract_iframe_sources(self, response) -> str:
        """Extract iframe source from the page."""
        try:
            soup = BeautifulSoup(response.content, 'html.parser')
            iframes = soup.select("iframe[data-lazy-src]")
            
            if not iframes:
                iframes = soup.select("iframe[src]")
                
            if iframes:
                iframe_url = iframes[0].get('data-lazy-src') or iframes[0].get('src')
                self.iframe_url = iframe_url
                logging.info(f"Iframe URL found: {iframe_url}")
                return iframe_url
            
            logging.error("No iframes found in the page")
            return None
            
        except Exception as e:
            logging.error(f"Error extracting iframe: {e}")
            raise

    def get_m3u8_url(self) -> str:
        """
        Extract m3u8 URL from hdPlayer page.
        """
        try:
            # First request to get iframe
            response = httpx.get(self.url, headers=self.headers, timeout=MAX_TIMEOUT)
            response.raise_for_status()
            
            iframe_url = self.extract_iframe_sources(response)
            if not iframe_url:
                raise ValueError("No iframe URL found")

            # Update headers for iframe request
            self.headers['referer'] = iframe_url
            
            # Request to iframe page
            logging.info(f"Making request to hdPlayer: {iframe_url}")
            response = httpx.get(iframe_url, headers=self.headers, timeout=MAX_TIMEOUT)
            response.raise_for_status()
            
            # Find m3u8 in the script
            soup = BeautifulSoup(response.text, 'html.parser')
            scripts = soup.find_all("script")
            
            for script in scripts:
                if not script.string:
                    continue
                    
                match = re.search(r'sources:\s*\[\{\s*file:\s*"([^"]+)"', script.string)
                if match:
                    self.m3u8_url = match.group(1)
                    logging.info(f"Found m3u8 URL: {self.m3u8_url}")
                    return self.m3u8_url

            logging.error("No m3u8 URL found in scripts")
            return None

        except Exception as e:
            logging.error(f"Error getting m3u8 URL: {e}")
            raise