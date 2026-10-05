"use client";
import { useEffect, useRef, useState } from "react";
import { displayTime, workspaceRequest as request } from "./workspace-api";

type Rules = { minimum_known: number; minimum_sessions: number; minimum_coverage: number; minimum_agreement: number; ready_lower_bound: number };
type Detail = { status: string; drill_id: string; drill_hash: string; blockers: string[]; workflow: { response: string; success_criteria: string; setup_steps: string[]; alternatives: string[]; capture_steps: string[]; progression: Rules } | null; progression: { state: string; next_action: string; reasons: string[]; summary: { numerator: number; denominator: number; sessions: number; eligible_unknown: number; unknown_eligibility: number; coverage: number | null }; agreement: number | null } | null; unavailable_trials?: number; logs: { id: string; state: string; started_at: string; ended_at: string; reported_attempts: number; obstacle: string }[]; evidence: { id: string; match_id: string; asset_id: string; start_us: number; end_us: number }[] };
const words = (s: string) => s.replaceAll("_", " ").toLowerCase();

export default function PracticeGuide({ assignment, csrf, zone, revision, onChanged }: { assignment: string; csrf: string; zone: string; revision: string; onChanged: () => void }) {
  const [data, setData] = useState<Detail | null>(null), [error, setError] = useState(""), [busy, setBusy] = useState(false), [reload, setReload] = useState(0);
  const pending = useRef<{ hash: string; id: string } | null>(null);
  useEffect(() => {
    const controller = new AbortController();
    const load = async () => { try { const next = await request<Detail>(csrf, `assignments/${assignment}/training`, "GET", undefined, controller.signal); if (!controller.signal.aborted) { setData(next); setError(""); } } catch (e) { if (!controller.signal.aborted) { setData(null); setError(e instanceof Error ? e.message : "Practice guidance unavailable"); } } };
    void load(); const timer = setInterval(() => { if (document.visibilityState === "visible") void load(); }, 10000);
    return () => { controller.abort(); clearInterval(timer); };
  }, [csrf, assignment, revision, reload]);
  async function act(path: string, method: string, body?: object) {
    setBusy(true); setError("");
    try { await request(csrf, path, method, body); setReload(n => n + 1); onChanged(); return true; }
    catch (e) { setError(e instanceof Error ? e.message : "Practice action failed"); return false; }
    finally { setBusy(false); }
  }
  return <article className="result practice-guide" aria-label="Reviewed practice guide">
    <h3>Reviewed practice guide</h3><button className="secondary" onClick={() => { setData(null); setReload(n => n + 1); }}>Refresh practice guidance</button>
    {error && <p role="alert" className="notice error">{error}</p>}{!data && !error && <p role="status">Loading practice guidance…</p>}
    {data && <>
      <p>{data.drill_id} · {words(data.status)}</p>
      {data.blockers.map(reason => <p className="notice" key={reason}>{words(reason)}. Existing versions need a new independent review before guidance is available.</p>)}
      {data.workflow && <>
        <p><strong>Response:</strong> {data.workflow.response}</p><p><strong>Success criteria:</strong> {data.workflow.success_criteria}</p>
        {([ ["Native setup", data.workflow.setup_steps], ["Reviewed alternatives", data.workflow.alternatives], ["Capture and review", data.workflow.capture_steps] ] as const).map(([title, rows]) => <div key={title}><h4>{title}</h4><ol>{rows.map((row, i) => <li key={i}>{row}</li>)}</ol></div>)}
        <p className="muted">Reviewed research rules: {data.workflow.progression.minimum_known} known trials across {data.workflow.progression.minimum_sessions} sessions; {(data.workflow.progression.minimum_coverage * 100).toFixed(0)}% coverage; {(data.workflow.progression.minimum_agreement * 100).toFixed(0)}% raw review agreement; {(data.workflow.progression.ready_lower_bound * 100).toFixed(0)}% lower success bound. The frozen plan can require more. Real progression still requires expert and G4 qualification.</p>
        {data.progression && <div role="status"><h4>{words(data.progression.state)}</h4><p>{data.progression.next_action}</p><p>{data.progression.summary.numerator}/{data.progression.summary.denominator} current known successes across {data.progression.summary.sessions} sessions; {data.progression.summary.eligible_unknown} unknown outcomes and {data.progression.summary.unknown_eligibility} unknown eligibility; {data.unavailable_trials || 0} unavailable linked trials.</p>{data.progression.reasons.map(r => <p key={r}>{words(r)}</p>)}<p className="muted">This guides the declared follow-up; it does not change drill difficulty, frozen dates, or establish improvement.</p></div>}
        {data.evidence.length > 0 && <details><summary>Current practice evidence (sample)</summary><ul>{data.evidence.map(e => <li key={e.id}><a href={`/api/assets/${e.asset_id}/media#t=${e.start_us / 1e6},${e.end_us / 1e6}`} target="_blank" rel="noreferrer">Play practice window {(e.start_us / 1e6).toFixed(2)}–{(e.end_us / 1e6).toFixed(2)} s</a></li>)}</ul></details>}
        <h4>Report a practice session</h4><p>Self-reports track adherence and obstacles. They add zero verified trials and never qualify a comparison.</p>
        <form onSubmit={e => { e.preventDefault(); const form = e.currentTarget, f = new FormData(form); const values = { state: String(f.get("state")), started_at: new Date(String(f.get("started_at"))).toISOString(), ended_at: new Date(String(f.get("ended_at"))).toISOString(), reported_attempts: Number(f.get("reported_attempts")), obstacle: String(f.get("obstacle")) }; const hash = JSON.stringify(values); if (pending.current?.hash !== hash) pending.current = { hash, id: crypto.randomUUID() }; void act(`assignments/${assignment}/reports`, "POST", { ...values, request_id: pending.current.id }).then(ok => { if (ok) { pending.current = null; form.reset(); } }); }}>
          <label htmlFor="practice-state">Session result</label><select id="practice-state" name="state"><option value="COMPLETED">Completed</option><option value="INTERRUPTED">Interrupted</option><option value="SKIPPED">Skipped</option></select>
          <label htmlFor="practice-started">Session started (local)</label><input id="practice-started" name="started_at" type="datetime-local" required />
          <label htmlFor="practice-ended">Session ended (local)</label><input id="practice-ended" name="ended_at" type="datetime-local" required />
          <label htmlFor="practice-reported">Self-reported attempts</label><input id="practice-reported" name="reported_attempts" type="number" min="0" max="2000" required /><p className="muted">Use zero for skipped sessions. Completed sessions require at least one attempt.</p>
          <label htmlFor="practice-obstacle">Obstacle</label><select id="practice-obstacle" name="obstacle">{["NONE", "SETUP", "TIME", "CAPTURE", "UNCLEAR", "OTHER"].map(s => <option key={s} value={s}>{words(s)}</option>)}</select><button disabled={busy}>Save self-report</button>
        </form>
      </>}
      <h4>Self-reported sessions</h4>{!data.logs.length && <p>No self-reports yet.</p>}<ul>{data.logs.map(log => <li key={log.id}>{words(log.state)} · {displayTime(log.started_at, zone)} · {log.reported_attempts} reported attempts · obstacle: {words(log.obstacle)} <button className="secondary" disabled={busy} onClick={() => void act(`practice-reports/${log.id}`, "DELETE")}>Delete self-report</button></li>)}</ul>
      {!['CANCELLED', 'WITHDRAWN'].includes(data.status) && <button className="danger" disabled={busy} onClick={() => void act(`assignments/${assignment}/cancel`, "POST", {})}>Cancel this assignment</button>}
    </>}
  </article>;
}
