# Flight Tracker — Architecture Document

## Overview

Flight Tracker is a full-stack web application for viewing live aircraft positions on a map and logging flight sightings. It consists of three services orchestrated by Docker Compose: a Vue 3 single-page application, a FastAPI backend, and a MariaDB database.

---

## System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Docker Compose                        │
│                                                         │
│  ┌───────────────┐   /api  ┌─────────────────────────┐  │
│  │   Frontend    │ ──────▶ │       Backend           │  │
│  │  Vue 3 + Vite │         │  FastAPI (uvicorn)       │  │
│  │  :5173        │ /photos │  :8000                  │  │
│  └───────────────┘ ──────▶ └────────────┬────────────┘  │
│                                          │               │
│                              ┌───────────▼─────────┐    │
│                              │     MariaDB 11       │    │
│                              │     :3306            │    │
│                              └─────────────────────┘    │
│                                                         │
└─────────────────────────────────────────────────────────┘
         │                         │
         ▼                         ▼
  External providers:       Uploads directory
  OpenSky Network           (./uploads volume)
  ADS-B Exchange
```

---

## Services

### Frontend — Vue 3 / Vite

| Property | Value |
|---|---|
| Image | `node:20` |
| Port | `5173` |
| Framework | Vue 3 (`^3.5.18`) |
| Build tool | Vite (`^7.1.2`) |
| State management | Pinia (`^3.0.3`) |
| Map library | Leaflet (`^1.9.4`) + `@vue-leaflet/vue-leaflet` (`^0.10.1`) |
| Styling | Tailwind CSS (via `@tailwindcss/vite`) |
| Testing | Vitest + jsdom + `@vue/test-utils` |
| Language | TypeScript (`^5.9.2`) |

The Vite dev server proxies two path prefixes to the backend:
- `/api` → `http://backend:8000` (API calls, `/api` prefix stripped)
- `/photos` → `http://backend:8000` (uploaded photo files)

### Backend — FastAPI

| Property | Value |
|---|---|
| Port | `8000` |
| Framework | FastAPI |
| Server | Uvicorn (`--reload` in dev) |
| ORM | SQLAlchemy |
| Migrations | Alembic |
| Image processing | Pillow |
| HTTP client | Requests |
| Testing | Pytest + HTTPX |

### Database — MariaDB 11

| Property | Value |
|---|---|
| Image | `mariadb:11` |
| Port | `3306` |
| Database | `flightlogs` |
| User | `flightuser` |
| Volume | `db_data` (named, persistent) |
| Connection string | `mysql+mysqlconnector://flightuser:flightpass@db:3306/flightlogs` |

---

## Backend Architecture

### Application Bootstrap (`app/main.py`)

The FastAPI app is created via a `create_app()` factory. A lifespan context manager handles startup/shutdown in order:

1. Create upload and runtime directories
2. Create database engine and session maker (stored on `app.state`)
3. Wait for database with retry logic (up to 30 attempts, 1s delay)
4. Run Alembic migrations
5. Seed aircraft category reference data
6. Initialise live flight provider (stored on `app.state`)
7. Initialise aircraft enrichment service and background queue

Registered routers:
- `flights_router` — prefix `/flights`
- `logs_router` — prefix `/logs`
- `photo_router` — prefix `/photos`

### Configuration (`app/config.py`)

All settings are loaded from environment variables via `Settings.from_env()` (LRU-cached). Key settings:

| Setting | Default | Description |
|---|---|---|
| `database_url` | MariaDB local | SQLAlchemy connection string |
| `upload_dir` | `./uploads` | Uploaded photo storage |
| `runtime_dir` | `/tmp/flight-logger-cache` | Aircraft DB snapshot cache |
| `max_nearby_radius_km` | `500` | Max query radius |
| `live_flight_provider` | `opensky` | Provider: `opensky` or `adsbx` |
| `opensky_client_id` | `None` | OpenSky OAuth client ID |
| `opensky_client_secret` | `None` | OpenSky OAuth client secret |
| `adsbx_api_key` | `None` | ADS-B Exchange API key |

### API Endpoints

