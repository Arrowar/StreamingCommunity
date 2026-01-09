# 10.01.26

import re
import os
import json
from typing import Optional


# Logic class
from .models import StreamInfo, Stream, DownloadProgress


class StreamParser:
    PROGRESS = re.compile(
        r"(Vid|Aud|Sub)\s+"                             # Stream type
        r"([^━\-]+?)\s+"                                # Description 
        r"[━\-\s]*"                                     # Progress bar chars (any)
        r"(\d+)/(\d+)\s+"                               # current/total segments
        r"([\d.]+)%"                                    # percentage
        r"(?:\s*([\d.]+[KMGT]*B?)/?([\d.]+[KMGT]*B?))?" # optional sizes
        r"(?:\s*([\d.]+[KMGT]*Bps))?"                   # optional speed
        r"(?:\s*([\d:.\-]+))?"                          # optional time
    )
    
    @staticmethod
    def parse_stream_info_from_json(meta_file_path, manifest_type_hint: str = None) -> StreamInfo:
        """Parse stream info directly from meta.json file instead of log parsing
        
        Args:
            meta_file_path: Path to meta.json file
            manifest_type_hint: Optional hint about manifest type ('HLS', 'DASH', or None for auto-detect)
        """
        if not os.path.exists(meta_file_path):
            return StreamInfo("UNKNOWN", [])
        
        try:
            with open(meta_file_path, 'r', encoding='utf-8-sig') as f:
                meta_data = json.load(f)
        except Exception as e:
            print(f"Error reading meta.json: {e}")
            return StreamInfo("UNKNOWN", [])
        
        streams = []
        manifest_type = manifest_type_hint if manifest_type_hint else "UNKNOWN"
        
        # Process each item in the meta.json array
        for item in meta_data:
            media_type = item.get("MediaType", "VIDEO").upper()
            
            # Only auto-detect if no hint was provided
            if not manifest_type_hint and manifest_type == "UNKNOWN":
                if "Codecs" in item and "Resolution" in item:
                    manifest_type = "DASH"
            
            # 1) Parse VIDEO streams
            if media_type == "VIDEO" or (media_type not in ["AUDIO", "SUBTITLES"] and "Resolution" in item):
                resolution = item.get("Resolution", "Unknown")
                bandwidth = item.get("Bandwidth", 0)
                codecs = item.get("Codecs", "unknown")
                segments_count = item.get("SegmentsCount", 0)
                
                # Convert bandwidth to Kbps
                bitrate = f"{bandwidth // 1000} Kbps" if bandwidth else "-"
                
                # Check if encrypted
                is_encrypted = False
                if "Playlist" in item and "MediaInit" in item["Playlist"]:
                    encrypt_info = item["Playlist"]["MediaInit"].get("EncryptInfo", {})
                    is_encrypted = encrypt_info.get("Method") is not None
                
                # Get duration
                duration = "-"
                if "Playlist" in item and "TotalDuration" in item["Playlist"]:
                    total_duration = item["Playlist"]["TotalDuration"]
                    
                    # Format duration as ~XXmXXs
                    minutes = int(total_duration // 60)
                    seconds = int(total_duration % 60)
                    duration = f"~{minutes}m{seconds}s"
                
                stream = Stream(
                    type="Video",
                    resolution=resolution,
                    bitrate=bitrate,
                    codec=codecs,
                    language="-",
                    lang_code="-",
                    language_long="-",
                    encrypted=is_encrypted,
                    duration=duration,
                    segments_count=segments_count
                )
                streams.append(stream)
            
            # 2) Parse AUDIO streams
            elif media_type == "AUDIO":
                language = item.get("Language", "unknown")
                name = item.get("Name", language)
                bandwidth = item.get("Bandwidth", 0)
                codecs = item.get("Codecs", "unknown")
                segments_count = item.get("SegmentsCount", 0)
                
                # Convert bandwidth to Kbps
                bitrate = f"{bandwidth // 1000} Kbps" if bandwidth else "-"
                
                # Check if encrypted
                is_encrypted = False
                if "Playlist" in item and "MediaInit" in item["Playlist"]:
                    encrypt_info = item["Playlist"]["MediaInit"].get("EncryptInfo", {})
                    is_encrypted = encrypt_info.get("Method") is not None
                
                # Get duration
                duration = "-"
                if "Playlist" in item and "TotalDuration" in item["Playlist"]:
                    total_duration = item["Playlist"]["TotalDuration"]
                    minutes = int(total_duration // 60)
                    seconds = int(total_duration % 60)
                    duration = f"~{minutes}m{seconds}s"
                
                stream = Stream(
                    type="Audio",
                    resolution="-",
                    bitrate=bitrate,
                    codec=codecs,
                    language=language,
                    lang_code=language,
                    language_long=name,
                    encrypted=is_encrypted,
                    duration=duration,
                    segments_count=segments_count
                )
                streams.append(stream)
            
            # 3) Parse SUBTITLE streams
            elif media_type == "SUBTITLES":
                language = item.get("Language", "unknown")
                name = item.get("Name", language)
                segments_count = item.get("SegmentsCount", 0)
                
                # Check if encrypted
                is_encrypted = False
                if "Playlist" in item and "MediaInit" in item["Playlist"]:
                    encrypt_info = item["Playlist"]["MediaInit"].get("EncryptInfo", {})
                    is_encrypted = encrypt_info.get("Method") is not None
                
                # Get duration
                duration = "-"
                if "Playlist" in item and "TotalDuration" in item["Playlist"]:
                    total_duration = item["Playlist"]["TotalDuration"]
                    minutes = int(total_duration // 60)
                    seconds = int(total_duration % 60)
                    duration = f"~{minutes}m{seconds}s"
                
                stream = Stream(
                    type="Subtitle",
                    resolution="-",
                    bitrate="-",
                    codec="-",
                    language=language,
                    lang_code=language,
                    language_long=name,
                    encrypted=is_encrypted,
                    duration=duration,
                    segments_count=segments_count
                )
                streams.append(stream)
        
        streams = StreamParser._deduplicate_subtitles(streams)
        return StreamInfo(manifest_type, streams)
    
    @staticmethod
    def _deduplicate_subtitles(streams: list) -> list:
        """Remove duplicate subtitle streams based on language and lang_code."""
        seen_subtitles = {}
        result = []
        
        for stream in streams:
            if stream.type == "Subtitle":
                key = (stream.language.lower(), stream.lang_code.lower())
                if key not in seen_subtitles:
                    seen_subtitles[key] = True
                    result.append(stream)
            else:
                result.append(stream)
        
        return result
    
    @staticmethod
    def parse_progress(line: str) -> Optional[DownloadProgress]:
        if match := StreamParser.PROGRESS.search(line):
            return DownloadProgress(
                stream_type=stream_type,
                description=description,
                current=current,
                total=total,
                percent=percent,
                downloaded_size=downloaded_size,
                total_size=total_size,
                speed=speed,
                time=time_remaining
            )
        return None