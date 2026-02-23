# 22.02.26

import json
import os
import uuid
import threading
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path


class SingletonMeta(type):
    _instances = {}
    _lock = threading.Lock()

    def __call__(cls, *args, **kwargs):
        with cls._lock:
            if cls not in cls._instances:
                cls._instances[cls] = super().__call__(*args, **kwargs)
            return cls._instances[cls]


class DownloadQueue(metaclass=SingletonMeta):
    """
    Manages a queue of items to download.
    Provides methods to add, remove, list, and persist queue items.
    """
    
    def __init__(self, queue_file: str = None):
        if not hasattr(self, '_initialized'):
            self._initialized = True
            self._init_queue(queue_file)
    
    def _init_queue(self, queue_file: str = None):
        """Initialize the queue manager."""
        self._lock = threading.Lock()
        self.queue: List[Dict[str, Any]] = []
        self.history: List[Dict[str, Any]] = []
        
        # Determine queue file location
        if queue_file:
            self.queue_file = queue_file
        else:
            # Default to config directory
            config_dir = Path.home() / '.streamingcommunity'
            config_dir.mkdir(exist_ok=True)
            self.queue_file = config_dir / 'download_queue.json'
        
        # Load existing queue
        self._load_queue()
    
    def add_item(self, media_item: Dict[str, Any], site_info: Dict[str, Any] = None) -> str:
        """
        Add an item to the download queue.
        
        Args:
            media_item: Dictionary containing media information
            site_info: Dictionary containing site-specific download info
        
        Returns:
            str: The unique ID of the queued item
        """
        with self._lock:
            item_id = str(uuid.uuid4())
            
            queue_item = {
                'id': item_id,
                'title': media_item.get('title') or media_item.get('name', 'Unknown'),
                'type': media_item.get('type') or media_item.get('media_type', 'Unknown'),
                'source': media_item.get('source', 'Unknown'),
                'source_alias': media_item.get('source_alias', ''),
                'added_at': datetime.now().isoformat(),
                'status': 'pending',  # pending, downloading, completed, failed
                'progress': 0,
                'error': None,
                'media_item': media_item,  # Full media item data
                'site_info': site_info or {},  # Site-specific download info
            }
            
            # Only include extra fields if they exist
            for field in ['year', 'id', 'url', 'plot', 'rating']:
                if field in media_item and media_item[field]:
                    queue_item[field] = media_item[field]
            
            self.queue.append(queue_item)
            self._save_queue()
            
            return item_id
    
    def remove_item(self, item_id: str) -> bool:
        """Remove an item from the queue by ID."""
        with self._lock:
            initial_length = len(self.queue)
            self.queue = [item for item in self.queue if item['id'] != item_id]
            
            if len(self.queue) < initial_length:
                self._save_queue()
                return True
            return False
    
    def get_item(self, item_id: str) -> Optional[Dict[str, Any]]:
        """Get a single queue item by ID."""
        with self._lock:
            for item in self.queue:
                if item['id'] == item_id:
                    return item.copy()
            return None
    
    def get_queue(self) -> List[Dict[str, Any]]:
        """Get the current queue (without full media_item data for display)."""
        with self._lock:
            return [
                {
                    'id': item['id'],
                    'title': item['title'],
                    'type': item['type'],
                    'source': item['source'],
                    'status': item['status'],
                    'progress': item['progress'],
                    'added_at': item['added_at'],
                    'error': item['error'],
                }
                for item in self.queue
            ]
    
    def get_queue_full(self) -> List[Dict[str, Any]]:
        """Get the current queue with full data."""
        with self._lock:
            return [item.copy() for item in self.queue]
    
    def update_item_status(self, item_id: str, status: str, progress: float = None, error: str = None) -> bool:
        """Update the status and progress of a queued item."""
        with self._lock:
            for item in self.queue:
                if item['id'] == item_id:
                    item['status'] = status
                    if progress is not None:
                        item['progress'] = progress
                    if error is not None:
                        item['error'] = error
                    self._save_queue()
                    return True
            return False
    
    def get_pending_items(self) -> List[Dict[str, Any]]:
        """Get all pending items that haven't been downloaded yet."""
        with self._lock:
            return [
                item.copy() for item in self.queue 
                if item['status'] == 'pending'
            ]
    
    def get_next_pending(self) -> Optional[Dict[str, Any]]:
        """Get the next pending item in the queue."""
        pending = self.get_pending_items()
        return pending[0] if pending else None
    
    def clear_completed(self) -> int:
        """Remove all completed items from the queue."""
        with self._lock:
            initial_length = len(self.queue)
            completed_items = [item for item in self.queue if item['status'] == 'completed']
            
            # Move completed items to history
            self.history.extend(completed_items)
            
            # Keep only non-completed items
            self.queue = [item for item in self.queue if item['status'] != 'completed']
            
            if len(self.queue) < initial_length:
                self._save_queue()
            
            return initial_length - len(self.queue)
    
    def clear_queue(self) -> int:
        """Clear the entire queue."""
        with self._lock:
            count = len(self.queue)
            self.queue = []
            self._save_queue()
            return count
    
    def get_queue_size(self) -> int:
        """Get the number of items in the queue."""
        with self._lock:
            return len(self.queue)
    
    def is_queue_empty(self) -> bool:
        """Check if queue is empty."""
        with self._lock:
            return len(self.queue) == 0
    
    def _save_queue(self) -> None:
        """Save the queue to a JSON file."""
        try:
            queue_data = {
                'version': '1.0',
                'saved_at': datetime.now().isoformat(),
                'queue': [
                    {
                        'id': item['id'],
                        'title': item['title'],
                        'type': item['type'],
                        'source': item['source'],
                        'source_alias': item['source_alias'],
                        'added_at': item['added_at'],
                        'status': item['status'],
                        'progress': item['progress'],
                        'error': item['error'],
                        'media_item': item['media_item'],
                        'site_info': item['site_info'],
                        **{k: item.get(k) for k in ['year', 'id', 'url', 'plot', 'rating'] if k in item}
                    }
                    for item in self.queue
                ]
            }
            
            os.makedirs(os.path.dirname(self.queue_file), exist_ok=True)
            with open(self.queue_file, 'w') as f:
                json.dump(queue_data, f, indent=2)
        except Exception as e:
            print(f"[ERROR] Failed to save queue: {str(e)}")
    
    def _load_queue(self) -> None:
        """Load the queue from a JSON file if it exists."""
        try:
            if isinstance(self.queue_file, str):
                self.queue_file = Path(self.queue_file)
            
            if self.queue_file.exists():
                with open(self.queue_file, 'r') as f:
                    data = json.load(f)
                    self.queue = data.get('queue', [])
            else:
                self.queue = []
        except Exception as e:
            print(f"[WARNING] Failed to load queue: {str(e)}")
            self.queue = []
    
    def export_queue(self, export_file: str) -> bool:
        """Export queue to a file for backup/sharing."""
        try:
            with self._lock:
                queue_data = {
                    'version': '1.0',
                    'exported_at': datetime.now().isoformat(),
                    'queue': self.queue
                }
                with open(export_file, 'w') as f:
                    json.dump(queue_data, f, indent=2)
            return True
        except Exception as e:
            print(f"[ERROR] Failed to export queue: {str(e)}")
            return False
    
    def import_queue(self, import_file: str, merge: bool = False) -> bool:
        """Import queue from a file."""
        try:
            with open(import_file, 'r') as f:
                data = json.load(f)
                imported_items = data.get('queue', [])
            
            with self._lock:
                if not merge:
                    self.queue = imported_items
                else:
                    # Merge with existing queue, avoiding duplicates
                    existing_ids = {item['id'] for item in self.queue}
                    for item in imported_items:
                        if item['id'] not in existing_ids:
                            self.queue.append(item)
                
                self._save_queue()
            return True
        except Exception as e:
            print(f"[ERROR] Failed to import queue: {str(e)}")
            return False
