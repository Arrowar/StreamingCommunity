# 10.01.26

from pathlib import Path


# External library
from rich.progress import ProgressColumn
from rich.text import Text


# Logic class
from .models import DownloadResult, MediaTrack


class FileUtils:   
    VIDEO_EXT = ['.mp4', '.mkv', '.ts', '.m4v', '.m4s']
    AUDIO_EXT = ['.m4a', '.aac', '.mp3', '.ts', '.m4s']
    SUBTITLE_EXT = ['.srt', '.vtt', '.ass', '.sub', '.idx']
    
    @staticmethod
    def find_downloaded_files(output_dir: Path, filename: str, audio_lang: str = None, subtitle_lang: str = None) -> DownloadResult:
        """Search downloaded files in the output directory"""
        result = DownloadResult()

        # Order files
        clean_filename = filename.rstrip('.')
        all_files = list(output_dir.glob(f"{clean_filename}*"))
        all_files.sort(key=lambda x: len(x.name))
        
        for file_path in all_files:
            suffix = file_path.suffix.lower()
            name_without_ext = file_path.name.replace(suffix, '')
            
            # 1) Video
            if name_without_ext == clean_filename and suffix in FileUtils.VIDEO_EXT and not result.video_path:
                result.video_path = str(file_path)
                continue
            
            # 2) Audio or subtitle
            if file_path.name.startswith(clean_filename):
                if suffix in FileUtils.SUBTITLE_EXT:
                    name_parts = file_path.name.replace(clean_filename, '').lstrip('.').split('.')
                    lang = name_parts[0] if name_parts and name_parts[0] else "unknown"
                    
                    result.subtitle_tracks.append(MediaTrack(
                        path=str(file_path),
                        language=lang,
                        format=suffix[1:]
                    ))
                
                # 3) Audio
                elif suffix in FileUtils.AUDIO_EXT and name_without_ext != clean_filename:
                    name_parts = file_path.name.replace(clean_filename, '').lstrip('.').split('.')
                    
                    if name_parts and len(name_parts) >= 2:
                        lang = name_parts[0]
                    else:
                        lang = audio_lang if audio_lang else "unknown"
                    
                    result.audio_tracks.append(MediaTrack(
                        path=str(file_path),
                        language=lang,
                        format=suffix[1:]
                    ))
        
        return result

class FormatUtils:
    @staticmethod
    def parse_size_to_mb(size_str: str) -> str:
        try:
            size_str = size_str.strip().replace(" ", "")
            if not size_str or size_str == "-":
                return "0.00 MB"
            
            if "GB" in size_str:
                value = float(size_str.replace("GB", ""))
                return f"{value:.2f} GB"
            elif "MB" in size_str:
                value = float(size_str.replace("MB", ""))
                if value > 900:
                    return f"{value / 1024:.2f} GB"
                return f"{value:.2f} MB"
            elif "KB" in size_str:
                value = float(size_str.replace("KB", ""))
                mb_value = value / 1024
                if mb_value > 900:
                    return f"{mb_value / 1024:.2f} GB"
                return f"{mb_value:.2f} MB"
            else:
                value = float(size_str)
                if value > 900:
                    return f"{value / 1024:.2f} GB"
                return f"{value:.2f} MB"
        except Exception:
            return "0.00 MB"
    
    @staticmethod
    def parse_speed_to_mb(speed_str: str) -> str:
        try:
            speed_str = speed_str.strip().replace(" ", "").replace("ps", "")
            if not speed_str or speed_str == "-":
                return "0.00 MB/s"
            
            if "GB" in speed_str:
                value = float(speed_str.replace("GB", ""))
                return f"{value * 1024:.2f} MB/s"
            elif "MB" in speed_str:
                value = float(speed_str.replace("MB", ""))
                return f"{value:.2f} MB/s"
            elif "KB" in speed_str:
                value = float(speed_str.replace("KB", ""))
                return f"{value / 1024:.2f} MB/s"
            else:
                value = float(speed_str)
                return f"{value:.2f} MB/s"
        except Exception:
            return "0.00 MB/s"
    
    @staticmethod
    def format_time(seconds: float) -> str:
        if seconds < 0 or seconds == float('inf'):
            return "00:00"
        
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes:02d}:{secs:02d}"
    
    @staticmethod
    def calculate_eta(current: int, total: int, elapsed: float) -> float:
        if current == 0 or total == 0:
            return 0.0
        
        progress_ratio = current / total
        if progress_ratio == 0:
            return 0.0
        
        estimated_total = elapsed / progress_ratio
        return max(0.0, estimated_total - elapsed)


class CustomBarColumn(ProgressColumn):
    def __init__(self, bar_width=40, complete_char="█", incomplete_char="░", complete_style="bright_magenta", incomplete_style="dim white"):
        super().__init__()
        self.bar_width = bar_width
        self.complete_char = complete_char
        self.incomplete_char = incomplete_char
        self.complete_style = complete_style
        self.incomplete_style = incomplete_style
    
    def render(self, task):
        completed = task.completed
        total = task.total or 100
        
        bar_width = int((completed / total) * self.bar_width) if total > 0 else 0
        bar_width = min(bar_width, self.bar_width)
        
        text = Text()
        if bar_width > 0:
            text.append(self.complete_char * bar_width, style=self.complete_style)
        if bar_width < self.bar_width:
            text.append(self.incomplete_char * (self.bar_width - bar_width), 
                       style=self.incomplete_style)
        
        return text