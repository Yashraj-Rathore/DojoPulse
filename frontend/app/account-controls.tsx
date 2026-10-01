"use client";

import { useEffect, useState } from "react";
import { displayTime, workspaceRequest as request } from "./workspace-api";
import type { AccountPolicy } from "./account-access";

type Scope = "PROCESSING" | "TRAINING";
type Account = {
  email: string | null; email_verified: boolean; processing_withdrawn: boolean;
  processing_consent: boolean; training_consent: boolean; suppressed_matches: number;
  sessions: { id: string; created_at: string; expires_at: string; current: boolean }[];
  consent_history: { id: string; scope: string; action: string; policy_version: string; created_at: string }[];
};

export default function AccountControls({ csrf }: { csrf: string }) {
  const [open, setOpen] = useState(false);
  const [account, setAccount] = useState<Account | null>(null);
  const [policy, setPolicy] = useState<AccountPolicy | null>(null);
  const [reload, setReload] = useState(0);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [pending, setPending] = useState<{ scope: Scope; action: "GRANT" | "WITHDRAW" } | null>(null);
  useEffect(() => {
    if (!open) return;
    const controller = new AbortController();
    void Promise.all([
      request<Account>(csrf, "account/details", "GET", undefined, controller.signal),
      request<AccountPolicy>(csrf, "account/policy", "GET", undefined, controller.signal),
    ]).then(([details, terms]) => { if (!controller.signal.aborted) { setAccount(details); setPolicy(terms); } })
      .catch(problem => { if (!controller.signal.aborted) setError(problem instanceof Error ? problem.message : "Account details unavailable."); });
    return () => controller.abort();
  }, [csrf, open, reload]);
  async function act(work: () => Promise<void>) {
    setBusy(true); setError(""); setMessage("");
    try { await work(); setReload(value => value + 1); }
    catch (problem) { setError(problem instanceof Error ? problem.message : "Account update failed."); }
    finally { setBusy(false); }
  }
  return <section className="wide" id="account-security"><details onToggle={event => setOpen(event.currentTarget.open)}>
    <summary>Account security and consent</summary>
    {error && <p role="alert" className="notice error">{error}</p>}
    {message && <p role="status" className="notice">{message}</p>}
    {open && !account && !error && <p role="status">Loading account details…</p>}
    {account && policy && <>
      <h3>Email and password</h3>
      <p>{account.email || "No verified address configured"} · {account.email_verified ? "Verified" : "Unverified"}</p>
      <p className="muted">Email verification and recovery currently use a private local test mailbox. Changing your address keeps the current address until verification succeeds.</p>
      <div className="history-columns">
        <form aria-label="Change email" onSubmit={event => {
          event.preventDefault(); const form = event.currentTarget; const values = new FormData(form);
          void act(async () => { await request(csrf, "account/email", "POST", { email: values.get("email"), password: values.get("password") }); form.reset(); setMessage("If eligible, a verification link has been prepared in the local test mailbox."); });
        }}>
          <label>Replacement email<input name="email" type="email" maxLength={254} required autoComplete="email" /></label>
          <label>Current password for email change<input name="password" type="password" required maxLength={256} autoComplete="current-password" /></label>
          <button disabled={busy || !policy.registration_enabled}>Verify replacement email</button>
        </form>
        <form aria-label="Change password" onSubmit={event => {
          event.preventDefault(); const values = new FormData(event.currentTarget);
          void act(async () => { await request(csrf, "account/password", "POST", { current_password: values.get("current"), new_password: values.get("replacement") }); window.location.reload(); });
        }}>
          <label>Current password<input name="current" type="password" required maxLength={256} autoComplete="current-password" /></label>
          <label>Replacement password<input name="replacement" type="password" required minLength={12} maxLength={256} autoComplete="new-password" /></label>
          <p className="muted">Changing your password signs out every session, including this one.</p>
          <button disabled={busy}>Change password and sign out</button>
        </form>
      </div>
      <h3>Signed-in sessions</h3>
      {account.sessions.map(session => <div className="result" key={session.id}>
        <p>{session.current ? "This session" : "Other session"} · Started {displayTime(session.created_at)} · Expires {displayTime(session.expires_at)}</p>
        <button className="secondary" disabled={busy} onClick={() => void act(async () => {
          const result = await request<{ signed_out: boolean }>(csrf, `account/sessions/${session.id}`, "DELETE");
          if (result.signed_out) window.location.reload(); else setMessage("Session signed out.");
        })}>Sign out {session.current ? "this session" : "other session"}</button>
      </div>)}
      <button disabled={busy} onClick={() => void act(async () => { await request(csrf, "account/logout-all", "POST"); window.location.reload(); })}>Sign out all sessions</button>
      <h3>Data permissions</h3>
      <p>Workspace processing: {account.processing_withdrawn ? "withdrawn" : account.processing_consent ? "allowed" : "not yet granted"}. Optional model training: {account.training_consent ? "allowed" : "off"}.</p>
      <p className="muted">Withdrawal stops new processing and cancels queued work. Existing records remain available for export or deletion in Workspace settings. Re-enabling does not restart cancelled work. No model-training service is enabled.</p>
      <div className="actions">{(["PROCESSING", "TRAINING"] as Scope[]).map(scope => {
        const granted = scope === "PROCESSING" ? account.processing_consent : account.training_consent;
        return <button className="secondary" key={scope} disabled={busy} onClick={() => setPending({ scope, action: granted ? "WITHDRAW" : "GRANT" })}>
          {granted ? "Withdraw" : "Allow"} {scope === "PROCESSING" ? "workspace processing" : "optional model training"}
        </button>;
      })}</div>
      {pending && <form key={pending.scope + pending.action} aria-label="Confirm data permission" onSubmit={event => {
        event.preventDefault(); void act(async () => {
          await request(csrf, "account/consent", "POST", { ...pending, policy_version: policy.version, request_id: crypto.randomUUID(), confirmed: true });
          setPending(null); setMessage("Data permission updated. A receipt was added to your history.");
        });
      }}><p>{policy.policies[pending.scope]}</p>
        <label><input type="checkbox" required />I confirm this {pending.action === "GRANT" ? "permission" : "withdrawal"} under policy {policy.version}.</label>
        <button disabled={busy}>Confirm data permission</button><button type="button" className="secondary" disabled={busy} onClick={() => setPending(null)}>Cancel</button>
      </form>}
      <p>{account.suppressed_matches} source records suppressed after match deletion. Explicitly re-linking a player will not restore these known matches.</p>
      <details><summary>Recent consent history</summary>
        {account.consent_history.length ? account.consent_history.map(receipt => <p key={receipt.id}>{receipt.scope} · {receipt.action} · {receipt.policy_version} · {displayTime(receipt.created_at)}</p>) : <p>No consent receipts yet.</p>}
        <p className="muted">Showing the latest 100 receipts. Download your account export for retained consent history.</p>
      </details>
    </>}
  </details></section>;
}
