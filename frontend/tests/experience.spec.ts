import { test, expect } from "@playwright/test";
import { preferences } from "./workspace-fixtures";

const overview = { runs: [], events: [], assignments: [], plans: [], evaluations: [], practice: [], drills: [] };
const event = { id: "11111111-1111-4111-8111-111111111111", match_id: "22222222-2222-4222-8222-222222222222", played_at: "2026-09-01T23:59:00Z", mode: "ranked", start_us: 1200000, end_us: 1400000, eligibility: "ELIGIBLE", outcome: "UNKNOWN", situation: "test-target/1", source_asset_id: "asset-1", source_hash: "a".repeat(64), game_build: "fixture", knowledge_revision: "knowledge/1", detector_version: "human-review/1", dataset_kind: "synthetic", metadata_state: "USER_UPLOAD", reviewed: true, review_count: 2, selectable: true };

test.use({ timezoneId: "America/Toronto" });

test("onboarding, preferences, persistent notices, local feedback and export", async ({ page }) => {
  let prefs = { ...preferences, onboarding_completed_at: null as string | null };
  let dismissed = false;
  const feedback: {id: string; category: string; message: string; status: string}[] = [];
  await page.route("**/api/**", async route => {
    const path = new URL(route.request().url()).pathname, method = route.request().method();
    let data: unknown = {};
    if (path === "/api/session") data = { authenticated: true, csrf: "fixture", local_uploads: false };
    else if (path === "/api/overview") data = overview;
    else if (path === "/api/preferences") {
      if (method === "PATCH") { const body = route.request().postDataJSON(); prefs = { ...prefs, ...body, ...(body.complete_onboarding ? { onboarding_completed_at: "2026-09-23T12:00:00Z" } : {}) }; }
      data = prefs;
    } else if (path === "/api/notices") { if (method === "POST") dismissed = true; data = { notices: dismissed || !prefs.analysis_notices ? [] : [{ key: "run:1", message: "Recording needs review", href: "#evidence", category: "analysis" }], remaining: 0 }; }
    else if (path === "/api/feedback") {
      if (method === "POST") { const body = route.request().postDataJSON(); feedback.push({ id: "feedback-1", ...body, status: "OPEN" }); data = { id: "feedback-1" }; }
      else data = { feedback };
    } else if (path === "/api/evidence") data = { events: [], total: 0, next_offset: null };
    else if (path === "/api/matches") data = { matches: [], total: 0, next_offset: null, syncs: [] };
    else if (path === "/api/match-providers") data = { providers: [] };
    else if (path === "/api/player-identities") data = { identities: [] };
    else if (path === "/api/account/export") return route.fulfill({ json: { schema: "dojopulse-export/1", username: prefs.username }, headers: { "Content-Disposition": 'attachment; filename="dojopulse-workspace.json"' } });
    else return route.fulfill({ status: 404, json: { error: "Unexpected request" } });
    await route.fulfill({ json: data });
  });
  await page.goto("/");
  await expect(page.getByRole("button", { name: "Complete setup guide" })).toBeDisabled();
  await page.getByLabel("I understand the supported scope", { exact: false }).check();
  await page.getByRole("button", { name: "Complete setup guide" }).click();
  await expect(page.getByText("Setup guide acknowledged.", { exact: false })).toBeVisible();
  await page.getByText("Updates (1)", { exact: true }).click();
  await page.getByRole("button", { name: "Dismiss Recording needs review" }).click();
  await page.reload();
  await expect(page.getByText("Updates (0)", { exact: true })).toBeVisible();
  await page.getByText("Account, privacy and preferences", { exact: true }).click();
  await page.getByLabel("Display times in").selectOption("browser");
  await page.getByLabel("Analysis and review updates", { exact: true }).uncheck();
  await page.getByRole("button", { name: "Save preferences" }).click();
  await expect(page.getByText("Preferences saved.", { exact: false })).toBeVisible();
  expect(prefs.analysis_notices).toBe(false);
  const download = page.waitForEvent("download");
  await page.getByRole("button", { name: "Download my workspace data (JSON)" }).click();
  expect((await download).suggestedFilename()).toBe("dojopulse-workspace.json");
  await page.getByText("Help, feedback and correction requests", { exact: true }).click();
  await page.getByLabel("What happened or what should change?").fill("Please clarify capture setup.");
  await page.getByRole("button", { name: "Save feedback" }).click();
  await expect(page.getByText("Feedback saved locally.", { exact: false })).toBeVisible();
  await expect(page.getByRole("list", { name: "Your feedback requests" })).toContainText("Please clarify capture setup.");
});

