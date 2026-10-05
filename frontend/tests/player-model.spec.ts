import { test, expect } from "@playwright/test";
import { mockWorkspace } from "./workspace-fixtures";

const counts = { numerator: 5, denominator: 50, failures: 45, eligible_unknown: 2, unknown_eligibility: 1, excluded: 3, coverage: 50 / 52, eligibility_coverage: 55 / 56, sessions: 5 };
const card = { id: "group", state: "OBSERVED_FAILURE_PATTERN", reasons: [], summary: counts, failure_interval: [.78, .95], priority_rank: 1, score: .4, policy_version: "diagnosis-policy/1", policy_hash: "a".repeat(64), scope: { situation: "tekken8.jin-vs-jin.blocked-uf4/v1", metric: "punish-success/v1", context: "jin/jin", game_build: "fixture", knowledge_revision: "knowledge/1", knowledge_hash: null, detector_version: "human-adjudication/1", platform: "synthetic", dataset_kind: "synthetic" }, review: { independently_reviewed: 56, agreement: 1 }, factors: { frequency: 52 / 56, value: .7, certainty: .78, trainability: .8 }, assessment: { rationale: "Synthetic relative value assessment." }, assessment_drill: { key: "drill/1", content_hash: "b".repeat(64) }, drills: [{ key: "drill/1", title: "Synthetic response drill" }], evidence_hash: "c".repeat(64), evidence_total: 56, evidence: [{ id: "event-1", match_id: "match-1", asset_id: "asset-1", start_us: 2000000, end_us: 2100000, outcome: "FAILURE", played_at: "2026-08-01T12:00:00Z" }], trends: [{ period: "2026-08", summary: counts }] };
const data = { cards: [card], card_total: 1, next_offset: null, filters: { date_from: "2026-08-01", date_to: "2026-08-31", dataset_kind: "synthetic" }, unavailable_events: {}, capture_inventory: { ranked_matches: 8, with_publication: 5, without_publication: 3 }, history: { summary: { wins: 1, losses: 3, unknown: 4, known_results: 4, win_rate: .25 }, trends: [{ period: "2026-08", wins: 1, losses: 3, unknown: 4 }] }, history_note: "Recorded match results describe history separately from gameplay.", frequency_note: "Frequency is the eligible share of reviewed candidate windows." };
const overview = { runs: [], events: [], drills: [], assignments: [], plans: [], evaluations: [], practice: [] };

test.beforeEach(async ({ page }) => {
  await page.route("**/api/session", r => r.fulfill({ json: { authenticated: true, csrf: "fixture", local_uploads: false } }));
  await page.route("**/api/overview", r => r.fulfill({ json: overview }));
  await page.route("**/api/match-providers", r => r.fulfill({ json: { providers: [] } }));
  await page.route("**/api/player-identities", r => r.fulfill({ json: { identities: [] } }));
  await page.route("**/api/matches?*", r => r.fulfill({ json: { matches: [], total: 0, next_offset: null, syncs: [] } }));
  await mockWorkspace(page);
});

test("priority explains unknowns, score pins, timestamp evidence and separate results", async ({ page }) => {
  await page.route("**/api/player-model?*", r => r.fulfill({ json: data })); await page.goto("/");
  const panel = page.locator("#diagnosis");
  await expect(panel.getByText("Research priority 1", { exact: true })).toBeVisible();
  await expect(panel.getByText("5 / 50 successful responses", { exact: true })).toBeVisible();
  await expect(panel.getByText(/2 unknown outcomes; 1 unknown eligibility; 3 excluded/)).toBeVisible();
  await panel.getByText("Priority calculation and provenance", { exact: true }).click();
  await expect(panel.getByText(/Score: 0.4000/)).toBeVisible();
  await expect(panel.getByText("a".repeat(64), { exact: false })).toBeVisible();
  await panel.getByText("Supporting timestamp evidence (1 of 56)", { exact: true }).click();
  await expect(panel.getByRole("link", { name: "Play supporting window" })).toHaveAttribute("href", "/api/assets/asset-1/media#t=2,2.1");
  await panel.getByRole("button", { name: "Inspect supporting match" }).click();
  await expect(page.getByText("Showing match match-1.", { exact: false })).toBeVisible();
  await expect(panel.getByText(/1 wins \/ 4 known results; 3 losses and 4 unknown/)).toBeVisible();
});

