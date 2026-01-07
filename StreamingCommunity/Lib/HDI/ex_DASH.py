# 05.01.26

import os
import shutil
import logging
from typing import Optional, Dict, Any
from pathlib import Path


# External
from rich.console import Console


# Internal utilities
from StreamingCommunity.Lib.FFmpeg.merge import join_audios, join_video, join_subtitle
from StreamingCommunity.Util import config_manager, os_manager, internet_manager
from StreamingCommunity.Util.os import get_wvd_path
from StreamingCommunity.Util.os import get_prd_path


# Logic class
from .extractor import get_widevine_keys, get_playready_keys
from .download import MediaDownloader, DownloadStatus
from .ex_MPD import MPDParser, DRMSystem


# Config
console = Console()
ENABLE_DEBUG = config_manager.config.get_bool('DEFAULT', 'debug')
DOWNLOAD_SPECIFIC_SUBTITLE = config_manager.config.get_list('M3U8_DOWNLOAD', 'specific_list_subtitles')
DOWNLOAD_SPECIFIC_AUDIO = config_manager.config.get_list('M3U8_DOWNLOAD', 'specific_list_audio')
MERGE_SUBTITLE = config_manager.config.get_bool('M3U8_DOWNLOAD', 'merge_subs')
CLEANUP_TMP = config_manager.config.get_bool('M3U8_DOWNLOAD', 'cleanup_tmp_folder')
EXTENSION_OUTPUT = config_manager.config.get("M3U8_CONVERSION", "extension")


