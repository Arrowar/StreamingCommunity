# 04.01.25

import os
import json
from typing import List, Tuple


# External 
from rich.console import Console


# Logic
from .object import StreamInfo 


# Variable
console = Console()


class LogParser:
    def __init__(self):
        self.warnings = []
        self.errors = []
    
    def parse_line(self, line: str) -> Tuple[bool, bool]:
        """Parse a log line, return (has_warning, has_error)"""
        line = line.strip()
        
        if 'WARN' in line.upper(): 
            self.warnings.append(line)

        if 'ERROR' in line.upper():
            self.errors.append(line)
            console.print(f"[red]{line}.")

        return 'WARN' in line.upper(), 'ERROR' in line.upper()


def create_key(s):
    """Create a unique key for a stream from meta.json data"""
    if "Resolution" in s and s.get("Resolution"): 
        return f"VIDEO|{s.get('Resolution','')}|{s.get('Bandwidth',0)}|{s.get('Codecs','')}|{s.get('FrameRate','')}|{s.get('VideoRange','')}"

    if s.get("MediaType") == "AUDIO": 
        return f"AUDIO|{s.get('Language','')}|{s.get('Name','')}|{s.get('Bandwidth',0)}|{s.get('Codecs','')}|{s.get('Channels','')}"

    return f"SUBTITLE|{s.get('Language','')}|{s.get('Name','')}"


def parse_meta_json(json_path: str, selected_json_path: str) -> List[StreamInfo]:
    """Parse meta.json and meta_selected.json to determine which streams are selected"""
    with open(json_path, 'r', encoding='utf-8-sig') as f: 
        metadata = json.load(f)
        
    selected_map = {}
    if selected_json_path and os.path.isfile(selected_json_path):
        with open(selected_json_path, 'r', encoding='utf-8-sig') as f:
            for s in json.load(f):
                
                # Check for encryption in segments
                enc = any(
                    seg.get("EncryptInfo", {}).get("Method") not in ["NONE", None] 
                    for part in s.get("Playlist", {}).get("MediaParts", [])
                    for seg in part.get("MediaSegments", [])
                )
                selected_map[create_key(s)] = {
                    'encrypted': enc, 
                    'extension': s.get("Extension", ""),
                    'duration': s.get("Playlist", {}).get("TotalDuration", 0),
                    'segments': s.get("SegmentsCount", 0)
                }
    
    streams = []
    seen_keys = set()
    for s in metadata:
        key = create_key(s)
        if key in seen_keys:
            continue
        seen_keys.add(key)
        
        bw = s.get('Bandwidth', 0)
        bw_str = f"{bw/1e6:.1f} Mbps" if bw >= 1e6 else (f"{bw/1e3:.0f} Kbps" if bw >= 1e3 else f"{bw:.0f} bps")
        
        sel = key in selected_map
        det = selected_map.get(key, {})
        
        # Determine stream type
        st_type = "Video" if ("Resolution" in s and s.get("Resolution")) else s.get("MediaType", "Video").title()
        if st_type == "Subtitles": 
            st_type = "Subtitle"
        
        streams.append(StreamInfo(
            type_=st_type,
            resolution=s.get("Resolution", ""),
            language=s.get("Language", ""),
            name=s.get("Name", ""),
            bandwidth="N/A" if st_type == "Subtitle" else bw_str,
            codec=s.get("Codecs", ""),
            selected=sel,
            encrypted=det.get('encrypted', False),
            extension=det.get('extension', s.get("Extension", "")),
            total_duration=det.get('duration', s.get("Playlist", {}).get("TotalDuration", 0)),
            segment_count=det.get('segments', s.get("SegmentsCount", 0))
        ))
    return streams