test("timeline filters, complete-match selection, correction request and mobile keyboard navigation", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.emulateMedia({ reducedMotion: "reduce" });
  let filterSeen = false, report: unknown;
  await page.route("**/api/**", async route => {
    const url = new URL(route.request().url()), path = url.pathname;
    let data: unknown;
    if (path === "/api/session") data = { authenticated: true, csrf: "fixture", local_uploads: false };
    else if (path === "/api/overview") data = overview;
    else if (path === "/api/preferences") data = preferences;
    else if (path === "/api/notices") data = { notices: [] };
    else if (path === "/api/feedback") { if (route.request().method() === "POST") { report = route.request().postDataJSON(); data = { id: "report-1" }; } else data = { feedback: [] }; }
    else if (path === "/api/evidence") { filterSeen ||= url.searchParams.get("outcome") === "UNKNOWN"; data = { events: [event], total: 1, next_offset: null }; }
    else if (path === "/api/match-providers") data = { providers: [] };
    else if (path === "/api/player-identities") data = { identities: [] };
    else if (path === "/api/matches") data = { matches: [], total: 0, next_offset: null, syncs: [] };
    else return route.fulfill({ status: 404, json: { error: "Media unavailable" } });
    await route.fulfill({ json: data });
  });
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Your workspace" })).toBeVisible();
  await page.keyboard.press("Tab");
  await expect(page.getByRole("link", { name: "Skip to workspace" })).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(page.locator("#workspace-content")).toBeFocused();
  await page.getByLabel("Evidence outcome").selectOption("UNKNOWN");
  await page.getByRole("button", { name: "Search evidence", exact: true }).click();
  await expect.poll(() => filterSeen).toBe(true);
  await page.getByRole("button", { name: "Select complete match", exact: false }).click();
  await expect(page.locator("#evidence")).toContainText("1 selected across pages and filters");
  await page.getByRole("button", { name: "Inspect event", exact: false }).click();
  await expect(page.getByRole("region", { name: "Evidence player" })).toContainText("1.20–1.40 seconds");
  await expect(page.locator("#evidence")).toContainText("UTC");
  await page.getByText("Evidence provenance", { exact: true }).click();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.locator(".evidence-detail").screenshot({ path: "test-results/m13-evidence-mobile.png" });
  await page.getByRole("button", { name: "Request evidence correction" }).click();
  await expect(page.getByLabel("What happened or what should change?")).toBeFocused();
  await page.getByLabel("What happened or what should change?").fill("The evidence window needs another review.");
  await page.getByRole("button", { name: "Save feedback" }).click();
  await expect.poll(() => report).toMatchObject({ event_id: event.id, category: "CORRECTION" });
});

test("account deletion needs explicit confirmation and returns to sign in", async ({ page }) => {
  let authenticated = true, deletions = 0;
  await page.route("**/api/**", async route => {
    const path = new URL(route.request().url()).pathname;
    let data: unknown;
    if (path === "/api/session") data = { authenticated, csrf: "fixture", local_uploads: false };
    else if (path === "/api/overview") data = overview;
    else if (path === "/api/preferences") data = preferences;
    else if (path === "/api/notices") data = { notices: [] };
    else if (path === "/api/feedback") data = { feedback: [] };
    else if (path === "/api/match-providers") data = { providers: [] };
    else if (path === "/api/player-identities") data = { identities: [] };
    else if (path === "/api/evidence") data = { events: [], total: 0, next_offset: null };
    else if (path === "/api/matches") data = { matches: [], total: 0, next_offset: null, syncs: [] };
    else if (path === "/api/account") { expect(route.request().postDataJSON()).toEqual({ password: "test-password", confirmation: "DELETE MY WORKSPACE" }); deletions++; authenticated = false; data = { status: "DELETED" }; }
    else return route.fulfill({ status: 404, json: { error: "Unexpected request" } });
    await route.fulfill({ json: data });
  });
  await page.goto("/");
  await page.getByText("Account, privacy and preferences", { exact: true }).click();
  await page.getByRole("button", { name: "Delete my workspace", exact: true }).click();
  await page.getByRole("button", { name: "Confirm permanent deletion" }).click();
  expect(deletions).toBe(0);
  await page.getByLabel("Current password", { exact: true }).fill("test-password");
  await page.getByLabel("Type DELETE MY WORKSPACE").fill("DELETE MY WORKSPACE");
  await page.getByRole("button", { name: "Confirm permanent deletion" }).click();
  await expect(page.getByRole("button", { name: "Sign in", exact: true })).toBeVisible();
  expect(deletions).toBe(1);
});

