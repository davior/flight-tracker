#!/usr/bin/env bash
# One-time server setup for Ubuntu/Debian — run as root
set -euo pipefail

echo "==> Updating package index..."
apt-get update -qq

echo "==> Installing prerequisites..."
apt-get install -y -qq ca-certificates curl gnupg git

echo "==> Adding Docker apt repository..."
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
    | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg

. /etc/os-release
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
https://download.docker.com/linux/ubuntu ${VERSION_CODENAME} stable" \
    | tee /etc/apt/sources.list.d/docker.list > /dev/null

echo "==> Installing Docker Engine..."
apt-get update -qq
apt-get install -y -qq \
    docker-ce docker-ce-cli containerd.io \
    docker-buildx-plugin docker-compose-plugin

echo "==> Enabling Docker service..."
systemctl enable --now docker

echo ""
echo "============================================================"
echo "  Server setup complete!"
echo "============================================================"
echo ""
echo "Next steps:"
echo ""
echo "  1. Clone the repository:"
echo "       git clone https://github.com/davior/flight-tracker.git /opt/flight-tracker"
echo ""
echo "  2. Enter the project directory:"
echo "       cd /opt/flight-tracker"
echo ""
echo "  3. Create your .env file from the template:"
echo "       cp .env.production.example .env"
echo "       nano .env"
echo ""
echo "     Fill in at minimum:"
echo "       DOMAIN          — your domain name (must already point at this server)"
echo "       MYSQL_ROOT_PASSWORD — strong random password"
echo "       MYSQL_PASSWORD  — strong random password"
echo "       JWT_SECRET_KEY  — generate with: python3 -c \"import secrets; print(secrets.token_hex(32))\""
echo "       LIVE_FLIGHT_PROVIDER + credentials"
echo ""
echo "  4. Run the first deploy:"
echo "       chmod +x scripts/deploy.sh"
echo "       ./scripts/deploy.sh"
echo ""
echo "  Subsequent updates:"
echo "       cd /opt/flight-tracker && ./scripts/deploy.sh"
echo ""
