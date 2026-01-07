# 10.01.26

import os
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Generator, Any, Optional, List, Dict


# Internal utilities
from StreamingCommunity.Util.config_json import config_manager


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
        
        # Try to use local manifest file with base URL to avoid re-downloading the manifest
        input_source = url
        raw_manifest = self._find_raw_manifest()
        
        if raw_manifest:
            input_source = raw_manifest
            
            # Extract base URL from the original URL
            # This is the URL up to (and including) the last slash before the manifest filename
            base_url = url.rsplit('/', 1)[0] + '/' if '/' in url else url
            self._log(f"Base URL: {base_url}", "INFO")

            # Build command with base-url
            command = self._build_command(input_source, filename, headers, decryption_keys, manifest_type=manifest_type)
            command.insert(2, "--base-url")
            command.insert(3, base_url)
        
        else:
            self._log(f"Using original URL for download: {url}", "INFO")
            command = self._build_command(input_source, filename, headers, decryption_keys, manifest_type=manifest_type)
        self._log(" ".join(command), "DOWNLOAD_START")
        yield {"status": "starting"}
        
        process = None
        
        try:
            #print("2) Call to start download with command: " + " ".join(command))
            with subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=False,
                bufsize=0,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            ) as process:
                
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
                    error_lines = [line for line in buffer if any(kw in line for kw in ["ERROR", "WARN", "Failed"])]
                    error_msg = "\n".join(error_lines[-10:]) if error_lines else "Unknown error"
                    self._log(error_msg, "ERROR")
                    raise ValueError(f"N_m3u8DL-RE failed with exit code {process.returncode}\n{error_msg}")
                
                # 4) Get downloaded files
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
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
            yield {"status": "cancelled"}
            raise

        except Exception as e:
            self._log(str(e), "EXCEPTION")
            yield {"status": "failed", "error": str(e)}
            raise