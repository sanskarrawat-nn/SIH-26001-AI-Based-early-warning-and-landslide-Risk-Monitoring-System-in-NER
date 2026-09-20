#!/bin/bash
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR/backend"

if [ -d "venv" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
fi

echo "Starting Landslide Early Warning System on http://127.0.0.1:8000 ..."
python3 -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
