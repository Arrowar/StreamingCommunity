```markdown
# Download Queue Feature Documentation

## Overview

The download queue feature allows you to search for multiple movies/TV shows and add them to a list, then download them all sequentially. This is useful when you want to download several items without manually waiting for each one to complete.

## Features

- **Add to Queue**: Search for items and add them to the download queue without starting the download immediately
- **Sequential Download**: Download all queued items one at a time in the order they were added
- **Queue Management**: View, remove, clear, and manage your queue
- **Queue Persistence**: Your queue is automatically saved and persists across sessions
- **Export/Import**: Save your queue to a file for backup or sharing with others
- **Progress Tracking**: Monitor which items are pending, downloading, completed, or failed

## Workflow

### 1. **Search and Add to Queue**

Using the interactive mode:
```bash
python -m StreamingCommunity --global
```

Follow these steps:
1. Search for a movie/series
2. When you find an item, you'll be asked what to do:
   - **Download now**: Start downloading immediately
   - **Add to queue**: Add to the queue for later batch download
   - **Search for another movie**: Continue searching
   - **Cancel**: Exit

### 2. **View Queue Status**

Check what's in your queue:
```bash
python -m StreamingCommunity -q status
```

This shows:
- Item number in queue
- Title
- Type (Film/Serie/Anime)
- Source (streaming platform)
- Current status (pending/downloading/completed/failed)
- Download progress percentage

### 3. **View Queue Summary**

Get quick statistics about your queue:
```bash
python -m StreamingCommunity -q summary
```

Shows:
- Total items in queue
- Number of pending items
- Number currently downloading
- Number completed
- Number with errors

### 4. **Start Batch Download**

Download all queued items sequentially:
```bash
python -m StreamingCommunity -q download
```

Or short form:
```bash
python -m StreamingCommunity -q start
```

The downloader will:
1. Display each item being downloaded
2. Call the appropriate streaming service's download function
3. Update the queue status as each item completes or fails
4. Move to the next item automatically

### 5. **Queue Management Commands**

#### Remove a specific item from queue:
```bash
python -m StreamingCommunity -q remove <item-id>
```

#### Clear entire queue:
```bash
python -m StreamingCommunity -q clear
```

#### Export queue to file (backup):
```bash
python -m StreamingCommunity -q export <file-path>
```

Example:
```bash
python -m StreamingCommunity -q export my_queue.json
```

#### Import queue from file:
```bash
python -m StreamingCommunity -q import <file-path>
```

Example:
```bash
python -m StreamingCommunity -q import my_queue.json
```

When importing, you'll be asked:
- **Merge with existing queue?**: Add to current queue or replace it

## File Locations

### Queue Storage
The queue is automatically saved to: `~/.streamingcommunity/download_queue.json`

This is a JSON file containing:
- All items in your queue
- Their metadata (title, type, source, etc.)
- Current status of each item
- Timestamp of last update

## Examples

### Example 1: Build a queue of movies to download

```bash
# Start searching
python -m StreamingCommunity --global

# Search for "Inception"
# Select it → Choose "Add to queue"
# Search for "The Dark Knight"
# Select it → Choose "Add to queue"
# Search for "Interstellar"
# Select it → Choose "Add to queue"

# Check what we added
python -m StreamingCommunity -q status

# Start the batch download
python -m StreamingCommunity -q download
```

### Example 2: Resume or manage queue

```bash
# See how many items are left
python -m StreamingCommunity -q summary

# Remove an item if we don't want it
python -m StreamingCommunity -q remove <item-id>

# Download the rest
python -m StreamingCommunity -q download
```

### Example 3: Save and restore queue

```bash
# Save your queue for later
python -m StreamingCommunity -q export movies_to_watch.json

# Later, restore it
python -m StreamingCommunity -q import movies_to_watch.json
```

## API Usage (For Developers)

If you're using the queue features programmatically:

```python
from StreamingCommunity.source.queue_manager import DownloadQueue
from StreamingCommunity.source.batch_downloader import BatchDownloader

# Initialize
queue = DownloadQueue()
downloader = BatchDownloader()

# Add items
item = {
    'title': 'My Movie',
    'type': 'Film',
    'source': 'StreamingCommunity',
    'source_alias': 'streamingcommunity_search',
    # ... other item data
}
queue_id = downloader.add_item_to_queue(item)

# View queue
downloader.get_queue_status()

# Download
downloader.download_queue_sequentially()

# Control
downloader.pause_downloads()
downloader.resume_downloads()
downloader.stop_downloads()
```

## Architecture

### Components

1. **DownloadQueue** (`StreamingCommunity/source/queue_manager.py`)
   - Manages the list of items to download
   - Handles persistence to JSON
   - Thread-safe operations

2. **BatchDownloader** (`StreamingCommunity/source/batch_downloader.py`)
   - Coordinates sequential downloading
   - Tracks progress and status
   - Handles user interactions

3. **Queue CLI** (`StreamingCommunity/cli/command/queue.py`)
   - Command-line interface for queue management
   - Integrates with main CLI

4. **Global Search Updates** (`StreamingCommunity/cli/command/global_search.py`)
   - Enhanced with queue option after item selection

## Status Values

Each item in the queue can have these statuses:

- **pending**: Item is in the queue, waiting to be downloaded
- **downloading**: Item is currently being downloaded
- **completed**: Item was successfully downloaded
- **failed**: Item failed to download (check error message)

## Notes

- Queue operations are thread-safe for multi-threaded scenarios
- The queue file is automatically saved after each change
- Export files are in JSON format and can be edited manually if needed
- Failed items remain in the queue for review or retry
- Download order is always first-in-first-out (FIFO)

## Troubleshooting

### Queue file corruption
If the queue file gets corrupted, it will be reset to empty. Simply re-add your items.

### Items stuck in "downloading" status
If the app crashes, items may remain in "downloading" status. Use `queue clear` or manually remove them.

### Import fails
Make sure the JSON file is properly formatted. Export from the app to see the correct format.

## Future Enhancements

Potential improvements:
- Pause/resume individual downloads
- Retry failed items
- Queue prioritization
- Scheduled downloads
- Bandwidth throttling
- Download scheduling (download at specific time)

```
