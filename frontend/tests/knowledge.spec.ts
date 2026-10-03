import { expect, test } from "@playwright/test";

const id = "00000000-0000-4000-8000-000000000001";
const asset = "00000000-0000-4000-8000-000000000002";
const match = "00000000-0000-4000-8000-000000000003";
const proposal = { id, key: "test/build/1", kind: "build", build_key: "fixture", dataset_kind: "synthetic", payload: { game_build: "fixture", platform: "synthetic", overlays: ["build"] }, provenance: { reference: "owned/1" }, hash: "a".repeat(64), state: "OPEN", reason: "", author: true, can_review: false, intact: true, effective: false, published_key: null, reviews: [] as { decision: string; note: string; own: boolean }[], review_visibility: "Submitted review receipts", sources: [{ asset_id: asset, source_sha256: "b".repeat(64), duration_seconds: 60, media_url: `/api/knowledge/${id}/media/${asset}` }] };
const data = { real_publication_approved: false, proposals: [proposal], builds: [{ key: "fixture", platform: "synthetic", verified: false }], sources: [{ id: asset, source_sha256: "b".repeat(64), metadata: { game_build: "fixture", platform: "synthetic" } }], definitions: [{ key: "test/compatibility/1", kind: "compatibility", hash: "c".repeat(64) }], reanalyses: [] };

test("knowledge tools require an operator session", async ({ page }) => {
  await page.route("**/api/session", r => r.fulfill({ json: { authenticated: true, operator: false } }));
  await page.goto("/knowledge");
  await expect(page.getByRole("main").getByRole("alert")).toContainText("Operator access required");
  await expect(page.getByRole("button", { name: "Publish new immutable version" })).toHaveCount(0);
});

test("independent review is sealed before other decisions are shown", async ({ page }) => {
  const bodies: Record<string, unknown>[] = [];
  let reviewed = false;
  await page.route("**/api/session", r => r.fulfill({ json: { authenticated: true, operator: true, csrf: "knowledge-csrf" } }));
  await page.route("**/api/knowledge", r => r.fulfill({ json: { ...data, proposals: [{ ...proposal, author: false, can_review: !reviewed, reviews: reviewed ? [{ decision: "APPROVE", note: "Independent fixture review", own: true }] : [], review_visibility: reviewed ? "Submitted review receipts" : "Sealed until you submit your independent decision" }] } }));
  await page.route(`**/api/knowledge/${id}/review`, r => {
    bodies.push(r.request().postDataJSON()); expect(r.request().headers()["x-csrftoken"]).toBe("knowledge-csrf"); reviewed = true; return r.fulfill({ json: {} });
  });
  await page.goto("/knowledge");
  await page.getByLabel("Selected proposal").selectOption(id);
  await expect(page.getByText("Sealed until you submit your independent decision")).toBeVisible();
  await page.getByLabel("Review decision").selectOption("APPROVE");
  await page.getByLabel("Evidence review note").fill("Independent fixture review");
  await page.getByLabel("I independently reviewed").check();
  await page.getByRole("button", { name: "Seal independent review" }).click();
  await expect(page.getByRole("status")).toContainText("Independent review sealed");
  expect(bodies[0]).toMatchObject({ decision: "APPROVE", note: "Independent fixture review", confirm_reviewed: true, proposal_hash: "a".repeat(64) });
  await expect(page.getByRole("button", { name: "Publish new immutable version" })).toHaveCount(0);
});

