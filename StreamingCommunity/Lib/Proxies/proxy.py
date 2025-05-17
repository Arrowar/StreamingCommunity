# 29.04.25

import sys
import time
import signal
import warnings
warnings.filterwarnings("ignore", category=UserWarning)


# External library
import httpx
from rich import print


# Internal utilities
from StreamingCommunity.Util.config_json import config_manager
from StreamingCommunity.Util.headers import get_headers


# Variable
MAX_TIMEOUT = config_manager.get_int("REQUESTS", "timeout")


class ProxyFinder:
    def __init__(self, url, timeout_threshold: float = 7.0):
        self.url = url
        self.timeout_threshold = timeout_threshold
        self.shutdown_flag = False
        signal.signal(signal.SIGINT, self._handle_interrupt)

    def _test_single_request(self, proxy_info: tuple) -> tuple:
        proxy, source = proxy_info
        try:
            start = time.time()
            print(f"[yellow]Testing proxy...")

            with httpx.Client(proxy=proxy, timeout=self.timeout_threshold) as client:
                response = client.get(self.url, headers=get_headers())
                if response.status_code == 200:
                    return (True, time.time() - start, response, source)
        except Exception:
            pass
        return (False, self.timeout_threshold + 1, None, source)

    def test_proxy(self, proxy_info: tuple) -> tuple:
        proxy, source = proxy_info
        if self.shutdown_flag:
            return (proxy, False, 0, None, source)
        
        success1, time1, text1, source = self._test_single_request(proxy_info)
        if not success1 or time1 > self.timeout_threshold:
            return (proxy, False, time1, None, source)
        
        success2, time2, _, source = self._test_single_request(proxy_info)
        avg_time = (time1 + time2) / 2
        return (proxy, success2 and time2 <= self.timeout_threshold, avg_time, text1, source)

    def _handle_interrupt(self, sig, frame):
        print("\n[red]Received keyboard interrupt. Terminating...")
        self.shutdown_flag = True
        sys.exit(0)

    def find_fast_proxy(self) -> str:
        try:
            proxy_config = config_manager.get("REQUESTS", "proxy")
            if proxy_config and isinstance(proxy_config, dict) and 'http' in proxy_config:
                print("[cyan]Using configured proxy from config.json...[/cyan]")
                return proxy_config['http']
        except Exception as e:
            print(f"[red]Error getting configured proxy: {str(e)}[/red]")
            
        return None