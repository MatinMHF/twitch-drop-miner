#!/bin/bash
set -e

echo "Updating Twitch Drop Miner to the latest version..."
git pull
docker compose pull || true
docker compose up -d --build

echo "Update complete! Twitch Drop Miner is running."
