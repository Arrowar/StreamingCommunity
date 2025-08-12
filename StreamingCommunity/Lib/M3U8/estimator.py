# 21.04.25

import time
import logging
import threading
from collections import deque


# External libraries
import psutil
from tqdm import tqdm


# Internal utilities
from StreamingCommunity.Util.color import Colors
from StreamingCommunity.Util.os import internet_manager


class M3U8_Ts_Estimator:
    def __init__(self, total_segments: int, segments_instance=None):
        """
        Initialize the M3U8_Ts_Estimator object.
        
        Parameters:
            - total_segments (int): Length of total segments to download.
        """
        self.ts_file_sizes = []
        self.total_segments = total_segments
        self.segments_instance = segments_instance
        self.lock = threading.Lock()
        self.speed = {"upload": "N/A", "download": "N/A"}
        self._running = True
        
        self.speed_thread = threading.Thread(target=self.capture_speed)
        self.speed_thread.daemon = True
        self.speed_thread.start()

    def __del__(self):
        """Ensure thread is properly stopped when the object is destroyed."""
        self._running = False
        
    def add_ts_file(self, size: int):
        """Add a file size to the list of file sizes."""
        if size <= 0:
            logging.error(f"Invalid input values: size={size}")
            return

        self.ts_file_sizes.append(size)

    def capture_speed(self, interval: float = 1.5):
        """Capture the internet speed periodically with improved efficiency."""
        last_upload, last_download = 0, 0
        speed_buffer = deque(maxlen=3)
        
        while self._running:
            try:
                # Get IO counters only once per loop to reduce function calls
                io_counters = psutil.net_io_counters()
                if not io_counters:
                    raise ValueError("No IO counters available")
                
                current_upload, current_download = io_counters.bytes_sent, io_counters.bytes_recv
                
                if last_upload and last_download:
                    upload_speed = (current_upload - last_upload) / interval
                    download_speed = (current_download - last_download) / interval
                    
                    # Only update buffer when we have valid data
                    if download_speed > 0:
                        speed_buffer.append(download_speed)
                    
                    # Use a more efficient approach for thread synchronization
                    avg_speed = sum(speed_buffer) / len(speed_buffer) if speed_buffer else 0
                    formatted_upload = internet_manager.format_transfer_speed(max(0, upload_speed))
                    formatted_download = internet_manager.format_transfer_speed(avg_speed)
                    
                    # Minimize lock time by preparing data outside the lock
                    with self.lock:
                        self.speed = {
                            "upload": formatted_upload,
                            "download": formatted_download
                        }
                
                last_upload, last_download = current_upload, current_download
                
            except Exception as e:
                if self._running:  # Only log if we're still supposed to be running
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
            # Only do calculations if we have data
            if not self.ts_file_sizes:
                return "0 B"
                
            total_size = sum(self.ts_file_sizes)
            mean_size = total_size / len(self.ts_file_sizes)
            return internet_manager.format_file_size(mean_size)

        except Exception as e:
            logging.error("An unexpected error occurred: %s", e)
            return "Error"
    
    def update_progress_bar(self, total_downloaded: int, progress_counter: tqdm) -> None:
        try:
            self.add_ts_file(total_downloaded * self.total_segments)
            
            file_total_size = self.calculate_total_size()
            if file_total_size == "Error":
                return
                
            number_file_total_size = file_total_size.split(' ')[0]
            units_file_total_size = file_total_size.split(' ')[1]
            
            # Get speed data outside of any locks
            speed_data = ["N/A", ""]
            with self.lock:
                download_speed = self.speed['download']
            
            if download_speed != "N/A":
                speed_data = download_speed.split(" ")
            
            average_internet_speed = speed_data[0] if len(speed_data) >= 1 else "N/A"
            average_internet_unit = speed_data[1] if len(speed_data) >= 2 else ""
            
            progress_str = (
                f"{Colors.GREEN}{number_file_total_size} {Colors.RED}{units_file_total_size}"
                f"{Colors.WHITE}, {Colors.CYAN}{average_internet_speed} {Colors.RED}{average_internet_unit} "
                #f"{Colors.WHITE}, {Colors.GREEN}CRR {Colors.RED}{retry_count} "
            )
            
            progress_counter.set_postfix_str(progress_str)
            
        except Exception as e:
            logging.error(f"Error updating progress bar: {str(e)}")