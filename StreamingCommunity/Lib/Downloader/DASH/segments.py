# 25.07.25

import os
import asyncio
import time


# External libraries
import httpx
from tqdm import tqdm
from rich.console import Console


# Internal utilities
from StreamingCommunity.Util.headers import get_userAgent
from StreamingCommunity.Lib.M3U8.estimator import M3U8_Ts_Estimator
from StreamingCommunity.Util.config_json import config_manager
from StreamingCommunity.Util.color import Colors


# Config
REQUEST_MAX_RETRY = config_manager.get_int('REQUESTS', 'max_retry')
DEFAULT_VIDEO_WORKERS = config_manager.get_int('M3U8_DOWNLOAD', 'default_video_workers')
DEFAULT_AUDIO_WORKERS = config_manager.get_int('M3U8_DOWNLOAD', 'default_audio_workers')
SEGMENT_MAX_TIMEOUT = config_manager.get_int("M3U8_DOWNLOAD", "segment_timeout")
LIMIT_SEGMENT = config_manager.get_int('M3U8_DOWNLOAD', 'limit_segment')
ENABLE_RETRY = config_manager.get_bool('M3U8_DOWNLOAD', 'enable_retry')


# Variable
console = Console()


class MPD_Segments:
    def __init__(self, tmp_folder: str, representation: dict, pssh: str = None, limit_segments: int = None):
        """
        Initialize MPD_Segments with temp folder, representation, optional pssh, and segment limit.
        
        Parameters:
            - tmp_folder (str): Temporary folder to store downloaded segments
            - representation (dict): Selected representation with segment URLs
            - pssh (str, optional): PSSH string for decryption
            - limit_segments (int, optional): Optional limit for number of segments to download
        """
        self.tmp_folder = tmp_folder
        self.selected_representation = representation
        self.pssh = pssh
        
        # Use LIMIT_SEGMENT from config if limit_segments is not specified or is 0
        if limit_segments is None or limit_segments == 0:
            self.limit_segments = LIMIT_SEGMENT if LIMIT_SEGMENT > 0 else None
        else:
            self.limit_segments = limit_segments
        
        self.enable_retry = ENABLE_RETRY
        self.download_interrupted = False
        self.info_nFailed = 0
        
        # OTHER INFO
        self.downloaded_segments = set()
        self.info_maxRetry = 0
        self.info_nRetry = 0
        
        # Progress
        self._last_progress_update = 0
        self._progress_update_interval = 0.1
        
        # Segment tracking
        self.segment_files = {}
        self.segments_lock = asyncio.Lock()

    def get_concat_path(self, output_dir: str = None):
        """
        Get the path for the concatenated output file.
        """
        rep_id = self.selected_representation['id']
        return os.path.join(output_dir or self.tmp_folder, f"{rep_id}_encrypted.m4s")
        
    def get_segments_count(self) -> int:
        """
        Returns the total number of segments available in the representation.
        """
        return len(self.selected_representation.get('segment_urls', []))

    def download_streams(self, output_dir: str = None, description: str = "DASH"):
        """
        Synchronous wrapper for download_segments, compatible with legacy calls.
        
        Parameters:
            - output_dir (str): Output directory for segments
            - description (str): Description for progress bar (e.g., "Video", "Audio Italian")
        """
        concat_path = self.get_concat_path(output_dir)

        # Apply segment limit if specified
        if self.limit_segments is not None:
            orig_count = len(self.selected_representation.get('segment_urls', []))
            if orig_count > self.limit_segments:

                # Limit segment URLs
                self.selected_representation['segment_urls'] = self.selected_representation['segment_urls'][:self.limit_segments]

        # Run async download in sync mode
        try:
            asyncio.run(self.download_segments(output_dir=output_dir, description=description))

        except KeyboardInterrupt:
            self.download_interrupted = True
            console.print("\n[red]Download interrupted by user (Ctrl+C).")

        return {
            "concat_path": concat_path,
            "representation_id": self.selected_representation['id'],
            "pssh": self.pssh
        }

    async def download_segments(self, output_dir: str = None, concurrent_downloads: int = None, description: str = "DASH"):
        """
        Download and concatenate all segments (including init) asynchronously and in order.
        
        Parameters:
            - output_dir (str): Output directory for segments
            - concurrent_downloads (int): Number of concurrent downloads
            - description (str): Description for progress bar (e.g., "Video", "Audio Italian")
        """
        rep = self.selected_representation
        rep_id = rep['id']
        segment_urls = rep['segment_urls']
        init_url = rep.get('init_url')

        os.makedirs(output_dir or self.tmp_folder, exist_ok=True)
        concat_path = os.path.join(output_dir or self.tmp_folder, f"{rep_id}_encrypted.m4s")
        
        temp_dir = os.path.join(output_dir or self.tmp_folder, f"{rep_id}_segments")
        os.makedirs(temp_dir, exist_ok=True)

        # Determine stream type (video/audio) for progress bar
        stream_type = description
        if concurrent_downloads is None:
            worker_type = 'video' if 'Video' in description else 'audio'
            concurrent_downloads = self._get_worker_count(worker_type)

        progress_bar = tqdm(
            total=len(segment_urls) + 1,
            desc=f"Downloading {rep_id}",
            bar_format=self._get_bar_format(stream_type)
        )

        # Define semaphore for concurrent downloads
        semaphore = asyncio.Semaphore(concurrent_downloads)

        # Initialize estimator
        estimator = M3U8_Ts_Estimator(total_segments=len(segment_urls) + 1)

        self.segment_files = {}
        self.downloaded_segments = set()
        self.info_nFailed = 0
        self.download_interrupted = False
        self.info_nRetry = 0
        self.info_maxRetry = 0

        try:
            timeout_config = httpx.Timeout(SEGMENT_MAX_TIMEOUT, connect=10.0)
            limits = httpx.Limits(max_keepalive_connections=20, max_connections=100)
            
            async with httpx.AsyncClient(timeout=timeout_config, limits=limits) as client:
                
                # Download init segment
                await self._download_init_segment(client, init_url, concat_path, estimator, progress_bar)

                # Download all segments (first batch) - writes to temp files
                await self._download_segments_batch(
                    client, segment_urls, temp_dir, semaphore, REQUEST_MAX_RETRY, estimator, progress_bar
                )

                # Retry failed segments only if enabled
                if self.enable_retry:
                    await self._retry_failed_segments(
                        client, segment_urls, temp_dir, semaphore, REQUEST_MAX_RETRY, estimator, progress_bar
                    )

                # Concatenate all segment files in order
                await self._concatenate_segments(concat_path, len(segment_urls))

        except KeyboardInterrupt:
            self.download_interrupted = True
            console.print("\n[red]Download interrupted by user (Ctrl+C).")

        finally:
            self._cleanup_resources(temp_dir, progress_bar)

        self._verify_download_completion()
        return self._generate_results(stream_type)

    async def _download_init_segment(self, client, init_url, concat_path, estimator, progress_bar):
        """
        Download the init segment and update progress/estimator.
        """
        if not init_url:
            with open(concat_path, 'wb') as outfile:
                pass
            return
        
        try:
            headers = {'User-Agent': get_userAgent()}
            response = await client.get(init_url, headers=headers, follow_redirects=True)

            with open(concat_path, 'wb') as outfile:
                if response.status_code == 200:
                    outfile.write(response.content)
                    estimator.add_ts_file(len(response.content))

            progress_bar.update(1)
            self._throttled_progress_update(len(response.content), estimator, progress_bar)

        except Exception as e:
            progress_bar.close()
            raise RuntimeError(f"Error downloading init segment: {e}")

    def _throttled_progress_update(self, content_size: int, estimator, progress_bar):
        """
        Throttled progress update to reduce CPU usage.
        """
        current_time = time.time()
        if current_time - self._last_progress_update > self._progress_update_interval:
            estimator.update_progress_bar(content_size, progress_bar)
            self._last_progress_update = current_time

    async def _download_segments_batch(self, client, segment_urls, temp_dir, semaphore, max_retry, estimator, progress_bar):
        """
        Download a batch of segments and write them to temp files immediately.
        """
        async def download_single(url, idx):
            async with semaphore:
                headers = {'User-Agent': get_userAgent()}
                
                for attempt in range(max_retry):
                    if self.download_interrupted:
                        return idx, False, attempt
                        
                    try:
                        timeout = min(SEGMENT_MAX_TIMEOUT, 10 + attempt * 3)
                        resp = await client.get(url, headers=headers, follow_redirects=True, timeout=timeout)

                        # Write to temp file immediately
                        if resp.status_code == 200:
                            temp_file = os.path.join(temp_dir, f"seg_{idx:06d}.tmp")
                            async with self.segments_lock:
                                with open(temp_file, 'wb') as f:
                                    f.write(resp.content)
                                self.segment_files[idx] = temp_file
                            
                            return idx, True, attempt, len(resp.content)
                        else:
                            if attempt < 2:
                                sleep_time = 0.5 + attempt * 0.5
                            else:
                                sleep_time = min(2.0, 1.1 * (2 ** attempt))
                            await asyncio.sleep(sleep_time)
                            
                    except Exception:
                        sleep_time = min(2.0, 1.1 * (2 ** attempt))
                        await asyncio.sleep(sleep_time)
                        
                return idx, False, max_retry, 0

        # Initial download attempt
        tasks = [download_single(url, i) for i, url in enumerate(segment_urls)]

        for coro in asyncio.as_completed(tasks):
            try:
                idx, success, nretry, size = await coro
                
                if success:
                    self.downloaded_segments.add(idx)
                else:
                    self.info_nFailed += 1
                
                if nretry > self.info_maxRetry:
                    self.info_maxRetry = nretry
                self.info_nRetry += nretry
                    
                progress_bar.update(1)
                estimator.add_ts_file(size)
                self._throttled_progress_update(size, estimator, progress_bar)

            except KeyboardInterrupt:
                self.download_interrupted = True
                print("\n[red]Download interrupted by user (Ctrl+C).")
                break

    async def _retry_failed_segments(self, client, segment_urls, temp_dir, semaphore, max_retry, estimator, progress_bar):
        """
        Retry failed segments up to 3 times.
        """
        max_global_retries = 3
        global_retry_count = 0

        while self.info_nFailed > 0 and global_retry_count < max_global_retries and not self.download_interrupted:
            failed_indices = [i for i in range(len(segment_urls)) if i not in self.downloaded_segments]
            if not failed_indices:
                break
            
            async def download_single(url, idx):
                async with semaphore:
                    headers = {'User-Agent': get_userAgent()}

                    for attempt in range(max_retry):
                        if self.download_interrupted:
                            return idx, False, attempt, 0
                            
                        try:
                            timeout = min(SEGMENT_MAX_TIMEOUT, 15 + attempt * 5)
                            resp = await client.get(url, headers=headers, timeout=timeout)
                            
                            # Write to temp file immediately
                            if resp.status_code == 200:
                                temp_file = os.path.join(temp_dir, f"seg_{idx:06d}.tmp")
                                async with self.segments_lock:
                                    with open(temp_file, 'wb') as f:
                                        f.write(resp.content)
                                    self.segment_files[idx] = temp_file
                                
                                return idx, True, attempt, len(resp.content)
                            else:
                                await asyncio.sleep(1.5 * (2 ** attempt))

                        except Exception:
                            await asyncio.sleep(1.5 * (2 ** attempt))
                            
                return idx, False, max_retry, 0

            retry_tasks = [download_single(segment_urls[i], i) for i in failed_indices]

            nFailed_this_round = 0
            for coro in asyncio.as_completed(retry_tasks):
                try:
                    idx, success, nretry, size = await coro

                    if success:
                        self.downloaded_segments.add(idx)
                    else:
                        nFailed_this_round += 1

                    if nretry > self.info_maxRetry:
                        self.info_maxRetry = nretry
                    self.info_nRetry += nretry
                    
                    progress_bar.update(0)
                    estimator.add_ts_file(size)
                    self._throttled_progress_update(size, estimator, progress_bar)

                except KeyboardInterrupt:
                    self.download_interrupted = True
                    console.print("\n[red]Download interrupted by user (Ctrl+C).")
                    break
                    
            self.info_nFailed = nFailed_this_round
            global_retry_count += 1

    async def _concatenate_segments(self, concat_path, total_segments):
        """
        Concatenate all segment files in order to the final output file.
        Skip missing segments and continue with available ones.
        """
        successful_segments = 0
        with open(concat_path, 'ab') as outfile:
            for idx in range(total_segments):
                if idx in self.segment_files:
                    temp_file = self.segment_files[idx]
                    if os.path.exists(temp_file):
                        with open(temp_file, 'rb') as infile:
                            outfile.write(infile.read())
                        successful_segments += 1

    def _get_bar_format(self, description: str) -> str:
        """
        Generate platform-appropriate progress bar format.
        """
        return (
            f"{Colors.YELLOW}DASH{Colors.CYAN} {description}{Colors.WHITE}: "
            f"{Colors.MAGENTA}{{bar:40}} "
            f"{Colors.LIGHT_GREEN}{{n_fmt}}{Colors.WHITE}/{Colors.CYAN}{{total_fmt}} {Colors.LIGHT_MAGENTA}TS {Colors.WHITE}"
            f"{Colors.DARK_GRAY}[{Colors.YELLOW}{{elapsed}}{Colors.WHITE} < {Colors.CYAN}{{remaining}}{Colors.DARK_GRAY}] "
            f"{Colors.WHITE}{{postfix}}"
        )

    def _get_worker_count(self, stream_type: str) -> int:
        """
        Calculate optimal parallel workers based on stream type and infrastructure.
        """
        base_workers = {
            'video': DEFAULT_VIDEO_WORKERS,
            'audio': DEFAULT_AUDIO_WORKERS
        }.get(stream_type.lower(), 2)
        return base_workers

    def _generate_results(self, stream_type: str) -> dict:
        """
        Package final download results.
        """
        return {
            'type': stream_type,
            'nFailed': getattr(self, 'info_nFailed', 0),
            'stopped': getattr(self, 'download_interrupted', False)
        }

    def _verify_download_completion(self) -> None:
        """
        Validate final download integrity - allow partial downloads.
        """
        total = len(self.selected_representation['segment_urls'])
        completed = getattr(self, 'downloaded_segments', set())

        if self.download_interrupted:
            return
        
        if total == 0:
            return
        
        completion_rate = len(completed) / total
        missing_count = total - len(completed)
        
        # Allow downloads with up to 30 missing segments or 90% completion rate
        if completion_rate >= 0.90 or missing_count <= 30:
            return
        
        else:
            missing = sorted(set(range(total)) - completed)
            console.print(f"[red]Missing segments: {missing[:10]}..." if len(missing) > 10 else f"[red]Missing segments: {missing}")

    def _cleanup_resources(self, temp_dir, progress_bar: tqdm) -> None:
        """
        Ensure resource cleanup and final reporting.
        """
        progress_bar.close()
        
        # Delete temp segment files
        if temp_dir and os.path.exists(temp_dir):
            try:
                for temp_file in self.segment_files.values():
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
                os.rmdir(temp_dir)

            except Exception as e:
                print(f"[yellow]Warning: Could not clean temp directory: {e}")
        
        if getattr(self, 'info_nFailed', 0) > 0:
            self._display_error_summary()
            
        # Clear memory
        self.segment_files = {}

    def _display_error_summary(self) -> None:
        """
        Generate final error report.
        """
        total_segments = len(self.selected_representation.get('segment_urls', []))
        failed_indices = [i for i in range(total_segments) if i not in self.downloaded_segments]
        successful_segments = len(self.downloaded_segments)

        console.print(f"[green]Download Summary: "
              f"[cyan]Max retries: [red]{getattr(self, 'info_maxRetry', 0)} [white]| "
              f"[cyan]Total retries: [red]{getattr(self, 'info_nRetry', 0)} [white]| "
              f"[cyan]Failed segments: [red]{getattr(self, 'info_nFailed', 0)} [white]| "
              f"[cyan]Failed indices: [red]{failed_indices}")