#!/bin/sh
set -e

echo "Starting Twitch Drop Miner Web Service..."
mkdir -p /app/data

exec python -m uvicorn app.main:app --host 0.0.0.0 --port 8080
