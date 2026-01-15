# 17.01.25

import os
import shutil
from typing import Optional


# External import 
from rich.console import Console


# Variable
console = Console()


def detect_subtitle_format(subtitle_path: str) -> Optional[str]:
    """Detects the actual format of a subtitle file by examining its content."""
    try:
        with open(subtitle_path, 'r', encoding='utf-8', errors='ignore') as f:
            first_lines = ''.join([f.readline() for _ in range(10)]).lower()
            
            if 'webvtt' in first_lines:
                return 'vtt'
            
            if '[script info]' in first_lines or '[v4+ styles]' in first_lines or '[v4 styles]' in first_lines:
                if 'format: name' in first_lines or 'format: marked' in first_lines:
                    return 'ass'
                return 'ssa'
            
            lines = first_lines.split('\n')
            for i, line in enumerate(lines):
                if line.strip().isdigit() and i + 1 < len(lines):
                    if '-->' in lines[i + 1]:
                        return 'srt'
            
            if '-->' in first_lines:
                return 'srt'
                
    except Exception as e:
        console.print(f"[red]Error detecting subtitle format for {subtitle_path}: {str(e)}")
    
    return None


def fix_subtitle_extension(subtitle_path: str) -> str:
    """Detects the actual subtitle format and renames the file with the correct extension."""
    detected_format = detect_subtitle_format(subtitle_path)
    
    if detected_format is None:
        console.print(f"[yellow]    Warning: Could not detect format for {subtitle_path}, keeping original extension")
        return subtitle_path
    
    # Get current extension
    base_name, current_ext = os.path.splitext(subtitle_path)
    current_ext = current_ext.lower().lstrip('.')
    
    # If extension is already correct, no need to rename
    if current_ext == detected_format:
        return subtitle_path
    
    # Create new path with correct extension
    new_path = f"{base_name}.{detected_format}"
    
    try:
        shutil.move(subtitle_path, new_path)
        console.print(f"[yellow]    Renamed subtitle: [cyan]{current_ext} [yellow]-> [cyan]{detected_format}")
        return new_path
    
    except Exception as e:
        console.print(f"[red]    Error renaming subtitle: {str(e)}")
        return subtitle_path