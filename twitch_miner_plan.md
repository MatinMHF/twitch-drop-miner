# Twitch Drop Miner (Self-Hosted Web Service) — Architecture & Implementation Plan

## 1. Executive Summary & Core Principles
This project provides a standalone, secure, self-hosted web service that automates Twitch Drop discovery, stream watching (via lightweight GraphQL heartbeats without streaming video/audio), and drop claiming. 

> [!IMPORTANT]
> **Strict Clean-Room Guarantee**: All API wrappers, GraphQL queries, mining state machines, security pipelines, and UI designs are designed and written **100% from scratch**, strictly avoiding code or design patterns from any existing open-source miners.

---

## 2. System Architecture

```mermaid
graph TD
    User([Web Browser]) <-->|HTTPS / WSS| NGINX_Or_FastAPI[FastAPI Web & API Server]
    
    subgraph Backend_Container [Docker Backend Service]
        NGINX_Or_FastAPI --> AuthLayer[Auth & Rate Limiting Engine<br/>JWT + Refresh Rotation + CSRF]
        NGINX_Or_FastAPI --> RestAPI[REST Endpoints & WebSocket Manager]
        
        RestAPI --> DB[(SQLite Database<br/>Encrypted Tokens & Watchlist)]
        
        MiningService[Twitch Drop Mining Engine] --> DB
        MiningService --> DeviceAuth[Twitch Device Code Flow Manager]
        MiningService --> GQLClient[Twitch GQL Client & Watch Tracker]
        MiningService --> Scheduler[Background Poller & Stream Failover]
        MiningService --> TwitchConstants[Twitch GQL & Spade Registry<br/>Configurable Query Hashes & Endpoints]
    end

    GQLClient <-->|GQL Heartbeats / Drop Claims| TwitchAPI[Twitch APIs & GQL Endpoint]
    DeviceAuth <-->|OAuth 2.0 Device Flow| TwitchOAuth[Twitch ID OAuth Service]
```

---

## 3. Tech Stack Specification

| Component | Technology | Rationale |
| :--- | :--- | :--- |
| **Backend Framework** | **FastAPI (Python 3.12, async/await)** | High performance, native async WebSocket support, robust Pydantic v2 validation. |
| **Database** | **SQLite + SQLAlchemy (aiosqlite)** | Lightweight, zero external DB dependencies, portable persistent volume storage. |
| **Cryptography & Auth** | **AES-256-GCM (`cryptography`), bcrypt (`passlib`), PyJWT** | Military-grade token encryption at rest, secure admin authentication, rotated refresh tokens. |
| **Twitch Client** | **HTTPX (Async HTTP/2)** | Modern asynchronous HTTP client for high-throughput GQL polling & minute-watched heartbeats. |
| **Frontend Framework** | **React 18 + Vite + TypeScript** | Type-safe, ultra-fast UI rendering and real-time state synchronization. |
| **Styling & UI** | **Tailwind CSS + Lucide Icons + Framer Motion** | Sleek modern dark mode UI, fully mobile-responsive, zero bloat. |
| **Containerization** | **Docker (Multi-stage) & Docker Compose** | Produces a single lightweight (<120MB) production container image with persistent data volume. |

---

## 4. Key Modules & Functional Specification

### 4.1. Twitch Drop Mining Engine
1. **Device Code OAuth Flow**:
   - Initiates Twitch OAuth Device Code flow (`https://id.twitch.tv/oauth2/device`).
   - Presents a verification URI and user code (with QR code in UI).
   - Automatically polls for authorization completion, receives user tokens, and encrypts them at rest.
2. **GQL Drop Campaign Discovery**:
   - Polls Twitch GQL directory and drop service endpoints (`DropCampaignDetails`, `DropsHighlightService_AvailableDrops`).
   - Matches active campaigns against the user's priority-ordered **Game Watchlist**.
3. **Headless Stream Watcher (Zero Video/Audio Download)**:
   - Emulates legitimate player presence by dispatching minute-watched payload events via Twitch GQL / Spade tracker every 60 seconds with proper broadcast session tokens.
   - Saves 100% bandwidth (operates on standard HTTP requests of only ~1-2 KB per minute).
4. **Auto Claiming & Channel Failover**:
   - Regularly checks campaign drop progress percentages.
   - Calls `ClaimDropMutation` as soon as drops reach 100%.
   - Detects if the current streamer goes offline, immediately querying the top active streamer broadcasting the same game with drop tags enabled and switching seamlessly.

