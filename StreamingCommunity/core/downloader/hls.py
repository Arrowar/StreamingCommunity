# 17.10.24

import os
import shutil
import logging
from typing import Any, Dict, Optional


# External libraries
from rich.console import Console


# Internal utilities
from StreamingCommunity.utils.http_client import get_headers
from StreamingCommunity.core.processors import join_video, join_audios, join_subtitles
from StreamingCommunity.core.downloader.media_players import MediaPlayers
from StreamingCommunity.utils import config_manager, os_manager, internet_manager


# DRM Utilities
from StreamingCommunity.source.N_m3u8 import MediaDownloader


# Config
console = Console()
CLEANUP_TMP = config_manager.config.get_bool('M3U8_DOWNLOAD', 'cleanup_tmp_folder')
EXTENSION_OUTPUT = config_manager.config.get("M3U8_CONVERSION", "extension")


class HLS_Downloader:
    def __init__(self, m3u8_url: str, license_url: Optional[str] = None, output_path: Optional[str] = None, headers: Optional[Dict[str, str]] = None):
        """
        Args:
            m3u8_url: Source M3U8 playlist URL
            license_url: License URL for DRM content (unused with MediaDownloader)
            output_path: Full path including filename and extension (e.g., /path/to/video.mp4)
            headers: Custom headers for requests
        """
        self.m3u8_url = str(m3u8_url).strip()
        self.license_url = str(license_url).strip() if license_url else None
        self.custom_headers = headers
        if self.custom_headers is None:
            self.custom_headers = get_headers()

        # Sanitize and validate output path
        if not output_path:
            output_path = f"download.{EXTENSION_OUTPUT}"
        
        self.output_path = os_manager.get_sanitize_path(output_path)
        if not self.output_path.endswith(f'.{EXTENSION_OUTPUT}'):
            self.output_path += f'.{EXTENSION_OUTPUT}'
        
        # Extract directory and filename components ONCE
        self.filename_base = os.path.splitext(os.path.basename(self.output_path))[0]
        self.output_dir = os.path.join(os.path.dirname(self.output_path), self.filename_base + "_hls_temp")
        self.file_already_exists = os.path.exists(self.output_path)
        
        # Status tracking
        self.error = None
        self.last_merge_result = None
        self.media_players = None
        
        # Setup MediaDownloader
        self.media_downloader = MediaDownloader(
            url=self.m3u8_url,
            output_dir=self.output_dir,
            filename=self.filename_base,
            headers=self.custom_headers
        )
        self.media_downloader.parser_stream()

    def start(self) -> Dict[str, Any]:
        """Main execution flow for downloading HLS content"""
        if self.file_already_exists:
            console.log(f"[yellow]File already exists: [red]{self.output_path}")
            return self.output_path, False
        
        # Create output directory
        os_manager.create_path(self.output_dir)
        
        # Create media player ignore files to prevent media scanners
        try:
            self.media_players = MediaPlayers(self.output_dir)
            self.media_players.create()
        except Exception:
            pass
        status = self.media_downloader.start_download()

        # Check if any media was downloaded
        if status.get('video') is None and status.get('audios') == [] and status.get('subtitles') == [] and status.get('external_subtitles') == []:
            logging.error("No media downloaded")
            return None, True

        # Merge files using FFmpeg
        final_file = self._merge_files(status)
        
        if not final_file or not os.path.exists(final_file):
            logging.error("Merge operation failed")
            return None, True
        
        # Move to final location if needed
        if os.path.abspath(final_file) != os.path.abspath(self.output_path):
            try:
                if os.path.exists(self.output_path):
                    os.remove(self.output_path)
                os.rename(final_file, self.output_path)
            except Exception as e:
                console.print(f"[yellow]Warning: Could not move file: {e}")
                self.output_path = final_file
        
        # Print summary and cleanup
        self._print_summary()
        if CLEANUP_TMP:
            shutil.rmtree(self.output_dir, ignore_errors=True)
        return self.output_path, False

    def _merge_files(self, status) -> Optional[str]:
        """Merge downloaded files using FFmpeg"""
        if status['video'] is None:
            return None
        
        video_path = status['video'].get('path')
        
        if not os.path.exists(video_path):
            console.print(f"[red]Video file not found: {video_path}")
            self.error = "Video file missing"
            return None
        
        # If no additional tracks, mux video using join_video
        if not status['audios'] and not status['subtitles']:
            console.print("[cyan]\nNo additional tracks to merge, muxing video...")
            merged_file, result_json = join_video(
                video_path=video_path,
                out_path=self.output_path
            )
            self.last_merge_result = result_json
            if os.path.exists(merged_file):
                return merged_file
            else:
                self.error = "Video mux failed"
                return None
        
        current_file = video_path
        
        # Merge audio tracks if present
        if status['audios']:
            console.print(f"[cyan]\nMerging [red]{len(status['audios'])} [cyan]audio track(s)...")
            audio_output = os.path.join(self.output_dir, f"{self.filename_base}_with_audio.{EXTENSION_OUTPUT}")
            
            merged_file, use_shortest, result_json = join_audios(
                video_path=current_file,
                audio_tracks=status['audios'],
                out_path=audio_output
            )
            self.last_merge_result = result_json
            
            if os.path.exists(merged_file):
                current_file = merged_file
            else:
                console.print("[yellow]Audio merge failed, continuing with video only")
        
        # Merge subtitles if enabled and present
        if status['subtitles']:
            console.print(f"[cyan]\nMerging [red]{len(status['subtitles'])} [cyan]subtitle track(s)...")
            sub_output = os.path.join(self.output_dir, f"{self.filename_base}_final.{EXTENSION_OUTPUT}")
            
            merged_file, result_json = join_subtitles(
                video_path=current_file,
                subtitles_list=status['subtitles'],
                out_path=sub_output
            )
            self.last_merge_result = result_json
            
            if os.path.exists(merged_file):
                if current_file != video_path and os.path.exists(current_file):
                    try:
                        os.remove(current_file)
                    except Exception:
                        pass
                current_file = merged_file
            else:
                console.print("[yellow]Subtitle merge failed, continuing without subtitles")
    
        return current_file

    def _print_summary(self):
        """Print download summary"""
        if not os.path.exists(self.output_path):
            return
        
        file_size = internet_manager.format_file_size(os.path.getsize(self.output_path))
        duration = 'N/A'
        
        if self.last_merge_result and isinstance(self.last_merge_result, dict):
            duration = self.last_merge_result.get('time', 'N/A')
        
        console.print("\n[green]Output:")
        console.print(f"  [cyan]Path: [red]{os.path.abspath(self.output_path)}")
        console.print(f"  [cyan]Size: [red]{file_size}")
        console.print(f"  [cyan]Duration: [red]{duration}")