# 29.04.25

import os
import sys
import time
import json
import signal
import warnings
warnings.filterwarnings("ignore", category=UserWarning)
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed


# External library
import httpx
from rich import print
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeRemainingColumn


# Internal utilities
from StreamingCommunity.Util.config_json import config_manager
from StreamingCommunity.Util.headers import get_headers


# Variable
MAX_TIMEOUT = config_manager.get_int("REQUESTS", "timeout")


class ProxyFinder:
    def __init__(self, url, timeout_threshold: float = 7.0, max_proxies: int = 150, max_workers: int = 12):
        self.url = url
        self.timeout_threshold = timeout_threshold
        self.max_proxies = max_proxies
        self.max_workers = max_workers
        self.found_proxy = None
        self.shutdown_flag = False
        self.json_file = os.path.join(os.path.dirname(__file__), 'working_proxies.json')
        signal.signal(signal.SIGINT, self._handle_interrupt)

    def load_saved_proxies(self) -> tuple:
        """Load saved proxies if they're not expired (2 hours old)"""
        try:
            if not os.path.exists(self.json_file):
                return None, None
                
            with open(self.json_file, 'r') as f:
                data = json.load(f)
                
            if not data.get('proxies') or not data.get('last_update'):
                return None, None
                
            last_update = datetime.fromisoformat(data['last_update'])
            if datetime.now() - last_update > timedelta(hours=2):
                return None, None
                
            return data['proxies'], last_update
        except Exception:
            return None, None
            
    def save_working_proxy(self, proxy: str, response_time: float):
        """Save working proxy to JSON file"""
        data = {
            'proxies': [{'proxy': proxy, 'response_time': response_time}],
            'last_update': datetime.now().isoformat()
        }
        try:
            with open(self.json_file, 'w') as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"[bold red]Error saving proxy:[/bold red] {str(e)}")

    def fetch_geonode(self) -> list:
        proxies = []
        try:
            response = httpx.get(
                "https://proxylist.geonode.com/api/proxy-list?protocols=http%2Chttps&limit=100&page=1&sort_by=speed&sort_type=asc",
                headers=get_headers(), 
                timeout=MAX_TIMEOUT
            )
            data = response.json()
            proxies = [(f"http://{p['ip']}:{p['port']}", "Geonode") for p in data.get('data', [])]
            
        except Exception as e:
            print(f"[bold red]Error in Geonode:[/bold red] {str(e)[:100]}")

        return proxies

    def fetch_proxyscrape(self) -> list:
        proxies = []
        try:
            response = httpx.get(
                "https://api.proxyscrape.com/v4/free-proxy-list/get?request=get_proxies&protocol=http&skip=0&proxy_format=protocolipport&format=json&limit=100&timeout=1000",
                headers=get_headers(), 
                timeout=MAX_TIMEOUT
            )
            data = response.json()
            if 'proxies' in data and isinstance(data['proxies'], list):
                proxies = [(proxy_data['proxy'], "ProxyScrape") for proxy_data in data['proxies'] if 'proxy' in proxy_data]

        except Exception as e:
            print(f"[bold red]Error in ProxyScrape:[/bold red] {str(e)[:100]}")

        return proxies

    def fetch_proxies_from_sources(self) -> list:
        #print("[cyan]Fetching proxies from sources...[/cyan]")
        with ThreadPoolExecutor(max_workers=3) as executor:
            proxyscrape_future = executor.submit(self.fetch_proxyscrape)
            geonode_future = executor.submit(self.fetch_geonode)
            
            sources_proxies = {}
            
            try:
                proxyscrape_result = proxyscrape_future.result()
                sources_proxies["proxyscrape"] = proxyscrape_result[:int(self.max_proxies/2)]
            except Exception as e:
                print(f"[bold red]Error fetching from proxyscrape:[/bold red] {str(e)[:100]}")
                sources_proxies["proxyscrape"] = []
            
            try:
                geonode_result = geonode_future.result()
                sources_proxies["geonode"] = geonode_result[:int(self.max_proxies/2)]
            except Exception as e:
                print(f"[bold red]Error fetching from geonode:[/bold red] {str(e)[:100]}")
                sources_proxies["geonode"] = []
            
            merged_proxies = []
            
            if "proxyscrape" in sources_proxies:
                merged_proxies.extend(sources_proxies["proxyscrape"])
            
            if "geonode" in sources_proxies:
                merged_proxies.extend(sources_proxies["geonode"])
            
            proxy_list = merged_proxies[:self.max_proxies]
            return proxy_list

    def _test_single_request(self, proxy_info: tuple) -> tuple:
        proxy, source = proxy_info
        try:
            start = time.time()
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
        print("\n[bold yellow]Received keyboard interrupt. Terminating...[/bold yellow]")
        self.shutdown_flag = True
        sys.exit(0)

    def find_fast_proxy(self) -> tuple:
        saved_proxies, last_update = self.load_saved_proxies()
        if saved_proxies:
            print("[cyan]Testing saved proxy...[/cyan]")
            for proxy_data in saved_proxies:
                result = self.test_proxy((proxy_data['proxy'], 'cached'))
                if result[1]:
                    return proxy_data['proxy'], result[3], result[2]
                else:
                    print(f"[red]Saved proxy {proxy_data['proxy']} failed - response time: {result[2]:.2f}s[/red]")

        proxies = self.fetch_proxies_from_sources()
        if not proxies:
            print("[bold red]No proxies fetched to test.[/bold red]")
            return (None, None, None)
             
        found_proxy = None
        response_text = None
        source = None
        failed_count = 0
        success_count = 0

        #print(f"[cyan]Testing {len(proxies)} proxies...[/cyan]")
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {executor.submit(self.test_proxy, p): p for p in proxies}
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                TextColumn("[cyan]{task.fields[success]}[/cyan]/[red]{task.fields[failed]}[/red]"),
                TimeRemainingColumn(),
            ) as progress:
                task = progress.add_task(
                    "[cyan]Testing Proxies", 
                    total=len(futures),
                    success=success_count,
                    failed=failed_count
                )
                
                for future in as_completed(futures):
                    if self.shutdown_flag:
                        break

                    try:
                        proxy, success, elapsed, response, proxy_source = future.result()
                        if success:
                            success_count += 1
                            print(f"[bold green]Found valid proxy:[/bold green] {proxy} ({elapsed:.2f}s)")
                            found_proxy = proxy
                            response_text = response
                            self.save_working_proxy(proxy, elapsed)
                            self.shutdown_flag = True
                            break
                        else:
                            failed_count += 1
                    except Exception:
                        failed_count += 1
                    
                    progress.update(task, advance=1, success=success_count, failed=failed_count)

        if not found_proxy:
            print("[bold red]No working proxies found[/bold red]")
        
        return (found_proxy, response_text, source)