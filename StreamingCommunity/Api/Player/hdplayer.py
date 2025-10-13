# 29.04.25

import re

# External library
from bs4 import BeautifulSoup


# Internal utilities
from StreamingCommunity.Util.headers import get_userAgent
from StreamingCommunity.Util.http_client import create_client



class VideoSource:
    def __init__(self):
        self.client = create_client(headers={'user-agent': get_userAgent()})

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
            base_domain = re.match(r'https?://(?:www\.)?([^/]+)', page_url).group(0)
            self.client.headers.update({'referer': base_domain})
            
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
                
            sources_pattern = r'file:"([^"]+)"'
            match = re.search(sources_pattern, response_hdplayer.text)

            if match:
                return match.group(1)

            return None

        except Exception as e:
            print(f"Error in HDPlayer: {str(e)}")
            return None

        finally:
            self.client.close()
