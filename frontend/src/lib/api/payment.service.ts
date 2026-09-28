import { apiGet, apiPost } from "./client";
import type { PaymentConfig, PaymentIntentResponse, BookingStatus } from "@/types/api";

/**
 * Payment setup. Card data never reaches Django — the browser confirms with
 * Stripe Elements using the client secret, and the webhook is what actually
 * confirms the booking. Cash / pay-on-arrival confirms the booking directly.
 */
export const paymentService = {
  config: () => apiGet<PaymentConfig>("/payments/config/"),
  createIntent: (reference: string) =>
    apiPost<PaymentIntentResponse>("/payments/intent/", { reference }),
  /** Confirm the booking as cash (pay the driver) — no card needed. */
  payCash: (reference: string) =>
    apiPost<BookingStatus>(`/bookings/${reference}/pay-cash/`),
};