class DASH_Downloader:
    def __init__(self, license_url: str, mpd_url: str, mpd_sub_list: list = None, output_path: str = None, drm_preference: str = 'widevine', custom_headers: Dict[str, str] = None, query_params: Dict[str, str] = None, key: str = None, license_headers: Dict[str, str] = None):
        """
        Initialize DASH Downloader.
        
        Parameters:
            license_url: URL to obtain DRM license
            mpd_url: URL of the MPD manifest
            mpd_sub_list: List of subtitle dicts (unused with MediaDownloader)
            output_path: Full path including filename and extension (e.g., /path/to/video.mp4)
            drm_preference: Preferred DRM system ('widevine', 'playready', 'auto')
            custom_headers: Custom headers for requests
            query_params: Query parameters for license requests
            key: Encryption key for license requests
        """
        self.license_url = str(license_url).strip() if license_url else None
        self.mpd_url = str(mpd_url).strip()
        self.drm_preference = drm_preference.lower()
        self.custom_headers = custom_headers or {}
        self.query_params = query_params or {}
        self.key = key
        self.license_headers = license_headers or {}
        self.raw_mpd_path = None
        
        # Sanitize and validate output path
        self.output_path = os_manager.get_sanitize_path(output_path)
        if not self.output_path.endswith(f'.{EXTENSION_OUTPUT}'):
            self.output_path += f'.{EXTENSION_OUTPUT}'
        
        # Extract directory and filename components ONCE
        self.output_dir = str(Path(self.output_path).parent)
        self.filename_base = Path(self.output_path).stem
        
        # Check if file already exists
        self.file_already_exists = os.path.exists(self.output_path)
        
        # DRM info
        self.drm_info = None
        self.decryption_keys = []
        
        # MediaDownloader instance
        self.media_downloader = None
        
        # Status tracking
        self.error = None
        self.last_merge_result = None
    
    def _fetch_drm_info(self) -> bool:
        """Parse MPD and extract DRM information from raw.mpd file if available, otherwise fetch from URL"""
        try:
            parser = MPDParser(self.mpd_url, headers=self.custom_headers)
            raw_mpd_path = None
            
            # 1) Try temp_analysis/raw.mpd first
            temp_analysis_path = os.path.join(self.output_dir, "temp_analysis", "raw.mpd")
            if os.path.exists(temp_analysis_path):
                raw_mpd_path = os.path.abspath(temp_analysis_path)
            
            # 2) Then check output_dir/raw.mpd
            else:
                output_raw_mpd = os.path.join(self.output_dir, "raw.mpd")
                if os.path.exists(output_raw_mpd):
                    raw_mpd_path = os.path.abspath(output_raw_mpd)
            
            # 3) Parse from file if found, otherwise from URL
            if raw_mpd_path:
                if not parser.parse_from_file(raw_mpd_path):
                    if not parser.parse():
                        return False
            else:
                if not parser.parse():
                    return False
            
            self.drm_info = parser.get_drm_info(self.drm_preference)
            return True
            
        except Exception as e:
            console.print(f"[yellow]Warning: Error parsing MPD for DRM info: {e}")
            return False
    
    def _fetch_decryption_keys(self) -> bool:
        """Fetch decryption keys based on DRM type"""
        if not self.license_url or not self.drm_info or not self.drm_info['pssh']:
            console.print("[yellow]No DRM protection or missing license info")
            return True
        
        drm_type = self.drm_info['selected_drm_type']
        pssh = self.drm_info['pssh']
        
        try:
            if drm_type == DRMSystem.WIDEVINE:
                keys = get_widevine_keys(
                    pssh=pssh,
                    license_url=self.license_url,
                    cdm_device_path=get_wvd_path(),
                    headers=self.license_headers,
                    query_params=self.query_params,
                    key=self.key
                )

            elif drm_type == DRMSystem.PLAYREADY:
                keys = get_playready_keys(
                    pssh=pssh,
                    license_url=self.license_url,
                    cdm_device_path=get_prd_path(),
                    headers=self.license_headers,
                    query_params=self.query_params,
                    key=self.key
                )

            else:
                console.print(f"[red]Unsupported DRM type: {drm_type}")
                self.error = f"Unsupported DRM type: {drm_type}"
                return False
            
            if keys:
                self.decryption_keys = keys
                return True
            
            else:
                console.print("[red]Failed to fetch decryption keys")
                self.error = "Failed to fetch decryption keys"
                return False
                
        except Exception as e:
            console.print(f"[red]Error fetching keys: {e}")
            self.error = f"Key fetch error: {e}"
            return False
    
    def start(self) -> Dict[str, Any]:
        """Main execution flow for downloading DASH content"""
        if self.file_already_exists:
            console.log(f"[yellow]File already exists: [red]{self.output_path}")
            return {
                'path': self.output_path,
                'url': self.mpd_url,
                'msg': 'File already exists',
                'error': None,
                'stopped': False
            }
        
        # Create output directory
        os_manager.create_path(self.output_dir)
        
        # Initialize MediaDownloader
        self.media_downloader = MediaDownloader(
            url=self.mpd_url,
            output_dir=self.output_dir,
            filename=self.filename_base,
            headers=self.custom_headers,
            decryption_keys=None  # We don't have keys yet
        )
        self.media_downloader.configure(
            select_audio_lang=DOWNLOAD_SPECIFIC_AUDIO,
            select_subtitle_lang=DOWNLOAD_SPECIFIC_SUBTITLE,
            enable_logging=True
        )
        
        # Get available streams - this generates raw.mpd in temp_analysis folder
        console.print("[cyan]Analyzing available streams...")
        stream_info = self.media_downloader.get_available_streams()
        
        if stream_info:
            console.print(f"[cyan]Manifest [yellow]{stream_info.manifest_type} [green]Video streams[white]: [red]{len(stream_info.video_streams)}[white], [green]Audio streams[white]: [red]{len(stream_info.audio_streams)}[white], [green]Subtitle streams[white]: [red]{len(stream_info.subtitle_streams)}")
            self.media_downloader.show_table(stream_info)
        
        # Parse MPD for DRM info (uses raw.mpd if available, falls back to URL)
        self._fetch_drm_info()
        
        # Fetch decryption keys if DRM protected
        if self.drm_info and self.drm_info['available_drm_types']:
            if not self._fetch_decryption_keys():
                return {
                    'path': None,
                    'url': self.mpd_url,
                    'msg': f'Failed to fetch decryption keys: {self.error}',
                    'error': self.error,
                    'stopped': True
                }
        
        # Set decryption keys on the existing MediaDownloader instance
        self.media_downloader.set_keys(self.decryption_keys if self.decryption_keys else None)
        
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
                'url': self.mpd_url,
                'msg': f'Download failed: {status.error_message or "Unknown error"}',
                'error': status.error_message,
                'stopped': True
            }
        
        # Merge files using FFmpeg
        final_file = self._merge_files(status)
        
        if not final_file or not os.path.exists(final_file):
            return {
                'path': None,
                'url': self.mpd_url,
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
            'url': self.mpd_url,
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
                    # Remove intermediate file if different
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
    
    def get_status(self):
        """Returns status dict for external use"""
        return {
            "path": self.output_path if os.path.exists(self.output_path) else None,
            "error": self.error,
            "stopped": self.error is not None
        }