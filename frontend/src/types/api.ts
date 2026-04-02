export type AppMode = "live" | "logged";
export type AppView = "map" | "list";
export type TimeWindow = "3h" | "6h" | "12h" | "1d" | "3d" | "7d" | "14d" | "30d";

export interface MapBounds {
  north: number;
  south: number;
  east: number;
  west: number;
}

export interface LatLng {
  lat: number;
  lon: number;
}

export interface LiveQueryState {
  visibleBounds: MapBounds;
  queryBounds: MapBounds;
  center: LatLng;
  isClamped: boolean;
}

export interface ApiPhoto {
  id: number;
  file_path: string;
  url: string;
  created_at: string;
}

export interface ApiLiveFlight {
  icao24: string;
  callsign: string | null;
  origin_country: string | null;
  latitude: number;
  longitude: number;
  altitude: number | null;
  velocity: number | null;
  heading: number | null;
  vertical_rate: number | null;
  last_contact: number | null;
  distance_km: number;
  type_code: string | null;
  manufacturer: string | null;
  model: string | null;
  category: string | null;
  category_label: string | null;
  category_description: string | null;
  display_type: string | null;
}

export interface ApiLoggedFlight {
  id: number;
  created_at: string;
  icao24: string;
  callsign: string | null;
  note: string | null;
  aircraft_latitude: number | null;
  aircraft_longitude: number | null;
  logger_latitude: number | null;
  logger_longitude: number | null;
  owner_uuid: string | null;
  type_code: string | null;
  manufacturer: string | null;
  model: string | null;
  category: string | null;
  category_label: string | null;
  category_description: string | null;
  display_type: string | null;
  photos: ApiPhoto[];
  distance_km: number;
  is_owner: boolean;
}

export interface ApiCreatedLog {
  id: number;
  created_at: string;
  icao24: string;
  callsign: string | null;
  origin_country: string | null;
  departure_airport: string | null;
  arrival_airport: string | null;
  aircraft_latitude: number | null;
  aircraft_longitude: number | null;
  altitude: number | null;
  velocity: number | null;
  heading: number | null;
  vertical_rate: number | null;
  owner_uuid: string | null;
  logger_name: string | null;
  logger_location: string | null;
  logger_latitude: number | null;
  logger_longitude: number | null;
  note: string | null;
  type_code: string | null;
  manufacturer: string | null;
  model: string | null;
  category: string | null;
  category_label: string | null;
  category_description: string | null;
  display_type: string | null;
  photos: ApiPhoto[];
}

export interface CreateLogFields {
  icao24: string;
  callsign?: string | null;
  aircraft_latitude?: number | null;
  aircraft_longitude?: number | null;
  altitude?: number | null;
  velocity?: number | null;
  heading?: number | null;
  vertical_rate?: number | null;
  owner_uuid: string;
  logger_latitude?: number | null;
  logger_longitude?: number | null;
  note?: string | null;
}

export interface ReportDraft {
  note: string;
  files: File[];
}