#### Flights (`/flights`)

| Method | Path | Description |
|---|---|---|
| `GET` | `/flights/capabilities` | Provider capabilities (history support, limits) |
| `GET` | `/flights/nearby` | Live flights in map bounds; `time_shift_minutes` (0–60) for historical view |
| `GET` | `/flights/{icao24}/trajectory` | Sampled historical positions for one aircraft |

**Trajectory parameters:**
- `max_history_minutes` (1–60, default **60**) — how far back to sample
- `step_minutes` (1–10, default **10**) — interval between samples
- Reference time is always **current wall-clock time** (not affected by time shift)

#### Logs (`/logs`)

| Method | Path | Description |
|---|---|---|
| `POST` | `/logs` | Create a flight log (multipart, up to 3 photos) |
| `GET` | `/logs/nearby` | Logged flights in map bounds within a time window |
| `GET` | `/photos/{photo_id}` | Serve an uploaded photo |

### Services

| Service | Description |
|---|---|
| `opensky.py` | OpenSky Network provider — OAuth2 token management, bounds queries, ICAO24 single-aircraft queries, up to 60 min history |
| `adsbx.py` | ADS-B Exchange provider — radius-based queries (max 185.2 km), no history |
| `live_flight_provider.py` | `LiveFlightProvider` Protocol defining the provider interface |
| `live_flight_provider_factory.py` | Selects and constructs the configured provider at startup |
| `trajectory.py` | Samples historical positions by looping backward in time; skips radar dropouts silently |
| `aircraft_enrichment.py` | Looks up ICAO24 in the aircraft registry cache; falls back to external snapshot |
| `aircraft_enrichment_queue.py` | Background queue for async registry enrichment |
| `aircraft_categories.py` | Loads and resolves aircraft category labels/descriptions |
| `image_storage.py` | Saves uploaded photos; resizes to max 1600px width; preserves EXIF |

### Database Schema

```
flight_logs
├── id               PK
├── created_at       DateTime (UTC)
├── flight_time      DateTime (UTC)
├── icao24           String(6), indexed
├── callsign         String(16)
├── origin_country   String(64)
├── departure_airport String(8)
├── arrival_airport  String(8)
├── aircraft_latitude  Numeric(9,6)
├── aircraft_longitude Numeric(9,6)
├── altitude         Float
├── velocity         Float
├── heading          Float
├── vertical_rate    Float
├── owner_uuid       String(36), indexed
├── logger_name      String(128)
├── logger_location  String(255)
├── logger_latitude  Numeric(9,6)
├── logger_longitude Numeric(9,6)
├── note             Text
├── trajectory       JSON (list of {lat, lng, alt, heading, velocity, timestamp})
└── photos           → flight_log_photos (cascade delete)

flight_log_photos
├── id               PK
├── flight_log_id    FK → flight_logs.id (CASCADE DELETE), indexed
├── file_path        String(512)
└── created_at       DateTime (UTC)

aircraft_registry   (enrichment cache)
├── icao24           PK String(6)
├── registration     String(32)
├── type_code        String(8), indexed
├── manufacturer     String(128)
├── model            String(128)
├── category         String(16)
├── first_seen       DateTime
└── last_updated     DateTime

aircraft_types      (reference)
├── type_code        PK
├── manufacturer
├── model
└── category

aircraft_categories (reference)
├── code             PK
├── label
└── description
```

Migrations are managed with **Alembic** and run automatically at startup.

---

## Frontend Architecture

### Component Tree

```
App.vue
├── MapShell.vue                  Map container (Leaflet)
│   ├── LiveFlightMarkers.vue     Aircraft icons (live mode)
│   │   └── LiveFlightPopup.vue   Click popup with flight details
│   ├── LoggedFlightMarkers.vue   Circle markers (logged mode)
│   │   └── LoggedFlightPopup.vue Click popup with log summary
│   └── FlightTrajectory.vue      Dashed polyline + sample dots
│
├── FlightListPanel.vue           List view (non-map)
├── LoggedFlightDetailDrawer.vue  Selected log detail (drawer/sidebar)
├── ReportFlightModal.vue         Log a flight (note + photos)
├── LiveTimeShiftBar.vue          Historical time slider (live mode)
├── LoggedTimeWindowBar.vue       Time window selector (logged mode)
├── ManualLocationSheet.vue       Manual location picker
├── FloatingControls.vue          Refresh + location buttons
├── BottomModeNav.vue             Live / Logged mode toggle
├── ViewToggle.vue                Map / List view toggle
└── ToastStack.vue                Transient notifications
```

