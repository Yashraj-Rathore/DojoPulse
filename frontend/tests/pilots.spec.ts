import { expect, test } from "@playwright/test";

const id = "00000000-0000-4000-8000-000000000001";
const study = { id, title: "Synthetic pilot", dataset_kind: "synthetic", state: "COLLECTING", role: "PARTICIPANT", revision: 1, protocol_digest: "a".repeat(64), protocol: { consent: "Adult study consent. Assigned reviewers can see registered sources. Training is separate.", target: "tekken8.jin-vs-jin.blocked-uf4/v1", baseline_end: "2026-10-09T20:00:00Z", followup_start: "2026-10-11T20:00:00Z", ends_at: "2026-11-08T20:00:00Z", audit_ends_at: "2026-11-15T20:00:00Z" } };
const detail = { ...study, pseudonym: id, members: [], sessions: [], captures: [], tasks: [], reports: [], available_sources: [] };

test("invitation fragment is scrubbed and adult study consent is explicit", async ({ page }) => {
  const bodies: object[] = [];
  await page.route("**/api/session", r => r.fulfill({ json: { authenticated: true, operator: false, csrf: "pilot-csrf" } }));
  await page.route("**/api/pilots", r => r.fulfill({ json: { studies: [] } }));
  await page.route("**/api/pilot-invitation", r => { expect(r.request().postDataJSON()).toEqual({ token: "secret-invite" }); return r.fulfill({ json: study }); });
  await page.route("**/api/pilot-join", r => { expect(r.request().headers()["x-csrftoken"]).toBe("pilot-csrf"); bodies.push(r.request().postDataJSON()); return r.fulfill({ json: { study_id: id } }); });
  await page.goto("/pilots#invite=secret-invite");
  await expect(page.getByLabel("Invitation token")).toHaveValue("secret-invite");
  expect(page.url()).not.toContain("secret-invite");
  await page.getByRole("button", { name: "Review invitation" }).click();
  await expect(page.getByText(study.protocol.consent)).toBeVisible();
  await page.getByLabel("I am an adult.").check();
  await page.getByLabel("I accept this specific study protocol.").check();
  await page.getByLabel("I have permission to share each recording").check();
  await page.getByRole("button", { name: "Accept study invitation" }).click();
  await expect(page.getByRole("status")).toContainText("Study consent recorded");
  expect(bodies).toEqual([{ token: "secret-invite", protocol_digest: study.protocol_digest, adult: true, accepted: true, rights: true }]);
});

test("missing session preserves unknown durations and retries the same request ID", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  const bodies: Record<string, unknown>[] = [];
  await page.route("**/api/session", r => r.fulfill({ json: { authenticated: true, csrf: "test" } }));
  await page.route("**/api/pilots", r => r.fulfill({ json: { studies: [study] } }));
  await page.route(`**/api/pilots/${id}`, r => r.fulfill({ json: detail }));
  await page.route(`**/api/pilots/${id}/session`, r => { bodies.push(r.request().postDataJSON()); return r.fulfill({ status: bodies.length === 1 ? 503 : 200, json: bodies.length === 1 ? { error: "Temporary failure. Retry." } : { recorded: true } }); });
  await page.goto("/pilots");
  await page.getByLabel("Selected study").selectOption(id);
  await page.getByLabel("Session code", { exact: true }).fill("missing-1");
  await page.getByLabel("Original play time (local)").fill("2026-10-02T20:00");
  await page.getByLabel("Capture state").selectOption("MISSING");
  await page.getByRole("button", { name: "Record session", exact: true }).click();
  await expect(page.getByRole("main").getByRole("alert")).toContainText("Retry");
  await page.getByRole("button", { name: "Record session", exact: true }).click();
  await expect(page.getByRole("status")).toContainText("Study record saved");
  expect(bodies[0]).toEqual(bodies[1]);
  expect(bodies[0]).toMatchObject({ state: "MISSING", playable_seconds: null, setup_seconds: null, insight_seconds: null, useful: null, unaided: false });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.screenshot({ path: "test-results/m18-pilot-mobile.png", fullPage: true });
});

