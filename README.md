# Flight Logger

Flight Logger is a full-stack app for viewing nearby aircraft, logging sightings with photos, and browsing logged flights on a map-first UI.

## Stack

- Frontend: Vue 3, TypeScript, Vite, Pinia, Leaflet
- Backend: FastAPI, SQLAlchemy, MariaDB
- Dev orchestration: Docker Compose

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

## Useful Notes

- Uploaded photos are stored in `uploads/`
- The frontend generates a local UUID and stores it in browser local storage
- The backend creates tables automatically on startup
- The first aircraft-enrichment lookup may download a local ADS-B snapshot into `/tmp/flight-logger-cache`
- `.env.example` is safe to commit; keep your real `.env` local and untracked
