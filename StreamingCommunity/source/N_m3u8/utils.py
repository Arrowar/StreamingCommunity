# 04.01.25

from typing import Optional


def convert_size_to_bytes(size_str: str) -> Optional[int]:
    """Convert size string (e.g., '45.40KB', '772.00B') to bytes"""
    try:
        size_str = size_str.upper().strip()
        if 'GB' in size_str:
            return int(float(size_str.replace('GB', '')) * 1024 * 1024 * 1024)
        elif 'MB' in size_str:
            return int(float(size_str.replace('MB', '')) * 1024 * 1024)
        elif 'KB' in size_str:
            return int(float(size_str.replace('KB', '')) * 1024)
        elif 'B' in size_str:
            return int(float(size_str.replace('B', '')))
        return None
    except Exception:
        return None


def format_bytes(bytes_num: int) -> str:
    """Format bytes to human readable string"""
    if bytes_num >= 1024 * 1024 * 1024:
        return f"{bytes_num/(1024*1024*1024):.2f} GB"
    elif bytes_num >= 1024 * 1024:
        return f"{bytes_num/(1024*1024):.2f} MB"
    elif bytes_num >= 1024:
        return f"{bytes_num/1024:.2f} KB"
    else:
        return f"{bytes_num} B"