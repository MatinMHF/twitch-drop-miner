# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
