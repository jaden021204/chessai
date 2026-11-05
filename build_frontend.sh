#!/bin/sh
set -e
cd frontend && npm ci --ignore-scripts --no-audit --no-fund && npm run build && cd ..
rm -rf chessai/frontend-dist || true
mv frontend/out chessai/frontend-dist
