# 22.02.26

from rich.console import Console
from rich.prompt import Prompt
from StreamingCommunity.source.batch_downloader import BatchDownloader


# Variable
console = Console()
msg = Prompt()
downloader = BatchDownloader()


def queue_command(action: str = None, args: list = None) -> None:
    """
    Handle queue management commands.
    
    Parameters:
        action (str): The queue action (status, download, clear, remove, etc.)
        args (list): Additional arguments for the action
    """
    if action is None:
        # Show menu
        display_queue_menu()
        return
    
    action = action.lower().strip()
    
    if action == "status" or action == "view":
        downloader.get_queue_status()
    
    elif action == "download" or action == "start":
        download_from_queue()
    
    elif action == "clear":
        if msg.ask("[red]Are you sure you want to clear the entire queue? (y/n)", 
                  choices=["y", "n"], default="n") == "y":
            downloader.clear_queue()
        else:
            console.print("[yellow]Cancelled")
    
    elif action == "summary":
        downloader.display_queue_summary()
    
    elif action == "remove":
        if args and len(args) > 0:
            item_id = args[0]
            downloader.remove_from_queue(item_id)
        else:
            console.print("[red]Please provide an item ID to remove")
    
    elif action == "export":
        export_queue_to_file()
    
    elif action == "import":
        import_queue_from_file()
    
    else:
        console.print(f"[red]Unknown action: {action}")
        display_queue_menu()


def display_queue_menu() -> None:
    """Display the queue management menu."""
    console.print("\n[green]Queue Management Commands:")
    console.print("[cyan]  queue status        - View items in queue")
    console.print("[cyan]  queue summary       - View queue statistics")
    console.print("[cyan]  queue download      - Start downloading queue")
    console.print("[cyan]  queue remove <id>   - Remove item from queue")
    console.print("[cyan]  queue clear         - Clear entire queue")
    console.print("[cyan]  queue export <file> - Export queue to file")
    console.print("[cyan]  queue import <file> - Import queue from file")
    console.print("[cyan]  queue help          - Show this menu")


def download_from_queue() -> None:
    """Start downloading items from the queue."""
    queue_size = downloader.download_queue.get_queue_size()
    
    if queue_size == 0:
        console.print("[yellow]Queue is empty! Add items first using global search.")
        return
    
    downloader.display_queue_summary()
    
    if msg.ask(f"\n[green]Download {queue_size} items? (y/n)", 
              choices=["y", "n"], default="y") == "y":
        downloader.download_queue_sequentially()
    else:
        console.print("[yellow]Download cancelled")


def export_queue_to_file() -> None:
    """Export queue to a file."""
    export_path = msg.ask("[green]Enter export file path", default="download_queue.json")
    
    if downloader.export_queue(export_path):
        console.print(f"[green]✓ Queue saved to {export_path}")
    else:
        console.print("[red]✗ Failed to export queue")


def import_queue_from_file() -> None:
    """Import queue from a file."""
    import_path = msg.ask("[green]Enter import file path")
    
    if not import_path:
        console.print("[yellow]Cancelled")
        return
    
    merge = msg.ask("[green]Merge with existing queue? (y/n)", 
                   choices=["y", "n"], default="n") == "y"
    
    if downloader.import_queue(import_path, merge):
        console.print(f"[green]✓ Queue loaded from {import_path}")
    else:
        console.print("[red]✗ Failed to import queue")
