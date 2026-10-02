"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import { workspaceRequest } from "../workspace-api";

type Study = { id: string; title: string; dataset_kind: string; state: string; role: string; revision: number; protocol_digest: string; protocol: { consent: string; target: string; baseline_end: string; followup_start: string; ends_at: string; audit_ends_at: string } };
type Member = { id: string; pseudonym: string; role: string; split: string };
type Session = { id: string; code: string; phase: string; state: string; played_at: string };
type Capture = { id: string; session_id: string; game_build: string; duration_seconds: number; source_sha256: string };
type Task = { id: string; kind: string; start_us: number; end_us: number; state: string; submitted: boolean; can_review: boolean; media_url: string; final_label: object | null; reviews: { label: object; adjudication: boolean }[] };
type Report = { id: string; gate: string; content_hash: string; data: { scope: string; scientific_gate: string; candidate_criteria_met: boolean; proposed_action: string; metrics: object }; decision: { action: string; reason: string; reference: string } | null };
type Detail = Study & { pseudonym: string | null; members: Member[]; sessions: Session[]; captures: Capture[]; tasks: Task[]; reports: Report[]; available_sources: { asset_id: string; played_at: string; game_build: string; session_id: string }[] };
const conditions = ["build_verified", "knowledge_verified", "move_verified", "block_verified", "actor_verified", "standing", "reach_validated", "alignment_validated", "window_complete", "timing_validated", "wall_clear", "resource_independent", "punish_confirmed", "failure_confirmed"];
const label = (value: string) => value.replaceAll("_", " ").toLowerCase();
function Field({ name, title, type = "text", min, max, required = true }: { name: string; title: string; type?: string; min?: number; max?: number; required?: boolean }) {
  return <label>{title}<input name={name} type={type} min={min} max={max} step={type === "datetime-local" ? "any" : undefined} required={required} /></label>;
}
function Choice({ name, title, options }: { name: string; title: string; options: string[] }) {
  return <label>{title}<select name={name}>{options.map(v => <option key={v} value={v}>{label(v)}</option>)}</select></label>;
}

