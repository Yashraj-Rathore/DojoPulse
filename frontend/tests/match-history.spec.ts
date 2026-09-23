import { test, expect } from "@playwright/test";

const providers = [
  { key: "ewgf-public", label: "EWGF.GG", enabled: false, reason: "Usage review and verified response data are pending." },
  { key: "synthetic-a", label: "Demo source A", enabled: true, reason: "Local demo with fictional matches.", example_id: "ExamplePlayer-A" },
];
const identity = { id: "identity-1", display_label: "Synthetic Player", value: "ExamplePlayer-A", state: "CLAIMED", can_sync: true, provider: "synthetic-a" };
const match = {
  id: "match-1", identity_id: identity.id, played_at: "2026-09-01T01:00:00Z", mode: "unknown", game_build: null,
  dataset_kind: "synthetic", opponent: "Synthetic Opponent", character: null, opponent_character: null,
  result: "WIN", metadata_state: "METADATA_IMPORTED", evidence_status: "EVIDENCE_REQUIRED", can_delete_metadata: true,
  source: { provider: "synthetic-a", revision: 1, retrieved_at: "2026-09-19T00:00:00Z", raw_game_version: "999" }, replays: [],
};
const blank = { matches: [], total: 0, next_offset: null, syncs: [] };
const overview = { runs: [], events: [], drills: [], assignments: [], plans: [], evaluations: [], practice: [] };

test("explicit selection, consent, import and removal flow", async ({ page }) => {
  let linked = false, synced = false, removed = false;
  let linkBody: unknown;
  await page.route("**/api/**", async route => {
    const url = new URL(route.request().url());
    const path = url.pathname;
    const method = route.request().method();
    let body: unknown;
    if (path === "/api/session") body = { authenticated: true, csrf: "fixture", local_uploads: false };
    else if (path === "/api/overview") body = overview;
    else if (path === "/api/match-providers") body = { providers };
    else if (path === "/api/player-candidates") body = { candidates: [{ display_name: "Synthetic Player", value: "ExamplePlayer-A", provider: "synthetic-a", ownership_verified: false, selection_token: "signed-fixture" }] };
    else if (path === "/api/player-identities" && method === "POST") { linked = true; linkBody = route.request().postDataJSON(); body = identity; }
    else if (path === "/api/player-identities") body = { identities: linked ? [{ ...identity, can_sync: !removed, state: removed ? "REVOKED" : "CLAIMED" }] : [] };
    else if (path.endsWith("/sync")) { synced = true; body = { id: "sync-1", status: "PENDING" }; }
    else if (path === "/api/matches/match-1" && method === "DELETE") { removed = true; body = { status: "DELETED", identity_sync_revoked: true }; }
    else if (path === "/api/matches") body = { ...blank, matches: synced && !removed ? [match] : [], total: synced && !removed ? 1 : 0 };
    else return route.fulfill({ status: 404, json: { error: "Unexpected request" } });
    await route.fulfill({ json: body });
  });
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Bring your match history" })).toBeVisible();
  await page.getByLabel("Match source", { exact: true }).selectOption("synthetic-a");
  await page.getByLabel("Player ID", { exact: true }).fill("ExamplePlayer-A");
  await page.getByRole("button", { name: "Find player" }).click();
  await expect(page.getByRole("button", { name: "Link selected player" })).toBeDisabled();
  await page.getByRole("radio").check();
  await expect(page.getByRole("button", { name: "Link selected player" })).toBeDisabled();
  await page.getByLabel("I consent to storing this player link", { exact: false }).check();
  await page.getByRole("button", { name: "Link selected player" }).click();
  await expect(page.getByText("Player linked. You can now import matches.")).toBeVisible();
  expect(linkBody).toEqual({ selection_token: "signed-fixture", processing_consent: true });
  await page.getByRole("button", { name: "Import matches", exact: true }).click();
  await expect(page.getByText("vs Synthetic Opponent")).toBeVisible();
  await expect(page.getByText("Gameplay evidence needed", { exact: true })).toBeVisible();
  await expect(page.getByText("Fictional demo", { exact: true })).toBeVisible();
  await expect(page.getByText("Build: Unknown", { exact: false })).toBeVisible();
  await page.screenshot({ path: "test-results/match-history-desktop.png", fullPage: true });
  await page.getByRole("button", { name: "Remove match", exact: true }).click();
  await expect(page.getByText("Its metadata will be deleted and imports for this player will stop.", { exact: false })).toBeVisible();
  await page.getByRole("button", { name: "Confirm removal" }).click();
  await expect(page.getByText("Match removed and player sync consent revoked.")).toBeVisible();
  await expect(page.getByText("vs Synthetic Opponent")).toHaveCount(0);
});

test("partial history, replay expiry and unknown build remain visible on mobile", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.route("**/api/**", route => {
    const path = new URL(route.request().url()).pathname;
    const body = path === "/api/session" ? { authenticated: true, csrf: "fixture", local_uploads: false }
      : path === "/api/overview" ? overview
      : path === "/api/match-providers" ? { providers }
      : path === "/api/player-identities" ? { identities: [identity] }
      : { ...blank, matches: [{ ...match, replays: [{ representation: "NATIVE_REPLAY", availability: "EXPIRED" }] }], total: 1,
        syncs: [{ id: "sync-1", provider: "synthetic-a", status: "COMPLETE", last_succeeded_at: "2026-09-19T00:00:00Z", coverage: { coverage: "PARTIAL", truncated: true, gaps: ["older history unavailable"] } }] };
    return route.fulfill({ json: body });
  });
  await page.goto("/");
  await expect(page.getByText("Partial history: some matches may be missing.")).toBeVisible();
  await expect(page.getByText("native replay: expired")).toBeVisible();
  await page.locator("#matches").screenshot({ path: "test-results/match-history-mobile.png" });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
});

