# 🎮 Twitch Drop Miner

<div align="center">

[![CI Pipeline](https://github.com/MatinMHF/twitch-drop-miner/actions/workflows/ci.yml/badge.svg)](https://github.com/MatinMHF/twitch-drop-miner/actions/workflows/ci.yml)
[![Latest Release](https://img.shields.io/github/v/release/MatinMHF/twitch-drop-miner?color=blue&logo=github)](https://github.com/MatinMHF/twitch-drop-miner/releases)
[![Docker](https://img.shields.io/badge/Docker-Multi--Stage-blue?logo=docker)](https://www.docker.com/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688?logo=fastapi)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18-61DAFB?logo=react)](https://react.dev/)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind-3.4-38B2AC?logo=tailwind-css)](https://tailwindcss.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A modern, standalone, self-hosted web service for automatic Twitch Drop mining. Built 100% from scratch with a clean-room architecture.

[Features](#-key-features) • [Quick Start](#-quick-start-with-docker) • [Architecture](#-architecture) • [Configuration](#%EF%B8%8F-configuration--constants) • [Security](#-security-model) • [Contributing](#-contributing)

</div>

---

## 📸 Dashboard Preview

```text
+-----------------------------------------------------------------------------------+
|  [Tv] Twitch Drop Miner  v1.1.0      (•) Telemetry Live   [@MatinMHF]  [⚙] [🌙] [🚪] |
+-----------------------------------------------------------------------------------+
|  [ Status: MINING ]  [ Claimed: 26 ]  [ Watchlist: 7 ]  [ Bandwidth Saved: 99.9% ]|
+-----------------------------------------------------------------------------------+
|  ACTIVE MINING OPERATION                                                          |
|  Channel: @nmplol (Live) [7.4k viewers]                                           |
|  Reward: GTA$1M (nopixel V Campaign)                                              |
|  Progress: [████████████████░░░░░░░░] 66.7% (160 / 240 mins)  [Est. 80m left]     |
+-----------------------------------------------------------------------------------+
|  [ Game Watchlist (Priority Queue) ]             |  [ Active Discovered Campaigns ]  |
|  1. Rainbow Six Siege [✓ All Drops Claimed] [▲▼] |  • nopixel V (Ends Sep 20)        |
|  2. Rust              [⏳ Waiting for Drops] [▲▼] |  • Overwatch 2 Community Drops    |
|  3. Delta Force       [✓ All Drops Claimed] [▲▼] |  • Valorant Champions Drops       |
|  4. Grand Theft Auto V [Mining Now (2 drops)]   |  • Apex Legends Global Drops      |
+-----------------------------------------------------------------------------------+
|  [ Claimed Rewards History ]                     |  [ Real-Time Telemetry & Logs ]   |
|  ✓ GTA$250K - Claimed 1h ago                     |  [15:08:55] Watching @nmplol      |
|  ✓ LAV-AA - Bombworks - Claimed 6h ago           |  [15:09:55] Heartbeat confirmed   |
+-----------------------------------------------------------------------------------+
```

---

## ✨ Key Features

- 🔒 **Twitch OAuth 2.0 Device Flow**: Authenticate seamlessly using standard TV/Console device activation codes (`twitch.tv/activate`). No passwords, no 2FA credentials entered, and zero brittle browser automation (Puppeteer/Selenium).
- ⚡ **Headless Zero-Bandwidth Mining**: Emulates minute-watched viewing events directly via Twitch GraphQL and Spade telemetry without downloading video or audio streams (saves ~99.9% bandwidth, using ~1KB/min).
- 🎯 **Accurate Drop Availability & Completion Detection**: Evaluates campaign time windows, preconditions, and claimed benefits in real-time. Distinguishes between earnable drops, completed campaigns (`All Drops Claimed`), and games waiting for future drops.
- 🔍 **Dynamic Game & Campaign Discovery**: Queries Twitch APIs directly to search games and discover active/upcoming drop events.
- 📋 **Priority Watchlist**: Organize watchlisted games with drag-and-drop or rank adjustments. Automatically transitions to the next available campaign or drop reward.
- 🔄 **Smart Streamer Failover**: Detects when a current streamer goes offline and automatically switches to the next top eligible streamer broadcasting the same game with drops enabled.
- 🎁 **Automated Reward Claiming**: Automatically triggers `ClaimDropMutation` when drops reach 100% and stores the reward history in a persistent SQLite database.
- 🛡️ **Hardened Security**:
  - OAuth access and refresh tokens are encrypted at rest using **AES-256-GCM**.
  - Admin login secured with **bcrypt** hashing.
  - Short-lived JWT access tokens with rotating refresh cookies.
  - Sliding-window rate limiting on sensitive routes.
  - CSRF protection and sanitized log streams that mask secrets.
- ⚙️ **Configurable Constants Registry**: Centralized storage for Spade endpoints and Twitch GraphQL persisted query hashes (with full `.env` override capability).
- 📱 **Modern Responsive UI**: Built with React 18, Vite, TypeScript, and Tailwind CSS with full dark/light theme support and real-time WebSocket telemetry.

---

## 🏗 Architecture

```mermaid
graph TD
    User([Browser Client]) <-->|HTTPS / WSS| FastAPI[FastAPI Web & API Server]
    
    subgraph Docker Container
        FastAPI --> Auth[Auth & Rate Limiter<br/>JWT + Refresh + CSRF]
        FastAPI --> DB[(SQLite Database<br/>AES-256 Encrypted Tokens)]
        FastAPI --> MiningService[Mining Engine & Scheduler]
        
        MiningService --> GQLClient[Twitch GQL Client]
        MiningService --> SpadeTracker[Spade Minute Watcher]
        MiningService --> QueryRegistry[Twitch Persisted Query Registry]
    end

    GQLClient <-->|GQL Queries & Claims| TwitchGQL[Twitch GraphQL API]
    SpadeTracker <-->|Heartbeats| TwitchSpade[Twitch Spade Telemetry]
```

---

## 🚀 Quick Start with Docker

### 1. Clone the repository
```bash
git clone https://github.com/MatinMHF/twitch-drop-miner.git
cd twitch-drop-miner
```

### 2. Configure Environment (Optional)
```bash
cp .env.example .env
```

### 3. Launch with Docker Compose
```bash
docker compose up -d --build
```

### 4. Access Web Dashboard
Open your browser at:
👉 **`http://localhost:8080`**

On first launch, follow the initial setup wizard to create your admin username and password.

---

## 🔄 Updating to the Latest Version

To update an existing installation without losing your settings, database, or tokens:

### Quick Update Script
```bash
# Linux / macOS
chmod +x update.sh
./update.sh
```

```cmd
:: Windows
update.bat
```

### Manual Command:
```bash
git pull
docker compose pull
docker compose up -d --build
```

---

## ⚙️ Configuration & Constants

All Twitch GraphQL Persisted Query Hashes and endpoints are centralized in `backend/app/core/twitch_constants.py`. When Twitch modifies their GQL schema, you can hotfix hashes directly in `.env` without altering code:

| Variable | Default | Description |
| :--- | :--- | :--- |
| `PORT` | `8080` | Web server listening port |
| `DATA_DIR` | `./data` | Persistent SQLite database and secrets storage directory |
| `REQUIRE_HTTPS` | `false` | Enforce HTTPS redirects and HSTS headers |
| `POLL_INTERVAL_MINUTES` | `30` | Interval to poll Twitch for new drop campaigns |
| `WATCH_HEARTBEAT_SECONDS` | `60` | Stream watch heartbeat interval |
| `TWITCH_SPADE_URL` | `https://spade.twitch.tv/batched` | Twitch analytics minute-watched endpoint |
| `TWITCH_HASH_DROP_CAMPAIGN_DETAILS` | `039277b...` | SHA-256 hash for campaign details GQL query |
| `TWITCH_HASH_AVAILABLE_DROPS` | `782dad0...` | SHA-256 hash for available drops GQL query |
| `TWITCH_HASH_VIEWER_DROPS_DASHBOARD` | `d9cae77...` | SHA-256 hash for drop inventory / dashboard query |
| `TWITCH_HASH_CLAIM_DROP` | `a455dee...` | SHA-256 hash for drop claiming GQL mutation |
| `TWITCH_HASH_DIRECTORY_GAME` | `86bcceb...` | SHA-256 hash for game directory channel list query |
| `TWITCH_HASH_PLAYBACK_ACCESS_TOKEN` | `ed230aa...` | SHA-256 hash for stream playback access token query |

---

## 🛠️ Bare-Metal Installation

### Backend
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```

### Frontend
```bash
cd frontend
npm install
npm run build # builds static SPA into backend/static
# Or run live dev server:
npm run dev
```

### Running Tests
```bash
PYTHONPATH=backend pytest backend/tests
```

---

## 🔐 Security Model

1. **AES-256-GCM Encryption**: OAuth tokens are encrypted using AES-GCM-256 with distinct 12-byte random initialization vectors before being written to SQLite.
2. **Rotating Refresh Tokens**: Access tokens expire in 15 minutes; refresh tokens are stored in secure HTTP-only cookies and rotated upon each refresh.
3. **Double-Submit CSRF**: Mutation endpoints enforce double-submit CSRF validation matching request headers against session cookies.
4. **Log Redaction**: Automatic log stream filter strips Bearer tokens, passwords, cookies, and OAuth payloads from all stdout/stderr logs.

---

## 🗑️ Uninstallation

To completely tear down the service and remove all containers, images, and data:

```bash
docker compose down -v
docker rmi twitch-drop-miner:latest
cd ..
rm -rf twitch-drop-miner
```

> [!WARNING]
> Passing the `-v` flag removes the persistent Docker data volume (`./data`). This permanently deletes your SQLite database, settings, game watchlist, and encrypted Twitch OAuth tokens.

---

## 🤝 Contributing

Contributions are welcome! Please review [CONTRIBUTING.md](CONTRIBUTING.md) for details on code style, testing, and pull request procedures.

---

## 📄 License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

