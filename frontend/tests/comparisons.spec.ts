import { expect, test } from "@playwright/test";
import { mockWorkspace } from "./workspace-fixtures";

const phase = { start: "2026-08-11T00:00:00Z", end: "2026-08-31T00:00:00Z", collection: { expected_sessions: 5, observed_sessions: 4, complete: false, missing_reported_sessions: 1, skipped_reported_sessions: 0, withdrawn_reported_sessions: 0, unresolved_recorded_sessions: 0, matches_without_current_target_publication: 0 }, sessions: [], evidence: [{ id: "event-1", match_id: "match-1", session_code: "session-1", eligibility: "ELIGIBLE", outcome: "UNKNOWN", source: { decoder: { image_sha256: "sha256:" + "a".repeat(64) }, pipeline: "reviewed/1" } }] };
const report = { plan_hash: "p".repeat(64), report_hash: "r".repeat(64), dataset_kind: "synthetic", protocol: { version: "comparison-protocol/1", source_policy: { changes_require_new_reviewed_plan: true }, baseline_planning: { known_outcomes: 50, sessions: 5, session_rate_variance: 0, reasons: ["TOO_FEW_SESSIONS_FOR_VARIANCE_PLANNING"], planning: { sessions_per_period: null, actual_power_validated: false } } }, specification: { minimum_sample: 40, minimum_sessions: 5, minimum_practice: 40, meaningful_change: .1 }, phases: { FOLLOWUP: phase, RETENTION: { ...phase, start: "2026-09-01T00:00:00Z", end: "2026-09-15T00:00:00Z" } }, revisions: [{ id: "result-1", phase: "FOLLOWUP", revision: 1, result_hash: "h".repeat(64), available: false, unavailable_reasons: ["SOURCE_EXPIRED_WITHDRAWN_OR_CHANGED"], result: { status: "OBSERVED_IMPROVEMENT", reasons: [] } }] };
test.beforeEach(async ({ page }) => {
  await page.route("**/api/session", r => r.fulfill({ json: { authenticated: true, csrf: "fixture", local_uploads: false } }));
  await page.route("**/api/overview", r => r.fulfill({ json: { runs: [], events: [], drills: [], assignments: [], plans: [{ id: "plan-1", assignment_id: "assignment-1" }], evaluations: [], practice: [] } }));
  await page.route("**/api/match-providers", r => r.fulfill({ json: { providers: [] } }));
  await page.route("**/api/player-identities", r => r.fulfill({ json: { identities: [] } }));
  await page.route("**/api/matches?*", r => r.fulfill({ json: { matches: [], total: 0, next_offset: null, syncs: [] } }));
  await mockWorkspace(page);
  await page.route("**/api/plans/plan-1/comparison", r => r.fulfill({ json: report }));
});

test("missing-session retry keeps its request identity and never adds verified outcomes", async ({ page }) => {
  const bodies: Record<string, unknown>[] = [];
  await page.route("**/api/plans/plan-1/sessions", r => { bodies.push(r.request().postDataJSON()); expect(r.request().headers()["x-csrftoken"]).toBe("fixture"); return r.fulfill(bodies.length === 1 ? { status: 503, json: { error: "Collection temporarily unavailable" } } : { status: 201, json: { id: "session-report" } }); });
  await page.goto("/"); await page.getByLabel("Evaluation plan", { exact: true }).selectOption("plan-1");
  const guide = page.getByRole("article", { name: "Longitudinal comparison guide" });
  await expect(guide.getByText(/Collection has gaps/)).toBeVisible();
  await guide.getByLabel("Original play session code").fill("session-1"); await guide.getByLabel("Session time (local)").fill("2026-08-12T10:00");
  await guide.getByRole("button", { name: "Save collection report" }).click(); await expect(guide.getByRole("alert")).toHaveText("Collection temporarily unavailable");
  await guide.getByRole("button", { name: "Save collection report" }).click(); await expect(guide.getByRole("alert")).toHaveCount(0);
  expect(bodies[0]).toEqual(bodies[1]); expect(bodies[0]).toMatchObject({ state: "MISSING", phase: "FOLLOWUP", code: "session-1", request_id: expect.any(String) });
  await expect(guide.getByText(/Reports track collection and add zero verified outcomes/)).toBeVisible();
});

test("retention includes all recorded evidence and unavailable history has no active improvement", async ({ page }) => {
  await page.route("**/api/plans/plan-1/evaluate", r => { expect(r.request().postDataJSON()).toEqual({ phase: "RETENTION" }); return r.fulfill({ json: { id: "retention-result" } }); });
  await page.goto("/"); await page.getByLabel("Evaluation plan", { exact: true }).selectOption("plan-1");
  const guide = page.getByRole("article", { name: "Longitudinal comparison guide" });
  await guide.getByLabel("Comparison period").selectOption("RETENTION");
  await guide.getByRole("button", { name: "Compare all recorded retention evidence" }).click();
  await expect(guide.getByText(/historical evidence unavailable/)).toBeVisible();
  await expect(guide.getByText("observed improvement", { exact: true })).toHaveCount(0);
  await guide.getByText("Baseline session adequacy & study planning", { exact: true }).click();
  await expect(guide.getByText(/Actual power and assumptions are unvalidated/)).toBeVisible();
  await expect(guide.getByRole("link", { name: "Download reproducible comparison report" })).toHaveAttribute("href", "/api/plans/plan-1/comparison?download=1");
});

test("comparison read failure clears earlier evidence and report removal withdraws it", async ({ page }) => {
  let failed = false, deleted = false;
  await page.route("**/api/plans/plan-1/comparison", r => failed ? r.fulfill({ status: 503, json: { error: "Comparison read unavailable" } }) : r.fulfill({ json: { ...report, phases: { FOLLOWUP: { ...phase, sessions: deleted ? [] : [{ id: "receipt-1", code: "session-1", state: "MISSING", revision: 1, played_at: "2026-08-12T10:00:00Z" }] } } } }));
  await page.route("**/api/comparison-sessions/receipt-1", r => { expect(r.request().method()).toBe("DELETE"); deleted = true; return r.fulfill({ json: { status: "DELETED" } }); });
  await page.goto("/"); await page.getByLabel("Evaluation plan", { exact: true }).selectOption("plan-1");
  const guide = page.getByRole("article", { name: "Longitudinal comparison guide" });
  await guide.getByRole("button", { name: "Delete collection report" }).click(); await expect(guide.getByRole("button", { name: "Delete collection report" })).toHaveCount(0);
  failed = true; await guide.getByRole("button", { name: "Refresh comparison" }).click(); await expect(guide.getByRole("alert")).toHaveText("Comparison read unavailable");
  await expect(guide.getByRole("link", { name: "Download reproducible comparison report" })).toHaveCount(0);
});

test("source provenance and hash reports fit a narrow comparison view", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/"); await page.getByLabel("Evaluation plan", { exact: true }).selectOption("plan-1");
  const guide = page.getByRole("article", { name: "Longitudinal comparison guide" });
  await guide.getByText(/Included evidence & source provenance/).click(); await guide.getByText("Source and decoder", { exact: true }).click();
  await guide.getByText("Frozen scope, source policy & report hashes", { exact: true }).click();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await guide.screenshot({ path: "test-results/m12-comparison-mobile.png" });
});
