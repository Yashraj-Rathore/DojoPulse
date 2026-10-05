import { expect, test } from "@playwright/test";

const id = "00000000-0000-4000-8000-000000000009";
const receiptId = "00000000-0000-4000-8000-000000000019";
const version = { id, version: "fixture-detector/1", dataset_id: id, state: "REGISTERED", role: "OWNER", content_hash: "a".repeat(64), disabled_reason: "" };
const report = { metrics: { slices: { SUCCESS: { precision: 1, recall: 1, tp: 1, fp: 0, fn: 0 }, FAILURE: { precision: null, recall: null, tp: 0, fp: 0, fn: 0 } }, abstention_rate: 0, observable_outcome_coverage: 1, timestamp_error_us: { median: 0, p95: 0 } }, negative_controls: { sources: 0, false_positives: 0 }, stop_reasons: [], software_pass: true, scientific_gate: "NOT_RUN", interpretation: "Software fixtures do not establish detector accuracy on real video." };
const receipt = { id: receiptId, snapshot_id: id, content_hash: "b".repeat(64), input_hash: "c".repeat(64), valid: true, reason: "", reviewed: false, approval_count: 0, report };

test("fixed version registration retries identical payload and requires exact approvals before activation", async ({ page }) => {
  let created = false; let ran = false; let activated = false; let approvals = 0; const bodies: object[] = [];
  await page.route("**/api/session", r => r.fulfill({ json: { authenticated: true, operator: true, csrf: "recognition-csrf" } }));
  await page.route("**/api/recognition", r => {
    if (r.request().method() === "POST") {
      expect(r.request().headers()["x-csrftoken"]).toBe("recognition-csrf"); bodies.push(r.request().postDataJSON());
      if (bodies.length === 1) return r.fulfill({ status: 503, json: { error: "Temporary transport failure. Retry." } });
      created = true; return r.fulfill({ json: version });
    }
    return r.fulfill({ json: { versions: created ? [version] : [], engine: "observation-rules/1", artifact_hash: "d".repeat(64) } });
  });
  await page.route(`**/api/recognition/${id}`, r => r.fulfill({ json: { ...version, state: activated ? "ACTIVE" : "REGISTERED", manifest: { version: version.version }, runs: ran ? [{ ...receipt, approval_count: approvals }] : [] } }));
  await page.route(`**/api/recognition/${id}/run`, r => { ran = true; return r.fulfill({ json: { id: receiptId } }); });
  await page.route(`**/api/recognition/${id}/activate`, r => { expect(r.request().postDataJSON()).toEqual({ run_id: receiptId }); activated = true; return r.fulfill({ json: {} }); });
  await page.route(`**/api/recognition/${id}/runs/${receiptId}`, r => r.fulfill({ json: { schema_version: "recognition-reproduction/1", report } }));
  await page.goto("/recognition");
  await page.getByLabel("Dataset ID", { exact: true }).fill(id);
  await page.getByLabel("Detector manifest JSON").fill(JSON.stringify({ version: version.version }));
  await page.getByLabel("First independent operator ID").fill("2"); await page.getByLabel("Second independent operator ID").fill("3");
  await page.getByRole("button", { name: "Register synthetic detector" }).click();
  await expect(page.getByRole("main").getByRole("alert")).toContainText("Retry");
  await page.getByRole("button", { name: "Register synthetic detector" }).click(); expect(bodies[0]).toEqual(bodies[1]);
  await expect(page.getByRole("heading", { name: version.version, exact: true })).toBeVisible();
  await page.getByLabel("Reviewed snapshot ID").fill(id); await page.getByLabel("Observation batch JSON").fill('{"sources":[]}');
  await page.getByRole("button", { name: "Run held-out software benchmark" }).click();
  await expect(page.getByRole("button", { name: "Activate reviewed synthetic version" })).toBeDisabled();
  const download = page.waitForEvent("download"); await page.getByRole("button", { name: "Download benchmark report" }).click();
  expect((await download).suggestedFilename()).toBe("dojopulse-recognition-report.json");
  approvals = 2; await page.reload(); await page.getByLabel("Selected detector").selectOption(id);
  await page.getByRole("button", { name: "Activate reviewed synthetic version" }).click();
  await expect(page.getByRole("status")).toContainText("Gameplay publication still requires independent human review");
});

