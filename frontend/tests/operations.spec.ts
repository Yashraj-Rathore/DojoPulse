import { expect, test } from "@playwright/test";

const snapshot = {
  generated_at: "2026-10-02T15:00:00Z", days: 1, scope: "Local engineering telemetry; no deployed qualification.",
  processing_paused: false, counts: { queued: 2, stale_slots: 1, retry_attempts: 1 }, alerts: ["STALE_SLOTS"],
  oldest_queue_seconds: 150, budget: { media_held: 600, processing_held: 1260, processing_used: 420 },
  objectives: { queue_p95_seconds: { value: null, samples: 1, target: 120, state: "INSUFFICIENT_DATA", approval: "PROPOSED_NOT_RELEASE_APPROVED" } },
  costs: ["SYNTHETIC", "OBSERVED"].map(scope => ({ scope, period_start: "2026-10-02", period_end: "2026-10-02", total_usd: null, missing_components: ["INFRASTRUCTURE", "REVIEW"], per_unit_usd: { capture: null }, denominators: { capture: 1 } })),
  missing_elapsed_attempts: 1, coverage_note: "Unavailable values remain null.",
};

test("operator dashboard shows pending work, proposed targets and unknown cost on mobile", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.route("**/api/session", route => route.fulfill({ json: { authenticated: true, operator: true, csrf: "test" } }));
  await page.route("**/api/operations?*", route => route.fulfill({ json: snapshot }));
  await page.goto("/operations");
  await expect(page.getByRole("heading", { name: "Needs attention" })).toBeVisible();
  await expect(page.getByRole("listitem")).toHaveText("stale slots");
  await expect(page.getByRole("cell", { name: "insufficient data" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "observed cost" })).toBeVisible();
  await expect(page.getByText("Unknown", { exact: true })).toHaveCount(5);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.screenshot({ path: "test-results/m17-operations-mobile.png", fullPage: true });
});

test("operator time retry keeps its request ID and sends CSRF", async ({ page }) => {
  await page.route("**/api/session", route => route.fulfill({ json: { authenticated: true, operator: true, csrf: "test-csrf" } }));
  await page.route("**/api/operations?*", route => route.fulfill({ json: snapshot }));
  const bodies: Record<string, unknown>[] = [];
  await page.route("**/api/operations/work", route => {
    expect(route.request().headers()["x-csrftoken"]).toBe("test-csrf");
    bodies.push(route.request().postDataJSON());
    return route.fulfill({ status: bodies.length === 1 ? 503 : 201, json: { created: true } });
  });
  await page.goto("/operations");
  await page.getByLabel("Measured seconds").fill("120");
  await page.getByRole("button", { name: "Record time", exact: true }).click();
  await expect(page.getByRole("main").getByRole("alert")).toContainText("not recorded");
  await page.getByRole("button", { name: "Record time", exact: true }).click();
  await expect(page.getByRole("status")).toContainText("Measurement recorded");
  expect(bodies).toHaveLength(2);
  expect(bodies[0]).toEqual(bodies[1]);
  expect(bodies[0]).toMatchObject({ seconds: 120, scope: "SYNTHETIC", kind: "REVIEW" });
});

test("nonoperators cannot load the dashboard and API denial remains visible", async ({ page }) => {
  let requests = 0;
  await page.route("**/api/session", route => route.fulfill({ json: { authenticated: true, operator: false } }));
  await page.route("**/api/operations?*", route => { requests++; return route.fulfill({ status: 403, json: { detail: "Operator access required" } }); });
  await page.goto("/operations");
  await expect(page.getByRole("main").getByRole("alert")).toContainText("Operator access required");
  expect(requests).toBe(0);
  await expect(page.getByRole("heading", { name: "Global daily budget" })).toHaveCount(0);
  await page.route("**/api/session", route => route.fulfill({ json: { authenticated: true, operator: true, csrf: "test" } }));
  await page.reload();
  await expect(page.getByRole("main").getByRole("alert")).toHaveText("Operator access required");
  expect(requests).toBe(1);
});
