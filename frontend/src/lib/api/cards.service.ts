import { apiGet, apiDelete } from "./client";

/** A card kept on file. Display bits only — never anything to charge with. */
export interface SavedCard {
  id: number;
  brand: string;
  last4: string;
  exp_month: number | null;
  exp_year: number | null;
  is_default: boolean;
  label: string;
  expiry: string;
}

export const cardsService = {
  list: () => apiGet<SavedCard[]>("/account/cards/"),
  remove: (id: number) => apiDelete<void>(`/account/cards/${id}/`),
};
