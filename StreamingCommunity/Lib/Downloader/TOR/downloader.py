# 23.06.24

import os
import re
import sys
import time
import shutil
import psutil
import logging


# External library
from rich.console import Console


# Internal utilities
from StreamingCommunity.Util.color import Colors
from StreamingCommunity.Util.os import internet_manager
from StreamingCommunity.Util.config_json import config_manager, get_use_large_bar


# External libraries
from tqdm import tqdm
import qbittorrentapi


# Tor config
HOST = config_manager.get_dict('QBIT_CONFIG', 'host')
PORT = config_manager.get_dict('QBIT_CONFIG', 'port')
USERNAME = config_manager.get_dict('QBIT_CONFIG', 'user')
PASSWORD = config_manager.get_dict('QBIT_CONFIG', 'pass')


# Variable
REQUEST_TIMEOUT = config_manager.get_float('REQUESTS', 'timeout')
console = Console()


class TOR_downloader:
    def __init__(self):
        """
        Initializes the TorrentManager instance.
        
        Parameters:
            - host (str): IP address or hostname of the qBittorrent Web UI.
            - port (int): Port of the qBittorrent Web UI.
            - username (str): Username for accessing qBittorrent.
            - password (str): Password for accessing qBittorrent.
        """
        try:
            console.print(f"[cyan]Connect to: [green]{HOST}:{PORT}")
            self.qb = qbittorrentapi.Client(
                host=HOST,
                port=PORT,
                username=USERNAME,
                password=PASSWORD
            )

        except:
            logging.error("Start qbittorrent first.")
            sys.exit(0)
        
        self.username = USERNAME
        self.password = PASSWORD
        self.latest_torrent_hash = None
        self.output_file = None
        self.file_name = None

        self.login()

    def login(self):
        """
        Logs into the qBittorrent Web UI.
        """
        try:
            self.qb.auth_log_in()
            self.logged_in = True
            logging.info("Successfully logged in to qBittorrent.")

        except Exception as e:
            logging.error(f"Failed to log in: {str(e)}")
            self.logged_in = False

    def delete_magnet(self, torrent_info):
        """
        Deletes a torrent if it is not downloadable (no seeds/peers).
        
        Parameters:
            - torrent_info: Object containing torrent information obtained from the qBittorrent API.
        """
        if (int(torrent_info.dlspeed) == 0 and 
            int(torrent_info.num_leechs) == 0 and 
            int(torrent_info.num_seeds) == 0):
            
            console.print(f"[bold red]Torrent not downloadable. Removing...[/bold red]")
            try:
                self.qb.torrents_delete(delete_files=True, torrent_hashes=torrent_info.hash)
            except Exception as delete_error:
                logging.error(f"Error while removing torrent: {delete_error}")
            
            self.latest_torrent_hash = None

    def add_magnet_link(self, magnet_link):
        """
        Adds a magnet link and retrieves detailed torrent information.
        
        Arguments:
            magnet_link (str): Magnet link to add.
        
        Returns:
            dict: Information about the added torrent, or None in case of error.
        """
        magnet_hash_match = re.search(r'urn:btih:([0-9a-fA-F]+)', magnet_link)
        if not magnet_hash_match:
            raise ValueError("Magnet link hash not found")
        
        magnet_hash = magnet_hash_match.group(1).lower()
        
        # Extract the torrent name, if available
        name_match = re.search(r'dn=([^&]+)', magnet_link)
        torrent_name = name_match.group(1).replace('+', ' ') if name_match else "Name not available"
        
        # Save the timestamp before adding the torrent
        before_add_time = time.time()
        
        console.print(f"[cyan]Adding magnet link ...")
        self.qb.torrents_add(urls=magnet_link)
        
        time.sleep(1)
        
        torrents = self.qb.torrents_info()
        matching_torrents = [
            t for t in torrents 
            if (t.hash.lower() == magnet_hash) or (getattr(t, 'added_on', 0) > before_add_time)
        ]
        
        if not matching_torrents:
            raise ValueError("No matching torrent found")
        
        torrent_info = matching_torrents[0]
        
        console.print("\n[bold green]Added Torrent Details:[/bold green]")
        console.print(f"[yellow]Name:[/yellow] {torrent_info.name or torrent_name}")
        console.print(f"[yellow]Hash:[/yellow] {torrent_info.hash}")
        print()

        self.latest_torrent_hash = torrent_info.hash
        self.output_file = torrent_info.content_path
        self.file_name = torrent_info.name

        # Wait and verify if the download is possible
        time.sleep(5)
        self.delete_magnet(self.qb.torrents_info(torrent_hashes=self.latest_torrent_hash)[0])
        
        return torrent_info

    def start_download(self):
        """
        Starts downloading the added torrent and monitors its progress.
        """
        if self.latest_torrent_hash is not None:
            try:

                # Custom progress bar for mobile and PC
                if get_use_large_bar():
                    bar_format = (
                        f"{Colors.YELLOW}[TOR] {Colors.WHITE}({Colors.CYAN}video{Colors.WHITE}): "
                        f"{Colors.RED}{{percentage:.2f}}% {Colors.MAGENTA}{{bar}} {Colors.WHITE}[ "
                        f"{Colors.YELLOW}{{elapsed}} {Colors.WHITE}< {Colors.CYAN}{{remaining}}{{postfix}} {Colors.WHITE}]"
                    )

                else:
                    bar_format = (
                        f"{Colors.YELLOW}Proc{Colors.WHITE}: "
                        f"{Colors.RED}{{percentage:.2f}}% {Colors.WHITE}| "
                        f"{Colors.CYAN}{{remaining}}{{postfix}} {Colors.WHITE}]"
                    )

                progress_bar = tqdm(
                    total=100,
                    ascii='░▒█',
                    bar_format=bar_format,
                    unit_scale=True,
                    unit_divisor=1024,
                    mininterval=0.05
                )

                with progress_bar as pbar:
                    while True:

                        torrent_info = self.qb.torrents_info(torrent_hashes=self.latest_torrent_hash)[0]
                        self.save_path = torrent_info.save_path
                        self.torrent_name = torrent_info.name

                        progress = torrent_info.progress * 100
                        pbar.n = progress

                        download_speed = torrent_info.dlspeed
                        total_size = torrent_info.size
                        downloaded_size = torrent_info.downloaded

                        # Format the downloaded size
                        downloaded_size_str = internet_manager.format_file_size(downloaded_size)
                        downloaded_size = downloaded_size_str.split(' ')[0]

                        # Safely format the total size
                        total_size_str = internet_manager.format_file_size(total_size)
                        total_size_parts = total_size_str.split(' ')
                        if len(total_size_parts) >= 2:
                            total_size = total_size_parts[0]
                            total_size_unit = total_size_parts[1]
                        else:
                            total_size = total_size_str
                            total_size_unit = ""

                        # Safely format the average download speed
                        average_internet_str = internet_manager.format_transfer_speed(download_speed)
                        average_internet_parts = average_internet_str.split(' ')
                        if len(average_internet_parts) >= 2:
                            average_internet = average_internet_parts[0]
                            average_internet_unit = average_internet_parts[1]
                        else:
                            average_internet = average_internet_str
                            average_internet_unit = ""

                        if get_use_large_bar():
                            pbar.set_postfix_str(
                                f"{Colors.WHITE}[ {Colors.GREEN}{downloaded_size} {Colors.WHITE}< {Colors.GREEN}{total_size} {Colors.RED}{total_size_unit} "
                                f"{Colors.WHITE}| {Colors.CYAN}{average_internet} {Colors.RED}{average_internet_unit}"
                            )
                        else:
                            pbar.set_postfix_str(
                                f"{Colors.WHITE}[ {Colors.GREEN}{downloaded_size}{Colors.RED} {total_size} "
                                f"{Colors.WHITE}| {Colors.CYAN}{average_internet} {Colors.RED}{average_internet_unit}"
                            )
                        
                        pbar.refresh()
                        time.sleep(0.2)

                        if int(progress) == 100:
                            break

            except KeyboardInterrupt:
                logging.info("Download process interrupted.")

    def is_file_in_use(self, file_path: str) -> bool:
        """
        Checks if a file is being used by any process.
        
        Parameters:
            - file_path (str): The file path to check.
            
        Returns:
            - bool: True if the file is in use, False otherwise.
        """
        for proc in psutil.process_iter(['open_files']):
            try:
                if any(file_path == f.path for f in proc.info['open_files'] or []):
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        return False

    def move_downloaded_files(self, destination: str):
        """
        Moves the downloaded files of the most recent torrent to a new location.
        
        Parameters:
            - destination (str): Destination folder.
            
        Returns:
            - bool: True if the move was successful, False otherwise.
        """
        console.print(f"[cyan]Destination folder: [red]{destination}")
        
        try:
            timeout = 5
            elapsed = 0
            
            while self.is_file_in_use(self.output_file) and elapsed < timeout:
                time.sleep(1)
                elapsed += 1
            
            if elapsed == timeout:
                raise Exception(f"File '{self.output_file}' is in use and could not be moved.")

            os.makedirs(destination, exist_ok=True)

            try:
                shutil.move(self.output_file, destination)
            except OSError as e:
                if e.errno == 17:  # Error when moving between different disks
                    shutil.copy2(self.output_file, destination)
                    os.remove(self.output_file)
                else:
                    raise

            time.sleep(5)
            last_torrent = self.qb.torrents_info()[-1]
            self.qb.torrents_delete(delete_files=True, torrent_hashes=last_torrent.hash)
            return True

        except Exception as e:
            print(f"Error moving file: {e}")
            return False