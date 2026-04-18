#!/bin/bash
# ops/build-frontend.sh — Build Next.js frontend
set -e
FRONTEND=/root/.openclaw/frontend

echo "[build-frontend] Building Next.js..."
cd "$FRONTEND"
npm run build 2>&1 | tail -20

if [ $? -eq 0 ]; then
    echo "[build-frontend] ✓ Build succeeded"
else
    echo "[build-frontend] ✗ Build FAILED — not restarting PM2"
    exit 1
fi
