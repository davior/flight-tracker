# Flight Logger – Frontend Specification

## Overview

Build a responsive frontend interface for the Flight Logger backend.

The UI must work seamlessly across:

* Mobile browsers (primary focus)
* Tablet
* Desktop

The interface is map-first and touch-friendly.

---

## Tech Stack

Framework:

* Vue 3 (Composition API)
* TypeScript

Mapping:

* Leaflet (via vue-leaflet)

UI:

* Use a lightweight, modern UI system (e.g. Tailwind CSS + headless components)

State:

* Pinia (state management)

HTTP:

* Axios or Fetch API

---

## Core UI Layout

### Main Screen

* Full-screen interactive map (Leaflet)
* No margins or padding (map covers entire viewport)

### Overlay Elements

#### Bottom Navigation Bar (fixed)

Height: ~60px

Contains:

* Toggle: "Live Flights"
* Toggle: "Logged Flights"

---

#### Floating Action Buttons (FABs)

Position: right side, stacked vertically

Buttons:

1. 📍 Center on My Location
2. 🧭 Set Location Manually (fallback if GPS unavailable)
3. 🔄 Refresh
4. ⚙️ Filters

---

#### View Toggle (top or floating)

* Toggle between:

  * Map View
  * List View

---

## Map Behaviour

### Interaction

* Pinch to zoom (mobile)
* Scroll zoom (desktop)
* Pan freely

### Data Fetching

Use map bounds (NOT fixed radius):

* On map move/zoom:

  * Get bounding box (lat/lon)
  * Request data within bounds

Debounce requests (300–500ms)

---

### Live Flights Mode

* Fetch from: `/flights/nearby`
* Poll every 20 seconds
* Also refresh on map move

---

### Logged Flights Mode

* Fetch from: `/logs/nearby`
* Use bounding box + time filter

---

## Flight Markers

### Live Flights

* Marker icon: aircraft-style or dot
* Clicking marker:

  * Show popup with:

    * Callsign
    * Aircraft type
    * Altitude (optional)
    * Heading (optional)

  * Button: "Report this flight"

---

### Logged Flights

* Marker icon: different color/style
* Clicking marker:

  * Show popup:

    * Callsign
    * Aircraft type
    * Time logged
    * Thumbnail image
    * Note preview

  * Button: "View details"

---

## Report Flight Flow

Triggered from Live Flight popup.

### Modal / Bottom Sheet

Fields:

* Callsign (readonly)
* Aircraft type (readonly if available)
* Comment (textarea)

### Photo Inputs

Two buttons:

1. 📷 Take Photo

   * Uses camera (mobile)
   * `<input capture="environment">`

2. 📁 Upload Photos

   * Multiple selection allowed
   * Max total images = 3

Preview selected images.

---

### Submit

* POST to `/logs`
* After success:

  * Close modal
  * Refresh logged flights

---

## Logged Flights – List View

Each item shows:

* Callsign
* Aircraft type
* Distance from user
* Time logged
* First image (thumbnail)

Sorted by:

* Distance OR newest first (choose nearest-first default)

---

## Logged Flight Detail View

When clicking a logged flight:

Show full detail panel:

* Callsign
* Aircraft type
* Distance
* Time logged
* Location
* Full note
* Image gallery

---

## Edit Mode (only for owner)

Condition:

* user_id matches log owner

Editable:

* Comment
* Photos:

  * Add (max 3 total)
  * Remove

---

## Filters (Logged Flights)

Accessible via ⚙️ button.

Options:

Time window:

* 3 hours
* 6 hours
* 12 hours
* 1 day
* 3 days
* 1 week
* 2 weeks
* 1 month

---

## User Identity (MVP)

* Generate UUID on first load
* Store in localStorage
* Send with every log request

---

## State Management

Global state should include:

* currentView (live / logged)
* mapBounds
* userLocation
* logs
* liveFlights
* filters (time window)

---

## API Integration

### Live Flights

GET `/flights/nearby`

* params: lat, lon (center)

---

### Logged Flights

GET `/logs/nearby`

* params:

  * lat
  * lon
  * bounds (if supported)
  * time_window

---

### Create Log

POST `/logs`

* multipart/form-data
* includes images

---

## Performance Considerations

* Debounce map movement
* Limit API calls
* Use marker clustering if many points

---

## Responsive Design

### Mobile (primary)

* Bottom sheet modals
* Large touch targets
* Fullscreen map

### Desktop

* Optional side panel for list view
* Hover interactions allowed

---

## Future Considerations (Do NOT implement now)

* User accounts
* Notifications
* Real-time WebSocket updates
* Advanced clustering

---
