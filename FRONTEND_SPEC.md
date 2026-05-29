# Chemtrail Tracker (Flight Logger) – Frontend Specification

## Overview

Build a responsive frontend interface for the Chemtrail Tracker (Flight Logger) backend.

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

## User Authentication

* Email/password registration and login
* Optional Google OAuth2
* JWT token-based authentication for API requests
* Session-based user identity (replaces UUID approach)
* Email verification required before account use
* Password reset via email token
* Admin users can manage all logs

---

## State Management (Pinia)

Global state should include:

* `auth.ts` - Current user, JWT token, authentication status
* `flights.ts` - Live flight list, polling status, trajectory cache
* `logs.ts` - Logged flight list, refresh status
* `map.ts` - Viewport bounds, user location, query bounds
* `ui.ts` - Current view, view mode, time filters, selected flight, toasts
* `identity.ts` - (Legacy) Browser UUID for backwards compatibility

---

## API Integration

### Authentication

* `POST /auth/register` - Create account
* `POST /auth/login` - Get JWT token
* `POST /auth/verify-email` - Verify email with token
* `POST /auth/request-password-reset` - Request password reset
* `POST /auth/reset-password` - Reset password with token
* `GET /auth/me` - Get current user info

All authenticated endpoints require `Authorization: Bearer {jwt_token}` header.

### Live Flights

`GET /flights/nearby`

* Query params: north, south, east, west, time_shift_minutes (optional)

---

### Logged Flights

`GET /logs/nearby`

* Query params: north, south, east, west, time_window_days
* Returns only logs within specified viewport and time window
* Indicates ownership for filtering edit/delete actions

---

### Create/Edit/Delete Log

* `POST /logs` - Create log (multipart/form-data with images, requires auth)
* `PATCH /logs/{log_id}` - Edit log (owner only)
* `DELETE /logs/{log_id}` - Delete log (owner or admin only)

---

## Performance Considerations

* Debounce map movement (300-500ms)
* Limit API call frequency with rate-limit backoff
* Cache trajectories in memory
* Use marker clustering for large flight counts

---

## Responsive Design

### Mobile (primary)

* Bottom sheet modals for reporting flights
* Large touch targets (48px minimum)
* Fullscreen map with overlay controls
* Bottom navigation bar for mode toggle

### Desktop

* Side drawer for flight details
* Hover interactions on markers
* Keyboard shortcuts for common actions

---

## Future Considerations (Do NOT implement now)

* Real-time WebSocket updates (polling is sufficient)
* Advanced trajectory prediction
* Flight plan routing data
* Multi-device synchronization
* Dark mode

---
