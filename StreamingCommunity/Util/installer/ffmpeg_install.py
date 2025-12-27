# 24.01.2024

import os
import shutil
from typing import Optional, Tuple


# External library
from rich.console import Console


# Logic
from .binary_paths import binary_paths


# Variable
console = Console()


def check_ffmpeg() -> Tuple[Optional[str], Optional[str]]:
    """
    Check for FFmpeg executables and download if not found.
    Order: system PATH -> binary directory -> download from GitHub
    
    Returns:
        Tuple[Optional[str], Optional[str]]: Paths to ffmpeg and ffprobe
    """
    system_platform = binary_paths.system
    ffmpeg_name = "ffmpeg.exe" if system_platform == "windows" else "ffmpeg"
    ffprobe_name = "ffprobe.exe" if system_platform == "windows" else "ffprobe"
    
    # STEP 1: Check system PATH
    ffmpeg_path = shutil.which(ffmpeg_name)
    ffprobe_path = shutil.which(ffprobe_name)
    
    if ffmpeg_path and ffprobe_path:
        return ffmpeg_path, ffprobe_path
    
    # STEP 2: Check binary directory
    ffmpeg_local = binary_paths.get_binary_path("ffmpeg", ffmpeg_name)
    ffprobe_local = binary_paths.get_binary_path("ffmpeg", ffprobe_name)
    
    if ffmpeg_local and os.path.isfile(ffmpeg_local) and ffprobe_local and os.path.isfile(ffprobe_local):
        return ffmpeg_local, ffprobe_local
    
    # STEP 3: Download from GitHub repository
    console.print("[red]FFmpeg not found. Downloading ...")
    ffmpeg_downloaded = binary_paths.download_binary("ffmpeg", ffmpeg_name)
    ffprobe_downloaded = binary_paths.download_binary("ffmpeg", ffprobe_name)
    
    if ffmpeg_downloaded and ffprobe_downloaded:
        return ffmpeg_downloaded, ffprobe_downloaded
    
    console.print("Failed to download FFmpeg", style="red")
    return None, None