### 4.2. Centralized Twitch Constants & Persisted Query Registry
- **Central Configuration File (`app/core/twitch_constants.py` / `app/engine/constants.py`)**:
  - The **Spade Tracker endpoint URL** (`https://video-edge-*.twitch.tv` / spade event tracking URL) and all Twitch **GraphQL Persisted Query Hashes (SHA-256)** are defined exclusively as structured constants in one centralized registry.
  - Hashes include: `DropCampaignDetails`, `DropsHighlightService_AvailableDrops`, `DirectoryPage_Game`, `PlaybackAccessToken_Template`, `VideoPlayerStreamInfoOverlayChannel`, `ClaimDropMutation`, `ChannelShell`, etc.
  - **Environment & Runtime Overrides**: Every hash and endpoint supports environment variable overrides (e.g. `TWITCH_HASH_DROP_CAMPAIGN_DETAILS=...`, `TWITCH_SPADE_URL=...`), allowing instant hotfixing when Twitch rotates query hashes without code modifications.
  - Zero hardcoding in API/query execution logic — all requests pull dynamically from the registry.

### 4.3. Security Architecture
- **Encryption at Rest**: OAuth access and refresh tokens are encrypted using **AES-256-GCM** with unique nonces before saving to SQLite.
- **Web UI Authentication**:
  - Initial setup wizard / login for web dashboard.
  - Bcrypt password hashing (cost factor 12).
  - Short-lived Access JWT (15 minutes) + HTTP-only Secure SameSite Refresh Token with automatic rotation.
  - Rate limiting on login and auth endpoints via sliding window rate limiter.
  - Double-submit CSRF cookie protection for state mutation endpoints.
  - Strict logging filters ensuring access tokens, refresh tokens, and passwords are never written to logs or console output.

### 4.4. Modern Web Dashboard
- **Dashboard View**: Live status (Mining / Idle / Paused), current game banner, active channel stream info, minute-by-minute drop progress ring/bar, and real-time logs.
- **Watchlist Manager**: Dynamic Twitch game search bar with auto-suggestions, drag-and-drop priority sorting, and auto-mine toggle switches.
- **Drop Inventory**: History of completed and claimed drops with timestamps and game badges.
- **Settings & Account**: Twitch connection status, polling interval configurations, timezone selector, session manager, and dark/light theme toggle.

---

## 5. Repository Structure

```text
twitch-drop-miner/
├── .github/
│   └── workflows/
│       └── ci.yml               # Linting, type checks, test suite, and Docker build test
├── backend/
│   ├── app/
│   │   ├── api/                 # REST & WebSocket route handlers (auth, games, drops, status, settings)
│   │   ├── core/                # Config, security (AES-GCM, JWT, bcrypt), twitch_constants.py, logger filters
│   │   ├── db/                  # SQLite models, engine, repository layer
│   │   ├── engine/              # Mining state machine, Twitch GQL client, spade tracker, stream watcher, scheduler
│   │   ├── schemas/             # Pydantic models for requests/responses
│   │   └── main.py              # FastAPI application entrypoint
│   ├── tests/                   # Pytest suite for API and engine logic
│   └── requirements.txt         # Production backend dependencies
├── frontend/
│   ├── src/
│   │   ├── components/          # Dashboard cards, DropProgress, Watchlist, AuthModal, ThemeToggle
│   │   ├── hooks/               # WebSocket hook, query hooks, auth context
│   │   ├── services/            # API client with token refresh interceptors
│   │   ├── types/               # TypeScript interfaces
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── package.json
│   ├── tailwind.config.js
│   └── vite.config.ts
├── docker/
│   ├── Dockerfile               # Multi-stage build (Vite static build + FastAPI runner)
│   └── entrypoint.sh            # Database initialization & service startup
├── docker-compose.yml           # Pre-configured compose file with persistent volumes
├── .env.example                 # Example configuration file (including GQL hash overrides)
├── .gitignore                   # Comprehensive gitignore
├── LICENSE                      # MIT License
├── README.md                    # In-depth setup, architecture, and deployment guide
├── CONTRIBUTING.md              # Contribution standards and guidelines
└── CHANGELOG.md                 # Initial release notes
```

---

## 6. Execution Steps Upon Approval

1. **Backend Implementation**: Implement FastAPI server, AES-256 token encryption, SQLite persistence, Twitch Device Flow handler, centralized GQL/Spade query registry, GQL miner engine, and WebSocket broadcaster.
2. **Frontend Implementation**: Build React + TypeScript + Tailwind web application with dark/light themes, responsive layout, real-time WebSocket dashboard, and watchlist management.
3. **Integration & Containerization**: Configure multi-stage Docker build, health checks, entrypoints, and `docker-compose.yml`.
4. **Testing & Quality Assurance**: Validate encryption routines, rate limiters, token rotation, and Twitch API payload schemas.
5. **Git & GitHub Repository Publishing**: Initialize local git repository, commit all source files, create the public GitHub repository, and push the initial release.
