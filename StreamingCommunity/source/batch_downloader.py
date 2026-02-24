# 22.02.26

from typing import Dict, Any
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt

from StreamingCommunity.source.queue_manager import DownloadQueue
from StreamingCommunity.services._base import load_search_functions


# Variable
console = Console()
msg = Prompt()


class BatchDownloader:
    """
    Manages sequential downloading of items from the download queue.
    Downloads one item at a time and updates queue status.
    """
    
    def __init__(self):
        self.download_queue = DownloadQueue()
        self.search_functions = load_search_functions()
        self.is_running = False
        self.is_paused = False
    
    def get_queue_status(self) -> None:
        """Display the current queue status."""
        queue_items = self.download_queue.get_queue()
        
        if not queue_items:
            console.print("[yellow]Queue is empty!")
            return
        
        console.print(f"\n[green]Queue Status - {len(queue_items)} items")
        console.print("─" * 80)
        
        table = Table(show_header=True, header_style="cyan")
        table.add_column("#", style="dim", width=3)
        table.add_column("Title", min_width=25)
        table.add_column("Type", width=12)
        table.add_column("Source", width=20)
        table.add_column("Status", width=12)
        table.add_column("Progress", width=10)
        
        for i, item in enumerate(queue_items, 1):
            status_color = {
                'pending': 'yellow',
                'downloading': 'cyan',
                'completed': 'green',
                'failed': 'red'
            }.get(item['status'], 'white')
            
            status_display = f"[{status_color}]{item['status']}"
            progress_display = f"{item['progress']:.0f}%" if item['progress'] > 0 else "—"
            
            table.add_row(
                str(i),
                item['title'][:24],
                item['type'],
                item['source'][:19],
                status_display,
                progress_display
            )
        
        console.print(table)
        console.print("─" * 80)
    
    def display_queue_summary(self) -> None:
        """Display a summary of queue statistics."""
        queue_items = self.download_queue.get_queue()
        
        if not queue_items:
            console.print("[yellow]Queue is empty!")
            return
        
        pending = sum(1 for item in queue_items if item['status'] == 'pending')
        downloading = sum(1 for item in queue_items if item['status'] == 'downloading')
        completed = sum(1 for item in queue_items if item['status'] == 'completed')
        failed = sum(1 for item in queue_items if item['status'] == 'failed')
        
        summary = f"""
[cyan]Queue Summary:
  Total items: {len(queue_items)}
  Pending: {pending}
  Downloading: {downloading}
  Completed: {completed}
  Failed: {failed}"""
        
        console.print(summary)
    
    def add_item_to_queue(self, media_item: Dict[str, Any]) -> str:
        """
        Add an item to the queue.
        
        Args:
            media_item: The media item to add
        
        Returns:
            str: The queue item ID
        """
        queue_id = self.download_queue.add_item(media_item)
        console.print(f"[green]✓ Added to queue! (ID: {queue_id})")
        console.print(f"[cyan]Queue size: {self.download_queue.get_queue_size()} items")
        return queue_id
    
    def remove_from_queue(self, item_id: str) -> bool:
        """
        Remove an item from the queue.
        
        Args:
            item_id: The ID of the item to remove
        
        Returns:
            bool: True if successful
        """
        if self.download_queue.remove_item(item_id):
            console.print("[green]✓ Removed from queue")
            return True
        else:
            console.print("[red]✗ Item not found in queue")
            return False
    
    def clear_queue(self) -> None:
        """Clear all items from the queue."""
        count = self.download_queue.clear_queue()
        console.print(f"[green]✓ Cleared {count} items from queue")
    
    def download_queue_sequentially(self, start_from_index: int = 0) -> None:
        """
        Download all pending items in the queue sequentially.
        
        Args:
            start_from_index: Index to start downloading from (0-based)
        """
        pending_items = self.download_queue.get_pending_items()
        
        if not pending_items:
            console.print("[yellow]No pending items in queue!")
            return
        
        self.is_running = True
        total_items = len(pending_items)
        
        console.print(f"\n[green]Starting batch download of {total_items} items...")
        console.print("─" * 80)
        
        for index, item in enumerate(pending_items[start_from_index:], start=start_from_index + 1):
            if not self.is_running:
                console.print("[yellow]Download cancelled by user")
                break
            
            # Display current item info
            panel_text = f"""[cyan]Downloading item {index}/{total_items}
[white]Title: {item['title']}
[white]Type: {item['type']}
[white]Source: {item['source']}"""
            
            console.print(Panel(panel_text, title="[bold cyan]Current Download", expand=False))
            
            # Update status to downloading
            self.download_queue.update_item_status(item['id'], 'downloading', 0)
            
            try:
                # Process the download
                self._download_item(item)
                
                # Mark as completed
                self.download_queue.update_item_status(item['id'], 'completed', 100)
                console.print(f"[green]✓ Download completed: {item['title']}\n")
                
            except Exception as e:
                # Mark as failed
                error_msg = str(e)
                self.download_queue.update_item_status(item['id'], 'failed', error=error_msg)
                console.print(f"[red]✗ Download failed: {item['title']}")
                console.print(f"[red]Error: {error_msg}\n")
        
        self.is_running = False
        
        # Display final summary
        self._display_download_summary()
    
    def _download_item(self, item: Dict[str, Any]) -> None:
        """
        Download a single item using its source's download function.
        
        Args:
            item: The queue item to download
        
        Raises:
            Exception: If download fails
        """
        source_alias = item.get('source_alias')
        
        if not source_alias or source_alias not in self.search_functions:
            raise Exception(f"Invalid source: {source_alias}")
        
        # Get the search function for this source
        func, _ = self.search_functions[source_alias]
        
        # Extract necessary information
        media_item = item.get('media_item', item)
        
        console.print(f"[cyan]Initiating download from {item.get('source')}...")
        
        # Call the download function with the media item
        try:
            func(direct_item=media_item)
        except Exception as e:
            raise Exception(f"Download failed: {str(e)}")
    
    def pause_downloads(self) -> None:
        """Pause the current download queue."""
        self.is_paused = True
        console.print("[yellow]Download paused")
    
    def resume_downloads(self) -> None:
        """Resume paused downloads."""
        self.is_paused = False
        console.print("[green]Download resumed")
    
    def stop_downloads(self) -> None:
        """Stop the current download queue."""
        self.is_running = False
        console.print("[red]Download stopped")
    
    def _display_download_summary(self) -> None:
        """Display a summary after batch download completes."""
        queue_items = self.download_queue.get_queue()
        
        completed = sum(1 for item in queue_items if item['status'] == 'completed')
        failed = sum(1 for item in queue_items if item['status'] == 'failed')
        pending = sum(1 for item in queue_items if item['status'] == 'pending')
        
        summary = f"""
[green]Download Summary:
  Completed: {completed}
  Failed: {failed}
  Pending: {pending}"""
        
        console.print(Panel(summary, title="[bold cyan]Download Complete", expand=False))
        
        # Optionally clear completed items
        if completed > 0:
            if msg.ask("[green]Remove completed items from queue? (y/n)", choices=["y", "n"], default="y") == "y":
                self.download_queue.clear_completed()
                console.print("[green]✓ Cleared completed items")
    
    def export_queue(self, export_path: str) -> bool:
        """
        Export the queue to a file.
        
        Args:
            export_path: Path to save the queue file
        
        Returns:
            bool: True if successful
        """
        if self.download_queue.export_queue(export_path):
            console.print(f"[green]✓ Queue exported to {export_path}")
            return True
        else:
            console.print("[red]✗ Failed to export queue")
            return False
    
    def import_queue(self, import_path: str, merge: bool = False) -> bool:
        """
        Import queue from a file.
        
        Args:
            import_path: Path to the queue file
            merge: If True, merge with existing queue; if False, replace
        
        Returns:
            bool: True if successful
        """
        if self.download_queue.import_queue(import_path, merge):
            console.print(f"[green]✓ Queue imported from {import_path}")
            return True
        else:
            console.print("[red]✗ Failed to import queue")
            return False
