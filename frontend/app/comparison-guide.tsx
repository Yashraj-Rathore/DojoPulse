"use client";
import { useEffect, useRef, useState } from "react";
import { displayTime, workspaceRequest as request } from "./workspace-api";

type Collection = { expected_sessions: number | null; observed_sessions: number; complete: boolean; missing_reported_sessions: number; skipped_reported_sessions: number; withdrawn_reported_sessions: number; unresolved_recorded_sessions: number; matches_without_current_target_publication: number; matches_with_unavailable_local_sources?: number };
type Session = { id: string; code: string; state: string; revision: number; played_at: string | null };
type Phase = { start: string; end: string; collection: Collection; sessions: Session[]; evidence: { id: string; match_id: string; session_code: string; eligibility: string; outcome: string; source: object }[] };
type Diagnostic = { known_outcomes: number; sessions: number; largest_session_share: number | null; session_rate_variance: number | null; reasons: string[]; planning: { sessions_per_period: number | null; target_power: number; actual_power_validated: boolean } };
type Report = { plan_hash: string; report_hash: string; dataset_kind: string; protocol: { version?: string; scope?: object; source_policy?: object; baseline_planning?: Diagnostic }; specification: { minimum_sample: number; minimum_sessions: number; minimum_practice: number; meaningful_change: number }; phases: Record<string, Phase>; revisions: { id: string; phase: string; revision: number; result_hash: string; available: boolean; unavailable_reasons: string[]; result: { status: string; reasons: string[]; retention?: { state: string }; diagnostics?: { baseline: Diagnostic; followup: Diagnostic } } }[] };
const words = (s: string) => s.replaceAll("_", " ").toLowerCase();

