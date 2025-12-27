# 29.12.25

import time
import os
import json
import base64
from typing import Dict, Optional


# Internal utilities
from StreamingCommunity.Util.config_json import config_manager
from StreamingCommunity.Util.http_client import create_client_curl, get_userAgent


# Constants
PUBLIC_TOKEN = "bm9haWhkZXZtXzZpeWcwYThsMHE6"
BASE_URL = "https://www.crunchyroll.com"
API_BETA_BASE_URL = "https://beta-api.crunchyroll.com"
PLAY_SERVICE_URL = "https://cr-play-service.prd.crunchyrollsvc.com"
DEFAULT_QPS = 3.0
DEFAULT_MAX_RETRIES = 3
DEFAULT_BASE_BACKOFF_MS = 300
DEFAULT_SLOWDOWN_AFTER = 50


class RateLimiter:
    def __init__(self, qps: float):
        self.qps = max(0.1, float(qps))
        self._last = 0.0

    def wait(self):
        if self.qps <= 0:
            return
        
        now = time.time()
        min_dt = 1.0 / self.qps
        elapsed = now - self._last
        
        if elapsed < min_dt:
            time.sleep(min_dt - elapsed)
        
        self._last = time.time()


class CrunchyrollClient:
    def __init__(self, qps: float = DEFAULT_QPS, locale: str = "it-IT", max_retries: int = DEFAULT_MAX_RETRIES, base_backoff_ms: int = DEFAULT_BASE_BACKOFF_MS, slowdown_after: int = DEFAULT_SLOWDOWN_AFTER) -> None:
        
        # Load configuration
        config = config_manager.get_dict("SITE_LOGIN", "crunchyroll")
        self.device_id = config.get('device_id')
        self.etp_rt = config.get('etp_rt')
        self.locale = locale or "it-IT"
        
        # API endpoints
        self.web_base_url = BASE_URL
        self.api_base_url = self._resolve_api_base_url(config)
        self.play_service_url = PLAY_SERVICE_URL
        
        # Token management
        self.token_cache_path = self._resolve_token_cache_path(config)
        self.token_cache_enabled = bool(config.get("token_cache", True) and self.token_cache_path)
        self.access_token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        self.account_id: Optional[str] = None
        self.expires_at: float = 0.0
        
        # HTTP settings
        self.user_agent = config.get("user_agent") or None
        self.rate_limiter = RateLimiter(qps or DEFAULT_QPS)
        self._req_count = 0
        
        # Retry settings
        self.max_retries = int(max_retries if max_retries is not None else DEFAULT_MAX_RETRIES)
        self.base_backoff_ms = int(base_backoff_ms if base_backoff_ms is not None else DEFAULT_BASE_BACKOFF_MS)
        self.slowdown_after = int(slowdown_after if slowdown_after is not None else DEFAULT_SLOWDOWN_AFTER)
        
        # Initialize
        cache_data = self._load_token_cache()
        if not self.user_agent:
            cached_ua = (cache_data or {}).get("user_agent")
            self.user_agent = cached_ua if (cached_ua or "").strip() else get_userAgent()
        
        self.session = create_client_curl(headers=self._get_headers(), cookies=self._get_cookies())

    @staticmethod
    def _resolve_api_base_url(config: Dict) -> str:
        """Resolve API base URL from config."""
        api_base = config.get("api_base") or config.get("api_base_url")
        value = str(api_base).strip() if api_base is not None else ""
        
        if value:
            lowered = value.lower()
            if lowered in ("www", "web", "default", "auto"):
                return BASE_URL
            if lowered in ("beta", "beta-api", "beta_api", "betaapi"):
                return API_BETA_BASE_URL
            if lowered.startswith("http://") or lowered.startswith("https://"):
                return value.rstrip("/")
        
        if bool(config.get("use_beta_api")):
            return API_BETA_BASE_URL
        
        return BASE_URL

    @staticmethod
    def _resolve_token_cache_path(config: Dict) -> Optional[str]:
        """Resolve token cache file path."""
        if config.get("token_cache") is False:
            return None
        
        raw = config.get("token_cache_path")
        path = str(raw).strip() if raw else os.path.join(".cache", "crunchyroll_token.json")
        
        if not os.path.isabs(path):
            base_dir = os.path.dirname(getattr(config_manager, "file_path", os.getcwd()))
            path = os.path.join(base_dir, path)
        
        return path

    # Token management
    @staticmethod
    def _jwt_exp(token: Optional[str]) -> Optional[int]:
        """Extract expiration from JWT token."""
        if not token or token.count(".") < 2:
            return None
        
        try:
            payload_b64 = token.split(".", 2)[1]
            padding = "=" * (-len(payload_b64) % 4)
            payload = base64.urlsafe_b64decode(payload_b64 + padding).decode("utf-8", errors="replace")
            obj = json.loads(payload)
            exp = obj.get("exp")
            
            if exp is None:
                return None
            
            exp_str = str(exp)
            return int(exp_str) if exp_str.isdigit() else None
        except Exception:
            return None

    def _set_expires_at(self, *, expires_in: Optional[int] = None) -> None:
        """Set token expiration with safety margin."""
        exp = self._jwt_exp(self.access_token)
        
        if exp and exp > 0:
            self.expires_at = float(exp - 60)
            return
        
        if expires_in is None:
            self.expires_at = 0.0
            return
        
        self.expires_at = time.time() + max(0, int(expires_in) - 60)

    def _load_token_cache(self) -> Dict:
        """Load cached tokens from disk."""
        if not self.token_cache_path:
            return {}
        
        try:
            if not os.path.exists(self.token_cache_path):
                return {}
            
            with open(self.token_cache_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            cached_device_id = (data or {}).get("device_id")
            if self.device_id and cached_device_id and cached_device_id != self.device_id:
                return {}
            
            # Load tokens
            access = (data or {}).get("access_token")
            refresh = (data or {}).get("refresh_token")
            account_id = (data or {}).get("account_id")
            
            if access:
                self.access_token = access
            if refresh:
                self.refresh_token = refresh
            if account_id:
                self.account_id = account_id
            
            self.expires_at = float((data or {}).get("expires_at") or 0.0)
            
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _save_token_cache(self) -> None:
        """Save tokens to disk cache."""
        if not self.token_cache_enabled or not self.token_cache_path:
            return
        
        try:
            os.makedirs(os.path.dirname(self.token_cache_path), exist_ok=True)
            
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
        except Exception:
            pass

    def _get_headers(self) -> Dict:
        """Build HTTP headers."""
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
        """Build cookies."""
        cookies = {'device_id': self.device_id}
        if self.etp_rt:
            cookies['etp_rt'] = self.etp_rt
        return cookies

    def start(self) -> bool:
        """Authenticate with Crunchyroll."""
        headers = self._get_headers()
        headers['authorization'] = f'Basic {PUBLIC_TOKEN}'
        headers['content-type'] = 'application/x-www-form-urlencoded'
        
        data = {
            'device_id': self.device_id,
            'device_type': 'Chrome on Windows',
            'grant_type': 'etp_rt_cookie',
        }
        
        self.rate_limiter.wait()
        response = self.session.post(
            f'{self.api_base_url}/auth/v1/token',
            cookies=self._get_cookies(),
            headers=headers,
            data=data
        )
        self._req_count += 1
        
        if response.status_code == 400:
            return False
        
        response.raise_for_status()
        result = response.json()
        
        self.access_token = result.get('access_token')
        self.refresh_token = result.get('refresh_token')
        self.account_id = result.get('account_id')
        
        expires_in = int(result.get('expires_in', 3600) or 3600)
        self._set_expires_at(expires_in=expires_in)
        self._save_token_cache()
        
        return True

    def _refresh(self) -> None:
        """Refresh access token."""
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
        
        self.rate_limiter.wait()
        response = self.session.post(
            f'{self.api_base_url}/auth/v1/token',
            cookies=self._get_cookies(),
            headers=headers,
            data=data
        )
        self._req_count += 1
        response.raise_for_status()
        
        result = response.json()
        self.access_token = result.get('access_token')
        self.refresh_token = result.get('refresh_token') or self.refresh_token
        
        expires_in = int(result.get('expires_in', 3600) or 3600)
        self._set_expires_at(expiresIn=expires_in)
        self._save_token_cache()

    def _ensure_token(self) -> None:
        """Ensure token is valid."""
        if not self.access_token:
            if not self.start():
                raise RuntimeError("Authentication failed")
            return
        
        if time.time() >= (self.expires_at - 30):
            try:
                self._refresh()
            except Exception:
                if not self.start():
                    raise RuntimeError("Re-authentication failed")

    def _request_with_retry(self, method: str, url: str, **kwargs):
        """Execute HTTP request with retry logic."""
        self._ensure_token()
        
        max_retries = int(kwargs.pop('_retries', self.max_retries))
        base_backoff_ms = int(kwargs.pop('_base_backoff_ms', self.base_backoff_ms))
        slowdown_after = int(kwargs.pop('_slowdown_after', self.slowdown_after))
        
        headers = kwargs.pop('headers', {}) or {}
        merged_headers = {**self._get_headers(), **headers}
        kwargs['headers'] = merged_headers
        kwargs.setdefault('cookies', self._get_cookies())
        kwargs.setdefault('timeout', config_manager.get_int('REQUESTS', 'timeout', default=30))
        
        attempt = 0
        while True:
            self.rate_limiter.wait()
            
            if self._req_count >= slowdown_after:
                time.sleep((base_backoff_ms + 200) / 1000.0)
            
            response = self.session.request(method, url, **kwargs)
            self._req_count += 1
            
            # Handle 401 - token expired
            if response.status_code == 401 and attempt < max_retries:
                attempt += 1
                try:
                    self._refresh()
                except Exception:
                    self.start()
                kwargs['headers'] = {**self._get_headers(), **headers}
                time.sleep((base_backoff_ms * attempt) / 1000.0)
                continue
            
            # Handle 429 - rate limit
            if response.status_code == 429 and attempt < max_retries:
                attempt += 1
                retry_after = response.headers.get("Retry-After")
                wait_s = float(str(retry_after).strip()) if retry_after else (base_backoff_ms * attempt + 750) / 1000.0
                self.rate_limiter.qps = max(0.5, float(self.rate_limiter.qps) * 0.8)
                time.sleep(max(0.0, float(wait_s)))
                continue
            
            # Handle 502, 503, 504 - server errors
            if response.status_code in (502, 503, 504) and attempt < max_retries:
                attempt += 1
                backoff = (base_backoff_ms * attempt + 100) / 1000.0
                time.sleep(backoff)
                continue
            
            return response

    def request(self, method: str, url: str, **kwargs):
        """Public request method."""
        return self._request_with_retry(method, url, **kwargs)

    def refresh(self) -> None:
        """Public refresh method."""
        self._refresh()

    def get_streams(self, media_id: str) -> Dict:
        """Get playback data for media ID."""
        playback_urls = [
            f'{self.play_service_url}/v3/{media_id}/web/chrome/play',
            f'{self.play_service_url}/v3/{media_id}/web/firefox/play',
            f'{self.web_base_url}/playback/v3/{media_id}/web/chrome/play',
            f'{self.web_base_url}/playback/v3/{media_id}/web/firefox/play',
        ]
        
        last_error: Optional[Exception] = None
        
        for pb_url in playback_urls:
            for attempt in range(2):
                try:
                    response = self._request_with_retry('GET', pb_url, params={'locale': self.locale})
                except Exception as e:
                    last_error = e
                    break
                
                if response.status_code == 403:
                    raise Exception("Playback Rejected: Subscription required")
                
                if response.status_code == 404:
                    last_error = Exception(f"Playback endpoint not found: {pb_url}")
                    break
                
                if response.status_code == 420:
                    self._handle_active_streams(response)
                    if attempt + 1 < 2:
                        time.sleep(1)
                        continue
                    raise Exception("TOO_MANY_ACTIVE_STREAMS. Wait and try again.")
                
                try:
                    response.raise_for_status()
                except Exception as e:
                    last_error = e
                    break
                
                data = response.json()
                if data.get('error') == 'Playback is Rejected':
                    raise Exception("Playback Rejected: Premium required")
                
                return data
        
        if last_error:
            raise last_error
        raise Exception("Playback failed")

    def _handle_active_streams(self, response):
        """Handle TOO_MANY_ACTIVE_STREAMS response."""
        try:
            payload = response.json()
        except Exception:
            return
        
        active_streams = payload.get("activeStreams") or []
        for stream in active_streams:
            content_id = stream.get("contentId")
            token = stream.get("token")
            if content_id and token:
                self.deauth_video(content_id, token)

    def deauth_video(self, media_id: str, token: str) -> bool:
        """Deactivate playback token."""
        if not media_id or not token:
            return False
        
        try:
            self.rate_limiter.wait()
            response = self.session.patch(
                f'{PLAY_SERVICE_URL}/v1/token/{media_id}/{token}/inactive',
                cookies=self._get_cookies(),
                headers=self._get_headers(),
            )
            self._req_count += 1
            return response.status_code in (200, 204)
        except Exception:
            return False

    def delete_active_stream(self, media_id: str, token: str) -> bool:
        """Delete active stream session."""
        if not token:
            return False
        
        try:
            response = self._request_with_retry(
                "DELETE",
                f'{self.play_service_url}/v1/token/{media_id}/{token}',
                _retries=1,
            )
            if response.status_code in (200, 204):
                return True
            
            if response.status_code not in (404, 405):
                return False
            
            response = self._request_with_retry(
                "DELETE",
                f'{self.web_base_url}/playback/v1/token/{media_id}/{token}',
                _retries=1,
            )
            return response.status_code in (200, 204)
        except Exception:
            return False