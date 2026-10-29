# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.4.0] - 2026-10-29

### Added
- **Bot-Free Full HLS Playlist Chunks Iteration**:
  - Implemented upstream DevilXD `f693b0c` pattern iterating through all ~15 stream chunks in each m3u8 playlist dispatching lightweight HTTP `HEAD` requests.
  - Reduced `WATCH_INTERVAL` to 20 seconds (`timedelta(seconds=20)`), establishing persistent playback presence on Twitch's CDN edge without media stream downloads (0 KB bandwidth overhead).
  - Effectively bypasses Twitch bot detection heuristics and prevents stalled drop progress.
- **Worker Resilience & Exponential Backoff Retry Loop**:
  - Implemented automatic self-healing retry mechanism in `SingleAccountWorker._run_wrapper` with exponential backoff on unhandled exceptions and transient network disconnects.
  - Prevents worker threads from permanently crashing or becoming orphaned during extended 24/7 mining sessions.
- **ACL Streamer Drops Enablement**:
  - Added guaranteed `drops_enabled = True` retention for channels present in official game developer Access Control Lists (ACLs), such as Rainbow Six Siege *Doktor's Curse 26*.
  - Prevents false-negative idle fallback when Twitch's `AvailableDrops` query only returns site-wide promotions (e.g. Apple TV).
- **Comprehensive Test Suite (40 Tests, 100% Pass Rate)**:
  - Added test suites for drop verification (`test_drop_verification.py`), HLS chunk playback simulation (`test_hls_watch.py`), GraphQL online resilience (`test_bulk_check_online_resilience.py`), worker recovery (`test_worker_recovery.py`), and ACL drops enablement (`test_acl_drops_enabled.py`).
  - Achieved 100% pass rate across all 40 test cases.
- **CI Pipeline Green Bootstrap**:
  - Added dynamic `sys.path` bootstrap in `backend/tests/conftest.py` ensuring reliable DevilXD module discovery in automated test runners.
  - Added `greenlet>=3.0.0` and `sqlalchemy[asyncio]` dependencies to `requirements.txt` for clean async database support across all GitHub Actions jobs.

### Fixed
- **Strict AvailableDrops Verification & Phantom Minute Elimination**:
  - Enforced `available_drops_check: true` to eliminate non-game campaign false positives (such as Apple TV site promotions) and ensure streams are strictly tied to real game campaigns.
  - Completely eliminated local phantom/speculative minutes (`extra_current_minutes`), guaranteeing the web UI and telemetry APIs display exclusively verified Twitch server-confirmed minutes (`real_current_minutes`).
- **GraphQL Fault Tolerance in `bulk_check_online`**:
  - Isolated `viewerDropCampaigns` service errors during stream polling so transient Twitch GraphQL service outages do not crash or derail channel discovery loops.
- **Multi-Account Cookie Seeding & Session Restoration**:
  - Resolved cookie jar seeding and session restoration during multi-account worker initialization without raising `KeyError: 'device_code'`.
  - Fixed Pydantic model rebuilds and error handling on device authorization flows.

## [1.3.1] - 2026-10-26

### Added
- **Tri-Layer Telemetry & HLS Stream Presence Verification**:
  - Activated `_send_watch_playlist()` in `Channel.send_watch()` sending lightweight HTTP HEAD requests to stream playlist chunks, proving legitimate player presence on Twitch's video CDN edge with zero video/audio stream download (0 KB bandwidth overhead).
  - Dual-layer authenticated telemetry dispatching: dispatches both authenticated GraphQL `sendSpadeEvents` mutations with OAuth token and direct Spade telemetry POST requests (`https://spade.twitch.tv/track`) with session cookies and authorization headers.
- **60-Second Fallback Progress Synchronization**:
  - Implemented automatic fallback polling in `BridgeProgress.minute_almost_done` to query `DropCurrentSessionContext` via GraphQL every 60 seconds if WebSocket PubSub telemetry is delayed or drops out.
