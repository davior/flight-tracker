import type { LatLng, MapBounds } from "@/types/api";

const EARTH_RADIUS_KM = 6371;

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
