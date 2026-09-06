@echo off
echo Updating Twitch Drop Miner to the latest version...
git pull
docker compose pull
docker compose up -d --build
echo Update complete! Twitch Drop Miner is running.
pause
