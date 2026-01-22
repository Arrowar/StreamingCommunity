# 04.01.25

import re
import platform
import subprocess
import asyncio
from pathlib import Path
from typing import Optional, List, Dict, Any


# External
import httpx
from rich.table import Table
from rich.console import Console
from rich.progress import Progress, TextColumn


# Internal 
from StreamingCommunity.utils.config import config_manager
from StreamingCommunity.utils import internet_manager
from StreamingCommunity.setup import get_ffmpeg_path, get_n_m3u8dl_re_path, get_bento4_decrypt_path, get_shaka_packager_path


# Logic
from .object import StreamInfo
from .pattern import VIDEO_LINE_RE, AUDIO_LINE_RE, SUBTITLE_LINE_RE, SEGMENT_RE, PERCENT_RE, SPEED_RE, SIZE_RE, SUBTITLE_FINAL_SIZE_RE
from .progress_bar import CustomBarColumn, ColoredSegmentColumn, CompactTimeColumn, CompactTimeRemainingColumn, SizeColumn
from .parser import parse_meta_json, LogParser
from .utils import convert_size_to_bytes


# Variable
console = Console(force_terminal=True if platform.system().lower() != 'windows' else None)
video_filter = config_manager.config.get("M3U8_DOWNLOAD", "select_video")
audio_filter = config_manager.config.get("M3U8_DOWNLOAD", "select_audio")
subtitle_filter = config_manager.config.get("M3U8_DOWNLOAD", "select_subtitle")
max_speed = config_manager.config.get("M3U8_DOWNLOAD", "max_speed")
check_segments_count = config_manager.config.get_bool("M3U8_DOWNLOAD", "check_segments_count")
concurrent_download = config_manager.config.get_int("M3U8_DOWNLOAD", "concurrent_download")
retry_count = config_manager.config.get_int("M3U8_DOWNLOAD", "retry_count")
request_timeout = config_manager.config.get_int("REQUESTS", "timeout")
thread_count = config_manager.config.get_int("M3U8_DOWNLOAD", "thread_count")
real_time_decryption = config_manager.config.get_bool("M3U8_DOWNLOAD", "real_time_decryption")
USE_PROXY = bool(config_manager.config.get_bool("REQUESTS", "use_proxy"))
CONF_PROXY = config_manager.config.get_dict("REQUESTS", "proxy") or {}


