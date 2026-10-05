"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import { workspaceRequest } from "../workspace-api";

type Measurement = { knowledge: string; game_build: string; platform: string; situation: string; metric: string };
type Dataset = { id: string; title: string; state: string; dataset_kind: string; measurement: Measurement };
type Slice = { sources: number; players: number; sessions: number; tasks: number; categories: Record<string, number>; missing_categories: string[]; adjudicated: number; structured_agreement_rate: number | null; review_seconds: number; timing: { independently_audited: number; unaudited: number; uncertainty_max_us: number | null; reviewer_start_gap_max_us: number | null }; detector_versions: string[]; recognition: object | null };
type QA = { splits: Record<string, Slice>; representative_coverage: boolean; scientific_gate: string; release_approval: boolean; timing_interpretation: string };
type Snapshot = { id: string; sequence: number; content_hash: string; valid: boolean; reason: string; qa: QA | null };
type Detail = Dataset & { measurement_available?: boolean; source_count: number; studies: { id: string; title: string; state: string; revision: number }[]; snapshots: Snapshot[] };
type Inventory = { datasets: Dataset[]; releases: { key: string; game_build: string; platform: string; dataset_kind: string }[] };
type Observability = { content_hash: string; data: { snapshot_hash: string; dataset_kind: string; scientific_gate: string; proposed_threshold_result: string; blockers: string[]; totals: { captures: number; excluded_non_ranked_captures: number; players: number; sessions: number; critical_windows: number; resolvable_windows: number; unresolved_windows: number; resolvable_rate: number | null; timing_unaudited_windows: number; review_seconds: number; unresolved_reasons: Record<string, number> }; interpretation: string } };

