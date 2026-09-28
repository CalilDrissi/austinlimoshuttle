"use client";

/**
 * Google Places address autocomplete for the From/To fields.
 *
 * Uses the new Places API (`AutocompleteSuggestion.fetchAutocompleteSuggestions`)
 * — the classic `AutocompleteService` is retired for keys created in 2025+, so
 * this needs "Places API (New)" enabled on the key. Predictions are biased to
 * the Austin service area but not restricted, and free text is always allowed:
 * the backend geocodes whatever string ends up in the field.
 *
 * The Google types aren't a project dependency, so the `google` global is typed
 * loosely here and the loose surface is kept inside this module.
 */

/* eslint-disable @typescript-eslint/no-explicit-any */

const SCRIPT_ID = "gmaps-js";
const AUSTIN = { lat: 30.2672, lng: -97.7431 };
const BIAS_RADIUS_M = 80_000; // ~50 miles around Austin

let loader: Promise<any> | null = null;

/** Load the Maps JS API (with Places) once; resolves to the `google` global. */
export function loadGoogleMaps(): Promise<any> {
  if (typeof window === "undefined") return Promise.reject(new Error("not in browser"));
  const w = window as any;
  if (w.google?.maps?.importLibrary) return Promise.resolve(w.google);
  if (loader) return loader;

  const key = process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY;
  loader = new Promise((resolve, reject) => {
    if (!key) {
      reject(new Error("NEXT_PUBLIC_GOOGLE_MAPS_API_KEY is not set"));
      return;
    }
    const ready = async () => {
      try {
        await w.google.maps.importLibrary("places");
        resolve(w.google);
      } catch (e) {
        reject(e);
      }
    };
    const existing = document.getElementById(SCRIPT_ID) as HTMLScriptElement | null;
    if (existing) {
      existing.addEventListener("load", ready);
      existing.addEventListener("error", () => reject(new Error("Google Maps failed to load")));
      return;
    }
    const s = document.createElement("script");
    s.id = SCRIPT_ID;
    s.async = true;
    s.src =
      `https://maps.googleapis.com/maps/api/js?key=${encodeURIComponent(key)}` +
      `&libraries=places&loading=async&v=weekly`;
    s.onload = ready;
    s.onerror = () => reject(new Error("Google Maps failed to load"));
    document.head.appendChild(s);
  });
  return loader;
}

export interface PlaceSuggestion {
  id: string;
  primary: string; // e.g. "Austin-Bergstrom International Airport"
  secondary: string; // e.g. "Austin, TX, USA"
  full: string; // the string written into the field / sent to the backend
  isAirport: boolean;
}

/** A per-editing-session token (groups keystrokes into one billable session). */
export async function newSessionToken(): Promise<any> {
  const google = await loadGoogleMaps();
  return new google.maps.places.AutocompleteSessionToken();
}

/** Fetch autocomplete predictions for `input`, biased to the Austin area. */
export async function fetchPlaceSuggestions(
  input: string,
  sessionToken: any,
): Promise<PlaceSuggestion[]> {
  const google = await loadGoogleMaps();
  const { AutocompleteSuggestion } = google.maps.places;
  const { suggestions } = await AutocompleteSuggestion.fetchAutocompleteSuggestions({
    input,
    sessionToken,
    includedRegionCodes: ["us"],
    locationBias: { center: AUSTIN, radius: BIAS_RADIUS_M },
  });
  return (suggestions ?? [])
    .map((s: any) => s.placePrediction)
    .filter(Boolean)
    .map((p: any): PlaceSuggestion => ({
      id: p.placeId ?? p.text?.text ?? "",
      primary: p.mainText?.text ?? p.text?.text ?? "",
      secondary: p.secondaryText?.text ?? "",
      full: p.text?.text ?? p.mainText?.text ?? "",
      isAirport: Array.isArray(p.types) && p.types.includes("airport"),
    }));
}
