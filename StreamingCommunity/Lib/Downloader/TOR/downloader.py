# 23.06.24

import os
import re
import sys
import time
import psutil
import logging
from pathlib import Path


# External libraries
from rich.console import Console
from tqdm import tqdm
import qbittorrentapi


# Internal utilities
from StreamingCommunity.Util.color import Colors
from StreamingCommunity.Util.os import internet_manager
from StreamingCommunity.Util.config_json import config_manager
from StreamingCommunity.Api.http_api import JOB_MANAGER


# Configuration
HOST = config_manager.get('QBIT_CONFIG', 'host')
PORT = config_manager.get('QBIT_CONFIG', 'port')
USERNAME = config_manager.get('QBIT_CONFIG', 'user')
PASSWORD = config_manager.get('QBIT_CONFIG', 'pass')

REQUEST_TIMEOUT = config_manager.get_float('REQUESTS', 'timeout')
console = Console()


class TOR_downloader:
    def __init__(self):
        """
        Initializes the TorrentDownloader instance and connects to qBittorrent.
        """
        self.console = Console()
        self.latest_torrent_hash = None
        self.output_file = None
        self.file_name = None
        self.save_path = None
        self.torrent_name = None
        
        self._connect_to_client()
    
    def _connect_to_client(self):
        """
        Establishes connection to qBittorrent client using configuration parameters.
        """
        self.console.print(f"[cyan]Connecting to qBittorrent: [green]{HOST}:{PORT}")
        
        try:
            # Create client with connection settings and timeouts
            self.qb = qbittorrentapi.Client(
                host=HOST,
                port=PORT,
                username=USERNAME,
                password=PASSWORD,
                VERIFY_WEBUI_CERTIFICATE=False,
                REQUESTS_ARGS={'timeout': REQUEST_TIMEOUT}
            )
            
            # Test connection and login
            self.qb.auth_log_in()
            qb_version = self.qb.app.version
            self.console.print(f"[green]Successfully connected to qBittorrent v{qb_version}")
            
        except Exception as e:
            logging.error(f"Unexpected error: {str(e)}")
            self.console.print(f"[bold red]Error initializing qBittorrent client: {str(e)}[/bold red]")
            sys.exit(1)
    
    def add_magnet_link(self, magnet_link, save_path=None):
        """
        Adds a magnet link to qBittorrent and retrieves torrent information.
        
        Args:
            magnet_link (str): Magnet link to add to qBittorrent
            save_path (str, optional): Directory where to save the downloaded files
            
        Returns:
            TorrentDictionary: Information about the added torrent
            
        Raises:
            ValueError: If magnet link is invalid or torrent can't be added
        """
        # Extract hash from magnet link
        magnet_hash_match = re.search(r'urn:btih:([0-9a-fA-F]+)', magnet_link)
        if not magnet_hash_match:
            raise ValueError("Invalid magnet link: hash not found")
        
        magnet_hash = magnet_hash_match.group(1).lower()
        
        # Extract torrent name from magnet link if available
        name_match = re.search(r'dn=([^&]+)', magnet_link)
        torrent_name = name_match.group(1).replace('+', ' ') if name_match else "Unknown"
        
        # Record timestamp before adding torrent for identification
        before_add_time = time.time()
        
        self.console.print(f"[cyan]Adding magnet link for: [yellow]{torrent_name}")
        
        # Prepare save path
        if save_path:
            self.console.print(f"[cyan]Setting save location to: [green]{save_path}")
            
            # Ensure save path exists
            os.makedirs(save_path, exist_ok=True)
        
        # Add the torrent with save options
        add_options = {
            "urls": magnet_link,
            "use_auto_torrent_management": False,  # Don't use automatic management
            "is_paused": False,                    # Start download immediately
            "tags": ["StreamingCommunity"]         # Add tag for easy identification
        }
        
        # If save_path is provided, add it to options
        if save_path:
            add_options["save_path"] = save_path
        
        add_result = self.qb.torrents_add(**add_options)
        
        if not add_result == "Ok.":
            raise ValueError(f"Failed to add torrent: {add_result}")
        
        # Wait for torrent to be recognized by the client
        time.sleep(1.5)
        
        # Find the newly added torrent
        matching_torrents = self._find_torrent(magnet_hash, before_add_time)
        
        if not matching_torrents:
            raise ValueError("Torrent was added but couldn't be found in client")
        
        torrent_info = matching_torrents[0]
        
        # Store relevant information
        self.latest_torrent_hash = torrent_info.hash
        self.output_file = torrent_info.content_path
        self.file_name = torrent_info.name
        self.save_path = torrent_info.save_path
        
        # Display torrent information
        self._display_torrent_info(torrent_info)
        
        # Check download viability after a short delay
        time.sleep(3)
        self._check_torrent_viability()
        
        return torrent_info
    
    def _find_torrent(self, magnet_hash=None, timestamp=None):
        """
        Find a torrent by hash or added timestamp.
        
        Args:
            magnet_hash (str, optional): Hash of the torrent to find
            timestamp (float, optional): Timestamp to compare against torrent added_on time
            
        Returns:
            list: List of matching torrent objects
        """
        # Get list of all torrents with detailed information
        torrents = self.qb.torrents_info()
        
        if magnet_hash:
            # First try to find by hash (most reliable)
            hash_matches = [t for t in torrents if t.hash.lower() == magnet_hash]
            if hash_matches:
                return hash_matches
        
        if timestamp:
            # Fallback to finding by timestamp (least recently added torrent after timestamp)
            time_matches = [t for t in torrents if getattr(t, 'added_on', 0) > timestamp]
            if time_matches:
                # Sort by added_on to get the most recently added
                return sorted(time_matches, key=lambda t: getattr(t, 'added_on', 0), reverse=True)
        
        # If we're just looking for the latest torrent
        if not magnet_hash and not timestamp:
            if torrents:
                return [sorted(torrents, key=lambda t: getattr(t, 'added_on', 0), reverse=True)[0]]
        
        return []
    
    def _display_torrent_info(self, torrent_info):
        """
        Display detailed information about a torrent.
        
        Args:
            torrent_info: Torrent object from qBittorrent API
        """
        self.console.print("\n[bold green]Torrent Details:[/bold green]")
        self.console.print(f"[yellow]Name:[/yellow] {torrent_info.name}")
        self.console.print(f"[yellow]Hash:[/yellow] {torrent_info.hash}")
        #self.console.print(f"[yellow]Size:[/yellow] {internet_manager.format_file_size(torrent_info.size)}")
        self.console.print(f"[yellow]Save Path:[/yellow] {torrent_info.save_path}")
        
        # Show additional metadata if available
        if hasattr(torrent_info, 'category') and torrent_info.category:
            self.console.print(f"[yellow]Category:[/yellow] {torrent_info.category}")
        
        if hasattr(torrent_info, 'tags') and torrent_info.tags:
            self.console.print(f"[yellow]Tags:[/yellow] {torrent_info.tags}")
        
        # Show connection info
        self.console.print(f"[yellow]Seeds:[/yellow] {torrent_info.num_seeds} complete, {torrent_info.num_complete} connected")
        self.console.print(f"[yellow]Peers:[/yellow] {torrent_info.num_leechs} incomplete, {torrent_info.num_incomplete} connected")
        print()
    
    def _check_torrent_viability(self):
        """
        Check if the torrent is viable for downloading (has seeds/peers).
        Removes the torrent if it doesn't appear to be downloadable.
        """
        if not self.latest_torrent_hash:
            return
        
        try:
            # Get updated torrent info
            torrent_info = self.qb.torrents_info(torrent_hashes=self.latest_torrent_hash)[0]
            
            # Check if torrent has no activity and no source (seeders or peers)
            if (torrent_info.dlspeed == 0 and 
                torrent_info.num_leechs == 0 and 
                torrent_info.num_seeds == 0 and
                torrent_info.state in ('stalledDL', 'missingFiles', 'error')):
                
                self.console.print("[bold red]Torrent not downloadable. No seeds or peers available. Removing...[/bold red]")
                self._remove_torrent(self.latest_torrent_hash)
                self.latest_torrent_hash = None
                return False
            
            return True
            
        except Exception as e:
            logging.error(f"Error checking torrent viability: {str(e)}")
            return False
    
    def _remove_torrent(self, torrent_hash, delete_files=True):
        """
        Remove a torrent from qBittorrent.
        
        Args:
            torrent_hash (str): Hash of the torrent to remove
            delete_files (bool): Whether to delete associated files
        """
        try:
            self.qb.torrents_delete(delete_files=delete_files, torrent_hashes=torrent_hash)
            self.console.print("[yellow]Torrent removed from client[/yellow]")
        except Exception as e:
            logging.error(f"Error removing torrent: {str(e)}")
    
    def move_completed_torrent(self, destination):
        """
        Move a completed torrent to a new destination using qBittorrent's API
        
        Args:
            destination (str): New destination path
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.latest_torrent_hash:
            self.console.print("[yellow]No active torrent to move[/yellow]")
            return False
            
        try:
            # Make sure destination exists
            os.makedirs(destination, exist_ok=True)
            
            # Get current state of the torrent
            torrent_info = self.qb.torrents_info(torrent_hashes=self.latest_torrent_hash)[0]
            
            if torrent_info.progress < 1.0:
                self.console.print("[yellow]Torrent not yet completed. Cannot move.[/yellow]")
                return False
                
            self.console.print(f"[cyan]Moving torrent to: [green]{destination}")
            
            # Use qBittorrent API to set location
            self.qb.torrents_set_location(location=destination, torrent_hashes=self.latest_torrent_hash)
            
            # Wait a bit for the move operation to complete
            time.sleep(2)
            
            # Verify move was successful
            updated_info = self.qb.torrents_info(torrent_hashes=self.latest_torrent_hash)[0]
            
            if Path(updated_info.save_path) == Path(destination):
                self.console.print(f"[bold green]Successfully moved torrent to {destination}[/bold green]")
                self.save_path = updated_info.save_path
                self.output_file = updated_info.content_path
                return True
            else:
                self.console.print(f"[bold red]Failed to move torrent. Current path: {updated_info.save_path}[/bold red]")
                return False
                
        except Exception as e:
            logging.error(f"Error moving torrent: {str(e)}")
            self.console.print(f"[bold red]Error moving torrent: {str(e)}[/bold red]")
            return False
    
    def start_download(self):
        """
        Start downloading the torrent and monitor its progress with a progress bar.
        """
        if not self.latest_torrent_hash:
            self.console.print("[yellow]No active torrent to download[/yellow]")
            return False
        
        try:
            # Ensure the torrent is started
            self.qb.torrents_resume(torrent_hashes=self.latest_torrent_hash)
            
            # Configure progress bar display format
            bar_format = (
                f"{Colors.YELLOW}[TOR] {Colors.WHITE}({Colors.CYAN}video{Colors.WHITE}): "
                f"{Colors.RED}{{percentage:.2f}}% {Colors.MAGENTA}{{bar}} {Colors.WHITE}[ "
                f"{Colors.YELLOW}{{elapsed}} {Colors.WHITE}< {Colors.CYAN}{{remaining}}{{postfix}} {Colors.WHITE}]"
            )

            # Initialize progress bar
            with tqdm(
                total=100,
                ascii='░▒█',
                bar_format=bar_format,
                unit_scale=True,
                unit_divisor=1024,
                mininterval=0.1
            ) as pbar:
                
                was_downloading = True
                stalled_count = 0
                
                while True:

                    # Get updated torrent information
                    try:
                        torrent_info = self.qb.torrents_info(torrent_hashes=self.latest_torrent_hash)[0]
                    except (IndexError, qbittorrentapi.exceptions.NotFound404Error):
                        self.console.print("[bold red]Torrent no longer exists in client[/bold red]")
                        return False
                    
                    # Store the latest path and name
                    self.save_path = torrent_info.save_path
                    self.torrent_name = torrent_info.name
                    self.output_file = torrent_info.content_path
                    
                    # Update progress
                    progress = torrent_info.progress * 100
                    pbar.n = progress
                    try:
                        JOB_MANAGER.update_progress(progress)
                    except Exception:
                        pass
                    
                    # Get download statistics
                    download_speed = torrent_info.dlspeed
                    total_size = torrent_info.size
                    downloaded_size = torrent_info.downloaded

                    # Format sizes and speeds using the existing functions without modification
                    downloaded_size_str = internet_manager.format_file_size(downloaded_size)
                    total_size_str = internet_manager.format_file_size(total_size)
                    download_speed_str = internet_manager.format_transfer_speed(download_speed)

                    # Parse the formatted strings to extract numbers and units
                    # The format is "X.XX Unit" from the format_file_size and format_transfer_speed functions
                    dl_parts = downloaded_size_str.split(' ')
                    dl_size_num = dl_parts[0] if len(dl_parts) > 0 else "0"
                    dl_size_unit = dl_parts[1] if len(dl_parts) > 1 else "B"

                    total_parts = total_size_str.split(' ')
                    total_size_num = total_parts[0] if len(total_parts) > 0 else "0"
                    total_size_unit = total_parts[1] if len(total_parts) > 1 else "B"

                    speed_parts = download_speed_str.split(' ')
                    speed_num = speed_parts[0] if len(speed_parts) > 0 else "0"
                    speed_unit = ' '.join(speed_parts[1:]) if len(speed_parts) > 1 else "B/s"
                    
                    # Check if download is active
                    currently_downloading = download_speed > 0
                    
                    # Handle stalled downloads
                    if was_downloading and not currently_downloading and progress < 100:
                        stalled_count += 1
                        if stalled_count >= 15:  # 3 seconds (15 * 0.2)
                            pbar.set_description(f"{Colors.RED}Stalled")
                    else:
                        stalled_count = 0
                        pbar.set_description(f"{Colors.GREEN}Active")
                    
                    was_downloading = currently_downloading
                    
                    # Update progress bar display with formatted statistics
                    pbar.set_postfix_str(
                        f"{Colors.GREEN}{dl_size_num} {Colors.RED}{dl_size_unit} {Colors.WHITE}< "
                        f"{Colors.GREEN}{total_size_num} {Colors.RED}{total_size_unit}{Colors.WHITE}, "
                        f"{Colors.CYAN}{speed_num} {Colors.RED}{speed_unit}"
                    )
                    pbar.refresh()
                    
                    # Check for completion
                    if int(progress) == 100:
                        pbar.n = 100
                        pbar.refresh()
                        break
                    
                    # Check torrent state for errors
                    if torrent_info.state in ('error', 'missingFiles', 'unknown'):
                        self.console.print(f"[bold red]Error in torrent: {torrent_info.state}[/bold red]")
                        return False
                    
                    time.sleep(0.3)
                
                self.console.print(f"[bold green]Download complete: {self.torrent_name}[/bold green]")
                return True
                
        except KeyboardInterrupt:
            self.console.print("[yellow]Download process interrupted[/yellow]")
            return False
        
        except Exception as e:
            logging.error(f"Error monitoring download: {str(e)}")
            self.console.print(f"[bold red]Error monitoring download: {str(e)}[/bold red]")
            return False
    
    def is_file_in_use(self, file_path):
        """
        Check if a file is currently being used by any process.
        
        Args:
            file_path (str): Path to the file to check
            
        Returns:
            bool: True if file is in use, False otherwise
        """
        # Convert to absolute path for consistency
        file_path = str(Path(file_path).resolve())
        
        try:
            for proc in psutil.process_iter(['open_files', 'name']):
                try:
                    proc_info = proc.info
                    if 'open_files' in proc_info and proc_info['open_files']:
                        for file_info in proc_info['open_files']:
                            if file_path == file_info.path:
                                return True
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            return False
        
        except Exception as e:
            logging.error(f"Error checking if file is in use: {str(e)}")
            return False
    
    def cleanup(self):
        """
        Clean up resources and perform final operations before shutting down.
        """
        if self.latest_torrent_hash:
            self._remove_torrent(self.latest_torrent_hash)
        
        try:
            self.qb.auth_log_out()
        except Exception:
            pass