class MediaDownloader:
    def __init__(self, url: str, output_dir: str, filename: str, headers: Optional[Dict] = None, key: Optional[str] = None, cookies: Optional[Dict] = None, decrypt_preference: str = "bento4"):
        self.url = url
        self.output_dir = Path(output_dir)
        self.filename = filename
        self.headers = headers or {}
        self.key = key
        self.cookies = cookies or {}
        self.decrypt_preference = decrypt_preference.lower()

        # Initialize other attributes
        self.streams = []
        self.external_subtitles = []
        self.force_best_video = False           # Flag to force best video if no video selected
        self.meta_json_path, self.meta_selected_path, self.raw_m3u8, self.raw_mpd = None, None, None, None 
        self.status = None
        self.manifest_type = "Unknown"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _normalize_filter(self, filter_value: str) -> str:
        """Normalize filter ensuring values are quoted if they contain special characters"""
        if not filter_value:
            return filter_value
        
        # Split by colon, but only if not preceded by a backslash
        parts = filter_value.split(':')
        normalized_parts = []
        special_chars = '|.*+?[]{}()^$'
        
        for part in parts:
            if '=' in part:
                key, val = part.split('=', 1)

                # Remove any existing quotes
                val = val.strip("'\"")
                
                # If contains special characters, ensure double quotes
                if any(c in val for c in special_chars):
                    normalized_parts.append(f'{key}="{val}"')
                else:
                    normalized_parts.append(f'{key}={val}')
            else:
                normalized_parts.append(part)
        
        return ':'.join(normalized_parts)

    def _get_common_args(self) -> List[str]:
        """Get common command line arguments for N_m3u8DL-RE"""
        cmd = []
        if self.headers:
            for k, v in self.headers.items():
                cmd.extend(["--header", f"{k}: {v}"])

        if self.cookies:
            if cookie_str := "; ".join(f"{k}={v}" for k, v in self.cookies.items()):
                cmd.extend(["--header", f"Cookie: {cookie_str}"])

        if USE_PROXY and (proxy_url := CONF_PROXY.get("https") or CONF_PROXY.get("http")):
            cmd.extend(["--use-system-proxy", "false", "--custom-proxy", proxy_url])

        cmd.extend(["--force-ansi-console", "--no-ansi-color"])
        return cmd
    
    def determine_decryption_tool(self) -> str:
        """Determine decryption tool based on preference and availability"""
        if self.decrypt_preference == "bento4":
            return get_bento4_decrypt_path()
        elif self.decrypt_preference == "shaka":
            return get_shaka_packager_path()
        else:
            console.log(f"[yellow]Unknown decryption preference '{self.decrypt_preference}'; defaulting to Bento4")
            return get_bento4_decrypt_path()

    def parser_stream(self) -> List[StreamInfo]:
        """Analyze playlist and display table of available streams"""
        analysis_path = self.output_dir / "analysis_temp"
        analysis_path.mkdir(exist_ok=True)
        
        # Normalize filter values
        normalized_video = self._normalize_filter(video_filter)
        normalized_audio = self._normalize_filter(audio_filter)
        normalized_subtitle = self._normalize_filter(subtitle_filter)
        
        cmd = [
            get_n_m3u8dl_re_path(),
            "--write-meta-json",
            "--no-log",
            "--save-dir", str(analysis_path),
            "--tmp-dir", str(analysis_path),
            "--save-name", "temp_analysis",
            "--select-video", normalized_video,
            "--select-audio", normalized_audio,
            "--select-subtitle", normalized_subtitle,
            "--skip-download"
        ]
        cmd.extend(self._get_common_args())
        cmd.append(self.url)

        console.print("[cyan]Analyzing playlist...")
        log_parser = LogParser()
        
        # Use errors='replace' to handle non-UTF-8 characters
        result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors='replace', timeout=request_timeout)
        
        # Save parsing log
        log_path = self.output_dir / f"{self.filename}_parsing.log"
        with open(log_path, 'w', encoding='utf-8', errors='replace') as log_file:
            log_file.write(f"Command: {' '.join(cmd)}\n{'='*80}\n\n")
            log_file.write(result.stdout)
            if result.stderr:
                log_file.write("\n--- STDERR ---\n")
                log_file.write(result.stderr)
        
        # Parse stderr and stdout
        for line in result.stderr.split('\n'):
            if line.strip():
                log_parser.parse_line(line)
        
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
                    name=ext_sub.get('name', ''),
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
        async with httpx.AsyncClient(headers=self.headers, timeout=request_timeout) as client:
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
        
        # Normalize all filter values
        normalized_video = self._normalize_filter(select_video)
        normalized_audio = self._normalize_filter(audio_filter)
        normalized_subtitle = self._normalize_filter(subtitle_filter)
        
        cmd = [get_n_m3u8dl_re_path()]
        
        # Options
        cmd.extend(["--save-name", self.filename])
        cmd.extend(["--save-dir", str(self.output_dir)])
        cmd.extend(["--tmp-dir", str(self.output_dir)])
        cmd.extend(["--ffmpeg-binary-path", get_ffmpeg_path()])
        cmd.extend(["--decryption-binary-path", self.determine_decryption_tool()])
        cmd.extend(["--no-log"])
        cmd.extend(["--write-meta-json", "false"])
        cmd.extend(["--binary-merge"])
        cmd.extend(["--del-after-done"])
        cmd.extend(["--select-video", normalized_video])
        cmd.extend(["--select-audio", normalized_audio])
        cmd.extend(["--select-subtitle", normalized_subtitle])
        cmd.extend(["--auto-subtitle-fix", "false"])        # CON TRUE ALCUNE VOLTE NON SCARICATA TUTTI I SUB SELEZIONATI
        
        cmd.extend(self._get_common_args())

        if concurrent_download:
            cmd.append("--concurrent-download")
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
        if real_time_decryption:
            cmd.extend(["--mp4-real-time-decryption", "true"])
        
        if self.key:
            keys = [self.key] if isinstance(self.key, str) else self.key
            for single_key in keys:
                cmd.extend(["--key", single_key])
        
        cmd.append(self.url)

        console.print("\n[cyan]Starting download...")
        
        # Download external subtitles
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        external_subs = loop.run_until_complete(self._download_external_subtitles())
        
        log_parser = LogParser()
        log_path = self.output_dir / f"{self.filename}_download.log"
        subtitle_sizes = {}
        
        with open(log_path, 'w', encoding='utf-8', errors='replace') as log_file:
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
                
                # Use errors='replace' to handle encoding issues
                proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors='replace')

                with proc:
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
        
        self.status = self._get_download_status(subtitle_sizes, external_subs)
        return self.status

    def _update_task(self, progress, tasks: dict, key: str, label: str, line: str):
        """Generic task update helper"""
        if key not in tasks:
            tasks[key] = progress.add_task(
                f"[yellow]{self.manifest_type} {label}",
                total=100, segment="0/0", speed="0Bps", size="0B/0B"
            )
        task = tasks[key]

        # 1) Update segments
        if m := SEGMENT_RE.search(line): 
            progress.update(task, segment=m.group(0))

        # 2) Update percentage
        if m := PERCENT_RE.search(line): 
            try: 
                progress.update(task, completed=float(m.group(1)))
            except Exception:  
                pass

        # 3) Update speed
        if m := SPEED_RE.search(line): 
            progress.update(task, speed=m.group(1))

        # 4) Update size
        if m := SIZE_RE.search(line): 
            progress.update(task, size=f"{m.group(1)}/{m.group(2)}")
        
        return task

    def _parse_progress_line(self, line: str, progress, tasks: dict, subtitle_sizes: dict):
        """Parse a progress line and update progress bars"""
        
        # 1) Video progress
        if line.startswith("Vid"):
            res = (VIDEO_LINE_RE.search(line).group(1) if VIDEO_LINE_RE.search(line) else 
                  next((s.resolution or s.extension or "main" for s in self.streams if s.type == "Video"), "main"))
            self._update_task(progress, tasks, f"video_{res}", f"[cyan]Vid [red]{res}", line)

        # 2) Audio progress
        elif line.startswith("Aud"):
            if m := AUDIO_LINE_RE.search(line):
                bitrate, lang_name = m.group(1).strip(), m.group(2).strip()
                display = lang_name
                if not any(c.isalpha() for c in lang_name):
                    display = next((s.language or s.name or bitrate for s in self.streams if s.type == "Audio" and s.bandwidth and bitrate in s.bandwidth), bitrate)
                self._update_task(progress, tasks, f"audio_{lang_name}_{bitrate}", f"[cyan]Aud [red]{display}", line)

        # 3) Subtitle progress
        elif line.startswith("Sub"):
            if m := SUBTITLE_LINE_RE.search(line):
                lang, name = m.group(1).strip(), m.group(2).strip()
                task = self._update_task(progress, tasks, f"sub_{lang}_{name}", f"[cyan]Sub [red]{name}", line)
                
                # Special capture for final size
                if fm := SUBTITLE_FINAL_SIZE_RE.search(line):
                    final_size = fm.group(1)
                    progress.update(task, size=final_size, completed=100)
                    subtitle_sizes[f"{lang}: {name}"] = final_size

                # Also capture size if available
                elif not SIZE_RE.search(line):
                    if sm := re.search(r"(\d+\.\d+(?:B|KB|MB|GB))\s*$", line):
                        subtitle_sizes[f"{lang}: {name}"] = sm.group(1)

    def _display_stream_table(self):
        """Display streams in a rich table"""
        table = Table(show_header=True, header_style="bold cyan")
        cols = [
            ("Type", "cyan"), ("Ext", "magenta"), ("Sel", "green"),
            ("Resolution", "yellow"), ("Bitrate", "yellow"), ("Codec", "green"), 
            ("Language", "blue"), ("Name", "green"), ("Duration", "magenta"), 
            ("Segments", None)
        ]
        for col, color in cols:
            table.add_column(col, style=color, justify="right" if col == "Segments" else "left")
        
        for s in self.streams:
            bitrate = s.bandwidth if (s.bandwidth and s.bandwidth not in ["0 bps", "N/A"]) else ""
            table.add_row(
                f"{s.type}{' [red]*CENC' if s.encrypted else ''}",
                s.extension or "",
                "X" if s.selected else "",
                s.resolution if s.type == "Video" else "",
                bitrate,
                s.codec or "",
                s.language or "",
                s.name or "",
                internet_manager.format_time(s.total_duration, add_hours=True) if s.total_duration > 0 else "N/A",
                str(s.segment_count)
            )
        
        console.print(table)

    def _extract_language_from_filename(self, filename: str, base_name: str) -> str:
        """Extract language from filename"""
        stem = filename[len(base_name):].lstrip('.') if filename.startswith(base_name) else filename
        return stem.rsplit('.', 1)[0].split('.')[0] if '.' in stem else stem

    def _get_download_status(self, subtitle_sizes: dict, external_subs: list) -> Dict[str, Any]:
        """Get final download status"""
        status = {'video': None, 'audios': [], 'subtitles': [], 'external_subtitles': external_subs}
        exts = {
            'video': ['.mp4', '.mkv', '.m4v', '.ts', '.mov', '.webm'],
            'audio': ['.m4a', '.aac', '.mp3', '.ts', '.mp4', '.wav', '.webm'],
            'subtitle': ['.srt', '.vtt', '.ass', '.sub', '.ssa']
        }
        
        # Find video
        for ext in exts['video']:
            if (f := self.output_dir / f"{self.filename}{ext}").exists():
                status['video'] = {'path': str(f), 'size': f.stat().st_size}
                break
        
        # Process downloaded subtitle metadata
        downloaded_subs = []
        for d_name, size_str in subtitle_sizes.items():
            lang, name = d_name.split(':', 1) if ':' in d_name else (d_name, d_name)
            lang, name = lang.strip(), name.strip()
            
            if sz := convert_size_to_bytes(size_str):
                downloaded_subs.append({'lang': lang, 'name': name, 'size': sz, 'used': False})

        def norm_lang(lang): 
            return set(lang.lower().replace('-', '.').split('.'))
        
        seen_langs = {} # Track seen language codes during scanning to handle duplicates

        # Scan files
        for f in sorted(list(self.output_dir.iterdir())):
            if not f.is_file(): 
                continue
            
            # Audio
            if any(f.name.lower().endswith(e) for e in exts['audio']):
                if status['video'] and f.name == Path(status['video']['path']).name:
                    continue

                name = f.stem[len(self.filename):].lstrip('.') if f.stem.lower().startswith(self.filename.lower()) else f.stem
                status['audios'].append({'path': str(f), 'name': name, 'size': f.stat().st_size})
            
            # Subtitle
            elif any(f.name.lower().endswith(e) for e in exts['subtitle']):
                ext_lang = self._extract_language_from_filename(f.stem, self.filename)
                f_size = f.stat().st_size
                best_sub, min_diff = None, float('inf')
                
                # 1. Try to find the best match based on size and language tokens
                f_lang_tokens = norm_lang(ext_lang)
                for sub in downloaded_subs:
                    if sub.get('used'): 
                        continue
                    
                    s_lang_tokens = norm_lang(sub['lang'])
                    overlap = f_lang_tokens & s_lang_tokens
                    diff = abs(sub['size'] - f_size)
                    
                    if (not f_lang_tokens or not s_lang_tokens or overlap) or not downloaded_subs:
                        if diff < min_diff and diff <= 2048:
                            min_diff, best_sub = diff, sub
                
                # 2. Determine display name
                if best_sub:
                    lang, name = best_sub['lang'], best_sub['name']
                    best_sub['used'] = True
                    
                    # If we've already seen this exact language code, use Language - Name
                    if seen_langs.get(lang):
                        final_name = f"{lang} - {name}" if name and name != lang else lang
                    else:
                        # First occurrence: always use the Language code
                        final_name = lang
                    
                    seen_langs[lang] = seen_langs.get(lang, 0) + 1
                else:
                    final_name = ext_lang

                status['subtitles'].append({
                    'path': str(f), 
                    'language': final_name, 
                    'name': final_name, 
                    'size': f_size
                })
        
        return status
    
    def get_status(self) -> Dict[str, Any]:
        """Get current download status"""
        return self.status if self.status else self._get_download_status({}, [])