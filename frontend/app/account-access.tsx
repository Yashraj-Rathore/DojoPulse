"use client";

import { useEffect, useRef, useState } from "react";
import { workspaceRequest as request } from "./workspace-api";

export type AccountPolicy = { version: string; registration_enabled: boolean; policies: Record<string, string> };
type Mode = "" | "register" | "recover" | "resend" | "verify" | "reset";

export default function AccountAccess({ csrf, authenticated }: { csrf: string; authenticated: boolean }) {
  const [policy, setPolicy] = useState<AccountPolicy | null>(null);
  const [mode, setMode] = useState<Mode>("");
  const [token, setToken] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const pendingLink = useRef<{ mode: Mode; token: string } | null>(null);

  useEffect(() => {
    const match = /^#account=(verify|reset):([A-Za-z0-9_-]{43})$/.exec(window.location.hash);
    if (match) {
      pendingLink.current = { mode: match[1] as Mode, token: match[2] };
      window.history.replaceState(null, "", window.location.pathname + window.location.search);
    }
    if (authenticated && !pendingLink.current) return;
    const controller = new AbortController();
    void request<AccountPolicy>(csrf, "account/policy", "GET", undefined, controller.signal).then(value => {
      if (controller.signal.aborted) return;
      setPolicy(value.version ? value : null);
      if (pendingLink.current) {
        setMode(pendingLink.current.mode); setToken(pendingLink.current.token);
      }
    }).catch(() => { /* Sign-in remains usable when registration is unavailable. */ });
    return () => controller.abort();
  }, [csrf, authenticated]);

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const values = new FormData(form);
    setBusy(true); setError(""); setMessage("");
    try {
      if (mode === "register") {
        await request(csrf, "account/register", "POST", {
          username: values.get("username"), email: values.get("email"), password: values.get("password"),
          policy_version: policy?.version, accepted_terms: values.get("terms") === "on",
        });
      } else if (mode === "recover" || mode === "resend") {
        await request(csrf, "account/link", "POST", { email: values.get("email"), purpose: mode === "recover" ? "RESET" : "VERIFY" });
      } else {
        await request(csrf, "account/confirm", "POST", {
          token, purpose: mode === "verify" ? "VERIFY" : "RESET",
          ...(mode === "reset" ? { password: values.get("password") } : {}),
        });
      }
      setMessage(mode === "verify" || mode === "reset" ? "Confirmed. You can now sign in." : "If these details are eligible, a link will be prepared in the local test mailbox. No live email is sent.");
      form.reset(); setMode(""); setToken(""); pendingLink.current = null;
    } catch (problem) { setError(problem instanceof Error ? problem.message : "Account request failed."); }
    finally { setBusy(false); }
  }

  if (authenticated && !mode && !message) return null;
  return <section className="login account-access" aria-labelledby="account-access-heading">
    <h2 id="account-access-heading">Account access</h2>
    {!authenticated && <div className="actions">
      <button className="secondary" disabled={busy || !policy?.registration_enabled} onClick={() => { setMode("register"); setError(""); }}>Create account</button>
      <button className="secondary" disabled={busy || !policy?.registration_enabled} onClick={() => { setMode("recover"); setError(""); }}>Forgot password</button>
      <button className="secondary" disabled={busy || !policy?.registration_enabled} onClick={() => { setMode("resend"); setError(""); }}>Resend verification</button>
    </div>}
    <p className="muted">{policy?.registration_enabled ? "Local account testing is enabled. Verification and recovery links are delivered only to a private test mailbox." : "New account registration and email recovery are unavailable in this workspace."}</p>
    {error && <p className="notice error" role="alert">{error}</p>}
    {message && <p className="notice" role="status">{message}</p>}
    {mode && <form key={mode} onSubmit={submit} aria-label="Account access form">
      <h3>{({ register: "Create your account", recover: "Recover your password", resend: "Request a new verification link", verify: "Verify your email", reset: "Set a new password" } as Record<string, string>)[mode]}</h3>
      {mode === "register" && <label>New username<input name="username" minLength={3} maxLength={30} pattern="[a-zA-Z0-9][a-zA-Z0-9_.-]{2,29}" autoComplete="username" required /></label>}
      {["register", "recover", "resend"].includes(mode) && <label>Email address<input name="email" type="email" maxLength={254} autoComplete="email" required /></label>}
      {["register", "reset"].includes(mode) && <label>New password (at least 12 characters)<input name="password" type="password" minLength={12} maxLength={256} autoComplete="new-password" required /></label>}
      {mode === "register" && <><p>{policy?.policies.TERMS}</p><label><input type="checkbox" name="terms" required />I accept this local account policy ({policy?.version}).</label></>}
      {mode === "verify" && <p>Confirm to verify the email address associated with this link.</p>}
      <button disabled={busy || !policy?.registration_enabled}>{busy ? "Working…" : "Confirm account request"}</button>
      <button type="button" className="secondary" disabled={busy} onClick={() => { setMode(""); setToken(""); pendingLink.current = null; }}>Cancel</button>
    </form>}
  </section>;
}
