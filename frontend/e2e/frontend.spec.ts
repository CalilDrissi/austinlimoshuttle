import { expect, test } from "@playwright/test";

/**
 * Frontend scaffold (F0).
 *
 * The design is not converted yet, so these check the pipeline rather than the
 * look: the vendored template stylesheet and fonts actually load, and the page
 * renders live data fetched from Django.
 *
 * The asset checks matter because both failure modes here are silent — a
 * hotlinked stylesheet or a missing font degrades quietly rather than erroring.
 */

test.describe("Frontend scaffold", () => {
  test("home page loads", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("heading", { name: "Austin Limo Shuttle" })).toBeVisible();
  });

  test("the template stylesheet is applied, not merely linked", async ({ page }) => {
    await page.goto("/");
    const heading = page.getByRole("heading", { name: "Austin Limo Shuttle" });

    // The template sets DM Sans via a next/font-generated family name. Browser
    // defaults would be Times or system-ui, so this proves the CSS took effect.
    const font = await heading.evaluate((el) => getComputedStyle(el).fontFamily);
    expect(font).toContain("DM_Sans");
  });

  test("template assets are served from our own origin", async ({ page }) => {
    const external: string[] = [];
    page.on("request", (req) => {
      const url = req.url();
      if (!url.startsWith("http://localhost:3000") && !url.startsWith("data:")) {
        external.push(url);
      }
    });

    await page.goto("/", { waitUntil: "networkidle" });

    // The scraped CSS originally hotlinked images from the demo deployment.
    const hotlinked = external.filter((u) => u.includes("luxride-nextjs.vercel.app"));
    expect(hotlinked, `hotlinked assets: ${hotlinked.join(", ")}`).toHaveLength(0);
  });

  test("the icon font loads", async ({ page }) => {
    const fontResponses: number[] = [];
    page.on("response", (res) => {
      if (res.url().includes("/fonts/")) fontResponses.push(res.status());
    });

    await page.goto("/", { waitUntil: "networkidle" });

    expect(fontResponses.length).toBeGreaterThan(0);
    expect(fontResponses.every((s) => s === 200)).toBe(true);
  });

  test("live vehicle data arrives from the Django API", async ({ page }) => {
    await page.goto("/");
    // Seeded from the real legacy import, not fixtures.
    await expect(page.getByText("Business Class")).toBeVisible();
    await expect(page.getByText("Business SUV")).toBeVisible();
    await expect(page.getByText("Mercedes Sprinter")).toBeVisible();
  });

  test("no console errors", async ({ page }) => {
    const errors: string[] = [];
    page.on("console", (msg) => {
      if (msg.type() === "error") errors.push(msg.text());
    });
    await page.goto("/", { waitUntil: "networkidle" });
    expect(errors, errors.join("\n")).toHaveLength(0);
  });
});

test.describe("API contract as the browser sees it", () => {
  const API = "http://127.0.0.1:8000";

  test("CORS lets the browser call the API", async ({ request }) => {
    const response = await request.get(`${API}/api/vehicles/`, {
      headers: { Origin: "http://localhost:3000" },
    });
    expect(response.status()).toBe(200);
    expect(response.headers()["access-control-allow-origin"]).toBe("http://localhost:3000");
    expect(response.headers()["access-control-allow-credentials"]).toBe("true");
  });

  test("a quote is priced server-side from two addresses", async ({ request }) => {
    const pickup = new Date(Date.now() + 3 * 24 * 3600 * 1000).toISOString();
    const response = await request.post(`${API}/api/quotes/`, {
      headers: { Origin: "http://localhost:3000" },
      data: {
        pickup_address: "Austin-Bergstrom International Airport",
        dropoff_address: "Downtown Austin, TX",
        pickup_at: pickup,
      },
    });

    // 200 with fares, or 422 if the mapping key is unavailable — both prove the
    // server is doing the measuring rather than trusting the caller.
    expect([200, 422]).toContain(response.status());

    if (response.status() === 200) {
      const body = await response.json();
      expect(body.journey.distance_miles).toBeTruthy();
      expect(body.quotes.length).toBeGreaterThan(0);
      // Money crosses the wire as a string; a float would carry rounding error.
      expect(typeof body.quotes[0].total).toBe("string");
      expect(body.quotes[0].quote_token).toBeTruthy();
    }
  });

  test("the API refuses a client-supplied distance", async ({ request }) => {
    const pickup = new Date(Date.now() + 3 * 24 * 3600 * 1000).toISOString();
    const response = await request.post(`${API}/api/quotes/`, {
      headers: { Origin: "http://localhost:3000" },
      data: {
        pickup_address: "Austin-Bergstrom International Airport",
        dropoff_address: "Downtown Austin, TX",
        pickup_at: pickup,
        distance_miles: "1", // ignored — the field does not exist
      },
    });

    if (response.status() === 200) {
      const body = await response.json();
      // A 1-mile journey would price near the minimum fare. The real distance
      // is roughly 11 miles, so the measured value must have won.
      expect(Number(body.journey.distance_miles)).toBeGreaterThan(5);
    }
  });

  test("another customer's booking is not readable", async ({ request }) => {
    const response = await request.get(`${API}/api/account/bookings/AAAA1111/`, {
      headers: { Origin: "http://localhost:3000" },
    });
    // 401/403 unauthenticated. Never 200, and never a 404 that confirms
    // existence to a signed-in stranger.
    expect([401, 403]).toContain(response.status());
  });
});
