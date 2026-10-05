import type { Page } from "@playwright/test";

export const preferences = { username: "local-player", display_timezone: "UTC", onboarding_completed_at: "2026-09-23T12:00:00Z", analysis_notices: true, practice_notices: true, followup_notices: true, processing_consent_at: null, training_consent_at: null };
export async function mockWorkspace(page: Page) {
  await page.route("**/api/plans/*/comparison", route => route.fulfill({ json: { plan_hash: "legacy", report_hash: "legacy", dataset_kind: "synthetic", protocol: {}, specification: { minimum_sample: 40, minimum_sessions: 5, minimum_practice: 40, meaningful_change: 0.1 }, phases: {}, revisions: [] } }));
  await page.route("**/api/assignments/*/training", route => route.fulfill({ json: { status: "ASSIGNED", drill_id: "legacy-fixture", drill_hash: "", blockers: ["REVIEWED_WORKFLOW_REQUIRED"], workflow: null, progression: null, evidence: [], logs: [] } }));
  await page.route("**/api/player-model?*", route => route.fulfill({ json: { cards: [], card_total: 0, next_offset: null, filters: { date_from: "2026-08-01", date_to: "2026-10-05", dataset_kind: "real" }, unavailable_events: {}, capture_inventory: { ranked_matches: 0, with_publication: 0, without_publication: 0 }, history: { summary: { wins: 0, losses: 0, unknown: 0, known_results: 0, win_rate: null }, trends: [] }, history_note: "Recorded ranked-match history is separate from gameplay diagnosis.", frequency_note: "Frequency describes reviewed candidate windows." } }));
  await page.route("**/api/preferences", route => route.fulfill({ json: preferences }));
  await page.route("**/api/notices", route => route.fulfill({ json: { notices: [], remaining: 0 } }));
  await page.route("**/api/feedback", route => route.fulfill({ json: { feedback: [] } }));
  await page.route("**/api/evidence?*", route => route.fulfill({ json: { events: [], total: 0, next_offset: null } }));
}
