"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";

type Proposal = { id: string; key: string; kind: string; build_key: string; dataset_kind: string; payload: Record<string, unknown>; provenance: Record<string, unknown>; hash: string; state: string; reason: string; author: boolean; can_review: boolean; intact: boolean; effective: boolean; published_key: string | null; reviews: { decision: string; note: string; own: boolean }[]; review_visibility: string; sources: { asset_id: string; source_sha256: string; duration_seconds: number; media_url: string }[] };
type Data = { proposals: Proposal[]; builds: { key: string; platform: string; verified: boolean }[]; sources: { id: string; source_sha256: string; metadata: Record<string, unknown> }[]; definitions: { key: string; kind: string; hash: string }[]; reanalyses: { id: string; match_id: string; target_id: string; run_id: string; run__status: string }[]; real_publication_approved: boolean };
type Impact = { matches: { id: string; game_build: string; dataset_kind: string; state: string }[]; note: string };
const required = ["build_verified", "knowledge_verified", "move_verified", "block_verified", "actor_verified", "standing", "reach_validated", "alignment_validated", "window_complete", "timing_validated", "wall_clear", "resource_independent"];
const templates: Record<string, object> = {
  build: { game_build: "fixture", platform: "synthetic", overlays: ["build-label", "input-history", "frame-display"] },
  move: { game_build: "fixture", build_definition: "rehearsal/build/1", move: "jin.uf4", startup_frames: null, on_block_frames: null, reach_test: "reviewed-reach-fixture", timing_test: "reviewed-timing-fixture" },
  situation: { game_build: "fixture", build_definition: "rehearsal/build/1", supported_semantics: "jin-standing-blocked-uf4/1", trigger: "opponent-jin-uf4-blocked", required_observations: required, unknown_rules: ["unobservable-or-ambiguous"], exclusions: ["wall", "axis", "stance", "resources", "reach"] },
  metric: { game_build: "fixture", build_definition: "rehearsal/build/1", supported_semantics: "jin-standing-blocked-uf4/1", numerator: "eligible-successes", denominator: "eligible-known-outcomes", unknown_policy: "exclude-and-report" },
  knowledge: { game_build: "fixture", build_definition: "rehearsal/build/1", situation_definition: "rehearsal/situation/1", metric_definition: "rehearsal/metric/1", move_versions: ["rehearsal/move/1"] },
  drill: { game_build: "fixture", build_definition: "rehearsal/build/1", situation_definition: "rehearsal/situation/1", metric_definition: "rehearsal/metric/1", knowledge_revision: "rehearsal/knowledge/1", title: "Standing block-punish rehearsal", repetitions: 40, setup: { standing: true, stage: "open-space", spacing: "reviewed" }, native_practice: { opponent: "jin", move: "uf4", candidate: "review-required" } },
  compatibility: { game_build: "fixture", build_definition: "rehearsal/build/1", from_knowledge: "rehearsal/knowledge/1", to_knowledge: "rehearsal/knowledge/2", disposition: "REANALYSIS_REQUIRED", rationale: "reviewed-patch-fixture" },
};

