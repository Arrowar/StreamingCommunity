# 22.12.25

import uuid
from typing import Dict


# Internal utilities
from StreamingCommunity.utils import config_manager
from StreamingCommunity.utils.http_client import create_client_curl


# Variable
_discovery_client = None
cookie_st = config_manager.login.get("discoveryeuplus", "st")


class DiscoveryPlus:
    def __init__(self, cookies: Dict[str, str]):
        """
        Initialize Discovery Plus client
        
        Args:
            cookies: Dictionary containing 'st' token
        """
        self.cookies = cookies
        self.device_id = str(uuid.uuid1())
        self.client_id = "b6746ddc-7bc7-471f-a16c-f6aaf0c34d26"
        self.base_url = "https://default.any-any.prd.api.discoveryplus.com"
        self.access_token = None
        
        self.headers = {
            'accept': '*/*',
            'accept-language': 'it,it-IT;q=0.9,en;q=0.8',
            'user-agent': 'androidtv dplus/20.8.1.2 (android/9; en-US; SHIELD Android TV-NVIDIA; Build/1)',
            'x-disco-client': 'ANDROIDTV:9:dplus:20.8.1.2',
            'x-disco-params': 'realm=bolt,bid=dplus,features=ar',
            'x-device-info': f'dplus/20.8.1.2 (NVIDIA/SHIELD Android TV; android/9-mdarcy; {self.device_id}/{self.client_id})',
        }
        
        self._authenticate()
    
    def _authenticate(self):
        """Authenticate and get access token"""
        url = f"{self.base_url}/token"
        params = {'realm': 'bolt', 'deviceId': self.device_id}
        
        response = create_client_curl(headers=self.headers, cookies=self.cookies).get(url, params=params)
        response.raise_for_status()
        
        data = response.json()
        self.access_token = data['data']['attributes']['token']
        
        # Get routing config
        url = f"{self.base_url}/session-context/headwaiter/v1/bootstrap"
        response = create_client_curl(headers=self.headers, cookies=self.cookies).post(url)
        response.raise_for_status()
        
        config = response.json()
        tenant = config['routing']['tenant']
        market = config['routing']['homeMarket']
        self.base_url = f"https://default.{tenant}-{market}.prd.api.discoveryplus.com"
    
    def get_playback_info(self, edit_id: str) -> Dict[str, str]:
        """
        Get manifest and license URLs for playback
        
        Args:
            edit_id: Edit ID of the content
            
        Returns:
            Dictionary with 'manifest' and 'license' URLs
        """
        url = f"{self.base_url}/playback-orchestrator/any/playback-orchestrator/v1/playbackInfo"
        
        headers = self.headers.copy()
        headers['Authorization'] = f'Bearer {self.access_token}'
        
        payload = {
            'appBundle': 'com.wbd.stream',
            'applicationSessionId': self.device_id,
            'capabilities': {
                'codecs': {
                    'audio': {
                        'decoders': [
                            {'codec': 'aac', 'profiles': ['lc', 'he', 'hev2', 'xhe']},
                            {'codec': 'eac3', 'profiles': ['atmos']},
                        ]
                    },
                    'video': {
                        'decoders': [
                            {
                                'codec': 'h264',
                                'levelConstraints': {
                                    'framerate': {'max': 60, 'min': 0},
                                    'height': {'max': 2160, 'min': 48},
                                    'width': {'max': 3840, 'min': 48},
                                },
                                'maxLevel': '5.2',
                                'profiles': ['baseline', 'main', 'high'],
                            },
                            {
                                'codec': 'h265',
                                'levelConstraints': {
                                    'framerate': {'max': 60, 'min': 0},
                                    'height': {'max': 2160, 'min': 144},
                                    'width': {'max': 3840, 'min': 144},
                                },
                                'maxLevel': '5.1',
                                'profiles': ['main10', 'main'],
                            },
                        ],
                        'hdrFormats': ['hdr10', 'hdr10plus', 'dolbyvision', 'dolbyvision5', 'dolbyvision8', 'hlg'],
                    },
                },
                'contentProtection': {
                    'contentDecryptionModules': [
                        {'drmKeySystem': 'playready', 'maxSecurityLevel': 'SL3000'}
                    ]
                },
                'manifests': {'formats': {'dash': {}}},
            },
            'consumptionType': 'streaming',
            'deviceInfo': {
                'player': {
                    'mediaEngine': {'name': '', 'version': ''},
                    'playerView': {'height': 2160, 'width': 3840},
                    'sdk': {'name': '', 'version': ''},
                }
            },
            'editId': edit_id,
            'firstPlay': False,
            'gdpr': False,
            'playbackSessionId': str(uuid.uuid4()),
            'userPreferences': {},
        }
        
        response = create_client_curl(headers=headers, cookies=self.cookies).post(url, json=payload)
        response.raise_for_status()
        
        data = response.json()
        
        # Get manifest URL
        manifest = (
            data.get('fallback', {}).get('manifest', {}).get('url', '').replace('_fallback', '')
            or data.get('manifest', {}).get('url')
        )
        
        # Get license URL
        license_url = (
            data.get('fallback', {}).get('drm', {}).get('schemes', {}).get('playready', {}).get('licenseUrl')
            or data.get('drm', {}).get('schemes', {}).get('playready', {}).get('licenseUrl')
        )
        
        return {
            'manifest': manifest,
            'license': license_url
        }


def get_client():
    """Get or create DiscoveryPlus client instance"""
    global _discovery_client
    if _discovery_client is None:
        if cookie_st is None or cookie_st == "":
            raise ValueError("ST cookie is required for Discovery Plus authentication")
        cookies = {'st': cookie_st}
        _discovery_client = DiscoveryPlus(cookies)
    return _discovery_client