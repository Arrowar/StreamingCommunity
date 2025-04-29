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


class VideoSource:
    def __init__(self, url: str):
        self.url = url
        self.headers = {
            'accept': 'application/json, text/javascript, */*; q=0.01',
            'accept-language': 'it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7',
            'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'origin': 'https://stayonline.pro',
            'user-agent': get_userAgent(),
            'x-requested-with': 'XMLHttpRequest',
        }

    def get_redirect_url(self):
        try:
            response = httpx.get(self.url, headers=self.headers, follow_redirects=True, timeout=MAX_TIMEOUT)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            
            for link in soup.find_all('a'):
                if link.get('href') is not None and 'stayonline' in link.get('href'):
                    self.redirect_url = link.get('href')
                    logging.info(f"Redirect URL: {self.redirect_url}")
                    return self.redirect_url
            
            raise Exception("Stayonline URL not found")
            
        except Exception as e:
            logging.error(f"Error getting redirect URL: {e}")
            raise

    def get_link_id(self):
        try:
            response = httpx.get(self.redirect_url, headers=self.headers, follow_redirects=True, timeout=MAX_TIMEOUT)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            
            for script in soup.find_all('script'):
                match = re.search(r'var\s+linkId\s*=\s*"([^"]+)"', script.text)
                if match:
                    return match.group(1)
            
            raise Exception("LinkId not found")
            
        except Exception as e:
            logging.error(f"Error getting link ID: {e}")
            raise

    def get_final_url(self, link_id):
        try:
            self.headers['referer'] = f'https://stayonline.pro/l/{link_id}/'
            data = {
                'id': link_id,
                'ref': '',
            }
            
            response = httpx.post('https://stayonline.pro/ajax/linkView.php', 
                                headers=self.headers, 
                                data=data,
                                timeout=MAX_TIMEOUT)
            response.raise_for_status()
            return response.json()['data']['value']
            
        except Exception as e:
            logging.error(f"Error getting final URL: {e}")
            raise

    def get_playlist(self):
        """
        Executes the entire flow to obtain the final video URL.
        """
        self.get_redirect_url()
        link_id = self.get_link_id()

        final_url = self.get_final_url(link_id)
        final_url = "https://mixdrop.club/f/1np7evr7ckerql4/"
        print("Final URL: ", final_url)

        response = httpx.get(final_url, timeout=MAX_TIMEOUT)
        soup = BeautifulSoup(response.text, "html.parser")
        
        script_text = None
        for script in soup.find_all('script'):
            if "eval" in str(script.text):
                script_text = str(script.text)
                break
        print("Found script: ", script_text)
        
        delivery_url = None
        beautified = jsbeautifier.beautify(script_text)
        for line in beautified.splitlines():
            if 'MDCore.wurl' in line:
                url = line.split('= ')[1].strip('"').strip(';')
                delivery_url = f"https:{url}"

        print("Found delivery URL: ", delivery_url)
        return delivery_url