#!/bin/bash
set -e

echo "=== ClickBites API Startup ==="

# Download model at startup (HF_TOKEN is available as runtime secret)
python ai/download_model.py

echo "=== Starting API server ==="
exec uvicorn app:app --host 0.0.0.0 --port 7860 --workers 1
