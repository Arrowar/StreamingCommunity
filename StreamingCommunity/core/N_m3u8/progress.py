# 10.01.26

import time
from typing import Dict, Any, Optional


# External libraries
from rich.console import Console
from rich.progress import Progress, TextColumn
from rich.table import Table


# Logic
from .utils import CustomBarColumn, FormatUtils


# Variable
console = Console()


class ProgressBarManager:
    def __init__(self, manifest_type: str = "UNKNOWN"):
        self.manifest_type = manifest_type
        self.progress_bars: Optional[Progress] = None
        self.video_task = None
        self.audio_tasks: Dict[str, Any] = {}
        self.video_start_time: Optional[float] = None
        self.audio_start_time: Optional[float] = None
        self.last_video_size = "0.00 MB"
        self.last_video_elapsed = 0.0
        self.last_audio_size = "0.00 MB"
        self.last_audio_elapsed = 0.0
    
    def setup(self) -> None:
        """Initialize progress bars"""
        self.progress_bars = Progress(
            TextColumn("[bold]{task.description}[/bold]"),
            CustomBarColumn(bar_width=40),
            TextColumn("[bright_green]{task.fields[current]}[/bright_green][dim]/[/dim][bright_cyan]{task.fields[total_segments]}[/bright_cyan]"),
            TextColumn("[dim]\\[[/dim][bright_yellow]{task.fields[elapsed]}[/bright_yellow][dim] < [/dim][bright_cyan]{task.fields[eta]}[/bright_cyan][dim]][/dim]"),
            TextColumn("[bright_green]{task.fields[size_value]}[/bright_green] [bright_magenta]{task.fields[size_unit]}[/bright_magenta]"),
            TextColumn("[dim]@[/dim]"),
            TextColumn("[bright_cyan]{task.fields[speed_value]}[/bright_cyan] [bright_magenta]{task.fields[speed_unit]}[/bright_magenta]"),
            console=console
        )
        self.progress_bars.start()
        
        # Add video task
        self.video_task = self.progress_bars.add_task(
            f"[yellow]{self.manifest_type} [cyan]Video",
            total=100,
            current="0", total_segments="0",
            elapsed="00:00", eta="00:00",
            size_value="0.00", size_unit="MB",
            speed_value="0.00", speed_unit="MB/s"
        )
        
        self.video_start_time = time.time()
    
    def add_audio_task(self, language: str, audio_langs: list, stream_info: Any = None) -> None:
        """Add audio task for a specific language"""
        if not self.progress_bars:
            return
        
        # Get all available audio languages from stream_info
        available_audio_langs = set()
        audio_lang_mapping = {}  # Map lowercase to display name
        
        if stream_info:
            for stream in stream_info.audio_streams:
                # Prefer lang_code over language for the key
                key = None
                display_name = None
                
                if stream.lang_code and stream.lang_code != "-":
                    key = stream.lang_code.lower()
                    display_name = stream.lang_code.upper()
                elif stream.language and stream.language != "-":
                    key = stream.language.lower()
                    display_name = stream.language.upper()
                
                if key:
                    available_audio_langs.add(key)
                    if key not in audio_lang_mapping:
                        audio_lang_mapping[key] = display_name
        
        # If using "all", create tasks for all available audio languages
        if "all" in [lang.lower() for lang in audio_langs]:
            for lang_key in available_audio_langs:
                if lang_key not in self.audio_tasks:
                    display_name = audio_lang_mapping.get(lang_key, lang_key.upper())
                    audio_task = self.progress_bars.add_task(
                        f"[yellow]{self.manifest_type} [cyan]Audio [bright_magenta][{display_name}]",
                        total=100,
                        current="0", total_segments="0",
                        elapsed="00:00", eta="00:00",
                        size_value="0.00", size_unit="MB",
                        speed_value="0.00", speed_unit="MB/s"
                    )
                    self.audio_tasks[lang_key] = audio_task
        
        else:
            # Create tasks only for selected languages
            for lang in audio_langs:
                lang_lower = lang.lower()
                if lang_lower not in self.audio_tasks:
                    if any(lang_lower in available_lang for available_lang in available_audio_langs):
                        audio_task = self.progress_bars.add_task(
                            f"[yellow]{self.manifest_type} [cyan]Audio [bright_magenta][{lang.upper()}]",
                            total=100,
                            current="0", total_segments="0",
                            elapsed="00:00", eta="00:00",
                            size_value="0.00", size_unit="MB",
                            speed_value="0.00", speed_unit="MB/s"
                        )
                        self.audio_tasks[lang_lower] = audio_task
    
    def update_video_progress(self, progress_data: Any) -> None:
        """Update video progress bar"""
        if not self.progress_bars or self.video_task is None:
            return
    
        if self.video_start_time is None:
            self.video_start_time = time.time()
        
        p = progress_data
        elapsed = time.time() - self.video_start_time
        eta = FormatUtils.calculate_eta(p.current, p.total, elapsed) if p.percent < 99.5 else 0
        
        size_str = FormatUtils.parse_size_to_mb(p.total_size)
        size_parts = size_str.rsplit(' ', 1)
        
        # Store last valid values
        if p.percent < 99.5 and len(size_parts) == 2 and size_parts[0] != "0.00":
            self.last_video_size = size_str
            self.last_video_elapsed = elapsed
        
        # Use stored values when Done
        if p.percent >= 99.5:
            final_size_parts = self.last_video_size.rsplit(' ', 1)
            final_elapsed = self.last_video_elapsed
        else:
            final_size_parts = size_parts
            final_elapsed = elapsed
        
        speed_value = "Done" if p.percent >= 99.5 else FormatUtils.parse_speed_to_mb(p.speed).split()[0]
        speed_unit = "" if p.percent >= 99.5 else "MB/s"
        
        self.progress_bars.update(
            self.video_task,
            completed=min(p.percent, 100.0),
            current=str(p.current), total_segments=str(p.total),
            elapsed=FormatUtils.format_time(final_elapsed),
            eta=FormatUtils.format_time(eta),
            size_value=final_size_parts[0] if len(final_size_parts) == 2 else "0.00",
            size_unit=final_size_parts[1] if len(final_size_parts) == 2 else "MB",
            speed_value=speed_value, speed_unit=speed_unit
        )
        self.progress_bars.refresh()
    
    def update_audio_progress(self, progress_data: Any, stream_info: Any = None) -> None:
        """Update audio progress bar"""
        if not self.progress_bars:
            return
     
        p = progress_data
        
        # Determine target task by extracting language from description
        audio_lang = None
        target_task = None
        
        # Try to extract language from description (format: "Audio | LANG")
        if " | " in p.description:
            parts = p.description.split(" | ")
            if len(parts) >= 2:
                audio_lang = parts[1].strip().lower()
        
        # If not found, try to match against available streams
        if not audio_lang or audio_lang not in self.audio_tasks:
            if stream_info and not audio_lang:
                for stream in stream_info.audio_streams:
                    # Try lang_code first
                    if stream.lang_code and stream.lang_code != "-":
                        if stream.lang_code.lower() in p.description.lower():
                            audio_lang = stream.lang_code.lower()
                            break
                    # Then try language
                    elif stream.language and stream.language != "-":
                        if stream.language.lower() in p.description.lower():
                            audio_lang = stream.language.lower()
                            break
            
            # If still not found, use unknown
            if not audio_lang:
                audio_lang = "unk"
        
        # Get or create the task
        if audio_lang not in self.audio_tasks:
            audio_task = self.progress_bars.add_task(
                f"[orange1]{self.manifest_type}[/orange1] [cyan]Audio[/cyan] [bright_magenta][{audio_lang.upper()}][/bright_magenta]",
                total=100,
                current="0", total_segments="0",
                elapsed="00:00", eta="00:00",
                size_value="0.00", size_unit="MB",
                speed_value="0.00", speed_unit="MB/s"
            )
            self.audio_tasks[audio_lang] = audio_task
            target_task = audio_task
        else:
            target_task = self.audio_tasks[audio_lang]
        
        if target_task:
            if self.audio_start_time is None:
                self.audio_start_time = time.time()
            
            elapsed = time.time() - self.audio_start_time
            eta = FormatUtils.calculate_eta(p.current, p.total, elapsed) if p.percent < 99.5 else 0
            
            size_str = FormatUtils.parse_size_to_mb(p.total_size)
            size_parts = size_str.rsplit(' ', 1)
            
            if p.percent < 99.5 and len(size_parts) == 2 and size_parts[0] != "0.00":
                self.last_audio_size = size_str
                self.last_audio_elapsed = elapsed
            
            if p.percent >= 99.5:
                final_size_parts = self.last_audio_size.rsplit(' ', 1)
                final_elapsed = self.last_audio_elapsed
            else:
                final_size_parts = size_parts
                final_elapsed = elapsed
            
            speed_value = "Done" if p.percent >= 99.5 else FormatUtils.parse_speed_to_mb(p.speed).split()[0]
            speed_unit = "" if p.percent >= 99.5 else "MB/s"
            
            self.progress_bars.update(
                target_task,
                completed=min(p.percent, 100.0),
                current=str(p.current), total_segments=str(p.total),
                elapsed=FormatUtils.format_time(final_elapsed),
                eta=FormatUtils.format_time(eta),
                size_value=final_size_parts[0] if len(final_size_parts) == 2 else "0.00",
                size_unit=final_size_parts[1] if len(final_size_parts) == 2 else "MB",
                speed_value=speed_value, speed_unit=speed_unit
            )
            self.progress_bars.refresh()
    
    def stop(self) -> None:
        """Stop and cleanup progress bars"""
        if self.progress_bars:
            self.progress_bars.stop()
            self.progress_bars = None


