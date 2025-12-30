# 15.12.2025

import os
import shutil
from typing import Optional


# External library
from rich.console import Console


# Logic
from .binary_paths import binary_paths


# Variable
console = Console()


def check_megatools() -> Optional[str]:
    """
    Check for megatools and download if not found.
    Order: system PATH -> binary directory -> download from GitHub
    
    Returns:
        Optional[str]: Path to megatools executable or None if not found
    """
    system_platform = binary_paths.system
    megatools_name = "megatools.exe" if system_platform == "windows" else "megatools"
    
    # STEP 1: Check system PATH
    megatools_path = shutil.which(megatools_name)
    
    if megatools_path:
        return megatools_path
    
    # STEP 2: Check binary directory
    megatools_local = binary_paths.get_binary_path("megatools", megatools_name)
    
    if megatools_local and os.path.isfile(megatools_local):
        return megatools_local
    
    # STEP 3: Download from GitHub repository
    console.print("[red]megatools not found. Downloading ...")
    megatools_downloaded = binary_paths.download_binary("megatools", megatools_name)
    
    if megatools_downloaded:
        return megatools_downloaded
    
    console.print("Failed to download megatools", style="red")
    return None