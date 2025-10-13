# 28.07.25

from typing import Tuple, List, Dict


# Internal utilities
from StreamingCommunity.Util.config_json import config_manager
from StreamingCommunity.Util.http_client import create_client_curl
from StreamingCommunity.Util.headers import get_userAgent


# Variable
PUBLIC_TOKEN = "bm9haWhkZXZtXzZpeWcwYThsMHE6"


class CrunchyrollClient:
    def __init__(self) -> None:
        config = config_manager.get_dict("SITE_LOGIN", "crunchyroll")
        self.device_id = config.get('device_id')
        self.etp_rt = config.get('etp_rt')
        self.locale = "it-IT"
        
        self.access_token = None
        self.refresh_token = None
        self.account_id = None

    def _get_headers(self) -> Dict:
        headers = {
            'user-agent': get_userAgent(),
        }
        if self.access_token:
            headers['authorization'] = f'Bearer {self.access_token}'
        return headers
    
    def _get_cookies(self) -> Dict:
        cookies = {'device_id': self.device_id}
        if self.etp_rt:
            cookies['etp_rt'] = self.etp_rt
        return cookies

    def start(self) -> bool:
        """Autorizza il client"""
        headers = self._get_headers()
        headers['authorization'] = f'Basic {PUBLIC_TOKEN}'
        headers['content-type'] = 'application/x-www-form-urlencoded'
        
        data = {
            'device_id': self.device_id,
            'device_type': 'Chrome on Windows',
            'grant_type': 'etp_rt_cookie',
        }

        response = create_client_curl(headers=headers).post('https://www.crunchyroll.com/auth/v1/token', cookies=self._get_cookies(), data=data)
        
        if response.status_code == 400:
            print("Error 400: Please enter a correct 'etp_rt' value in config.json. You can find the value in the request headers.")
            return False
            
        result = response.json()
        self.access_token = result.get('access_token')
        self.refresh_token = result.get('refresh_token')
        self.account_id = result.get('account_id')
        
        return True

    def get_streams(self, media_id: str) -> Dict:
        """Ottieni gli stream disponibili"""
        response = create_client_curl(headers=self._get_headers()).get(f'https://www.crunchyroll.com/playback/v3/{media_id}/web/chrome/play', cookies=self._get_cookies(), params={'locale': self.locale})

        if response.status_code == 403:
            raise Exception("Playback is Rejected: The current subscription does not have access to this content")
        
        if response.status_code == 420:
            raise Exception("TOO_MANY_ACTIVE_STREAMS. Wait a few minutes and try again.")
        
        response.raise_for_status()
        
        data = response.json()
        
        if data.get('error') == 'Playback is Rejected':
            raise Exception("Playback is Rejected: Premium required")
        
        return data

    def delete_active_stream(self, media_id: str, token: str) -> bool:
        """Elimina uno stream attivo"""
        response = create_client_curl(headers=self._get_headers()).delete(f'https://www.crunchyroll.com/playback/v1/token/{media_id}/{token}', cookies=self._get_cookies())
        response.raise_for_status()
        return response.status_code in [200, 204]


def get_playback_session(client: CrunchyrollClient, url_id: str) -> Tuple[str, Dict, List[Dict]]:
    """
    Return the playback session details including the MPD URL, headers, and subtitles.
    
    Parameters:
        - client: Instance of CrunchyrollClient
        - url_id: ID of the media to fetch
    """
    data = client.get_streams(url_id)
    url = data.get('url')
    
    # Collect subtitles if available
    subtitles = []
    if 'subtitles' in data:
        collected = []
        for lang, info in data['subtitles'].items():
            sub_url = info.get('url')

            if not sub_url:
                continue
            
            collected.append({
                'language': lang, 
                'url': sub_url, 
                'format': info.get('format')
            })

        if collected:
            subtitles = collected
    
    # Return the MPD URL, headers, and subtitles
    headers = client._get_headers()
    return url, headers, subtitles