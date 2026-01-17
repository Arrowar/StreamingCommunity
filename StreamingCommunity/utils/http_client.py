# 09.08.25
from __future__ import annotations

import time
import random
from typing import Any, Dict, Optional, Union


# External library
import httpx
import ua_generator
from curl_cffi_smart import requests


# Internal utilities
from StreamingCommunity.utils import config_manager


# Variable
ua =  ua_generator.generate(device='desktop', browser=('chrome', 'edge'))
CONF_PROXY = config_manager.config.get_dict("REQUESTS", "proxy") or {}
USE_PROXY = bool(config_manager.config.get_bool("REQUESTS", "use_proxy"))



def _get_timeout() -> int:
    try:
        return int(config_manager.config.get_int("REQUESTS", "timeout"))
    except Exception:
        return 20


def _get_max_retry() -> int:
    try:
        return int(config_manager.config.get_int("REQUESTS", "max_retry"))
    except Exception:
        return 3


def _get_verify() -> bool:
    try:
        return bool(config_manager.config.get_bool("REQUESTS", "verify"))
    except Exception:
        return True


def _get_proxies() -> Optional[Dict[str, str]]:
    """Return proxies dict if `USE_PROXY` is true and proxy config is present, else None."""
    if not USE_PROXY:
        return None

    try:
        proxies = CONF_PROXY if isinstance(CONF_PROXY, dict) else config_manager.config.get_dict("REQUESTS", "proxy")
        if not isinstance(proxies, dict):
            return None
        # Normalize empty strings
        cleaned: Dict[str, str] = {}
        for scheme, url in proxies.items():
            if isinstance(url, str) and url.strip():
                cleaned[scheme] = url.strip()
        return cleaned or None
    except Exception:
        return None