test("reviewer sees an independent queue and defaults evidence to unknown", async ({ page }) => {
  const reviewer = { ...study, role: "REVIEWER" };
  const task = { id: "review-task", kind: "TARGET", start_us: 0, end_us: 1000000, state: "PENDING", submitted: false, can_review: true, media_url: "/private-test.mp4", final_label: null, reviews: [] };
  let submitted = false;
  let body: Record<string, unknown> = {};
  await page.route("**/api/session", r => r.fulfill({ json: { authenticated: true, csrf: "review-csrf", operator: false } }));
  await page.route("**/api/pilots", r => r.fulfill({ json: { studies: [reviewer] } }));
  await page.route(`**/api/pilots/${id}`, r => r.fulfill({ json: { ...detail, ...reviewer, tasks: [{ ...task, submitted, can_review: !submitted }] } }));
  await page.route(`**/api/pilots/${id}/review`, r => { body = r.request().postDataJSON(); submitted = true; return r.fulfill({ json: { recorded: true } }); });
  await page.goto("/pilots");
  await page.getByLabel("Selected study").selectOption(id);
  await expect(page.getByRole("heading", { name: "Assigned review queue" })).toBeVisible();
  await expect(page.getByText("Completed independent labels", { exact: true })).toHaveCount(0);
  await expect(page.getByRole("heading", { name: "Record every session" })).toHaveCount(0);
  await page.getByLabel("Timestamp uncertainty, microseconds").fill("20000");
  await page.getByLabel("Measured review seconds").fill("40");
  await page.getByRole("button", { name: "Submit independent review" }).click();
  await expect(page.getByText("Your review is submitted.")).toBeVisible();
  expect(body).toMatchObject({ task_id: "review-task", seconds: 40, label: { visibility: "UNOBSERVABLE", conditions: { build_verified: null, punish_confirmed: null, uncertainty_us: 20000 } } });
});

test("expert decisions remain separate from candidate metrics and withdrawal is explicit", async ({ page }) => {
  const expert = { ...study, role: "EXPERT", state: "FROZEN" };
  let removed = false;
  let decision: object = {};
  await page.route("**/api/session", r => r.fulfill({ json: { authenticated: true, csrf: "test" } }));
  await page.route("**/api/pilots", r => r.fulfill({ json: { studies: removed ? [] : [expert] } }));
  await page.route(`**/api/pilots/${id}`, r => {
    if (r.request().method() === "DELETE") { removed = true; return r.fulfill({ json: { withdrawn: true } }); }
    return r.fulfill({ json: { ...detail, ...expert, reports: [{ id: "report-1", gate: "G1", content_hash: "hash", data: { scope: "SOFTWARE_REHEARSAL", scientific_gate: "NOT_RUN", candidate_criteria_met: false, proposed_action: "WAIT", metrics: { captures: 0 } }, decision: null }] } });
  });
  await page.route(`**/api/pilots/${id}/decision`, r => { decision = r.request().postDataJSON(); return r.fulfill({ json: { recorded: true } }); });
  await page.goto("/pilots");
  await page.getByLabel("Selected study").selectOption(id);
  await expect(page.getByText("SOFTWARE_REHEARSAL · scientific gate NOT_RUN.", { exact: false })).toBeVisible();
  await page.getByLabel("Offline decision reference code").fill("local-review");
  await page.getByRole("button", { name: "Record independent decision" }).click();
  await expect(page.getByRole("status")).toContainText("Study record saved");
  expect(decision).toEqual({ report_id: "report-1", action: "WAIT", reason: "INSUFFICIENT_SAMPLE", reference: "local-review" });
  await page.getByRole("button", { name: "Withdraw from study", exact: true }).click();
  expect(removed).toBe(false);
  await page.getByRole("button", { name: "Confirm study withdrawal" }).click();
  await expect(page.getByRole("status")).toContainText("Study access revoked");
  expect(removed).toBe(true);
});
