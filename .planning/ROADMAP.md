# Roadmap - Milestone 1.0.0: StreamingCommunity Electron GUI

## Phase 1: FastAPI Backend Foundation
**Goal**: Working Python API server that wraps StreamingCommunity modules with full REST + WebSocket endpoints.

**Requirements**: REQ-001, REQ-002, REQ-003, REQ-004, REQ-005, REQ-006, REQ-007, REQ-008

**Must-haves**:
- FastAPI application with CORS enabled for Electron
- API abstraction layer (port/adapt Django GUI's `BaseStreamingAPI` pattern)
- Service discovery endpoint (list all sites with categories)
- Single-site search endpoint
- Global search endpoint (multi-site with consolidation)
- Series metadata endpoint (seasons/episodes)
- Download initiation endpoint (background threaded)
- WebSocket endpoint for real-time download progress
- Download management endpoints (list, cancel, history)
- Download tracker integration with StreamingCommunity's tracker

**Success criteria**:
- All 15+ services discoverable via API
- Search returns structured results with poster URLs
- Downloads start in background and report progress via WebSocket
- Can test full workflow via curl/httpie/Postman

---

## Phase 2: Electron App Shell + Search UI
**Goal**: Working Electron desktop app with Netflix-style search interface connected to the FastAPI backend.

**Requirements**: REQ-009, REQ-010, REQ-016

**Must-haves**:
- Electron app scaffolding (main process, renderer, preload)
- Python backend auto-launch as sidecar process on app start
- Frontend framework setup (React + Tailwind CSS for Netflix-style)
- Dark theme base layout with navigation
- Search bar with site selector dropdown
- Category filter tabs (All, Anime, Film & Series, Series)
- Poster card grid for search results
- Card hover effects showing title, type, year, action buttons
- Global search mode (search all sites)
- Loading states and error handling
- Responsive layout within desktop window

**Success criteria**:
- App launches, starts Python backend automatically
- User can search any site and see poster card results
- Category filtering works
- Global search returns consolidated results from multiple sites

---

## Phase 3: Series Detail + Download Flow
**Goal**: Complete media browsing and download initiation through the GUI.

**Requirements**: REQ-011, REQ-012

**Must-haves**:
- Series detail view with season/episode browser
- Episode selection UI (individual, range "1-5", all "*")
- Movie direct download button on card
- Download initiation from series detail view
- Download dashboard page
- Active downloads with real-time progress bars (WebSocket)
- Download speed and ETA display
- Per-file stream details (expandable)
- Cancel/kill download button
- Download history (completed/failed)
- Toast notifications for download start/complete/fail

**Success criteria**:
- Can browse series seasons and episodes
- Can start movie and series episode downloads
- Download progress updates in real-time
- Can cancel active downloads
- Download history persists during session

---

## Phase 4: Settings, Credentials & Configuration
**Goal**: Full settings management and credential handling through the GUI.

**Requirements**: REQ-013, REQ-014, REQ-015, REQ-017, REQ-018

**Must-haves**:
- Settings page with sections:
  - Download: output path (with folder picker), format (mkv/mp4)
  - Quality: video, audio, subtitle selection preferences
  - Network: proxy configuration, request settings
  - General: close console behavior, device info toggle
- Credential management page:
  - Per-site login fields (username/password or token)
  - Secure password inputs
  - Save/update credentials to login.json
- Config persistence (read/write config.json, login.json)
- Auto-update check notification
- Hook execution at app start/stop (pre_run, post_run)
- Settings take effect without app restart

**Success criteria**:
- All CLI config options accessible through GUI
- Credentials saved securely and used by backend
- Update notification appears when new CLI version available
- Hooks execute at appropriate lifecycle points

---

## Phase 5: Cross-Platform Packaging & Polish
**Goal**: Production-ready builds for all platforms with polished UX.

**Requirements**: REQ-019

**Must-haves**:
- Electron Builder configuration
- Windows build (.exe installer)
- macOS build (.dmg)
- Linux build (.AppImage or .deb)
- Python backend bundling strategy (embedded Python or system requirement)
- App icon and branding
- First-run setup wizard (check Python deps, download paths)
- Error recovery and graceful degradation
- Performance optimization (lazy loading, caching)
- Keyboard shortcuts for common actions

**Success criteria**:
- Clean install on Windows, macOS, and Linux
- App starts without manual Python setup (or guides through it)
- Professional look and feel
- No critical bugs in core workflow

---

## Phase Summary

| Phase | Description | Requirements |
|-------|-------------|-------------|
| 1 | FastAPI Backend Foundation | REQ-001 through REQ-008 |
| 2 | Electron App Shell + Search UI | REQ-009, REQ-010, REQ-016 |
| 3 | Series Detail + Download Flow | REQ-011, REQ-012 |
| 4 | Settings, Credentials & Config | REQ-013, REQ-014, REQ-015, REQ-017, REQ-018 |
| 5 | Cross-Platform Packaging & Polish | REQ-019 |
