#!/usr/bin/env bash
# Deploy / update the Chemtrail Tracker (Flight Tracker) application.
# Run from the repository root on the server.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_DIR"

# Guard: require .env to exist
if [ ! -f .env ]; then
    echo "ERROR: .env not found in $REPO_DIR"
    echo "Copy .env.production.example to .env and fill in your values first."
    exit 1
fi

# Guard: require shared "web" Docker network (created by the infra project)
if ! docker network inspect web >/dev/null 2>&1; then
    echo "ERROR: Docker network 'web' not found."
    echo "Deploy the infra project first: cd /opt/infra && docker compose up -d"
    exit 1
fi

echo "==> Pulling latest changes..."
git pull origin main

echo "==> Building containers..."
docker compose -f docker-compose.prod.yml build

echo "==> Starting / updating services..."
docker compose -f docker-compose.prod.yml up -d --remove-orphans

echo "==> Running database migrations..."
docker compose -f docker-compose.prod.yml exec backend python migrate.py upgrade

echo ""
echo "============================================================"
echo "  Deployment complete!"
echo "============================================================"
docker compose -f docker-compose.prod.yml ps
