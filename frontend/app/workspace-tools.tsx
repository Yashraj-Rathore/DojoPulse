"use client";
import { useCallback, useEffect, useState } from "react";
import { workspaceRequest as request } from "./workspace-api";

type Preferences = { username: string; display_timezone: string; onboarding_completed_at: string | null; analysis_notices: boolean; practice_notices: boolean; followup_notices: boolean; processing_consent_at: string | null; training_consent_at: string | null };
type Notice = { key: string; message: string; href: string; category: string };
type Feedback = { id: string; category: string; status: string; message: string };

export default function WorkspaceTools({ csrf, onTimezone, onDeleted, reportEvent }: { csrf: string; onTimezone: (zone: string) => void; onDeleted: () => void; reportEvent: string }) {
  const [prefs, setPrefs] = useState<Preferences | null>(null), [notices, setNotices] = useState<Notice[]>([]), [remaining, setRemaining] = useState(0);
  const [feedback, setFeedback] = useState<Feedback[]>([]), [error, setError] = useState(""), [message, setMessage] = useState(""), [busy, setBusy] = useState(false);
  const [ack, setAck] = useState(false), [deleting, setDeleting] = useState(false), [feedbackKey, setFeedbackKey] = useState(() => crypto.randomUUID());
  useEffect(() => { if (reportEvent) document.getElementById("feedback-message")?.focus(); }, [reportEvent]);
  const load = useCallback(async (signal?: AbortSignal) => {
    const [p, n, f] = await Promise.all([request<Preferences>(csrf, "preferences", "GET", undefined, signal), request<{notices: Notice[]; remaining: number}>(csrf, "notices", "GET", undefined, signal), request<{feedback: Feedback[]}>(csrf, "feedback", "GET", undefined, signal)]);
    if (!signal?.aborted) { setPrefs(p); onTimezone(p.display_timezone || "UTC"); setNotices(n.notices || []); setRemaining(n.remaining || 0); setFeedback(f.feedback || []); }
  }, [csrf, onTimezone]);
  useEffect(() => { const controller = new AbortController(); const refresh = () => { if (document.visibilityState === "visible") void load(controller.signal).catch(e => { if (!controller.signal.aborted) setError(e.message); }); }; refresh(); const timer = setInterval(refresh, 15000); return () => { controller.abort(); clearInterval(timer); }; }, [load]);
  async function act(work: () => Promise<void>) { setBusy(true); setError(""); setMessage(""); try { await work(); await load(); } catch (e) { setError(e instanceof Error ? e.message : "Try again."); } finally { setBusy(false); } }
  return <section id="workspace" className="wide" aria-labelledby="workspace-heading">
    <h2 id="workspace-heading">Your workspace</h2>
    {error && <p role="alert" className="notice error">Workspace controls: {error} <button onClick={() => void act(async () => {})} disabled={busy}>Retry workspace controls</button></p>}
    {message && <p role="status" className="notice">{message}</p>}
    <details open={prefs ? !prefs.onboarding_completed_at : true}><summary>Start here: supported scope and next steps</summary>
      <p>DojoPulse is a local research prototype for Tekken 8. The candidate situation is Jin blocking Jin’s u/f+4. No build, automatic detector or drill is released for real-player coaching yet.</p>
      <ol><li>Confirm a player in <a href="#matches">match history</a>. Current sources are fictional demos; names and real IDs cannot be looked up yet.</li><li>Use a supported <a href="#capture">recording</a> when gameplay evidence is needed. Match results alone do not establish missed punishes.</li><li><a href="#evidence">Inspect reviewed evidence</a>, select complete baseline captures, assign an approved drill, and freeze a plan before practice.</li><li>Record practice and later comparable matches. A review operator must validate evidence; success is never assumed.</li></ol>
      <p>Capture: Steam PC, English UI, Jin vs Jin, 1080p constant 60 fps, SDR H.264 MP4, up to 10 minutes / 512 MiB. Preserve HUD, input histories, frame information and battle status. Record the exact build and original play time.</p>
      {!prefs?.onboarding_completed_at && <><label><input type="checkbox" checked={ack} onChange={e => setAck(e.target.checked)} />I understand the supported scope, review requirements and current limitations.</label><button disabled={busy || !ack || !prefs} onClick={() => void act(async () => { await request(csrf, "preferences", "PATCH", { complete_onboarding: true }); setMessage("Setup guide acknowledged. Start with your player and matches."); })}>Complete setup guide</button></>}
    </details>
    <details><summary>Updates ({notices.length}{remaining ? "+" : ""})</summary><p className="muted">In-app only, refreshed while this page is open. Latest 100 records per category. Dismissals persist across sessions.</p>
      {!notices.length && <p>No new updates for your enabled categories.</p>}
      {notices.map(n => <div className="result" key={n.key}><a href={n.href}>{n.message}</a><button className="secondary" disabled={busy} aria-label={`Dismiss ${n.message}`} onClick={() => void act(async () => { await request(csrf, "notices", "POST", { key: n.key }); })}>Dismiss</button></div>)}
      {remaining > 0 && <p>{remaining} more updates will appear as you dismiss these.</p>}
    </details>
    <details id="account"><summary>Account, privacy and preferences</summary>
      <p>Workspace: {prefs?.username || "loading"}. Media is private to your account. Processing consent is required for each import/upload; model-training consent is separate and is {prefs?.training_consent_at ? "recorded" : "not granted"}.</p>
      <p>Recordings are retained for at most 60 days from upload in this local workflow. Removing evidence withdraws dependent conclusions. Stop syncing from match history; delete recordings there to withdraw their processing. Hosted backups and provider deletion are not available in this prototype.</p>
      {prefs && <form key={[prefs.display_timezone, prefs.analysis_notices, prefs.practice_notices, prefs.followup_notices].join(":")} onSubmit={e => { e.preventDefault(); const form = new FormData(e.currentTarget); void act(async () => { await request(csrf, "preferences", "PATCH", { display_timezone: form.get("zone"), analysis_notices: form.has("analysis"), practice_notices: form.has("practice"), followup_notices: form.has("followup") }); setMessage("Preferences saved. No external notifications are sent."); }); }}>
        <label htmlFor="display-zone">Display times in</label><select id="display-zone" name="zone" defaultValue={prefs.display_timezone || "UTC"}><option value="UTC">UTC</option><option value="browser">My device timezone</option></select>
        <fieldset><legend>In-app notice preferences</legend><label><input type="checkbox" name="analysis" defaultChecked={prefs.analysis_notices} />Analysis and review updates</label><label><input type="checkbox" name="practice" defaultChecked={prefs.practice_notices} />Assigned practice reminders</label><label><input type="checkbox" name="followup" defaultChecked={prefs.followup_notices} />Follow-up window reminders</label></fieldset>
        <button disabled={busy}>Save preferences</button>
      </form>}
      <button className="secondary" disabled={busy} onClick={() => void act(async () => { const data = await request(csrf, "account/export"); const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: "application/json" })); const link = document.createElement("a"); link.href = url; link.download = "dojopulse-workspace.json"; document.body.append(link); link.click(); link.remove(); setTimeout(() => URL.revokeObjectURL(url), 1000); setMessage("Workspace export downloaded. Keep it private."); })}>Download my workspace data (JSON)</button><p className="muted">Export includes your records and preferences; private videos are separate downloads from evidence review. Raw provider payloads and other people’s identifiers are omitted. The local export limit is 10,000 records.</p>
      <button className="secondary" disabled={busy} onClick={() => void request(csrf, "session", "DELETE").then(onDeleted).catch(e => setError(e.message))}>Sign out</button>
      <button className="secondary" disabled={busy} onClick={() => setDeleting(!deleting)}>Delete my workspace</button>
      {deleting && <form className="notice error" onSubmit={e => { e.preventDefault(); const body = Object.fromEntries(new FormData(e.currentTarget)); setBusy(true); setError(""); void request(csrf, "account", "DELETE", body).then(onDeleted).catch(e => setError(e.message)).finally(() => setBusy(false)); }}>
        <p>This disables your account, stops imports, deletes local media and personal source links, and withdraws dependent evidence. Minimal audit tombstones remain. This cannot be undone; export first if needed.</p>
        <label htmlFor="delete-password">Current password</label><input id="delete-password" name="password" type="password" autoComplete="current-password" required />
        <label htmlFor="delete-confirm">Type DELETE MY WORKSPACE</label><input id="delete-confirm" name="confirmation" required pattern="DELETE MY WORKSPACE" autoComplete="off" />
        <button disabled={busy}>Confirm permanent deletion</button><button type="button" className="secondary" onClick={() => setDeleting(false)}>Keep my workspace</button>
      </form>}
    </details>
    <details id="support" open={reportEvent ? true : undefined}><summary>Help, feedback and correction requests</summary>
      <dl><dt>Queued or processing</dt><dd>Keep the capture. The local operator must run the worker. Refresh history to see progress.</dd><dt>Review required or correction pending</dt><dd>Media validation is separate from attribution and gameplay review. A local operator must review it; do not interpret pending results as failures.</dd><dt>Failed or expired recording</dt><dd>Check the capture profile. Reprocess an available recording, or attach a replacement after removal. Deleted/expired evidence cannot support conclusions.</dd><dt>Unknown or inconclusive</dt><dd>Insufficient visibility, exposure or comparable evidence limits the conclusion. Gather eligible independent sessions without selecting only favorable attempts.</dd></dl>
      <p>Feedback stays in this workspace’s operator queue. Nothing is emailed or sent to a provider. There is no promised response time. Do not include passwords, private keys or unnecessary opponent information.</p>
      <form onChange={() => setFeedbackKey(crypto.randomUUID())} onSubmit={e => { e.preventDefault(); const form = e.currentTarget; const values = Object.fromEntries(new FormData(form)); void act(async () => { const saved = await request<{id: string}>(csrf, "feedback", "POST", { ...values, event_id: reportEvent || null, request_id: feedbackKey }); setMessage(`Feedback saved locally. Reference: ${saved.id}`); form.reset(); setFeedbackKey(crypto.randomUUID()); }); }}>
        {reportEvent && <p className="muted">Correction reference: {reportEvent}. Submitting a request does not change reviewed evidence.</p>}
        <label htmlFor="feedback-category">Feedback category</label><select key={reportEvent} id="feedback-category" name="category" defaultValue={reportEvent ? "CORRECTION" : "QUESTION"}><option value="QUESTION">Question</option><option value="PROBLEM">Problem</option><option value="CORRECTION">Evidence correction</option><option value="SUGGESTION">Suggestion</option></select>
        <label htmlFor="feedback-message">What happened or what should change?</label><textarea id="feedback-message" name="message" required minLength={5} maxLength={2000} rows={4} />
        <button disabled={busy}>Save feedback</button>
      </form>
      {feedback.length > 0 && <ul aria-label="Your feedback requests">{feedback.map(f => <li key={f.id}>{f.category.toLowerCase()}: {f.message} — {f.status.toLowerCase()} <small>({f.id})</small></li>)}</ul>}
    </details>
  </section>;
}
