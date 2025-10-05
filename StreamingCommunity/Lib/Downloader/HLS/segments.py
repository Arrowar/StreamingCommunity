# 18.04.24

import os
import time
import logging
import binascii
import asyncio
from urllib.parse import urljoin, urlparse
from typing import Dict, Optional


# External libraries
import httpx
from tqdm import tqdm
from rich.console import Console


# Internal utilities
from StreamingCommunity.Util.color import Colors
from StreamingCommunity.Util.headers import get_userAgent
from StreamingCommunity.Util.config_json import config_manager


# Logic class
from ...M3U8 import (
    M3U8_Decryption,
    M3U8_Ts_Estimator,
    M3U8_Parser,
    M3U8_UrlFix
)


# Config
REQUEST_MAX_RETRY = config_manager.get_int('REQUESTS', 'max_retry')
REQUEST_VERIFY = config_manager.get_bool('REQUESTS', 'verify')
DEFAULT_VIDEO_WORKERS = config_manager.get_int('M3U8_DOWNLOAD', 'default_video_workers')
DEFAULT_AUDIO_WORKERS = config_manager.get_int('M3U8_DOWNLOAD', 'default_audio_workers')
MAX_TIMEOOUT = config_manager.get_int("REQUESTS", "timeout")
SEGMENT_MAX_TIMEOUT = config_manager.get_int("M3U8_DOWNLOAD", "segment_timeout")


# Variable
console = Console()


