import { test, expect } from "@playwright/test";
import { preferences } from "./workspace-fixtures";

const policy = { version: "local-research-2026-09/1", registration_enabled: true, policies: {
  TERMS: "Local research account policy.", PROCESSING: "Process selected evidence. Withdrawal stops new work.", TRAINING: "Optional training permission. No training service is enabled.",
} };

test("registration requires policy acceptance and recovery uses a generic local-mail response", async ({ page }) => {
  const submitted: { path: string; body: Record<string, unknown> }[] = [];
  await page.route("**/api/**", async route => {
    const path = new URL(route.request().url()).pathname;
    if (path === "/api/session") return route.fulfill({ json: { authenticated: false, csrf: "test" } });
    if (path === "/api/account/policy") return route.fulfill({ json: policy });
    submitted.push({ path, body: route.request().postDataJSON() });
    return route.fulfill({ status: 202, json: { status: "ACCEPTED" } });
  });
  await page.goto("/");
  await page.getByRole("button", { name: "Create account", exact: true }).click();
  await page.getByLabel("New username").fill("new.player");
  await page.getByLabel("Email address", { exact: true }).fill("player@example.com");
  await page.getByLabel("New password", { exact: false }).fill("Fixture-only-password!42");
  await page.getByRole("button", { name: "Confirm account request" }).click();
  expect(submitted).toHaveLength(0);
  await page.getByLabel("I accept this local account policy", { exact: false }).check();
  await page.getByRole("button", { name: "Confirm account request" }).click();
  await expect(page.getByRole("status")).toContainText("No live email is sent");
  expect(submitted[0]).toMatchObject({ path: "/api/account/register", body: { accepted_terms: true, policy_version: policy.version } });
  await page.getByRole("button", { name: "Forgot password" }).click();
  await page.getByLabel("Email address", { exact: true }).fill("unknown@example.com");
  await page.getByRole("button", { name: "Confirm account request" }).click();
  await expect.poll(() => submitted.length).toBe(2);
  expect(submitted[1]).toMatchObject({ path: "/api/account/link", body: { purpose: "RESET" } });
});

test("reset link is scrubbed from the URL, waits for confirmation and renders on mobile", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  const token = "s".repeat(43);
  const submissions: unknown[] = [];
  const urls: string[] = [];
  await page.route("**/api/**", async route => {
    urls.push(route.request().url());
    const path = new URL(route.request().url()).pathname;
    if (path === "/api/session") return route.fulfill({ json: { authenticated: false, csrf: "test" } });
    if (path === "/api/account/policy") return route.fulfill({ json: policy });
    submissions.push(route.request().postDataJSON());
    return route.fulfill({ json: { status: "CONFIRMED" } });
  });
  await page.goto(`/#account=reset:${token}`);
  await expect(page.getByRole("heading", { name: "Set a new password" })).toBeVisible();
  expect(new URL(page.url()).hash).toBe("");
  expect(submissions).toHaveLength(0);
  expect(urls.some(url => url.includes(token))).toBe(false);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.getByLabel("New password", { exact: false }).fill("Fixture-only-password!42");
  await page.getByRole("region", { name: "Account access" }).screenshot({ path: "test-results/m14-recovery-mobile.png" });
  await page.getByRole("button", { name: "Confirm account request" }).click();
  await expect(page.getByRole("status")).toHaveText("Confirmed. You can now sign in.");
  expect(submissions).toEqual([{ token, purpose: "RESET", password: "Fixture-only-password!42" }]);
});

test("account controls revoke a session and explicitly confirm consent withdrawal", async ({ page }) => {
  let processing = true, revoked = false;
  const mutations: { path: string; body: unknown }[] = [];
  await page.route("**/api/**", async route => {
    const path = new URL(route.request().url()).pathname;
    const method = route.request().method();
    if (method !== "GET") mutations.push({ path, body: route.request().postData() ? route.request().postDataJSON() : null });
    let data: unknown;
    if (path === "/api/session") data = { authenticated: true, csrf: "test", local_uploads: false };
    else if (path === "/api/account/policy") data = policy;
    else if (path === "/api/account/details") data = {
      email: "player@example.com", email_verified: true, processing_consent: processing, processing_withdrawn: !processing,
      training_consent: false, suppressed_matches: 1, consent_history: [],
      sessions: revoked ? [] : [{ id: "other", created_at: "2026-09-30T12:00:00Z", expires_at: "2026-10-07T12:00:00Z", current: false }],
    };
    else if (path === "/api/account/sessions/other") { revoked = true; data = { signed_out: false }; }
    else if (path === "/api/account/consent") { processing = false; data = { receipt_id: "receipt" }; }
    else if (path === "/api/account/email") data = { status: "ACCEPTED" };
    else if (path === "/api/overview") data = { runs: [], events: [], assignments: [], plans: [], evaluations: [], practice: [], drills: [] };
    else if (path === "/api/preferences") data = preferences;
    else if (path === "/api/notices") data = { notices: [] };
    else if (path === "/api/feedback") data = { feedback: [] };
    else if (path === "/api/evidence") data = { events: [], total: 0, next_offset: null };
    else if (path === "/api/matches") data = { matches: [], syncs: [], total: 0, next_offset: null };
    else if (path === "/api/player-identities") data = { identities: [] };
    else if (path === "/api/match-providers") data = { providers: [] };
    else return route.fulfill({ status: 404, json: { error: "Unexpected request" } });
    await route.fulfill({ json: data });
  });
  await page.goto("/");
  await page.getByText("Account security and consent", { exact: true }).click();
  await page.getByRole("button", { name: "Sign out other session" }).click();
  await expect(page.locator("#account-security").getByRole("status")).toContainText("Session signed out");
  await page.getByRole("button", { name: "Withdraw workspace processing" }).click();
  await page.getByRole("button", { name: "Confirm data permission", exact: true }).click();
  expect(mutations.filter(item => item.path.endsWith("consent"))).toHaveLength(0);
  await page.getByLabel("I confirm this withdrawal", { exact: false }).check();
  await page.getByRole("button", { name: "Confirm data permission", exact: true }).click();
  await expect(page.locator("#account-security")).toContainText("Workspace processing: withdrawn");
  expect(mutations.find(item => item.path.endsWith("consent"))?.body).toMatchObject({ scope: "PROCESSING", action: "WITHDRAW", confirmed: true });
  await page.getByLabel("Replacement email").fill("new@example.com");
  await page.getByLabel("Current password for email change").fill("Fixture-only-password!42");
  await page.getByRole("button", { name: "Verify replacement email" }).click();
  await expect(page.locator("#account-security").getByRole("status")).toContainText("local test mailbox");
  await page.locator("#account-security").screenshot({ path: "test-results/m14-account-desktop.png" });
});
