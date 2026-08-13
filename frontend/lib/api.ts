/**
 * Typed client for the Django API.
 *
 * Types in `api-types.ts` are generated from `docs/openapi.yaml` — regenerate
 * with `npm run api:types` after any backend endpoint change rather than
 * hand-editing them.
 *
 * Two rules this client exists to enforce, both inherited from the backend:
 *
 *   1. Never send a price or a distance. Quotes take two addresses and return a
 *      signed token; the server measures and prices. There is deliberately no
 *      helper here that would let a caller supply either.
 *   2. Never treat a browser-side card confirmation as payment. Stripe's
 *      webhook confirms a booking — poll `getBooking` and show a pending state.
 */

import type { paths } from "./api-types";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly detail: string,
    readonly fields?: Record<string, string[]>,
  ) {
    super(detail);
    this.name = "ApiError";
  }
}

type Json = Record<string, unknown>;

/** Read a cookie in the browser. Returns null during server rendering. */
function readCookie(name: string): string | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie.match(new RegExp(`(^| )${name}=([^;]+)`));
  return match ? decodeURIComponent(match[2]) : null;
}

async function request<T>(
  path: string,
  init: RequestInit & { json?: Json } = {},
): Promise<T> {
  const { json, ...rest } = init;
  const headers = new Headers(rest.headers);

  if (json !== undefined) {
    headers.set("Content-Type", "application/json");
  }

  // Django requires the CSRF token on session-authenticated writes.
  const method = (rest.method ?? "GET").toUpperCase();
  if (!["GET", "HEAD", "OPTIONS"].includes(method)) {
    const token = readCookie("csrftoken");
    if (token) headers.set("X-CSRFToken", token);
  }

  const response = await fetch(`${BASE_URL}${path}`, {
    ...rest,
    headers,
    // Session cookies must travel with every request, including cross-origin
    // during local development.
    credentials: "include",
    body: json !== undefined ? JSON.stringify(json) : rest.body,
  });

  if (response.status === 204) return undefined as T;

  const body = await response.json().catch(() => ({}) as Json);

  if (!response.ok) {
    const detail =
      (body as { detail?: string }).detail ??
      Object.values(body as Record<string, string[]>)
        .flat()
        .join(" ") ??
      `Request failed (${response.status})`;
    throw new ApiError(response.status, detail, body as Record<string, string[]>);
  }

  return body as T;
}

/* -------------------------------------------------------------------------- */
/* Content                                                                     */
/* -------------------------------------------------------------------------- */

export type Page =
  paths["/api/pages/{slug}/"]["get"]["responses"][200]["content"]["application/json"];
export type Vehicle =
  paths["/api/vehicles/"]["get"]["responses"][200]["content"]["application/json"][number];

export const getPage = (slug: string, init?: RequestInit) =>
  request<Page>(`/api/pages/${slug}/`, init);

export const listPages = (init?: RequestInit) =>
  request<Page[]>("/api/pages/", init);

export const listVehicles = (init?: RequestInit) =>
  request<Vehicle[]>("/api/vehicles/", init);

export const getAvailability = (init?: RequestInit) =>
  request<{
    blackout_dates: { date: string; name: string; percentage: string }[];
    time_surcharges: {
      name: string;
      start_time: string;
      end_time: string;
      percentage: string;
      crosses_midnight: boolean;
    }[];
  }>("/api/availability/", init);

/* -------------------------------------------------------------------------- */
/* Quoting                                                                     */
/* -------------------------------------------------------------------------- */

export interface QuoteRequest {
  pickup_address: string;
  /** Omit for hourly hire. */
  dropoff_address?: string;
  /** ISO 8601 with offset. */
  pickup_at: string;
  /** Hourly hire only. Mutually exclusive with dropoff_address. */
  hours?: string;
  meet_and_greet?: boolean;
}

export interface QuoteLine {
  kind: string;
  label: string;
  /** Decimal string. Money is never a float. */
  amount: string;
}

