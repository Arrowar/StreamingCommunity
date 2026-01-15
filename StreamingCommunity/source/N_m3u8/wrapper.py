# 04.01.25

import re
import subprocess
import asyncio
from pathlib import Path
from typing import Optional, List, Dict, Any


# External
import httpx
from rich.table import Table
from rich.console import Console
from rich.progress import Progress, TextColumn


# Interl 
from StreamingCommunity.utils.config import config_manager
from StreamingCommunity.utils import internet_manager
from StreamingCommunity.setup import get_ffmpeg_path, get_n_m3u8dl_re_path, get_bento4_decrypt_path


# Logic
from .object import StreamInfo
from .pattern import (VIDEO_LINE_RE, AUDIO_LINE_RE, SUBTITLE_LINE_RE, SEGMENT_RE, PERCENT_RE, SPEED_RE, SIZE_RE, SUBTITLE_FINAL_SIZE_RE)
from .progress_bar import CustomBarColumn, ColoredSegmentColumn, CompactTimeColumn, CompactTimeRemainingColumn, SizeColumn
from .parser import parse_meta_json, LogParser
from .utils import convert_size_to_bytes


# Variable
console = Console()
video_filter = config_manager.config.get("M3U8_DOWNLOAD", "select_video")
audio_filter = config_manager.config.get("M3U8_DOWNLOAD", "select_audio")
subtitle_filter = config_manager.config.get("M3U8_DOWNLOAD", "select_subtitle")
max_speed = config_manager.config.get("M3U8_DOWNLOAD", "max_speed")
check_segments_count = config_manager.config.get_bool("M3U8_DOWNLOAD", "check_segments_count")
concurrent_download = config_manager.config.get_int("M3U8_DOWNLOAD", "concurrent_download")
retry_count = config_manager.config.get_int("M3U8_DOWNLOAD", "retry_count")
request_timeout = config_manager.config.get_int("REQUESTS", "timeout")
thread_count = config_manager.config.get_int("M3U8_DOWNLOAD", "thread_count")
USE_PROXY = bool(config_manager.config.get_bool("REQUESTS", "use_proxy"))
CONF_PROXY = config_manager.config.get_dict("REQUESTS", "proxy") or {}


