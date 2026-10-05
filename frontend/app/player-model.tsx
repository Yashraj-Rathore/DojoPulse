"use client";
import { useEffect, useRef, useState } from "react";
import { displayTime, workspaceRequest as request } from "./workspace-api";

type Counts = { numerator: number; denominator: number; failures: number; eligible_unknown: number; unknown_eligibility: number; excluded: number; coverage: number | null; eligibility_coverage: number | null; sessions: number };
type History = { wins: number; losses: number; unknown: number; known_results: number; win_rate: number | null };
type Drill = { key: string; title: string };
type Card = {
  id: string; state: string; reasons: string[]; summary: Counts; failure_interval: number[] | null;
  priority_rank: number | null; score: number | null; policy_version: string; policy_hash: string;
  scope: { situation: string; metric: string; context: string; game_build: string; knowledge_revision: string; knowledge_hash: string | null; detector_version: string; platform: string; dataset_kind: string };
  review: { independently_reviewed: number; agreement: number | null };
  factors: { frequency: number | null; value: number | null; certainty: number | null; trainability: number | null };
  assessment: { rationale: string } | null; assessment_drill: { key: string; content_hash: string } | null; drills: Drill[];
  evidence_hash: string; evidence_total: number;
  evidence: { id: string; match_id: string; asset_id: string; start_us: number; end_us: number; outcome: string; played_at: string }[];
  trends: { period: string; summary: Counts }[];
};
type Model = { cards: Card[]; card_total: number; next_offset: number | null; filters: Record<string, string>; unavailable_events: Record<string, number>; capture_inventory: { ranked_matches: number; with_publication: number; without_publication: number }; history: { summary: History; trends: (History & { period: string })[] }; history_note: string; frequency_note: string };
const percent = (value: number | null) => value == null ? "Unknown" : `${(value * 100).toFixed(1)}%`;
const states: Record<string, string> = { INSUFFICIENT_EVIDENCE: "More evidence needed", REVIEW_REQUIRED: "Independent review needed", UNSUPPORTED_SCOPE: "Unsupported situation or context", REAL_VALIDATION_PENDING: "Real-game diagnosis validation pending", OBSERVED_FAILURE_PATTERN: "Observed failure pattern", NO_CLEAR_FAILURE_PATTERN: "No clear failure pattern" };

