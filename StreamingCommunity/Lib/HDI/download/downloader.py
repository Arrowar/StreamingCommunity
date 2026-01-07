# 10.01.26

import os
import time
from pathlib import Path
from typing import Generator, Any, Optional, List, Dict


# External library
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, TextColumn


# Internal utilities
from StreamingCommunity.Util.http_client import fetch


# Logic class
from .models import StreamInfo, DownloadStatusInfo, DownloadStatus, DownloadConfig, MediaTrack
from .wrapper import N_m3u8DLWrapper
from .parser import StreamParser
from .utils import CustomBarColumn, FileUtils, FormatUtils


# Variable
console = Console()
show_full_table = False


class MediaDownloader:
    def __init__(self, url: str, output_dir: Path, filename: str, headers: Optional[Dict[str, str]] = None, decryption_keys: Optional[List[str]] = None, external_subtitles: Optional[List[dict]] = None):
        self.url = url
        self.output_dir = Path(output_dir)
        self.filename = filename
        self.headers = headers
        self.decryption_keys = decryption_keys
        self.external_subtitles = external_subtitles or []
        
        # Configuration and status
        self.config = DownloadConfig()
        self.status_info = DownloadStatusInfo()
        self.stream_info: Optional[StreamInfo] = None
        
        # Internal timing for progress calculation
        self._video_start_time: Optional[float] = None
        self._audio_start_time: Optional[float] = None
        
        # Audio selection tracking
        self.audio_disponibili = 0
        self.audio_selezionati = 0
    
    def configure(self, **kwargs) -> None:
        """Configuration for the downloader.
        
        Args:
            - select_audio_lang: List[str] - audio languages to download
            - select_subtitle_lang: List[str] - subtitle languages to download
            - select_forced_subtitles: bool - download forced subtitles
            - set_resolution: str - "best", "worst", or number (e.g., "1080")
            - auto_merge_tracks: bool - merge tracks into a single file
            - concurrent_download: bool - simultaneous video+audio download
            - thread_count: int - number of threads
            - retry_count: int - retry attempts on error
            - enable_logging: bool - enable logging to file
        """
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
    
    def set_keys(self, decryption_keys: Optional[List[str]]) -> None:
        """Update decryption keys for the downloader"""
        self.decryption_keys = decryption_keys
    
    def get_available_streams(self) -> Optional[StreamInfo]:
        """Get information about available streams"""
        if not self.stream_info:
            meta_path = os.path.join(self.output_dir, "temp_analysis", "meta.json")
            
            if os.path.exists(meta_path):
                self.stream_info = StreamParser.parse_stream_info_from_json(meta_path)
            
            # If meta.json not found, get from wrapper
            if not self.stream_info or not self.stream_info.streams:
                wrapper = N_m3u8DLWrapper(self.config, self.output_dir)
                self.stream_info = wrapper.get_available_streams(self.url, self.headers)
        
        return self.stream_info
    
    def show_table(self, stream_info: Optional[StreamInfo] = None) -> None:
        """Show table with available streams"""
        if stream_info is None:
            stream_info = self.get_available_streams()
            if stream_info is None:
                console.print("[red]Unable to retrieve stream information.")
                return
        
        table = Table()
        table.add_column("Type", style="bright_cyan")
        table.add_column("Sel", style="bold bright_green", justify="center")
        table.add_column("Resolution", style="bright_yellow")
        table.add_column("Bitrate", style="bright_white")
        table.add_column("Codec", style="bright_green")
        table.add_column("Lang", style="bright_magenta")
        table.add_column("Lang_L", style="bright_blue")
        table.add_column("Duration", style="bright_white")
        table.add_column("Segments", style="bright_cyan", justify="right")
        table.add_column("Est. Size", style="bright_yellow", justify="right")
        
        # Get selected streams
        best_video = stream_info.video_streams[0] if stream_info.video_streams else None
        audio_langs = self.config.select_audio_lang or []
        subtitle_langs = self.config.select_subtitle_lang or []
        
        # Count audio streams from the actual stream list (not the filtered list)
        self.audio_disponibili = len([s for s in stream_info.streams if s.type == "Audio"])
        self.audio_selezionati = 0
        
        # Count subtitle streams from the actual stream list
        self.subtitle_disponibili = len([s for s in stream_info.streams if s.type == "Subtitle"])
        self.subtitle_selezionati = 0
        
        # Count how many audio streams match the configured languages
        matching_audio_streams = 0
        for stream in stream_info.streams:
            if stream.type == "Audio":
                if audio_langs:
                    if "all" in [lang.lower() for lang in audio_langs]:
                        matching_audio_streams += 1
                    elif any(lang.lower() == stream.language.lower() for lang in audio_langs):
                        matching_audio_streams += 1
        
        # Count how many subtitle streams match the configured languages
        matching_subtitle_streams = 0
        for stream in stream_info.streams:
            if stream.type == "Subtitle":
                if subtitle_langs:
                    if "all" in [lang.lower() for lang in subtitle_langs]:
                        matching_subtitle_streams += 1
                    elif any(lang.lower() == stream.language.lower() for lang in subtitle_langs):
                        matching_subtitle_streams += 1
        
        # Streams from manifest
        for stream in stream_info.streams:
            will_download = False
            
            if stream.type == "Video":
                will_download = (stream == best_video)

            elif stream.type == "Audio":
                if "all" in [lang.lower() for lang in audio_langs]:
                    will_download = True
                else:
                    # Use only stream.language for matching (which contains the actual language code)
                    will_download = any(lang.lower() == stream.language.lower() for lang in audio_langs)
                    
                if will_download:
                    self.audio_selezionati += 1

            elif stream.type == "Subtitle":
                if "all" in [lang.lower() for lang in subtitle_langs]:
                    will_download = True
                else:
                    will_download = any(lang.lower() == stream.language.lower() for lang in subtitle_langs)

                if will_download and not self.config.select_forced_subtitles:
                    if "[forced]" in stream.language.lower() or "[cc]" in stream.language.lower():
                        will_download = False
                        
                if will_download:
                    self.subtitle_selezionati += 1
                
                # Skip non-selected subtitles if more than 6 and show_full_table is False
                if self.subtitle_disponibili > 6 and not show_full_table and not will_download:
                    continue
            
            sel_icon = "X" if will_download else ""
            type_display = f"{stream.type} [red]*CENC[/red]" if stream.encrypted else stream.type
            
            # Calculate estimated size
            est_size = "-"
            if stream.segments_count > 0 and stream.bitrate != "-":
                try:
                    # Extract bitrate value (e.g., "5000 Kbps" -> 5000)
                    bitrate_value = int(stream.bitrate.split()[0])
                    
                    # Get duration in seconds
                    duration_seconds = 0
                    if stream.duration != "-":

                        # Parse ~XXmXXs format
                        duration_str = stream.duration.strip("~")
                        if "m" in duration_str:
                            parts = duration_str.split("m")
                            minutes = int(parts[0])
                            seconds = int(parts[1].rstrip("s"))
                            duration_seconds = minutes * 60 + seconds
                    
                    if duration_seconds > 0:
                        
                        # Size = (bitrate in Kbps * duration in seconds) / 8 / 1024 = MB
                        size_mb = (bitrate_value * duration_seconds) / 8 / 1024
                        if size_mb > 1024:
                            est_size = f"~{size_mb / 1024:.1f} GB"
                        else:
                            est_size = f"~{size_mb:.1f} MB"
                except Exception:
                    est_size = "-"
            
            segments_display = str(stream.segments_count) if stream.segments_count > 0 else "-"
            
            table.add_row(
                type_display, sel_icon, stream.resolution,
                stream.bitrate, stream.codec,
                stream.lang_code if stream.lang_code != "-" else stream.language,
                stream.language_long if stream.language_long != "-" else "-",
                getattr(stream, 'duration', '-'),
                segments_display,
                est_size
            )
        
        # External subtitles
        for ext_sub in self.external_subtitles:
            table.add_row(
                "Subtitle [yellow](Ext)[/yellow]", "X", "-", "-", "-",
                ext_sub.get("language", "unknown"),
                f"Ext ({ext_sub.get('language', 'unknown')})",
                "-"
            )
        
        console.print(table)

    def start_download(self, show_progress: bool = True) -> Generator[Dict[str, Any], None, None]:
        """Start the download process, yielding status updates."""
        self.status_info = DownloadStatusInfo()
        self.status_info.status = DownloadStatus.PARSING
        self._video_start_time = None
        self._audio_start_time = None
        
        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Apply auto-selection if stream info is available
        if self.stream_info:
            self._apply_auto_selection(self.stream_info)
        
        download_wrapper = N_m3u8DLWrapper(self.config, self.output_dir)
        
        # Variable for progress display
        table_shown = False
        progress_bars = None
        video_task = None
        audio_tasks = {}
        
        try:
            for update in download_wrapper.download(self.url, self.filename, self.headers, self.decryption_keys, self.stream_info):
                self._update_status(update)
                
                if show_progress:
                    # 1) Parsing - store stream info but don't show table (already shown before download)
                    if update.get("status") == "parsing" and not table_shown:
                        if "stream_info" in update:
                            table_shown = True
                            self.stream_info = update["stream_info"]
                            console.file.flush()
                    
                    # 2) Selected streams - setup progress bars
                    elif update.get("status") == "selected" and not progress_bars:
                        protocol = self.stream_info.manifest_type if self.stream_info else "UNKNOWN"
                        progress_bars = Progress(
                            TextColumn("[bold]{task.description}[/bold]"),
                            CustomBarColumn(bar_width=40),
                            TextColumn("[bright_green]{task.fields[current]}[/bright_green][dim]/[/dim][bright_cyan]{task.fields[total_segments]}[/bright_cyan]"),
                            TextColumn("[dim]\\[[/dim][bright_yellow]{task.fields[elapsed]}[/bright_yellow][dim] < [/dim][bright_cyan]{task.fields[eta]}[/bright_cyan][dim]][/dim]"),
                            TextColumn("[bright_green]{task.fields[size_value]}[/bright_green] [bright_magenta]{task.fields[size_unit]}[/bright_magenta]"),
                            TextColumn("[dim]@[/dim]"),
                            TextColumn("[bright_cyan]{task.fields[speed_value]}[/bright_cyan] [bright_magenta]{task.fields[speed_unit]}[/bright_magenta]"),
                            console=console
                        )
                        progress_bars.start()
                        
                        # 3) Task video
                        video_task = progress_bars.add_task(
                            f"[yellow]{protocol} [cyan]Video",
                            total=100,
                            current="0", total_segments="0",
                            elapsed="00:00", eta="00:00",
                            size_value="0.00", size_unit="MB",
                            speed_value="0.00", speed_unit="MB/s"
                        )
                        
                        # 4) Task audio
                        if self.config.select_audio_lang and self.stream_info:

                            # If using "all", create a single audio task
                            if "all" in [lang.lower() for lang in self.config.select_audio_lang]:
                                audio_task = progress_bars.add_task(
                                    f"[yellow]{protocol} [cyan]Audio [bright_magenta][ALL]",
                                    total=100,
                                    current="0", total_segments="0",
                                    elapsed="00:00", eta="00:00",
                                    size_value="0.00", size_unit="MB",
                                    speed_value="0.00", speed_unit="MB/s"
                                )
                                audio_tasks["all"] = audio_task

                            else:
                                available_audio_langs = set()
                                for stream in self.stream_info.audio_streams:

                                    # Add both lang_code and language for matching
                                    if stream.lang_code and stream.lang_code != "-":
                                        available_audio_langs.add(stream.lang_code.lower())
                                    if stream.language and stream.language != "-":
                                        available_audio_langs.add(stream.language.lower())
                                
                                # Create tasks only for configured languages that exist in the streams
                                for lang in self.config.select_audio_lang:
                                    lang_lower = lang.lower()

                                    # Check if the configured language is present in the available streams
                                    if any(lang_lower in available_lang for available_lang in available_audio_langs):
                                        audio_task = progress_bars.add_task(
                                            f"[yellow]{protocol} [cyan]Audio [bright_magenta][{lang.upper()}]",
                                            total=100,
                                            current="0", total_segments="0",
                                            elapsed="00:00", eta="00:00",
                                            size_value="0.00", size_unit="MB",
                                            speed_value="0.00", speed_unit="MB/s"
                                        )
                                        audio_tasks[lang_lower] = audio_task  # Use lowercase key
                    
                    # 5) Downloading - update progress
                    elif update.get("status") == "downloading" and progress_bars:
                        self._update_progress_bars(update, progress_bars, video_task, audio_tasks)
                    
                    # 6) Finished
                    elif update.get("status") == "completed":
                        if progress_bars:
                            progress_bars.stop()
                        console.file.flush()
                    
                    # 7) Failed
                    elif update.get("status") == "failed":
                        if progress_bars:
                            progress_bars.stop()
                        console.print(f"[bold red]Download fallito: {update.get('error')}")
                        console.file.flush()
                
                yield update
                
                if self.status_info.status in [DownloadStatus.COMPLETED, DownloadStatus.FAILED]:
                    break
        
        except KeyboardInterrupt:
            if show_progress and progress_bars:
                progress_bars.stop()
                console.print("\n[yellow]7) Download cancelled")
            self.status_info.status = DownloadStatus.CANCELLED
            raise
        
        except Exception as e:
            if show_progress and progress_bars:
                progress_bars.stop()
            self.status_info.status = DownloadStatus.FAILED
            self.status_info.error_message = str(e)
            raise
    
    def _apply_auto_selection(self, stream_info: StreamInfo):
        """Apply automatic audio/subtitle selection if no matches found"""
        total_audio_streams = len(stream_info.audio_streams)
        total_subtitle_streams = len(stream_info.subtitle_streams)

        # Auto audio selection
        audio_langs = self.config.select_audio_lang or []
        matching_audio_streams = 0
        
        for stream in stream_info.audio_streams:
            if audio_langs:
                # Use exact matching for language codes
                if any(lang.lower() == stream.language.lower() for lang in audio_langs):
                    matching_audio_streams += 1

        # If no audio matches but audio is available, select the first one
        if total_audio_streams > 0 and matching_audio_streams == 0 and len(audio_langs) > 0:
            first_audio_lang = stream_info.audio_streams[0].language
            self.config.select_audio_lang = [first_audio_lang]
            console.print("[yellow]None of the specified audio languages were found. Automatically selecting the first available audio language.")

        elif total_audio_streams > 0 and len(audio_langs) == 0:
            first_audio_lang = stream_info.audio_streams[0].language
            self.config.select_audio_lang = [first_audio_lang]
            console.print("[yellow]No audio language specified. Automatically selecting the first available audio language.")
        
        # Auto subtitle selection
        subtitle_langs = self.config.select_subtitle_lang or []
        matching_subtitle_streams = 0
        
        for stream in stream_info.subtitle_streams:
            if subtitle_langs:
                if any(lang.lower() == stream.language.lower() for lang in subtitle_langs):
                    matching_subtitle_streams += 1
        
        if total_subtitle_streams > 0 and matching_subtitle_streams == 0 and len(subtitle_langs) > 0:
            first_subtitle_lang = stream_info.subtitle_streams[0].language
            self.config.select_subtitle_lang = [first_subtitle_lang]
            console.print("[yellow]None of the specified subtitle languages were found. Automatically selecting the first available subtitle language.")

        elif total_subtitle_streams > 0 and len(subtitle_langs) == 0:
            first_subtitle_lang = stream_info.subtitle_streams[0].language
            self.config.select_subtitle_lang = [first_subtitle_lang]
            console.print("[yellow]No subtitle language specified. Automatically selecting the first available subtitle language.")
    
    def _update_progress_bars(self, update, progress_bars, video_task, audio_tasks):
        """Aggiorna le progress bar con i nuovi dati"""
        protocol = self.stream_info.manifest_type if self.stream_info else "UNKNOWN"
        
        # 1) Video progress
        if "progress_video" in update:
            p = update["progress_video"]
            if self._video_start_time is None:
                self._video_start_time = time.time()
            
            elapsed = time.time() - self._video_start_time
            eta = FormatUtils.calculate_eta(p.current, p.total, elapsed) if p.percent < 99.5 else 0
            
            size_str = FormatUtils.parse_size_to_mb(p.total_size)
            size_parts = size_str.rsplit(' ', 1)
            
            speed_value = "Done" if p.percent >= 99.5 else FormatUtils.parse_speed_to_mb(p.speed).split()[0]
            speed_unit = "" if p.percent >= 99.5 else "MB/s"
            
            progress_bars.update(
                video_task,
                completed=min(p.percent, 100.0),
                current=str(p.current), total_segments=str(p.total),
                elapsed=FormatUtils.format_time(elapsed),
                eta=FormatUtils.format_time(eta),
                size_value=size_parts[0] if len(size_parts) == 2 else "0.00",
                size_unit=size_parts[1] if len(size_parts) == 2 else "MB",
                speed_value=speed_value, speed_unit=speed_unit
            )
            progress_bars.refresh()
        
        # 2) Audio progress
        if "progress_audio" in update:
            p = update["progress_audio"]
            
            # Check if we're using "all" mode
            target_task = None
            if "all" in audio_tasks:
                target_task = audio_tasks["all"]
            else:
                audio_lang = None
                if " | " in p.description:
                    parts = p.description.split(" | ")
                    if len(parts) >= 2:
                        audio_lang = parts[1].strip().lower()
                
                # Check if we already have a task for this language
                if not audio_lang or audio_lang not in audio_tasks:
                    if self.stream_info and not audio_lang:
                        for stream in self.stream_info.audio_streams:
                            if stream.language.lower() in p.description.lower():
                                audio_lang = stream.language.lower()  # Use language instead of lang_code
                                break
                    
                    # Fallback 
                    if not audio_lang:
                        audio_lang = "unk"
                    
                    if audio_lang not in audio_tasks:
                        audio_task = progress_bars.add_task(
                            f"[orange1]{protocol}[/orange1] [cyan]Audio[/cyan] [bright_magenta][{audio_lang.upper()}][/bright_magenta]",
                            total=100,
                            current="0", total_segments="0",
                            elapsed="00:00", eta="00:00",
                            size_value="0.00", size_unit="MB",
                            speed_value="0.00", speed_unit="MB/s"
                        )
                        audio_tasks[audio_lang] = audio_task
                        target_task = audio_task
                    else:
                        target_task = audio_tasks[audio_lang]
                        
                else:
                    target_task = audio_tasks[audio_lang]
            
            if target_task:
                if self._audio_start_time is None:
                    self._audio_start_time = time.time()
                
                elapsed = time.time() - self._audio_start_time
                eta = FormatUtils.calculate_eta(p.current, p.total, elapsed) if p.percent < 99.5 else 0
                
                size_str = FormatUtils.parse_size_to_mb(p.total_size)
                size_parts = size_str.rsplit(' ', 1)
                
                speed_value = "Done" if p.percent >= 99.5 else FormatUtils.parse_speed_to_mb(p.speed).split()[0]
                speed_unit = "" if p.percent >= 99.5 else "MB/s"
                
                progress_bars.update(
                    target_task,
                    completed=min(p.percent, 100.0),
                    current=str(p.current), total_segments=str(p.total),
                    elapsed=FormatUtils.format_time(elapsed),
                    eta=FormatUtils.format_time(eta),
                    size_value=size_parts[0] if len(size_parts) == 2 else "0.00",
                    size_unit=size_parts[1] if len(size_parts) == 2 else "MB",
                    speed_value=speed_value, speed_unit=speed_unit
                )
                progress_bars.refresh()
    
    def _update_status(self, update: Dict[str, Any]) -> None:
        """Update internal status based on the update"""
        status = update.get("status")
        
        # 1) Parsing
        if status == "parsing":
            self.status_info.status = DownloadStatus.PARSING
            if "stream_info" in update:
                self.stream_info = update["stream_info"]

        # 2) Selected / Downloading
        elif status in ["selected", "downloading"]:
            self.status_info.status = DownloadStatus.DOWNLOADING

        # 3) Completed
        elif status == "completed":
            self.status_info.status = DownloadStatus.COMPLETED
            self.status_info.is_completed = True
            result = update.get("result")
            if result:
                self._process_completed_download(result)

        # 4) Failed
        elif status == "failed":
            self.status_info.status = DownloadStatus.FAILED
            self.status_info.error_message = update.get("error")

        # 5) Cancelled
        elif status == "cancelled":
            self.status_info.status = DownloadStatus.CANCELLED
    
    def _process_completed_download(self, result):
        """Process downloaded files and download external subtitles"""
        self.status_info.video_path = result.video_path
        
        # Map language codes to long names
        lang_mapping = {}
        if self.stream_info:
            for stream in self.stream_info.streams:
                if stream.type in ["Audio", "Subtitle"] and stream.language_long:
                    if stream.language and stream.language != "-":
                        lang_mapping[stream.language.lower()] = stream.language_long
                    if stream.lang_code and stream.lang_code != "-":
                        lang_mapping[stream.lang_code.lower()] = stream.language_long
        
        # Audio tracks from manifest
        self.status_info.audios_paths = [
            {"path": track.path, "language": lang_mapping.get(track.language.lower(), track.language)}
            for track in result.audio_tracks
        ]
        
        # Subtitles from manifest + external
        all_subtitles = list(result.subtitle_tracks)
        
        # Download external subtitles if configured
        if self.external_subtitles and self.config.select_subtitle_lang:
            filtered_externals = [
                ext_sub for ext_sub in self.external_subtitles
                if any(lang.lower() in ext_sub.get('language', '').lower() 
                      for lang in self.config.select_subtitle_lang)
            ]
            
            if filtered_externals:
                external_subs = self._download_external_subtitles(filtered_externals)
                all_subtitles.extend(external_subs)
        
        self.status_info.subtitle_paths = [
            {
                "path": track.path,
                "language": lang_mapping.get(track.language.lower(), track.language),
                "format": getattr(track, 'format', None)
            }
            for track in all_subtitles
        ]
    
    def _download_external_subtitles(self, external_subtitles: List[dict]) -> List[MediaTrack]:
        """Download external subtitles from URLs"""
        downloaded_subs = []
        
        for sub_info in external_subtitles:
            url = sub_info.get('url')
            language = sub_info.get('language', 'unknown')
            format_ext = sub_info.get('format', 'srt')
            
            try:
                sub_filename = f"{self.filename}.{language}.{format_ext}"
                sub_path = self.output_dir / sub_filename
                console.print(f"\n[cyan]Download ext sub: [yellow]{language}.{format_ext}")
                
                response_text = fetch(url, headers=self.headers)
                if response_text is None:
                    raise Exception("Failed to download subtitle")
                
                with open(sub_path, 'w', encoding='utf-8') as f:
                    f.write(response_text)
                
                downloaded_subs.append(MediaTrack(
                    path=str(sub_path),
                    language=language,
                    format=format_ext
                ))

            except Exception as e:
                print(f"Errore download sottotitolo {url}: {e}")
                continue
        
        return downloaded_subs
    
    def get_status(self) -> DownloadStatusInfo:
        if (self.status_info.is_completed and not self.status_info.video_path and not self.status_info.audios_paths):
            audio_lang_param = None
            if self.config.select_audio_lang:
                if "all" in [lang.lower() for lang in self.config.select_audio_lang]:
                    audio_lang_param = None
                else:
                    audio_lang_param = self.config.select_audio_lang[0] if isinstance(self.config.select_audio_lang, list) else self.config.select_audio_lang
            
            # Determine the subtitle language parameter for file finding
            subtitle_lang_param = None
            if self.config.select_subtitle_lang:
                if "all" in [lang.lower() for lang in self.config.select_subtitle_lang]:
                    subtitle_lang_param = None
                else:
                    subtitle_lang_param = self.config.select_subtitle_lang[0] if isinstance(self.config.select_subtitle_lang, list) else self.config.select_subtitle_lang
            
            result = FileUtils.find_downloaded_files(
                self.output_dir, self.filename,
                audio_lang_param,
                subtitle_lang_param
            )
            
            if result:
                self._process_completed_download(result)
        
        return self.status_info