test("independent reviewer sees aggregate receipt and submits the pinned hash", async ({ page }) => {
  let reviewed = false; let body: object = {};
  await page.route("**/api/session", r => r.fulfill({ json: { authenticated: true, operator: true, csrf: "test" } }));
  await page.route("**/api/recognition", r => r.fulfill({ json: { versions: [{ ...version, role: "REVIEWER" }], engine: "observation-rules/1", artifact_hash: "d".repeat(64) } }));
  await page.route(`**/api/recognition/${id}`, r => r.fulfill({ json: { ...version, role: "REVIEWER", manifest: {}, runs: [{ ...receipt, reviewed }] } }));
  await page.route(`**/api/recognition/${id}/review`, r => { body = r.request().postDataJSON(); reviewed = true; return r.fulfill({ json: {} }); });
  await page.goto("/recognition"); await page.getByLabel("Selected detector").selectOption(id);
  await expect(page.getByRole("button", { name: "Run held-out software benchmark" })).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Download benchmark report" })).toHaveCount(0);
  await page.getByRole("button", { name: "Approve software receipt" }).click();
  expect(body).toMatchObject({ run_id: receiptId, report_hash: receipt.content_hash, decision: "APPROVE" });
  await expect(page.getByRole("button", { name: "Reject software receipt" })).toBeDisabled();
});

test("mobile drift failure shows separate slices, fallback and stop control", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 }); let stopped = false;
  await page.route("**/api/session", r => r.fulfill({ json: { authenticated: true, operator: true, csrf: "test" } }));
  await page.route("**/api/recognition", r => r.fulfill({ json: { versions: [version], engine: "observation-rules/1", artifact_hash: "d".repeat(64) } }));
  await page.route(`**/api/recognition/${id}`, r => r.fulfill({ json: { ...version, state: stopped ? "DISABLED" : "ACTIVE", disabled_reason: stopped ? "OPERATOR_STOP" : "", manifest: { version: "x".repeat(150) }, runs: [{ ...receipt, report: { ...report, software_pass: false, metrics: { ...report.metrics, abstention_rate: 1 }, stop_reasons: ["ABSTENTION_STOP"] } }] } }));
  await page.route(`**/api/recognition/${id}/disable`, r => { stopped = true; return r.fulfill({ json: {} }); });
  await page.goto("/recognition"); await page.getByLabel("Selected detector").selectOption(id);
  await expect(page.getByText("Stop reasons: abstention stop.")).toBeVisible();
  await expect(page.getByRole("button", { name: "Activate reviewed synthetic version" })).toBeDisabled();
  await expect(page.getByRole("link", { name: "Open independent media review fallback" })).toHaveAttribute("href", "/pilots");
  await page.getByRole("button", { name: "Stop candidate version" }).focus();
  await expect(page.getByRole("button", { name: "Stop candidate version" })).toBeFocused();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.screenshot({ path: "test-results/m09-recognition-mobile.png", fullPage: true });
  await page.getByRole("button", { name: "Stop candidate version" }).click(); await expect(page.getByRole("status")).toContainText("stopped");
});

test("invalidated evidence and nonoperators cannot use recognition controls", async ({ page }) => {
  await page.route("**/api/session", r => r.fulfill({ json: { authenticated: true, operator: true, csrf: "test" } }));
  await page.route("**/api/recognition", r => r.fulfill({ json: { versions: [version], engine: "observation-rules/1", artifact_hash: "d".repeat(64) } }));
  await page.route(`**/api/recognition/${id}`, r => r.fulfill({ json: { ...version, state: "INVALIDATED", manifest: null, runs: [] } }));
  await page.goto("/recognition"); await page.getByLabel("Selected detector").selectOption(id);
  await expect(page.getByText("Private recognition inputs and reports have been erased or withheld. Register a new version using currently authorized data.")).toBeVisible();
  await expect(page.getByRole("button", { name: "Run held-out software benchmark" })).toHaveCount(0);
  await page.route("**/api/session", r => r.fulfill({ json: { authenticated: true, operator: false } }));
  await page.reload(); await expect(page.getByRole("main").getByRole("alert")).toContainText("local operator account");
  await expect(page.getByRole("button", { name: "Register synthetic detector" })).toHaveCount(0);
});
