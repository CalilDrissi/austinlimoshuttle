/**
 * Vehicle imagery.
 *
 * The API doesn't serve photos (the `Vehicle` serializer omits the field), so
 * each vehicle class maps to a bundled template asset by slug. Keyed on the real
 * slugs from /api/vehicles/; unknown slugs fall back to a generic car image.
 */
const BY_SLUG: Record<string, string> = {
  "business-class": "/assets/imgs/page/homepage1/e-class.png",
  "business-suv": "/assets/imgs/page/homepage1/suv.png",
  "chrysler-300-limousine": "/assets/imgs/page/homepage1/v-class.png",
  "mercedes-sprinter": "/assets/imgs/page/homepage1/suv-class.png",
};

const FALLBACK = "/assets/imgs/page/fleet/vehicle.png";

export function vehicleImage(slug: string): string {
  return BY_SLUG[slug] ?? FALLBACK;
}
