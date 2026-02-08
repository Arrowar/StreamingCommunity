# Requirements

## V1 Requirements (Must Have)

### REQ-001: Python API Server
FastAPI backend that wraps StreamingCommunity Python modules through an abstraction layer. Must import modules directly (not shell execution). Serves REST endpoints and WebSocket connections for the Electron frontend.

### REQ-002: Streaming Service Discovery
API endpoint that returns all available streaming services with metadata (name, category, index). Mirrors `load_search_functions()` from `cli/run.py`.

### REQ-003: Single-Site Search
API endpoint accepting site identifier + search query. Returns structured results with media metadata (title, type, year, poster URL, ID). Uses the lazy-loading pattern from `LazySearchModule`.

### REQ-004: Global Search
API endpoint that searches across all services (or filtered by category). Consolidates results with source attribution. Mirrors `global_search()` from CLI.

### REQ-005: Series Metadata
API endpoint returning seasons and episodes for a series. Mirrors the Django GUI's `series_metadata` endpoint pattern.

### REQ-006: Download Initiation
API endpoint to start a download (movie or specific episodes). Runs in background thread with tracking. Returns download ID for progress monitoring.

### REQ-007: Real-Time Download Progress
WebSocket endpoint streaming download progress (percentage, speed, ETA, per-file details). Replaces Django GUI's 800ms AJAX polling with push-based updates.

### REQ-008: Download Management
API endpoints to list active/completed downloads, cancel active downloads, and view download history.

### REQ-009: Electron Desktop Application
Cross-platform Electron app with React/Vue/Svelte frontend. Communicates with FastAPI backend via HTTP and WebSocket.

### REQ-010: Netflix-Style UI - Search & Browse
Dark theme interface with search bar, site selector/filter, and poster card grid for results. Category filtering (anime, film & series, series). Hover cards showing title, type, year, and action buttons.

### REQ-011: Netflix-Style UI - Series Detail
Season/episode browser with episode selection (individual, range, or all). Visual episode list with metadata.

### REQ-012: Netflix-Style UI - Download Dashboard
Active downloads with real-time progress bars, speed, ETA. Expandable stream details per download. Kill/cancel button. History of completed/failed downloads.

### REQ-013: Settings Management
UI for configuring: download output path, video/audio/subtitle quality preferences, proxy settings, media format (mkv/mp4), and general preferences. Maps to `config.json` values.

### REQ-014: Credential Management
UI for managing per-site login credentials. Maps to `login.json`. Secure input fields for passwords/tokens.

### REQ-015: Configuration Sync
Settings changes in the GUI write back to the StreamingCommunity config files (config.json, login.json). Changes take effect without restart.

### REQ-016: Category Filtering
Filter available services by category (anime, film_&_serie, serie) matching CLI's `--category` behavior.

### REQ-017: Auto-Update Check
Display notification when a new version of StreamingCommunity CLI is available. Mirror CLI's GitHub update check.

### REQ-018: Hook Support
Support pre_run and post_run hooks as configured in StreamingCommunity's config. Execute at app startup/shutdown.

### REQ-019: Cross-Platform Packaging
Electron builds for Windows (.exe), macOS (.dmg), and Linux (.AppImage/.deb). Each includes or bundles the Python backend.

## V2 Requirements (Nice to Have)

### REQ-V2-001: Media Player Integration
Built-in video player or launch in external player.

### REQ-V2-002: Download Queue
Queue system for scheduling multiple downloads with priority.

### REQ-V2-003: Notification System
Desktop notifications for download completion/failure.

### REQ-V2-004: Watch History
Track what the user has searched/downloaded previously.

### REQ-V2-005: Favorites/Bookmarks
Save media items for later download.

### REQ-V2-006: Auto-Download Scheduling
Schedule recurring searches and auto-download new episodes.

## Out of Scope

- Modifying StreamingCommunity core package code
- Mobile app versions (iOS/Android)
- Web-hosted version (this is a desktop app)
- User authentication/multi-user support
- Streaming/playback DRM content in the GUI
- Creating new streaming service plugins
