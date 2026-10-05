import { expect, test } from "@playwright/test";
import { mockWorkspace } from "./workspace-fixtures";

const overview = { runs: [], events: [], drills: [], assignments: [{ id: "assignment-1", drill_id: "drill/2", status: "ASSIGNED" }], plans: [], evaluations: [], practice: [] };
const detail = { id: "assignment-1", status: "ASSIGNED", drill_id: "drill/2", drill_hash: "d".repeat(64), blockers: [], workflow: { response: "Synthetic reviewed response.", success_criteria: "Independent reviewers confirm the visible response.", setup_steps: ["Prepare the synthetic native fixture."], alternatives: ["Use the independently reviewed safe alternative."], capture_steps: ["Record the entire practice block including uncertain windows."], progression: { minimum_known: 40, minimum_sessions: 2, minimum_coverage: .9, minimum_agreement: .8, ready_lower_bound: .7 } }, progression: { state: "MORE_REVIEWED_PRACTICE_NEEDED", next_action: "Collect enough compatible reviewed trials across distinct sessions.", reasons: [], summary: { numerator: 0, denominator: 0, sessions: 0, eligible_unknown: 0, unknown_eligibility: 0, coverage: null }, agreement: null }, unavailable_trials: 0, logs: [], evidence: [] };

test.beforeEach(async ({ page }) => {
  await page.route("**/api/session", r => r.fulfill({ json: { authenticated: true, csrf: "fixture", local_uploads: false } }));
  await page.route("**/api/overview", r => r.fulfill({ json: overview }));
  await page.route("**/api/match-providers", r => r.fulfill({ json: { providers: [] } }));
  await page.route("**/api/player-identities", r => r.fulfill({ json: { identities: [] } }));
  await page.route("**/api/matches?*", r => r.fulfill({ json: { matches: [], total: 0, next_offset: null, syncs: [] } }));
  await mockWorkspace(page);
});

test("guided setup reports an interrupted session separately with stable retry identity", async ({ page }) => {
  const bodies: Record<string, unknown>[] = []; let accepted = false;
  await page.route("**/api/assignments/assignment-1/training", r => r.fulfill({ json: { ...detail, logs: accepted ? [{ id: "report-1", state: "INTERRUPTED", started_at: "2026-08-07T10:00:00Z", ended_at: "2026-08-07T10:10:00Z", reported_attempts: 3, obstacle: "SETUP" }] : [] } }));
  await page.route("**/api/assignments/assignment-1/reports", r => { bodies.push(r.request().postDataJSON()); if (bodies.length === 1) return r.fulfill({ status: 503, json: { error: "Temporary report outage" } }); accepted = true; return r.fulfill({ status: 201, json: { id: "report-1", verified_trials: 0 } }); });
  await page.goto("/"); await page.getByLabel("Drill assignment", { exact: true }).selectOption("assignment-1");
  const guide = page.getByRole("article", { name: "Reviewed practice guide" });
  await expect(guide.getByText("Prepare the synthetic native fixture.")).toBeVisible();
  await guide.getByLabel("Session result").selectOption("INTERRUPTED");
  await guide.getByLabel("Session started (local)").fill("2026-08-07T10:00");
  await guide.getByLabel("Session ended (local)").fill("2026-08-07T10:10");
  await guide.getByLabel("Self-reported attempts").fill("3"); await guide.getByLabel("Obstacle", { exact: true }).selectOption("SETUP");
  await guide.getByRole("button", { name: "Save self-report" }).click(); await expect(guide.getByRole("alert")).toHaveText("Temporary report outage");
  await guide.getByRole("button", { name: "Save self-report" }).click();
  await expect(guide.getByText(/3 reported attempts/)).toBeVisible(); expect(bodies[0]).toEqual(bodies[1]);
  expect(bodies[1]).toMatchObject({ state: "INTERRUPTED", reported_attempts: 3, obstacle: "SETUP", request_id: expect.any(String) });
  await expect(guide.getByText(/0\/0 current known successes/)).toBeVisible();
});

test("withdrawn or failed guidance clears native instructions and reports can be erased", async ({ page }) => {
  let state = "active", deleted = false;
  await page.route("**/api/assignments/assignment-1/training", r => state === "failed" ? r.fulfill({ status: 503, json: { error: "Practice read unavailable" } }) : r.fulfill({ json: state === "withdrawn" ? { ...detail, workflow: null, progression: null, blockers: ["ASSIGNMENT_OR_DRILL_UNAVAILABLE"], logs: [] } : { ...detail, logs: deleted ? [] : [{ id: "report-1", state: "SKIPPED", started_at: "2026-08-07T10:00:00Z", ended_at: "2026-08-07T10:00:00Z", reported_attempts: 0, obstacle: "TIME" }] } }));
  await page.route("**/api/practice-reports/report-1", r => { expect(r.request().method()).toBe("DELETE"); deleted = true; return r.fulfill({ json: { status: "DELETED" } }); });
  await page.goto("/"); await page.getByLabel("Drill assignment", { exact: true }).selectOption("assignment-1");
  const guide = page.getByRole("article", { name: "Reviewed practice guide" });
  await guide.getByRole("button", { name: "Delete self-report" }).click(); await expect(guide.getByText("No self-reports yet.")).toBeVisible();
  state = "withdrawn"; await guide.getByRole("button", { name: "Refresh practice guidance" }).click(); await expect(guide.getByText("Prepare the synthetic native fixture.")).toHaveCount(0);
  state = "failed"; await guide.getByRole("button", { name: "Refresh practice guidance" }).click(); await expect(guide.getByRole("alert")).toHaveText("Practice read unavailable");
});

test("cancelled assignment hides new practice controls and native guide fits mobile", async ({ page }) => {
  let cancelled = false;
  await page.setViewportSize({ width: 390, height: 844 });
  await page.route("**/api/assignments/assignment-1/training", r => r.fulfill({ json: cancelled ? { ...detail, status: "CANCELLED", workflow: null, progression: null, blockers: ["ASSIGNMENT_OR_DRILL_UNAVAILABLE"] } : detail }));
  await page.route("**/api/assignments/assignment-1/cancel", r => { expect(r.request().headers()["x-csrftoken"]).toBe("fixture"); cancelled = true; return r.fulfill({ json: { status: "CANCELLED" } }); });
  await page.goto("/"); await page.getByLabel("Drill assignment", { exact: true }).selectOption("assignment-1");
  const guide = page.getByRole("article", { name: "Reviewed practice guide" });
  await expect(guide.getByText("Synthetic reviewed response.", { exact: false })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await guide.screenshot({ path: "test-results/m11-practice-mobile.png" });
  await guide.getByRole("button", { name: "Cancel this assignment" }).click();
  await expect(guide.getByRole("button", { name: "Save self-report" })).toHaveCount(0);
});
