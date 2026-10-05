import { expect, test } from "@playwright/test";

const id = "00000000-0000-4000-8000-000000000001";
const measurement = { knowledge: "test/knowledge/1", game_build: "fixture", platform: "synthetic", situation: "test/situation/1", metric: "test/metric/1" };
const dataset = { id, title: "Reviewed fixture data", state: "COLLECTING", dataset_kind: "synthetic", measurement };
const slice = { sources: 1, players: 1, sessions: 1, tasks: 1, categories: { SUCCESS: 1, FAILURE: 0, NEAR_MISS: 0, UNCERTAIN: 0, TARGET_ABSENT: 0 }, missing_categories: ["FAILURE", "NEAR_MISS", "UNCERTAIN", "TARGET_ABSENT"], adjudicated: 0, structured_agreement_rate: 1, review_seconds: 120, timing: { independently_audited: 1, unaudited: 0, uncertainty_max_us: 100, reviewer_start_gap_max_us: 100 }, detector_versions: [], recognition: null };
const qa = { splits: { "held-out": slice }, representative_coverage: false, scientific_gate: "NOT_RUN", release_approval: false, timing_interpretation: "Reviewer agreement does not establish real frame accuracy." };
const snapshot = { id: "snapshot-1", sequence: 1, content_hash: "a".repeat(64), valid: true, reason: "", qa };
const observability = { content_hash: "b".repeat(64), data: { snapshot_hash: snapshot.content_hash, dataset_kind: "synthetic", scientific_gate: "NOT_RUN", proposed_threshold_result: "INSUFFICIENT_EVIDENCE", blockers: ["SYNTHETIC_DATA", "INSUFFICIENT_CAPTURES", "EXPERT_QUALIFICATION_NOT_VERIFIED"], totals: { captures: 1, excluded_non_ranked_captures: 0, players: 1, sessions: 1, critical_windows: 1, resolvable_windows: 0, unresolved_windows: 1, resolvable_rate: 0, timing_unaudited_windows: 1, review_seconds: 120, unresolved_reasons: { UNKNOWN_OUTCOME: 1 } }, interpretation: "Timing completeness and reviewer agreement do not prove frame accuracy or automatic recognition." } };

test("collection pins reviewed knowledge, retries sealing and exports a current snapshot", async ({ page }) => {
  let created = false; let frozen = false; let sealed = false; let linked = false;
  const sealBodies: object[] = [];
  await page.route("**/api/session", r => r.fulfill({ json: { authenticated: true, operator: true, csrf: "dataset-csrf" } }));
  await page.route("**/api/datasets", r => {
    if (r.request().method() === "POST") { expect(r.request().headers()["x-csrftoken"]).toBe("dataset-csrf"); expect(r.request().postDataJSON()).toMatchObject({ title: "Reviewed fixture data", dataset_kind: "synthetic", knowledge_key: measurement.knowledge }); created = true; return r.fulfill({ json: dataset }); }
    return r.fulfill({ json: { datasets: created ? [dataset] : [], releases: [{ key: measurement.knowledge, game_build: "fixture", platform: "synthetic", dataset_kind: "synthetic" }] } });
  });
  await page.route(`**/api/datasets/${id}`, r => r.fulfill({ json: { ...dataset, state: frozen ? "FROZEN" : "COLLECTING", source_count: 1, studies: linked ? [{ id, title: "Independent labels", state: frozen ? "FROZEN" : "COLLECTING", revision: 1 }] : [], snapshots: sealed ? [snapshot] : [] } }));
  await page.route(`**/api/datasets/${id}/study`, r => { linked = true; return r.fulfill({ json: { study_id: id } }); });
  await page.route(`**/api/datasets/${id}/freeze`, r => { frozen = true; return r.fulfill({ json: { frozen: true } }); });
  await page.route(`**/api/datasets/${id}/seal`, r => { sealBodies.push(r.request().postDataJSON()); if (sealBodies.length === 1) return r.fulfill({ status: 503, json: { error: "Temporary transport failure. Retry." } }); sealed = true; return r.fulfill({ json: { id: snapshot.id } }); });
  await page.route(`**/api/datasets/${id}/snapshots/${snapshot.id}`, r => r.fulfill({ json: { content_hash: snapshot.content_hash, data: { schema_version: "dataset-snapshot/1", automatic_publication: false } } }));
  await page.goto("/datasets");
  await page.getByLabel("Dataset title").fill("Reviewed fixture data");
  await page.getByRole("button", { name: "Create synthetic dataset" }).click();
  await expect(page.getByRole("heading", { name: dataset.title, exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "Freeze dataset inputs" })).toBeDisabled();
  await page.getByLabel("Review study title").fill("Independent labels");
  await page.getByRole("button", { name: "Create linked review study" }).click();
  await expect(page.getByRole("link", { name: "Independent labels" })).toHaveAttribute("href", `/pilots#study=${id}`);
  await page.getByRole("button", { name: "Freeze dataset inputs" }).click();
  await page.getByRole("button", { name: "Seal reviewed snapshot" }).click();
  await expect(page.getByRole("main").getByRole("alert")).toContainText("Retry");
  await page.getByRole("button", { name: "Seal reviewed snapshot" }).click();
  await expect(page.getByText("Scientific gate NOT_RUN. Coverage checklist incomplete.")).toBeVisible();
  expect(sealBodies[0]).toEqual(sealBodies[1]);
  const download = page.waitForEvent("download");
  await page.getByRole("button", { name: "Download snapshot 1" }).click();
  expect((await download).suggestedFilename()).toBe("dojopulse-dataset-1.json");
  await expect(page.getByRole("status")).toContainText("current permissions require separate checks");
});

