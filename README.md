# Flight Logger

Flight Logger is a full-stack app for viewing nearby aircraft, logging sightings with photos, and browsing logged flights on a map-first UI.

## Stack

- Frontend: Vue 3, TypeScript, Vite, Pinia, Leaflet
- Backend: FastAPI, SQLAlchemy, MariaDB
- Dev orchestration: Docker Compose

## Deploy to Production

The production stack runs behind Caddy (automatic HTTPS). Outbound email uses smtp2go; inbound forwarding uses ImprovMX.

### 1. Provision a server

On a fresh Ubuntu/Debian VPS, install Docker:

```bash
curl -fsSL https://raw.githubusercontent.com/davior/flight-tracker/main/scripts/setup-server.sh | sudo bash
```

### 2. Set DNS A records (before deploying)

Caddy needs these to resolve before it can issue TLS certificates:

| Record | Name | Value |
|--------|------|-------|
| A | `chemtrail-tracker.com` | your server's public IP |
| A | `www.chemtrail-tracker.com` | your server's public IP |

### 3. Clone the repo and create `.env`

```bash
git clone https://github.com/davior/flight-tracker.git /opt/flight-tracker
cd /opt/flight-tracker
cp .env.production.example .env
nano .env
```

Required values to fill in:

| Variable | Notes |
|----------|-------|
| `DOMAIN` | your domain name |
| `MYSQL_ROOT_PASSWORD` | strong random password |
| `MYSQL_PASSWORD` | strong random password |
| `JWT_SECRET_KEY` | `python3 -c "import secrets; print(secrets.token_hex(32))"` |
| `LIVE_FLIGHT_PROVIDER` + credentials | `opensky` or `adsbx` |
| `SMTP_PASSWORD` | smtp2go account password (from smtp2go dashboard) |

### 4. Deploy

```bash
./scripts/deploy.sh
```

This builds containers, starts all services, and runs database migrations.

### 5. Configure DNS and email records

Add the remaining DNS records (MX, SPF, DKIM, DMARC) at your registrar.
See `DNS_RECORDS.md` for the exact values and setup sequence.

### Subsequent deploys

```bash
cd /opt/flight-tracker && ./scripts/deploy.sh
```

### Fresh production reset

If you want to wipe the production stack and all persisted app data before redeploying:

```bash
cd /opt/flight-tracker
./scripts/reset-production.sh
```

Useful flags:

- `--prune` also runs `docker system prune -af` after project images are removed
- `--yes` skips the destructive-action confirmation prompt

This removes the production containers, named volumes (including uploaded files and Caddy's cached TLS certificates), then calls `./scripts/deploy.sh`. Caddy will re-obtain a TLS certificate from Let's Encrypt on first start — this requires ports 80 and 443 to be reachable and DNS to be pointing at the server.

---

## Run In Debug

The easiest debug workflow is Docker Compose. It starts:

- MariaDB on `localhost:3306`
- FastAPI backend on `http://localhost:8000`
- Vite frontend on `http://localhost:5173`

From the repo root:

Create a local `.env` file first if you want live-flight provider credentials loaded into Docker Compose:

```bash
cp .env.example .env
```

Then set:

```dotenv
LIVE_FLIGHT_PROVIDER=opensky
OPENSKY_CLIENT_ID=your-client-id
OPENSKY_CLIENT_SECRET=your-client-secret
# For ADS-B Exchange instead:
# LIVE_FLIGHT_PROVIDER=adsbx
# ADSBX_API_KEY=your-api-key
# ADSBX_API_BASE_URL=https://adsbexchange.com/api/aircraft
```

Then start the stack:

```bash
docker compose up --build
```

Debug behavior in this setup:

- The backend runs with `uvicorn --reload`
- The frontend runs with the Vite dev server
- Source folders are mounted into the containers, so code changes are picked up without rebuilding
- Docker Compose reads live-flight provider settings from the repo-root `.env` file if present

## Open The App

- Frontend UI: `http://localhost:5173`
- Backend API docs: `http://localhost:8000/docs`

## Stop The Stack

Press `Ctrl+C` in the Compose terminal, or run:

```bash
docker compose down
```

To also remove the database volume:

```bash
docker compose down -v
```

## Run Services Separately

If you want to debug services outside Compose, use the following.

### 1. Start The Database

From the repo root:

```bash
docker compose up -d db
```

### 2. Run The Backend Locally

From `backend/`:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export DATABASE_URL='mysql+mysqlconnector://flightuser:flightpass@127.0.0.1:3306/flightlogs'
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Optional env vars for live-flight provider access:

```bash
export LIVE_FLIGHT_PROVIDER='opensky'
export OPENSKY_CLIENT_ID='your-client-id'
export OPENSKY_CLIENT_SECRET='your-client-secret'
```

Or for ADS-B Exchange:

```bash
export LIVE_FLIGHT_PROVIDER='adsbx'
export ADSBX_API_KEY='your-api-key'
export ADSBX_API_BASE_URL='https://adsbexchange.com/api/aircraft'
```

### 3. Run The Frontend Locally

From `frontend/`:

```bash
cd frontend
npm install
npm run dev -- --host 0.0.0.0
```

The Vite config proxies API requests to the backend container name `backend` in Compose. For pure local frontend debugging, set:

```bash
export VITE_API_BASE='http://127.0.0.1:8000'
```

Then run:

```bash
npm run dev -- --host 0.0.0.0
```

## Run Tests

### Backend

From `backend/`:

```bash
.venv/bin/python -m pytest -q
```

### Frontend

From `frontend/`:

```bash
npm run test
npm run build
```

## Database Migrations

This project uses Alembic for database schema migrations. Migrations run automatically when the backend starts.

### Common Migration Commands

From the `backend/` directory with the virtual environment activated:

```bash
# Check current migration status
python migrate.py current

# View migration history
python migrate.py history

# Create a new migration (auto-detects model changes)
python migrate.py create "add user table"

# Manually upgrade to latest
python migrate.py upgrade

# Downgrade one migration
python migrate.py downgrade

# Or use alembic directly
alembic current
alembic history
alembic revision --autogenerate -m "migration message"
alembic upgrade head
alembic downgrade -1
```

### Migration Best Practices

1. **Always review auto-generated migrations** before applying them
2. **Test migrations on a copy of production data** before deploying
3. **Never edit applied migrations** - create a new one instead
4. **Commit migrations to version control** alongside model changes

### How Migrations Work

- On startup, the backend automatically runs `alembic upgrade head`
- This ensures the database schema matches the current codebase
- For fresh databases, all migrations are applied in order
- For existing databases, only new migrations are applied

## Useful Notes

- Uploaded photos are stored in `uploads/`
- The frontend generates a local UUID and stores it in browser local storage
- Database migrations run automatically on backend startup
- The first aircraft-enrichment lookup may download a local ADS-B snapshot into `/tmp/flight-logger-cache`
- `.env.example` is safe to commit; keep your real `.env` local and untracked