export default function Pilots() {
  const [csrf, setCsrf] = useState("");
  const [authenticated, setAuthenticated] = useState(false);
  const [operator, setOperator] = useState(false);
  const [studies, setStudies] = useState<Study[]>([]);
  const [selected, setSelected] = useState("");
  const [data, setData] = useState<Detail | null>(null);
  const [invitation, setInvitation] = useState<Study | null>(null);
  const [token, setToken] = useState("");
  const [inviteToken, setInviteToken] = useState("");
  const [error, setError] = useState("");
  const [status, setStatus] = useState("");
  const [busy, setBusy] = useState(false);
  const [withdraw, setWithdraw] = useState(false);
  const ids = useRef<Record<string, string>>({});
  const invitationFragment = useRef<string | null>(null);
  const refresh = useCallback(async () => {
    const response = await workspaceRequest<{ studies: Study[] }>(csrf, "pilots");
    setStudies(response.studies);
    if (selected && response.studies.some(s => s.id === selected)) setData(await workspaceRequest<Detail>(csrf, `pilots/${selected}`));
    else setData(null);
  }, [csrf, selected]);
  useEffect(() => {
    let cancelled = false;
    // Invitation secrets never enter query parameters, analytics or request URLs.
    const fragment = new URLSearchParams(window.location.hash.slice(1));
    const invite = fragment.get("invite") || invitationFragment.current;
    invitationFragment.current = invite;
    if (invite) window.history.replaceState(null, "", window.location.pathname);
    fetch("/api/session", { cache: "no-store" }).then(r => r.json()).then(s => {
      if (cancelled) return;
      if (invite) setToken(invite);
      setCsrf(s.csrf || ""); setAuthenticated(!!s.authenticated); setOperator(!!s.operator);
      if (!s.authenticated) setError("Sign in through the player workspace to access a study.");
    }).catch(() => { if (!cancelled) setError("The local API is unavailable."); });
    return () => { cancelled = true; };
  }, []);
  useEffect(() => {
    if (!authenticated) return;
    const load = () => void refresh().catch(e => setError(e.message));
    load();
  }, [authenticated, refresh]);
  async function act(work: () => Promise<void>) {
    setBusy(true); setError(""); setStatus("");
    try { await work(); await refresh(); } catch (e) { setError(e instanceof Error ? e.message : "Request failed"); } finally { setBusy(false); }
  }
  async function submit(event: React.FormEvent<HTMLFormElement>, operation: string, transform: (fields: Record<string, FormDataEntryValue>) => object = fields => fields, idempotent = false) {
    event.preventDefault(); const form = event.currentTarget;
    const path = operation === "create" ? "pilots" : `pilots/${selected}/${operation}`;
    const fields = Object.fromEntries(new FormData(form));
    const key = `${path}/${String(fields.task_id || "")}`;
    if (idempotent) ids.current[key] ??= crypto.randomUUID();
    await act(async () => {
      const payload = { ...transform(fields), ...(idempotent ? { request_id: ids.current[key] } : {}) };
      const result = await workspaceRequest<{ token?: string; id?: string }>(csrf, path, "POST", payload);
      delete ids.current[key];
      if (result.token) setInviteToken(result.token);
      if (operation === "create" && result.id) setSelected(result.id);
      setStatus("Study record saved. Real scientific and release approval remain separate.");
      form.reset();
    });
  }
  async function download(kind: "reports" | "annotations") {
    await act(async () => {
      const result = kind === "reports" ? await workspaceRequest<Detail>(csrf, `pilots/${selected}`) : await workspaceRequest<object>(csrf, `pilots/${selected}/annotations`, "POST", {});
      const blob = new Blob([JSON.stringify(kind === "reports" ? (result as Detail).reports : result, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob); const link = document.createElement("a"); link.href = url; link.download = `dojopulse-pilot-${kind}.json`; link.click(); URL.revokeObjectURL(url);
    });
  }
  const nullableNumber = (value: FormDataEntryValue) => String(value) === "" ? null : Number(value);
  const bool = (value: FormDataEntryValue) => String(value) === "unknown" ? null : String(value) === "true";
  return <main className="operations pilots">
    <header><span className="brand">DojoPulse / Pilots</span><Link href="/">Player workspace</Link></header>
    <div className="intro"><div className="eyebrow">Local study rehearsal</div><h1>Capture, review<br />and assess the evidence.</h1><p>Real participant intake needs an approved protocol. These tools rehearse a pseudonymous study with synthetic sources. Synthetic results leave G1–G6 NOT_RUN.</p></div>
    {error && <p className="notice error" role="alert">{error}</p>}{status && <p className="notice" role="status">{status}</p>}
    {authenticated && <>
      <section><h2>Join an invited study</h2><label>Invitation token<input value={token} onChange={e => { setToken(e.target.value); setInvitation(null); }} autoComplete="off" /></label>
        <button disabled={busy || !token} onClick={() => void act(async () => { setInvitation(await workspaceRequest<Study>(csrf, "pilot-invitation", "POST", { token })); })}>Review invitation</button>
        {invitation && <form onSubmit={e => { e.preventDefault(); const f = new FormData(e.currentTarget); void act(async () => { const result = await workspaceRequest<{ study_id: string }>(csrf, "pilot-join", "POST", { token, protocol_digest: invitation.protocol_digest, adult: f.has("adult"), accepted: f.has("accepted"), rights: f.has("rights") }); setSelected(result.study_id); setInvitation(null); setToken(""); setStatus("Study consent recorded. You can withdraw from this study at any time."); }); }}>
          <h3>{invitation.title} / {label(invitation.role)}</h3><p>{invitation.protocol.consent}</p><p>Study retention ends {invitation.protocol.audit_ends_at}. Model training permission is separate.</p>
          <label><input type="checkbox" name="adult" required />I am an adult.</label><label><input type="checkbox" name="accepted" required />I accept this specific study protocol.</label>{invitation.role === "PARTICIPANT" && <label><input type="checkbox" name="rights" required />I have permission to share each recording I register with assigned study reviewers.</label>}
          <button disabled={busy}>Accept study invitation</button>
        </form>}
      </section>
      {operator && <section><details><summary>Create a synthetic study</summary><form onSubmit={e => void submit(e, "create", f => ({ title: f.title, dataset_kind: "synthetic" }), true)}><Field name="title" title="Study title" /><p>Dates are frozen now: seven baseline days, two practice days, 28 follow-up days and seven audit days. Real intake is gated.</p><button disabled={busy}>Create study</button></form></details></section>}
      <section><h2>Your studies</h2><label>Selected study<select value={selected} onChange={e => { setSelected(e.target.value); setWithdraw(false); setInviteToken(""); }}><option value="">Select a study</option>{studies.map(s => <option key={s.id} value={s.id}>{s.title} / {label(s.role)} / {label(s.state)}</option>)}</select></label><button disabled={busy} onClick={() => void act(refresh)}>Refresh study</button>{!studies.length && <p>No active study membership yet.</p>}</section>
      {data && <>
        <section><h2>{data.title}</h2><p>{label(data.role)} · {data.dataset_kind} · {label(data.state)} · revision {data.revision}</p>{data.pseudonym && <p className="muted">Your study pseudonym: {data.pseudonym}</p>}<details><summary>Frozen study protocol</summary><p>{data.protocol.consent}</p><dl><dt>Target</dt><dd>{data.protocol.target}</dd><dt>Baseline cutoff</dt><dd>{data.protocol.baseline_end}</dd><dt>Follow-up starts</dt><dd>{data.protocol.followup_start}</dd><dt>Follow-up ends</dt><dd>{data.protocol.ends_at}</dd></dl></details>
          {withdraw ? <><p>{data.role === "MANAGER" ? "Close this study and erase every member's study evidence?" : "Withdraw and erase your study evidence, labels and dependent reports?"} Private recordings remain in their owner&#39;s workspace under their original retention policy.</p><button disabled={busy} onClick={() => void act(async () => { await workspaceRequest(csrf, `pilots/${selected}`, "DELETE"); setSelected(""); setWithdraw(false); setStatus("Study access revoked and dependent study evidence erased."); })}>{data.role === "MANAGER" ? "Confirm study closure" : "Confirm study withdrawal"}</button><button className="secondary" onClick={() => setWithdraw(false)}>Keep study access</button></> : <button className="secondary" disabled={busy} onClick={() => setWithdraw(true)}>{data.role === "MANAGER" ? "Close study" : "Withdraw from study"}</button>}
        </section>
        {data.role === "MANAGER" && data.state === "COLLECTING" && <>
          <section><h2>Invite independent members</h2><form onSubmit={e => void submit(e, "invite")}><Choice name="role" title="Invited role" options={["PARTICIPANT", "REVIEWER", "ADJUDICATOR", "EXPERT"]} /><button disabled={busy}>Create invitation</button></form>{inviteToken && <><label>Invitation link<textarea readOnly value={`${window.location.origin}/pilots#invite=${encodeURIComponent(inviteToken)}`} /></label><p>Give this 24-hour invitation to the intended role holder. They must accept themselves. One role per account per study.</p></>}</section>
          <section><h2>Assign participant splits</h2><form onSubmit={e => void submit(e, "split")}><label>Participant<select name="enrollment_id" required>{data.members.filter(m => m.role === "PARTICIPANT").map(m => <option key={m.id} value={m.id}>{m.pseudonym} / {m.split}</option>)}</select></label><Choice name="split" title="Player-disjoint split" options={["development", "validation", "held-out"]} /><Choice name="comparison_order" title="Prospective comparator allocation" options={["UNASSIGNED", "STRUCTURED_FIRST", "NATIVE_FIRST", "USUAL_FIRST"]} /><p>Assign before the first session. Balance and review comparison allocation separately. Held-out labels stay hidden from the manager until source inputs are frozen.</p><button disabled={busy}>Assign split and allocation</button></form></section>
        </>}
        {data.role === "PARTICIPANT" && data.state === "COLLECTING" && <>
          <section><h2>Record every session</h2><p>Include missing recordings, invalid captures and zero-opportunity sessions. Leave unknown durations blank. Use a private source&#39;s chronology for captured sessions, or enter a code and time for other attempts.</p><form onSubmit={e => void submit(e, "session", f => { const source = data.available_sources.find(s => s.asset_id === f.source_chronology); const { source_chronology: ignored, ...fields } = f; void ignored; return { ...fields, code: source ? source.session_id : f.code, played_at: source ? source.played_at : new Date(String(f.played_at)).toISOString(), playable_seconds: nullableNumber(f.playable_seconds), setup_seconds: nullableNumber(f.setup_seconds), insight_seconds: nullableNumber(f.insight_seconds), useful: bool(f.useful), unaided: f.unaided === "on" }; }, true)}>
            <label>Use private source chronology<select name="source_chronology"><option value="">Enter a session code and play time</option>{data.available_sources.map(s => <option key={s.asset_id} value={s.asset_id}>{s.session_id} / {s.played_at}</option>)}</select></label><Field name="code" title="Session code" required={false} /><Choice name="phase" title="Study phase" options={["BASELINE", "PRACTICE", "FOLLOWUP", "NATIVE", "USUAL"]} /><Field name="played_at" title="Original play time (local)" type="datetime-local" required={false} /><Choice name="state" title="Capture state" options={["CAPTURED", "MISSING", "ZERO_OPPORTUNITIES", "INVALID"]} /><Field name="playable_seconds" title="Playable seconds" type="number" min={0} max={86400} required={false} /><Field name="setup_seconds" title="Setup seconds" type="number" min={0} max={86400} required={false} /><label><input type="checkbox" name="unaided" />I completed setup without assistance.</label><Choice name="useful" title="Useful insight" options={["unknown", "true", "false"]} /><Field name="insight_seconds" title="Seconds to useful insight" type="number" min={0} max={86400} required={false} /><button disabled={busy}>Record session</button>
          </form></section>
          <section><h2>Register a retained source</h2><p>Upload and validate recordings in your private workspace first. Registering grants only assigned study reviewers access until study consent expires.</p><form onSubmit={e => void submit(e, "capture")}><label>Captured session<select name="session_id" required>{data.sessions.filter(s => s.state === "CAPTURED").map(s => <option key={s.id} value={s.id}>{s.code} / {s.played_at}</option>)}</select></label><label>Private source<select name="asset_id" required>{data.available_sources.map(s => <option key={s.asset_id} value={s.asset_id}>{s.asset_id.slice(0, 8)} / {s.played_at} / {s.game_build}</option>)}</select></label><button disabled={busy || !data.available_sources.length}>Register source</button></form></section>
          <section><details><summary>Link a reviewed canonical evaluation</summary><p>Use the exact study target, dates and only registered study sources. Pilot labels require separate operator publication before the normal evaluation pipeline can use them.</p><form onSubmit={e => void submit(e, "evaluation")}><Field name="evaluation_id" title="Latest evaluation ID" /><button disabled={busy}>Link evaluation</button></form></details></section>
        </>}
        {data.sessions.length > 0 && <section><h2>Session inventory</h2><ul>{data.sessions.map(s => <li key={s.id}>{s.code} / {label(s.phase)} / {label(s.state)} / {s.played_at}</li>)}</ul></section>}
        {data.role === "MANAGER" && data.state === "COLLECTING" && <section><h2>Assign source review</h2><p>QC covers the entire validated source. Target/trial windows cannot overlap. Optional predictions are frozen before review; reviewers cannot see them.</p><form onSubmit={e => void submit(e, "task", f => ({ capture_id: f.capture_id, kind: f.kind, start_us: Number(f.start_us), end_us: Number(f.end_us), reviewer_one: f.reviewer_one, reviewer_two: f.reviewer_two, adjudicator: f.adjudicator, prediction: f.detector_version ? { detector_version: f.detector_version, start_us: Number(f.prediction_start_us), eligibility: f.prediction_eligibility, outcome: f.prediction_outcome } : null }), true)}>
          <label>Registered capture<select name="capture_id" required>{data.captures.map(c => <option key={c.id} value={c.id}>{c.id.slice(0, 8)} / {c.game_build} / {c.duration_seconds}s</option>)}</select></label><Choice name="kind" title="Review task" options={["QC", "TARGET", "TRIAL"]} /><Field name="start_us" title="Window start, microseconds" type="number" min={0} max={600000000} /><Field name="end_us" title="Window end, microseconds" type="number" min={0} max={600000000} />{["reviewer_one", "reviewer_two", "adjudicator"].map(name => <label key={name}>{label(name)}<select name={name} required>{data.members.filter(m => m.role === (name === "adjudicator" ? "ADJUDICATOR" : "REVIEWER")).map(m => <option key={m.id} value={m.id}>{m.pseudonym}</option>)}</select></label>)}
          <details><summary>Optional frozen detector prediction</summary><Field name="detector_version" title="Detector version" required={false} /><Field name="prediction_start_us" title="Predicted start, microseconds" type="number" min={0} max={600000000} required={false} /><Choice name="prediction_eligibility" title="Predicted eligibility" options={["UNKNOWN", "ELIGIBLE", "INELIGIBLE"]} /><Choice name="prediction_outcome" title="Predicted outcome" options={["UNKNOWN", "SUCCESS", "FAILURE"]} /></details><button disabled={busy || !data.captures.length}>Assign review task</button>
        </form></section>}
        <section><h2>{data.role === "MANAGER" ? "Review progress" : "Assigned review queue"}</h2><p>Other labels appear only after both independent reviewers submit. Disagreements require the assigned third reviewer.</p>{!data.tasks.length && <p>No assigned tasks.</p>}{data.tasks.map(task => <article className="result" key={task.id}><h3>{task.kind} / {task.id.slice(0, 8)}</h3><p>{task.start_us}–{task.end_us} microseconds / {label(task.state)}</p>
          {task.can_review && <><video controls preload="none" src={task.media_url} aria-label={`Review recording ${task.id.slice(0, 8)}`} /><form onSubmit={e => void submit(e, "review", f => ({ task_id: task.id, seconds: Number(f.seconds), label: task.kind === "QC" ? { visibility: f.visibility, profile_valid: f.profile_valid === "true", target_absent: f.target_absent === "true" } : { visibility: f.visibility, conditions: { ...Object.fromEntries(conditions.map(c => [c, bool(f[c])])), uncertainty_us: Number(f.uncertainty_us) } } }), true)}>
            <input type="hidden" name="task_id" value={task.id} /><Choice name="visibility" title="Evidence visibility" options={["UNOBSERVABLE", "UNCERTAIN", "RESOLVABLE"]} />{task.kind === "QC" ? <><Choice name="profile_valid" title="Capture profile valid" options={["false", "true"]} /><Choice name="target_absent" title="Target absent in source" options={["false", "true"]} /></> : <><div className="pilot-conditions">{conditions.map(c => <Choice key={c} name={c} title={label(c)} options={["unknown", "true", "false"]} />)}</div><Field name="uncertainty_us" title="Timestamp uncertainty, microseconds" type="number" min={0} max={1000000} /></>}<Field name="seconds" title="Measured review seconds" type="number" min={1} max={28800} /><p>Submitted reviews are immutable. Unknown evidence must remain unknown.</p><button disabled={busy}>Submit independent review</button>
          </form></>}{task.submitted && <p>Your review is submitted.</p>}{task.reviews.length > 0 && <details><summary>Completed independent labels</summary><pre>{JSON.stringify(task.reviews, null, 2)}</pre></details>}{task.final_label && <details><summary>Resolved label</summary><pre>{JSON.stringify(task.final_label, null, 2)}</pre></details>}
        </article>)}</section>
        {data.role === "MANAGER" && <section><h2>Freeze and assess the dataset</h2><p>Freezing prevents new members, sessions, captures, tasks and predictions. Assigned reviews may finish; each new review invalidates older reports. Withdrawal always remains available.</p><button disabled={busy || data.state !== "COLLECTING"} onClick={() => void act(async () => { await workspaceRequest(csrf, `pilots/${selected}/freeze`, "POST", {}); setStatus("Source inputs frozen. Independent reviews can still finish."); })}>Freeze source inputs</button><button disabled={busy || data.state !== "FROZEN"} onClick={() => void act(async () => { await workspaceRequest(csrf, `pilots/${selected}/reports`, "POST", {}); setStatus("Six evidence reports generated. Scientific gates remain NOT_RUN."); })}>Generate G1–G6 reports</button><button className="secondary" disabled={busy || !data.reports.length} onClick={() => void download("reports")}>Download current reports</button><button className="secondary" disabled={busy || data.state !== "FROZEN"} onClick={() => void download("annotations")}>Export reviewed annotations</button></section>}
        {data.reports.map(report => <section key={report.id}><h2>{report.gate} / {label(report.data.proposed_action)}</h2><p>{report.data.scope} · scientific gate {report.data.scientific_gate}. Candidate criteria {report.data.candidate_criteria_met ? "met" : "not met"}.</p><details><summary>Metrics and missing evidence</summary><pre>{JSON.stringify(report.data.metrics, null, 2)}</pre></details>{report.decision ? <p>Independent decision: {label(report.decision.action)} / {label(report.decision.reason)} / {report.decision.reference}</p> : data.role === "EXPERT" && <form onSubmit={e => void submit(e, "decision", f => ({ ...f, report_id: report.id }))}><Choice name="action" title="Gate decision" options={["WAIT", "NARROW", "STOP", "CONTINUE"]} /><Choice name="reason" title="Decision reason" options={["INSUFFICIENT_SAMPLE", "UNOBSERVABLE", "RECOGNITION", "INGESTION", "PRACTICE", "EXPOSURE", "COMPARABILITY", "UTILITY", "CRITERIA_MET"]} /><Field name="reference" title="Offline decision reference code" /><p>This records a study decision. It does not approve gameplay recognition, knowledge or production release.</p><button disabled={busy}>Record independent decision</button></form>}</section>)}
      </>}
    </>}
  </main>;
}
