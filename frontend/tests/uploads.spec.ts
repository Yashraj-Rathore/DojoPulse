import { test, expect, type Page, type Route } from "@playwright/test";
import { createHash } from "node:crypto";
import { mockWorkspace } from "./workspace-fixtures";

const bytes = Buffer.alloc(600000, 7);
const file = { name: "fixture.mp4", mimeType: "video/mp4", buffer: bytes };
const match = { id: "fixture-match", played_at: "2026-09-01T01:00:00Z", mode: "ranked", game_build: "fixture", dataset_kind: "synthetic", opponent: "Fixture opponent", character: "jin", opponent_character: "jin", result: "WIN", metadata_state: "METADATA_IMPORTED", evidence_status: "EVIDENCE_REQUIRED", can_attach_recording: true, can_delete_metadata: true, recordings: [], replays: [], recording_target: { metadata_revision: 1, player_namespace: "polaris", player_id: "Player-A", player_slot: 1, opponent_ids: [{ namespace: "polaris", value: "Player-B" }] } };

async function mount(page: Page, upload: (route: Route) => Promise<void>) {
  await page.route("**/api/**", async route => {
    const path = new URL(route.request().url()).pathname;
    if (path.startsWith("/api/upload-sessions")) return upload(route);
    const body = path === "/api/session" ? { authenticated: true, csrf: "fixture", local_uploads: true }
      : path === "/api/overview" ? { runs: [], events: [], drills: [], assignments: [], plans: [], evaluations: [], practice: [] }
      : path === "/api/match-providers" ? { providers: [] }
      : path === "/api/player-identities" ? { identities: [] }
      : { matches: [match], total: 1, next_offset: null, syncs: [] };
    await route.fulfill({ json: body });
  });
  await mockWorkspace(page); await page.goto("/");
}
async function fill(page: Page) {
  await page.getByRole("button", { name: "Attach recording", exact: true }).click();
  await page.getByLabel("Gameplay recording", { exact: true }).setInputFiles(file);
  await page.getByLabel("Recording session ID").fill("fixture-session");
  await page.getByRole("region", { name: "Attach recording form" }).getByLabel("Recording content").selectOption("synthetic");
  for (const label of ["I checked both players", "I consent to processing and storing this recording", "This is one continuous"]) await page.getByRole("region", { name: "Attach recording form" }).getByLabel(label, { exact: false }).check();
}

for (const refresh of [false, true]) {
  test(`resumes confirmed bytes after interrupted transfer${refresh ? " and refresh" : ""}`, async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    let received = 0, lost = false, state = "UPLOADING", requestId = "";
    const offsets: number[] = [];
    const transfer = () => ({ id: "fixture-upload", state, received_bytes: received, bytes: bytes.length, storage_provider: "LOCAL", chunk_bytes: 262144 });
    await mount(page, async route => {
      const method = route.request().method(), path = new URL(route.request().url()).pathname;
      if (path === "/api/upload-sessions") {
        const body = route.request().postDataJSON();
        expect(body.sha256).toBe(createHash("sha256").update(bytes).digest("hex"));
        expect(body.md5).toBe(createHash("md5").update(bytes).digest("base64"));
        if (requestId) expect(body.request_id).toBe(requestId); else requestId = body.request_id;
      } else if (path.endsWith("/chunk")) {
        const offset = Number(route.request().headers()["upload-offset"]); offsets.push(offset);
        expect(offset).toBe(received); received += route.request().postDataBuffer()!.length;
        if (!lost) { lost = true; return route.abort("failed"); }
      } else if (path.endsWith("/complete")) state = "VERIFYING";
      else if (method === "DELETE") state = "CANCELLED";
      await route.fulfill({ json: transfer() });
    });
    await fill(page);
    await page.getByRole("button", { name: "Upload for attribution review" }).click();
    await expect.poll(() => lost).toBe(true);
    await page.getByRole("button", { name: "Pause upload" }).click();
    await expect(page.getByText("Upload paused", { exact: true })).toBeVisible();
    expect(await page.evaluate(() => Object.keys(JSON.parse(sessionStorage.getItem("dojopulse-pending-upload")!)).sort())).toEqual(["fingerprint", "id", "requestId"]);
    if (refresh) { await page.reload(); await fill(page); }
    await page.getByRole("button", { name: refresh ? "Upload for attribution review" : "Resume upload" }).click();
    await expect(page.getByText("Checking recording integrity", { exact: true })).toBeVisible();
    expect(received).toBe(bytes.length); expect(offsets).toEqual([0, 262144, 524288]);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
    await page.locator(".recording-panel").screenshot({ path: `test-results/m06-verification-${refresh}.png` });
    await page.getByRole("button", { name: "Pause upload" }).click();
    await page.getByRole("button", { name: "Cancel upload", exact: true }).click();
    await expect(page.getByText("Upload cancelled", { exact: true })).toBeVisible();
    expect(await page.evaluate(() => sessionStorage.getItem("dojopulse-pending-upload"))).toBeNull();
  });
}

