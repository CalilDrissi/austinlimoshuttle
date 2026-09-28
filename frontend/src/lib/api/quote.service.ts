import { apiPost } from "./client";
import type { QuoteRequest, QuoteResponse } from "@/types/api";

/**
 * Price a journey across every vehicle. The server measures the distance from
 * the two addresses and returns a signed `quote_token` per vehicle — the only
 * way to create a booking. No price or distance is ever sent by the client.
 */
export const quoteService = {
  create: (body: QuoteRequest) => apiPost<QuoteResponse>("/quotes/", body),
};
