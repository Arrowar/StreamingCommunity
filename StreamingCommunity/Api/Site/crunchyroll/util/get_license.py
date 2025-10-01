# 28.07.25

import uuid
from dataclasses import dataclass, field
from typing import Optional,  Dict, Any


# External library
from curl_cffi.requests import Session


# Internal utilities
from StreamingCommunity.Util.config_json import config_manager
from StreamingCommunity.Util.headers import get_userAgent


# Variable
device_id = None
auth_basic = 'bm9haWhkZXZtXzZpeWcwYThsMHE6'
etp_rt = config_manager.get_dict("SITE_LOGIN", "crunchyroll")['etp_rt']
x_cr_tab_id = config_manager.get_dict("SITE_LOGIN", "crunchyroll")['x_cr_tab_id']


@dataclass
class Token:
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    expires_in: Optional[int] = None
    token_type: Optional[str] = None
    scope: Optional[str] = None
    country: Optional[str] = None
    account_id: Optional[str] = None
    profile_id: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)



def generate_device_id():
    global device_id

    if device_id is not None:
        return device_id
    
    device_id = str(uuid.uuid4())
    return device_id


def get_auth_token(device_id):
    with Session(impersonate="chrome110") as session:
        cookies = {
            'etp_rt': etp_rt,
        }
        response = session.post(
            'https://www.crunchyroll.com/auth/v1/token',
            headers={
                'authorization': f'Basic {auth_basic}',
                'user-agent': get_userAgent(),
            },
            data={
                'device_id': device_id,
                'device_type': 'Chrome on Windows',
                'grant_type': 'etp_rt_cookie',
            },
            cookies=cookies
        )
        if response.status_code == 400:
            print("Error 400: Please enter a correct 'etp_rt' value in config.json. You can find the value in the request headers.")

        # Get the JSON response
        data = response.json()
        known = {
            'access_token', 'refresh_token', 'expires_in', 'token_type', 'scope',
            'country', 'account_id', 'profile_id'
        }
        extra = {k: v for k, v in data.items() if k not in known}
        return Token(
            access_token=data.get('access_token'),
            refresh_token=data.get('refresh_token'),
            expires_in=data.get('expires_in'),
            token_type=data.get('token_type'),
            scope=data.get('scope'),
            country=data.get('country'),
            account_id=data.get('account_id'),
            profile_id=data.get('profile_id'),
            extra=extra
        )


def get_playback_session(token: Token, device_id: str, url_id: str):
    """
    Crea una sessione per ottenere i dati di playback e sottotitoli da Crunchyroll.
    """
    cookies = {
        'device_id': device_id,
        'etp_rt': etp_rt
    }
    headers = {
        'authorization': f'Bearer {token.access_token}',
        'user-agent': get_userAgent(),
        'x-cr-tab-id': x_cr_tab_id
    }

    with Session(impersonate="chrome110") as session:
        response = session.get(
            f'https://www.crunchyroll.com/playback/v3/{url_id}/web/chrome/play',
            cookies=cookies,
            headers=headers
        )

        if (response.status_code == 403):
            raise Exception("Playback is Rejected: The current subscription does not have access to this content")
        
        if (response.status_code == 420):
            raise Exception("TOO_MANY_ACTIVE_STREAMS. Wait a few minutes and try again.")

        response.raise_for_status()

        # Get the JSON response
        data = response.json()
        
        if data.get('error') == 'Playback is Rejected':
            raise Exception("Playback is Rejected: Premium required")
        
        url = data.get('url')
        
        subtitles = []
        if 'subtitles' in data:
            subtitles = [
                {'language': lang, 'url': info['url'], 'format': info.get('format')}
                for lang, info in data['subtitles'].items()
            ]
        
        return url, headers, subtitles