export default function PlayerModel({ csrf, zone, onEvidence, onAssigned }: { csrf: string; zone: string; onEvidence: (match: string) => void; onAssigned: (assignment: string) => void }) {
  const [model, setModel] = useState<Model | null>(null), [filters, setFilters] = useState(""), [offset, setOffset] = useState(0), [reload, setReload] = useState(0);
  const [error, setError] = useState(""), [busy, setBusy] = useState(false);
  useEffect(() => {
    const controller = new AbortController();
    async function load() {
      try {
        const next = await request<Model>(csrf, `player-model?offset=${offset}&limit=20&${filters}`, "GET", undefined, controller.signal);
        if (!controller.signal.aborted) { setModel(next); setError(""); }
      } catch (e) { if (!controller.signal.aborted) { setModel(null); setError(e instanceof Error ? e.message : "Diagnosis unavailable"); } }
    }
    void load(); const timer = setInterval(() => { if (document.visibilityState === "visible") void load(); }, 10000);
    return () => { controller.abort(); clearInterval(timer); };
  }, [csrf, filters, offset, reload]);
  function changeScope(query: string) { setModel(null); setError(""); setFilters(query); setOffset(0); }
  const assignmentRequests = useRef(new Map<string, string>());
  async function assign(drill: Drill, card: Card) {
    setBusy(true); setError("");
    try {
      const key = `${drill.key}:${card.id}:${card.evidence_hash}:${card.policy_hash}`;
      if (!assignmentRequests.current.has(key)) assignmentRequests.current.set(key, crypto.randomUUID());
      const result = await request<{ id: string }>(csrf, "assignments", "POST", { drill_key: drill.key, request_id: assignmentRequests.current.get(key), diagnosis: { card_id: card.id, evidence_hash: card.evidence_hash, policy_hash: card.policy_hash, filters: model!.filters } });
      onAssigned(result.id);
    }
    catch (e) { setError(e instanceof Error ? e.message : "Assignment unavailable"); setReload(n => n + 1); }
    finally { setBusy(false); }
  }
  return <section id="diagnosis" className="wide player-model" aria-labelledby="diagnosis-heading">
    <h2 id="diagnosis-heading">Your measured priorities</h2>
    <p>Diagnosis uses complete current ranked-event publications in the selected scope. Unknown outcomes remain unknown. Proposed thresholds and research scores still need expert and player validation.</p>
    <form className="filter-form" onSubmit={e => { e.preventDefault(); const query = new URLSearchParams(); for (const [key, value] of new FormData(e.currentTarget)) if (value) query.set(key, String(value)); changeScope(query.toString()); }}>
      <div className="rows">
        <div><label htmlFor="model-from">Diagnosis from (UTC date)</label><input id="model-from" name="date_from" type="date" /></div>
        <div><label htmlFor="model-to">Diagnosis through (UTC date)</label><input id="model-to" name="date_to" type="date" /></div>
        <div><label htmlFor="model-context">Diagnosis context</label><input id="model-context" name="context" maxLength={100} placeholder="For example: jin/jin" /></div>
        <div><label htmlFor="model-scope">Evidence scope</label><select id="model-scope" name="dataset_kind"><option value="real">Real gameplay</option><option value="synthetic">Synthetic software fixtures</option></select></div>
      </div>
      <details><summary>Measurement version filters</summary><div className="rows">{([ ["game_build", "Game build", 80], ["knowledge_revision", "Knowledge revision", 160], ["detector_version", "Detector version", 100], ["platform", "Capture platform", 50], ["situation", "Situation definition", 160] ] as const).map(([name, label, max]) => <div key={name}><label htmlFor={`model-${name}`}>{label}</label><input id={`model-${name}`} name={name} maxLength={max} /></div>)}</div></details>
      <button>Apply diagnosis filters</button><button type="reset" className="secondary" onClick={() => changeScope("")}>Clear diagnosis filters</button>
    </form>
    <button className="secondary" onClick={() => { setModel(null); setReload(n => n + 1); }}>Refresh diagnosis</button>
    {error && <p role="alert" className="notice error">{error}</p>}
    {!model && !error && <p role="status">Loading diagnosis…</p>}
    {model && <>
      <p role="status">{model.card_total} measurement groups · {model.filters.date_from} through {model.filters.date_to} (UTC).</p>
      {model.filters.dataset_kind === "synthetic" && <p className="notice">Synthetic software test — these priorities do not describe real gameplay.</p>}
      <p className="muted">{model.capture_inventory.with_publication} / {model.capture_inventory.ranked_matches} recorded ranked captures have a publication; {model.capture_inventory.without_publication} have none. A missing publication does not establish an absent opportunity.</p>
      {Object.entries(model.unavailable_events).map(([reason, count]) => <p className="notice" key={reason}>{count} events excluded: {reason.replaceAll("_", " ").toLowerCase()}.</p>)}
      {!model.cards.length && <p className="empty">No available reviewed gameplay in this scope. Import reviewed evidence or adjust the dates and versions.</p>}
      {model.cards.map(card => <article className="result" key={card.id} aria-label={`Diagnosis ${card.scope.context} ${card.scope.game_build}`}>
        <span className="tag">{card.priority_rank == null ? "Unranked" : `Research priority ${card.priority_rank}`}</span><h3>{states[card.state] || card.state.replaceAll("_", " ")}</h3>
        <p>{card.scope.context} · build {card.scope.game_build} · {card.scope.platform} · {card.scope.dataset_kind}</p>
        <p><strong>{card.summary.numerator} / {card.summary.denominator} successful responses</strong>; {card.summary.failures} failures across {card.summary.sessions} distinct reviewed sessions.</p>
        <p>{card.summary.eligible_unknown} unknown outcomes; {card.summary.unknown_eligibility} unknown eligibility; {card.summary.excluded} excluded windows. Known outcome coverage: {percent(card.summary.coverage)}; eligibility coverage: {percent(card.summary.eligibility_coverage)}.</p>
        <p className="muted">{card.failure_interval ? `Descriptive 95% failure interval: ${percent(card.failure_interval[0])} to ${percent(card.failure_interval[1])}.` : "Uncertainty unavailable until known outcomes exist."} This event-based interval does not establish improvement or causation.</p>
        <p className="muted">Independent review: {card.review.independently_reviewed} / {card.evidence_total} windows; raw label agreement {percent(card.review.agreement)}.</p>
        {card.reasons.length > 0 && <ul aria-label="Diagnosis requirements">{card.reasons.map(reason => <li key={reason}>{reason.replaceAll("_", " ").toLowerCase()}</li>)}</ul>}
        <details><summary>Priority calculation and provenance</summary><p>Score: {card.score == null ? "Unavailable" : card.score.toFixed(4)}. Eligible-window frequency {percent(card.factors.frequency)} × reviewed relative value {percent(card.factors.value)} × certainty {percent(card.factors.certainty)} × reviewed trainability {percent(card.factors.trainability)}.</p><p>{model.frequency_note} Certainty combines the lower failure interval with review agreement. Value and trainability are reviewed relative assessments, not expected damage or promised gains.</p>{card.assessment && <p>Assessment: {card.assessment.rationale}</p>}<dl><dt>Measurement</dt><dd>{card.scope.situation}<br />{card.scope.metric}<br />{card.scope.knowledge_revision}<br />{card.scope.detector_version}</dd><dt>Knowledge hash</dt><dd>{card.scope.knowledge_hash || "Legacy synthetic fixture"}</dd><dt>Policy</dt><dd>{card.policy_version}<br />{card.policy_hash}</dd><dt>Selected evidence hash</dt><dd>{card.evidence_hash}</dd>{card.assessment_drill && <><dt>Reviewed assessment version</dt><dd>{card.assessment_drill.key}<br />{card.assessment_drill.content_hash}</dd></>}</dl></details>
        <details><summary>Supporting timestamp evidence ({card.evidence.length} of {card.evidence_total})</summary><p>Sampled failure windows appear first. Counts and thresholds use every available window in this group.</p><ul>{card.evidence.map(event => <li key={event.id}>{displayTime(event.played_at, zone)} · {event.outcome} · {(event.start_us / 1e6).toFixed(2)}–{(event.end_us / 1e6).toFixed(2)} s<br /><a href={`/api/assets/${event.asset_id}/media#t=${event.start_us / 1e6},${event.end_us / 1e6}`} target="_blank" rel="noreferrer">Play supporting window</a> <button className="secondary" onClick={() => onEvidence(event.match_id)}>Inspect supporting match</button></li>)}</ul></details>
        <details><summary>Gameplay history for this measurement</summary><p>Monthly counts are descriptive. Versions remain separate; these trends do not replace a frozen baseline/follow-up evaluation.</p><ul>{card.trends.map(period => <li key={period.period}>{period.period}: {period.summary.numerator}/{period.summary.denominator} successes · {period.summary.eligible_unknown} unknown outcomes · {period.summary.unknown_eligibility} unknown eligibility · {period.summary.sessions} sessions.</li>)}</ul></details>
        {card.drills.map(drill => <button key={drill.key} disabled={busy || card.state !== "OBSERVED_FAILURE_PATTERN"} onClick={() => void assign(drill, card)}>Assign {drill.title}</button>)}
      </article>)}
      <div className="history-pagination"><button disabled={offset === 0} onClick={() => { setModel(null); setOffset(Math.max(0, offset - 20)); }}>Previous diagnoses</button><button disabled={model.next_offset == null} onClick={() => { setModel(null); setOffset(model.next_offset!); }}>Next diagnoses</button></div>
      <div className="result"><h3>Recorded match results</h3><p>{model.history.summary.wins} wins / {model.history.summary.known_results} known results; {model.history.summary.losses} losses and {model.history.summary.unknown} unknown results. Recorded win rate: {percent(model.history.summary.win_rate)}.</p><p className="muted">{model.history_note} Match results do not establish performance in a particular gameplay situation, or a rank-based skill score.</p><ul>{model.history.trends.map(period => <li key={period.period}>{period.period}: {period.wins} wins, {period.losses} losses, {period.unknown} unknown results.</li>)}</ul></div>
    </>}
  </section>;
}
