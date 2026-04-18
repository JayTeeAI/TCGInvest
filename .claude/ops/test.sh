#!/bin/bash
# ops/test.sh — Run pytest suite
set -e
echo "[test] Activating venv..."
source /root/.openclaw/workspace/venv/bin/activate

echo "[test] Installing pytest if needed..."
pip install -q pytest pytest-asyncio httpx 2>/dev/null || true

echo "[test] Running tests..."
cd /root/.openclaw
python3 -m pytest api/tests/ -v --tb=short 2>&1
EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo "[test] ✓ All tests passed"
else
    echo "[test] ✗ Tests FAILED (exit $EXIT_CODE)"
    exit $EXIT_CODE
fi
