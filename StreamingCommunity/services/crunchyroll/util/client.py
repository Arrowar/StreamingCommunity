# 29.12.25

import time
import os
import logging
import json
import base64
from typing import Dict, Optional


# Internal utilities
from StreamingCommunity.utils import config_manager
from StreamingCommunity.utils.http_client import create_client_curl, get_userAgent


# Constants
PUBLIC_TOKEN = "bm9haWhkZXZtXzZpeWcwYThsMHE6"
BASE_URL = "https://www.crunchyroll.com"
API_BETA_BASE_URL = "https://beta-api.crunchyroll.com"
PLAY_SERVICE_URL = "https://cr-play-service.prd.crunchyrollsvc.com"


class CrunchyrollClient:
    def __init__(self, locale: str = "it-IT", **kwargs) -> None:
        self.device_id = config_manager.login.get('crunchyroll', 'device_id')
        self.etp_rt = config_manager.login.get('crunchyroll', 'etp_rt')
        self.locale = locale

        self.web_base_url = BASE_URL
        self.api_base_url = self._resolve_api_base_url()
        self.play_service_url = PLAY_SERVICE_URL
        self.token_cache_path = self._resolve_token_cache_path()
        self.token_cache_enabled = True
        self.user_agent = None
        
        self.access_token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        self.account_id: Optional[str] = None
        self.expires_at: float = 0.0

        # Load cached tokens
        cache_data = self._load_token_cache()
        if not self.user_agent:
            cached_ua = cache_data.get("user_agent") if isinstance(cache_data, dict) else None
            self.user_agent = cached_ua if isinstance(cached_ua, str) and cached_ua.strip() else get_userAgent()
        
        self.session = create_client_curl(headers=self._get_headers(), cookies=self._get_cookies())

    @staticmethod
    def _resolve_api_base_url() -> str:
        """Determine the correct API base URL - defaults to beta API."""
        return API_BETA_BASE_URL

    @staticmethod
    def _resolve_token_cache_path() -> str:
        """Resolve absolute path for token cache file - always enabled."""
        base_dir = os.getcwd()
        path = os.path.join(base_dir, ".cache", "crunchyroll_token.json")
        return path

    @staticmethod
    def _jwt_exp(token: Optional[str]) -> Optional[int]:
        """Extract expiration timestamp from JWT token payload."""
        if not isinstance(token, str) or token.count(".") < 2:
            return None
        
        try:
            payload_b64 = token.split(".", 2)[1]
            padding = "=" * (-len(payload_b64) % 4)
            payload = base64.urlsafe_b64decode(payload_b64 + padding).decode("utf-8", errors="replace")
            obj = json.loads(payload)
            exp = obj.get("exp")

            if isinstance(exp, int):
                return exp
            if isinstance(exp, str) and exp.isdigit():
                return int(exp)
            
        except Exception:
            pass
        return None

    def _set_expires_at(self, *, expires_in: Optional[int] = None) -> None:
        """Set token expiration time from JWT or expires_in value."""
        exp = self._jwt_exp(self.access_token)
        if isinstance(exp, int) and exp > 0:
            self.expires_at = float(exp - 60)
            return
        
        if expires_in is None:
            self.expires_at = 0.0
            return
        
        self.expires_at = time.time() + max(0, int(expires_in) - 60)

    def _load_token_cache(self) -> Dict:
        """Load cached authentication tokens from file if available."""
        if not self.token_cache_path:
            return {}
        
        try:
            if not os.path.exists(self.token_cache_path):
                return {}
            
            with open(self.token_cache_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            if not isinstance(data, dict):
                return {}

            cached_device_id = data.get("device_id")
            if self.device_id and isinstance(cached_device_id, str) and cached_device_id != self.device_id:
                return {}

            access = data.get("access_token")
            refresh = data.get("refresh_token")
            if isinstance(access, str) and access:
                self.access_token = access
            if isinstance(refresh, str) and refresh:
                self.refresh_token = refresh

            account_id = data.get("account_id")
            if isinstance(account_id, str) and account_id:
                self.account_id = account_id

            try:
                self.expires_at = float(data.get("expires_at") or 0.0)
            except Exception:
                self.expires_at = 0.0

            return data
        except Exception as e:
            logging.error(f"Token cache load failed: {e}")
            return {}

    def _save_token_cache(self) -> None:
        """Save current authentication tokens to cache file."""
        if not self.token_cache_path:
            return
        
        try:
            cache_dir = os.path.dirname(self.token_cache_path)
            if cache_dir:
                os.makedirs(cache_dir, exist_ok=True)
            
            payload = {
                "device_id": self.device_id,
                "account_id": self.account_id,
                "access_token": self.access_token,
                "refresh_token": self.refresh_token,
                "expires_at": self.expires_at,
                "user_agent": self.user_agent,
                "api_base_url": self.api_base_url,
                "saved_at": time.time(),
            }

            with open(self.token_cache_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)

        except Exception as e:
            logging.error(f"Token cache save failed: {e}")

    def _get_headers(self) -> Dict:
        """Generate HTTP headers for API requests including authorization."""
        headers = {
            'user-agent': self.user_agent or get_userAgent(),
            'accept': 'application/json, text/plain, */*',
            'origin': self.web_base_url,
            'referer': f'{self.web_base_url}/',
            'accept-language': f'{self.locale.replace("_", "-")},en-US;q=0.8,en;q=0.7',
        }
        if self.access_token:
            headers['authorization'] = f'Bearer {self.access_token}'
            
        return headers

    def _get_cookies(self) -> Dict:
        """Generate cookies for API requests including device_id and etp_rt."""
        cookies = {'device_id': self.device_id}
        if self.etp_rt:
            cookies['etp_rt'] = self.etp_rt
        return cookies

    def start(self) -> bool:
        """Authenticate using etp_rt cookie - single attempt."""
        headers = self._get_headers()
        headers['authorization'] = f'Basic {PUBLIC_TOKEN}'
        headers['content-type'] = 'application/x-www-form-urlencoded'
        
        data = {
            'device_id': self.device_id,
            'device_type': 'Chrome on Windows',
            'grant_type': 'etp_rt_cookie',
        }

        response = self.session.post(
            f'{self.api_base_url}/auth/v1/token',
            cookies=self._get_cookies(),
            headers=headers,
            data=data
        )
        
        if response.status_code != 200:
            logging.error(f"Authentication failed: {response.status_code}")
            return False
        
        result = response.json()
        
        self.access_token = result.get('access_token')
        self.refresh_token = result.get('refresh_token')
        self.account_id = result.get('account_id')
        
        expires_in = int(result.get('expires_in', 3600) or 3600)
        self._set_expires_at(expires_in=expires_in)
        self._save_token_cache()
        
        return True

    def _refresh(self) -> None:
        """Refresh access token - single attempt."""
        if not self.refresh_token:
            raise RuntimeError("refresh_token missing")
        
        headers = self._get_headers()
        headers['authorization'] = f'Basic {PUBLIC_TOKEN}'
        headers['content-type'] = 'application/x-www-form-urlencoded'
        
        data = {
            'grant_type': 'refresh_token',
            'refresh_token': self.refresh_token,
            'device_type': 'Chrome on Windows',
        }
        if self.device_id:
            data['device_id'] = self.device_id

        response = self.session.post(
            f'{self.api_base_url}/auth/v1/token',
            cookies=self._get_cookies(),
            headers=headers,
            data=data
        )
        
        if response.status_code != 200:
            raise RuntimeError(f"Token refresh failed: {response.status_code}")
        
        result = response.json()
        self.access_token = result.get('access_token')
        self.refresh_token = result.get('refresh_token') or self.refresh_token
        
        expires_in = int(result.get('expires_in', 3600) or 3600)
        self._set_expires_at(expiresIn=expires_in)
        self._save_token_cache()

    def _ensure_token(self) -> None:
        """Ensure valid access token - no retries."""
        if not self.access_token:
            if not self.start():
                raise RuntimeError("Authentication failed")
            return
        
        # Refresh if expiring soon
        if time.time() >= (self.expires_at - 30):
            try:
                self._refresh()
            except Exception:
                if not self.start():
                    raise RuntimeError("Re-authentication failed")

    def request(self, method: str, url: str, **kwargs):
        """Single request attempt - no retries."""
        self._ensure_token()
        
        headers = kwargs.pop('headers', {}) or {}
        merged_headers = {**self._get_headers(), **headers}
        kwargs['headers'] = merged_headers
        kwargs.setdefault('cookies', self._get_cookies())
        kwargs.setdefault('timeout', config_manager.config.get_int('REQUESTS', 'timeout', default=30))
        
        response = self.session.request(method, url, **kwargs)
        
        # Only handle 401 once
        if response.status_code == 401:
            try:
                self._refresh()
            except Exception:
                self.start()
            kwargs['headers'] = {**self._get_headers(), **headers}
            response = self.session.request(method, url, **kwargs)
        
        return response

    def refresh(self) -> None:
        """Public refresh method."""
        self._refresh()

    def get_streams(self, media_id: str) -> Dict:
        """Get playback data - single attempt only."""
        pb_url = f'{self.play_service_url}/v3/{media_id}/web/chrome/play'

        response = self.request('GET', pb_url, params={'locale': self.locale})

        if response.status_code == 403:
            raise Exception("Playback Rejected: Subscription required")

        if response.status_code == 404:
            raise Exception(f"Playback endpoint not found: {pb_url}")

        if response.status_code == 420:
            try:
                payload = response.json()
                error_code = payload.get("error")
                active_streams = payload.get("activeStreams", [])

                if error_code in ("TOO_MANY_ACTIVE_STREAMS", "TOO_MANY_CONCURRENT_STREAMS") and active_streams:
                    logging.warning(f"TOO_MANY_ACTIVE_STREAMS: cleaning up {len(active_streams)} streams")
                    for s in active_streams:
                        if isinstance(s, dict):
                            content_id = s.get("contentId")
                            token = s.get("token")
                            if content_id and token:
                                self.deauth_video(content_id, token)
            except Exception:
                pass
            
            raise Exception("TOO_MANY_ACTIVE_STREAMS. Wait and try again.")

        if response.status_code != 200:
            raise Exception(f"Playback failed: {response.status_code}")

        data = response.json()

        if data.get('error') == 'Playback is Rejected':
            raise Exception("Playback Rejected: Premium required")

        return data

    def deauth_video(self, media_id: str, token: str) -> bool:
        """Mark playback token as inactive to free stream slot."""
        if not media_id or not token:
            return False

        try:
            response = self.session.patch(
                f'{PLAY_SERVICE_URL}/v1/token/{media_id}/{token}/inactive',
                cookies=self._get_cookies(),
                headers=self._get_headers(),
            )
            return response.status_code in (200, 204)
        
        except Exception as e:
            logging.error(f"Failed to deauth stream token: {e}")
            return False