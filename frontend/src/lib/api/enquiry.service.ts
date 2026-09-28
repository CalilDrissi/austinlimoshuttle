import { apiPost } from "./client";
import type { EnquiryRequest } from "@/types/api";

/** Contact-form submission → back-office inbox. Rate-limited server-side. */
export const enquiryService = {
  submit: (body: EnquiryRequest) => apiPost<{ detail: string }>("/enquiries/", body),
};
