# 21.04.25

import sys
import time
import logging
import threading
from collections import deque


# External libraries
import psutil
from tqdm import tqdm


# Internal utilities
from StreamingCommunity.Util.color import Colors
from StreamingCommunity.Util.config_json import get_use_large_bar
from StreamingCommunity.Util.os import internet_manager


class M3U8_Ts_Estimator:
    def __init__(self, total_segments: int, segments_instance=None):
        """
        Initialize the M3U8_Ts_Estimator object.
        
        Parameters:
            - total_segments (int): Length of total segments to download.
        """
        self.ts_file_sizes = []
        self.now_downloaded_size = 0
        self.total_segments = total_segments
        self.segments_instance = segments_instance
        self.lock = threading.Lock()
        self.speed = {"upload": "N/A", "download": "N/A"}

        if get_use_large_bar():
            logging.debug("USE_LARGE_BAR is True, starting speed capture thread")
            self.speed_thread = threading.Thread(target=self.capture_speed)
            self.speed_thread.daemon = True
            self.speed_thread.start()

        else:
            logging.debug("USE_LARGE_BAR is False, speed capture thread not started")

    def add_ts_file(self, size: int, size_download: int, duration: float):
        """Add a file size to the list of file sizes."""
        if size <= 0 or size_download <= 0 or duration <= 0:
            logging.error(f"Invalid input values: size={size}, size_download={size_download}, duration={duration}")
            return

        self.ts_file_sizes.append(size)
        self.now_downloaded_size += size_download
        logging.debug(f"Current total downloaded size: {self.now_downloaded_size}")

    def capture_speed(self, interval: float = 1):
        """Capture the internet speed periodically."""
        last_upload, last_download = 0, 0
        speed_buffer = deque(maxlen=3)
        
        while True:
            try:
                io_counters = psutil.net_io_counters()
                if not io_counters:
                    raise ValueError("No IO counters available")
                
                current_upload, current_download = io_counters.bytes_sent, io_counters.bytes_recv
                if last_upload and last_download:
                    upload_speed = (current_upload - last_upload) / interval
                    download_speed = (current_download - last_download) / interval
                    speed_buffer.append(max(0, download_speed))
                    
                    with self.lock:
                        self.speed = {
                            "upload": internet_manager.format_transfer_speed(max(0, upload_speed)),
                            "download": internet_manager.format_transfer_speed(sum(speed_buffer) / len(speed_buffer))
                        }
                        logging.debug(f"Updated speeds - Upload: {self.speed['upload']}, Download: {self.speed['download']}")
                
                last_upload, last_download = current_upload, current_download
            except Exception as e:
                logging.error(f"Error in speed capture: {str(e)}")
                self.speed = {"upload": "N/A", "download": "N/A"}
            
            time.sleep(interval)

    def calculate_total_size(self) -> str:
        """
        Calculate the total size of the files.

        Returns:
            str: The mean size of the files in a human-readable format.
        """
        try:
            total_size = sum(self.ts_file_sizes)
            mean_size = total_size / len(self.ts_file_sizes)
            return internet_manager.format_file_size(mean_size)

        except Exception as e:
            logging.error("An unexpected error occurred: %s", e)
            return "Error"
    
    def update_progress_bar(self, total_downloaded: int, duration: float, progress_counter: tqdm) -> None:
        try:
            self.add_ts_file(total_downloaded * self.total_segments, total_downloaded, duration)
            
            file_total_size = self.calculate_total_size()
            number_file_total_size = file_total_size.split(' ')[0]
            units_file_total_size = file_total_size.split(' ')[1]
            
            if get_use_large_bar():
                speed_data = self.speed['download'].split(" ")
                
                if len(speed_data) >= 2:
                    average_internet_speed = speed_data[0]
                    average_internet_unit = speed_data[1]
                else:
                    average_internet_speed = "N/A"
                    average_internet_unit = ""
                
                retry_count = self.segments_instance.active_retries if self.segments_instance else 0
                progress_str = (
                    f"{Colors.GREEN}{number_file_total_size} {Colors.WHITE}< {Colors.RED}{units_file_total_size}"
                    f"{Colors.WHITE} {Colors.CYAN}{average_internet_speed} {Colors.RED}{average_internet_unit}"
                    f"{Colors.WHITE}, {Colors.GREEN}CRR {Colors.RED}{retry_count} "
                )
                
            else:
                retry_count = self.segments_instance.active_retries if self.segments_instance else 0
                progress_str = (
                    f"{Colors.GREEN}{number_file_total_size} {Colors.WHITE}< {Colors.RED}{units_file_total_size}"
                    f"{Colors.WHITE}, {Colors.GREEN}CRR {Colors.RED}{retry_count} "
                )
            
            progress_counter.set_postfix_str(progress_str)
            
        except Exception as e:
            logging.error(f"Error updating progress bar: {str(e)}")