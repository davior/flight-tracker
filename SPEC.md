# Flight Logger – Specification

## Overview

Flight Logger is a full-stack web application that allows users to:

### Authentication and User Accounts
1. Register and authenticate with email/password
2. Verify email address via token-based verification
3. Reset password via email token
4. Support OAuth2 (Google authentication)
5. Distinguish user logs from community logs (by owner)

---
### View live flights
1. View aircraft currently near their location
2. Explore live flights in a map view or list view
3. Query flights using the current map viewport rather than a fixed radius selector
4. Apply a live time shift from now back to 60 minutes ago
5. Keep live polling active while respecting the selected time shift
6. Log a selected live flight with contextual information and a user-entered note
7. Query historical flight trajectories (when provider supports it)

---
### Log and browse flight reports
1. Upload up to 3 photos per log (resized, EXIF preserved)
2. Store logs in a MariaDB database with owner attribution
3. View logs of flights near the visible map area
4. Filter logged flights by time window
5. Distinguish community logs from the viewer's own logs
6. View logged flights in either map or list mode
7. Edit logged flights after creation

---
### Aircraft enrichment and provider support
1. Enrich aircraft data using ICAO24 lookup with local caching
2. Support multiple live-flight providers behind a common interface
3. Expose whether the active live-flight provider supports historical live lookups
4. Capture and persist flight trajectories for logged flights
5. Track provider usage and availability

## Tech Stack

Backend:

* Python 3.11+
* FastAPI (async web framework)
* SQLAlchemy (ORM)
* Alembic (database migrations)
* MariaDB 11 (database)
* Pillow (image processing)
* PyJWT (authentication)
* Pydantic (validation and settings)

Frontend:

* Vue 3 (Composition API)
* TypeScript
* Pinia (state management)
* Leaflet (mapping)
* Vite (build tool)
* Tailwind CSS (styling)
* Vitest (testing)

External APIs:

* OpenSky Network (flight positions, authenticated historical lookups up to 60 minutes)
* ADS-B Exchange (current live positions only)
* Google OAuth2 (optional user authentication)
* SMTP2GO (email service)

Infrastructure:

* Docker Compose (local development)
* Docker (production containers)
* Caddy (reverse proxy, automatic HTTPS)

---

## Core Concepts

### Aircraft Identity

* ICAO24 is the primary identifier
* Callsign is metadata only (not unique)

---

## Database Schema

### users

* id (PK)
* email (unique)
* username (unique)
* password_hash
* is_verified (boolean)
* verification_token
* verification_token_expires
* password_reset_token
* password_reset_expires
* google_id (optional, for OAuth)
* tutorial_seen (boolean)
* is_admin (boolean)
* is_active (boolean)
* created_at

---

### flight_logs

* id (PK)
* created_at (timestamp, indexed)
* flight_time (timestamp when flight was logged, indexed)
* icao24 (string, indexed, required)
* callsign
* origin_country

Aircraft position:

* aircraft_latitude
* aircraft_longitude (indexed for spatial queries)
* altitude
* velocity
* heading
* vertical_rate

Route:

* departure_airport
* arrival_airport

Observer:

* owner_id (FK → users.id, nullable, indexed)
* owner_uuid (legacy UUID field, nullable, indexed)
* logger_name
* logger_location
* logger_latitude
* logger_longitude

Other:

* note (text)
* trajectory (JSON, optional - persisted flight path)

---

### flight_log_photos

* id (PK)
* flight_log_id (FK → flight_logs.id, indexed)
* file_path
* media_type (string, e.g., "image")
* created_at

Constraints:

* max 3 photos per flight_log

---

### aircraft_registry (cache)

* icao24 (PK)
* registration
* type_code (indexed)
* manufacturer
* model
* category
* operator
* operator_icao
* operator_iata
* operator_callsign
* owner
* serial_number
* first_seen
* last_updated

---

### flight_routes (optional)

* id (PK)
* flight_log_id (FK → flight_logs.id)
* departure_airport
* arrival_airport
* created_at

---

## API Endpoints

### Authentication

#### POST /auth/register
Register a new user account.

Fields:
* email (required)
* username (required)
* password (required)

Returns:
* user details and JWT token

---

#### POST /auth/login
Authenticate and obtain JWT token.

Fields:
* email or username
* password

Returns:
* JWT token and user details

---

#### POST /auth/verify-email
Verify email address with token.

Fields:
* verification_token

---

#### POST /auth/request-password-reset
Request password reset email.

Fields:
* email

---

#### POST /auth/reset-password
Reset password with token.

Fields:
* token
* new_password

---

#### GET /auth/me
Get current authenticated user.

Returns:
* user details

---

### Live Flights

#### GET /flights/nearby

Params:

* north (required)
* south (required)
* east (required)
* west (required)
* time_shift_minutes (optional, 0-60)

Returns:

* list of aircraft from the configured live-flight provider

Behavior:

* Uses the current visible map bounds
* Rejects oversized live queries beyond the configured maximum radius
* For historical live lookups, applies a time shift in minutes from now
* Historical lookups are only available when the configured provider supports them

---

#### GET /flights/capabilities

Returns:

* provider
* supports_history
* max_history_minutes
* history_step_minutes

---

#### GET /flights/provider-status

Returns:

* active provider name
* status of each configured provider
* last successful query time

---

#### GET /flights/trajectory/{icao24}

Get historical flight trajectory for an aircraft.

Params:

* icao24 (path parameter)
* reference_time (unix timestamp, optional)

Returns:

* list of trajectory points with lat, lng, altitude, heading, velocity, timestamp

---

### Flight Logging

#### POST /logs

Accepts multipart/form-data. Requires authentication.

Fields:

* aircraft data (icao24 required)
* route (optional - departure_airport, arrival_airport)
* observer info (optional - logger_name, logger_location, logger_latitude, logger_longitude)
* note (optional)
* photos (0–3 files)

Behavior:

* Resize images (max 1600px)
* Preserve EXIF metadata
* Save to disk
* Store file paths in DB
* Enrich aircraft via registry
* Build and store flight trajectory (background task)
* Associate log with authenticated user

Returns:

* created flight log with all details and photo URLs

---

#### GET /logs/{log_id}

Get details of a specific logged flight.

Returns:

* flight log details including photos and trajectory

---

#### PATCH /logs/{log_id}

Update a logged flight (owner only).

Fields:

* Any updatable fields (note, observer info, route)

Returns:

* updated flight log

---

#### DELETE /logs/{log_id}

Delete a logged flight (owner or admin only).

---

#### GET /logs/nearby

Query parameters:

* north (required)
* south (required)
* east (required)
* west (required)
* time_window_days (required)

Returns:

* nearby logged flights for the current viewport, filtered by time window
* photo URLs
* ownership flag for the current viewer
* distance from map center

Filtering Logic:

* Aircraft position falls within requested bounds
* flight_time >= NOW() - INTERVAL time_window_days DAY
* Excludes logs without valid aircraft coordinates

---

### Photos

#### GET /photos/{photo_id}

Get a photo file.

Returns:

* image file with appropriate content-type

---

#### GET /photos/{photo_id}/metadata

Get photo metadata.

Returns:

* file size, format, upload date, EXIF data

---

## Aircraft Enrichment

Process:

1. Check aircraft_registry cache for ICAO24
2. If not found:
   * Query external enrichment source (OpenSky or ADS-B Exchange registry)
   * Store result with timestamp
3. Enrich with detailed category information from static aircraft type mappings
4. Gracefully handle missing or incomplete data

Caching:

* Cache entries are updated periodically
* Failed lookups are cached with an error marker
* Cache respects rate limits of external providers

---

## Image Handling

* Max 3 photos
* Resize to max 1600px
* Preserve EXIF metadata
* Supported: JPEG, PNG

---

## Constraints

* Do not exceed 3 images per log
* Must handle missing aircraft metadata gracefully
* Must not crash on failed API calls
* Live flight lookups must respect the configured maximum nearby radius
* Live historical lookups are capped at 60 minutes from now
* Logged-flight filtering is viewport-based, not fixed-radius based
* Authentication is required for logging flights (creating, editing, deleting)
* Users can only edit or delete their own logs (unless admin)
* All API responses must be consistent regardless of user's authentication status

---

## Non-Goals (for now)

* Persistent storage of live-flight history snapshots (individual snapshots)
* Full real-time WebSocket updates (polling is sufficient)
* Advanced trajectory prediction or interpolation
* Flight plan / ADS-B routing data (position-only)

Polling for live updates and trajectory building is an explicit supported behavior.

---

## Implementation Notes

### Nearby Logged Flights

* Use aircraft position for distance calculation (not logger position)
* Exclude records where aircraft_latitude or longitude is null
* Distance calculation uses Haversine formula
* Allowed time windows: `0.5` to `28` days in `0.5` increments (default `1`)

### Authentication

* JWT tokens are issued on login and used for authenticated endpoints
* Password reset and email verification use time-limited tokens
* Google OAuth2 is optional and configured via environment variables
* Admin users can view/manage logs from other users



# Folder Layout