export default function Datasets() {
  const [csrf, setCsrf] = useState("");
  const [ready, setReady] = useState(false);
  const [inventory, setInventory] = useState<Inventory>({ datasets: [], releases: [] });
  const [selected, setSelected] = useState("");
  const [detail, setDetail] = useState<Detail | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [status, setStatus] = useState("");
  const [closing, setClosing] = useState(false);
  const [assessment, setAssessment] = useState<{ snapshotId: string; report: Observability } | null>(null);
  const requests = useRef<Record<string, string>>({});
  const refresh = useCallback(async (signal?: AbortSignal) => {
    const result = await workspaceRequest<Inventory>(csrf, "datasets", "GET", undefined, signal);
    if (signal?.aborted) return;
    setInventory(result);
    if (selected && result.datasets.some(row => row.id === selected)) {
      const next = await workspaceRequest<Detail>(csrf, `datasets/${selected}`, "GET", undefined, signal);
      if (!signal?.aborted) setDetail(next);
    } else setDetail(null);
  }, [csrf, selected]);
  useEffect(() => {
    const controller = new AbortController();
    fetch("/api/session", { cache: "no-store", signal: controller.signal }).then(r => r.json()).then(session => {
      if (!session.authenticated || !session.operator) { setError("Sign in with a local operator account to manage datasets."); return; }
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
    try { await work(); await refresh(); } catch (e) { setAssessment(null); setError(e instanceof Error ? e.message : "Request failed"); } finally { setBusy(false); }
  }
  async function submit(event: React.FormEvent<HTMLFormElement>, operation: "create" | "study") {
    event.preventDefault(); const form = event.currentTarget; const fields = Object.fromEntries(new FormData(form));
    const path = operation === "create" ? "datasets" : `datasets/${selected}/study`;
    requests.current[path] ??= crypto.randomUUID();
    await act(async () => {
      const result = await workspaceRequest<{ id?: string }>(csrf, path, "POST", { ...fields, request_id: requests.current[path], ...(operation === "create" ? { dataset_kind: "synthetic" } : {}) });
      delete requests.current[path]; form.reset();
      if (result.id) setSelected(result.id);
      setStatus(operation === "create" ? "Dataset specification pinned." : "Consented review study created. Open Pilot studies to invite members and register sources.");
    });
  }
  async function download(snapshot: Snapshot) {
    await act(async () => {
      const bundle = await workspaceRequest<object>(csrf, `datasets/${selected}/snapshots/${snapshot.id}`);
      const url = URL.createObjectURL(new Blob([JSON.stringify(bundle, null, 2)], { type: "application/json" }));
      const anchor = document.createElement("a"); anchor.href = url; anchor.download = `dojopulse-dataset-${snapshot.sequence}.json`; anchor.click(); URL.revokeObjectURL(url);
      setStatus("Current snapshot exported. Media bytes and current permissions require separate checks when using an offline copy.");
    });
  }
  async function assess(snapshot: Snapshot) {
    setAssessment(null);
    await act(async () => {
      const report = await workspaceRequest<Observability>(csrf, `datasets/${selected}/snapshots/${snapshot.id}/observability`);
      setAssessment({ snapshotId: snapshot.id, report });
      const url = URL.createObjectURL(new Blob([JSON.stringify(report, null, 2)], { type: "application/json" }));
      const anchor = document.createElement("a"); anchor.href = url; anchor.download = `dojopulse-observability-${snapshot.sequence}.json`; anchor.click(); URL.revokeObjectURL(url);
      setStatus("Observability report exported. Proposed thresholds do not approve a scientific gate or real recognition.");
    });
  }
  return <main className="operations pilots">
    <header><span className="brand">DojoPulse / Datasets</span><Link href="/">Player workspace</Link><Link href="/pilots">Pilot studies</Link><Link href="/knowledge">Knowledge review</Link></header>
    <div className="intro"><div className="eyebrow">Local dataset operations</div><h1>Freeze the inputs.<br />Keep the evidence traceable.</h1><p>Collections bind consented independent review to one exact build and measurement. Coverage checks and synthetic metrics do not qualify real gameplay recognition. Model training permission is separate.</p></div>
    {error && <p className="notice error" role="alert">{error}</p>}{status && <p className="notice" role="status">{status}</p>}
    {ready && <>
      <section><h2>Create a collection</h2>{!inventory.releases.length ? <p>Publish a reviewed synthetic knowledge bundle in Knowledge review first. Draft and legacy definitions cannot create a dataset.</p> : <form onSubmit={e => void submit(e, "create")}>
        <label>Dataset title<input name="title" required maxLength={80} pattern="[A-Za-z0-9 _.-]+" /></label>
        <label>Reviewed knowledge<select name="knowledge_key" required>{inventory.releases.filter(r => r.dataset_kind === "synthetic").map(r => <option key={r.key} value={r.key}>{r.key} / {r.game_build} / {r.platform}</option>)}</select></label>
        <p>The specification and coverage checklist are immutable. Real intake remains gated.</p><button disabled={busy}>Create synthetic dataset</button>
      </form>}</section>
      <section><h2>Your collections</h2><label>Selected dataset<select value={selected} disabled={busy} onChange={e => { setSelected(e.target.value); setDetail(null); setAssessment(null); setClosing(false); setError(""); }}><option value="">Select a dataset</option>{inventory.datasets.map(d => <option key={d.id} value={d.id}>{d.title} / {d.state.toLowerCase()}</option>)}</select></label><button className="secondary" disabled={busy} onClick={() => void act(refresh)}>Refresh datasets</button></section>
      {detail && <>
        <section><h2>{detail.title}</h2><p>{detail.dataset_kind} / {detail.state.toLowerCase()} / {detail.source_count} registered sources</p><dl><dt>Exact build / platform</dt><dd>{detail.measurement.game_build} / {detail.measurement.platform}</dd><dt>Knowledge</dt><dd>{detail.measurement.knowledge}</dd><dt>Situation</dt><dd>{detail.measurement.situation}</dd><dt>Metric</dt><dd>{detail.measurement.metric}</dd></dl>
          {closing ? <><p>Close all linked studies and erase their labels, source grants and private snapshots? Workspace recordings keep their original retention.</p><button disabled={busy} onClick={() => void act(async () => { await workspaceRequest(csrf, `datasets/${selected}`, "DELETE"); setSelected(""); setDetail(null); setClosing(false); setStatus("Collection closed and private dataset evidence erased."); })}>Confirm collection closure</button><button className="secondary" onClick={() => setClosing(false)}>Keep collection</button></> : <button className="secondary" disabled={busy} onClick={() => setClosing(true)}>Close collection</button>}
        </section>
        <section><h2>Consented review studies</h2><p>Use Pilot studies for invitations, prospective sessions, source registration, blind independent review and adjudication. Player, session and source splits stay locked across these studies and snapshots.</p>{detail.studies.map(s => <p key={s.id}><Link href={`/pilots#study=${s.id}`}>{s.title}</Link> / {s.state.toLowerCase()} / revision {s.revision}</p>)}
          {detail.state === "COLLECTING" && <form onSubmit={e => void submit(e, "study")}><label>Review study title<input name="title" required maxLength={80} pattern="[A-Za-z0-9 _.-]+" /></label><button disabled={busy}>Create linked review study</button></form>}
        </section>
        <section><h2>Freeze and seal</h2>{detail.measurement_available === false && <p className="notice error">Pinned knowledge is unavailable. Close this collection or create a new one with currently reviewed definitions.</p>}<p>Freeze all source inputs and predictions before revealing held-out labels. Reviews may finish afterward. Sealing requires complete source QC and resolved independent labels. Missing sampling categories remain visible.</p>
          {detail.state === "COLLECTING" ? <button disabled={busy || !detail.studies.length || detail.measurement_available === false} onClick={() => void act(async () => { await workspaceRequest(csrf, `datasets/${selected}/freeze`, "POST", {}); setStatus("Dataset and linked study inputs frozen. Assigned reviews can still finish."); })}>Freeze dataset inputs</button> : <button disabled={busy || detail.measurement_available === false} onClick={() => void act(async () => { const path = `datasets/${selected}/seal`; requests.current[path] ??= crypto.randomUUID(); await workspaceRequest(csrf, path, "POST", { request_id: requests.current[path] }); delete requests.current[path]; setStatus("Immutable snapshot sealed. Scientific gates remain NOT_RUN."); })}>Seal reviewed snapshot</button>}
        </section>
        <section><h2>Snapshot history</h2>{!detail.snapshots.length && <p>No sealed snapshot yet.</p>}{detail.snapshots.map(snapshot => <article className="result" key={snapshot.id}><h3>Snapshot {snapshot.sequence} / {snapshot.valid ? "current" : "invalidated"}</h3><p className="muted">{snapshot.content_hash}</p>{!snapshot.valid && <p>Private data erased or withheld: {snapshot.reason.toLowerCase().replaceAll("_", " ")}.</p>}{snapshot.qa && <>
          <p>Scientific gate {snapshot.qa.scientific_gate}. Coverage checklist {snapshot.qa.representative_coverage ? "complete" : "incomplete"}.</p>
          {Object.entries(snapshot.qa.splits).map(([split, slice]) => <div key={split}><h4>{split}</h4><p>{slice.sources} sources / {slice.players} players / {slice.sessions} sessions / {slice.tasks} windows</p><p>{Object.entries(slice.categories).map(([key, count]) => `${key.toLowerCase().replaceAll("_", " ")}: ${count}`).join(" · ")}</p><p>Missing categories: {slice.missing_categories.length ? slice.missing_categories.map(c => c.toLowerCase().replaceAll("_", " ")).join(", ") : "none"}.</p><p>{slice.adjudicated} adjudicated tasks / {slice.review_seconds}s review time. Timing audited: {slice.timing.independently_audited}; unaudited: {slice.timing.unaudited}. Maximum uncertainty: {slice.timing.uncertainty_max_us ?? "unknown"} microseconds.</p>{slice.recognition && <details><summary>Reference-relative prediction slices</summary><pre>{JSON.stringify(slice.recognition, null, 2)}</pre></details>}</div>)}
          <p>{snapshot.qa.timing_interpretation}</p><button className="secondary" disabled={busy} onClick={() => void download(snapshot)}>Download snapshot {snapshot.sequence}</button>
          {snapshot.valid && <button className="secondary" disabled={busy} onClick={() => void assess(snapshot)}>Assess observability {snapshot.sequence}</button>}
          {snapshot.valid && assessment?.snapshotId === snapshot.id && assessment.report.data.snapshot_hash === snapshot.content_hash && <section aria-label={`Observability for snapshot ${snapshot.sequence}`}>
            <h4>Human observability / {assessment.report.data.dataset_kind}</h4>
            <p>G1 {assessment.report.data.scientific_gate}. {assessment.report.data.proposed_threshold_result.toLowerCase().replaceAll("_", " ")}.</p>
            <p>{assessment.report.data.totals.captures} ranked captures of 20 required / {assessment.report.data.totals.players} players / {assessment.report.data.totals.sessions} sessions. {assessment.report.data.totals.excluded_non_ranked_captures} other captures kept separate.</p>
            <p>{assessment.report.data.totals.resolvable_windows} resolvable / {assessment.report.data.totals.critical_windows} critical windows; {assessment.report.data.totals.unresolved_windows} unresolved. Resolvable rate: {assessment.report.data.totals.resolvable_rate === null ? "unknown" : `${(100 * assessment.report.data.totals.resolvable_rate).toFixed(1)}%`}.</p>
            <p>{assessment.report.data.totals.timing_unaudited_windows} windows lack complete timing audits. Recorded review time: {assessment.report.data.totals.review_seconds}s.</p>
            <p>Unresolved reasons: {Object.entries(assessment.report.data.totals.unresolved_reasons).map(([reason, count]) => `${reason.toLowerCase().replaceAll("_", " ")}: ${count}`).join("; ") || "none recorded"}.</p>
            <p>Remaining checks: {assessment.report.data.blockers.map(reason => reason.toLowerCase().replaceAll("_", " ")).join("; ")}.</p>
            <p>{assessment.report.data.interpretation}</p>
          </section>}
        </>}</article>)}</section>
      </>}
    </>}
  </main>;
}