test("invalidated snapshots expose no QA or download and closure requires a deliberate action", async ({ page }) => {
  let closed = false;
  await page.route("**/api/session", r => r.fulfill({ json: { authenticated: true, operator: true, csrf: "test" } }));
  await page.route("**/api/datasets", r => r.fulfill({ json: { datasets: closed ? [] : [dataset], releases: [] } }));
  await page.route(`**/api/datasets/${id}`, r => {
    if (r.request().method() === "DELETE") { closed = true; return r.fulfill({ json: { closed: true } }); }
    return r.fulfill({ json: { ...dataset, state: "FROZEN", source_count: 0, studies: [], snapshots: [{ ...snapshot, valid: false, reason: "SOURCE_WITHDRAWN", qa: null }] } });
  });
  await page.goto("/datasets"); await page.getByLabel("Selected dataset").selectOption(id);
  await expect(page.getByText("Private data erased or withheld: source withdrawn.")).toBeVisible();
  await expect(page.getByRole("button", { name: "Download snapshot 1" })).toHaveCount(0);
  await page.getByRole("button", { name: "Close collection", exact: true }).click(); expect(closed).toBe(false);
  await page.getByRole("button", { name: "Confirm collection closure" }).click();
  await expect(page.getByRole("status")).toContainText("private dataset evidence erased"); expect(closed).toBe(true);
});

test("dataset review preserves unknown frame audits and selects the linked study", async ({ page }) => {
  let body: Record<string, unknown> = {};
  const study = { id, title: "Dataset review", dataset_kind: "synthetic", state: "COLLECTING", role: "REVIEWER", revision: 1, protocol_digest: "b".repeat(64), protocol: { dataset_id: id, consent: "Dataset consent", target: measurement.situation } };
  await page.route("**/api/session", r => r.fulfill({ json: { authenticated: true, operator: false, csrf: "test" } }));
  await page.route("**/api/pilots", r => r.fulfill({ json: { studies: [study] } }));
  await page.route(`**/api/pilots/${id}`, r => r.fulfill({ json: { ...study, members: [], sessions: [], captures: [], reports: [], available_sources: [], tasks: [{ id: "task-1", kind: "TARGET", start_us: 0, end_us: 1000000, state: "PENDING", submitted: false, can_review: true, media_url: "/unavailable.mp4", final_label: null, reviews: [] }] } }));
  await page.route(`**/api/pilots/${id}/review`, r => { body = r.request().postDataJSON(); return r.fulfill({ json: { recorded: true } }); });
  await page.goto(`/pilots#study=${id}`);
  await expect(page.getByLabel("Selected study")).toHaveValue(id); expect(page.url()).not.toContain("#study");
  await page.getByLabel("Timestamp uncertainty, microseconds").fill("20000");
  await page.getByLabel("Measured review seconds").fill("30");
  await page.getByRole("button", { name: "Submit independent review" }).click();
  expect(body).toMatchObject({ label: { timing: { start_us: null, end_us: null, frame_duration_us: null } } });
});

