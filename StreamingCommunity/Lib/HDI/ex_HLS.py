# 17.10.24

import os
import shutil
import logging
from pathlib import Path
from typing import Any, Dict, Optional


# Extermal
from rich.console import Console


# Internal utilities
from StreamingCommunity.Lib.FFmpeg import join_video, join_audios, join_subtitle
from StreamingCommunity.Util import config_manager, os_manager, internet_manager


# Logic
from .download import MediaDownloader, DownloadStatus


# Config
console = Console()
ENABLE_DEBUG = config_manager.config.get_bool('DEFAULT', 'debug')
DOWNLOAD_SPECIFIC_AUDIO = config_manager.config.get_list('M3U8_DOWNLOAD', 'specific_list_audio')
DOWNLOAD_SPECIFIC_SUBTITLE = config_manager.config.get_list('M3U8_DOWNLOAD', 'specific_list_subtitles')
MERGE_SUBTITLE = config_manager.config.get_bool('M3U8_DOWNLOAD', 'merge_subs')
CLEANUP_TMP = config_manager.config.get_bool('M3U8_DOWNLOAD', 'cleanup_tmp_folder')
EXTENSION_OUTPUT = config_manager.config.get("M3U8_CONVERSION", "extension")


class HLS_Downloader:
    def __init__(self, m3u8_url: str, license_url: Optional[str] = None, output_path: Optional[str] = None, headers: Optional[Dict[str, str]] = None):
        """
        Initialize HLS Downloader.
        
        Args:
            m3u8_url: Source M3U8 playlist URL
            license_url: License URL for DRM content (unused with MediaDownloader)
            output_path: Full path including filename and extension (e.g., /path/to/video.mp4)
            headers: Custom headers for requests
        """
        self.m3u8_url = str(m3u8_url).strip()
        self.license_url = str(license_url).strip() if license_url else None
        self.custom_headers = headers or {}
        
        # Sanitize and validate output path
        if not output_path:
            output_path = f"download.{EXTENSION_OUTPUT}"
        
        self.output_path = os_manager.get_sanitize_path(output_path)
        if not self.output_path.endswith(f'.{EXTENSION_OUTPUT}'):
            self.output_path += f'.{EXTENSION_OUTPUT}'
        
        # Extract directory and filename components ONCE
        self.output_dir = str(Path(self.output_path).parent)
        self.filename_base = Path(self.output_path).stem
        
        # Check if file already exists
        self.file_already_exists = os.path.exists(self.output_path)
        
        # Status tracking
        self.error = None
        self.last_merge_result = None
        
        # Setup MediaDownloader
        self.media_downloader = MediaDownloader(
            url=self.m3u8_url,
            output_dir=self.output_dir,
            filename=self.filename_base,
            headers=self.custom_headers
        )
        self.media_downloader.configure(
            select_audio_lang=DOWNLOAD_SPECIFIC_AUDIO,
            select_subtitle_lang=DOWNLOAD_SPECIFIC_SUBTITLE,
            enable_logging=True
        )

    def start(self) -> Dict[str, Any]:
        """Main execution flow for downloading HLS content"""
        if self.file_already_exists:
            console.log(f"[yellow]File already exists: [red]{self.output_path}")
            return {
                'path': self.output_path,
                'url': self.m3u8_url,
                'msg': 'File already exists',
                'error': None,
                'stopped': False
            }
        
        # Create output directory
        os_manager.create_path(self.output_dir)
        
        # Get available streams
        console.print("[cyan]Analyzing available streams...")
        stream_info = self.media_downloader.get_available_streams()
        
        if stream_info:
            console.print(f"[cyan]Manifest [yellow]{stream_info.manifest_type} [green]Video streams[white]: [red]{len(stream_info.video_streams)}[white], [green]Audio streams[white]: [red]{len(stream_info.audio_streams)}[white], [green]Subtitle streams[white]: [red]{len(stream_info.subtitle_streams)}")
            self.media_downloader.show_table(stream_info)
        
        # Start download
        for update in self.media_downloader.start_download(show_progress=True):
            pass  # Progress is shown automatically

        # Get final status
        status = self.media_downloader.get_status()
        if status.video_path is None:
            console.log("[red]Cant find video path after download")
        
        if status.status != DownloadStatus.COMPLETED or not status.video_path:
            return {
                'path': None,
                'url': self.m3u8_url,
                'msg': f'Download failed: {status.error_message or "Unknown error"}',
                'error': status.error_message,
                'stopped': True
            }
        
        # Merge files using FFmpeg
        final_file = self._merge_files(status)
        
        if not final_file or not os.path.exists(final_file):
            return {
                'path': None,
                'url': self.m3u8_url,
                'msg': 'Merge failed',
                'error': self.error or 'Merge operation failed',
                'stopped': True
            }
        
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
        self._cleanup_temp_files(status)
        
        return {
            'path': self.output_path,
            'url': self.m3u8_url,
            'msg': 'Download completed successfully',
            'error': None,
            'stopped': False
        }

    def _merge_files(self, status) -> Optional[str]:
        """Merge downloaded files using FFmpeg"""
        video_path = status.video_path
        
        if not os.path.exists(video_path):
            console.print(f"[red]Video file not found: {video_path}")
            self.error = "Video file missing"
            return None
        
        # If no additional tracks, mux video using join_video
        if not status.audios_paths and not status.subtitle_paths:
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
        if status.audios_paths:
            audio_tracks = []
            for audio in status.audios_paths:
                if os.path.exists(audio['path']):
                    audio_tracks.append({
                        'path': audio['path'],
                        'name': audio['language']
                    })
            
            if audio_tracks:
                console.print(f"[cyan]\nMerging [red]{len(audio_tracks)} [cyan]audio track(s)...")
                audio_output = os.path.join(self.output_dir, f"{self.filename_base}_with_audio.{EXTENSION_OUTPUT}")
                
                merged_file, use_shortest, result_json = join_audios(
                    video_path=current_file,
                    audio_tracks=audio_tracks,
                    out_path=audio_output
                )
                self.last_merge_result = result_json
                
                if os.path.exists(merged_file):
                    current_file = merged_file
                else:
                    console.print("[yellow]Audio merge failed, continuing with video only")
        
        # Merge subtitles if enabled and present
        if MERGE_SUBTITLE and status.subtitle_paths:
            sub_tracks = []
            for sub in status.subtitle_paths:
                if os.path.exists(sub['path']):
                    sub_tracks.append({
                        'path': sub['path'],
                        'language': sub['language']
                    })
            
            if sub_tracks:
                console.print(f"[cyan]\nMerging [red]{len(sub_tracks)} [cyan]subtitle(s)...")
                sub_output = os.path.join(self.output_dir, f"{self.filename_base}_final.{EXTENSION_OUTPUT}")
                
                merged_file, result_json = join_subtitle(
                    video_path=current_file,
                    subtitles_list=sub_tracks,
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

    def _cleanup_temp_files(self, status):
        """Clean up temporary files"""
        if not CLEANUP_TMP:
            return
        
        files_to_remove = []
        
        # Add original downloaded files
        if status.video_path and os.path.abspath(status.video_path) != os.path.abspath(self.output_path):
            files_to_remove.append(status.video_path)
        
        for audio in status.audios_paths:
            if os.path.abspath(audio['path']) != os.path.abspath(self.output_path):
                files_to_remove.append(audio['path'])
        
        for sub in status.subtitle_paths:
            if os.path.abspath(sub['path']) != os.path.abspath(self.output_path):
                files_to_remove.append(sub['path'])
        
        # Remove intermediate merge files
        intermediate_patterns = [
            f"{self.filename_base}_with_audio.{EXTENSION_OUTPUT}",
            f"{self.filename_base}_final.{EXTENSION_OUTPUT}"
        ]
        
        for pattern in intermediate_patterns:
            file_path = os.path.join(self.output_dir, pattern)
            if os.path.exists(file_path) and os.path.abspath(file_path) != os.path.abspath(self.output_path):
                files_to_remove.append(file_path)
        
        # Remove files
        for file_path in files_to_remove:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except Exception as e:
                logging.warning(f"Could not remove temp file {file_path}: {e}")

        # Remove log file and folder
        if not ENABLE_DEBUG:
            os.remove(os.path.join(self.output_dir, "log.txt"))
            shutil.rmtree(os.path.join(self.output_dir, "temp_analysis"))

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