- **Dynamic Heartbeat & Progress Pytest Suite**:
  - Added dedicated test suite `backend/tests/test_heartbeat_payload.py` ensuring timestamp dynamism per heartbeat and verifying 60-second progress fallback logic. 100% test pass rate across 15 test suites.

### Fixed
- **Dynamic Heartbeat Telemetry & Frozen Timestamp Resolution**:
  - Replaced frozen `@cached_property` on `Stream._watch_payload` and `Stream.spade_payload` with dynamic properties evaluating `isonow()` per heartbeat.
  - Solved critical issue where Twitch rejected repeated minutes as duplicate timestamps after channel switch or during extended mining sessions.
- **Resilient Spade URL Extraction**:
  - Enhanced `Channel.get_spade_url()` with graceful fallback to `https://spade.twitch.tv/track`, preventing unhandled exceptions when channel HTML/JS scraping fails.

## [1.3.0] - 2026-09-23

### Added
- **Real In-Game Reward Benefit Name Resolution**:
  - Automatically resolves real in-game item reward titles (e.g. `'2024 Frost Uniform'`, `'OL' CLANKER'`) when game publishers define raw drop slots with generic names such as `'Test'`, `'Drop'`, or `'Reward'`.
- **Global Shared Campaigns Architecture**:
  - Introduced unified cross-account shared campaign cache. When Twitch GraphQL returns `dropCampaigns: null` for newly created or restricted accounts, instances automatically inherit verified global campaigns discovered across other connected accounts.
- **Enhanced Multi-Target Live Dashboard UI**:
  - Each actively mining account renders an independent, detailed live status card.
  - High-resolution **Official Game Box Art** thumbnail with dedicated hover-to-zoom preview modal.
  - High-contrast **Drop Reward Item Badge** with interactive hover magnification pop-up.
  - Prominent **Account Owner Tag** (`Account: @username`) with pulsing status indicator.
  - Streamer info, viewer counts, and exact minute watched counter with animated gradient progress bar.
- **Smart Interactive Installer (`install.sh`)**:
  - Intelligent installation script that detects existing deployments and prompts:
    - Press `y`: Safe in-place update preserving SQLite database, watchlist priorities, and AES-256 encrypted tokens.
    - Press `n`: Clean reinstallation from scratch with optional database wipe.

### Fixed
- **MultiTwitchAccountsResponse Pydantic Typo**:
  - Added missing `List` import to `app.schemas.auth` preventing HTTP 500 error on `/api/auth/twitch/accounts`.
- **Twitch OAuth Scope Deprecation**:
  - Replaced deprecated legacy v5/Kraken scopes with modern RFC 8628 Twitch OAuth 2.0 scopes, resolving HTTP 400 error on `twitch.tv/activate`.
- **Device Code Client Compatibility**:
  - Switched default device flow client ID to Twitch's supported SmartBox/TV client.

## [1.2.1] - 2026-09-12

### Fixed
- **Watchlist Disappearing in Idle State**:
  - Fixed a critical `ValidationError` in `GET /api/games/watchlist` where `is_currently_mining` evaluated to `None` instead of a strict boolean when all drop campaigns completed or the miner entered `IDLE` state.
  - Added multi-account campaign inventory aggregation across all active mining workers.
  - Hardened drop calculation with defensive error handling so watchlist retrieval never returns 500.

## [1.2.0] - 2026-09-12

### Added
- **Multi-Account Concurrent Mining**:
  - Connect multiple Twitch accounts simultaneously via OAuth 2.0 Device Code Flow.
  - Multi-instance DevilXD engine manager (`MultiAccountMiningManager`) running parallel watch loops, WebSocket PubSub clients, and drop claimers.
  - Per-account cookie jar isolation (`cookies_<user_id>.jar`) preventing session collisions across connected accounts.
  - Multi-account management modal with individual account disconnect and "Add Another Account" flow.
  - Live parallel account execution status cards on the dashboard.
