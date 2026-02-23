# Quick Start: Download Queue Feature

## 5-Minute Setup

### Step 1: Search and Add Items to Queue

Run the interactive search:
```bash
python -m StreamingCommunity --global
```

**Process**:
1. Enter your search term (e.g., "Inception")
2. Select search sites (choose "1" for all sites)
3. Browse results and select a movie
4. When asked "What would you like to do?", choose **"2. Add to queue"**
5. Repeat: Search for another movie and add to queue
6. When done adding items, choose **"3. Search for another movie"** or **"4. Cancel"**

### Step 2: View Your Queue

```bash
python -m StreamingCommunity -q status
```

You'll see a table like:
```
┏━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━┓
┃ # ┃ Title                    ┃ Type       ┃ Source               ┃ Status     ┃ Progress ┃
┡━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━┩
│ 1 │ Inception                │ Film       │ StreamingCommunity   │ pending    │ —        │
│ 2 │ The Dark Knight          │ Film       │ StreamingCommunity   │ pending    │ —        │
│ 3 │ Interstellar             │ Film       │ StreamingCommunity   │ pending    │ —        │
└───┴──────────────────────────┴────────────┴──────────────────────┴────────────┴──────────┘
```

### Step 3: Download Everything

```bash
python -m StreamingCommunity -q download
```

The system will:
1. Show you each item being downloaded
2. Download them one by one
3. Show progress for each
4. Mark as completed when done
5. Skip any that fail and continue with the next

---

## Common Commands

| Task | Command |
|------|---------|
| View queue items | `python -m StreamingCommunity -q status` |
| See queue stats | `python -m StreamingCommunity -q summary` |
| Start downloading | `python -m StreamingCommunity -q download` |
| Clear all items | `python -m StreamingCommunity -q clear` |
| Remove one item | `python -m StreamingCommunity -q remove <id>` |
| Save queue | `python -m StreamingCommunity -q export backup.json` |
| Load queue | `python -m StreamingCommunity -q import backup.json` |

---

## Real-World Example

### Scenario: Build a "Watch Later" list

**Day 1: Add movies**
```bash
# Search and add several movies
python -m StreamingCommunity --global
# → Search "Marvel", add 3 movies to queue
# → Search "Inception", add it
# → Search "Interstellar", add it
# → Exit
```

**Check what we have**:
```bash
python -m StreamingCommunity -q status
# Output: 5 items pending
```

**Save it for later**:
```bash
python -m StreamingCommunity -q export watch_later.json
```

**Day 2: Download everything**
```bash
# Load the queue
python -m StreamingCommunity -q import watch_later.json

# Start downloading all 5 movies
python -m StreamingCommunity -q download
```

The system will:
- Download movie 1 (Avengers)
- Then movie 2 (Avengers: Age of Ultron)
- Then movie 3 (Avengers: Infinity War)
- Then Inception
- Then Interstellar

All automatically, one after another!

---

## Understanding the Queue States

| Status | Meaning |
|--------|---------|
| **pending** | Waiting to be downloaded |
| **downloading** | Currently being downloaded |
| **completed** | Successfully downloaded ✓ |
| **failed** | Download failed (check logs) |

After download completes, you'll be asked if you want to remove completed items:
```
Remove completed items from queue? (y/n)
```

If you choose "yes", only pending and failed items remain.

---

## Useful Workflows

### 1. **Batch Download Overnight**
```bash
# Add 20 movies to queue
python -m StreamingCommunity --global
# ... add movies ...

# Save queue
python -m StreamingCommunity -q export night_queue.json

# Later: Start download (monitor if needed)
python -m StreamingCommunity -q import night_queue.json
python -m StreamingCommunity -q download
```

### 2. **Organize by Source**
```bash
# Create queue for one streaming service
python -m StreamingCommunity --global
# ... search and add only from Netflix via global search ...

# Save it
python -m StreamingCommunity -q export netflix_queue.json
```

### 3. **Test Before Bulk Download**
```bash
# Add one movie as test
python -m StreamingCommunity --global
# ... add 1 movie ...

# Download to verify it works
python -m StreamingCommunity -q download

# If successful, add more items and download again
```

### 4. **Remove Problem Items**
```bash
# View what's in queue
python -m StreamingCommunity -q status

# If one item has "failed" status, remove it
python -m StreamingCommunity -q remove <id-of-failed-item>

# Try downloading again
python -m StreamingCommunity -q download
```

---

## Troubleshooting

**Q: How do I see which items are being downloaded?**
```bash
python -m StreamingCommunity -q status
```
Items with "downloading" status are currently being processed.

**Q: I added items but don't see them**
```bash
python -m StreamingCommunity -q summary
```
Shows total count. If 0, nothing was added. Try adding again.

**Q: I want to stop the download**
Press `Ctrl+C` in the terminal. The queue will be saved, and you can resume later.

**Q: Can I download items in a different order?**
Currently, downloads are in the order items were added (FIFO). To change order, export queue, manually edit the JSON to reorder items, then import again.

**Q: What if a download fails?**
The item status will show "failed" with an error message. You can:
- Try downloading again
- Remove the failed item
- Continue downloading other items

---

## File Storage

Your queue is stored in:
```
~/.streamingcommunity/download_queue.json
```

This is a regular JSON file. You can:
- Back it up
- Share it with others
- Edit it manually (if needed)
- Delete it to reset (queue will become empty)

---

## Advanced: Save/Load Queues

### Save queue with descriptive name
```bash
python -m StreamingCommunity -q export "my_favorites_$(date +%Y%m%d).json"
```

### List your saved queues
```bash
ls ~/.streamingcommunity/*.json
```

### Merge two queue files
```bash
# Load first queue
python -m StreamingCommunity -q import queue1.json

# Import second queue and merge
python -m StreamingCommunity -q import queue2.json
# When asked "Merge with existing queue?", choose "y"

# View combined queue
python -m StreamingCommunity -q status

# Download all
python -m StreamingCommunity -q download
```

---

## Next Steps

1. **Try it out**: Run `python -m StreamingCommunity --global` and add a movie to queue
2. **View results**: Run `python -m StreamingCommunity -q status`
3. **Download**: Run `python -m StreamingCommunity -q download`
4. **Explore**: Check the full documentation in `QUEUE_FEATURE_GUIDE.md`

**Happy downloading!** 🎬