test("guided synthetic baseline, frozen plan, practice and honest comparison", async ({ page }) => {
  let assigned = false, frozen = false, practiced = false, evaluated = false;
  const counts = { numerator: 1, denominator: 1, eligible_unknown: 0, unknown_eligibility: 0, coverage: 1, rate: 1 };
  await page.route("**/api/**", async route => {
    const url = new URL(route.request().url()), path = url.pathname, method = route.request().method();
    let data: unknown;
    if (path === "/api/session") data = { authenticated: true, csrf: "fixture", local_uploads: false };
    else if (path === "/api/preferences") data = { ...preferences, display_timezone: "browser" };
    else if (path === "/api/notices") data = { notices: [] };
    else if (path === "/api/feedback") data = { feedback: [] };
    else if (path === "/api/match-providers") data = { providers: [] };
    else if (path === "/api/player-identities") data = { identities: [] };
    else if (path === "/api/matches") data = { matches: [], total: 0, next_offset: null, syncs: [] };
    else if (path === "/api/evidence") data = { events: [{ ...event, mode: url.searchParams.get("mode") || "ranked" }], total: 1, next_offset: null };
    else if (path === "/api/assignments" && method === "POST") { assigned = true; data = { id: "assignment-1" }; }
    else if (path === "/api/plans" && method === "POST") { expect(route.request().postDataJSON().baseline_ids).toEqual([event.id]); frozen = true; data = { id: "plan-1" }; }
    else if (path === "/api/assignments/assignment-1/practice") { expect(frozen).toBe(true); practiced = true; data = { id: "practice-1" }; }
    else if (path === "/api/plans/plan-1/evaluate") { expect(practiced).toBe(true); evaluated = true; data = { id: "evaluation-1" }; }
    else if (path === "/api/overview") data = { ...overview,
      drills: [{ key: "synthetic-drill/1", status: "APPROVED", payload: { title: "Synthetic test drill" } }],
      assignments: assigned ? [{ id: "assignment-1", drill_id: "synthetic-drill/1", status: practiced ? "PRACTICED" : "ASSIGNED" }] : [],
      plans: frozen ? [{ id: "plan-1", assignment_id: "assignment-1", specification: { baseline_membership: [[event.id, "hash"]], baseline_end: "2026-09-02T00:00:00Z", followup_start: "2026-09-05T00:00:00Z", followup_end: "2026-09-15T00:00:00Z" } }] : [],
      practice: practiced ? [{ id: "practice-1", attempts: 1, summary: counts }] : [],
      evaluations: evaluated ? [{ id: "evaluation-1", revision: 1, invalidated_at: null, result: { status: "INSUFFICIENT_EXPOSURE", dataset_kind: "synthetic", baseline: counts, followup: counts, verified_practice: 1, observed_change: 0, change_interval: null, next_action: "Gather more independent sessions before drawing a conclusion." } }] : [],
    };
    else return route.fulfill({ status: 404, json: { error: "Unexpected request" } });
    await route.fulfill({ json: data });
  });
  await page.goto("/");
  await expect(page.locator("#evidence")).toContainText("America/Toronto");
  await page.getByRole("button", { name: "Assign reviewed drill" }).click();
  await page.getByRole("button", { name: "Select complete match", exact: false }).click();
  await expect(page.getByRole("button", { name: "Link selected practice evidence" })).toBeDisabled();
  await page.getByLabel("Baseline cutoff (local)").fill("2026-09-02T00:00");
  await page.getByLabel("Follow-up starts after practice").fill("2026-09-05T00:00");
  await page.getByLabel("Follow-up ends", { exact: true }).fill("2026-09-15T00:00");
  await page.getByRole("button", { name: "Freeze selected baseline" }).click();
  await expect(page.getByText("Frozen plan plan-1", { exact: true })).toBeVisible();
  await page.getByLabel("Evidence purpose").selectOption("practice");
  await page.getByRole("button", { name: "Search evidence", exact: true }).click();
  await page.getByRole("button", { name: "Select complete match", exact: false }).click();
  await page.getByRole("button", { name: "Link selected practice evidence" }).click();
  await expect(page.getByText("Reviewed practice attempts linked: 1.", { exact: false })).toBeVisible();
  await page.getByLabel("Evidence purpose").selectOption("ranked");
  await page.getByRole("button", { name: "Search evidence", exact: true }).click();
  await page.getByRole("button", { name: "Select complete match", exact: false }).click();
  await page.getByRole("button", { name: "Evaluate selected follow-up" }).click();
  await expect(page.getByText("INSUFFICIENT EXPOSURE", { exact: true })).toBeVisible();
  await expect(page.getByText("Gather more independent sessions before drawing a conclusion.")).toBeVisible();
  await page.screenshot({ path: "test-results/m13-training-desktop.png", fullPage: true });
});