- **Interactive Drag-and-Drop Priority Watchlist**:
  - Reorder game priority by directly dragging game cards up and down with dedicated visual grip handle.
  - Viewport edge auto-scrolling: smoothly scrolls the page when dragging near top or bottom edges to easily manage large watchlists.

### Fixed
- **Docker Frontend Build**:
  - Switched frontend builder to `node:20-slim` to resolve libc / musl binary compatibility during Vite/Rollup production compilation.
  - Resolved `MultiAccountMiningManager` attribute compatibility in `list_watchlist` API.

## [1.1.0] - 2026-09-08

### Fixed
- **Watchlist Drop Count Accuracy**:
  - Excluded expired and historical in-progress campaigns from active drop calculations in `list_watchlist`.
  - Accurately evaluate drop earnability by checking `can_earn()` and `is_claimed` status.
  - Added `is_completed` flag and `All Drops Claimed` badge when all drops for an active campaign have been claimed.
  - Prevented expired campaigns in `dropCampaignsInProgress` from polluting `get_available_drop_campaigns`.

## [1.0.1] - 2026-09-06

### Fixed
- **Twitch GraphQL Persisted Query Hashes**:
  - Updated `DropsHighlightService_AvailableDrops`, `DropCampaignDetails`, `ViewerDropsDashboard`, `DirectoryPage_Game`, `ClaimDropMutation`, `PlaybackAccessToken_Template`, `VideoPlayerStreamInfoOverlayChannel`, and `DirectoryGameRedirect` hashes to verified working versions to resolve `PersistedQueryNotFound` errors.
  - Enhanced `search_games` in GraphQL client with resilient multi-tier lookup (active campaigns filter and `DirectoryGameRedirect`).
- **Container Volume Permissions**:
  - Fixed `PermissionError: [Errno 13] Permission denied: '/app/data/.master_secrets'` by introducing root permission bootstrapping in `docker/entrypoint.sh` with safe unprivileged execution via `gosu appuser`.
- **Frontend TypeScript Build**:
  - Removed unused imports and variables across all React components to achieve 100% clean `tsc && vite build`.

### Added
- **Update Workflow Scripts**:
  - Added `update.sh` (Linux/macOS) and `update.bat` (Windows) for seamless in-place updating without data loss.
  - Added comprehensive `Updating` and `Uninstallation` sections to `README.md`.

## [1.0.0] - 2026-09-06

### Added
- **Clean-Room Twitch Mining Core**:
  - Headless watch engine utilizing Spade telemetry and GraphQL minute-watched heartbeats without downloading any video/audio stream data.
  - Automatic campaign discovery and priority-based game queue.
  - Automatic drop reward claiming via `ClaimDropMutation`.
  - Automatic channel failover when a stream goes offline.
- **Twitch OAuth 2.0 Device Code Flow**:
  - Browserless TV/Console authentication flow with activation code and QR support.
  - Zero password storage or browser automation required.
- **Security & Cryptography**:
  - AES-256-GCM token encryption at rest.
  - Bcrypt-hashed admin authentication.
  - Short-lived JWT access tokens with rotating refresh cookies.
  - Sliding-window rate limiting on sensitive routes.
  - CSRF protection and sanitized log output.
- **Modern Web Dashboard**:
  - React 18 + Vite + TypeScript + Tailwind CSS UI.
  - Dark and light theme support.
  - Real-time telemetry via WebSocket.
  - Interactive game search and drag-and-drop priority watchlist manager.
- **Configurable Twitch Query Registry**:
  - All GraphQL persisted query hashes and Spade endpoints centralized in a single registry with environment variable overrides.
- **Docker & Infrastructure**:
  - Multi-stage Docker build producing a lightweight container (<120MB).
  - Pre-configured `docker-compose.yml` with persistent volume mount.
  - GitHub Actions CI pipeline for tests and Docker builds.