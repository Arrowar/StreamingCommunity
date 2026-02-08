# StreamingCommunity Electron GUI

## Vision
A cross-platform desktop GUI for the StreamingCommunity CLI tool, built with Electron and backed by a Python FastAPI server. The GUI replicates the full CLI workflow with a Netflix-style dark interface featuring poster card grids, real-time download progress, and full feature parity with the command-line tool.

## Context
- **Existing Project**: StreamingCommunity is a Python CLI supporting 15+ Italian streaming platforms with DRM content handling
- **Not Our Code**: The CLI is maintained by another developer; we build a GUI layer on top
- **Existing GUI Reference**: A Django web GUI already exists in `GUI/` directory with an API abstraction layer pattern we can reuse
- **Entry Point**: `test_run.py` calls `StreamingCommunity.cli.run:main()` — the GUI must replicate this entire workflow

## Architecture Decision
- **Frontend**: Electron (cross-platform desktop app)
- **Backend**: FastAPI Python server (reuses StreamingCommunity Python modules directly)
- **Communication**: HTTP REST + WebSocket for real-time download progress
- **Pattern Reference**: `GUI/searchapp/api/` provides BaseStreamingAPI abstraction pattern
- **Deployment**: Electron bundles the frontend; Python backend runs as a sidecar process

## Key Design Principles
1. **Non-invasive**: Do not modify the StreamingCommunity core package
2. **Abstraction Layer**: All CLI interaction goes through an API layer (like Django GUI does)
3. **Direct Python Imports**: Import StreamingCommunity modules directly, no shell execution
4. **Real-time Updates**: WebSocket for download progress (upgrade from Django's AJAX polling)
5. **Cross-platform**: Windows, macOS, Linux support via Electron

## Target Users
- Users who prefer a graphical interface over CLI
- Users who want visual media browsing with poster artwork
- Users who want to manage multiple downloads visually

## Success Criteria
- Full CLI workflow replicated: site selection → search → media browse → download
- All 15+ streaming services accessible
- Real-time download progress with speed/ETA
- Global search across all services
- Settings management (download path, quality, proxy, credentials)
- Netflix-style card grid with poster images
- Cross-platform builds (Windows, macOS, Linux)
