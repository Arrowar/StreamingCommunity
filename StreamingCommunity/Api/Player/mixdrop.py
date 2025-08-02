# 05.07.24

import re
import logging


# External libraries
import httpx
import jsbeautifier
from bs4 import BeautifulSoup


# Internal utilities
from StreamingCommunity.Util.config_json import config_manager
from StreamingCommunity.Util.headers import get_userAgent


# Variable
MAX_TIMEOUT = config_manager.get_int("REQUESTS", "timeout")
REQUEST_VERIFY = config_manager.get_bool('REQUESTS', 'verify')

class VideoSource:
    STAYONLINE_BASE_URL = "https://stayonline.pro"
    MIXDROP_BASE_URL = "https://mixdrop.sb"

    def __init__(self, url: str):
        self.url = url
        self.redirect_url: str = None
        self._init_headers()

    def _init_headers(self) -> None:
        """Initialize the base headers used for requests."""
        self.headers = {
            'origin': self.STAYONLINE_BASE_URL,
            'user-agent': get_userAgent(),
        }

    def _get_mixdrop_headers(self) -> dict:
        """Get headers specifically for MixDrop requests."""
        return {
            'referer': 'https://mixdrop.club/',
            'user-agent': get_userAgent()
        }

    def get_redirect_url(self) -> str:
        """Extract the stayonline redirect URL from the initial page."""
        try:
            response = httpx.get(self.url, headers=self.headers, follow_redirects=True, timeout=MAX_TIMEOUT, verify=REQUEST_VERIFY)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            
            for link in soup.find_all('a'):
                href = link.get('href')
                if href and 'stayonline' in href:
                    self.redirect_url = href
                    logging.info(f"Redirect URL: {self.redirect_url}")
                    return self.redirect_url
            
            raise ValueError("Stayonline URL not found")
            
        except Exception as e:
            logging.error(f"Error getting redirect URL: {e}")
            raise

    def get_link_id(self) -> str:
        """Extract the link ID from the redirect page."""
        if not self.redirect_url:
            raise ValueError("Redirect URL not set. Call get_redirect_url first.")

        try:
            response = httpx.get(self.redirect_url, headers=self.headers, follow_redirects=True, timeout=MAX_TIMEOUT, verify=REQUEST_VERIFY)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            
            for script in soup.find_all('script'):
                match = re.search(r'var\s+linkId\s*=\s*"([^"]+)"', script.text)
                if match:
                    return match.group(1)
            
            raise ValueError("LinkId not found")
            
        except Exception as e:
            logging.error(f"Error getting link ID: {e}")
            raise

    def get_final_url(self, link_id: str) -> str:
        """Get the final URL using the link ID."""
        try:
            self.headers['referer'] = f'{self.STAYONLINE_BASE_URL}/l/{link_id}/'
            data = {'id': link_id, 'ref': ''}
            
            response = httpx.post(f'{self.STAYONLINE_BASE_URL}/ajax/linkView.php', headers=self.headers, data=data, timeout=MAX_TIMEOUT, verify=REQUEST_VERIFY)
            response.raise_for_status()
            return response.json()['data']['value']
            
        except Exception as e:
            logging.error(f"Error getting final URL: {e}")
            raise

    def _extract_video_id(self, final_url: str) -> str:
        """Extract video ID from the final URL."""
        parts = final_url.split('/')
        if len(parts) < 5:
            raise ValueError("Invalid final URL format")
        return parts[4]

    def _extract_delivery_url(self, script_text: str) -> str:
        """Extract delivery URL from beautified JavaScript."""
        beautified = jsbeautifier.beautify(script_text)
        for line in beautified.splitlines():
            if 'MDCore.wurl' in line:
                url = line.split('= ')[1].strip('"').strip(';')
                return f"https:{url}"
        raise ValueError("Delivery URL not found in script")

    def get_playlist(self) -> str:
        """
        Execute the entire flow to obtain the final video URL.
        Returns:
            str: The final video delivery URL
        """
        self.get_redirect_url()
        link_id = self.get_link_id()

        final_url = self.get_final_url(link_id)
        video_id = self._extract_video_id(final_url)

        response = httpx.get(
            f'{self.MIXDROP_BASE_URL}/e/{video_id}',
            headers=self._get_mixdrop_headers(),
            timeout=MAX_TIMEOUT,
            verify=REQUEST_VERIFY
        )
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        
        script_text = next(
            (script.text for script in soup.find_all('script') 
             if "eval" in str(script.text)),
            None
        )
        
        if not script_text:
            raise ValueError("Required script not found")

        return self._extract_delivery_url(script_text).replace('"', '')
