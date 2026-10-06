import {test, expect, type Page} from "@playwright/test";
import {mockWorkspace} from "./workspace-fixtures";

const device = {id: "device-fixture", label: "Fixture gaming PC", expires_at: "2027-01-01T12:00:00Z", revoked_at: null as string | null};
const match = {id: "match-fixture", played_at: "2026-09-01T12:00:00Z", mode: "ranked", game_build: "fixture", dataset_kind: "synthetic", can_attach_recording: true, recording_target: {metadata_revision: 1, player_namespace: "polaris", player_id: "fixture-player", player_slot: 1, opponent_ids: [{namespace: "polaris", value: "fixture-opponent"}]}, recordings: [], replays: [], result: "UNKNOWN", metadata_state: "METADATA_IMPORTED", evidence_status: "EVIDENCE_REQUIRED", source: null};

async function mount(page: Page, records: object[], handler?: (path: string, method: string, body: unknown) => object | undefined) {
  await page.route("**/api/**", async route => {
    const request = route.request(), path = new URL(request.url()).pathname;
    const override = handler?.(path, request.method(), request.postData() ? request.postDataJSON() : undefined);
    const data = override ?? (path === "/api/session" ? {authenticated: true, csrf: "fixture", local_uploads: true}
      : path === "/api/overview" ? {runs: [], events: [], drills: [], assignments: [], plans: [], evaluations: [], practice: []}
      : path === "/api/recording-devices" ? {enabled: true, policy_version: "fixture-policy", policy: "Explicit sync consent", devices: [device]}
      : path === "/api/synced-recordings" ? {recordings: records}
      : path === "/api/match-providers" ? {providers: []}
      : path === "/api/player-identities" ? {identities: []}
      : {matches: [match], total: 1, next_offset: null, syncs: []});
    await route.fulfill({json: data});
  });
  await mockWorkspace(page, false);
  await page.goto("/");
}

const recording = {id: "session-fixture", asset_id: "asset-fixture", availability: "AVAILABLE", uploaded_at: "2026-10-06T12:00:00Z", bytes: 1000000, media_url: "/api/assets/asset-fixture/media", match_id: null, attribution_state: "UNASSIGNED"};

test("explicit pairing, private ephemeral code, revocation and responsive states", async ({page}) => {
  await page.setViewportSize({width: 390, height: 844});
  let paired = false, revoked = false;
  await mount(page, [{...recording, availability: "PENDING", media_url: null}], (path, method, body) => {
    if (path === "/api/recording-devices" && method === "POST") {expect(body).toEqual({label: "My PC", sync_consent: true, policy_version: "fixture-policy"}); paired = true; return {pairing_code: "fixture-one-use-code", expires_at: new Date(Date.now() + 600000).toISOString()};}
    if (path === "/api/recording-devices/device-fixture" && method === "DELETE") {revoked = true; return {revoked: true};}
    if (path === "/api/recording-devices" && method === "GET" && revoked) return {enabled: true, policy_version: "fixture-policy", devices: [{...device, revoked_at: "2026-10-06T12:00:00Z"}]};
  });
  const section = page.getByRole("region", {name: "Recording sync", exact: true});
  await section.getByLabel("Computer label").fill("My PC");
  await section.getByLabel("I allow this paired computer", {exact: false}).check();
  await section.getByRole("button", {name: "Create pairing code"}).click();
  await expect(section.getByLabel("Pairing code", {exact: true})).toHaveValue("fixture-one-use-code");
  expect(paired).toBe(true);
  expect(await page.evaluate(() => JSON.stringify([localStorage, sessionStorage]))).not.toContain("fixture-one-use-code");
  await section.getByRole("button", {name: "Hide pairing code"}).click();
  await expect(section.getByLabel("Pairing code", {exact: true})).toHaveCount(0);
  await section.getByRole("button", {name: "Revoke Fixture gaming PC"}).click();
  await expect(section.getByText("Revoked", {exact: true})).toBeVisible();
  expect(revoked).toBe(true);
  await expect(section.getByText("Transfer or media validation is pending.", {exact: false})).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await section.screenshot({path: "test-results/m22-recording-sync-mobile.png"});
});

test("uses synced bytes for confirmed attribution without a second upload", async ({page}) => {
  let attached = false, uploads = 0;
  await mount(page, [recording], (path, method, body) => {
    if (path.startsWith("/api/upload-sessions")) uploads++;
    if (path.endsWith("/attach") && method === "POST") {
      const value = body as {match_id: string; metadata: {player_id: string; opponent_id: string; played_at: string; session_id: string}};
      expect(value.match_id).toBe(match.id); expect(value.metadata.player_id).toBe("fixture-player"); expect(value.metadata.opponent_id).toBe("fixture-opponent"); expect(value.metadata.played_at).toBe(match.played_at); expect(value.metadata.session_id).toBe("review-session");
      attached = true; return {attribution_state: "PENDING_REVIEW"};
    }
  });
  const section = page.getByRole("region", {name: "Recording sync", exact: true});
  await expect(section.locator("video")).toHaveAttribute("src", recording.media_url);
  await section.getByLabel("Imported match for this recording").selectOption(match.id);
  await section.getByRole("button", {name: "Confirm match attribution"}).click();
  const form = section.getByRole("region", {name: "Attach recording form"});
  await expect(form.getByLabel("Gameplay recording", {exact: true})).toHaveCount(0);
  await form.getByLabel("Recording session ID").fill("review-session");
  await form.getByLabel("Recording content").selectOption("synthetic");
  for (const label of ["I checked both players", "I consent to processing", "This is one continuous"]) await form.getByLabel(label, {exact: false}).check();
  await form.getByRole("button", {name: "Submit synced recording for attribution review"}).click();
  await expect(section.getByText("Attribution submitted for visual review.", {exact: false})).toBeVisible();
  expect(attached).toBe(true); expect(uploads).toBe(0);
});

test("remote deletion confirmation keeps local originals and removed playback unavailable", async ({page}) => {
  let removed = false;
  await mount(page, [recording], (path, method) => {
    if (path === "/api/assets/asset-fixture" && method === "DELETE") {removed = true; return {status: "DELETED"};}
    if (path === "/api/synced-recordings" && removed) return {recordings: [{...recording, availability: "REMOVED", media_url: null}]};
  });
  const section = page.getByRole("region", {name: "Recording sync", exact: true});
  await section.getByRole("button", {name: "Remove synced recording"}).click();
  await expect(section.getByText("Your original PC file stays intact.", {exact: false})).toBeVisible();
  expect(removed).toBe(false);
  await section.getByRole("button", {name: "Delete remote recording"}).click();
  await expect(section.getByText("REMOVED", {exact: true})).toBeVisible();
  await expect(section.locator("video")).toHaveCount(0);
  expect(removed).toBe(true);
});
