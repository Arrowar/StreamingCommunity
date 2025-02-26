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
from typing import Dict


# External libraries
import httpx
from tqdm import tqdm
from rich.console import Console


# Internal utilities
from StreamingCommunity.Util.color import Colors
from StreamingCommunity.Util.headers import get_userAgent
from StreamingCommunity.Util.config_json import config_manager, get_use_large_bar


# Logic class
from ...M3U8 import (
    M3U8_Decryption,
    M3U8_Ts_Estimator,
    M3U8_Parser,
    M3U8_UrlFix
)

# Config
TQDM_DELAY_WORKER = config_manager.get_float('M3U8_DOWNLOAD', 'tqdm_delay')
REQUEST_MAX_RETRY = config_manager.get_int('REQUESTS', 'max_retry')
REQUEST_VERIFY = config_manager.get_int('REQUESTS', 'verify')
DEFAULT_VIDEO_WORKERS = config_manager.get_int('M3U8_DOWNLOAD', 'default_video_workser')
DEFAULT_AUDIO_WORKERS = config_manager.get_int('M3U8_DOWNLOAD', 'default_audio_workser')
MAX_TIMEOOUT = config_manager.get_int("REQUESTS", "timeout")
MAX_INTERRUPT_COUNT = 3
SEGMENT_MAX_TIMEOUT = config_manager.get_int("M3U8_DOWNLOAD", "segment_timeout")
TELEGRAM_BOT = config_manager.get_bool('DEFAULT', 'telegram_bot')


# Variable
console = Console()


