# Chemtrail Tracker (Flight Tracker) — Architecture Document

## Overview

Chemtrail Tracker is a full-stack web application for viewing live aircraft positions on a map and logging flight sightings. It consists of three services orchestrated by Docker Compose: a Vue 3 single-page application, a FastAPI backend, and a MariaDB database.

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
- `auth_router` — prefix `/auth` (authentication endpoints)
- `flights_router` — prefix `/flights` (live flight queries)
- `logs_router` — prefix `/logs` (flight logging and retrieval)
- `photo_router` — prefix `/photos` (photo serving)
- `airports_router` — prefix `/airports` (airport data)
- `admin_router` — prefix `/admin` (administrative operations)

### Configuration (`app/config.py`)

All settings are loaded from environment variables via `Settings.from_env()` (LRU-cached). Key settings:

**Database & Storage:**

| Setting | Default | Description |
|---|---|---|
| `database_url` | MariaDB local | SQLAlchemy connection string |
| `upload_dir` | `./uploads` | Uploaded photo storage directory |
| `runtime_dir` | `/tmp/flight-logger-cache` | Aircraft registry snapshot cache |
| `max_nearby_radius_km` | `500` | Maximum query radius for live/logged flights |

**Live Flight Provider:**

| Setting | Default | Description |
|---|---|---|
| `live_flight_provider` | `opensky` | Active provider: `opensky` or `adsbx` |
| `opensky_client_id` | `None` | OpenSky Network OAuth client ID |
| `opensky_client_secret` | `None` | OpenSky Network OAuth client secret |
| `adsbx_api_key` | `None` | ADS-B Exchange API key |
| `adsbx_api_base_url` | `https://adsbexchange.com/api/aircraft` | ADS-B Exchange API endpoint |

**Authentication & Security:**

| Setting | Default | Description |
|---|---|---|
| `jwt_secret_key` | Required in prod | Secret key for JWT signing |
| `jwt_algorithm` | `HS256` | JWT signing algorithm |
| `access_token_expire_minutes` | `1440` | JWT token lifetime (1 day) |
| `google_oauth_client_id` | `None` | Google OAuth client ID (optional) |
| `google_oauth_client_secret` | `None` | Google OAuth client secret (optional) |

**Email Service:**

| Setting | Default | Description |
|---|---|---|
| `smtp_host` | `None` | SMTP server hostname |
| `smtp_port` | `587` | SMTP server port |
| `smtp_user` | `None` | SMTP authentication username |
| `smtp_password` | `None` | SMTP authentication password |
| `smtp_from_email` | `noreply@domain` | From address for transactional emails |

**Logging & Features:**

| Setting | Default | Description |
|---|---|---|
| `log_level` | `INFO` | Application log level |
| `enable_ai_features` | `False` | Enable Claude AI integration |
| `environment` | `development` | Deployment environment |

### API Endpoints

#### Authentication (`/auth`)

| Method | Path | Description |
|---|---|---|
| `POST` | `/auth/register` | Create a new user account |
| `POST` | `/auth/login` | Authenticate and get JWT token |
| `POST` | `/auth/verify-email` | Verify email with token |
| `POST` | `/auth/request-password-reset` | Request password reset email |
| `POST` | `/auth/reset-password` | Reset password with token |
| `GET` | `/auth/me` | Get current authenticated user |

#### Flights (`/flights`)

| Method | Path | Description |
|---|---|---|
| `GET` | `/flights/capabilities` | Provider capabilities (history support, limits) |
| `GET` | `/flights/provider-status` | Status of configured live-flight providers |
| `GET` | `/flights/nearby` | Live flights in map bounds; `time_shift_minutes` (0–60) for historical view |
| `GET` | `/flights/trajectory/{icao24}` | Sampled historical positions for one aircraft |

**Trajectory parameters:**
- `max_history_minutes` (1–60, default **60**) — how far back to sample
- `step_minutes` (1–10, default **10**) — interval between samples
- Reference time is always **current wall-clock time** (not affected by time shift)

#### Flight Logs (`/logs`)

| Method | Path | Description |
|---|---|---|
| `POST` | `/logs` | Create a flight log (multipart, up to 3 photos; requires auth) |
| `GET` | `/logs/{log_id}` | Get details of a specific logged flight |
| `PATCH` | `/logs/{log_id}` | Edit a log (owner only; requires auth) |
| `DELETE` | `/logs/{log_id}` | Delete a log (owner or admin; requires auth) |
| `GET` | `/logs/nearby` | Logged flights in map bounds within a time window |

#### Photos (`/photos`)

| Method | Path | Description |
|---|---|---|
| `GET` | `/photos/{photo_id}` | Serve an uploaded photo |
| `GET` | `/photos/{photo_id}/metadata` | Get photo metadata (EXIF, dimensions, etc.) |

### Services

**Live Flight Providers:**

| Service | Description |
|---|---|
| `opensky.py` | OpenSky Network provider — OAuth2 token management, bounds queries, single-aircraft queries, up to 60 min history |
| `adsbx.py` | ADS-B Exchange provider — radius-based queries (max 185.2 km), no history support |
| `live_flight_provider.py` | Abstract `LiveFlightProvider` interface |
| `live_flight_provider_factory.py` | Factory that selects and constructs the configured provider at startup |
| `provider_router.py` | Routes requests between multiple providers for redundancy/fallback |
| `provider_usage_tracker.py` | Monitors provider API usage and rate limits |

**Aircraft Enrichment:**

| Service | Description |
|---|---|
| `aircraft_enrichment.py` | ICAO24 lookup with local caching and fallback to external enrichment |
| `aircraft_enrichment_queue.py` | Background queue for async registry enrichment |
| `aircraft_categories.py` | Loads static aircraft category reference data and type mappings |

