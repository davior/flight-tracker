import type { ApiLoggedFlight } from "@/types/api";

export function sortLoggedFlightsNearestFirst(logs: ApiLoggedFlight[]): ApiLoggedFlight[] {
  return [...logs].sort((left, right) => {
    if (left.distance_km !== right.distance_km) {
      return left.distance_km - right.distance_km;
    }
    return new Date(right.flight_time).getTime() - new Date(left.flight_time).getTime();
  });
}
