import { apiGet } from "./client";
import type { Vehicle, Page, Availability } from "@/types/api";

/** Read-only public catalog & CMS content. */
export const catalogService = {
  listVehicles: () => apiGet<Vehicle[]>("/vehicles/"),
  listPages: () => apiGet<Page[]>("/pages/"),
  getPage: (slug: string) => apiGet<Page>(`/pages/${slug}/`),
  availability: () => apiGet<Availability>("/availability/"),
};
