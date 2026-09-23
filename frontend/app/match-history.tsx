"use client";

import { useEffect, useState } from "react";
import AttachRecording, { type RecordingTarget } from "./attach-recording";
import { displayTime } from "./workspace-api";

type Provider = { key: string; label: string; enabled: boolean; reason: string; example_id?: string };
type Candidate = { display_name: string; value: string; provider: string; selection_token: string; ownership_verified: boolean };
type Identity = { id: string; value: string; display_label: string | null; state: string; can_sync: boolean; provider: string | null };
type Sync = { id: string; provider: string; status: string; last_succeeded_at: string | null; next_attempt_at: string | null; coverage: { coverage: string; gaps: string[]; truncated: boolean } | null };
type Match = {
  id: string; played_at: string; mode: string; game_build: string | null; dataset_kind: string;
  opponent: string | null; character: string | null; opponent_character: string | null;
  result: string; metadata_state: string; evidence_status: string; can_delete_metadata: boolean;
  source: { provider: string; revision: number; retrieved_at: string; raw_game_version: string | null } | null;
  replays: { representation: string; availability: string }[];
  can_attach_recording?: boolean; recording_target?: RecordingTarget | null;
  recordings?: {source_id: string; asset_id: string; attribution_state: string; source_hash: string; run_id: string; status: string; can_manage: boolean}[];
};
type History = { matches: Match[]; total: number; next_offset: number | null; syncs: Sync[] };
const blank: History = { matches: [], total: 0, next_offset: null, syncs: [] };

async function request<T>(csrf: string, path: string, method = "GET", body?: object, signal?: AbortSignal): Promise<T> {
  const response = await fetch(`/api/${path}`, {
    method, credentials: "same-origin", cache: "no-store", signal,
    headers: { "Content-Type": "application/json", "X-CSRFToken": csrf },
    body: body ? JSON.stringify(body) : undefined,
  });
  const data = await response.json();
  if (!response.ok) throw new Error(typeof data.error === "string" ? data.error : "Could not complete this request. Check your selection and try again.");
  return data;
}

const words = (value: string) => value.toLowerCase().replaceAll("_", " ");

