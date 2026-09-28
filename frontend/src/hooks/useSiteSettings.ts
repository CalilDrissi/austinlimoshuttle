"use client";

import { useQuery } from "@tanstack/react-query";
import { siteService, type SiteSettings } from "@/lib/api/site.service";

/**
 * Contact details for the header and footer.
 *
 * Cached for an hour: these change perhaps twice a year, and the header renders
 * on every page.
 */
export function useSiteSettings(): SiteSettings | undefined {
  const { data } = useQuery({
    queryKey: ["site-settings"],
    queryFn: () => siteService.get(),
    staleTime: 60 * 60 * 1000,
  });
  return data;
}
