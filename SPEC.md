# Flight Logger – Specification

## Overview

Flight Logger is a web application that allows users to:

### View live flights
1. View aircraft currently near their location
2. Explore live flights in a map view or list view
3. Query flights using the current map viewport rather than a fixed radius selector
4. Apply a live time shift from now back to 60 minutes ago
5. Keep live polling active while respecting the selected time shift
6. Log a selected live flight with contextual information and a user-entered note

---
### Log and browse flight reports
1. Upload up to 3 photos per log (resized, EXIF preserved)
2. Store logs in a MariaDB database
3. View logs of flights near the visible map area
4. Filter logged flights by time window
5. Distinguish community logs from the viewer's own logs
6. View logged flights in either map or list mode

---
### Aircraft enrichment and provider support
1. Enrich aircraft data using ICAO24 lookup with local caching
2. Support multiple live-flight providers behind a common interface
3. Expose whether the active live-flight provider supports historical live lookups

## Tech Stack

Backend:

* Python
* FastAPI
* SQLAlchemy
* MariaDB
* Pillow (image processing)

Frontend:

* Vue 3
* TypeScript
* Pinia
* Leaflet
* Vite

External APIs:

* OpenSky Network (flight positions, including authenticated historical lookups up to 60 minutes)
* ADS-B Exchange (current live positions)

---

## Core Concepts

### Aircraft Identity

* ICAO24 is the primary identifier
* Callsign is metadata only (not unique)

---

## Database Schema

### flight_logs

* id (PK)
* created_at

Aircraft:

* icao24 (required)
* callsign
* origin_country

Route:

* departure_airport
* arrival_airport

Aircraft position:

* aircraft_latitude
* aircraft_longitude
* altitude
* velocity
* heading
* vertical_rate

Observer:

* logger_name
* logger_location
* logger_latitude
* logger_longitude

Other:

* note

---

### flight_log_photos

* id (PK)
* flight_log_id (FK → flight_logs.id)
* file_path
* created_at

Constraints:

* max 3 photos per flight_log

---

### aircraft_registry (cache)

* icao24 (PK)
* registration
* type_code
* manufacturer
* model
* category
* first_seen
* last_updated

---

### aircraft_types (static)

* type_code (PK)
* manufacturer
* model
* category

---

## API Endpoints

### GET /flights/nearby

Params:

* north
* south
* east
* west
* time_shift_minutes (optional, 0-60)

Returns:

* list of aircraft from the configured live-flight provider

Behavior:

* Uses the current visible map bounds
* Rejects oversized live queries beyond the configured maximum radius
* For historical live lookups, applies a time shift in minutes from now
* Historical lookups are only available when the configured provider supports them

---

### GET /flights/capabilities

Returns:

* provider
* supports_history
* max_history_minutes
* history_step_minutes

---

### POST /logs

Accepts multipart/form-data

Fields:

* aircraft data (icao24 required)
* route (optional)
* observer info (optional)
* note (optional)
* photos (0–3 files)

Behavior:

* Resize images (max 1600px)
* Preserve EXIF metadata
* Save to disk
* Store file paths in DB
* Enrich aircraft via registry

---

### GET /logs/nearby

Query parameters:

* north
* south
* east
* west
* time_window_days
* viewer_uuid

Returns:

* nearby logged flights for the current viewport
* photo URLs
* ownership flag for the current viewer

---

### GET /photos/{photo_id}

* Returns image file

---

## Aircraft Enrichment

Process:

1. Check aircraft_registry
2. If not found:

   * Query external source
   * Store result
3. Map type_code → aircraft_types

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

---

## Non-Goals (for now)

* Authentication
* Full trajectory tracking
* Persistent storage of live-flight history snapshots

Polling for live updates is an explicit supported behavior.

---

## Development Order

1. Database models
2. Aircraft enrichment service
3. Flight API (OpenSky integration)
4. Logging endpoint with photo upload
5. Logs retrieval
6. Photo serving
7. Map-first frontend with live and logged modes

---


## Nearby Logged Flights (New Feature)

Users can retrieve previously logged flights near the currently visible map area.

### Query Behavior

Filter logs by:

1. Current map bounds
2. Logged-flight day range

---

## API Endpoint

### GET /logs/nearby

Query parameters:

* north (required)
* south (required)
* east (required)
* west (required)
* time_window_days (required)

---

## Allowed Time Windows

* numeric days from `0.5` to `28`
* increments of `0.5`
* default `1`

---

## Filtering Logic

Return logs where:

* The logged aircraft position falls within the requested bounds
* flight_time >= NOW() - INTERVAL time_window_days DAY

---

## Response

Same as GET /logs, but filtered.

Include:

* aircraft data
* observer data
* photo URLs

---

## Notes

* Use aircraft position for distance calculation (not logger position)
* If aircraft_latitude or longitude is null, exclude record
* Distance calculation can use Haversine formula

---



# Folder Layout
<pre>
flight-logger/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── db.py
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── config.py
│   │   ├── api/
│   │   │   ├── flights.py
│   │   │   ├── logs.py
│   │   ├── services/
│   │   │   ├── aircraft_enrichment.py
│   │   │   ├── aircraft_enrichment_queue.py
│   │   │   ├── adsbx.py
│   │   │   ├── live_flight_provider.py
│   │   │   ├── live_flight_provider_factory.py
│   │   │   ├── opensky.py
│   │   └── utils/
│   │       ├── geo.py
│   ├── requirements.txt
│
├── frontend/
│   ├── index.html
│   ├── src/
│   │   ├── App.vue
│   │   ├── components/
│   │   ├── lib/
│   │   ├── stores/
│   │   └── styles/
│
├── uploads/
├── docker-compose.yml
└── SPEC.md
</pre>
