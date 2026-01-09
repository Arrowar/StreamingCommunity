# 10.01.26

import os
import subprocess
from datetime import datetime
from urllib.parse import urlparse, urlunparse
from typing import Generator, Any, Optional, List, Dict


# Internal utilities
from StreamingCommunity.utils import config_manager
from StreamingCommunity.setup import binary_paths


# Logic class
from .models import StreamInfo, DownloadConfig
from .parser import StreamParser
from .utils import FileUtils


# Variable
CHECK_SEGMENTS_COUNT = config_manager.config.get_bool("M3U8_DOWNLOAD", "check_segments_count")


class N_m3u8DLWrapper:
    def __init__(self, config: DownloadConfig, output_dir: str):
        self.config = config
        self.output_dir = output_dir
        self.log_path = os.path.join(output_dir, "log.txt") if config.enable_logging else None
        self.raw_manifest_path = None
    
    def _log(self, message: str, label: str = "INFO"):
        if not self.config.enable_logging or not self.log_path:
            return
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] {label}: {message}\n")
    
    def _find_raw_manifest(self) -> Optional[str]:
        """Find raw manifest file (raw.m3u8 or raw.mpd) in temp_analysis folder"""
        temp_analysis = os.path.join(self.output_dir, "temp_analysis")
        
        if not os.path.exists(temp_analysis):
            return None
        
        for ext in ['.m3u8', '.mpd']:
            raw_file = os.path.join(temp_analysis, f"raw{ext}")
            if os.path.exists(raw_file):
                return os.path.abspath(raw_file)
        
        return None
    
    def _extract_base_url(self, url: str) -> str:
        """Extract base URL preserving all parameters except the manifest filename"""
        try:
            parsed = urlparse(url)
            
            path_parts = parsed.path.rstrip('/').split('/')
            if path_parts and any(ext in path_parts[-1].lower() for ext in ['.m3u8', '.mpd']):
                base_path = '/'.join(path_parts[:-1])
                if base_path and not base_path.endswith('/'):
                    base_path += '/'
            else:
                base_path = parsed.path
                if not base_path.endswith('/'):
                    base_path += '/'
            
            return urlunparse((parsed.scheme, parsed.netloc, base_path, parsed.params, parsed.query, parsed.fragment))

        except Exception as e:
            self._log(f"Error extracting base URL: {e}", "WARN")
            return url.rsplit('/', 1)[0] + '/' if '/' in url else url
    
    def _build_command(self, url: str, filename: str, headers: Optional[Dict[str, str]] = None, decryption_keys: Optional[List[str]] = None, skip_download: bool = False) -> List[str]:
        """Build N_m3u8DL-RE command"""
        output_dir_abs = str(os.path.abspath(self.output_dir))
        
        if skip_download:
            command = [self.config.n_m3u8dl_path, url, "--save-name", filename, "--save-dir", output_dir_abs, "--tmp-dir", output_dir_abs, "--skip-download", "--auto-select", "--write-meta-json"]
        else:
            command = [self.config.n_m3u8dl_path, url, "--save-name", filename, "--save-dir", output_dir_abs, "--tmp-dir", output_dir_abs, "--thread-count", str(self.config.thread_count), "--download-retry-count", str(self.config.retry_count),  "--http-request-timeout", str(self.config.req_timeout),  "--no-log",  "--check-segments-count", str(CHECK_SEGMENTS_COUNT),  "--binary-merge",  "--del-after-done"]
            
            if binary_paths._detect_system().lower() == "linux":
                command.append("--force-ansi-console")
            
            if self.config.concurrent_download:
                command.append("-mt")
            
            # Select video
            if self.config.set_resolution == "best":
                command.extend(["--select-video", "best"])
            elif self.config.set_resolution == "worst":
                command.extend(["--select-video", "worst"])
            elif self.config.set_resolution.isdigit():
                command.extend(["--select-video", f"res=*{self.config.set_resolution}*:for=best"])
            else:
                command.extend(["--select-video", "best"])
            
            # Select audio
            if self.config.select_audio_lang:
                audio_langs = self.config.select_audio_lang if isinstance(self.config.select_audio_lang, list) else [self.config.select_audio_lang]
                
                if len(audio_langs) == 1 and audio_langs[0].lower() == "all":
                    command.extend(["--select-audio", "all"])
                elif len(audio_langs) > 1:
                    audio_lang = "|".join(audio_langs)
                    command.extend(["--select-audio", f"lang={audio_lang}:for=best{len(audio_langs)}"])
                else:
                    command.extend(["--select-audio", f"lang={audio_langs[0]}"])
            else:
                command.append("--drop-audio")
            
            # Select subtitles
            if self.config.select_subtitle_lang:
                subtitle_langs = self.config.select_subtitle_lang if isinstance(self.config.select_subtitle_lang, list) else [self.config.select_subtitle_lang]
                
                if len(subtitle_langs) == 1 and subtitle_langs[0].lower() == "all":
                    command.extend(["--select-subtitle", "all"])
                elif len(subtitle_langs) > 1:
                    subtitle_lang = "|".join(subtitle_langs)
                    if self.config.select_forced_subtitles:
                        command.extend(["--select-subtitle", f"lang={subtitle_lang}:name=.*[Ff]orced.*:for=all"])
                    else:
                        command.extend(["--select-subtitle", f"lang={subtitle_lang}:name=^(?!.*[Ff]orced)(?!.*\\[CC\\]).*$:for=all"])
                else:
                    subtitle_lang = subtitle_langs[0]
                    if self.config.select_forced_subtitles:
                        command.extend(["--select-subtitle", f"lang={subtitle_lang}:name=.*[Ff]orced.*"])
                    else:
                        command.extend(["--select-subtitle", f"lang={subtitle_lang}:name=^(?!.*[Ff]orced)(?!.*\\[CC\\]).*$:for=best"])
            
            # Decryption keys
            if decryption_keys:
                for key in decryption_keys:
                    command.append(f"--key={key}")
            
            # mp4decrypt path
            if self.config.mp4decrypt_path:
                command.extend(["--decryption-binary-path", self.config.mp4decrypt_path])

            # Max speed 
            if self.config.max_speed:
                command.extend(["--max-speed", str(self.config.max_speed)])
        
        # Headers
        if headers:
            for key, value in headers.items():
                command.extend(["-H", f"{key}: {value}"])
        
        return command
    
    def _run_command(self, command: List[str], timeout: Optional[int] = None) -> subprocess.CompletedProcess:
        """Run command and return result"""
        self._log(" ".join(command), "COMMAND")
        
        result = subprocess.run(
            command, capture_output=True, text=False, timeout=timeout, 
            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
        )
        
        try:
            stdout = result.stdout.decode('utf-8', errors='ignore')
        except Exception:
            stdout = str(result.stdout, errors='ignore')
        
        try:
            stderr = result.stderr.decode('utf-8', errors='ignore')
        except Exception:
            stderr = str(result.stderr, errors='ignore')
        
        self._log(stdout, "STDOUT")
        self._log(stderr, "STDERR")
        self._log(f"Return code: {result.returncode}", "STATUS")
        
        return result
    
    def get_available_streams(self, url: str, headers: Optional[Dict[str, str]] = None) -> Optional[StreamInfo]:
        """Get available streams without downloading"""
        command = self._build_command(url, "temp_analysis", headers, skip_download=True)
        meta_path = os.path.join(self.output_dir, "temp_analysis", "meta.json")
        
        try:
            process = subprocess.Popen(
                command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=False,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            
            # Wait for meta.json or process completion with timeout
            import time
            max_wait = 15
            start_time = time.time()
            
            while time.time() - start_time < max_wait:
                if os.path.exists(meta_path):
                    self._log("meta.json found, terminating process", "INFO")
                    process.terminate()
                    try:
                        process.wait(timeout=2)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait()
                    break
                
                if process.poll() is not None:
                    break
                
                time.sleep(0.1)
            else:
                self._log("Timeout waiting for meta.json", "WARN")
                if process.poll() is None:
                    process.terminate()
                    try:
                        process.wait(timeout=2)
                    except subprocess.TimeoutExpired:
                        process.kill()
            
            # Parse from meta.json file
            if os.path.exists(meta_path):
                manifest_type_hint = None
                raw_mpd = os.path.join(self.output_dir, "temp_analysis", "raw.mpd")
                raw_m3u8 = os.path.join(self.output_dir, "temp_analysis", "raw.m3u8")
                
                if os.path.exists(raw_mpd):
                    manifest_type_hint = "DASH"
                elif os.path.exists(raw_m3u8):
                    manifest_type_hint = "HLS"
                
                stream_info = StreamParser.parse_stream_info_from_json(meta_path, manifest_type_hint)
                return stream_info if stream_info.streams else None
            
            return None
            
        except Exception as e:
            self._log(str(e), "ERROR")
            return None
        
    def download(self, url: str, filename: str, headers: Optional[Dict[str, str]] = None, decryption_keys: Optional[List[str]] = None, stream_info: Optional[StreamInfo] = None) -> Generator[Dict[str, Any], None, None]:
        """Download the media and yield progress updates"""
        
        if stream_info is None:
            stream_info = self.get_available_streams(url, headers)
            yield {"status": "parsing", "stream_info": stream_info}
        else:
            self._log("Using pre-fetched stream info", "INFO")
            yield {"status": "parsing", "stream_info": stream_info}
        
        # Check if we should use raw file or original URL
        use_raw_file = self.config.use_raw_forDownload
        raw_manifest = self._find_raw_manifest() if use_raw_file else None
        
        # Build command
        if use_raw_file and raw_manifest:
            input_source = raw_manifest
            base_url = self._extract_base_url(url)
            self._log(f"Using raw file with base URL: {base_url}", "INFO")

            command = self._build_command(input_source, filename, headers, decryption_keys)
            command.insert(2, "--base-url")
            command.insert(3, base_url)
        else:
            self._log(f"Using original URL for download: {url}", "INFO")
            command = self._build_command(url, filename, headers, decryption_keys)
        
        self._log(" ".join(command), "DOWNLOAD_START")
        yield {"status": "starting"}
        
        # Execute download
        process = None
        buffer = []
        in_stream_list = False
        
        try:
            process = subprocess.Popen(
                command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=False, bufsize=0, 
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            
            for line in iter(process.stdout.readline, b''):
                try:
                    output = line.decode('utf-8', errors='ignore').strip()
                except Exception:
                    output = str(line, errors='ignore').strip()
                
                if not output:
                    continue
                
                buffer.append(output)
                self._log(output, "OUTPUT")
                
                # Check for 404 errors
                if "404" in output and "Not Found" in output:
                    self._log("404 error detected, terminating download", "WARN")
                    process.terminate()
                    try:
                        process.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        process.kill()
                    yield {"status": "failed", "error": "404 Not Found", "has_404": True}
                    return
                
                # Parse stream list
                if any(kw in output for kw in ["Extracted", "streams found", "Vid ", "Aud ", "Sub "]):
                    in_stream_list = True
                
                if in_stream_list and any(kw in output for kw in ["Selected streams:", "Start downloading"]):
                    in_stream_list = False
                    yield {"status": "selected"}
                
                # Selected streams
                if "Selected streams:" in output:
                    yield {"status": "selected", "selected_streams": []}
                
                # Parse progress
                if progress := StreamParser.parse_progress(output):
                    update = {"status": "downloading"}
                    if progress.stream_type == "Vid":
                        update["progress_video"] = progress
                    elif progress.stream_type == "Aud":
                        update["progress_audio"] = progress
                    yield update
            
            process.wait()
            
            if process.returncode != 0:
                error_lines = [line for line in buffer if any(kw in line for kw in ["ERROR", "WARN", "Failed", "404"])]
                error_msg = "\n".join(error_lines[-5:]) if error_lines else "Unknown error"
                self._log(f"Download failed with exit code {process.returncode}: {error_msg}", "ERROR")
                yield {"status": "failed", "error": f"N_m3u8DL-RE failed with exit code {process.returncode}\n{error_msg}"}
                return
            
            # Download successful
            result = FileUtils.find_downloaded_files(
                self.output_dir,
                filename,
                self.config.select_audio_lang[0] if isinstance(self.config.select_audio_lang, list) else self.config.select_audio_lang,
                self.config.select_subtitle_lang[0] if isinstance(self.config.select_subtitle_lang, list) else self.config.select_subtitle_lang
            )
            yield {"status": "completed", "result": result}
            
        except KeyboardInterrupt:
            self._log("Cancelled by user", "CANCEL")
            if process and process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
            yield {"status": "cancelled"}
            raise

        except Exception as e:
            self._log(str(e), "EXCEPTION")
            if process and process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
            yield {"status": "failed", "error": str(e)}
            raise