test("failed cleanup retains receipt and retry clears stale account receipt", async ({ page }) => {
  let received = 0, failed = false, cancels = 0;
  await mount(page, async route => {
    const path = new URL(route.request().url()).pathname;
    if (route.request().method() === "DELETE") {
      cancels++;
      return route.fulfill({ status: cancels === 1 ? 503 : 404, json: { error: cancels === 1 ? "Cleanup temporarily unavailable" : "Upload unavailable" } });
    }
    if (path.endsWith("/chunk")) { received = 262144; failed = true; return route.abort("failed"); }
    await route.fulfill({ json: { id: "fixture-upload", state: "UPLOADING", received_bytes: received, bytes: bytes.length, storage_provider: "LOCAL", chunk_bytes: 262144 } });
  });
  await fill(page); await page.getByRole("button", { name: "Upload for attribution review" }).click();
  await expect.poll(() => failed).toBe(true); await page.getByRole("button", { name: "Pause upload" }).click();
  await page.getByRole("button", { name: "Cancel upload", exact: true }).click();
  await expect(page.getByRole("region", { name: "Upload progress" }).getByRole("alert")).toContainText("Cleanup temporarily unavailable");
  expect(await page.evaluate(() => sessionStorage.getItem("dojopulse-pending-upload"))).not.toBeNull();
  await page.getByRole("button", { name: "Cancel upload", exact: true }).click();
  await expect(page.getByText("Upload cancelled", { exact: true })).toBeVisible();
  expect(await page.evaluate(() => sessionStorage.getItem("dojopulse-pending-upload"))).toBeNull();
});

test("direct GCS chunks omit app credentials and wait for verified completion", async ({ page }) => {
  let received = 0, verifying = false;
  const capability = "https://storage.googleapis.com/upload/storage/v1/b/fixture-bucket/o?uploadType=resumable&upload_id=fixture-secret";
  await page.route("https://storage.googleapis.com/**", async route => {
    const headers = route.request().headers();
    expect(headers["x-csrftoken"]).toBeUndefined(); expect(headers["cookie"]).toBeUndefined(); expect(headers["authorization"]).toBeUndefined();
    expect(headers["content-range"]).toBe(`bytes ${received}-${Math.min(bytes.length, received + 262144) - 1}/${bytes.length}`);
    received += route.request().postDataBuffer()!.length;
    await route.fulfill({ status: received === bytes.length ? 200 : 308 });
  });
  await mount(page, async route => {
    if (new URL(route.request().url()).pathname.endsWith("/complete")) verifying = true;
    await route.fulfill({ json: { id: "fixture-upload", state: verifying ? "VERIFYING" : "UPLOADING", received_bytes: received, bytes: bytes.length, storage_provider: "GCS", chunk_bytes: 262144, upload_url: capability } });
  });
  await fill(page); await page.getByRole("button", { name: "Upload for attribution review" }).click();
  await expect(page.getByText("Checking recording integrity", { exact: true })).toBeVisible();
  expect(received).toBe(bytes.length);
  expect(await page.evaluate(() => sessionStorage.getItem("dojopulse-pending-upload"))).not.toContain("fixture-secret");
  await page.getByRole("button", { name: "Pause upload" }).click();
});