export default function MatchHistory({ csrf, zone = "UTC", onEvidence }: { csrf: string; zone?: string; onEvidence?: (id: string) => void }) {
  const date = (value: string) => displayTime(value, zone);
  const [filters, setFilters] = useState("");
  const [providers, setProviders] = useState<Provider[]>([]);
  const [identities, setIdentities] = useState<Identity[]>([]);
  const [history, setHistory] = useState<History>(blank);
  const [provider, setProvider] = useState("");
  const [query, setQuery] = useState("");
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [selection, setSelection] = useState("");
  const [searched, setSearched] = useState(false);
  const [consent, setConsent] = useState(false);
  const [identityFilter, setIdentityFilter] = useState("");
  const [offset, setOffset] = useState(0);
  const [reload, setReload] = useState(0);
  const [busy, setBusy] = useState(false);
  const [ready, setReady] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [removing, setRemoving] = useState<string | null>(null);
  const [attaching, setAttaching] = useState<string | null>(null);
  const [removingRecording, setRemovingRecording] = useState<string | null>(null);
  const activeProvider = providers.find(item => item.key === provider && item.enabled);

  useEffect(() => {
    const controller = new AbortController();
    let loading = false;
    const load = async () => {
      if (loading) return;
      loading = true;
      try {
        const suffix = `?offset=${offset}&limit=20&${filters}${identityFilter ? `&identity=${encodeURIComponent(identityFilter)}` : ""}`;
        const [sources, links, matches] = await Promise.all([
          request<{ providers: Provider[] }>(csrf, "match-providers", "GET", undefined, controller.signal),
          request<{ identities: Identity[] }>(csrf, "player-identities", "GET", undefined, controller.signal),
          request<History>(csrf, `matches${suffix}`, "GET", undefined, controller.signal),
        ]);
        if (!controller.signal.aborted) {
          setProviders(sources.providers); setIdentities(links.identities); setHistory(matches); setReady(true);
        }
      } catch (problem) {
        if (!controller.signal.aborted) {
          setError(problem instanceof Error ? problem.message : "History is unavailable."); setReady(true);
        }
      } finally { loading = false; }
    };
    void load();
    const timer = setInterval(() => { if (document.visibilityState === "visible") void load(); }, 5000);
    return () => { controller.abort(); clearInterval(timer); };
  }, [csrf, identityFilter, offset, reload, filters]);

  function resetSelection() { setCandidates([]); setSelection(""); setConsent(false); setSearched(false); }
  async function act(work: () => Promise<void>) {
    setBusy(true); setError(""); setMessage("");
    try { await work(); setReload(value => value + 1); }
    catch (problem) { setError(problem instanceof Error ? problem.message : "Request failed."); }
    finally { setBusy(false); }
  }

  return <section id="matches" className="wide match-history" aria-labelledby="match-heading">
    <div className="history-heading"><div><div className="eyebrow">Your player & matches</div><h2 id="match-heading">Bring your match history</h2></div><span className="tag">Preview</span></div>
    <p>Link a player profile, import available results, then add gameplay evidence when you want to investigate a specific situation.</p>
    <p className="muted">Live Tekken services are not connected yet. The local demo uses fictional players and matches. Player-name search is not available.</p>
    {error && <div className="notice error" role="alert">{error}</div>}
    {message && <p className="notice" role="status">{message}</p>}
    {!ready ? <p role="status">Loading match history…</p> : <>
      <div className="history-columns">
        <div>
          <h3>1. Find and confirm a player</h3>
          <form onSubmit={event => {
            event.preventDefault(); resetSelection();
            void act(async () => {
              const result = await request<{ candidates: Candidate[] }>(csrf, "player-candidates", "POST", { provider, query, kind: "RESOLVE_ID" });
              setCandidates(result.candidates); setSearched(true);
            });
          }}>
            <label htmlFor="match-provider">Match source</label>
            <select id="match-provider" value={provider} disabled={busy} onChange={event => { setProvider(event.target.value); setQuery(""); resetSelection(); }}>
              <option value="">Choose an available source</option>
              {providers.map(item => <option key={item.key} value={item.key} disabled={!item.enabled}>{item.label}{item.enabled ? "" : " — unavailable"}</option>)}
            </select>
            <label htmlFor="player-id">Player ID</label>
            <input id="player-id" value={query} maxLength={200} autoComplete="off" required disabled={busy || !activeProvider}
              placeholder={activeProvider?.example_id || "Choose a source first"} onChange={event => { setQuery(event.target.value); resetSelection(); }} />
            {activeProvider?.example_id && <p className="muted">Demo ID: <code>{activeProvider.example_id}</code></p>}
            <button disabled={busy || !activeProvider || !query}>Find player</button>
          </form>
          <details><summary>Source availability</summary>{providers.map(item => <p className="muted" key={item.key}><strong>{item.label}:</strong> {item.reason}</p>)}</details>
          {searched && !candidates.length && <p role="status">No player found for that exact ID. Check the ID and selected source.</p>}
          {!!candidates.length && <fieldset className="candidate-list"><legend>Confirm the correct profile</legend>
            {candidates.map(candidate => <label key={candidate.selection_token}>
              <input type="radio" name="player-candidate" checked={selection === candidate.selection_token} onChange={() => setSelection(candidate.selection_token)} disabled={busy} />
              <strong>{candidate.display_name}</strong> · {candidate.value}<span className="muted"> · fictional profile</span>
            </label>)}
            <p className="muted">Linking a public profile does not verify that you control it.</p>
            <label><input type="checkbox" checked={consent} disabled={busy} onChange={event => setConsent(event.target.checked)} />I consent to storing this player link and importing its match metadata into my workspace.</label>
            <button disabled={busy || !selection || !consent} onClick={() => void act(async () => {
              await request(csrf, "player-identities", "POST", { selection_token: selection, processing_consent: consent });
              resetSelection(); setMessage("Player linked. You can now import matches.");
            })}>Link selected player</button>
          </fieldset>}
        </div>
        <div><h3>2. Import matches</h3>
          {identities.length ? identities.map(identity => <div className="result" key={identity.id}>
            <strong>{identity.display_label || "Player profile"}</strong><p className="muted">{identity.value} · {identity.state === "CLAIMED" ? "Ownership unverified" : "Sync consent revoked"}</p>
            {identity.can_sync ? <>
              <button disabled={busy || !providers.some(item => item.enabled && item.key === (activeProvider?.key || identity.provider))} onClick={() => void act(async () => {
                await request(csrf, `player-identities/${identity.id}/sync`, "POST", { provider: activeProvider?.key || identity.provider });
                setOffset(0); setMessage("Import queued. Matches will appear when processing finishes.");
              })}>Import matches</button>
              <button className="secondary" disabled={busy} onClick={() => void act(async () => {
                await request(csrf, `player-identities/${identity.id}`, "DELETE");
                setMessage("Sync consent revoked. Previously imported matches remain in your history.");
              })}>Stop syncing</button>
            </> : <p className="muted">Automatic imports are stopped for this player.</p>}
          </div>) : <p className="empty">No player linked yet. Find a profile and confirm your selection to begin.</p>}
          {history.syncs.map(sync => <div key={sync.id} className="sync-status"><span className="tag">{words(sync.status)}</span><span> {providers.find(item => item.key === sync.provider)?.label || sync.provider}</span>
            {sync.status === "PENDING" || sync.status === "PROCESSING" ? <p className="muted">Import queued or in progress. This page refreshes automatically.</p> : null}
            {sync.status === "ATTENTION_REQUIRED" && <p className="muted">Import needs review. Previously imported matches are still available.</p>}
            {sync.last_succeeded_at && <p className="muted">Last imported {date(sync.last_succeeded_at)}. Source coverage does not guarantee a complete play history.</p>}
            {sync.coverage && (sync.coverage.truncated || sync.coverage.coverage !== "COMPLETE_FOR_QUERY" || sync.coverage.gaps.length > 0) && <p className="notice">Partial history: some matches may be missing.</p>}
          </div>)}
        </div>
      </div>
      <div className="history-heading"><h3>3. Review your history</h3><button className="secondary" disabled={busy} onClick={() => { setError(""); setReload(value => value + 1); }}>Refresh history</button></div>
      <details><summary>Search and filter matches</summary><form onSubmit={event => { event.preventDefault(); const query = new URLSearchParams(); for (const [key, value] of new FormData(event.currentTarget)) if (value) query.set(key, String(value)); setFilters(query.toString()); setOffset(0); }}><div className="rows">
        <div><label htmlFor="match-from">Matches from (UTC date)</label><input id="match-from" name="date_from" type="date" /></div><div><label htmlFor="match-to">Matches through (UTC date)</label><input id="match-to" name="date_to" type="date" /></div>
        <div><label htmlFor="match-character">Character key</label><input id="match-character" name="character" maxLength={50} placeholder="For example: jin" /></div><div><label htmlFor="match-situation">Reviewed situation key</label><input id="match-situation" name="situation" maxLength={160} /></div>
        <div><label htmlFor="match-outcome">Reviewed event outcome</label><select id="match-outcome" name="outcome"><option value="">Any outcome</option><option>SUCCESS</option><option>FAILURE</option><option>UNKNOWN</option></select></div>
        <div><label htmlFor="match-evidence">Evidence availability</label><select id="match-evidence" name="evidence"><option value="">Any evidence state</option><option value="VIDEO">Attributed video</option><option value="PENDING">Attribution pending</option><option value="METADATA">Metadata only</option></select></div>
      </div><p className="muted">Dates use UTC calendar boundaries. Situation/outcome filters search current undisputed reviewed events; metadata-only results cannot supply gameplay outcomes.</p><button disabled={busy}>Search matches</button><button type="reset" className="secondary" onClick={() => { setFilters(""); setOffset(0); }}>Clear match filters</button></form></details>
      <label htmlFor="history-player">Show player</label><select id="history-player" value={identityFilter} onChange={event => { setIdentityFilter(event.target.value); setOffset(0); setHistory(blank); }}>
        <option value="">All players and recordings</option>{identities.map(identity => <option key={identity.id} value={identity.id}>{identity.display_label || identity.value}</option>)}
      </select>
      {history.matches.length ? <div className="scroll"><table><caption>{history.total} imported matches and recordings · results are separate from coaching evidence</caption><thead><tr><th>Played</th><th>Match</th><th>Result</th><th>Source & evidence</th><th>Actions</th></tr></thead><tbody>
        {history.matches.map(match => <tr key={match.id}>
          <td data-label="Played">{date(match.played_at)}{match.dataset_kind === "synthetic" && <p><span className="tag">Fictional demo</span></p>}</td>
          <td data-label="Match"><strong>vs {match.opponent || "Unknown opponent"}</strong><p className="muted">{match.character || "Unknown character"} / {match.opponent_character || "Unknown character"}<br />Mode: {words(match.mode)}<br />Build: {match.game_build || "Unknown"}</p>{onEvidence && <button className="secondary" onClick={() => onEvidence(match.id)}>Browse match evidence</button>}</td>
          <td data-label="Result">{words(match.result)}{match.metadata_state === "REVIEW_REQUIRED" && <p className="notice">Correction needs review</p>}</td>
          <td data-label="Source & evidence">{match.source ? <><strong>{providers.find(item => item.key === match.source?.provider)?.label || match.source.provider}</strong><p className="muted">Revision {match.source.revision} · imported {date(match.source.retrieved_at)}</p></> : <strong>User recording</strong>}
            <p>{match.evidence_status === "EVIDENCE_REQUIRED" ? "Gameplay evidence needed" : match.evidence_status === "ATTRIBUTION_PENDING" ? "Recording attribution needs review" : "Video attached — gameplay review required"}</p>
            {match.recordings?.map(recording => <div key={recording.source_id}>
              <p className="tag">{words(recording.status)}</p><p className="muted">Attribution: {words(recording.attribution_state)}</p>
              <a href={`/api/assets/${recording.asset_id}/media`} target="_blank" rel="noreferrer">Review recording</a>
              {recording.can_manage && <><details><summary>Operator review reference</summary><p className="muted">Source: {recording.source_id}<br />SHA-256: {recording.source_hash}</p></details>
                <button className="secondary" disabled={busy || ["QUEUED", "PROCESSING"].includes(recording.status)} onClick={() => void act(async () => { await request(csrf, `matches/${match.id}/recordings/${recording.source_id}/reprocess`, "POST", {request_id: crypto.randomUUID()}); setMessage("Recording queued for reprocessing."); })}>Reprocess recording</button></>}
              {removingRecording === recording.asset_id ? <div><p>Remove this recording and withdraw its evidence? Imported match history will remain.</p>
                <button disabled={busy} onClick={() => void act(async () => { await request(csrf, `assets/${recording.asset_id}`, "DELETE"); setRemovingRecording(null); setMessage("Recording removed. Imported match history retained."); })}>Confirm recording removal</button>
                <button className="secondary" disabled={busy} onClick={() => setRemovingRecording(null)}>Keep recording</button></div> : <button className="secondary" disabled={busy} onClick={() => setRemovingRecording(recording.asset_id)}>Remove recording</button>}
            </div>)}
            {match.replays.map((replay, index) => <p className="muted" key={index}>{words(replay.representation)}: {words(replay.availability)}</p>)}
          </td>
          <td data-label="Actions">{match.can_attach_recording && <button disabled={busy} onClick={() => setAttaching(match.id)}>Attach recording</button>}{match.can_delete_metadata && (removing === match.id ? <div className="remove-match"><p>Remove this match? Its metadata will be deleted and imports for this player will stop.</p>
            <button disabled={busy} onClick={() => void act(async () => { await request(csrf, `matches/${match.id}`, "DELETE"); setRemoving(null); setOffset(0); setMessage("Match removed and player sync consent revoked."); })}>Confirm removal</button>
            <button className="secondary" disabled={busy} onClick={() => setRemoving(null)}>Keep match</button></div> : <button className="secondary" disabled={busy} onClick={() => setRemoving(match.id)}>Remove match</button>)}</td>
        </tr>)}
      </tbody></table></div> : <p className="empty">No matches in this view yet. Link a player and import available matches, or use a recording below.</p>}
      {history.matches.filter(match => match.id === attaching && match.recording_target).map(match => <AttachRecording key={match.id} csrf={csrf} zone={zone} match={{...match, recording_target: match.recording_target!}}
        onCancel={() => setAttaching(null)} onComplete={() => {setAttaching(null); setMessage("Recording queued. Attribution and gameplay evidence require separate review."); setReload(value => value + 1);}} />)}
      <div className="history-pagination"><button className="secondary" disabled={offset === 0 || busy} onClick={() => { setOffset(Math.max(0, offset - 20)); setHistory(blank); }}>Previous matches</button><button className="secondary" disabled={history.next_offset === null || busy} onClick={() => { setOffset(history.next_offset!); setHistory(blank); }}>Next matches</button></div>
      <p className="muted">Match results alone cannot identify missed punishes or measure practice. <a href="#capture">Record a supported gameplay clip</a> to use the existing evidence-review flow.</p>
    </>}
  </section>;
}