test("proposal retries preserve request identity and mobile layout", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  const bodies: Record<string, unknown>[] = [];
  await page.route("**/api/session", r => r.fulfill({ json: { authenticated: true, operator: true, csrf: "test" } }));
  await page.route("**/api/knowledge", r => {
    if (r.request().method() === "GET") return r.fulfill({ json: data });
    bodies.push(r.request().postDataJSON()); return r.fulfill({ status: bodies.length === 1 ? 503 : 201, json: bodies.length === 1 ? { error: "Temporary failure. Retry." } : { id } });
  });
  await page.goto("/knowledge");
  await page.getByText("Prepare a new evidence-pinned version").click();
  await page.getByLabel("New version key").fill("test/build/1");
  await page.getByLabel("Canonical game build").selectOption("fixture");
  await page.getByLabel("Owned validated sources").selectOption(asset);
  await page.getByLabel("First independent operator account ID").fill("2");
  await page.getByLabel("Second independent operator account ID").fill("3");
  await page.getByLabel("Offline source / permission reference code").fill("owned/1");
  await page.getByLabel("I permit these two assigned reviewers").check();
  await page.getByLabel("I have permission to publish").check();
  await page.getByRole("button", { name: "Seal proposal" }).click();
  await expect(page.getByRole("main").getByRole("alert")).toContainText("Retry");
  await page.getByRole("button", { name: "Seal proposal" }).click();
  await expect(page.getByRole("status")).toContainText("Proposal sealed");
  expect(bodies[0]).toEqual(bodies[1]);
  expect(bodies[0]).toMatchObject({ dataset_kind: "synthetic", reviewer_one: 2, reviewer_two: 3, asset_ids: [asset], provenance: { share_with_reviewers: true, publish_game_facts: true } });
  await page.getByLabel("Selected proposal").selectOption(id);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.screenshot({ path: "test-results/m07-knowledge-mobile.png", fullPage: true });
});

test("publication requires both approvals and withdrawal is confirmed", async ({ page }) => {
  let two = false; let published = false; let withdrawn = false;
  const commands: string[] = [];
  await page.route("**/api/session", r => r.fulfill({ json: { authenticated: true, operator: true, csrf: "test" } }));
  await page.route("**/api/knowledge", r => r.fulfill({ json: { ...data, proposals: [{ ...proposal, state: withdrawn ? "WITHDRAWN" : published ? "PUBLISHED" : "OPEN", reviews: Array.from({ length: two ? 2 : 1 }, () => ({ decision: "APPROVE", note: "Synthetic source reviewed", own: false })) }] } }));
  await page.route(`**/api/knowledge/${id}/*`, r => { commands.push(r.request().url().split("/").at(-1)!); published = true; if (commands.at(-1) === "withdraw") withdrawn = true; return r.fulfill({ json: {} }); });
  await page.goto("/knowledge"); await page.getByLabel("Selected proposal").selectOption(id);
  await expect(page.getByRole("button", { name: "Publish new immutable version" })).toBeDisabled();
  two = true; await page.getByRole("button", { name: "Refresh queue" }).click();
  await page.getByRole("button", { name: "Publish new immutable version" }).click();
  await expect(page.getByRole("status")).toContainText("No gameplay facts were created");
  await page.getByRole("button", { name: "Withdraw release and dependent evidence" }).click();
  expect(commands).toEqual(["publish"]);
  await page.getByRole("button", { name: "Confirm withdraw" }).click();
  await expect(page.getByRole("status")).toContainText("Release grant updated");
  expect(commands).toEqual(["publish", "withdraw"]);
});

test("patch preview abstains on incompatible builds and queues explicit review", async ({ page }) => {
  const queued: object[] = [];
  await page.route("**/api/session", r => r.fulfill({ json: { authenticated: true, operator: true, csrf: "test" } }));
  await page.route("**/api/knowledge", r => r.fulfill({ json: data }));
  await page.route("**/api/knowledge/reanalysis?*", r => r.fulfill({ json: { matches: [{ id: match, game_build: "fixture", dataset_kind: "synthetic", state: "READY" }, { id, game_build: "old-build", dataset_kind: "synthetic", state: "CAPTURE_BUILD_INCOMPATIBLE" }], note: "Original builds and frozen plans remain unchanged." } }));
  await page.route("**/api/knowledge/reanalysis", r => { queued.push(r.request().postDataJSON()); return r.fulfill({ status: 202, json: { status: "QUEUED", review_required: true } }); });
  await page.goto("/knowledge");
  await page.getByLabel("Published compatibility mapping").selectOption("test/compatibility/1");
  await page.getByRole("button", { name: "Preview affected matches" }).click();
  await expect(page.getByText("CAPTURE BUILD INCOMPATIBLE", { exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "Queue reviewed reanalysis" })).toHaveCount(1);
  await page.getByRole("button", { name: "Queue reviewed reanalysis" }).click();
  await expect(page.getByRole("status")).toContainText("Independent gameplay review is required");
  expect(queued[0]).toMatchObject({ match_id: match, mapping_key: "test/compatibility/1" });
});
