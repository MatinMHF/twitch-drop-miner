#!/bin/bash
set -e

echo "=========================================================="
echo "         Twitch Drop Miner - Safe In-Place Updater        "
echo "=========================================================="

echo "🔄 Pulling latest source code..."
if [ -d ".git" ]; then
    git pull
fi

echo "📦 Rebuilding and restarting containers..."
docker compose pull 2>/dev/null || true
docker compose up -d --build

echo "✅ Update complete! All settings, custom watchlists, and encrypted tokens preserved."
echo "👉 Web Dashboard: http://localhost:8080"
