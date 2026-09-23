#!/bin/bash
set -e

echo "=========================================================="
echo "          Twitch Drop Miner - Smart Installer             "
echo "=========================================================="

# Check if Docker and Docker Compose are installed
if ! command -v docker &> /dev/null; then
    echo "❌ Error: Docker is not installed. Please install Docker first."
    exit 1
fi

if ! docker compose version &> /dev/null && ! command -v docker-compose &> /dev/null; then
    echo "❌ Error: Docker Compose is not installed."
    exit 1
fi

# Detect existing installation
EXISTING_FOUND=false
if [ -d "./data" ] || [ -f "docker-compose.yml" ] || (docker ps -a --format '{{.Names}}' 2>/dev/null | grep -q "twitch-drop-miner"); then
    EXISTING_FOUND=true
fi

if [ "$EXISTING_FOUND" = true ]; then
    echo ""
    echo "⚠️  Existing Twitch Drop Miner installation detected."
    read -p "Do you want to update the existing installation? [y/n] (y=update, n=clean install from scratch): " choice
    case "$choice" in
        y|Y|yes|YES)
            echo ""
            echo "🔄 Updating existing installation (preserving database, custom watchlist, and encrypted tokens)..."
            if [ -d ".git" ]; then
                git pull
            fi
            docker compose pull 2>/dev/null || true
            docker compose up -d --build
            echo ""
            echo "✅ Update complete! Twitch Drop Miner is running."
            echo "👉 Web Dashboard: http://localhost:8080"
            exit 0
            ;;
        n|N|no|NO)
            echo ""
            echo "⚠️  Starting clean installation from scratch..."
            echo "Stopping and tearing down existing containers..."
            docker compose down -v 2>/dev/null || true
            read -p "Do you want to wipe the previous database and tokens in ./data? [y/n]: " wipe_choice
            if [ "$wipe_choice" = "y" ] || [ "$wipe_choice" = "Y" ]; then
                rm -rf ./data
                mkdir -p ./data
                chmod -R 777 ./data 2>/dev/null || true
                echo "🧹 Previous data wiped clean."
            else
                mkdir -p ./data
                chmod -R 777 ./data 2>/dev/null || true
            fi
            if [ -d ".git" ]; then
                git pull
            fi
            if [ ! -f ".env" ] && [ -f ".env.example" ]; then
                cp .env.example .env
            fi
            docker compose up -d --build
            echo ""
            echo "✅ Clean installation complete! Twitch Drop Miner is running."
            echo "👉 Web Dashboard: http://localhost:8080"
            exit 0
            ;;
        *)
            echo "❌ Invalid input. Please answer with 'y' to update or 'n' to reinstall. Aborting."
            exit 1
            ;;
    esac
fi

# Fresh installation
echo ""
echo "🚀 Performing new installation of Twitch Drop Miner..."
if [ ! -f ".env" ] && [ -f ".env.example" ]; then
    cp .env.example .env
fi
mkdir -p ./data
chmod -R 777 ./data 2>/dev/null || true
docker compose up -d --build

echo ""
echo "✅ Installation complete! Twitch Drop Miner is running in the background."
echo "👉 Web Dashboard: http://localhost:8080"
