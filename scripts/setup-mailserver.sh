#!/usr/bin/env bash
# One-time setup: create the mail account and generate DKIM keys.
# Run from the repo root AFTER the mailserver container is healthy:
#   docker compose -f docker-compose.prod.yml ps mailserver
set -euo pipefail

DOMAIN="chemtrail-tracker.com"
EMAIL="accounts@chemtrail-tracker.com"

read -rsp "Password for ${EMAIL}: " MAIL_PASSWORD
echo

echo "==> Creating account ${EMAIL}..."
docker compose -f docker-compose.prod.yml exec mailserver setup email add "${EMAIL}" "${MAIL_PASSWORD}"

echo "==> Generating DKIM keys for ${DOMAIN}..."
docker compose -f docker-compose.prod.yml exec mailserver setup config dkim domain "${DOMAIN}"

echo ""
echo "Account created. DKIM public key (add as DNS TXT record):"
echo ""
cat "./mailserver/config/opendkim/keys/${DOMAIN}/mail.txt"
echo ""
echo "See DNS_RECORDS.md for all required DNS records."