test("mobile snapshot remains readable and explains missing adverse evidence", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.route("**/api/session", r => r.fulfill({ json: { authenticated: true, operator: true, csrf: "test" } }));
  await page.route("**/api/datasets", r => r.fulfill({ json: { datasets: [dataset], releases: [] } }));
  await page.route(`**/api/datasets/${id}`, r => r.fulfill({ json: { ...dataset, state: "FROZEN", source_count: 1, studies: [], snapshots: [snapshot] } }));
  await page.route(`**/api/datasets/${id}/snapshots/${snapshot.id}/observability`, r => r.fulfill({ json: observability }));
  await page.goto("/datasets"); await page.getByLabel("Selected dataset").selectOption(id);
  await expect(page.getByText("Missing categories: failure, near miss, uncertain, target absent.")).toBeVisible();
  await expect(page.getByText(qa.timing_interpretation)).toBeVisible();
  const download = page.waitForEvent("download");
  await page.getByRole("button", { name: "Assess observability 1" }).click();
  expect((await download).suggestedFilename()).toBe("dojopulse-observability-1.json");
  await expect(page.getByRole("region", { name: "Observability for snapshot 1" })).toContainText("1 ranked captures of 20 required");
  await expect(page.getByText("G1 NOT_RUN. insufficient evidence.")).toBeVisible();
  await expect(page.getByText("Remaining checks: synthetic data; insufficient captures; expert qualification not verified.")).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.getByRole("button", { name: "Download snapshot 1" }).focus();
  await expect(page.getByRole("button", { name: "Download snapshot 1" })).toBeFocused();
  await page.screenshot({ path: "test-results/m08-datasets-mobile.png", fullPage: true });
});

test("zero-window report preserves unknown rate and expired evidence removes the assessment", async ({ page }) => {
  let revoked = false;
  await page.route("**/api/session", r => r.fulfill({ json: { authenticated: true, operator: true, csrf: "test" } }));
  await page.route("**/api/datasets", r => r.fulfill({ json: { datasets: [dataset], releases: [] } }));
  await page.route(`**/api/datasets/${id}`, r => r.fulfill({ json: { ...dataset, state: "FROZEN", source_count: 1, studies: [], snapshots: [revoked ? { ...snapshot, valid: false, reason: "SOURCE_EXPIRED", qa: null } : snapshot] } }));
  await page.route(`**/api/datasets/${id}/snapshots/${snapshot.id}/observability`, r => r.fulfill(revoked ? { status: 410, json: { error: "Source evidence expired. Report withheld." } } : { json: { ...observability, data: { ...observability.data, totals: { ...observability.data.totals, critical_windows: 0, unresolved_windows: 0, resolvable_rate: null } } } }));
  await page.goto("/datasets"); await page.getByLabel("Selected dataset").selectOption(id);
  await page.getByRole("button", { name: "Assess observability 1" }).focus();
  await page.keyboard.press("Enter");
  await expect(page.getByRole("region", { name: "Observability for snapshot 1" })).toContainText("Resolvable rate: unknown.");
  await expect(page.getByRole("button", { name: "Assess observability 1" })).toBeEnabled();
  revoked = true;
  await page.getByRole("button", { name: "Assess observability 1" }).click();
  await expect(page.getByRole("main").getByRole("alert")).toContainText("Report withheld");
  await expect(page.getByRole("region", { name: "Observability for snapshot 1" })).toHaveCount(0);
  await page.getByRole("button", { name: "Refresh datasets" }).click();
  await expect(page.getByRole("button", { name: "Assess observability 1" })).toHaveCount(0);
});

test("nonoperators cannot open dataset management", async ({ page }) => {
  await page.route("**/api/session", r => r.fulfill({ json: { authenticated: true, operator: false } }));
  await page.goto("/datasets");
  await expect(page.getByRole("main").getByRole("alert")).toContainText("local operator account");
  await expect(page.getByRole("button", { name: "Create synthetic dataset" })).toHaveCount(0);
});
