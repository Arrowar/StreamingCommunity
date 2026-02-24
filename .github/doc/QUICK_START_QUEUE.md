```markdown
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

... (content omitted here; full guide is in the queue feature guide) ...

```
