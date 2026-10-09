/**
 * Fallback image for a vehicle that has no uploaded photo.
 *
 * Real photos come from the back office: /api/vehicles/ returns each vehicle's
 * `photo` as an absolute URL (VehicleSerializer.get_photo). The storefront shows
 * that photo; this neutral placeholder is used ONLY until one is uploaded — never
 * a mismatched stock car keyed off the slug (that was the old behaviour and made
 * the storefront misrepresent the real fleet).
 */
export const VEHICLE_PLACEHOLDER = "/assets/imgs/page/fleet/vehicle.png";
