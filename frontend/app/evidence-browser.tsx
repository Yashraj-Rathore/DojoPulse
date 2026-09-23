"use client";
import { useEffect, useRef, useState } from "react";
import { displayTime, workspaceRequest as request } from "./workspace-api";

type Evidence = { id: string; match_id: string; played_at: string; mode: string; start_us: number; end_us: number; outcome: string; eligibility: string; situation: string; source_asset_id: string; source_hash: string; game_build: string | null; knowledge_revision: string | null; detector_version: string; dataset_kind: string; metadata_state: string; reviewed: boolean; review_count: number; selectable: boolean };
type Page = { events: Evidence[]; total: number; next_offset: number | null };
const blank: Page = { events: [], total: 0, next_offset: null };

export default function EvidenceBrowser({ csrf, selected, onSelect, zone, onReport, matchId, onClearMatch }: { csrf: string; selected: string[]; onSelect: (ids: string[]) => void; zone: string; onReport: (id: string) => void; matchId: string; onClearMatch: () => void }) {
  const [page, setPage] = useState<Page>(blank), [filters, setFilters] = useState(""), [offset, setOffset] = useState(0), [reload, setReload] = useState(0);
  const [active, setActive] = useState<Evidence | null>(null), [error, setError] = useState(""), [loading, setLoading] = useState(true), [unavailable, setUnavailable] = useState(false);
  const video = useRef<HTMLVideoElement>(null);
  useEffect(() => {
    const controller = new AbortController();
    async function load() { try { const data = await request<Page>(csrf, `evidence?offset=${offset}&limit=20&${filters}${matchId ? `&match=${matchId}` : ""}`, "GET", undefined, controller.signal); if (!controller.signal.aborted) { setPage(data.events ? data : blank); setError(""); setLoading(false); } } catch (e) { if (!controller.signal.aborted) { setError(e instanceof Error ? e.message : "Evidence unavailable"); setLoading(false); } } }
    void load(); const timer = setInterval(() => { if (document.visibilityState === "visible") void load(); }, 10000);
    return () => { controller.abort(); clearInterval(timer); };
  }, [csrf, filters, offset, reload, matchId]);
  // A selected record disappearing after deletion/correction closes its player on refresh.
  const inspected = active && page.events.find(e => e.id === active.id);
  async function selectMatch(item: Evidence) {
    setError(""); const ids: string[] = []; let cursor: number | null = 0;
    try { while (cursor !== null) { const result: Page = await request<Page>(csrf, `evidence?match=${item.match_id}&offset=${cursor}&limit=100`); if (result.total > 2000) throw new Error("This match exceeds the local selection limit. Ask the operator to review segmentation."); ids.push(...result.events.filter(e => e.selectable).map(e => e.id)); cursor = result.next_offset; } onSelect([...new Set([...selected, ...ids])]); }
    catch (e) { setError(e instanceof Error ? e.message : "Selection failed"); }
  }
  return <section id="evidence" className="wide" aria-labelledby="evidence-heading">
    <h2 id="evidence-heading">02 / Inspect the evidence</h2>
    {matchId && <p>Showing match {matchId.slice(0, 8)}. <button className="secondary" onClick={onClearMatch}>Show evidence from all matches</button></p>}
    <p>Review source windows, eligibility and outcomes together. Unknown is not failure. Only the current reviewed publication is selectable; disputed source metadata is shown for review.</p>
    <form className="filter-form" onSubmit={e => { e.preventDefault(); const form = new FormData(e.currentTarget); const query = new URLSearchParams(); for (const [key, value] of form) if (value) query.set(key, String(value)); setFilters(query.toString()); setOffset(0); setLoading(true); setActive(null); }}>
      <div className="rows"><div><label htmlFor="event-from">Evidence from (UTC date)</label><input id="event-from" name="date_from" type="date" /></div><div><label htmlFor="event-to">Evidence through (UTC date)</label><input id="event-to" name="date_to" type="date" /></div>
        <div><label htmlFor="event-situation">Situation key</label><input id="event-situation" name="situation" maxLength={160} placeholder="Exact situation identifier" /></div>
        <div><label htmlFor="event-character">Evidence character key</label><input id="event-character" name="character" maxLength={50} placeholder="For example: jin" /></div>
        <div><label htmlFor="event-outcome">Evidence outcome</label><select id="event-outcome" name="outcome"><option value="">All outcomes</option><option>SUCCESS</option><option>FAILURE</option><option>UNKNOWN</option></select></div>
        <div><label htmlFor="event-mode">Evidence purpose</label><select id="event-mode" name="mode"><option value="">All purposes</option><option value="ranked">Ranked</option><option value="practice">Practice</option><option value="takeover">Takeover</option></select></div>
        <div><label htmlFor="event-eligibility">Eligibility</label><select id="event-eligibility" name="eligibility"><option value="">All eligibility</option><option>ELIGIBLE</option><option>INELIGIBLE</option><option>UNKNOWN</option></select></div>
      </div><button>Search evidence</button><button type="reset" className="secondary" onClick={() => { setFilters(""); setOffset(0); setActive(null); }}>Clear evidence filters</button>
    </form>
    <p role="status">{loading ? "Loading evidence…" : `${page.total} reviewed events found.`} {selected.length} selected across pages and filters.</p>
    <p className="muted">Select every reviewed opportunity in the relevant captures before freezing or comparing. Filtering does not clear selections; the server rejects incomplete capture selections.</p>
    <button className="secondary" onClick={() => onSelect([])} disabled={!selected.length}>Clear evidence selection</button><button className="secondary" onClick={() => setReload(n => n + 1)}>Refresh evidence</button>
    {error && <p role="alert" className="notice error">{error}</p>}
    {!page.events.length && !loading && <p className="empty">No adjudicated opportunities. The absence of a detected attack does not establish a missed punish. Clear filters or wait for independent review.</p>}
    <ul className="evidence-list">{page.events.map(item => <li key={item.id}>
      <div><strong>{displayTime(item.played_at, zone)}</strong> · {item.mode} · {(item.start_us / 1e6).toFixed(2)}–{(item.end_us / 1e6).toFixed(2)} s</div>
      <p>{item.eligibility} · {item.outcome} {item.dataset_kind === "synthetic" && <span className="tag">Synthetic evidence</span>}</p>
      {!item.selectable && <p className="notice">Source correction or review is pending. This event cannot support a new conclusion.</p>}
      <label><input type="checkbox" aria-label={`Select event ${item.id}`} disabled={!item.selectable} checked={selected.includes(item.id)} onChange={e => onSelect(e.target.checked ? [...new Set([...selected, item.id])] : selected.filter(id => id !== item.id))} />Include in evidence selection</label>
      <button className="secondary" onClick={() => { setActive(item); setUnavailable(false); }}>Inspect event {item.id.slice(0, 8)}</button>
      <button className="secondary" disabled={!item.selectable} onClick={() => void selectMatch(item)}>Select complete match {item.match_id.slice(0, 8)}</button>
    </li>)}</ul>
    {inspected && <div className="evidence-detail" role="region" aria-label="Evidence player">
      <h3>Source window: {(inspected.start_us / 1e6).toFixed(2)}–{(inspected.end_us / 1e6).toFixed(2)} seconds</h3>
      <video key={inspected.id} ref={video} controls preload="metadata" aria-label="Recorded gameplay evidence" src={`/api/assets/${inspected.source_asset_id}/media#t=${inspected.start_us / 1e6},${inspected.end_us / 1e6}`} onLoadedMetadata={e => { e.currentTarget.currentTime = inspected.start_us / 1e6; }} onError={() => setUnavailable(true)} />
      {unavailable && <p role="alert">The recording is unavailable or unsupported by this browser. Refresh evidence or report the problem.</p>}
      <button className="secondary" onClick={() => { if (video.current) video.current.currentTime = inspected.start_us / 1e6; }}>Jump to event start</button>
      <a href={`/api/assets/${inspected.source_asset_id}/media`} target="_blank" rel="noreferrer">Open original recording</a>
      <p>{inspected.situation} · {inspected.eligibility} / {inspected.outcome}. {inspected.reviewed ? `Reviewed; ${inspected.review_count} review records.` : "Review incomplete."} Review the frames and context; these labels are not an automatic accuracy guarantee.</p>
      <details><summary>Evidence provenance</summary><p>Build: {inspected.game_build || "Unknown"}<br />Knowledge: {inspected.knowledge_revision || "Unknown"}<br />Detector: {inspected.detector_version}<br />SHA-256: {inspected.source_hash}<br />Match: {inspected.match_id}</p></details>
      <button onClick={() => { onReport(inspected.id); document.getElementById("support")?.scrollIntoView(); }}>Request evidence correction</button>
    </div>}
    <div className="history-pagination"><button disabled={offset === 0} onClick={() => { setOffset(Math.max(0, offset - 20)); setActive(null); }}>Previous evidence</button><button disabled={page.next_offset == null} onClick={() => { setOffset(page.next_offset!); setActive(null); }}>Next evidence</button></div>
  </section>;
}
