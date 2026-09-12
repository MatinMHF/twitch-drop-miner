# Implementation Plan: Multi-Account Concurrent Mining

## Goal
Enable multi-account concurrent Twitch drop claiming in Twitch Drops Miner while strictly adhering to:
1. Preserve existing account (`goldendragongt`, `536739254`) without deletion or token invalidation.
2. Preserve existing admin panel credentials (`matin`).
3. Preserve all 33 games in the watchlist and their exact priority ordering.

## Architecture
- **Worker Level:** Transform `MiningWorker` from a single-engine holder into a multi-account worker orchestrator (`MultiAccountMiningManager`). Each active Twitch account gets its own isolated `Twitch` instance, separate WebSocket connection, separate cookies storage (`cookies_<user_id>.jar`), and its own status tracking.
- **Repository Level:** Add `get_all_active_twitch_accounts(db)` and account-specific disconnect `delete_twitch_account_by_id(db, id)`.
- **API Level:** Expand `/api/auth/twitch/accounts` to list all connected accounts and disconnect a specific account by ID, while keeping backwards compatibility for `/api/auth/twitch/account`.
- **Frontend Level:** Update UI to display all connected Twitch accounts, allow initiating a new Device Code flow without overwriting existing accounts, and display multi-account status tabs/cards.

## Tasks
1. Database & Cookie Isolation: Support per-account cookie jars (`cookies_<user_id>.jar`) so accounts do not overwrite each other's session.
2. Repositories: Add multi-account query and delete functions.
3. Multi-Account Mining Manager: Refactor `miner_worker.py` to manage N instances of `MiningWorker` concurrently.
4. API Endpoints: Expose endpoints for multi-account listing, status, and targeted disconnection.
5. Frontend UI: Add multi-account cards/switcher and "Add Account" flow in `TwitchDeviceAuthModal` and Dashboard.
6. Verification & Server Sync: Build, test locally, and safely deploy to Lightsail container without wiping data.
