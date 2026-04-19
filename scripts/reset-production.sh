#!/usr/bin/env bash
# Fully reset the production stack, wipe persisted app data, and redeploy.
# Run from any directory on the server that has this repository checked out.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="${REPO_DIR}/docker-compose.prod.yml"
DEPLOY_SCRIPT="${REPO_DIR}/scripts/deploy.sh"
MAIL_SETUP_SCRIPT="${REPO_DIR}/scripts/setup-mailserver.sh"

PRUNE_UNUSED=0
SETUP_MAIL=0
AUTO_CONFIRM=0

usage() {
    cat <<'EOF'
Usage: ./scripts/reset-production.sh [options]

Options:
  --prune       Also run "docker system prune -af" after removing project images
  --setup-mail  Re-run scripts/setup-mailserver.sh after redeploy completes
  --yes         Skip the destructive-action confirmation prompt
  -h, --help    Show this help text

This command destroys production data for this project, including:
  - MariaDB data
  - Uploaded files
  - Caddy certificate/config volumes
  - Mail server bind-mounted state under ./mailserver/
EOF
}

while [ "$#" -gt 0 ]; do
    case "$1" in
        --prune)
            PRUNE_UNUSED=1
            ;;
        --setup-mail)
            SETUP_MAIL=1
            ;;
        --yes)
            AUTO_CONFIRM=1
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "ERROR: Unknown option: $1" >&2
            usage >&2
            exit 1
            ;;
    esac
    shift
done

if [ ! -f "${COMPOSE_FILE}" ]; then
    echo "ERROR: ${COMPOSE_FILE} not found" >&2
    exit 1
fi

if [ ! -x "${DEPLOY_SCRIPT}" ]; then
    echo "ERROR: ${DEPLOY_SCRIPT} is missing or not executable" >&2
    exit 1
fi

echo "Repository: ${REPO_DIR}"
echo "Compose file: ${COMPOSE_FILE}"
echo ""
echo "This will permanently remove the production stack and all persisted app data."
echo "It will preserve the repository checkout, .env, and Docker installation."

if [ "${AUTO_CONFIRM}" -ne 1 ]; then
    read -r -p "Type RESET to continue: " CONFIRM
    if [ "${CONFIRM}" != "RESET" ]; then
        echo "Aborted."
        exit 1
    fi
fi

cd "${REPO_DIR}"

echo "==> Stopping and removing the production stack..."
docker compose -f docker-compose.prod.yml down -v --remove-orphans

echo "==> Verifying project containers are gone..."
docker compose -f docker-compose.prod.yml ps

echo "==> Removing bind-mounted mail state..."
rm -rf \
    "${REPO_DIR}/mailserver/data" \
    "${REPO_DIR}/mailserver/state" \
    "${REPO_DIR}/mailserver/config" \
    "${REPO_DIR}/mailserver/logs"

echo "==> Removing project images..."
mapfile -t PROJECT_IMAGES < <(docker compose -f docker-compose.prod.yml config --images | awk 'NF')
if [ "${#PROJECT_IMAGES[@]}" -gt 0 ]; then
    printf '  %s\n' "${PROJECT_IMAGES[@]}"
    docker rmi "${PROJECT_IMAGES[@]}" 2>/dev/null || true
else
    echo "  No project images found."
fi

if [ "${PRUNE_UNUSED}" -eq 1 ]; then
    echo "==> Pruning unused Docker artifacts..."
    docker system prune -af
fi

if [ ! -f "${REPO_DIR}/.env" ]; then
    echo "ERROR: ${REPO_DIR}/.env not found; restore it before redeploying." >&2
    exit 1
fi

echo "==> Redeploying from a clean state..."
"${DEPLOY_SCRIPT}"

if [ "${SETUP_MAIL}" -eq 1 ]; then
    if [ ! -x "${MAIL_SETUP_SCRIPT}" ]; then
        echo "ERROR: ${MAIL_SETUP_SCRIPT} is missing or not executable" >&2
        exit 1
    fi

    echo "==> Re-running mail setup..."
    "${MAIL_SETUP_SCRIPT}"
fi

echo ""
echo "============================================================"
echo "  Production reset complete!"
echo "============================================================"
docker compose -f docker-compose.prod.yml ps