```
flight-tracker/
├── backend/
│   ├── app/
│   │   ├── main.py                    # FastAPI app entry point
│   │   ├── db.py                      # SQLAlchemy setup
│   │   ├── config.py                  # Settings and configuration
│   │   ├── models.py                  # SQLAlchemy ORM models
│   │   ├── schemas.py                 # Pydantic request/response schemas
│   │   ├── serializers.py             # Response serialization helpers
│   │   ├── dependencies.py            # FastAPI dependencies
│   │   ├── migrations.py              # Database migration helpers
│   │   ├── logging_config.py          # Logging configuration
│   │   │
│   │   ├── api/
│   │   │   ├── flights.py             # Live flight endpoints
│   │   │   ├── logs.py                # Flight logging endpoints
│   │   │   ├── auth.py                # User authentication endpoints
│   │   │   ├── airports.py            # Airport data endpoints
│   │   │   └── admin/                 # Administrative endpoints
│   │   │       └── ...
│   │   │
│   │   ├── services/
│   │   │   ├── live_flight_provider.py              # Abstract provider interface
│   │   │   ├── live_flight_provider_factory.py      # Provider factory
│   │   │   ├── provider_router.py                   # Multi-provider routing
│   │   │   ├── opensky.py                           # OpenSky integration
│   │   │   ├── adsbx.py                             # ADS-B Exchange integration
│   │   │   ├── aircraft_enrichment.py               # Aircraft data enrichment
│   │   │   ├── aircraft_enrichment_queue.py         # Async enrichment queue
│   │   │   ├── aircraft_categories.py               # Aircraft type mappings
│   │   │   ├── image_storage.py                     # Image upload/retrieval
│   │   │   ├── trajectory.py                        # Flight trajectory builder
│   │   │   ├── auth_service.py                      # JWT/auth utilities
│   │   │   ├── email_service.py                     # Email sending
│   │   │   ├── ai_service.py                        # AI integration (Claude)
│   │   │   ├── data_seeder.py                       # Database seeding
│   │   │   ├── data_sync.py                         # Data synchronization
│   │   │   ├── data_refresh_scheduler.py            # Periodic data refresh
│   │   │   ├── provider_usage_tracker.py            # Provider usage monitoring
│   │   │   ├── threat_detector.py                   # Threat detection
│   │   │   └── admin_seeder.py                      # Admin user creation
│   │   │
│   │   ├── middleware/
│   │   │   └── ...                                  # Custom middleware
│   │   │
│   │   └── utils/
│   │       ├── geo.py                 # Geospatial utilities (Haversine, bounds)
│   │       └── ...
│   │
│   ├── alembic/                       # Database migrations (Alembic)
│   │   ├── env.py
│   │   ├── script.py.mako
│   │   └── versions/
│   │
│   ├── tests/                         # Pytest test suite
│   │   ├── conftest.py
│   │   ├── test_flights_api.py
│   │   ├── test_logs_api.py
│   │   ├── test_auth_api.py
│   │   ├── test_aircraft_enrichment.py
│   │   ├── test_live_flight_providers.py
│   │   ├── test_image_storage.py
│   │   ├── test_trajectory.py
│   │   └── ...
│   │
│   ├── requirements.txt                # Python dependencies
│   ├── migrate.py                      # Migration utility script
│   └── sync_data.py                    # Data synchronization script
│
├── frontend/
│   ├── index.html
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── tailwind.config.ts
│   ├── src/
│   │   ├── main.ts                    # Entry point
│   │   ├── App.vue                    # Root component
│   │   ├── AppShell.vue               # App layout wrapper
│   │   │
│   │   ├── components/
│   │   │   ├── MapView.vue
│   │   │   ├── ListView.vue
│   │   │   ├── FlightDetails.vue
│   │   │   ├── LogForm.vue
│   │   │   └── ...
│   │   │
│   │   ├── stores/
│   │   │   ├── flights.ts             # Live flights state (Pinia)
│   │   │   ├── logs.ts                # Logged flights state (Pinia)
│   │   │   ├── map.ts                 # Map state (Pinia)
│   │   │   ├── auth.ts                # Authentication state (Pinia)
│   │   │   ├── ui.ts                  # UI state (Pinia)
│   │   │   └── ...
│   │   │
│   │   ├── types/
│   │   │   ├── api.ts                 # API response types
│   │   │   ├── auth.ts                # Auth-related types
│   │   │   └── ...
│   │   │
│   │   ├── lib/
│   │   │   ├── api.ts                 # API client
│   │   │   ├── geospatial.ts          # Geospatial utilities
│   │   │   └── ...
│   │   │
│   │   └── styles/
│   │       └── ...
│   │
│   └── package.json
│
├── web/                               # Public website (served on apex domain)
│   ├── index.html
│   └── ...
│
├── uploads/                           # Volume for flight log photos
│
├── docker-compose.yml                 # Docker Compose orchestration
├── docker-compose.prod.yml            # Production Compose config
├── Dockerfile.backend
├── Dockerfile.frontend
│
├── scripts/
│   ├── setup-server.sh                # Production server setup
│   ├── deploy.sh                      # Production deployment
│   ├── reset-production.sh            # Production reset/cleanup
│   └── ...
│
├── SPEC.md                            # This file: functional specification
├── FRONTEND_SPEC.md                   # Frontend design specification
├── ARCHITECTURE.md                    # System architecture documentation
├── README.md                          # Project overview and setup
├── MIGRATIONS.md                      # Database migration guide
├── DNS_RECORDS.md                     # DNS configuration
├── FIREWALL.md                        # Firewall rules
│
├── .env.example                       # Environment variables template
├── .env.production.example            # Production env template
└── .github/
    └── workflows/                     # GitHub Actions CI/CD
```
