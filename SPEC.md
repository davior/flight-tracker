# Flight Logger – Specification

## Overview

Flight Logger is a web application that allows users to:

### Log Flights the see
1. View aircraft currently near their location
2. Change the flights they can see based on radius (like 20km, 50km, 100km - default to 20km)
3. Log a selected flight with contextual information (and a user entered note)
4. Upload up to 3 photos per log (resized, EXIF preserved)
5. Store logs in a MariaDB database
6. Enrich aircraft data using ICAO24 lookup with local caching

---
### View flights logged by others
1. View logs of flights near their location
2. Change the radius of the area to view logs in
3. Change how far back to view flight logs for (number of days from 1 to 30 - default to 1)
4. Boolean Filter to "Show only my logs"
5. Edit the log details if they were the person who uploaded it

## Tech Stack

Backend:

* Python
* FastAPI
* SQLAlchemy
* MariaDB
* Pillow (image processing)

Frontend (later phase):

* Plain HTML, CSS, JavaScript

External APIs:

* OpenSky Network (flight positions)

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

* lat
* lon
* radius_km (default 50)

Returns:

* list of aircraft from OpenSky

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

### GET /logs

* Returns recent logs
* Includes photo URLs

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

---

## Non-Goals (for now)

* Authentication
* Real-time updates (polling is fine)
* Full trajectory tracking
* Complex UI frameworks

---

## Development Order

1. Database models
2. Aircraft enrichment service
3. Flight API (OpenSky integration)
4. Logging endpoint with photo upload
5. Logs retrieval
6. Photo serving
7. Frontend (later)

---


## Nearby Logged Flights (New Feature)

Users can retrieve previously logged flights near their current location.

### Query Behavior

Filter logs by:

1. Distance from user location
2. Time window

---

## API Endpoint

### GET /logs/nearby

Query parameters:

* lat (required)
* lon (required)
* radius_km (required, must be one of predefined values)
* time_window (required)

---

## Vabirable Radius Values
 Defined by the interface but allow variable input
* 20 km
* 50 km
* 100 km

Reject other values.

---

## Allowed Time Windows

* "1h"   (last 1 hour)
* "6h"
* "24h"
* "7d"
* "30d"

---

## Filtering Logic

Return logs where:

* Distance between (lat, lon) and (aircraft_latitude, aircraft_longitude) <= radius_km
* created_at >= NOW() - time_window

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
flight-logger/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── db.py
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── config.py
│   │   ├── routes/
│   │   │   ├── flights.py
│   │   │   ├── logs.py
│   │   │   ├── photos.py
│   │   ├── services/
│   │   │   ├── enrichment.py
│   │   │   ├── opensky.py
│   │   └── utils/
│   │       ├── image.py
│   ├── requirements.txt
│
├── frontend/
│   ├── index.html
│   ├── app.js
│   ├── styles.css
│
├── uploads/
├── docker-compose.yml
└── SPEC.md