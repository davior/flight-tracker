import type { ApiLoggedFlight } from "@/types/api";

export function sortLoggedFlightsNearestFirst(logs: ApiLoggedFlight[]): ApiLoggedFlight[] {
  return [...logs].sort((left, right) => {
    if (left.distance_km !== right.distance_km) {
      return left.distance_km - right.distance_km;
    }
    return new Date(right.created_at).getTime() - new Date(left.created_at).getTime();
  });
}
