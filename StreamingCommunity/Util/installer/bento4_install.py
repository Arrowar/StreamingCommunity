# 18.07.25

import os
import shutil
from typing import Optional


# External library
from rich.console import Console


# Logic
from .binary_paths import binary_paths


# Variable
console = Console()


def check_mp4decrypt() -> Optional[str]:
    """
    Check for mp4decrypt and download if not found.
    Order: system PATH -> binary directory -> download from GitHub
    
    Returns:
        Optional[str]: Path to mp4decrypt executable or None if not found
    """
    system_platform = binary_paths.system
    mp4decrypt_name = "mp4decrypt.exe" if system_platform == "windows" else "mp4decrypt"
    
    # STEP 1: Check system PATH
    mp4decrypt_path = shutil.which(mp4decrypt_name)
    
    if mp4decrypt_path:
        return mp4decrypt_path
    
    # STEP 2: Check binary directory
    mp4decrypt_local = binary_paths.get_binary_path("bento4", mp4decrypt_name)
    
    if mp4decrypt_local and os.path.isfile(mp4decrypt_local):
        return mp4decrypt_local
    
    # STEP 3: Download from GitHub repository
    console.print("[red]mp4decrypt not found. Downloading ...")
    mp4decrypt_downloaded = binary_paths.download_binary("bento4", mp4decrypt_name)
    
    if mp4decrypt_downloaded:
        return mp4decrypt_downloaded
    
    console.print("Failed to download mp4decrypt", style="red")
    return None