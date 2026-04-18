#!/bin/bash
# ops/build-api.sh — Validate FastAPI backend
set -e
echo "[build-api] Activating venv..."
source /root/.openclaw/workspace/venv/bin/activate

echo "[build-api] Installing/updating dependencies..."
pip install -q -r /root/.openclaw/api/requirements.txt 2>/dev/null || true

echo "[build-api] Syntax check on main.py..."
python3 -m py_compile /root/.openclaw/api/main.py
echo "[build-api] ✓ API syntax OK"

echo "[build-api] Checking FastAPI import..."
python3 -c "
import sys
sys.path.insert(0, '/root/.openclaw/api')
from fastapi import FastAPI
print('[build-api] ✓ FastAPI importable')
"

echo "[build-api] DONE"