class M3U8_Segments:
    def __init__(self, url: str, tmp_folder: str, is_index_url: bool = True):
        """
        Initializes the M3U8_Segments object.

        Parameters:
            - url (str): The URL of the M3U8 playlist.
            - tmp_folder (str): The temporary folder to store downloaded segments.
            - is_index_url (bool): Flag indicating if `m3u8_index` is a URL (default True).
        """
        self.url = url
        self.tmp_folder = tmp_folder
        self.is_index_url = is_index_url
        self.expected_real_time = None
        self.tmp_file_path = os.path.join(self.tmp_folder, "0.ts")
        os.makedirs(self.tmp_folder, exist_ok=True)

        # Util class
        self.decryption: M3U8_Decryption = None 
        self.class_ts_estimator = M3U8_Ts_Estimator(0, self) 
        self.class_url_fixer = M3U8_UrlFix(url)

        # Sync
        self.queue = PriorityQueue()
        self.stop_event = threading.Event()
        self.downloaded_segments = set()
        self.base_timeout = 0.5
        self.current_timeout = 3.0

        # Stopping
        self.interrupt_flag = threading.Event()
        self.download_interrupted = False
        self.interrupt_count = 0
        self.force_stop = False
        self.interrupt_lock = threading.Lock()

        # OTHER INFO
        self.info_maxRetry = 0
        self.info_nRetry = 0
        self.info_nFailed = 0
        self.active_retries = 0 
        self.active_retries_lock = threading.Lock()

    def __get_key__(self, m3u8_parser: M3U8_Parser) -> bytes:
        key_uri = urljoin(self.url, m3u8_parser.keys.get('uri'))
        parsed_url = urlparse(key_uri)
        self.key_base_url = f"{parsed_url.scheme}://{parsed_url.netloc}/"
        
        try:
            client_params = {'headers': {'User-Agent': get_userAgent()}, 'timeout': MAX_TIMEOOUT}
            response = httpx.get(url=key_uri, **client_params)
            response.raise_for_status()

            hex_content = binascii.hexlify(response.content).decode('utf-8')
            return bytes.fromhex(hex_content)
            
        except Exception as e:
            raise Exception(f"Failed to fetch key: {e}")
    
    def parse_data(self, m3u8_content: str) -> None:
        m3u8_parser = M3U8_Parser()
        m3u8_parser.parse_data(uri=self.url, raw_content=m3u8_content)

        self.expected_real_time_s = m3u8_parser.duration

        if m3u8_parser.keys:
            key = self.__get_key__(m3u8_parser)    
            self.decryption = M3U8_Decryption(
                key, 
                m3u8_parser.keys.get('iv'), 
                m3u8_parser.keys.get('method')
            )

        self.segments = [
            self.class_url_fixer.generate_full_url(seg)
            if "http" not in seg else seg
            for seg in m3u8_parser.segments
        ]
        self.class_ts_estimator.total_segments = len(self.segments)

    def get_info(self) -> None:
        if self.is_index_url:
            try:
                client_params = {'headers': {'User-Agent': get_userAgent()}, 'timeout': MAX_TIMEOOUT}
                response = httpx.get(self.url, **client_params)
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
        client_params = {
            'headers': {'User-Agent': get_userAgent()},
            'timeout': SEGMENT_MAX_TIMEOUT,
            'follow_redirects': True,
            'http2': False
        }
        return httpx.Client(**client_params)
                            
    def download_segment(self, ts_url: str, index: int, progress_bar: tqdm, backoff_factor: float = 1.1) -> None:
        """
        Downloads a TS segment and adds it to the segment queue with retry logic.

        Parameters:
            - ts_url (str): The URL of the TS segment.
            - index (int): The index of the segment.
            - progress_bar (tqdm): Progress counter for tracking download progress.
            - backoff_factor (float): The backoff factor for exponential backoff (default is 1.5 seconds).
        """
        for attempt in range(REQUEST_MAX_RETRY):
            if self.interrupt_flag.is_set():
                return
            
            try:
                with self._get_http_client() as client:
                    start_time = time.time()
                    response = client.get(ts_url)
        
                    # Validate response and content
                    response.raise_for_status()
                    segment_content = response.content
                    content_size = len(segment_content)
                    duration = time.time() - start_time

                    # Decrypt if needed and verify decrypted content
                    if self.decryption is not None:
                        try:
                            segment_content = self.decryption.decrypt(segment_content)
                            
                        except Exception as e:
                            logging.error(f"Decryption failed for segment {index}: {str(e)}")
                            self.interrupt_flag.set()   # Interrupt the download process
                            self.stop_event.set()       # Trigger the stopping event for all threads
                            break                       # Stop the current task immediately

                    self.class_ts_estimator.update_progress_bar(content_size, duration, progress_bar)
                    self.queue.put((index, segment_content))
                    self.downloaded_segments.add(index)  
                    progress_bar.update(1)
                    return

            except Exception as e:
                logging.info(f"Attempt {attempt + 1} failed for segment {index} - '{ts_url}': {e}")
                
                if attempt > self.info_maxRetry:
                    self.info_maxRetry = ( attempt + 1 )
                self.info_nRetry += 1

                if attempt + 1 == REQUEST_MAX_RETRY:
                    console.log(f"[red]Final retry failed for segment: {index}")
                    self.queue.put((index, None))  # Marker for failed segment
                    progress_bar.update(1)
                    self.info_nFailed += 1
                    return
                
                with self.active_retries_lock:
                    self.active_retries += 1
                
                sleep_time = backoff_factor * (2 ** attempt)
                logging.info(f"Retrying segment {index} in {sleep_time} seconds...")
                time.sleep(sleep_time)
                
                with self.active_retries_lock:
                    self.active_retries -= 1

    def write_segments_to_file(self):
        """
        Writes segments to file with additional verification.
        """
        buffer = {}
        expected_index = 0
        
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
                        if index == expected_index:
                            expected_index += 1
                        continue

                    # Write segment if it's the next expected one
                    if index == expected_index:
                        f.write(segment_content)
                        f.flush()
                        expected_index += 1

                        # Write any buffered segments that are now in order
                        while expected_index in buffer:
                            next_segment = buffer.pop(expected_index)

                            if next_segment is not None:
                                f.write(next_segment)
                                f.flush()

                            expected_index += 1
                    
                    else:
                        buffer[index] = segment_content

                except queue.Empty:
                    self.current_timeout = min(MAX_TIMEOOUT, self.current_timeout * 1.1)
                    time.sleep(0.05)

                    if self.stop_event.is_set():
                        break

                except Exception as e:
                    logging.error(f"Error writing segment {index}: {str(e)}")
    
    def download_streams(self, description: str, type: str):
        """
        Downloads all TS segments in parallel and writes them to a file.

        Parameters:
            - description: Description to insert on tqdm bar
            - type (str): Type of download: 'video' or 'audio'
        """
        if TELEGRAM_BOT:

          # Viene usato per lo screen 
          console.log("####")
          
        self.get_info()
        self.setup_interrupt_handler()

        progress_bar = tqdm(
            total=len(self.segments), 
            unit='s',
            ascii='░▒█',
            bar_format=self._get_bar_format(description),
            mininterval=0.6,
            maxinterval=1.0,
            file=sys.stdout,        # Using file=sys.stdout to force in-place updates because sys.stderr may not support carriage returns in this environment.
        )

        try:
            writer_thread = threading.Thread(target=self.write_segments_to_file)
            writer_thread.daemon = True
            writer_thread.start()

            # Configure workers and delay
            max_workers = self._get_worker_count(type)
            
            # Download segments with completion verification
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = []
                for index, segment_url in enumerate(self.segments):

                    # Check for interrupt before submitting each task
                    if self.interrupt_flag.is_set():
                        break

                    time.sleep(TQDM_DELAY_WORKER)
                    futures.append(executor.submit(self.download_segment, segment_url, index, progress_bar))

                # Wait for futures with interrupt handling
                for future in as_completed(futures):
                    if self.interrupt_flag.is_set():
                        break
                    try:
                        future.result()
                    except Exception as e:
                        logging.error(f"Error in download thread: {str(e)}")

                # Interrupt handling for missing segments
                if not self.interrupt_flag.is_set():
                    total_segments = len(self.segments)
                    completed_segments = len(self.downloaded_segments)
                    
                    if completed_segments < total_segments:
                        missing_segments = set(range(total_segments)) - self.downloaded_segments
                        logging.warning(f"Missing segments: {sorted(missing_segments)}")
                        
                        # Retry missing segments with interrupt check
                        for index in missing_segments:
                            if self.interrupt_flag.is_set():
                                break

                            try:
                                self.download_segment(self.segments[index], index, progress_bar)
                                
                            except Exception as e:
                                logging.error(f"Failed to retry segment {index}: {str(e)}")

        finally:
            self._cleanup_resources(writer_thread, progress_bar)

        if not self.interrupt_flag.is_set():
            self._verify_download_completion()

        return self._generate_results(type)
    
    def _get_bar_format(self, description: str) -> str:
        """
        Generate platform-appropriate progress bar format.
        """
        if not get_use_large_bar():
            return (
                f"{Colors.YELLOW}Proc{Colors.WHITE}: "
                f"{Colors.RED}{{percentage:.2f}}% "
                f"{Colors.CYAN}{{remaining}}{{postfix}} {Colors.WHITE}]"
            )
            
        else:
            return (
                f"{Colors.YELLOW}[HLS] {Colors.WHITE}({Colors.CYAN}{description}{Colors.WHITE}): "
                f"{Colors.RED}{{percentage:.2f}}% "
                f"{Colors.MAGENTA}{{bar}} "
                f"{Colors.YELLOW}{{elapsed}}{Colors.WHITE} < {Colors.CYAN}{{remaining}}{Colors.WHITE}{{postfix}}{Colors.WHITE}"
            )
    
    def _get_worker_count(self, stream_type: str) -> int:
        """
        Calculate optimal parallel workers based on stream type and infrastructure.
        """
        base_workers = {
            'video': DEFAULT_VIDEO_WORKERS,
            'audio': DEFAULT_AUDIO_WORKERS
        }.get(stream_type.lower(), 1)

        return base_workers
    
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
        
        #if self.download_interrupted:
        #    console.print("\n[red]Download terminated by user")
            
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