test("disabled sources and empty lookup do not pretend to import", async ({ page }) => {
  await page.route("**/api/**", route => {
    const path = new URL(route.request().url()).pathname;
    const body = path === "/api/session" ? { authenticated: true, csrf: "fixture", local_uploads: false }
      : path === "/api/overview" ? overview
      : path === "/api/match-providers" ? { providers }
      : path === "/api/player-identities" ? { identities: [] }
      : path === "/api/player-candidates" ? { candidates: [] } : blank;
    return route.fulfill({ json: body });
  });
  await page.goto("/");
  await expect(page.getByRole("button", { name: "Find player" })).toBeDisabled();
  await expect(page.locator("#match-provider option[value=ewgf-public]")).toBeDisabled();
  await page.getByLabel("Match source", { exact: true }).selectOption("synthetic-a");
  await page.getByLabel("Player ID", { exact: true }).fill("missing-id");
  await page.getByRole("button", { name: "Find player" }).click();
  await expect(page.getByText("No player found for that exact ID.", { exact: false })).toBeVisible();
  await expect(page.getByRole("button", { name: "Link selected player" })).toHaveCount(0);
});

for (const reject of [false, true]) {
  test(`recording attachment ${reject ? "retains attribution errors" : "and removal preserve match history"}`, async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    let attached = false;
    await page.route("**/api/**", async route => {
      const path = new URL(route.request().url()).pathname;
      const method = route.request().method();
      let body: unknown;
      if (path === "/api/session") body = { authenticated: true, csrf: "fixture", local_uploads: true };
      else if (path === "/api/overview") body = overview;
      else if (path === "/api/match-providers") body = { providers };
      else if (path === "/api/player-identities") body = { identities: [identity] };
      else if (path === "/api/matches/match-1/recordings" && method === "POST") {
        expect(route.request().headers()["x-csrftoken"]).toBe("fixture");
        expect(route.request().headers()["content-type"]).toContain("multipart/form-data");
        expect(route.request().postData()).toContain('"metadata_revision":1');
        if (reject) return route.fulfill({ status: 400, json: { error: "Match metadata changed. Refresh and review the match again" } });
        attached = true; body = { match_id: match.id, status: "QUEUED", attribution_state: "PENDING_REVIEW" };
      } else if (path === "/api/assets/asset-1" && method === "DELETE") { attached = false; body = { status: "DELETED" }; }
      else if (path === "/api/matches") body = { ...blank, total: 1, matches: [{ ...match,
        can_attach_recording: !attached, can_delete_metadata: !attached,
        evidence_status: attached ? "ATTRIBUTION_PENDING" : "EVIDENCE_REQUIRED",
        recording_target: { metadata_revision: 1, player_namespace: "polaris", player_id: identity.value, player_slot: 1, opponent_ids: [{ namespace: "polaris", value: "Opponent-A" }] },
        recordings: attached ? [{ source_id: "source-1", asset_id: "asset-1", status: "QUEUED", attribution_state: "PENDING_REVIEW", source_hash: "a".repeat(64), can_manage: true }] : [],
      }] };
      else return route.fulfill({ status: 404, json: { error: "Unexpected request" } });
      await route.fulfill({ json: body });
    });
    await page.goto("/");
    await page.getByRole("button", { name: "Attach recording", exact: true }).click();
    await page.getByLabel("Gameplay recording", { exact: true }).setInputFiles({ name: "synthetic.mp4", mimeType: "video/mp4", buffer: Buffer.from("synthetic-upload-fixture") });
    await page.getByLabel("Recorded game build").fill("fixture");
    await page.getByLabel("Recording session ID").fill("session-1");
    await page.getByLabel("Recorded purpose").selectOption("ranked");
    await page.getByLabel("Recording content").selectOption("synthetic");
    await page.getByLabel("I checked both players", { exact: false }).check();
    await page.getByRole("button", { name: "Upload for attribution review" }).click();
    await expect(page.getByRole("region", { name: "Attach recording form" })).toBeVisible();
    expect(attached).toBe(false); // Browser enforces the separate processing-consent checkbox.
    await page.getByLabel("I consent to processing and storing this recording", { exact: false }).check();
    await page.locator(".recording-panel").screenshot({ path: `test-results/recording-form-${reject}.png` });
    await page.getByRole("button", { name: "Upload for attribution review" }).click();
    if (reject) {
      await expect(page.getByRole("region", { name: "Attach recording form" }).getByRole("alert")).toContainText("Match metadata changed");
      await expect(page.getByLabel("Recorded game build")).toHaveValue("fixture");
      return;
    }
    await expect(page.getByText("Recording attribution needs review", { exact: true })).toBeVisible();
    await expect(page.getByRole("button", { name: "Reprocess recording" })).toBeDisabled();
    await page.getByText("Operator review reference", { exact: true }).click();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
    await page.getByRole("button", { name: "Remove recording", exact: true }).click();
    await page.getByRole("button", { name: "Confirm recording removal" }).click();
    await expect(page.getByText("Recording removed. Imported match history retained.")).toBeVisible();
    await expect(page.getByText("vs Synthetic Opponent")).toBeVisible();
    await expect(page.getByRole("button", { name: "Attach recording", exact: true })).toBeVisible();
  });
}
