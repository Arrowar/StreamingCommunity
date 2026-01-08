# 10.01.26

import os
import logging
import subprocess
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse, urlunparse
from typing import Generator, Any, Optional, List, Dict


# Internal utilities
from StreamingCommunity.utils.config_json import config_manager


# Logic class
from .models import StreamInfo, DownloadConfig
from .parser import StreamParser
from .utils import FileUtils


# Variable
CHECK_SEGMENTS_COUNT = config_manager.config.get_bool("M3U8_DOWNLOAD", "check_segments_count")


class N_m3u8DLWrapper:
    def __init__(self, config: DownloadConfig, output_dir: Path):
        self.config = config
        self.output_dir = output_dir
        self.log_path = output_dir / "log.txt" if config.enable_logging else None
        self.raw_manifest_path = None  # Path to raw.mpd or raw.m3u8
    
    def _log(self, message: str, label: str = "INFO"):
        if not self.config.enable_logging or not self.log_path:
            return
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] {label}: {message}\n")
    
    def _find_raw_manifest(self) -> Optional[str]:
        """Find raw manifest file (raw.m3u8 or raw.mpd) in temp_analysis folder"""
        temp_analysis = self.output_dir / "temp_analysis"
        
        if not temp_analysis.exists():
            return None
        
        # Look for raw.m3u8 or raw.mpd
        for ext in ['.m3u8', '.mpd']:
            raw_file = temp_analysis / f"raw{ext}"
            if raw_file.exists():
                return str(raw_file.resolve())
        
        return None
    
    def _extract_base_url(self, url: str) -> str:
        """Extract base URL preserving all parameters except the manifest filename"""
        try:
            parsed = urlparse(url)
            
            # Get the path and remove the last component (manifest filename)
            path_parts = parsed.path.rstrip('/').split('/')
            if path_parts and any(ext in path_parts[-1].lower() for ext in ['.m3u8', '.mpd']):
                base_path = '/'.join(path_parts[:-1])
                if base_path and not base_path.endswith('/'):
                    base_path += '/'
            else:
                base_path = parsed.path
                if not base_path.endswith('/'):
                    base_path += '/'
            
            # Reconstruct the URL with all original components except the modified path
            base_url = urlunparse((
                parsed.scheme,
                parsed.netloc, 
                base_path,
                parsed.params,
                parsed.query,  # Preserve query parameters
                parsed.fragment
            ))
            
            return base_url
            
        except Exception as e:
            self._log(f"Error extracting base URL: {e}", "WARN")
            return url.rsplit('/', 1)[0] + '/' if '/' in url else url
    
    def _attempt_download(self, command: List[str], filename: str, headers: Optional[Dict[str, str]] = None, decryption_keys: Optional[List[str]] = None) -> bool:
        """Attempt to download with the given command. Returns True if successful, False otherwise."""
        process = None
        try:
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=False, bufsize=0, creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0)
            
            buffer = []
            in_stream_list = False
            
            for line in iter(process.stdout.readline, b''):
                try:
                    output = line.decode('utf-8', errors='ignore').strip()
                except Exception:
                    output = str(line, errors='ignore').strip()
                
                if not output:
                    continue
                
                buffer.append(output)
                self._log(output, "OUTPUT")
                
                # Check for 404 errors early
                if "404" in output and "Not Found" in output:
                    self._log("404 error detected, download will fail", "WARN")
                
                # 1) Parse stream list
                if any(kw in output for kw in ["Extracted", "streams found", "Vid ", "Aud ", "Sub "]):
                    in_stream_list = True
                
                if in_stream_list and any(kw in output for kw in ["Selected streams:", "Start downloading"]):
                    in_stream_list = False
                
                # 2) Selected streams
                if "Selected streams:" in output:
                    pass
                
                # 3) Parse progress (optional for this method)
                if progress := StreamParser.parse_progress(output):
                    logging.info("Parsed progress: " + str(progress))
                    pass
            
            process.wait()
            
            if process.returncode != 0:
                error_lines = [line for line in buffer if any(kw in line for kw in ["ERROR", "WARN", "Failed", "404"])]
                error_msg = "\n".join(error_lines[-5:]) if error_lines else "Unknown error"
                self._log(f"Download attempt failed with exit code {process.returncode}: {error_msg}", "ERROR")
                return False
            
            return True
            
        except KeyboardInterrupt:
            self._log("Download interrupted by user", "WARN")
            if process and process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
            raise
        except Exception as e:
            self._log(f"Exception in download attempt: {e}", "ERROR")
            if process and process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
            return False
    
    def _attempt_download_with_progress(self, command: List[str], filename: str, headers: Optional[Dict[str, str]] = None, decryption_keys: Optional[List[str]] = None) -> Generator[Dict[str, Any], None, None]:
        """Attempt to download with progress updates. Yields status updates."""
        process = None
        try:
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=False, bufsize=0, creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0)
            
            buffer = []
            in_stream_list = False
            
            for line in iter(process.stdout.readline, b''):
                try:
                    output = line.decode('utf-8', errors='ignore').strip()
                except Exception:
                    output = str(line, errors='ignore').strip()
                
                if not output:
                    continue
                
                buffer.append(output)
                self._log(output, "OUTPUT")
                
                # Check for 404 errors and terminate immediately
                if "404" in output and "Not Found" in output:
                    self._log("404 error detected, terminating download immediately", "WARN")
                    process.terminate()
                    try:
                        process.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        process.kill()
                    yield {"status": "failed", "error": "404 Not Found - retry needed", "has_404": True}
                    return
                
                # 1) Parse stream list
                if any(kw in output for kw in ["Extracted", "streams found", "Vid ", "Aud ", "Sub "]):
                    in_stream_list = True
                
                if in_stream_list and any(kw in output for kw in ["Selected streams:", "Start downloading"]):
                    in_stream_list = False
                    yield {"status": "selected"}
                
                # 2) Selected streams
                if "Selected streams:" in output:
                    yield {"status": "selected", "selected_streams": []}
                
                # 3) Parse progress
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
                self._log(f"Download attempt failed with exit code {process.returncode}: {error_msg}", "ERROR")
                yield {"status": "failed", "error": f"N_m3u8DL-RE failed with exit code {process.returncode}\n{error_msg}"}
                return
            
            # Download successful - find files and yield result
            result = FileUtils.find_downloaded_files(
                self.output_dir,
                filename,
                self.config.select_audio_lang[0] if isinstance(self.config.select_audio_lang, list) else self.config.select_audio_lang,
                self.config.select_subtitle_lang[0] if isinstance(self.config.select_subtitle_lang, list) else self.config.select_subtitle_lang
            )
            yield {"status": "completed", "result": result}
            
        except KeyboardInterrupt:
            self._log("Download interrupted by user", "WARN")
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
            self._log(f"Exception in download attempt: {e}", "ERROR")
            if process and process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
            yield {"status": "failed", "error": str(e)}
    
    def _build_command(self, url: str, filename: str, headers: Optional[Dict[str, str]] = None, decryption_keys: Optional[List[str]] = None, skip_download: bool = False, manifest_type: str = "UNKNOWN") -> List[str]:
        # Use absolute paths to avoid issues with relative path resolution
        output_dir_abs = str(Path(self.output_dir).resolve())
        
        if skip_download:
            command = [
                self.config.n_m3u8dl_path, url, "--save-name", filename, "--save-dir", output_dir_abs, "--tmp-dir", output_dir_abs, "--skip-download", "--auto-select", "--write-meta-json"
            ]
        else:
            command = [
                self.config.n_m3u8dl_path, url, "--save-name", filename, "--save-dir", output_dir_abs, "--tmp-dir", output_dir_abs, "--thread-count", str(self.config.thread_count), "--download-retry-count", str(self.config.retry_count),
                "--no-log", "--check-segments-count", "false", "--binary-merge", "--del-after-done"
            ]
            
            if self.config.concurrent_download:
                command.append("-mt")
            
            # 1) Select video
            if self.config.set_resolution == "best":
                command.extend(["--select-video", "best"])
            elif self.config.set_resolution == "worst":
                command.extend(["--select-video", "worst"])
            elif self.config.set_resolution.isdigit():
                command.extend(["--select-video", f"res=*{self.config.set_resolution}*:for=best"])
            else:
                command.extend(["--select-video", "best"])
            
            # 2) Select audio
            if self.config.select_audio_lang:
                audio_langs = self.config.select_audio_lang if isinstance(self.config.select_audio_lang, list) else [self.config.select_audio_lang]
                
                # Case 1: select all audio
                if len(audio_langs) == 1 and audio_langs[0].lower() == "all":
                    command.extend(["--select-audio", "all"])

                # Case 2: multiple audio languages
                elif len(audio_langs) > 1:
                    audio_lang = "|".join(audio_langs)
                    command.extend(["--select-audio", f"lang={audio_lang}:for=best{len(audio_langs)}"])
                
                # Case 3: single audio language
                else:
                    command.extend(["--select-audio", f"lang={audio_langs[0]}"])

            else:
                command.append("--drop-audio")
            
            # 3) Select subtitles
            if self.config.select_subtitle_lang:
                subtitle_langs = self.config.select_subtitle_lang if isinstance(self.config.select_subtitle_lang, list) else [self.config.select_subtitle_lang]
                
                # Case 1: select all subtitles
                if len(subtitle_langs) == 1 and subtitle_langs[0].lower() == "all":
                    command.extend(["--select-subtitle", "all"])

                # Case 2: multiple subtitle languages
                elif len(subtitle_langs) > 1:
                    subtitle_lang = "|".join(subtitle_langs)
                    if self.config.select_forced_subtitles:
                        command.extend(["--select-subtitle", f"lang={subtitle_lang}:name=.*[Ff]orced.*:for=all"])
                    else:
                        command.extend(["--select-subtitle", f"lang={subtitle_lang}:name=^(?!.*[Ff]orced)(?!.*\\[CC\\]).*$:for=all"])

                # Case 3: single subtitle language with forced option or CC exclusion
                else:
                    subtitle_lang = subtitle_langs[0]
                    if self.config.select_forced_subtitles:
                        command.extend(["--select-subtitle", f"lang={subtitle_lang}:name=.*[Ff]orced.*"])
                    else:
                        command.extend(["--select-subtitle", f"lang={subtitle_lang}:name=^(?!.*[Ff]orced)(?!.*\\[CC\\]).*$:for=best"])
            
            # 4) Decryption keys
            if decryption_keys:
                for key in decryption_keys:
                    command.append(f"--key={key}")
            
            # 5) mp4decrypt path
            if self.config.mp4decrypt_path:
                command.extend(["--decryption-binary-path", self.config.mp4decrypt_path])

            # 6) Max speed 
            if self.config.max_speed:
                command.extend(["--max-speed", str(self.config.max_speed)])
        
        # 7) Headers
        if headers:
            for key, value in headers.items():
                command.extend(["-H", f"{key}: {value}"])
        
        return command
    
    def get_available_streams(self, url: str, headers: Optional[Dict[str, str]] = None) -> Optional[StreamInfo]:
        """Get available streams without downloading"""
        command = self._build_command(url, "temp_analysis", headers, skip_download=True)
        self._log(" ".join(command), "COMMAND")
        
        try:
            #print("1) Call to get available streams with command: " + " ".join(command))
            result = subprocess.run(
                command,
                capture_output=True,
                text=False,
                timeout=15,
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
            
            # Try to parse from meta.json file first
            meta_path = os.path.join(self.output_dir, "temp_analysis", "meta.json")
            
            if os.path.exists(meta_path):
                manifest_type_hint = None
                raw_mpd = os.path.join(self.output_dir, "temp_analysis", "raw.mpd")
                raw_m3u8 = os.path.join(self.output_dir, "temp_analysis", "raw.m3u8")
                
                if os.path.exists(raw_mpd):
                    manifest_type_hint = "DASH"
                elif os.path.exists(raw_m3u8):
                    manifest_type_hint = "HLS"
                
                stream_info = StreamParser.parse_stream_info_from_json(Path(meta_path), manifest_type_hint)
                return stream_info if stream_info.streams else None
            
            return None
            
        except Exception as e:
            self._log(str(e), "ERROR")
            return None
    
    def download(self, url: str, filename: str, headers: Optional[Dict[str, str]] = None, decryption_keys: Optional[List[str]] = None, stream_info: Optional[StreamInfo] = None) -> Generator[Dict[str, Any], None, None]:
        """Download the media and yield progress updates"""
        
        # Use provided stream_info or get it if not available
        if stream_info is None:
            stream_info = self.get_available_streams(url, headers)

        manifest_type = stream_info.manifest_type if stream_info else "UNKNOWN"
        
        # Check if we should use raw file or go directly to original URL
        use_raw_file = self.config.use_raw_forDownload
        raw_manifest = self._find_raw_manifest() if use_raw_file else None
        
        # Build command based on configuration
        if use_raw_file and raw_manifest:
            input_source = raw_manifest
            
            # Extract base URL preserving all parameters
            base_url = self._extract_base_url(url)
            self._log(f"Using raw file with base URL: {base_url}", "INFO")

            # Build command with base-url
            command = self._build_command(input_source, filename, headers, decryption_keys, manifest_type=manifest_type)
            command.insert(2, "--base-url")
            command.insert(3, base_url)
        
        else:
            self._log(f"Using original URL for download: {url}", "INFO")
            command = self._build_command(url, filename, headers, decryption_keys, manifest_type=manifest_type)
        
        self._log(" ".join(command), "DOWNLOAD_START")
        yield {"status": "starting"}
        
        try:
            # First attempt
            for update in self._attempt_download_with_progress(command, filename, headers, decryption_keys):
                yield update
                if update.get("status") == "completed":
                    return
                
                elif update.get("status") == "failed":
                    if update.get("has_404", False) and use_raw_file and raw_manifest:
                        self._log("404 error detected, switching to original URL immediately", "INFO")
                        yield {"status": "retrying"}
                        
                        # Switch to original URL
                        command = self._build_command(url, filename, headers, decryption_keys, manifest_type=manifest_type)
                        self._log(" ".join(command), "DOWNLOAD_RETRY")
                        
                        # Try with original URL
                        for retry_update in self._attempt_download_with_progress(command, filename, headers, decryption_keys):
                            yield retry_update
                            if retry_update.get("status") == "completed":
                                return
                        
                        # If retry also failed, give up
                        yield {"status": "failed", "error": "Both raw manifest and original URL failed"}
                        return
                    else:
                        # No retry needed or possible
                        return
            
            # If we reach here without explicit completion/failure, something went wrong
            yield {"status": "failed", "error": "Download completed without status"}

        except KeyboardInterrupt:
            self._log("Cancelled by user", "CANCEL")
            yield {"status": "cancelled"}
            raise

        except Exception as e:
            self._log(str(e), "EXCEPTION")
            yield {"status": "failed", "error": str(e)}
            raise