export default function ComparisonGuide({ plan, csrf, zone, revision, onChanged }: { plan: string; csrf: string; zone: string; revision: string; onChanged: () => void }) {
  const [data, setData] = useState<Report | null>(null), [error, setError] = useState(""), [busy, setBusy] = useState(false), [reload, setReload] = useState(0);
  const [phase, setPhase] = useState("FOLLOWUP"), [state, setState] = useState("MISSING");
  const pending = useRef<{ hash: string; id: string } | null>(null);
  useEffect(() => {
    const controller = new AbortController();
    const load = async () => { try { const next = await request<Report>(csrf, `plans/${plan}/comparison`, "GET", undefined, controller.signal); if (!controller.signal.aborted) { setData(next); setError(""); } } catch (e) { if (!controller.signal.aborted) { setData(null); setError(e instanceof Error ? e.message : "Comparison unavailable"); } } };
    void load(); const timer = setInterval(() => { if (document.visibilityState === "visible") void load(); }, 10000);
    return () => { controller.abort(); clearInterval(timer); };
  }, [csrf, plan, revision, reload]);
  async function act(path: string, method: string, body?: object) {
    setBusy(true); setError("");
    try { await request(csrf, path, method, body); setReload(n => n + 1); onChanged(); return true; }
    catch (e) { setError(e instanceof Error ? e.message : "Comparison action failed"); return false; }
    finally { setBusy(false); }
  }
  const selected = data?.phases[phase];
  const codes = [...new Set(selected?.evidence.map(e => e.session_code) || [])];
  return <article className="result" aria-label="Longitudinal comparison guide">
    <h3>Comparison evidence & retention</h3><button className="secondary" onClick={() => { setData(null); setReload(n => n + 1); }}>Refresh comparison</button>
    {error && <p role="alert" className="notice error">{error}</p>}{!data && !error && <p role="status">Loading comparison…</p>}
    {data && <>
      <p>{data.dataset_kind === "synthetic" ? "Synthetic software test — not gameplay evidence." : "Observational comparison; player benefit is not established."}</p>
      <p>The frozen plan needs {data.specification.minimum_sample} known outcomes across {data.specification.minimum_sessions} sessions per period and {data.specification.minimum_practice} verified practice attempts. These are exploratory floors, not a guarantee of statistical power. Meaningful change: {(data.specification.meaningful_change * 100).toFixed(1)} percentage points.</p>
      {!data.protocol.version && <p className="notice">This earlier plan has no retention schedule or missing-session ledger. Freeze a new plan to declare these before collection.</p>}
      <label htmlFor="comparison-phase">Comparison period</label><select id="comparison-phase" value={phase} onChange={e => setPhase(e.target.value)}>{Object.keys(data.phases).map(p => <option key={p} value={p}>{p === "RETENTION" ? "Retention" : "Follow-up"}</option>)}</select>
      {selected && <>
        <p>{displayTime(selected.start, zone)} → {displayTime(selected.end, zone)}. Original frozen dates remain in force.</p>
        <p role="status">{selected.collection.observed_sessions} observed sessions / {selected.collection.expected_sessions ?? "undeclared"} planned. {selected.collection.complete ? "Recorded collection is complete." : "Collection has gaps; improvement cannot be established."}</p>
        <p>Missing: {selected.collection.missing_reported_sessions}; skipped: {selected.collection.skipped_reported_sessions}; withdrawn: {selected.collection.withdrawn_reported_sessions}; unresolved: {selected.collection.unresolved_recorded_sessions}; recorded matches without current target evidence: {selected.collection.matches_without_current_target_publication}; unavailable local sources: {selected.collection.matches_with_unavailable_local_sources ?? 0}.</p>
        <p className="muted">All recorded target opportunities in this window are included, including unfavorable and unknown outcomes. We cannot detect matches you never submit. Missing recordings add no outcomes.</p>
        <button disabled={busy} onClick={() => void act(`plans/${plan}/evaluate`, "POST", { phase })}>Compare all recorded {phase === "RETENTION" ? "retention" : "follow-up"} evidence</button>
        <details><summary>Included evidence & source provenance ({selected.evidence.length})</summary><ul>{selected.evidence.map(e => <li key={e.id}>Match {e.match_id.slice(0, 8)} · session {e.session_code} · {words(e.eligibility)} / {words(e.outcome)}<details><summary>Source and decoder</summary><pre>{JSON.stringify(e.source, null, 2)}</pre></details></li>)}</ul></details>
        {data.protocol.version && <>
          <h4>Report collection gaps or recorded sessions</h4><p>Reports track collection and add zero verified outcomes. Use the original play session code to resolve a gap when its reviewed recordings arrive.</p>
          <form onSubmit={e => { e.preventDefault(); const form = e.currentTarget, f = new FormData(form); const code = String(f.get("code")); const values = { phase, state, code, ...(state === "RECORDED" ? { match_ids: [...new Set(selected.evidence.filter(e => e.session_code === code).map(e => e.match_id))] } : { played_at: new Date(String(f.get("played_at"))).toISOString() }) }; const hash = JSON.stringify(values); if (pending.current?.hash !== hash) pending.current = { hash, id: crypto.randomUUID() }; void act(`plans/${plan}/sessions`, "POST", { ...values, request_id: pending.current.id }).then(ok => { if (ok) { pending.current = null; form.reset(); } }); }}>
            <fieldset disabled={busy}><label htmlFor="collection-state">Collection status</label><select id="collection-state" value={state} onChange={e => setState(e.target.value)}><option value="MISSING">Played, recording missing</option><option value="SKIPPED">Planned session skipped</option><option value="RECORDED">Owned recordings received</option></select>
            <label htmlFor="collection-code">Original play session code</label>{state === "RECORDED" ? <select id="collection-code" name="code" required><option value="">Select a recorded session</option>{codes.map(c => <option key={c}>{c}</option>)}</select> : <input id="collection-code" name="code" pattern="[A-Za-z0-9][A-Za-z0-9_.:-]{0,99}" maxLength={100} required />}
            {state !== "RECORDED" && <><label htmlFor="collection-played">Session time (local)</label><input id="collection-played" name="played_at" type="datetime-local" required /></>}
            <button>Save collection report</button></fieldset>
          </form>
          <ul>{selected.sessions.map(s => <li key={s.id}>{words(s.state)} · {s.code || "removed session"} · revision {s.revision}{s.played_at && ` · ${displayTime(s.played_at, zone)}`}{s.state !== "DELETED" && <button className="secondary" disabled={busy} onClick={() => void act(`comparison-sessions/${s.id}`, "DELETE")}>Delete collection report</button>}</li>)}</ul>
        </>}
      </>}
      {data.protocol.baseline_planning && <details><summary>Baseline session adequacy & study planning</summary><p>Known outcomes: {data.protocol.baseline_planning.known_outcomes}; sessions: {data.protocol.baseline_planning.sessions}; session-rate variance: {data.protocol.baseline_planning.session_rate_variance ?? "unknown"}.</p><p>{data.protocol.baseline_planning.planning.sessions_per_period == null ? "Too little or degenerate variance for a planning estimate." : `Illustrative sessions per period: ${data.protocol.baseline_planning.planning.sessions_per_period}.`}</p><p>Baseline-only normal approximation assumes independent session rates and equal variance. Actual power and assumptions are unvalidated; this estimate does not approve a larger study.</p>{data.protocol.baseline_planning.reasons.map(r => <p key={r}>{words(r)}</p>)}</details>}
      <h4>Append-only result history</h4>{!data.revisions.length && <p>No comparison revisions yet.</p>}{data.revisions.map(r => <div className="result" key={r.id}><p>Revision {r.revision} · {words(r.phase)} · {r.available ? words(r.result.status) : "historical evidence unavailable"}</p>{!r.available ? <p>{r.unavailable_reasons.map(words).join("; ")}. Re-evaluate current evidence before using this result.</p> : <>{r.result.reasons.map(reason => <p key={reason}>{words(reason)}</p>)}{r.result.retention && <p>{words(r.result.retention.state)}. This does not establish causation.</p>}</>}<details><summary>Frozen result hash</summary><code>{r.result_hash}</code></details></div>)}
      <details><summary>Frozen scope, source policy & report hashes</summary><pre>{JSON.stringify({ scope: data.protocol.scope, source_policy: data.protocol.source_policy, plan_hash: data.plan_hash, report_hash: data.report_hash }, null, 2)}</pre><p>A source, decoder, build or measurement change requires a new reviewed plan. Earlier results remain historical.</p></details>
      <a href={`/api/plans/${plan}/comparison?download=1`} download>Download reproducible comparison report</a>
    </>}
  </article>;
}
