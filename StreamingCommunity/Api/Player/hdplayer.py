# 29.04.25

import re


# External library
import httpx
from bs4 import BeautifulSoup


# Internal utilities
from StreamingCommunity.Util.headers import get_headers
from StreamingCommunity.Util.config_json import config_manager


# Variable
MAX_TIMEOUT = config_manager.get_int("REQUESTS", "timeout")


class VideoSource:
    def __init__(self, proxy=None):
        self.client = httpx.Client(headers=get_headers(), timeout=MAX_TIMEOUT, proxy=proxy)

    def extractLinkHdPlayer(self, response):
        """Extract iframe source from the page."""
        soup = BeautifulSoup(response.content, 'html.parser')
        iframes = soup.find_all("iframe")
        if iframes:
            return iframes[0].get('data-lazy-src')
        return None

    def get_m3u8_url(self, page_url):
        """
        Extract m3u8 URL from hdPlayer page.
        """
        try:
            # Get the page content
            response = self.client.get(page_url)
            
            # Extract HDPlayer iframe URL
            iframe_url = self.extractLinkHdPlayer(response)
            if not iframe_url:
                return None

            # Get HDPlayer page content
            response_hdplayer = self.client.get(iframe_url)
            if response_hdplayer.status_code != 200:
                return None

            soup = BeautifulSoup(response_hdplayer.text, 'html.parser')

            # Find m3u8 URL in scripts
            for script in soup.find_all("script"):
                match = re.search(r'sources:\s*\[\{\s*file:\s*"([^"]+)"', script.text)
                if match:
                    return match.group(1)

            return None

        except Exception as e:
            print(f"Error in HDPlayer: {str(e)}")
            return None

        finally:
            self.client.close()