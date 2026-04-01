import { defineStore } from "pinia";
import { computed, ref } from "vue";

import { MAX_NEARBY_RADIUS_KM, deriveCenterFromBounds, fitBoundsToMaxRadius } from "@/lib/geo";
import type { LatLng, LiveQueryState, MapBounds } from "@/types/api";

export const useMapStore = defineStore("map", () => {
  const center = ref<LatLng | null>(null);
  const zoom = ref(12);
  const bounds = ref<MapBounds | null>(null);
  const userLocation = ref<LatLng | null>(null);
  const COORDINATE_EPSILON = 0.00001;
  const viewportCenter = computed(() => (bounds.value ? deriveCenterFromBounds(bounds.value) : center.value));

  const query = computed(() => (bounds.value && viewportCenter.value ? { bounds: bounds.value, center: viewportCenter.value } : null));
  const liveQuery = computed<LiveQueryState | null>(() => {
    if (!bounds.value || !viewportCenter.value) {
      return null;
    }

    const { bounds: queryBounds, isClamped } = fitBoundsToMaxRadius(bounds.value, MAX_NEARBY_RADIUS_KM);
    return {
      visibleBounds: bounds.value,
      queryBounds,
      center: viewportCenter.value,
      isClamped,
    };
  });

  function setCenter(next: LatLng): void {
    if (
      center.value &&
      Math.abs(center.value.lat - next.lat) <= COORDINATE_EPSILON &&
      Math.abs(center.value.lon - next.lon) <= COORDINATE_EPSILON
    ) {
      return;
    }
    center.value = next;
  }

  function setBounds(next: MapBounds): void {
    if (
      bounds.value &&
      Math.abs(bounds.value.north - next.north) <= COORDINATE_EPSILON &&
      Math.abs(bounds.value.south - next.south) <= COORDINATE_EPSILON &&
      Math.abs(bounds.value.east - next.east) <= COORDINATE_EPSILON &&
      Math.abs(bounds.value.west - next.west) <= COORDINATE_EPSILON
    ) {
      return;
    }
    bounds.value = next;
  }

  function setUserLocation(next: LatLng): void {
    userLocation.value = next;
    setCenter(next);
  }

  async function requestUserLocation(): Promise<LatLng> {
    return await new Promise<LatLng>((resolve, reject) => {
      if (!navigator.geolocation) {
        reject(new Error("Geolocation is unavailable"));
        return;
      }
      if (!window.isSecureContext) {
        reject(new Error("Location access requires HTTPS or localhost. Use Location Settings to set your location."));
        return;
      }

      navigator.geolocation.getCurrentPosition(
        (position) => {
          const next = {
            lat: position.coords.latitude,
            lon: position.coords.longitude,
          };
          setUserLocation(next);
          resolve(next);
        },
        (error) => {
          if (error.code === error.PERMISSION_DENIED) {
            reject(new Error("Location permission was denied. Use Location Settings to set your location."));
            return;
          }
          reject(new Error("Unable to access your location"));
        },
        {
          enableHighAccuracy: true,
          timeout: 10000,
        },
      );
    });
  }

  return {
    bounds,
    center,
    liveQuery,
    query,
    userLocation,
    viewportCenter,
    zoom,
    requestUserLocation,
    setBounds,
    setCenter,
    setUserLocation,
  };
});