def _default_headers(extra: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    headers = {"User-Agent": get_userAgent()}
    if extra:
        headers.update(extra)
    return headers


def create_client(*, headers: Optional[Dict[str, str]] = None, cookies: Optional[Dict[str, str]] = None, timeout: Optional[Union[int, float]] = None,
    verify: Optional[bool] = None, proxies: Optional[Dict[str, str]] = None, http2: bool = False, follow_redirects: bool = True,
) -> httpx.Client:
    """Factory for a configured httpx.Client."""
    proxy_value = proxies if proxies is not None else _get_proxies()
    client_kwargs = dict(
        headers=_default_headers(headers),
        cookies=cookies,
        timeout=timeout if timeout is not None else _get_timeout(),
        verify=_get_verify() if verify is None else verify,
        follow_redirects=follow_redirects,
        http2=http2,
    )

    if proxy_value:
        # Try new-style 'proxies' kwarg first
        try:
            return httpx.Client(**client_kwargs, proxies=proxy_value)
        except TypeError:
            # Older httpx may require a single proxy URL via 'proxy'
            single_proxy = None
            if isinstance(proxy_value, dict):
                single_proxy = proxy_value.get("https") or proxy_value.get("http")
            elif isinstance(proxy_value, str):
                single_proxy = proxy_value

            # If we have a single proxy URL, try passing as 'proxy'
            if single_proxy:
                return httpx.Client(**client_kwargs, proxy=single_proxy)
            raise
    else:
        return httpx.Client(**client_kwargs)


def create_async_client(*, headers: Optional[Dict[str, str]] = None, cookies: Optional[Dict[str, str]] = None,
    timeout: Optional[Union[int, float]] = None, verify: Optional[bool] = None, proxies: Optional[Dict[str, str]] = None,
    http2: bool = False, follow_redirects: bool = True,
) -> httpx.AsyncClient:
    """Factory for a configured httpx.AsyncClient."""
    proxy_value = proxies if proxies is not None else _get_proxies()
    client_kwargs = dict(
        headers=_default_headers(headers),
        cookies=cookies,
        timeout=timeout if timeout is not None else _get_timeout(),
        verify=_get_verify() if verify is None else verify,
        follow_redirects=follow_redirects,
        http2=http2,
    )

    if proxy_value:
        try:
            return httpx.AsyncClient(**client_kwargs, proxies=proxy_value)
        except TypeError:
            single_proxy = None
            if isinstance(proxy_value, dict):
                single_proxy = proxy_value.get("https") or proxy_value.get("http")
            elif isinstance(proxy_value, str):
                single_proxy = proxy_value

            if single_proxy:
                return httpx.AsyncClient(**client_kwargs, proxy=single_proxy)
            raise
    else:
        return httpx.AsyncClient(**client_kwargs)


def create_client_curl(*, headers: Optional[Dict[str, str]] = None, cookies: Optional[Dict[str, str]] = None,
    timeout: Optional[Union[int, float]] = None, verify: Optional[bool] = None, proxies: Optional[Dict[str, str]] = None,
    impersonate: str = "chrome99", allow_redirects: bool = True,
):
    """Factory for a configured curl_cffi session."""
    session = requests.Session()
    session.headers.update(_default_headers(headers))
    if cookies:
        session.cookies.update(cookies)
    session.timeout = timeout if timeout is not None else _get_timeout()
    session.verify = _get_verify() if verify is None else verify
    proxy_value = proxies if proxies is not None else _get_proxies()
    if proxy_value:
        session.proxies = proxy_value
    session.impersonate = impersonate
    session.allow_redirects = allow_redirects
    
    return session


def _sleep_with_backoff(attempt: int, base: float = 1.1, cap: float = 10.0) -> None:
    """Exponential backoff with jitter."""
    delay = min(base * (2 ** attempt), cap)

    # Add small jitter to avoid thundering herd
    delay += random.uniform(0.0, 0.25)
    time.sleep(delay)


def fetch(url: str, *, method: str = "GET", params: Optional[Dict[str, Any]] = None,
    data: Optional[Any] = None, json: Optional[Any] = None, headers: Optional[Dict[str, str]] = None,
    cookies: Optional[Dict[str, str]] = None, timeout: Optional[Union[int, float]] = None,
    verify: Optional[bool] = None, proxies: Optional[Dict[str, str]] = None,
    follow_redirects: bool = True, http2: bool = False,
    max_retry: Optional[int] = None, return_content: bool = False,
) -> Optional[Union[str, bytes]]:
    """
    Perform an HTTP request with retry. Returns text or bytes according to return_content.
    Returns None if all retries fail.
    """
    attempts = max_retry if max_retry is not None else _get_max_retry()

    with create_client(
        headers=headers,
        cookies=cookies,
        timeout=timeout,
        verify=verify,
        proxies=proxies,
        http2=http2,
        follow_redirects=follow_redirects,
    ) as client:
        for attempt in range(attempts):
            try:
                resp = client.request(method, url, params=params, data=data, json=json)
                resp.raise_for_status()
                return resp.content if return_content else resp.text
            except Exception:
                if attempt + 1 >= attempts:
                    break
                _sleep_with_backoff(attempt)
        return None


async def async_fetch(url: str, *, method: str = "GET", params: Optional[Dict[str, Any]] = None,
    data: Optional[Any] = None, json: Optional[Any] = None, headers: Optional[Dict[str, str]] = None,
    cookies: Optional[Dict[str, str]] = None, timeout: Optional[Union[int, float]] = None,
    verify: Optional[bool] = None, proxies: Optional[Dict[str, str]] = None,
    follow_redirects: bool = True, http2: bool = False,
    max_retry: Optional[int] = None, return_content: bool = False,
) -> Optional[Union[str, bytes]]:
    """
    Async HTTP request with retry. Returns text or bytes according to return_content.
    Returns None if all retries fail.
    """
    attempts = max_retry if max_retry is not None else _get_max_retry()

    async with create_async_client(
        headers=headers,
        cookies=cookies,
        timeout=timeout,
        verify=verify,
        proxies=proxies,
        http2=http2,
        follow_redirects=follow_redirects,
    ) as client:
        for attempt in range(attempts):
            try:
                resp = await client.request(method, url, params=params, data=data, json=json)
                resp.raise_for_status()
                return resp.content if return_content else resp.text
            except Exception:
                if attempt + 1 >= attempts:
                    break
                # Use same backoff logic for async by sleeping in thread (short duration)
                _sleep_with_backoff(attempt)
        return None


def get_userAgent() -> str:
    user_agent =  ua_generator.generate().text
    return user_agent


def get_headers() -> dict:
    return ua.headers.get()