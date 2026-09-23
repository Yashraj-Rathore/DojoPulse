import type { Page } from "@playwright/test";

export const preferences = { username: "local-player", display_timezone: "UTC", onboarding_completed_at: "2026-09-23T12:00:00Z", analysis_notices: true, practice_notices: true, followup_notices: true, processing_consent_at: null, training_consent_at: null };
export async function mockWorkspace(page: Page) {
  await page.route("**/api/preferences", route => route.fulfill({ json: preferences }));
  await page.route("**/api/notices", route => route.fulfill({ json: { notices: [], remaining: 0 } }));
  await page.route("**/api/feedback", route => route.fulfill({ json: { feedback: [] } }));
  await page.route("**/api/evidence?*", route => route.fulfill({ json: { events: [], total: 0, next_offset: null } }));
}
