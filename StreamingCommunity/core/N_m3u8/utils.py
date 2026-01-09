# 10.01.26

import os

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
    def find_downloaded_files(output_dir: str, filename: str, audio_lang: str = None, subtitle_lang: str = None) -> DownloadResult:
        """Download files finder"""
        result = DownloadResult()
        clean_filename = filename.rstrip('.')
        
        try:
            files = os.listdir(output_dir)
        except:
            return result
        
        # Order and filter files
        matching_files = [(f, os.path.join(output_dir, f)) for f in files if f.startswith(clean_filename)]
        matching_files.sort(key=lambda x: len(x[0]))
        
        for basename, filepath in matching_files:
            ext = os.path.splitext(basename)[1].lower()
            name_no_ext = os.path.splitext(basename)[0]
            
            # 1) Video
            if name_no_ext == clean_filename and ext in FileUtils.VIDEO_EXT and not result.video_path:
                result.video_path = filepath
                continue
            
            # 2)Subtitle
            if ext in FileUtils.SUBTITLE_EXT:
                parts = basename.replace(clean_filename, '').lstrip('.').split('.')
                lang = parts[0] if parts else "unknown"
                result.subtitle_tracks.append(MediaTrack(path=filepath, language=lang, format=ext[1:]))
            
            # 3) Audio
            elif ext in FileUtils.AUDIO_EXT and name_no_ext != clean_filename:
                parts = basename.replace(clean_filename, '').lstrip('.').split('.')
                lang = parts[0] if parts and len(parts) >= 2 else (audio_lang or "unknown")
                result.audio_tracks.append(MediaTrack(path=filepath, language=lang, format=ext[1:]))
        
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
            text.append(self.incomplete_char * (self.bar_width - bar_width), style=self.incomplete_style)
        
        return text