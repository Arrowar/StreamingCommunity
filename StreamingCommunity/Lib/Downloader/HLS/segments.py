# 18.04.24

import os
import sys
import time
import queue
import signal
import logging
import binascii
import threading
from queue import PriorityQueue
from urllib.parse import urljoin, urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Optional


# External libraries
import httpx
from tqdm import tqdm
from rich.console import Console


# Internal utilities
from StreamingCommunity.Util.color import Colors
from StreamingCommunity.Util.headers import get_userAgent
from StreamingCommunity.Util.http_client import create_client
from StreamingCommunity.Util.config_json import config_manager


# Logic class
from ...M3U8 import (
    M3U8_Decryption,
    M3U8_Ts_Estimator,
    M3U8_Parser,
    M3U8_UrlFix
)

# Config
TQDM_DELAY_WORKER = 0.01
REQUEST_MAX_RETRY = config_manager.get_int('REQUESTS', 'max_retry')
REQUEST_VERIFY = config_manager.get_bool('REQUESTS', 'verify')
DEFAULT_VIDEO_WORKERS = config_manager.get_int('M3U8_DOWNLOAD', 'default_video_workers')
DEFAULT_AUDIO_WORKERS = config_manager.get_int('M3U8_DOWNLOAD', 'default_audio_workers')
MAX_TIMEOOUT = config_manager.get_int("REQUESTS", "timeout")
SEGMENT_MAX_TIMEOUT = config_manager.get_int("M3U8_DOWNLOAD", "segment_timeout")
TELEGRAM_BOT = config_manager.get_bool('DEFAULT', 'telegram_bot')
MAX_INTERRUPT_COUNT = 3

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

        # Sync
        self.queue = PriorityQueue(maxsize=20)
        self.buffer = {}
        self.expected_index = 0 
        self.write_buffer = bytearray()  
        self.write_batch_size = 50

        self.stop_event = threading.Event()
        self.downloaded_segments = set()
        self.base_timeout = 1.0
        self.current_timeout = 3.0

        # Stopping
        self.interrupt_flag = threading.Event()
        self.download_interrupted = False
        self.interrupt_count = 0
        self.force_stop = False
        self.interrupt_lock = threading.Lock()

        # HTTP Client
        self._client = None
        self._client_lock = threading.Lock()

        # OTHER INFO
        self.info_maxRetry = 0
        self.info_nRetry = 0
        self.info_nFailed = 0
        self.active_retries = 0 
        self.active_retries_lock = threading.Lock()

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
    
    def setup_interrupt_handler(self):
        """
        Set up a signal handler for graceful interruption.
        """
        def interrupt_handler(signum, frame):
            with self.interrupt_lock:
                self.interrupt_count += 1
                if self.interrupt_count >= MAX_INTERRUPT_COUNT:
                    self.force_stop = True
                    
            if self.force_stop:
                console.print("\n[red]Force stop triggered! Exiting immediately.")
                self._cleanup_client()

            else:
                if not self.interrupt_flag.is_set():
                    remaining = MAX_INTERRUPT_COUNT - self.interrupt_count
                    console.print(f"\n[red]- Stopping gracefully... (Ctrl+C {remaining}x to force)")
                    self.download_interrupted = True

                    if remaining == 1:
                        self.interrupt_flag.set()
                    
        if threading.current_thread() is threading.main_thread():
            signal.signal(signal.SIGINT, interrupt_handler)
        else:
            print("Signal handler must be set in the main thread")

    def _get_http_client(self):
        """
        Get a reusable HTTP client using the centralized factory.
        Uses optimized settings for segment downloading with custom headers.
        """
        if self._client is None:
            with self._client_lock:
                self._client = create_client(
                    headers=self.custom_headers,
                    timeout=SEGMENT_MAX_TIMEOUT
                )
                
        return self._client
    
    def _cleanup_client(self):
        """Pulizia client"""
        if self._client:
            try:
                self._client.close()
            except Exception:
                pass
            self._client = None
                            
    def download_segment(self, ts_url: str, index: int, progress_bar: tqdm, backoff_factor: float = 1.02) -> None:
        """
        Downloads a TS segment

        Parameters:
            - ts_url (str): The URL of the TS segment.
            - index (int): The index of the segment.
            - progress_bar (tqdm): Progress counter for tracking download progress.
            - backoff_factor (float): Backoff factor.
        """
        for attempt in range(REQUEST_MAX_RETRY):
            if self.interrupt_flag.is_set():
                return
            
            try:
                client = self._get_http_client()
                timeout = min(SEGMENT_MAX_TIMEOUT, 10 + attempt * 5)

                # Make request with custom headers
                response = client.get(ts_url, timeout=timeout, headers=self.custom_headers)
                response.raise_for_status()
                segment_content = response.content
                content_size = len(segment_content)

                # Decrypt if needed
                if self.decryption is not None:
                    try:
                        segment_content = self.decryption.decrypt(segment_content)
                    except Exception as e:
                        logging.error(f"Decryption failed for segment {index}: {str(e)}")

                        if attempt + 1 == REQUEST_MAX_RETRY:
                            self.interrupt_flag.set()
                            self.stop_event.set()

                        raise e

                current_time = time.time()
                if current_time - self._last_progress_update > self._progress_update_interval:
                    self.class_ts_estimator.update_progress_bar(content_size, progress_bar)
                    self._last_progress_update = current_time
                
                try:
                    self.queue.put((index, segment_content), timeout=0.05)
                    self.downloaded_segments.add(index)  
                    progress_bar.update(1)
                    return
                
                except queue.Full:
                    time.sleep(0.02)

                    try:
                        self.queue.put((index, segment_content), timeout=0.1)
                        self.downloaded_segments.add(index)  
                        progress_bar.update(1)
                        return
                    
                    except queue.Full:
                        self.queue.put((index, segment_content))
                        self.downloaded_segments.add(index)  
                        progress_bar.update(1)
                        return

            except Exception:
                
                if attempt > self.info_maxRetry:
                    self.info_maxRetry = attempt + 1
                self.info_nRetry += 1

                if attempt + 1 == REQUEST_MAX_RETRY:
                    console.print(f" -- [red]Final retry failed for segment: {index}")
                    
                    try:
                        self.queue.put((index, None), timeout=0.1)
                    except queue.Full:
                        time.sleep(0.02)
                        self.queue.put((index, None))

                    progress_bar.update(1)
                    self.info_nFailed += 1
                    return
                
                if attempt < 2:
                    sleep_time = 0.5 + attempt * 0.5
                else:
                    sleep_time = min(3.0, backoff_factor ** attempt)
                
                time.sleep(sleep_time)

    def write_segments_to_file(self):
        """
        Writes segments to file with additional verification.
        """
        with open(self.tmp_file_path, 'wb') as f:
            while not self.stop_event.is_set() or not self.queue.empty():
                if self.interrupt_flag.is_set():
                    break
                
                try:
                    index, segment_content = self.queue.get(timeout=self.current_timeout)

                    # Successful queue retrieval: reduce timeout
                    self.current_timeout = max(self.base_timeout, self.current_timeout / 2)

                    # Handle failed segments
                    if segment_content is None:
                        if index == self.expected_index:
                            self.expected_index += 1
                        continue

                    # Write segment if it's the next expected one
                    if index == self.expected_index:
                        f.write(segment_content)
                        f.flush()
                        self.expected_index += 1

                        # Write any buffered segments that are now in order
                        while self.expected_index in self.buffer:
                            next_segment = self.buffer.pop(self.expected_index)

                            if next_segment is not None:
                                f.write(next_segment)
                                f.flush()

                            self.expected_index += 1
                    
                    else:
                        self.buffer[index] = segment_content

                except queue.Empty:
                    self.current_timeout = min(MAX_TIMEOOUT, self.current_timeout * 1.1)
                    time.sleep(0.05)

                    if self.stop_event.is_set():
                        break

                except Exception as e:
                    logging.error(f"Error writing segment {index}: {str(e)}")
    
    def download_init_segment(self) -> bool:
        """
        Downloads the initialization segment if available.
        
        Returns:
            bool: True if init segment was downloaded successfully, False otherwise
        """
        if not self.has_init_segment:
            return False
            
        init_url = self.segment_init_url
        if not init_url.startswith("http"):
            init_url = self.class_url_fixer.generate_full_url(init_url)
            
        try:
            client = self._get_http_client()
            response = client.get(
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
                    return False
            
            # Put init segment in queue with highest priority (0)
            self.queue.put((0, init_content))
            self.downloaded_segments.add(0)
            
            # Adjust expected_index to 1 since we've handled index 0 separately
            self.expected_index = 0
            logging.info("Init segment downloaded successfully")
            return True
            
        except Exception as e:
            logging.error(f"Failed to download init segment: {str(e)}")
            return False
    
    def download_streams(self, description: str, type: str):
        """
        Downloads all TS segments in parallel and writes them to a file.

        Parameters:
            - description: Description to insert on tqdm bar
            - type (str): Type of download: 'video' or 'audio'
        """
        if TELEGRAM_BOT:
          console.log("####")
          
        self.get_info()
        self.setup_interrupt_handler()

        progress_bar = tqdm(
            total=len(self.segments) + (1 if self.has_init_segment else 0), 
            bar_format=self._get_bar_format(description),
            file=sys.stdout,
        )

        try:
            self.class_ts_estimator.total_segments = len(self.segments)
            
            writer_thread = threading.Thread(target=self.write_segments_to_file)
            writer_thread.daemon = True
            writer_thread.start()
            max_workers = self._get_worker_count(type)
            
            # First download the init segment if available
            if self.has_init_segment:
                if self.download_init_segment():
                    progress_bar.update(1)
            
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = []
                
                # Start segment indices from 1 if we have an init segment
                start_idx = 1 if self.has_init_segment else 0
                
                for index, segment_url in enumerate(self.segments):
                    if self.interrupt_flag.is_set():
                        break

                    # Adjust index if we have an init segment
                    queue_index = index + start_idx
                        
                    # Delay every 200 submissions to reduce CPU usage
                    if index % 200 == 0 and index > 0:
                        time.sleep(TQDM_DELAY_WORKER)
                        
                    futures.append(executor.submit(self.download_segment, segment_url, queue_index, progress_bar))

                # Process completed futures
                for future in as_completed(futures):
                    if self.interrupt_flag.is_set():
                        break
                    try:
                        future.result(timeout=1.0)
                    except Exception as e:
                        logging.error(f"Error in download thread: {str(e)}")

                # Retry missing segments if necessary
                if not self.interrupt_flag.is_set():
                    total_segments = len(self.segments)
                    completed_segments = len(self.downloaded_segments)
                    
                    if completed_segments < total_segments:
                        missing_segments = set(range(total_segments)) - self.downloaded_segments
                        logging.warning(f"Missing {len(missing_segments)} segments")

                        # Retry missing segments with interrupt check
                        retry_workers = min(2, len(missing_segments))
                        if retry_workers > 0:
                            retry_futures = []
                            for index in missing_segments:
                                if self.interrupt_flag.is_set():
                                    break
                                retry_futures.append(executor.submit(self.download_segment, self.segments[index], index, progress_bar))
                            
                            for future in as_completed(retry_futures):
                                if self.interrupt_flag.is_set():
                                    break
                                try:
                                    future.result(timeout=2.0)
                                except Exception as e:
                                    logging.error(f"Failed to retry segment: {str(e)}")

        finally:
            self._cleanup_resources(writer_thread, progress_bar)

        if not self.interrupt_flag.is_set():
            self._verify_download_completion()

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
        Return parallel workers based on stream type and infrastructure.
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
        
    def _cleanup_resources(self, writer_thread: threading.Thread, progress_bar: tqdm) -> None:
        """Ensure resource cleanup and final reporting."""
        self.stop_event.set()
        writer_thread.join(timeout=30)
        progress_bar.close()
        self._cleanup_client()
        
        if self.info_nFailed > 0:
            self._display_error_summary()

        self.buffer = {}
        self.write_buffer.clear()
        self.expected_index = 0

    def _display_error_summary(self) -> None:
        """Generate final error report."""
        console.print(f"\n[cyan]Retry Summary: "
                     f"[white]Max retries: [green]{self.info_maxRetry} "
                     f"[white]Total retries: [green]{self.info_nRetry} "
                     f"[white]Failed segments: [red]{self.info_nFailed}")
        
        if self.info_nRetry > len(self.segments) * 0.3:
            console.print("[yellow]Warning: High retry count detected. Consider reducing worker count in config.")