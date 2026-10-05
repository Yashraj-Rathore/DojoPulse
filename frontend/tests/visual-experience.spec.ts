import { test, expect } from "@playwright/test";
import { mockWorkspace } from "./workspace-fixtures";

const overview = { runs: [], events: [], assignments: [], plans: [], evaluations: [], practice: [], drills: [] };

test("visitor artwork, responsive layout and workspace entry preserve honest access states", async ({ page }) => {
  await page.route("**/api/session", route => route.fulfill({ json: { authenticated: false, csrf: "fixture" } }));
  await page.route("**/api/account/policy", route => route.fulfill({ json: { version: "local/1", registration_enabled: false, policies: {} } }));
  await page.goto("/");
  await expect(page).toHaveTitle(/DojoPulse/);
  await expect(page.getByRole("heading", { name: "Open your local workspace" })).toBeVisible();
  await expect(page.locator(".hero-art")).toHaveJSProperty("complete", true);
  expect(await page.locator(".hero-art").evaluate(node => (node as HTMLImageElement).naturalWidth)).toBeGreaterThan(0);
  await expect(page.getByText("Gameplay validation is pending.", { exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "Create account", exact: true })).toBeDisabled();
  for (const width of [1440, 768, 390, 320]) {
    await page.setViewportSize({ width, height: 900 });
    await page.evaluate(() => document.fonts.ready);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    if (width === 1440 || width === 390) {
      await page.screenshot({ path: `test-results/dojo-visitor-${width}.png`, fullPage: true });
    }
  }
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.getByRole("link", { name: "Open your workspace", exact: true }).click();
  await expect(page).toHaveURL(/#sign-in$/);
  await expect(page.getByRole("button", { name: "Sign in", exact: true })).toBeInViewport();
  await page.getByLabel("Username", { exact: true }).focus();
  await expect(page.getByLabel("Username", { exact: true })).toBeFocused();
  await page.getByRole("link", { name: "The training loop", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Less guesswork. A clearer next session." })).toBeInViewport();
});

test("player entry links reach visible training tools and keep keyboard access", async ({ page }) => {
  await mockWorkspace(page);
  await page.route("**/api/session", route => route.fulfill({ json: { authenticated: true, csrf: "fixture", local_uploads: false } }));
  await page.route("**/api/overview", route => route.fulfill({ json: overview }));
  await page.route("**/api/match-providers", route => route.fulfill({ json: { providers: [] } }));
  await page.route("**/api/player-identities", route => route.fulfill({ json: { identities: [] } }));
  await page.route("**/api/matches?*", route => route.fulfill({ json: { matches: [], total: 0, next_offset: null, syncs: [] } }));
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Your training path" })).toBeVisible();
  await page.keyboard.press("Tab");
  await expect(page.getByRole("link", { name: "Skip to workspace" })).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(page.locator("#workspace-content")).toBeFocused();
  await page.getByRole("link", { name: "The training loop", exact: true }).click();
  await expect(page.locator("#training-path")).toBeInViewport();
  await page.getByRole("link", { name: "Review your matches", exact: true }).click();
  await expect(page.locator("#matches")).toBeInViewport();
  await page.getByRole("link", { name: "Capture guide", exact: true }).click();
  await expect(page.locator("#capture")).toBeInViewport();
  await expect(page.getByRole("button", { name: "Queue capture" })).toBeDisabled();
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.evaluate(() => document.fonts.ready);
  await page.locator("#training-path").screenshot({ path: "test-results/dojo-training-desktop.png" });
  await page.setViewportSize({ width: 390, height: 844 });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.locator("#training-path").screenshot({ path: "test-results/dojo-training-mobile.png" });
});
