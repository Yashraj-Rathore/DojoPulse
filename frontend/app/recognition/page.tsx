"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import { workspaceRequest } from "../workspace-api";

type Version = { id: string; version: string; dataset_id: string; state: string; role: "OWNER" | "REVIEWER"; content_hash: string; disabled_reason: string };
type Report = { metrics: { slices: Record<string, { precision: number | null; recall: number | null; tp: number; fp: number; fn: number }>; abstention_rate: number | null; observable_outcome_coverage: number | null; timestamp_error_us: { median: number | null; p95: number | null } }; negative_controls: { sources: number; false_positives: number }; stop_reasons: string[]; software_pass: boolean; scientific_gate: string; interpretation: string };
type Receipt = { id: string; snapshot_id: string; content_hash: string; input_hash: string; valid: boolean; reason: string; reviewed: boolean; approval_count: number; report: Report | null };
type Detail = Version & { manifest: object | null; runs: Receipt[] };
type Inventory = { versions: Version[]; engine: string; artifact_hash: string };

export default function Recognition() {
  const [csrf, setCsrf] = useState("");
  const [ready, setReady] = useState(false);
  const [inventory, setInventory] = useState<Inventory>({ versions: [], engine: "", artifact_hash: "" });
  const [selected, setSelected] = useState("");
  const [detail, setDetail] = useState<Detail | null>(null);
  const [error, setError] = useState("");
  const [status, setStatus] = useState("");
  const [busy, setBusy] = useState(false);
  const requests = useRef<Record<string, string>>({});
  const refresh = useCallback(async (signal?: AbortSignal) => {
    const list = await workspaceRequest<Inventory>(csrf, "recognition", "GET", undefined, signal);
    if (signal?.aborted) return;
    setInventory(list);
    if (selected && list.versions.some(v => v.id === selected)) {
      const next = await workspaceRequest<Detail>(csrf, `recognition/${selected}`, "GET", undefined, signal);
      if (!signal?.aborted) setDetail(next);
    } else setDetail(null);
  }, [csrf, selected]);
  useEffect(() => {
    const controller = new AbortController();
    fetch("/api/session", { cache: "no-store", signal: controller.signal }).then(r => r.json()).then(session => {
      if (!session.authenticated || !session.operator) { setError("Sign in with a local operator account to manage recognition."); return; }
      setCsrf(session.csrf); setReady(true);
    }).catch(e => { if (!controller.signal.aborted) setError(e.message); });
    return () => controller.abort();
  }, []);
  useEffect(() => {
    if (!ready) return;
    const controller = new AbortController();
    const load = () => void refresh(controller.signal).catch(e => { if (!controller.signal.aborted) { setDetail(null); setError(e.message); } });
    load();
    return () => controller.abort();
  }, [ready, refresh]);
  async function act(work: () => Promise<void>) {
    setBusy(true); setError(""); setStatus("");
    try { await work(); await refresh(); } catch (e) { setError(e instanceof Error ? e.message : "Request failed"); } finally { setBusy(false); }
  }
  async function submit(event: React.FormEvent<HTMLFormElement>, operation: "register" | "run") {
    event.preventDefault(); const form = event.currentTarget; const fields = Object.fromEntries(new FormData(form));
    await act(async () => {
      const path = operation === "register" ? "recognition" : `recognition/${selected}/run`;
      const payload = operation === "register" ? { dataset_id: fields.dataset_id, configuration: JSON.parse(String(fields.configuration)), reviewer_one: Number(fields.reviewer_one), reviewer_two: Number(fields.reviewer_two) } : { snapshot_id: fields.snapshot_id, observations: JSON.parse(String(fields.observations)) };
      const key = `${path}:${JSON.stringify(payload)}`;
      requests.current[key] ??= crypto.randomUUID();
      const result = await workspaceRequest<{ id: string }>(csrf, path, "POST", { ...payload, request_id: requests.current[key] });
      delete requests.current[key]; form.reset();
      if (operation === "register") setSelected(result.id);
      setStatus(operation === "register" ? "Immutable synthetic detector registered. Real release remains gated." : "Held-out software receipt recorded. Open the current report before independent review.");
    });
  }
  async function command(operation: string, receipt?: Receipt, decision?: string) {
    await act(async () => {
      const path = `recognition/${selected}/${operation}`;
      const key = `${path}:${receipt?.id}:${decision}`;
      requests.current[key] ??= crypto.randomUUID();
      await workspaceRequest(csrf, path, "POST", receipt ? { run_id: receipt.id, ...(operation === "review" ? { report_hash: receipt.content_hash, decision, request_id: requests.current[key] } : {}) } : {});
      delete requests.current[key];
      setStatus(operation === "activate" ? "Synthetic candidate version activated. Gameplay publication still requires independent human review." : operation === "disable" ? "Candidate version stopped." : "Independent report decision recorded.");
    });
  }
  async function download(receipt: Receipt) {
    await act(async () => {
      const bundle = await workspaceRequest<object>(csrf, `recognition/${selected}/runs/${receipt.id}`);
      const url = URL.createObjectURL(new Blob([JSON.stringify(bundle, null, 2)], { type: "application/json" }));
      const anchor = document.createElement("a"); anchor.href = url; anchor.download = "dojopulse-recognition-report.json"; anchor.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
      setStatus("Current benchmark and observation inputs exported. Keep this private; offline copies require separate deletion.");
    });
  }
  const percent = (value: number | null) => value === null ? "unavailable" : `${(value * 100).toFixed(1)}%`;
  return <main className="recognition-workspace"><header><p className="eyebrow">LOCAL OPERATOR WORKSPACE</p><h1>Recognition validation</h1><p>Version candidates, inspect held-out errors and stop drift. Real Tekken detector release and scientific gate G2 remain unrun.</p><nav className="steps"><Link href="/">Training workspace</Link><Link href="/datasets">Datasets</Link><Link href="/pilots">Independent media review</Link></nav></header>
    {error && <p role="alert" className="notice error">{error}</p>}{status && <p role="status" className="notice">{status}</p>}
    {ready && <><section><h2>Register a fixed version</h2><p>Pin the dataset measurement, capture profile, engine artifacts and stop limits. Two independent operators review the exact benchmark receipt. This does not grant real detector approval.</p><details><summary>Installed engine identity</summary><p>{inventory.engine}</p><p className="muted">{inventory.artifact_hash}</p></details>
      <form onSubmit={e => void submit(e, "register")}><label>Dataset ID<input name="dataset_id" required /></label><label>Detector manifest JSON<textarea name="configuration" required maxLength={20000} rows={6} /></label><label>First independent operator ID<input name="reviewer_one" type="number" min={1} required /></label><label>Second independent operator ID<input name="reviewer_two" type="number" min={1} required /></label><button disabled={busy}>Register synthetic detector</button></form>
      <label>Selected detector<select value={selected} onChange={e => { setSelected(e.target.value); setDetail(null); setError(""); }}><option value="">Choose a version</option>{inventory.versions.map(v => <option key={v.id} value={v.id}>{v.version} / {v.state.toLowerCase()} / {v.role.toLowerCase()}</option>)}</select></label></section>
      {detail && <><section><h2>{detail.version}</h2><p>State: {detail.state.toLowerCase()}. {detail.disabled_reason.toLowerCase().replaceAll("_", " ")}</p><p className="muted">{detail.content_hash}</p>{detail.state === "INVALIDATED" ? <p>Private recognition inputs and reports have been erased or withheld. Register a new version using currently authorized data.</p> : <><details><summary>Pinned configuration</summary><pre>{JSON.stringify(detail.manifest, null, 2)}</pre></details>{detail.role === "OWNER" && <><button className="secondary" disabled={busy || detail.state === "DISABLED"} onClick={() => void command("disable")}>Stop candidate version</button><form onSubmit={e => void submit(e, "run")}><label>Reviewed snapshot ID<input name="snapshot_id" required /></label><label>Observation batch JSON<textarea name="observations" required rows={6} maxLength={500000} /></label><p>Include every held-out source, including clips without targets. Low support, conflicts, missing observations and unsupported profiles retain UNKNOWN.</p><button disabled={busy}>Run held-out software benchmark</button></form></>}</>}</section>
        <section><h2>Benchmark history</h2>{!detail.runs.length && <p>No available benchmark receipt.</p>}{detail.runs.map((receipt, index) => <article className="result" key={receipt.id}><h3>Receipt {receipt.id}</h3><p className="muted">{receipt.content_hash}</p>{!receipt.valid || !receipt.report ? <p>Private evidence unavailable: {receipt.reason.toLowerCase().replaceAll("_", " ")}.</p> : <><p>Software check {receipt.report.software_pass ? "passed" : "requires review"}; scientific gate {receipt.report.scientific_gate}. Independent approvals: {receipt.approval_count}/2.</p><p>{receipt.report.interpretation}</p><p>Abstention {percent(receipt.report.metrics.abstention_rate)}. Observable outcome coverage {percent(receipt.report.metrics.observable_outcome_coverage)}.</p><p>Timestamp error median {receipt.report.metrics.timestamp_error_us.median ?? "unavailable"} / p95 {receipt.report.metrics.timestamp_error_us.p95 ?? "unavailable"} microseconds.</p><div className="table-wrap"><table><thead><tr><th>Slice</th><th>Precision</th><th>Recall</th><th>TP / FP / FN</th></tr></thead><tbody>{Object.entries(receipt.report.metrics.slices).map(([name, slice]) => <tr key={name}><th>{name}</th><td>{percent(slice.precision)}</td><td>{percent(slice.recall)}</td><td>{slice.tp} / {slice.fp} / {slice.fn}</td></tr>)}</tbody></table></div><p>Target-absent sources: {receipt.report.negative_controls.sources}. False positives: {receipt.report.negative_controls.false_positives}.</p>{receipt.report.stop_reasons.length > 0 && <p>Stop reasons: {receipt.report.stop_reasons.join(", ").toLowerCase().replaceAll("_", " ")}.</p>}
          {detail.role === "OWNER" ? <><button className="secondary" disabled={busy} onClick={() => void download(receipt)}>Download benchmark report</button><button disabled={busy || !receipt.report.software_pass || receipt.approval_count !== 2 || index !== 0 || detail.state === "ACTIVE"} onClick={() => void command("activate", receipt)}>Activate reviewed synthetic version</button></> : <><button disabled={busy || receipt.reviewed} onClick={() => void command("review", receipt, "APPROVE")}>Approve software receipt</button><button className="secondary" disabled={busy || receipt.reviewed} onClick={() => void command("review", receipt, "REJECT")}>Reject software receipt</button><p>Reviewers receive aggregate metrics. Private source IDs and observation evidence stay in the dataset owner’s workspace.</p></>}
          <p><Link href="/pilots">Open independent media review fallback</Link>. Candidate outcomes are unverified and do not enter diagnosis, practice counts or improvement claims.</p></>}</article>)}</section></>}
    </>}
  </main>;
}
