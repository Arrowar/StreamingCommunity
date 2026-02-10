# 04.01.25

import os
import json
from typing import List, Tuple


# External 
from rich.console import Console


# Logic
from ..utils.object import StreamInfo 


# Variable
console = Console()


class LogParser:
    def __init__(self, show_warnings: bool = True, show_errors: bool = True):
        self.warnings = []
        self.errors = []
        self.show_warnings = show_warnings
        self.show_errors = show_errors
    
    def parse_line(self, line: str) -> Tuple[bool, bool]:
        """Parse a log line, return (has_warning, has_error)"""
        line = line.strip()
        
        if 'WARN' in line.upper(): 
            self.warnings.append(line)
            if self.show_warnings and 'Response' in str(line):
                console.print(f"N_M3U8[yellow] - {line}")

        if 'ERROR' in line.upper():
            self.errors.append(line)
            if self.show_errors:
                console.print(f"N_M3U8[red] - {line}")

        return 'WARN' in line.upper(), 'ERROR' in line.upper()


def create_key(s):
    """Create a unique key for a stream from meta.json data"""
    if "Resolution" in s and s.get("Resolution"): 
        return f"VIDEO|{s.get('Resolution','')}|{s.get('Bandwidth',0)}|{s.get('Codecs','')}|{s.get('FrameRate','')}|{s.get('VideoRange','')}"

    if s.get("MediaType") == "AUDIO": 
        return f"AUDIO|{s.get('Language','')}|{s.get('Name','')}|{s.get('Bandwidth',0)}|{s.get('Codecs','')}|{s.get('Channels','')}"

    return f"SUBTITLE|{s.get('Language','')}|{s.get('Name','')}|{s.get('Role','')}"


def get_track_protection(s) -> str:
    """Check for encryption in all segments. Returns 'NONE', 'CENC'*, etc."""
    all_methods = set()
    playlist = s.get('Playlist', {})
    
    # Check MediaInit
    init = playlist.get('MediaInit', {})
    if init:
        m = init.get('EncryptInfo', {}).get('Method', 'NONE')
        if m: 
            all_methods.add(m)
        
    # Check all segments in all parts
    for part in playlist.get('MediaParts', []):
        for seg in part.get('MediaSegments', []):
            m = seg.get('EncryptInfo', {}).get('Method', 'NONE')
            if m: 
                all_methods.add(m)
    
    if not all_methods: 
        return 'NONE'
    
    non_none = [m for m in all_methods if m and m.upper() != 'NONE']
    if not non_none: 
        return 'NONE'
    
    # If mixed (contains NONE and something else), add asterisk
    if 'NONE' in all_methods:
        main = 'CENC' if 'CENC' in non_none else 'CBCS' if 'CBCS' in non_none else non_none[0]
        return f"{main}*"
    
    return non_none[0]


def classify_stream(s):
    """Classify stream type based on meta.json data"""
    group_id = s.get("GroupId", "")
    if isinstance(group_id, str) and group_id.startswith("thumb_"):
        return "Thumbnail"
    
    # Check MediaType
    media_type = s.get("MediaType", "").upper()
    if media_type == "AUDIO":
        return "Audio"
    elif media_type == "SUBTITLES":
        return "Subtitle"
    elif media_type == "VIDEO":
        return "Video"
    
    # Fallback: if has Resolution, it's Video
    if "Resolution" in s and s.get("Resolution"):
        return "Video"
    
    # Default to Video for unknown types
    return "Video"


def parse_meta_json(json_path: str, selected_json_path: str) -> List[StreamInfo]:
    """Parse meta.json and meta_selected.json to determine which streams are selected"""
    if not os.path.exists(json_path):
        return []

    with open(json_path, 'r', encoding='utf-8-sig') as f: 
        metadata = json.load(f)
        
    selected_map = {}
    if selected_json_path and os.path.isfile(selected_json_path):
        with open(selected_json_path, 'r', encoding='utf-8-sig') as f:
            for s in json.load(f):
                enc_method = get_track_protection(s)
                enc = '*' in enc_method or (enc_method != 'NONE' and enc_method != '')

                selected_map[create_key(s)] = {
                    'encrypted': enc,
                    'encryption_method': enc_method,
                    'extension': s.get("Extension", ""),
                    'duration': s.get("Playlist", {}).get("TotalDuration", 0),
                    'segments': s.get("SegmentsCount", 0)
                }
    
    streams = []
    seen_keys = {}
    for s in metadata:
        key = create_key(s)
        bw = s.get('Bandwidth', 0)
        track_protection = get_track_protection(s)
        
        if key in seen_keys:
            idx = seen_keys[key]
            streams[idx].total_duration += s.get("Playlist", {}).get("TotalDuration", 0)
            streams[idx].segment_count += s.get("SegmentsCount", 0)
            
            # Aggregate protection
            old_p = streams[idx].segments_protection
            if track_protection != old_p:
                if old_p == 'NONE':
                    streams[idx].segments_protection = track_protection
                elif track_protection != 'NONE':
                    p_name = old_p.replace('*', '') if old_p != 'NONE' else track_protection.replace('*', '')
                    streams[idx].segments_protection = f"{p_name}*"
            continue
            
        seen_keys[key] = len(streams)
        bw_str = f"{bw/1e6:.1f} Mbps" if bw >= 1e6 else (f"{bw/1e3:.0f} Kbps" if bw >= 1e3 else f"{bw:.0f} bps")
        
        sel = key in selected_map
        det = selected_map.get(key, {})
        st_type = classify_stream(s)
        
        streams.append(StreamInfo(
            type_=st_type,
            resolution=s.get("Resolution", ""),
            language=s.get("Language", ""),
            name=s.get("Name", ""),
            bandwidth="N/A" if st_type == "Subtitle" else bw_str,
            raw_bandwidth=bw,
            codec=s.get("Codecs", ""),
            selected=sel,
            extension=det.get('extension', s.get("Extension", "")),
            total_duration=det.get('duration', s.get("Playlist", {}).get("TotalDuration", 0)),
            segment_count=det.get('segments', s.get("SegmentsCount", 0)),
            segments_protection = det.get('encryption_method', track_protection),
        ))
        streams[-1].track_id = s.get("GroupId") or s.get("id") or ""
        
    return streams