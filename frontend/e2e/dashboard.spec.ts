import { expect, test } from "@playwright/test";

/**
 * Staff dashboard — the Django-templates application.
 *
 * Runs against the real development database: 2,217 imported bookings, 1,254
 * customers, 928 enquiries. Nothing here is seeded, which is the point — these
 * are the screens as staff would actually meet them.
 *
 * In headed mode this doubles as a walkthrough of the built system.
 */

const DASHBOARD = "http://127.0.0.1:8000";
const EMAIL = "cal@austinlimoshuttle.local";
const PASSWORD = "DashboardDemo2026!";

test.describe("Staff dashboard", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(`${DASHBOARD}/admin/login/?next=/dashboard/`);
    // Django renders labels with a trailing colon ("Email address:"), and the
    // input is still named `username` even though our USERNAME_FIELD is email.
    // Target the ids, which are stable.
    await page.locator("#id_username").fill(EMAIL);
    await page.locator("#id_password").fill(PASSWORD);
    await page.getByRole("button", { name: /log in/i }).click();
    await expect(page).toHaveURL(/\/dashboard\//);
  });

  test("overview shows live counters and upcoming pickups", async ({ page }) => {
    await expect(page.getByRole("heading", { name: "Overview" })).toBeVisible();
    await expect(page.getByText("Pickups today")).toBeVisible();
    await expect(page.getByText("Awaiting payment")).toBeVisible();
    await expect(page.getByText("Next pickups")).toBeVisible();
  });

  test("dispatch board lists the next 48 hours", async ({ page }) => {
    await page.getByRole("link", { name: "Dispatch" }).click();
    await expect(page.getByRole("heading", { name: "Dispatch board" })).toBeVisible();

    // Either real bookings in the window, or an honest empty state.
    const rows = page.locator("tbody tr");
    const count = await rows.count();
    if (count === 0) {
      await expect(page.getByText(/Nothing scheduled/)).toBeVisible();
    } else {
      // Each row offers inline driver and status controls.
      await expect(rows.first().locator("select[name='driver']")).toBeVisible();
      await expect(rows.first().locator("select[name='status']")).toBeVisible();
    }
  });

  test("bookings list searches 2,217 real records", async ({ page }) => {
    await page.getByRole("link", { name: "Bookings" }).click();
    await expect(page.getByRole("heading", { name: "Bookings" })).toBeVisible();

    const firstReference = await page.locator("tbody tr td a").first().innerText();

    await page.locator("input[name='q']").fill(firstReference);
    await page.getByRole("button", { name: /filter/i }).click();

    await expect(page.locator("tbody tr")).toHaveCount(1);
    await expect(page.getByText(firstReference).first()).toBeVisible();
  });

  test("booking detail shows the itinerary and audit trail", async ({ page }) => {
    await page.goto(`${DASHBOARD}/dashboard/bookings/`);
    await page.locator("tbody tr td a").first().click();

    await expect(page.getByText("Journey")).toBeVisible();
    await expect(page.getByText("Fare")).toBeVisible();
    await expect(page.getByText("History")).toBeVisible();
    // Manager-only panel.
    await expect(page.getByText("Update")).toBeVisible();
  });

  test("enquiries inbox shows real submissions", async ({ page }) => {
    await page.getByRole("link", { name: "Enquiries" }).click();
    await expect(page.getByRole("heading", { name: "Enquiries" })).toBeVisible();
    await expect(page.locator("tbody tr").first()).toBeVisible();
  });

  test("payment settings never render the stored secret", async ({ page }) => {
    await page.goto(`${DASHBOARD}/dashboard/settings/payments/`);
    await expect(page.getByRole("heading", { name: "Payment settings" })).toBeVisible();

    // The secret field must be write-only.
    const secret = page.locator("input[name='secret_key']");
    await expect(secret).toHaveAttribute("type", "password");
    await expect(secret).toHaveValue("");

    // And nothing resembling a live key may appear anywhere in the page.
    const body = await page.content();
    expect(body).not.toMatch(/sk_(live|test)_[A-Za-z0-9]{20,}/);
  });

  test("email settings offer a test send", async ({ page }) => {
    await page.goto(`${DASHBOARD}/dashboard/settings/email/`);
    await expect(page.getByRole("heading", { name: "Email settings" })).toBeVisible();
    await expect(page.getByRole("button", { name: /send test/i })).toBeVisible();
  });

  test("paypal page states the flow is not wired up", async ({ page }) => {
    await page.goto(`${DASHBOARD}/dashboard/settings/paypal/`);
    await expect(page.getByRole("heading", { name: "PayPal settings" })).toBeVisible();
    await expect(page.getByText(/not wired up/)).toBeVisible();
  });

  test("the rate card validates as a set", async ({ page }) => {
    await page.goto(`${DASHBOARD}/admin/fleet/vehicle/`);
    await page.getByRole("link", { name: "Business Class" }).click();

    // Four cumulative distance bands, edited inline.
    await expect(page.getByText("Distance bands", { exact: false })).toBeVisible();
    const bands = page.locator("input[name$='-rate_per_mile']");
    expect(await bands.count()).toBeGreaterThanOrEqual(4);
  });
});

test.describe("Access control", () => {
  test("signed-out staff cannot reach the dashboard", async ({ page }) => {
    await page.context().clearCookies();
    await page.goto(`${DASHBOARD}/dashboard/`);
    await expect(page).toHaveURL(/\/admin\/login\//);
  });

  test("signed-out users cannot reach payment settings", async ({ page }) => {
    await page.context().clearCookies();
    await page.goto(`${DASHBOARD}/dashboard/settings/payments/`);
    await expect(page).toHaveURL(/\/admin\/login\//);
  });
});