def show_streams_table(streams_data: Dict[str, Any], external_subtitles: list = None, show_full_table: bool = False) -> None:
    """Show table with available streams"""
    if not streams_data.get("success"):
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
    
    # Count selections
    subtitle_disponibili = len([s for s in streams_data["streams"] if s["type"] == "Subtitle"])
    
    for stream in streams_data["streams"]:
        # Skip non-selected subtitles if more than 6 and show_full_table is False
        if (stream["type"] == "Subtitle" and subtitle_disponibili > 6 and 
            not show_full_table and not stream["selected"]):
            continue
        
        sel_icon = "X" if stream["selected"] else ""
        type_display = f"{stream['type']} [red]*CENC[/red]" if stream["encrypted"] else stream["type"]
        
        table.add_row(
            type_display, sel_icon, stream["resolution"] or "-",
            stream["bitrate"] or "-", stream["codec"] or "-",
            stream["lang_code"] or "-", stream.get("language", "-"),
            "-", str(stream["segments_count"]) if stream["segments_count"] else "-"
        )
    
    # Add external subtitles
    if external_subtitles:
        for ext_sub in external_subtitles:
            table.add_row(
                "Subtitle [yellow](Ext)[/yellow]", "X", "-", "-", "-",
                ext_sub.get("language", "unknown"),
                f"Ext ({ext_sub.get('language', 'unknown')})", "-", "-"
            )
    
    console.print(table)