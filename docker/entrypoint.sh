#!/bin/sh
set -e

# Ensure data directory exists and is owned by appuser
mkdir -p /app/data
chown -R appuser:appuser /app/data
chmod -R 755 /app/data

# Drop privileges to appuser and launch FastAPI
if [ "$(id -u)" = "0" ]; then
    exec gosu appuser python -m uvicorn app.main:app --host 0.0.0.0 --port 8080
else
    exec python -m uvicorn app.main:app --host 0.0.0.0 --port 8080
fi
