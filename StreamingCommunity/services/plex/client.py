# 12.02.26

import uuid
from typing import Dict, Any


# Internal utilities
from StreamingCommunity.utils.http_client import create_client, get_headers


class PlexAPI:
    BASE_URL = "https://vod.provider.plex.tv"
    USER_ENDPOINT = "https://plex.tv/api/v2/users/anonymous"
    SCREEN_ENDPOINT = "https://luma.plex.tv/api/screen"
    PROVIDER = "provider://tv.plex.provider.vod"
    
    def __init__(self):
        self.client_id = str(uuid.uuid4())
        self.headers = get_headers()
        self.headers.update({
            "User-Agent": "Mozilla/5.0 (Linux; Android 11; Smart TV Build/AR2101; wv)",
            "accept": "application/json",
            "x-plex-client-identifier": self.client_id,
            "x-plex-language": "en",
            "x-plex-product": "Plex Mediaverse",
            "x-plex-provider-version": "6.5.0",
        })
        self.client = create_client(headers=self.headers)
        self.auth_token = None
        self._authenticate()
    
    def _authenticate(self):
        """Authenticate with Plex anonymous user"""
        try:
            r = self.client.post(self.USER_ENDPOINT)
            r.raise_for_status()

            # Parse response to get auth token
            json_response = r.json()
            self.auth_token = json_response.get("authToken")
            if not self.auth_token:
                self.auth_token = json_response.get("user", {}).get("authToken")
            
            if not self.auth_token:
                raise ValueError("Failed to get auth token")
            
            self.client.headers.update({"x-plex-token": self.auth_token})
        except Exception as e:
            raise Exception(f"Errore autenticazione Plex: {e}")
    
    def get_headers(self):
        return dict(self.client.headers)


def get_playback_info(metadata: Any) -> Dict[str, Any]:
    """Generate playback info: manifest URL and license URL. Works with dict or object with metadata."""
    api = get_client()
    BASE_URL = "https://vod.provider.plex.tv"

    # Check if metadata is a dict or an object
    if isinstance(metadata, dict):
        media_list = metadata.get("Media", [])
    else:
        media_list = getattr(metadata, "media", [])
    
    dash_media = next((x for x in media_list if x.get("protocol", "").lower() == "dash"), None)
    hls_media = next((x for x in media_list if x.get("protocol", "").lower() == "hls"), None)
    
    media = dash_media or hls_media
    if not media:
        return {"error": "No DASH or HLS media found"}
    
    media_key = media.get("id")
    has_drm = media.get("drm")
    protocol = "DASH" if dash_media else "HLS"
    
    result = {
        "protocol": protocol,
        "drm": has_drm,
        "media_id": media_key
    }
    
    if has_drm:
        manifest_url = (f"{BASE_URL}/library/parts/{media_key}?includeAllStreams=1&X-Plex-Product=Plex+Mediaverse&X-Plex-Token={api.auth_token}&X-Plex-DRM=widevine")
        license_url = (f"{BASE_URL}/library/parts/{media_key}/license?X-Plex-Token={api.auth_token}&X-Plex-DRM=widevine")
        result["manifest_url"] = manifest_url
        result["license_url"] = license_url
    else:
        manifest_url = (f"{BASE_URL}/library/parts/{media_key}?includeAllStreams=1&X-Plex-Product=Plex+Mediaverse&X-Plex-Token={api.auth_token}")
        result["manifest_url"] = manifest_url
        result["license_url"] = None
    
    return result


_plex_api = None

def get_client():
    global _plex_api
    if _plex_api is None:
        _plex_api = PlexAPI()
    return _plex_api