**User & Authentication:**

| Service | Description |
|---|---|
| `auth_service.py` | JWT token generation/validation, password hashing, verification token management |
| `email_service.py` | Email sending for verification, password reset, and notifications |

**Data & Storage:**

| Service | Description |
|---|---|
| `image_storage.py` | Photo upload, resizing (max 1600px), EXIF preservation, deletion |
| `trajectory.py` | Historical trajectory building by sampling backwards in time; skips radar dropouts |
| `data_seeder.py` | Database initialization and reference data seeding |
| `data_sync.py` | Manual or scheduled aircraft registry synchronization from external sources |
| `data_refresh_scheduler.py` | Periodic refresh of reference data and caches |

**Advanced Features:**

| Service | Description |
|---|---|
| `ai_service.py` | Claude AI integration for analysis and features |
| `threat_detector.py` | Anomaly detection and threat classification |

### Database Schema

```
users                           (authentication & user accounts)
├── id                  PK
├── email               String(255), unique, indexed
├── username            String(64), unique, indexed
├── password_hash       String(255)
├── is_verified         Boolean (default: false)
├── verification_token  String(255)
├── verification_token_expires DateTime
├── password_reset_token String(255)
├── password_reset_expires DateTime
├── google_id           String(255), unique, optional
├── tutorial_seen       Boolean (default: false)
├── is_admin            Boolean (default: false)
├── is_active           Boolean (default: true)
└── created_at          DateTime (UTC)

flight_logs
├── id                  PK
├── created_at          DateTime (UTC), indexed
├── flight_time         DateTime (UTC), indexed
├── icao24              String(6), indexed
├── callsign            String(16)
├── origin_country      String(64)
├── departure_airport   String(8)
├── arrival_airport     String(8)
├── aircraft_latitude   Numeric(9,6)
├── aircraft_longitude  Numeric(9,6)
├── altitude            Float
├── velocity            Float
├── heading             Float
├── vertical_rate       Float
├── owner_id            FK → users.id, nullable, indexed
├── owner_uuid          String(36), indexed (legacy)
├── logger_name         String(128)
├── logger_location     String(255)
├── logger_latitude     Numeric(9,6)
├── logger_longitude    Numeric(9,6)
├── note                Text
├── trajectory          JSON (trajectory points)
└── photos              → flight_log_photos (cascade delete)

flight_log_photos
├── id                  PK
├── flight_log_id       FK → flight_logs.id (CASCADE), indexed
├── file_path           String(512)
├── media_type          String(16)
└── created_at          DateTime (UTC)

aircraft_registry      (enrichment cache)
├── icao24              PK String(6)
├── registration        String(32)
├── type_code           String(8), indexed
├── manufacturer        String(128)
├── model               String(128)
├── category            String(16)
├── operator            String(128)
├── operator_icao       String(8)
├── operator_iata       String(8)
├── operator_callsign   String(64)
├── owner               String(128)
├── serial_number       String(32)
├── first_seen          DateTime
└── last_updated        DateTime

aircraft_types        (reference data)
├── type_code           PK
├── manufacturer
├── model
└── category

aircraft_categories   (reference data)
├── code                PK
├── label
└── description

data_sync_log         (tracking external syncs)
├── id                  PK
├── source              String
├── last_synced_at      DateTime
├── last_sync_status    Enum
├── last_sync_error     Text
└── row_count           Integer
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
| `auth.ts` | Current user, JWT token, authentication status, login/logout/register |
| `flights.ts` | Live flight list, polling, rate-limit backoff, trajectory fetch & cache |
| `logs.ts` | Logged flight list, refresh, `byId()` lookup, ownership tracking |
| `map.ts` | Viewport bounds, user location, query bounds with 500 km clamp |
| `ui.ts` | Mode, view, time shift, time window, selected flight ICAO24, selected log ID, toasts |
| `identity.ts` | Browser UUID (persisted in `localStorage`, legacy) |

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

The app uses a **two-tier ownership model**:

### Authenticated users (primary)

Users register with email + password (or Google OAuth) and receive a **JWT** access token. The token is stored in `localStorage` and sent as `Authorization: Bearer {token}` on every API request. The backend validates it via `get_current_user` (in `app/dependencies.py`) and returns the `User` ORM object.

User accounts are stored in the `users` table (added in migration `20260410_0000_c5d8e3f9a012_add_users_and_owner_id.py`). Each `FlightLog` has an `owner_id` FK to `users.id` (`ON DELETE SET NULL`).

Auth endpoints live at `/auth/`:
- `POST /auth/register` — email + username + password; sends verification email
- `POST /auth/login` — returns `TokenResponse` with JWT
- `POST /auth/verify-email` — consumes one-time token from email link
- `POST /auth/resend-verification` — resend verification email
- `POST /auth/forgot-password` / `POST /auth/reset-password` — password reset via email
- `POST /auth/google` — Google OAuth (ID token exchange)
- `GET /auth/me` — returns current user
- `PATCH /auth/me` — update username or password
- `PATCH /auth/me/tutorial-seen` — marks the one-time onboarding tutorial complete

### Anonymous sessions (legacy / fallback)

Browsers without an account generate a random **UUID v4** stored in `localStorage` (`owner_uuid`). This was the original identity mechanism. The `owner_uuid` column is still present on `flight_logs` for backwards compatibility, but new logs written by authenticated users set `owner_id` instead.

The `is_owner` flag in `GET /logs/nearby` responses uses `owner_id` to determine ownership.

---

## Photo Storage

- Stored on disk at `./uploads/` (Docker volume)
- Resized to max **1600px** width (Pillow); EXIF metadata preserved
- Max **3 photos** per flight log
- Served at `GET /photos/{photo_id}` via `FileResponse`
- Paths stored relative to `upload_dir` in the database
