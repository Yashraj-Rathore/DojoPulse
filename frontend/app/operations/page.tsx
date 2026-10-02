"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";

type Objective = { value: number | null; samples: number; target: number; state: string; approval: string };
type Cost = { scope: string; period_start: string; period_end: string; total_usd: string | null; missing_components: string[]; per_unit_usd: Record<string, string | null>; denominators: Record<string, number> };
type Snapshot = { generated_at: string; scope: string; days: number; processing_paused: boolean; counts: Record<string, number>; alerts: string[]; oldest_queue_seconds: number; budget: Record<string, number>; objectives: Record<string, Objective>; costs: Cost[]; missing_elapsed_attempts: number; coverage_note: string };
const label = (value: string) => value.toLowerCase().replaceAll("_", " ");
const number = (value: number | null) => value === null ? "Unknown" : value.toLocaleString(undefined, { maximumFractionDigits: 3 });

export default function Operations() {
  const [data, setData] = useState<Snapshot | null>(null);
  const [days, setDays] = useState("1");
  const [csrf, setCsrf] = useState("");
  const [error, setError] = useState("");
  const [status, setStatus] = useState("");
  const [busy, setBusy] = useState(false);
  const [operator, setOperator] = useState(false);
  const workRequest = useRef<string | null>(null);
  const refresh = useCallback(async () => {
    const response = await fetch(`/api/operations?days=${days}`, { credentials: "same-origin", cache: "no-store" });
    const json = await response.json();
    if (!response.ok) throw new Error(json.detail || json.error || "Operations unavailable");
    setData(json); setError("");
  }, [days]);
  useEffect(() => {
    let cancelled = false;
    fetch("/api/session", { cache: "no-store" }).then(r => r.json()).then(session => {
      if (cancelled) return;
      setCsrf(session.csrf || "");
      if (!session.authenticated || !session.operator) { setError("Operator access required. Sign in with an active staff account."); return; }
      setOperator(true);
    }).catch(() => { if (!cancelled) setError("The local API is unavailable."); });
    return () => { cancelled = true; };
  }, []);
  useEffect(() => {
    if (!operator) return;
    const load = () => void refresh().catch(e => setError(e.message));
    load();
  }, [operator, refresh]);
  async function record(event: React.FormEvent<HTMLFormElement>, kind: "work" | "cost") {
    event.preventDefault(); setBusy(true); setError(""); setStatus("");
    const form = event.currentTarget;
    const fields = Object.fromEntries(new FormData(form));
    if (kind === "work") workRequest.current ??= crypto.randomUUID();
    const payload = kind === "work" ? { ...fields, seconds: Number(fields.seconds), request_id: workRequest.current } : fields;
    try {
      const response = await fetch(`/api/operations/${kind}`, { method: "POST", credentials: "same-origin", headers: { "Content-Type": "application/json", "X-CSRFToken": csrf }, body: JSON.stringify(payload) });
      if (!response.ok) throw new Error("Measurement was not recorded. Check the fields and access, then retry.");
      if (kind === "work") workRequest.current = null;
      setStatus("Measurement recorded. Synthetic measurements remain separate from observed use.");
      form.reset(); await refresh();
    } catch (e) { setError(e instanceof Error ? e.message : "Request failed"); } finally { setBusy(false); }
  }
  const today = new Date().toISOString().slice(0, 10);
  return <main className="operations">
    <header><span className="brand">DojoPulse / Operations</span><Link href="/">Player workspace</Link></header>
    <div className="intro"><div className="eyebrow">Local operator workspace</div><h1>Capacity, failures<br />and measured cost.</h1><p>These measurements describe software operations. Gameplay validation and hosted release qualification remain pending.</p></div>
    {error && <p className="notice error" role="alert">{error}</p>}
    {status && <p className="notice" role="status">{status}</p>}
    {operator && <><section aria-label="Reporting window"><label htmlFor="ops-days">Whole UTC days, including today</label><select id="ops-days" value={days} onChange={e => setDays(e.target.value)}>{[1, 7, 30].map(d => <option key={d} value={d}>{d} day{d > 1 ? "s" : ""}</option>)}</select><button disabled={busy} onClick={() => void refresh().catch(e => setError(e.message))}>Refresh measurements</button></section>
    {!data ? <p role="status">Loading measurements…</p> : <>
      <p className="muted">Updated {new Date(data.generated_at).toLocaleString()}. {data.scope}</p>
      <section aria-label="Operational alerts"><h2>Needs attention</h2><p>Optional processing: {data.processing_paused ? "paused" : "enabled"}.</p>{data.alerts.length ? <ul>{data.alerts.map(a => <li key={a}>{label(a)}</li>)}</ul> : <p>No configured operational alerts in this snapshot.</p>}<p className="muted">This page does not send pages or notifications. Follow the operations runbook for escalation.</p></section>
      <div className="grid"><section><h2>Work and failures</h2><dl>{Object.entries(data.counts).map(([key, value]) => <div key={key}><dt>{label(key)}</dt><dd>{number(value)}</dd></div>)}<dt>Oldest queued work, seconds</dt><dd>{number(data.oldest_queue_seconds)}</dd></dl></section>
      <section><h2>Global daily budget</h2><dl>{Object.entries(data.budget).map(([key, value]) => <div key={key}><dt>{label(key)}, seconds</dt><dd>{number(value)}</dd></div>)}</dl><p>Reservations remain held until physical work stops, including after cancellation and across midnight.</p></section>
      <section className="wide"><h2>Proposed service objectives</h2><p>Targets require release approval and representative evidence. Fewer than 20 samples produces insufficient data.</p><div className="scroll"><table><thead><tr><th>Measure</th><th>Observed</th><th>Proposed target</th><th>Samples</th><th>State</th></tr></thead><tbody>{Object.entries(data.objectives).map(([key, value]) => <tr key={key}><th scope="row">{label(key)}</th><td data-label="Observed">{number(value.value)}</td><td data-label="Proposed target">{number(value.target)}</td><td data-label="Samples">{value.samples}</td><td data-label="State">{label(value.state)}</td></tr>)}</tbody></table></div><p className="muted">{data.coverage_note} Unmeasured attempt durations: {data.missing_elapsed_attempts}.</p></section>
      {data.costs.map(cost => <section key={cost.scope}><h2>{label(cost.scope)} cost</h2><p>{cost.period_start} through {cost.period_end}, USD.</p><p className="metric">{cost.total_usd === null ? "Unknown" : `$${cost.total_usd}`}</p>{cost.missing_components.length > 0 && <p>Missing: {cost.missing_components.map(label).join(", ")}.</p>}<dl>{Object.entries(cost.per_unit_usd).map(([key, value]) => <div key={key}><dt>Per {label(key)} ({cost.denominators[key]} units)</dt><dd>{value === null ? "Unknown" : `$${value}`}</dd></div>)}</dl><p className="muted">Whole-window allocated cost. Failed analyses and nonpositive comparable results count; observed entries require actual supporting records.</p></section>)}
      </div>
    </>}
    <section><h2>Record review or support time</h2><p>Record actual operator work, or label a rehearsal synthetic. Do not include player details.</p><form onSubmit={e => void record(e, "work")}><label htmlFor="work-kind">Work type</label><select id="work-kind" name="kind"><option value="REVIEW">Review</option><option value="SUPPORT">Support</option></select><label htmlFor="work-seconds">Measured seconds</label><input id="work-seconds" name="seconds" type="number" min="1" max="28800" required /><label htmlFor="work-scope">Time evidence</label><select id="work-scope" name="scope"><option value="SYNTHETIC">Synthetic rehearsal</option><option value="OBSERVED">Observed work</option></select><button disabled={busy}>Record time</button></form></section>
    <section><details><summary>Record a cost observation</summary><p>Use an exact reporting window and one entry per component. Missing components remain unknown; an explicitly verified zero is allowed. Reference an offline record code without names or invoice details.</p><form onSubmit={e => void record(e, "cost")}><label htmlFor="cost-component">Component</label><select id="cost-component" name="component">{["INFRASTRUCTURE", "PROVIDER", "REVIEW", "SUPPORT"].map(c => <option key={c} value={c}>{label(c)}</option>)}</select><label htmlFor="cost-scope">Cost evidence</label><select id="cost-scope" name="scope"><option value="SYNTHETIC">Synthetic rehearsal</option><option value="OBSERVED">Observed cost</option></select><label htmlFor="cost-start">UTC period start</label><input id="cost-start" type="date" name="period_start" defaultValue={today} max={today} required /><label htmlFor="cost-end">UTC period end</label><input id="cost-end" type="date" name="period_end" defaultValue={today} max={today} required /><label htmlFor="cost-amount">Amount, USD</label><input id="cost-amount" type="number" name="amount_usd" min="0" max="999999.999999" step="0.000001" required /><label htmlFor="cost-reference">Evidence reference code</label><input id="cost-reference" name="reference" maxLength={80} pattern="[A-Za-z0-9_-]+" required /><button disabled={busy}>Record cost</button></form></details></section>
    </>}
  </main>;
}