class MediaDownloader:
    def __init__(self, url: str, output_dir: str, filename: str, headers: Optional[Dict] = None, key: Optional[str] = None, cookies: Optional[Dict] = None):
        self.url = url
        self.output_dir = Path(output_dir)
        self.filename = filename
        self.headers = headers or {}
        self.key = key
        self.cookies = cookies or {}
        self.streams = []
        self.external_subtitles = []
        self.force_best_video = False           # Flag to force best video if no video selected
        self.meta_json_path, self.meta_selected_path, self.raw_m3u8, self.raw_mpd = None, None, None, None 
        self.status = None
        self.manifest_type = "Unknown"
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def parser_stream(self) -> List[StreamInfo]:
        """Analyze playlist and display table of available streams"""
        analysis_path = self.output_dir / "analysis_temp"
        analysis_path.mkdir(exist_ok=True)
        
        cmd = [
            get_n_m3u8dl_re_path(),
            self.url,
            "--write-meta-json", "true",
            "--no-log", "true",
            "--save-dir", str(analysis_path),
            "--tmp-dir", str(analysis_path),
            "--save-name", "temp_analysis",
            "--select-video", video_filter,
            "--select-audio", audio_filter,
            "--select-subtitle", subtitle_filter,
            "--skip-download"
        ]
        
        if self.headers:
            for k, v in self.headers.items():
                cmd.extend(["--header", f"{k}: {v}"])

        if self.cookies:
            cookie_str = "; ".join(f"{k}={v}" for k, v in self.cookies.items())
            if cookie_str:
                cmd.extend(["--header", f"Cookie: {cookie_str}"])
        
        if USE_PROXY:
            proxy_url = CONF_PROXY.get("https") or CONF_PROXY.get("http")
            if proxy_url:
                cmd.extend(["--use-system-proxy", "false", "--custom-proxy", proxy_url])

        console.print("[cyan]Analyzing playlist...")
        log_parser = LogParser()
        result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", timeout=30)
        
        # Parse stderr for warnings/errors
        for line in result.stderr.split('\n'):
            if line.strip():
                log_parser.parse_line(line)
        
        # Also parse stdout
        for line in result.stdout.split('\n'):
            if line.strip():
                log_parser.parse_line(line)
        
        analysis_dir = analysis_path / "temp_analysis"
        self.meta_json_path = analysis_dir / "meta.json"
        self.meta_selected_path = analysis_dir / "meta_selected.json"
        self.raw_m3u8 = analysis_dir / "raw.m3u8"
        self.raw_mpd = analysis_dir / "raw.mpd"
        
        # Determine manifest type
        self.manifest_type = "Unknown"
        if self.raw_mpd.exists():
            self.manifest_type = "DASH"
        elif self.raw_m3u8.exists():
            self.manifest_type = "HLS"
        
        if self.meta_json_path.exists():
            self.streams = parse_meta_json(str(self.meta_json_path), str(self.meta_selected_path))

            # If there are video streams but none were selected by the configured filter,
            # force `--select-video best` for the actual download to avoid downloading nothing.
            try:
                has_video = any(s.type == "Video" for s in self.streams)
                video_selected = any(s.type == "Video" and s.selected for s in self.streams)
                if has_video and not video_selected:
                    console.log("[yellow]No video matched select_video filter; forcing 'best' for download[/yellow]")
                    self.force_best_video = True
            except Exception:
                self.force_best_video = False
            
            # Add external subtitles to stream list
            for ext_sub in self.external_subtitles:

                # Determine selection for external subtitles based on `subtitle_filter` from config
                ext_lang = ext_sub.get('language', '') or ''
                selected = False
                try:

                    # Try to extract language tokens from the selection filter, e.g. lang='ita|eng|it|en'
                    lang_match = re.search(r"lang=['\"]([^'\"]+)['\"]", subtitle_filter or "")
                    if lang_match:
                        tokens = [t.strip() for t in lang_match.group(1).split('|') if t.strip()]
                        for t in tokens:
                            tl = t.lower()
                            el = ext_lang.lower()

                            # match exact, prefix (en -> en-US), or contained token
                            if not el:
                                continue
                            if tl == el or el.startswith(tl) or tl in el:
                                selected = True
                                break
                    
                    else:
                        # Fallback: try to match any simple alpha tokens found in the filter
                        simple_tokens = re.findall(r"[A-Za-z]{2,}", subtitle_filter or "")
                        for t in simple_tokens:
                            if t.lower() in ext_lang.lower():
                                selected = True
                                break
                
                except Exception:
                    selected = False

                # Persist selection and extension back to the external subtitle dict
                ext_type = ext_sub.get('type') or ext_sub.get('format') or 'srt'
                ext_sub['_selected'] = selected
                ext_sub['_ext'] = ext_type

                self.streams.append(StreamInfo(
                    type_="Subtitle [red]*EXT",
                    language=ext_sub.get('language', ''),
                    name=(ext_sub.get('type') or ext_sub.get('format') or 'External'),
                    selected=selected,
                    extension=ext_type
                ))
            
            self._display_stream_table()
            return self.streams
        
        return []

    def get_metadata(self) -> tuple:
        """Get paths to metadata files"""
        return str(self.meta_json_path), str(self.meta_selected_path), str(self.raw_m3u8), str(self.raw_mpd)
    
    def set_key(self, key: str):
        """Set decryption key"""
        self.key = key
    
    async def _download_external_subtitles(self):
        """Download external subtitles using httpx"""
        if not self.external_subtitles:
            return []
        
        downloaded = []
        async with httpx.AsyncClient(headers=self.headers, timeout=30.0) as client:
            for sub in self.external_subtitles:
                try:
                    # Skip external subtitles that were marked as not selected (default: True)
                    if not sub.get('_selected', True):
                        continue

                    url = sub['url']
                    lang = sub.get('language', 'unknown')
                    # Prefer previously resolved extension, then explicit 'type', then 'format', then fallback 'srt'
                    sub_type = sub.get('_ext') or sub.get('type') or sub.get('format') or 'srt'

                    # Create filename
                    sub_filename = f"{self.filename}.{lang}.{sub_type}"
                    sub_path = self.output_dir / sub_filename
                    
                    # Download
                    response = await client.get(url)
                    response.raise_for_status()
                    
                    # Save
                    with open(sub_path, 'wb') as f:
                        f.write(response.content)
                    
                    downloaded.append({
                        'path': str(sub_path),
                        'language': lang,
                        'type': sub_type,
                        'size': len(response.content)
                    })
                    
                except Exception as e:
                    console.log(f"[red]Failed to download external subtitle: {e}[/red]")
        
        return downloaded

    def start_download(self) -> Dict[str, Any]:
        """Start the download process with automatic retry on segment count mismatch"""
        log_parser = LogParser()
        select_video = ("best" if getattr(self, "force_best_video", False) else video_filter)
        cmd = [
            get_n_m3u8dl_re_path(),
            self.url,
            "--save-name", self.filename,
            "--save-dir", str(self.output_dir),
            "--tmp-dir", str(self.output_dir),
            "--ffmpeg-binary-path", get_ffmpeg_path(),
            "--decryption-binary-path", get_bento4_decrypt_path(),
            "--no-log",
            "--write-meta-json", "false",
            "--binary-merge", "true",
            "--del-after-done", "true",
            "--select-video", select_video,
            "--select-audio", audio_filter,
            "--select-subtitle", subtitle_filter,
            "--auto-subtitle-fix", "false"           # CON TRUE ALCUNE VOLTE NON SCARICATA TUTTI I SUB SELEZIONATI
        ]

        if concurrent_download:
            cmd.extend(["--concurrent-download", "true"])
        if thread_count > 0:
            cmd.extend(["--thread-count", str(thread_count)])
        if request_timeout > 0:
            cmd.extend(["--http-request-timeout", str(request_timeout)])
        if retry_count > 0:
            cmd.extend(["--download-retry-count", str(retry_count)])
        if max_speed:
            cmd.extend(["--max-speed", max_speed])
        if check_segments_count:
            cmd.extend(["--check-segments-count", "true"])
        
        # Add key if provided
        if self.key:
            for single_key in self.key:
                cmd.extend(["--key", single_key])
        
        # Add header
        if self.headers:
            for k, v in self.headers.items():
                cmd.extend(["--header", f"{k}: {v}"])

        if self.cookies:
            cookie_str = "; ".join(f"{k}={v}" for k, v in self.cookies.items())
            if cookie_str:
                cmd.extend(["--header", f"Cookie: {cookie_str}"])

        if USE_PROXY:
            proxy_url = CONF_PROXY.get("https") or CONF_PROXY.get("http")
            if proxy_url:
                cmd.extend(["--use-system-proxy", "false", "--custom-proxy", proxy_url])
        
        console.print("\n[cyan]Starting download...")
        
        # Download external subtitles in parallel
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        external_subs = loop.run_until_complete(self._download_external_subtitles())
        
        # Start main download
        log_parser = LogParser()
        log_path = self.output_dir / f"{self.filename}_download.log"
        subtitle_sizes = {}
        
        with open(log_path, 'w', encoding='utf-8') as log_file:
            log_file.write(f"Command: {' '.join(cmd)}\n{'='*80}\n\n")
            
            with Progress(
                TextColumn("[purple]{task.description}", justify="left"),
                CustomBarColumn(bar_width=40), ColoredSegmentColumn(),
                TextColumn("[dim][[/dim]"), CompactTimeColumn(), TextColumn("[dim]<[/dim]"), CompactTimeRemainingColumn(), TextColumn("[dim]][/dim]"),
                SizeColumn(),
                TextColumn("[dim]@[/dim]"), TextColumn("[red]{task.fields[speed]}[/red]", justify="right"),
                console=console,
            ) as progress:
                
                tasks = {}
                
                with subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8") as proc:
                    for line in proc.stdout:
                        line = line.rstrip()
                        if not line:
                            continue
                        
                        if line.strip():
                            log_parser.parse_line(line)
                        
                        log_file.write(line + "\n")
                        log_file.flush()
                        
                        # Parse for progress updates
                        self._parse_progress_line(line, progress, tasks, subtitle_sizes)
                        
                        # Check for segment count error
                        if "Segment count check not pass" in line:
                            console.log(f"[red]Segment count mismatch detected: {line}[/red]")
                    
                    proc.wait()
        
        # Get final status
        self.status = self._get_download_status(subtitle_sizes, external_subs)
        return self.status

    def _parse_progress_line(self, line: str, progress, tasks: dict, subtitle_sizes: dict):
        """Parse a progress line and update progress bars with better colors"""
        
        # 1) Video progress
        if line.startswith("Vid"):
            video_match = VIDEO_LINE_RE.search(line)

            if video_match:
                resolution = video_match.group(1)
            else:
                # Fallback: no resolution in meta; try to use first video stream info
                resolution = ""
                for s in self.streams:
                    if s.type == "Video":
                        resolution = s.resolution or s.extension or "main"
                        break

            task_key = f"video_{resolution}"

            if task_key not in tasks:
                display_res = resolution if resolution else "main"
                tasks[task_key] = progress.add_task(
                    f"[yellow]{self.manifest_type} [cyan]Vid [red]{display_res}",
                    total=100,
                    segment="0/0",
                    speed="0Bps",
                    size="0B/0B"
                )

            # Update progress
            task = tasks[task_key]

            # Get segment count
            if segment_match := SEGMENT_RE.search(line):
                progress.update(task, segment=segment_match.group(0))

            # Get percentage
            if percent_match := PERCENT_RE.search(line):
                try:
                    progress.update(task, completed=float(percent_match.group(1)))
                except Exception:
                    pass

            # Get speed
            if speed_match := SPEED_RE.search(line):
                progress.update(task, speed=speed_match.group(1))

            # Get size
            if size_match := SIZE_RE.search(line):
                current = size_match.group(1)
                total = size_match.group(2)
                progress.update(task, size=f"{current}/{total}")

        # 2) Audio progress
        elif line.startswith("Aud"):
            audio_match = AUDIO_LINE_RE.search(line)
            if audio_match:
                bitrate = audio_match.group(1).strip()
                language_or_name = audio_match.group(2).strip()
                
                # Determine what to display: prefer language, fallback to name
                display_name = language_or_name
                
                # Se l'audio è identificato solo per bitrate, cerchiamo il nome nella lista degli stream
                if not any(c.isalpha() for c in language_or_name):
                    for stream in self.streams:
                        if stream.type == "Audio" and stream.bandwidth and bitrate in stream.bandwidth:
                            if stream.language:
                                display_name = stream.language
                            elif stream.name:
                                display_name = stream.name
                            else:
                                display_name = bitrate
                            break
                    else:
                        display_name = bitrate
                
                task_key = f"audio_{language_or_name}_{bitrate.replace(' ', '_')}"
                
                if task_key not in tasks:
                    tasks[task_key] = progress.add_task(
                        f"[yellow]{self.manifest_type} [cyan]Aud [red]{display_name}",
                        total=100,
                        segment="0/0",
                        speed="0Bps",
                        size="0B/0B"
                    )
                
                task = tasks[task_key]
                
                # Get segment count
                if segment_match := SEGMENT_RE.search(line):
                    progress.update(task, segment=segment_match.group(0))
                
                if percent_match := PERCENT_RE.search(line):
                    progress.update(task, completed=float(percent_match.group(1)))
                
                if speed_match := SPEED_RE.search(line):
                    progress.update(task, speed=speed_match.group(1))
                
                if size_match := SIZE_RE.search(line):
                    current = size_match.group(1)
                    total = size_match.group(2)
                    progress.update(task, size=f"{current}/{total}")
        
        # 3) Subtitle progress
        elif line.startswith("Sub"):
            subtitle_match = SUBTITLE_LINE_RE.search(line)
            if subtitle_match:
                language_code = subtitle_match.group(1).strip()
                subtitle_name = subtitle_match.group(2).strip()
                task_key = f"sub_{language_code}_{subtitle_name.replace(' ', '_')}"
                display_name = f"{language_code}: {subtitle_name}"
                
                if task_key not in tasks:
                    tasks[task_key] = progress.add_task(
                        f"[yellow]{self.manifest_type} [cyan]Sub [red]{subtitle_name}",
                        total=100,
                        segment="0/0",
                        speed="0Bps",
                        size="0B/0B"
                    )
                
                task = tasks[task_key]
                
                # Get segment count
                if segment_match := SEGMENT_RE.search(line):
                    progress.update(task, segment=segment_match.group(0))
                
                if percent_match := PERCENT_RE.search(line):
                    progress.update(task, completed=float(percent_match.group(1)))
                
                # Capture final size
                if size_final_match := SUBTITLE_FINAL_SIZE_RE.search(line):
                    final_size = size_final_match.group(1)
                    progress.update(task, size=final_size, completed=100)
                    subtitle_sizes[display_name] = final_size
                elif size_match := SIZE_RE.search(line):
                    current = size_match.group(1)
                    total = size_match.group(2)
                    progress.update(task, size=f"{current}/{total}")
                else:
                    
                    # Try to extract size from the line pattern
                    size_match_simple = re.search(r"(\d+\.\d+(?:B|KB|MB|GB))\s*$", line)
                    if size_match_simple:
                        final_size = size_match_simple.group(1)
                        subtitle_sizes[display_name] = final_size

    def _display_stream_table(self):
        """Display streams in a rich table"""
        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("Type", style="cyan")
        table.add_column("Sel", style="green", justify="center")
        table.add_column("Resolution", style="yellow")
        table.add_column("Bitrate", style="yellow")
        table.add_column("Codec", style="green")
        table.add_column("Ext", style="magenta")
        table.add_column("Language", style="blue")
        table.add_column("Name", style="green")
        table.add_column("Duration", style="magenta")
        table.add_column("Segments", justify="right")
        
        for stream in self.streams:
            type_info = stream.type
            if stream.encrypted:
                type_info += " [red]*CENC"
            
            # Build resolution info
            if stream.type == "Video":
                resolution = stream.resolution
                if stream.bandwidth and stream.bandwidth != "0 bps":
                    bitrate = stream.bandwidth
                else:
                    bitrate = ""

            elif stream.type in ["Audio", "Subtitle", "Subtitle [red]*EXT"]:
                resolution = ""
                if stream.type == "Audio":
                    if stream.bandwidth and stream.bandwidth != "0 bps" and stream.bandwidth != "N/A":
                        bitrate = stream.bandwidth
                    else:
                        bitrate = ""
                else:
                    bitrate = ""
            else:
                resolution = ""
                bitrate = ""
            
            codec = stream.codec if stream.codec else ""
            ext = stream.extension if stream.extension else ""
            name = stream.name if stream.name else ""
            language = stream.language if stream.language else ""
            
            # Format duration from meta_selected.json
            if stream.total_duration > 0:
                duration = internet_manager.format_time(stream.total_duration, add_hours=True)
            else:
                duration = "N/A"
            
            table.add_row(
                type_info,
                "X" if stream.selected else "",
                resolution,
                bitrate,
                codec,
                ext,
                language,
                name,
                duration,
                str(stream.segment_count)
            )
        
        console.print(table)

    def _extract_language_from_filename(self, filename: str, base_name: str) -> str:
        """Extract language from filename by removing base name and extension"""
        if filename.startswith(base_name):
            stem = filename[len(base_name):].lstrip('.')
        else:
            stem = filename
        
        if '.' in stem:
            stem = stem.rsplit('.', 1)[0]
        
        parts = stem.split('.')
        return parts[0]

    def _get_download_status(self, subtitle_sizes: dict, external_subs: list) -> Dict[str, Any]:
        """Get final download status"""
        status = {
            'video': None, 
            'audios': [], 
            'subtitles': [],
            'external_subtitles': external_subs
        }
        
        video_extensions = ['.mp4', '.mkv', '.m4v', '.ts', '.mov']
        audio_extensions = ['.m4a', '.aac', '.mp3', '.ts', '.mp4', '.wav']
        subtitle_extensions = ['.srt', '.vtt', '.ass', '.sub', '.ssa']
        
        # Find video file
        for ext in video_extensions:
            main_file = self.output_dir / f"{self.filename}{ext}"
            if main_file.exists():
                status['video'] = {
                    'path': str(main_file),
                    'size': main_file.stat().st_size
                }
                break
        
        # Prepare subtitle size mapping
        subtitle_size_map = {}
        for display_name, size_str in subtitle_sizes.items():
            
            # Parse display name like "eng: English [CC]"
            if ':' in display_name:
                lang, name = display_name.split(':', 1)
                lang = lang.strip()
                name = name.strip()
            else:
                lang = display_name
                name = display_name
            
            size_bytes = convert_size_to_bytes(size_str)
            if size_bytes:
                key1 = (lang, name)
                key2 = (lang, name.lower())
                key3 = (lang, "")  # Just language
                
                subtitle_size_map[key1] = (name, size_bytes)
                subtitle_size_map[key2] = (name, size_bytes)
                subtitle_size_map[key3] = (name, size_bytes)
        
        # Group subtitles by language for better matching
        subtitles_by_lang = {}
        for (lang, _), (name, size) in subtitle_size_map.items():
            if lang not in subtitles_by_lang:
                subtitles_by_lang[lang] = []
            subtitles_by_lang[lang].append((name, size))
        
        # Scan for audio and subtitle files
        for file_path in self.output_dir.iterdir():
            if not file_path.is_file():
                continue
            
            file_name = file_path.name
            file_stem = file_path.stem
            
            # Audio files
            if any(file_name.lower().endswith(ext) for ext in audio_extensions):

                # Skip if this is the main video file
                if status['video'] and file_path.name == Path(status['video']['path']).name:
                    continue
                
                audio_name = file_stem
                if audio_name.lower().startswith(self.filename.lower()):
                    audio_name = audio_name[len(self.filename):].lstrip('.')
                
                status['audios'].append({
                    'path': str(file_path),
                    'name': audio_name,
                    'size': file_path.stat().st_size
                })
            
            # Subtitle files
            elif any(file_name.lower().endswith(ext) for ext in subtitle_extensions):
                sub_size = file_path.stat().st_size
                sub_stem = file_stem
                
                # Extract language from filename
                extracted_lang = self._extract_language_from_filename(sub_stem, self.filename)
                
                # Try to find the best match
                best_match_name = None
                min_diff = float('inf')
                
                # First, try exact language match
                if extracted_lang in subtitles_by_lang:
                    for name, size in subtitles_by_lang[extracted_lang]:
                        diff = abs(size - sub_size)
                        if diff < min_diff and diff <= 2048:  # 2KB tolerance
                            min_diff = diff
                            best_match_name = name
                
                # If no match found, try all subtitles
                if not best_match_name:
                    for (lang, name), (_, size) in subtitle_size_map.items():
                        diff = abs(size - sub_size)
                        if diff < min_diff and diff <= 2048:
                            min_diff = diff
                            best_match_name = name
                
                # If still no match, use extracted language
                if not best_match_name:
                    best_match_name = extracted_lang
                
                status['subtitles'].append({
                    'path': str(file_path),
                    'language': extracted_lang,
                    'name': best_match_name,
                    'size': sub_size
                })
        
        return status
    
    def get_status(self) -> Dict[str, Any]:
        """Get current download status"""
        return self.status if self.status else self._get_download_status({}, [])