# 28.07.25

import uuid
from dataclasses import dataclass, field
from typing import Optional,  Dict, Any


# External library
from curl_cffi.requests import Session


# Internal utilities
from StreamingCommunity.Util.config_json import config_manager
from StreamingCommunity.Util.headers import get_userAgent, get_headers


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


@dataclass
class Account:
    account_id: Optional[str] = None
    external_id: Optional[str] = None
    email: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Profile:
    profile_id: Optional[str] = None
    email: Optional[str] = None
    profile_name: Optional[str] = None
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


def get_account(token: Token, device_id):
    with Session(impersonate="chrome110") as session:
        country = (token.country or "IT")
        cookies = {
            'device_id': device_id,
            'c_locale': f'{country.lower()}-{country.upper()}',
        }
        response = session.get(
            'https://www.crunchyroll.com/accounts/v1/me',
            headers={
                'authorization': f'Bearer {token.access_token}',
                'user-agent': get_userAgent(),
            },
            cookies=cookies
        )
        response.raise_for_status()

        # Get the JSON response
        data = response.json()
        known = {
            'account_id', 'external_id', 'email'
        }
        extra = {k: v for k, v in data.items() if k not in known}
        return Account(
            account_id=data.get('account_id'),
            external_id=data.get('external_id'),
            email=data.get('email'),
            extra=extra
        )


def get_profiles(token: Token, device_id):
    with Session(impersonate="chrome110") as session:
        country = token.country
        cookies = {
            'device_id': device_id,
            'c_locale': f'{country.lower()}-{country.upper()}',
        }
        response = session.get(
            'https://www.crunchyroll.com/accounts/v1/me/multiprofile',
            headers={
                'authorization': f'Bearer {token.access_token}',
                'user-agent': get_userAgent(),
            },
            cookies=cookies
        )
        response.raise_for_status()

        # Get the JSON response
        data = response.json()
        profiles = []
        for p in data.get('profiles', []):
            known = {
                'profile_id', 'email', 'profile_name'
            }
            extra = {k: v for k, v in p.items() if k not in known}
            profiles.append(Profile(
                profile_id=p.get('profile_id'),
                email=p.get('email'),
                profile_name=p.get('profile_name'),
                extra=extra
            ))
        return profiles


def cr_login_session(device_id: str, email: str, password: str):
    """
    Esegue una richiesta di login a Crunchyroll SSO usando curl_cffi.requests.
    """
    cookies = {
        'device_id': device_id,
    }
    data = (
        f'{{"email":"{email}","password":"{password}","eventSettings":{{}}}}'
    )
    with Session(impersonate="chrome110") as session:
        response = session.post(
            'https://sso.crunchyroll.com/api/login',
            cookies=cookies,
            headers=get_headers(),
            data=data
        )
        response.raise_for_status()
        return response


def get_playback_session(token: Token, device_id: str, url_id: str):
    """
    Crea una sessione per ottenere i dati di playback da Crunchyroll.
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
        return url, headers