test("insufficient and real validation states stay unranked and cannot assign", async ({ page }) => {
  await page.route("**/api/player-model?*", r => r.fulfill({ json: { ...data, cards: [{ ...card, state: "REAL_VALIDATION_PENDING", score: null, priority_rank: null, reasons: ["EXPERT_AND_USER_UTILITY_VALIDATION"], scope: { ...card.scope, dataset_kind: "real" } }], filters: { ...data.filters, dataset_kind: "real" } } }));
  await page.goto("/"); const panel = page.locator("#diagnosis");
  await expect(panel.getByText("Real-game diagnosis validation pending", { exact: true })).toBeVisible();
  await expect(panel.getByText("Unranked", { exact: true })).toBeVisible();
  await expect(panel.getByRole("button", { name: "Assign Synthetic response drill" })).toBeDisabled();
  await expect(panel.getByText("expert and user utility validation", { exact: true })).toBeVisible();
});

test("scope filters are explicit and mobile cards stay readable", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.route("**/api/player-model?*", r => r.fulfill({ json: data })); await page.goto("/");
  await page.getByLabel("Diagnosis from (UTC date)").fill("2026-08-01");
  await page.getByLabel("Diagnosis through (UTC date)").fill("2026-08-31");
  await page.getByLabel("Diagnosis context", { exact: true }).fill("jin/jin");
  await page.getByLabel("Evidence scope", { exact: true }).selectOption("synthetic");
  await page.getByText("Measurement version filters", { exact: true }).click();
  await page.getByLabel("Knowledge revision", { exact: true }).fill("knowledge/1");
  const sent = page.waitForRequest(r => r.url().includes("/api/player-model?") && r.url().includes("knowledge_revision="));
  await page.getByRole("button", { name: "Apply diagnosis filters" }).click();
  const url = new URL((await sent).url()); expect(url.searchParams.get("context")).toBe("jin/jin");
  expect(url.searchParams.get("dataset_kind")).toBe("synthetic"); expect(url.searchParams.has("outcome")).toBe(false);
  await expect(page.locator("#diagnosis").getByText("Observed failure pattern", { exact: true })).toBeVisible();
  await page.locator("#diagnosis").getByText("Priority calculation and provenance", { exact: true }).click();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await page.locator("#diagnosis").screenshot({ path: "test-results/m10-diagnosis-mobile.png" });
});

test("reviewed research priority assigns through the existing training pipeline", async ({ page }) => {
  await page.route("**/api/player-model?*", r => r.fulfill({ json: data }));
  await page.route("**/api/assignments", r => r.fulfill({ status: 201, json: { id: "assignment-1" } }));
  await page.goto("/");
  const sent = page.waitForRequest(r => r.url().endsWith("/api/assignments") && r.method() === "POST");
  await page.getByRole("button", { name: "Assign Synthetic response drill" }).click();
  expect((await sent).postDataJSON()).toEqual({ drill_key: "drill/1", request_id: expect.any(String), diagnosis: { card_id: card.id, evidence_hash: card.evidence_hash, policy_hash: card.policy_hash, filters: data.filters } });
  await expect(page.getByRole("heading", { name: "03 / Practice the same response" })).toBeVisible();
});

test("refresh removes withdrawn evidence and failed reads clear old priorities", async ({ page }) => {
  let state = "active";
  await page.route("**/api/player-model?*", r => state === "failed" ? r.fulfill({ status: 503, json: { error: "Diagnosis temporarily unavailable" } }) : r.fulfill({ json: state === "active" ? data : { ...data, cards: [], card_total: 0, unavailable_events: { WITHDRAWN_EXPIRED_OR_DISPUTED: 56 } } }));
  await page.goto("/"); const panel = page.locator("#diagnosis");
  await expect(panel.getByText("Research priority 1", { exact: true })).toBeVisible();
  state = "withdrawn"; await panel.getByRole("button", { name: "Refresh diagnosis" }).click();
  await expect(panel.getByText("Research priority 1", { exact: true })).toHaveCount(0);
  await expect(panel.getByText(/56 events excluded/)).toBeVisible();
  state = "active"; await panel.getByRole("button", { name: "Refresh diagnosis" }).click();
  await expect(panel.getByText("Research priority 1", { exact: true })).toBeVisible();
  state = "failed"; await panel.getByRole("button", { name: "Refresh diagnosis" }).click();
  await expect(panel.getByRole("alert")).toHaveText("Diagnosis temporarily unavailable");
  await expect(panel.getByText("Research priority 1", { exact: true })).toHaveCount(0);
});