class M3U8_Segments:
    def __init__(self, url: str, tmp_folder: str, is_index_url: bool = True, limit_segments: int = None, custom_headers: Optional[Dict[str, str]] = None):
        """
        Initializes the M3U8_Segments object.

        Parameters:
            - url (str): The URL of the M3U8 playlist.
            - tmp_folder (str): The temporary folder to store downloaded segments.
            - is_index_url (bool): Flag indicating if `m3u8_index` is a URL (default True).
            - limit_segments (int): Optional limit for number of segments to process.
            - custom_headers (Dict[str, str]): Optional custom headers to use for all requests.
        """
        self.url = url
        self.tmp_folder = tmp_folder
        self.is_index_url = is_index_url
        self.limit_segments = limit_segments
        self.custom_headers = custom_headers if custom_headers else {'User-Agent': get_userAgent()}
        self.expected_real_time = None
        self.tmp_file_path = os.path.join(self.tmp_folder, "0.ts")
        os.makedirs(self.tmp_folder, exist_ok=True)

        # Util class
        self.decryption: M3U8_Decryption = None 
        self.class_ts_estimator = M3U8_Ts_Estimator(0, self) 
        self.class_url_fixer = M3U8_UrlFix(url)

        # Download tracking
        self.downloaded_segments = set()
        self.download_interrupted = False

        # Stats
        self.info_maxRetry = 0
        self.info_nRetry = 0
        self.info_nFailed = 0

        # Progress throttling
        self._last_progress_update = 0
        self._progress_update_interval = 0.1

    def __get_key__(self, m3u8_parser: M3U8_Parser) -> bytes:
        """
        Fetches the encryption key from the M3U8 playlist.

        Args:
            m3u8_parser (M3U8_Parser): An instance of M3U8_Parser containing parsed M3U8 data.

        Returns:
            bytes: The decryption key in byte format.
        """
        key_uri = urljoin(self.url, m3u8_parser.keys.get('uri'))
        parsed_url = urlparse(key_uri)
        self.key_base_url = f"{parsed_url.scheme}://{parsed_url.netloc}/"
        
        try:
            client_params = {
                'headers': self.custom_headers, 
                'timeout': MAX_TIMEOOUT, 
                'verify': REQUEST_VERIFY
            }
            response = httpx.get(url=key_uri, **client_params)
            response.raise_for_status()

            hex_content = binascii.hexlify(response.content).decode('utf-8')
            return bytes.fromhex(hex_content)
            
        except Exception as e:
            raise Exception(f"Failed to fetch key: {e}")
    
    def parse_data(self, m3u8_content: str) -> None:
        """
        Parses the M3U8 content and extracts necessary data.

        Args:
            m3u8_content (str): The raw M3U8 playlist content.
        """
        m3u8_parser = M3U8_Parser()
        m3u8_parser.parse_data(uri=self.url, raw_content=m3u8_content)

        self.expected_real_time_s = m3u8_parser.duration
        self.segment_init_url = m3u8_parser.init_segment
        self.has_init_segment = self.segment_init_url is not None

        if m3u8_parser.keys:
            key = self.__get_key__(m3u8_parser)    
            self.decryption = M3U8_Decryption(key, m3u8_parser.keys.get('iv'), m3u8_parser.keys.get('method'))

        segments = [
            self.class_url_fixer.generate_full_url(seg)
            if "http" not in seg else seg
            for seg in m3u8_parser.segments
        ]
        
        if self.limit_segments and len(segments) > self.limit_segments:
            logging.info(f"Limiting segments from {len(segments)} to {self.limit_segments}")
            segments = segments[:self.limit_segments]
            
        self.segments = segments
        self.class_ts_estimator.total_segments = len(self.segments)
        
    def get_segments_count(self) -> int:
        """
        Returns the total number of segments.
        """
        return len(self.segments) if hasattr(self, 'segments') else 0

    def get_info(self) -> None:
        """
        Retrieves M3U8 playlist information from the given URL.
        """
        if self.is_index_url:
            try:
                client_params = {
                    'headers': self.custom_headers, 
                    'timeout': MAX_TIMEOOUT, 
                    'verify': REQUEST_VERIFY
                }
                response = httpx.get(self.url, **client_params, follow_redirects=True)
                response.raise_for_status()
                
                self.parse_data(response.text)
                with open(os.path.join(self.tmp_folder, "playlist.m3u8"), "w") as f:
                    f.write(response.text)
                    
            except Exception as e:
                raise RuntimeError(f"M3U8 info retrieval failed: {e}")

    def _throttled_progress_update(self, content_size: int, progress_bar: tqdm):
        """
        Throttled progress update to reduce CPU usage.
        """
        current_time = time.time()
        if current_time - self._last_progress_update > self._progress_update_interval:
            self.class_ts_estimator.update_progress_bar(content_size, progress_bar)
            self._last_progress_update = current_time

    async def _download_init_segment(self, client: httpx.AsyncClient, progress_bar: tqdm) -> bytes:
        """
        Downloads the initialization segment if available.
        
        Returns:
            bytes: Init segment content or empty bytes if not available
        """
        if not self.has_init_segment:
            return b''
            
        init_url = self.segment_init_url
        if not init_url.startswith("http"):
            init_url = self.class_url_fixer.generate_full_url(init_url)
            
        try:
            response = await client.get(
                init_url, 
                timeout=SEGMENT_MAX_TIMEOUT, 
                headers=self.custom_headers
            )
            response.raise_for_status()
            init_content = response.content
            
            # Decrypt if needed (although init segments are typically not encrypted)
            if self.decryption is not None:
                try:
                    init_content = self.decryption.decrypt(init_content)
                except Exception as e:
                    logging.error(f"Decryption failed for init segment: {str(e)}")
                    return b''
            
            progress_bar.update(1)
            self._throttled_progress_update(len(init_content), progress_bar)
            logging.info("Init segment downloaded successfully")
            return init_content
            
        except Exception as e:
            logging.error(f"Failed to download init segment: {str(e)}")
            return b''

    async def _download_segment(self, client: httpx.AsyncClient, ts_url: str, index: int, semaphore: asyncio.Semaphore, max_retry: int) -> tuple:
        """
        Downloads a single TS segment with retry logic.

        Parameters:
            - client: Async HTTP client
            - ts_url: The URL of the TS segment
            - index: The index of the segment
            - semaphore: Semaphore for controlling concurrency
            - max_retry: Maximum number of retries

        Returns:
            tuple: (index, segment_content, retry_count)
        """
        async with semaphore:
            for attempt in range(max_retry):
                if self.download_interrupted:
                    return index, b'', attempt
                
                try:
                    timeout = min(SEGMENT_MAX_TIMEOUT, 10 + attempt * 5)
                    response = await client.get(
                        ts_url, 
                        timeout=timeout, 
                        headers=self.custom_headers,
                        follow_redirects=True
                    )
                    response.raise_for_status()
                    segment_content = response.content

                    # Decrypt if needed
                    if self.decryption is not None:
                        try:
                            segment_content = self.decryption.decrypt(segment_content)
                        except Exception as e:
                            logging.error(f"Decryption failed for segment {index}: {str(e)}")
                            if attempt + 1 == max_retry:
                                return index, b'', attempt
                            raise e

                    return index, segment_content, attempt

                except Exception:
                    if attempt + 1 == max_retry:
                        console.print(f" -- [red]Final retry failed for segment: {index}")
                        return index, b'', max_retry
                    
                    # Exponential backoff
                    if attempt < 2:
                        sleep_time = 0.5 + attempt * 0.5
                    else:
                        sleep_time = min(3.0, 1.02 ** attempt)
                    
                    await asyncio.sleep(sleep_time)
            
            return index, b'', max_retry

    async def _download_segments_batch(self, client: httpx.AsyncClient, results: list, semaphore: asyncio.Semaphore, progress_bar: tqdm):
        """
        Download all segments in parallel and store them in the results array.
        """
        async def download_with_progress(url, idx):
            """Download segment and update progress."""
            idx_result, data, nretry = await self._download_segment(client, url, idx, semaphore, REQUEST_MAX_RETRY)
            
            # Update stats
            if data and len(data) > 0:
                self.downloaded_segments.add(idx)
            else:
                self.info_nFailed += 1
            
            if nretry > self.info_maxRetry:
                self.info_maxRetry = nretry
            self.info_nRetry += nretry
            
            progress_bar.update(1)
            self._throttled_progress_update(len(data), progress_bar)
            
            return idx_result, data

        # Create all download tasks
        tasks = [download_with_progress(url, i) for i, url in enumerate(self.segments)]
        
        # Execute all tasks and collect results
        for coro in asyncio.as_completed(tasks):
            try:
                idx, data = await coro
                results[idx] = data
            except KeyboardInterrupt:
                self.download_interrupted = True
                console.print("\n[red]Download interrupted by user (Ctrl+C).")
                break

    async def _retry_failed_segments(self, client: httpx.AsyncClient, results: list, semaphore: asyncio.Semaphore, progress_bar: tqdm):
        """
        Retry failed segments up to 3 times.
        """
        max_global_retries = 3
        global_retry_count = 0

        while self.info_nFailed > 0 and global_retry_count < max_global_retries and not self.download_interrupted:
            failed_indices = [i for i, data in enumerate(results) if not data or len(data) == 0]
            if not failed_indices:
                break

            console.print(f"[yellow]Retrying {len(failed_indices)} failed segments (attempt {global_retry_count+1}/{max_global_retries})...")
            
            async def retry_single(idx):
                """Retry downloading a single failed segment."""
                idx_result, data, nretry = await self._download_segment(
                    client, self.segments[idx], idx, semaphore, REQUEST_MAX_RETRY
                )
                
                if data and len(data) > 0:
                    self.downloaded_segments.add(idx)
                
                if nretry > self.info_maxRetry:
                    self.info_maxRetry = nretry
                self.info_nRetry += nretry
                
                self._throttled_progress_update(len(data), progress_bar)
                return idx_result, data

            retry_tasks = [retry_single(i) for i in failed_indices]
            
            nFailed_this_round = 0
            for coro in asyncio.as_completed(retry_tasks):
                try:
                    idx, data = await coro
                    if data and len(data) > 0:
                        results[idx] = data
                    else:
                        nFailed_this_round += 1
                except KeyboardInterrupt:
                    self.download_interrupted = True
                    console.print("\n[red]Download interrupted by user (Ctrl+C).")
                    break
                    
            self.info_nFailed = nFailed_this_round
            global_retry_count += 1

    def _write_results_to_file(self, init_content: bytes, results: list):
        """
        Write init segment and all downloaded segments to file in order.
        Skips failed segments (empty bytes) but continues with subsequent segments.
        """
        with open(self.tmp_file_path, 'wb') as f:

            # Write init segment first if available
            if init_content:
                f.write(init_content)
            
            # Write all segments in order
            for data in results:
                if data and len(data) > 0:
                    f.write(data)

    async def download_segments_async(self, description: str, type: str):
        """
        Downloads all TS segments asynchronously.

        Parameters:
            - description: Description to insert on tqdm bar
            - type (str): Type of download: 'video' or 'audio'
        """
        self.get_info()

        # Initialize progress bar
        total_segments = len(self.segments) + (1 if self.has_init_segment else 0)
        progress_bar = tqdm(
            total=total_segments,
            bar_format=self._get_bar_format(description)
        )

        # Pre-allocate results array
        results = [None] * len(self.segments)
        
        # Reset stats
        self.downloaded_segments = set()
        self.info_nFailed = 0
        self.info_nRetry = 0
        self.info_maxRetry = 0
        self.download_interrupted = False

        try:
            # Configure HTTP client
            timeout_config = httpx.Timeout(SEGMENT_MAX_TIMEOUT, connect=10.0)
            limits = httpx.Limits(max_keepalive_connections=20, max_connections=100)
            
            async with httpx.AsyncClient(timeout=timeout_config, limits=limits, verify=REQUEST_VERIFY) as client:
                
                # Download init segment first
                init_content = await self._download_init_segment(client, progress_bar)
                
                # Determine worker count based on type
                max_workers = self._get_worker_count(type)
                semaphore = asyncio.Semaphore(max_workers)
                
                # Update estimator
                self.class_ts_estimator.total_segments = len(self.segments)
                
                # Download all segments
                await self._download_segments_batch(client, results, semaphore, progress_bar)
                
                # Retry failed segments
                if not self.download_interrupted:
                    await self._retry_failed_segments(client, results, semaphore, progress_bar)
                
                # Write all results to file
                self._write_results_to_file(init_content, results)

        except KeyboardInterrupt:
            self.download_interrupted = True
            console.print("\n[red]Download interrupted by user (Ctrl+C).")
            
        finally:
            self._cleanup_resources(progress_bar)

        if not self.download_interrupted:
            self._verify_download_completion()

        return self._generate_results(type)

    def download_streams(self, description: str, type: str):
        """
        Synchronous wrapper for download_segments_async.

        Parameters:
            - description: Description to insert on tqdm bar
            - type (str): Type of download: 'video' or 'audio'
        """
        try:
            return asyncio.run(self.download_segments_async(description, type))
        
        except KeyboardInterrupt:
            self.download_interrupted = True
            console.print("\n[red]Download interrupted by user (Ctrl+C).")
            return self._generate_results(type)

    def _get_bar_format(self, description: str) -> str:
        """
        Generate platform-appropriate progress bar format.
        """
        return (
            f"{Colors.YELLOW}[HLS]{Colors.CYAN} {description}{Colors.WHITE}: "
            f"{Colors.MAGENTA}{{bar:40}} "
            f"{Colors.LIGHT_GREEN}{{n_fmt}}{Colors.WHITE}/{Colors.CYAN}{{total_fmt}} {Colors.LIGHT_MAGENTA}TS {Colors.WHITE}"
            f"{Colors.DARK_GRAY}[{Colors.YELLOW}{{elapsed}}{Colors.WHITE} < {Colors.CYAN}{{remaining}}{Colors.DARK_GRAY}] "
            f"{Colors.WHITE}{{postfix}}"
        )
    
    def _get_worker_count(self, stream_type: str) -> int:
        """
        Return parallel workers based on stream type.
        """
        return {
            'video': DEFAULT_VIDEO_WORKERS,
            'audio': DEFAULT_AUDIO_WORKERS
        }.get(stream_type.lower(), 1)
    
    def _generate_results(self, stream_type: str) -> Dict:
        """Package final download results."""
        return {
            'type': stream_type,
            'nFailed': self.info_nFailed,
            'stopped': self.download_interrupted
        }
    
    def _verify_download_completion(self) -> None:
        """Validate final download integrity."""
        total = len(self.segments)
        if len(self.downloaded_segments) / total < 0.999:
            missing = sorted(set(range(total)) - self.downloaded_segments)
            raise RuntimeError(f"Download incomplete ({len(self.downloaded_segments)/total:.1%}). Missing segments: {missing}")
        
    def _cleanup_resources(self, progress_bar: tqdm) -> None:
        """Ensure resource cleanup and final reporting."""
        progress_bar.close()
        
        if self.info_nFailed > 0:
            self._display_error_summary()

    def _display_error_summary(self) -> None:
        """Generate final error report."""
        console.print(f"\n[cyan]Retry Summary: "
                     f"[white]Max retries: [green]{self.info_maxRetry} "
                     f"[white]Total retries: [green]{self.info_nRetry} "
                     f"[white]Failed segments: [red]{self.info_nFailed}")
        
        if self.info_nRetry > len(self.segments) * 0.3:
            console.print("[yellow]Warning: High retry count detected. Consider reducing worker count in config.")