export interface QuoteResult {
  vehicle_id: number;
  vehicle_name: string;
  subtotal: string;
  surcharge_total: string;
  tax: string;
  total: string;
  currency: string;
  lines: QuoteLine[];
  /** Signed and short-lived. Present this when creating a booking. */
  quote_token: string;
}

export interface QuoteResponse {
  journey: {
    distance_miles: string;
    duration_minutes: number;
    pickup_address: string;
    dropoff_address: string;
  } | null;
  quotes: QuoteResult[];
}

/**
 * Price a journey across every bookable vehicle.
 *
 * Note the absence of a distance field: the server measures the route from the
 * two addresses. A client-supplied distance would be a client-supplied fare.
 */
export const createQuote = (body: QuoteRequest) =>
  request<QuoteResponse>("/api/quotes/", { method: "POST", json: body as unknown as Json });

/* -------------------------------------------------------------------------- */
/* Bookings                                                                    */
/* -------------------------------------------------------------------------- */

export interface BookingRequest {
  quote_token: string;
  passenger_count?: number;
  luggage_count?: number;
  flight_number?: string;
  pickup_sign?: string;
  notes?: string;
  /** Guest checkout. Ignored when signed in. */
  guest_email?: string;
  guest_name?: string;
}

export interface Booking {
  reference: string;
  status: "pending" | "confirmed" | "completed" | "cancelled";
  status_display: string;
  trip_type: string;
  pickup_address: string;
  dropoff_address: string;
  pickup_at: string;
  distance_miles: string | null;
  duration_minutes: number | null;
  hours: string | null;
  passenger_count: number;
  luggage_count: number;
  flight_number: string;
  pickup_sign: string;
  meet_and_greet: boolean;
  notes: string;
  vehicle_name: string;
  subtotal: string;
  surcharge_total: string;
  tax: string;
  total: string;
  currency: string;
  price_lines: QuoteLine[];
  created_at: string;
}

export const createBooking = (body: BookingRequest) =>
  request<Booking>("/api/bookings/", { method: "POST", json: body as unknown as Json });

export const listMyBookings = (init?: RequestInit) =>
  request<Booking[]>("/api/account/bookings/", init);

export const getBooking = (reference: string, init?: RequestInit) =>
  request<Booking>(`/api/account/bookings/${reference}/`, init);

export const cancelBooking = (reference: string) =>
  request<Booking>(`/api/account/bookings/${reference}/`, {
    method: "PATCH",
    json: { action: "cancel" },
  });

/* -------------------------------------------------------------------------- */
/* Payments                                                                    */
/* -------------------------------------------------------------------------- */

export const getPaymentConfig = () =>
  request<{ enabled: boolean; publishable_key: string; mode: string | null }>(
    "/api/payments/config/",
  );

export const createPaymentIntent = (reference: string) =>
  request<{
    client_secret: string;
    publishable_key: string;
    amount: string;
    currency: string;
    reference: string;
  }>("/api/payments/intent/", { method: "POST", json: { reference } });

/* -------------------------------------------------------------------------- */
/* Auth                                                                        */
/* -------------------------------------------------------------------------- */

export interface User {
  email: string;
  first_name: string;
  last_name: string;
  phone?: string;
}

export const signIn = (email: string, password: string) =>
  request<User>("/api/auth/login/", { method: "POST", json: { email, password } });

export const signOut = () => request<void>("/api/auth/logout/", { method: "POST" });

export const register = (body: {
  email: string;
  password: string;
  first_name?: string;
  last_name?: string;
  phone?: string;
}) => request<User>("/api/auth/register/", { method: "POST", json: body });

export const me = (init?: RequestInit) => request<User>("/api/auth/me/", init);

export const requestPasswordReset = (email: string) =>
  request<{ detail: string }>("/api/auth/password-reset/", {
    method: "POST",
    json: { email },
  });

/* -------------------------------------------------------------------------- */
/* Enquiries                                                                   */
/* -------------------------------------------------------------------------- */

export const submitEnquiry = (body: {
  name: string;
  email: string;
  phone?: string;
  nature?: "general" | "service" | "corporate";
  subject?: string;
  message: string;
  company_name?: string;
}) => request<{ detail: string }>("/api/enquiries/", { method: "POST", json: body });
