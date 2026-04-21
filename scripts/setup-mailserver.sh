#!/usr/bin/env bash
# One-time setup: create the mail account and generate DKIM keys.
# Run from the repo root. The mailserver container may be running or stopped.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOMAIN="chemtrail-tracker.com"
EMAIL="accounts@chemtrail-tracker.com"
ACCOUNTS_FILE="${REPO_DIR}/mailserver/config/postfix-accounts.cf"

read -rsp "Password for ${EMAIL}: " MAIL_PASSWORD
echo

if [ -z "${MAIL_PASSWORD}" ]; then
    echo "ERROR: Password cannot be empty" >&2
    exit 1
fi

mkdir -p "${REPO_DIR}/mailserver/config"

echo "==> Creating account ${EMAIL}..."
# Hash on the host so special characters ($ @ etc.) in the password are
# never passed through a remote shell context where they could be mis-interpreted.
HASH=$(openssl passwd -6 "${MAIL_PASSWORD}")
printf '%s|{SHA512-CRYPT}%s\n' "${EMAIL}" "${HASH}" > "${ACCOUNTS_FILE}"
echo "  Written: ${ACCOUNTS_FILE}"

echo "==> Restarting mailserver to load account..."
docker compose -f docker-compose.prod.yml restart mailserver

echo "==> Waiting for mailserver to become healthy (up to 90s)..."
for i in $(seq 1 18); do
    sleep 5
    if docker compose -f docker-compose.prod.yml exec -T mailserver setup email list 2>/dev/null | grep -q "${EMAIL}"; then
        echo "  Mailserver is up and account is active."
        break
    fi
    printf '  Still waiting... (%ds)\n' "$((i * 5))"
done

echo "==> Generating DKIM keys for ${DOMAIN}..."
docker compose -f docker-compose.prod.yml exec -T mailserver setup config dkim domain "${DOMAIN}"

echo ""
echo "Account created."
echo ""
DKIM_TXT="${REPO_DIR}/mailserver/config/opendkim/keys/${DOMAIN}/mail.txt"
DKIM_KEY="${REPO_DIR}/mailserver/config/opendkim/keys/${DOMAIN}/mail.private"
if [ -f "${DKIM_TXT}" ]; then
    echo "DKIM public key (add as DNS TXT record for mail._domainkey.${DOMAIN}):"
    echo ""
    cat "${DKIM_TXT}"
elif [ -f "${DKIM_KEY}" ]; then
    echo "DKIM public key (add as DNS TXT record for mail._domainkey.${DOMAIN}):"
    echo ""
    echo "v=DKIM1; k=rsa; p=$(openssl rsa -in "${DKIM_KEY}" -pubout 2>/dev/null | grep -v "^---" | tr -d '\n')"
else
    echo "WARNING: DKIM key files not found at ${REPO_DIR}/mailserver/config/opendkim/"
    echo "Run: docker compose -f docker-compose.prod.yml exec mailserver setup config dkim domain ${DOMAIN}"
fi
echo ""
echo "See DNS_RECORDS.md for all required DNS records."