export default function Knowledge() {
  const [data, setData] = useState<Data | null>(null);
  const [csrf, setCsrf] = useState("");
  const [operator, setOperator] = useState(false);
  const [error, setError] = useState("");
  const [status, setStatus] = useState("");
  const [busy, setBusy] = useState(false);
  const [kind, setKind] = useState("build");
  const [payload, setPayload] = useState(JSON.stringify(templates.build, null, 2));
  const [selected, setSelected] = useState("");
  const [mapping, setMapping] = useState("");
  const [impact, setImpact] = useState<Impact | null>(null);
  const [confirmation, setConfirmation] = useState<"retire" | "withdraw" | null>(null);
  const requests = useRef<Record<string, string>>({});
  const requestId = (key: string) => requests.current[key] ??= crypto.randomUUID();
  const refresh = useCallback(async () => {
    const r = await fetch("/api/knowledge", { credentials: "same-origin", cache: "no-store" });
    const json = await r.json();
    if (!r.ok) throw new Error(json.error || json.detail || "Knowledge workspace unavailable");
    setData(json);
  }, []);
  useEffect(() => {
    let cancelled = false;
    fetch("/api/session", { cache: "no-store" }).then(r => r.json()).then(s => {
      if (cancelled) return;
      setCsrf(s.csrf || "");
      if (!s.authenticated || !s.operator) { setError("Operator access required. Sign in with an active staff account."); return; }
      setOperator(true);
    }).catch(() => { if (!cancelled) setError("The local API is unavailable."); });
    return () => { cancelled = true; };
  }, []);
  useEffect(() => {
    if (!operator) return;
    const load = () => void refresh().catch(e => setError(e.message));
    load();
  }, [operator, refresh]);
  async function action(work: () => Promise<void>) {
    setBusy(true); setError(""); setStatus("");
    try { await work(); } catch (e) { setError(e instanceof Error ? e.message : "Request failed"); } finally { setBusy(false); }
  }
  async function post(path: string, value: object) {
    const r = await fetch(`/api/knowledge${path}`, { method: "POST", credentials: "same-origin", headers: { "Content-Type": "application/json", "X-CSRFToken": csrf }, body: JSON.stringify(value) });
    const json = await r.json();
    if (!r.ok) throw new Error(json.error || json.detail || "Operation failed. Check the evidence and retry.");
    return json;
  }
  async function propose(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault(); const form = event.currentTarget; const f = new FormData(form);
    await action(async () => {
      const candidate = JSON.parse(payload);
      const result = await post("", { key: f.get("key"), kind, build_key: f.get("build"), dataset_kind: f.get("scope"), payload: candidate, provenance: { reference: f.get("reference"), rights: f.get("rights"), share_with_reviewers: f.get("sharing") === "on", publish_game_facts: f.get("publishing") === "on" }, asset_ids: f.getAll("sources"), reviewer_one: Number(f.get("reviewer-one")), reviewer_two: Number(f.get("reviewer-two")), request_id: requestId("proposal") });
      delete requests.current.proposal; await refresh(); setSelected(result.id); setStatus("Proposal sealed. Two independent decisions are required before publication.");
    });
  }
  const proposal = data?.proposals.find(p => p.id === selected);
  async function review(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (!proposal) return;
    const f = new FormData(event.currentTarget);
    await action(async () => {
      await post(`/${proposal.id}/review`, { proposal_hash: proposal.hash, decision: f.get("decision"), note: f.get("note"), confirm_reviewed: f.get("reviewed") === "on", request_id: requestId(`review:${proposal.id}`) });
      delete requests.current[`review:${proposal.id}`]; await refresh(); setStatus("Independent review sealed. Corrections require a new proposal.");
    });
  }
  async function release(operation: "publish" | "retire" | "withdraw") {
    if (!proposal) return;
    await action(async () => { await post(`/${proposal.id}/${operation}`, {}); setConfirmation(null); setImpact(null); await refresh(); setStatus(operation === "publish" ? "New immutable version published for this evidence scope. No gameplay facts were created." : "Release grant updated. Historical versions remain in the audit record."); });
  }
  return <main className="knowledge-workspace">
    <header><span className="brand">DojoPulse / Knowledge</span><Link href="/">Player workspace</Link></header>
    <div className="intro"><div className="eyebrow">Local operator workspace</div><h1>Review the facts.<br />Publish a version.</h1><p>Exact builds, move evidence and supported measurement definitions need independent review. Synthetic rehearsals do not establish real game knowledge. Real publication and hosted access remain gated.</p></div>
    {error && <p className="notice error" role="alert">{error}</p>}{status && <p className="notice" role="status">{status}</p>}
    {operator && (!data ? <p role="status">Loading review workspace...</p> : <>
      <section><h2>Evidence review queue</h2><button disabled={busy} onClick={() => void action(refresh)}>Refresh queue</button><label htmlFor="knowledge-selected">Selected proposal</label><select id="knowledge-selected" value={selected} onChange={e => { setSelected(e.target.value); setConfirmation(null); }}><option value="">Choose a proposal</option>{data.proposals.map(p => <option key={p.id} value={p.id}>{p.key} / {p.state} / {p.dataset_kind}</option>)}</select>
      {proposal && <><p><strong>{proposal.key}</strong> / {proposal.kind} / {proposal.dataset_kind} / {proposal.build_key}</p><p>State: {proposal.state}. Current evidence: {proposal.intact ? "intact" : "unavailable or changed"}. Usable release: {proposal.effective ? "yes" : "no"}.</p><p className="muted">Sealed digest: <code>{proposal.hash}</code>{proposal.reason && ` / ${proposal.reason}`}</p><details open><summary>Candidate facts and provenance</summary><pre>{JSON.stringify({ payload: proposal.payload, provenance: proposal.provenance }, null, 2)}</pre></details>
      <h3>Explicitly shared review sources</h3><p>The author authorized assigned reviewers to view each whole recording. Verify build overlays, move identity, reach, timing and exclusions in the source.</p>{proposal.sources.map(s => <div key={s.asset_id}><p>SHA-256: <code>{s.source_sha256}</code> / {s.duration_seconds} seconds</p><video controls preload="none" src={s.media_url} aria-label="Knowledge evidence recording" /></div>)}
      <h3>Independent decisions</h3><p>{proposal.review_visibility}</p>{proposal.reviews.map((r, i) => <p key={i}>{r.own ? "Your decision" : "Independent decision"}: {r.decision}. {r.note}</p>)}
      {proposal.can_review && <form onSubmit={e => void review(e)}><label htmlFor="knowledge-decision">Review decision</label><select id="knowledge-decision" name="decision"><option value="REJECT">Reject / evidence insufficient</option><option value="APPROVE">Approve exact candidate and sources</option></select><label htmlFor="knowledge-note">Evidence review note</label><textarea id="knowledge-note" name="note" maxLength={2000} required /><label className="check"><input type="checkbox" name="reviewed" required />I independently reviewed the complete candidate and its source evidence.</label><button disabled={busy}>Seal independent review</button></form>}
      {proposal.author && <>{proposal.state === "OPEN" && <button disabled={busy || !proposal.intact || proposal.reviews.filter(r => r.decision === "APPROVE").length !== 2 || proposal.dataset_kind === "real" && !data.real_publication_approved} onClick={() => void release("publish")}>Publish new immutable version</button>}{proposal.dataset_kind === "real" && <p>Real publication needs separate current-build, expert, rights and release approval.</p>}{proposal.state === "PUBLISHED" && <button className="secondary" disabled={busy} onClick={() => setConfirmation("retire")}>Retire from new use</button>}{proposal.state !== "WITHDRAWN" && <button className="secondary" disabled={busy} onClick={() => setConfirmation("withdraw")}>Withdraw release and dependent evidence</button>}{confirmation && <div className="notice"><p>{confirmation === "retire" ? "Retire this version from new assignments and publications? Frozen historical evidence stays valid while its sources and approvals remain available." : "Withdraw this proposal and dependent releases? Existing conclusions will be invalidated and pending reanalysis cancelled."}</p><button disabled={busy} onClick={() => void release(confirmation)}>Confirm {confirmation}</button><button className="secondary" onClick={() => setConfirmation(null)}>Keep current state</button></div>}</>}
      </>}
      </section>
      <section><details><summary>Register an unverified build</summary><p>Registration records an exact version and platform for review. It does not verify the patch or its overlays.</p><form onSubmit={e => { e.preventDefault(); const f = new FormData(e.currentTarget); void action(async () => { const r = await post("/builds", { version: f.get("version"), platform: f.get("platform") }); await refresh(); setStatus(`Build registered: ${r.key}. In-game evidence and two independent reviewers are still required.`); }); }}><label htmlFor="new-build-version">Exact version label</label><input id="new-build-version" name="version" pattern="[A-Za-z0-9_.-]+" maxLength={30} required /><label htmlFor="new-build-platform">Build platform</label><select id="new-build-platform" name="platform"><option value="steam">Steam PC</option><option value="ps5">PS5 (capture profile not released)</option><option value="xbox_series">Xbox Series (capture profile not released)</option><option value="synthetic">Synthetic rehearsal</option></select><button disabled={busy}>Register unverified build</button></form></details></section>
      <section><details><summary>Prepare a new evidence-pinned version</summary><p>Publish build evidence first, then moves, situation, metric, knowledge and drill. Each version needs two assigned independent operator accounts. New versions never change a draft&apos;s approval flags. Do not enter private names, source tokens or imported proprietary tables in public game facts.</p><form onSubmit={e => void propose(e)}>
        <label htmlFor="knowledge-key">New version key</label><input id="knowledge-key" name="key" maxLength={160} pattern="[A-Za-z0-9_.:/-]+" required />
        <label htmlFor="knowledge-kind">Artifact type</label><select id="knowledge-kind" value={kind} onChange={e => { setKind(e.target.value); setPayload(JSON.stringify(templates[e.target.value], null, 2)); }}>{Object.keys(templates).map(k => <option key={k}>{k}</option>)}</select>
        <label htmlFor="knowledge-build">Canonical game build</label><select id="knowledge-build" name="build" required><option value="">Choose exact build and platform</option>{data.builds.map(b => <option key={b.key} value={b.key}>{b.key} / {b.platform} / {b.verified ? "verified" : "unverified"}</option>)}</select>
        <label htmlFor="knowledge-scope">Evidence scope</label><select id="knowledge-scope" name="scope"><option value="synthetic">Synthetic rehearsal</option><option value="real">Real evidence preparation (publication gated)</option></select>
        <label htmlFor="knowledge-payload">Candidate facts (JSON)</label><textarea id="knowledge-payload" rows={16} maxLength={32768} value={payload} onChange={e => setPayload(e.target.value)} required /><p className="muted">Templates contain no verified Tekken frame facts. Unknown move facts must be reviewed before a candidate can be sealed.</p>
        <label htmlFor="knowledge-source">Owned validated sources (select one or more)</label><select id="knowledge-source" name="sources" multiple required>{data.sources.map(s => <option key={s.id} value={s.id}>{s.id.slice(0, 8)} / {String(s.metadata.game_build || "unknown build")} / {String(s.metadata.platform || "unknown platform")}</option>)}</select>
        <label htmlFor="knowledge-reviewer-one">First independent operator account ID</label><input id="knowledge-reviewer-one" name="reviewer-one" type="number" min={1} required /><label htmlFor="knowledge-reviewer-two">Second independent operator account ID</label><input id="knowledge-reviewer-two" name="reviewer-two" type="number" min={1} required />
        <label htmlFor="knowledge-reference">Offline source / permission reference code</label><input id="knowledge-reference" name="reference" maxLength={160} pattern="[A-Za-z0-9_.:/-]+" required /><label htmlFor="knowledge-rights">Source rights</label><select id="knowledge-rights" name="rights"><option value="OWNED_RECORDING">My permitted recording</option><option value="PERMITTED_FACTS">Separately permitted factual evidence</option></select>
        <label className="check"><input name="sharing" type="checkbox" required />I permit these two assigned reviewers to view the whole selected recordings.</label><label className="check"><input name="publishing" type="checkbox" required />I have permission to publish these game facts, free of personal details.</label><button disabled={busy}>Seal proposal</button>
      </form></details></section>
      <section><h2>Patch compatibility and reanalysis</h2><p>A reviewed mapping records same measurement, reanalysis required, or incompatible. Cross-build recordings cannot be relabeled as a new patch. Frozen comparison windows keep their original versions.</p><label htmlFor="knowledge-mapping">Published compatibility mapping</label><select id="knowledge-mapping" value={mapping} onChange={e => { setMapping(e.target.value); setImpact(null); }}><option value="">Choose reviewed mapping</option>{data.definitions.filter(d => d.kind === "compatibility").map(d => <option key={d.key}>{d.key}</option>)}</select><button disabled={busy || !mapping} onClick={() => void action(async () => { const r = await fetch(`/api/knowledge/reanalysis?mapping_key=${encodeURIComponent(mapping)}`, { cache: "no-store" }); const j = await r.json(); if (!r.ok) throw new Error(j.error || j.detail || "Impact unavailable"); setImpact(j); })}>Preview affected matches</button>
        {impact && <><p>{impact.note}</p>{impact.matches.length === 0 && <p>No affected recordings in this workspace.</p>}{impact.matches.map(m => <div className="result" key={m.id}><p>Match {m.id.slice(0, 8)} / captured build {m.game_build} / {m.dataset_kind}</p><p>{m.state.replaceAll("_", " ")}</p>{m.state === "READY" && <button disabled={busy} onClick={() => void action(async () => { const r = await post("/reanalysis", { match_id: m.id, mapping_key: mapping, request_id: requestId(`reanalysis:${m.id}:${mapping}`) }); delete requests.current[`reanalysis:${m.id}:${mapping}`]; await refresh(); setImpact(null); setStatus(`Reanalysis queued (${r.status}). Independent gameplay review is required before replacement.`); })}>Queue reviewed reanalysis</button>}</div>)}</>}
        {data.reanalyses.map(r => <p key={r.id}>Match {r.match_id.slice(0, 8)} / {r.target_id} / {r.run__status}. Gameplay publication still requires reviewed annotations.</p>)}
      </section>
    </>)}
  </main>;
}
