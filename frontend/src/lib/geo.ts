import type { LatLng, MapBounds } from "@/types/api";

const EARTH_RADIUS_KM = 6371;
const GEO_EPSILON = 0.000001;
const CLAMP_RADIUS_MARGIN_KM = 0.1;

export const MAX_NEARBY_RADIUS_KM = 500;

export function haversineKm(from: LatLng, to: LatLng): number {
  const lat1 = (from.lat * Math.PI) / 180;
  const lat2 = (to.lat * Math.PI) / 180;
  const dLat = ((to.lat - from.lat) * Math.PI) / 180;
  const dLon = ((to.lon - from.lon) * Math.PI) / 180;

  const a =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos(lat1) * Math.cos(lat2) * Math.sin(dLon / 2) * Math.sin(dLon / 2);

  return EARTH_RADIUS_KM * (2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a)));
}

export function deriveCenterFromBounds(bounds: MapBounds): LatLng {
  return {
    lat: (bounds.north + bounds.south) / 2,
    lon: (bounds.east + bounds.west) / 2,
  };
}

export function deriveRadiusFromBounds(bounds: MapBounds): number {
  const center = deriveCenterFromBounds(bounds);
  const corners: LatLng[] = [
    { lat: bounds.north, lon: bounds.east },
    { lat: bounds.north, lon: bounds.west },
    { lat: bounds.south, lon: bounds.east },
    { lat: bounds.south, lon: bounds.west },
  ];

  return corners.reduce((max, corner) => Math.max(max, haversineKm(center, corner)), 1);
}

export function boundsEqual(left: MapBounds, right: MapBounds, epsilon = GEO_EPSILON): boolean {
  return (
    Math.abs(left.north - right.north) <= epsilon &&
    Math.abs(left.south - right.south) <= epsilon &&
    Math.abs(left.east - right.east) <= epsilon &&
    Math.abs(left.west - right.west) <= epsilon
  );
}

function buildCenteredSquareBounds(center: LatLng, halfSpan: number): MapBounds {
  const north = Math.min(90, center.lat + halfSpan);
  const south = Math.max(-90, center.lat - halfSpan);
  const east = Math.min(180, center.lon + halfSpan);
  const west = Math.max(-180, center.lon - halfSpan);

  // Ensure bounds are valid (north > south, east > west)
  // This can happen when zoomed out to extreme latitudes
  const minSpan = GEO_EPSILON * 2;

  return {
    north: Math.max(north, south + minSpan),
    south: Math.min(south, north - minSpan),
    east: Math.max(east, west + minSpan),
    west: Math.min(west, east - minSpan),
  };
}

export function fitBoundsToMaxRadius(
  bounds: MapBounds,
  maxRadiusKm: number,
): { bounds: MapBounds; isClamped: boolean } {
  const safeRadius = Math.max(maxRadiusKm - CLAMP_RADIUS_MARGIN_KM, 0.1);
  if (deriveRadiusFromBounds(bounds) <= safeRadius) {
    return { bounds, isClamped: false };
  }

  const center = deriveCenterFromBounds(bounds);
  const maxHalfSpan = Math.min(
    bounds.north - center.lat,
    center.lat - bounds.south,
    bounds.east - center.lon,
    center.lon - bounds.west,
    90 - center.lat,
    center.lat + 90,
    180 - center.lon,
    center.lon + 180,
  );

  let low = 0;
  let high = Math.max(maxHalfSpan, GEO_EPSILON);
  let best = buildCenteredSquareBounds(center, low);

  for (let index = 0; index < 32; index += 1) {
    const halfSpan = (low + high) / 2;
    const candidate = buildCenteredSquareBounds(center, halfSpan);
    if (deriveRadiusFromBounds(candidate) <= safeRadius) {
      best = candidate;
      low = halfSpan;
    } else {
      high = halfSpan;
    }
  }

  return { bounds: best, isClamped: !boundsEqual(best, bounds) };
}

export function resolveLoggedFlightPoint(flight: {
  aircraft_latitude: number | null;
  aircraft_longitude: number | null;
  logger_latitude: number | null;
  logger_longitude: number | null;
}): LatLng | null {
  if (flight.aircraft_latitude !== null && flight.aircraft_longitude !== null) {
    return { lat: flight.aircraft_latitude, lon: flight.aircraft_longitude };
  }
  if (flight.logger_latitude !== null && flight.logger_longitude !== null) {
    return { lat: flight.logger_latitude, lon: flight.logger_longitude };
  }
  return null;
}

export function formatDistance(distanceKm: number): string {
  if (distanceKm < 1) {
    return `${Math.round(distanceKm * 1000)} m`;
  }
  return `${distanceKm.toFixed(1)} km`;
}