### State Stores (Pinia)

| Store | Responsibility |
|---|---|
| `flights.ts` | Live flight list, polling, rate-limit backoff, trajectory fetch & cache |
| `logs.ts` | Logged flight list, refresh, `byId()` lookup |
| `map.ts` | Viewport bounds, user location, query bounds with 500 km clamp |
| `ui.ts` | Mode, view, time shift, time window, selected flight ICAO24, selected log ID, toast messages |
| `identity.ts` | Browser UUID (persisted in `localStorage`) |

### Key Data Flows

**Live flight view:**
```
Map viewport change (debounced 400ms)
  → flights store refresh()
  → GET /flights/nearby?bounds&time_shift_minutes
  → Enrich with aircraft registry data
  → Render LiveFlightMarkers
  → Poll every 30s (exponential backoff on 429)
```

**Trajectory display:**
```
User clicks live flight marker
  → ui store: selectedFlightIcao24 = icao24
  → flights store watcher triggers loadTrajectory()
  → GET /flights/{icao24}/trajectory (samples last 60 min at 10-min intervals)
  → FlightTrajectory renders dashed blue polyline + dot markers
  → Cleared on mode switch or new flight selected
```

**Log a flight:**
```
User clicks "Report this flight" in popup
  → ReportFlightModal opens (flight data pre-filled)
  → User adds note + up to 3 photos
  → POST /logs (multipart/form-data)
  → Backend: saves photos, creates FlightLog, enriches aircraft
  → Background task: build_trajectory() → stored in log.trajectory JSON
  → logs store refreshed
```

**Logged flight trajectory:**
```
User selects a logged flight marker
  → ui store: selectedLogId set
  → logsStore.byId(selectedLogId).trajectory read directly
  → FlightTrajectory renders stored trajectory points
```

---

## Live Flight Providers

### OpenSky Network

- Authentication: OAuth2 client credentials (token cached, auto-refreshed)
- Bounds query: `GET /api/states/all?lamin&lomin&lamax&lomax[&time]`
- Single aircraft: `GET /api/states/all?icao24={hex}[&time]` (global, no bounds)
- History: up to **60 minutes** in the past (requires credentials)
- Rate limits: exponential backoff on 429 (1min → 2min → 5min → 10min)

### ADS-B Exchange

- Authentication: `api-auth` header with API key
- Bounds query: radius-based, max **185.2 km**
- History: **not supported**
- No trajectory support

---

## Trajectory Sampling

When a live flight is selected, or when a flight is logged, the backend samples historical positions:

```
reference_time = now (wall-clock, always current regardless of time shift)
for offset in [0, 10, 20, 30, 40, 50, 60] minutes:
    query_time = reference_time - offset * 60  (rounded to 5s boundary)
    record = provider.get_flight_by_icao24(icao24, query_time)
    if found → append TrajectoryPoint
    if not found → skip (radar dropout, continue searching)
return points sorted oldest → newest
```

Default: **60 minutes** back, **10-minute** steps → up to 7 sample points.
Both values are configurable as query parameters on the trajectory endpoint.

---

## User Identity

There are no user accounts. Each browser generates a random **UUID v4** stored in `localStorage` (`owner_uuid`). This UUID is attached to flight logs, allowing the UI to distinguish "your" logs from others' when viewing nearby logs.

---

## Photo Storage

- Stored on disk at `./uploads/` (Docker volume)
- Resized to max **1600px** width (Pillow); EXIF metadata preserved
- Max **3 photos** per flight log
- Served at `GET /photos/{photo_id}` via `FileResponse`
- Paths stored relative to `upload_dir` in the database
