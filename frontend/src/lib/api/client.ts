import { API_BASE_URL } from "./config";
import type { ApiError } from "@/types/api";

export class ApiRequestError extends Error {
  constructor(
    public readonly status: number,
    public readonly error: ApiError,
  ) {
    super(ApiRequestError.messageFrom(error));
  }

  /** Flatten DRF's { detail } or { field: [msg] } into one human string. */
  static messageFrom(error: ApiError): string {
    if (!error) return "Request failed";
    if (typeof error.detail === "string") return error.detail;
    const parts: string[] = [];
    for (const v of Object.values(error)) {
      if (Array.isArray(v)) parts.push(v.join(" "));
      else if (typeof v === "string") parts.push(v);
    }
    return parts.join(" ") || "Request failed";
  }

  /** First message for a specific field, if the backend returned one. */
  fieldError(field: string): string | undefined {
    const v = this.error?.[field];
    if (Array.isArray(v)) return String(v[0]);
    if (typeof v === "string") return v;
    return undefined;
  }
}

const SAFE = new Set(["GET", "HEAD", "OPTIONS", "TRACE"]);

function getCookie(name: string): string | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`));
  return match ? decodeURIComponent(match[1]) : null;
}

/**
 * Django's SessionAuthentication enforces CSRF on authenticated unsafe requests.
 * The token rides in a cookie and must be echoed in `X-CSRFToken`. The storefront
 * uses its own path-scoped cookie (`mm_store_csrftoken`) so a customer login here
 * can't rotate the token the dashboard/driver forms rely on — mirrors the scoped
 * session cookie. See backend config/session.py ScopedCsrfMiddleware.
 * Anonymous requests (guest checkout, login, register) don't need it, so a
 * missing cookie is fine — we just send it when present.
 */
const CSRF_COOKIE = "mm_store_csrftoken";
let csrfPrimed = false;
export async function ensureCsrf(): Promise<void> {
  if (csrfPrimed || getCookie(CSRF_COOKIE)) {
    csrfPrimed = true;
    return;
  }
  try {
    await fetch(`${API_BASE_URL}/auth/csrf/`, { credentials: "include" });
  } catch {
    /* offline / not critical — writes will surface their own error */
  }
  csrfPrimed = true;
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const method = (init.method ?? "GET").toUpperCase();

  if (!SAFE.has(method)) await ensureCsrf();
  const csrf = getCookie(CSRF_COOKIE);

  const res = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    method,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...(csrf && !SAFE.has(method) ? { "X-CSRFToken": csrf } : {}),
      ...init.headers,
    },
  });

  if (!res.ok) {
    const error: ApiError = await res
      .json()
      .catch(() => ({ detail: res.statusText }));
    throw new ApiRequestError(res.status, error);
  }

  if (res.status === 204) return undefined as T;
  return res.json();
}

export const apiGet = <T>(path: string) => request<T>(path);
export const apiPost = <T>(path: string, body?: unknown) =>
  request<T>(path, { method: "POST", body: body === undefined ? undefined : JSON.stringify(body) });
export const apiPatch = <T>(path: string, body?: unknown) =>
  request<T>(path, { method: "PATCH", body: body === undefined ? undefined : JSON.stringify(body) });
export const apiPut = <T>(path: string, body?: unknown) =>
  request<T>(path, { method: "PUT", body: JSON.stringify(body) });
export const apiDelete = <T>(path: string) => request<T>(path, { method: "DELETE" });
