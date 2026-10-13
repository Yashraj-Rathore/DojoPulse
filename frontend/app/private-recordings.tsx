"use client";

import {useEffect, useRef, useState} from "react";
import {displayTime, workspaceRequest} from "./workspace-api";
import {useResumableUpload, UploadProgress} from "./resumable-upload";

type Quality = {frame_count: number; gaps_over_limit: number; irregular_intervals: number; max_frame_gap_us: number; timing_matches_declared_profile: boolean; precise_gameplay_analysis_approved: false};
type Preview = {state: string; phase?: string; progress?: number; media_url: string | null; quality?: Quality};
type Recording = {asset_id: string; bytes: number; uploaded_at: string; preview: Preview};
type Interval = {start_us: number; end_us: number; gap_us: number; reason: string};
type Windows = {intervals: Interval[]; next_offset: number | null; total: number};

export default function PrivateRecordings({csrf, zone = "UTC"}: {csrf: string; zone?: string}) {
  const [recordings, setRecordings] = useState<Recording[]>([]);
  const [error, setError] = useState(""), [message, setMessage] = useState("");
  const [revision, setRevision] = useState(0), [busy, setBusy] = useState<string | null>(null);
  const [windows, setWindows] = useState<Record<string, Windows>>({});
  const file = useRef<HTMLInputElement>(null);
  const requests = useRef<Record<string, string>>({});
  const hidden = useRef(new Set<string>());
  const upload = useResumableUpload(csrf);
  useEffect(() => {
    const controller = new AbortController(); let loading = false;
    async function load() {
      if (loading) return; loading = true;
      try {
        const data = await workspaceRequest<{recordings: Recording[]}>(csrf, "private-recordings", "GET", undefined, controller.signal);
        if (!controller.signal.aborted) {
          const current = (data.recordings ?? []).map(row => hidden.current.has(row.asset_id) ? {...row, preview: {...row.preview, media_url: null}} : row);
          setRecordings(current); setError(""); setWindows(previous => Object.fromEntries(Object.entries(previous).filter(([id]) => current.some(row => row.asset_id === id && row.preview?.media_url))));
        }
      } catch {
        if (!controller.signal.aborted) {setRecordings([]); setWindows({}); setError("Private recordings are unavailable. Playback has been cleared; retry when your session is available.");}
      } finally {loading = false;}
    }
    void load();
    const timer = setInterval(() => {if (document.visibilityState === "visible") void load();}, 5000);
    return () => {controller.abort(); clearInterval(timer);};
  }, [csrf, revision]);
  async function prepare(id: string) {
    setBusy(id); setError("");
    const requestId = requests.current[id] ??= crypto.randomUUID();
    try {await workspaceRequest(csrf, `assets/${id}/preview`, "POST", {request_id: requestId}); hidden.current.delete(id); setMessage("Playback preparation queued. Your original recording is retained."); setRevision(v => v + 1);}
    catch (problem) {setError(problem instanceof Error ? problem.message : "Playback preparation failed.");}
    finally {setBusy(null);}
  }
  async function remove(id: string) {
    hidden.current.add(id); setBusy(id); setError(""); setRecordings(rows => rows.map(row => row.asset_id === id ? {...row, preview: {state: "PURGING", media_url: null}} : row)); setWindows({});
    try {await workspaceRequest(csrf, `assets/${id}/preview`, "DELETE"); delete requests.current[id]; setMessage("Converted playback removed. The original recording remains in your workspace.");}
    catch {setError("Cleanup is pending. Playback stays hidden until its current state is confirmed.");}
    finally {setBusy(null); setRevision(v => v + 1);}
  }
  async function gaps(id: string, offset = 0) {
    try {const result = await workspaceRequest<Windows>(csrf, `assets/${id}/preview/quality?offset=${offset}`, "GET"); setWindows(values => ({...values, [id]: result}));}
    catch {setWindows({}); setRecordings(rows => rows.map(row => row.asset_id === id ? {...row, preview: {state: "UNAVAILABLE", media_url: null}} : row)); setError("Timing details are unavailable. Playback has been cleared.");}
  }
  return <section className="wide" id="private-recordings" aria-labelledby="private-recordings-heading">
    <div className="eyebrow">Replay review</div><h2 id="private-recordings-heading">Private recordings</h2>
    <p>Watch your recordings here. Playback preparation keeps the recorded timing and shows gaps; it does not approve frame-accurate coaching.</p>
    {error && <p role="alert" className="notice error">{error}</p>}{message && <p role="status">{message}</p>}
    <details><summary>Add an MP4 recording</summary><form onSubmit={event => {event.preventDefault(); const form = new FormData(event.currentTarget); const recording = file.current?.files?.[0]; if (!recording) return; const build = String(form.get("build") ?? "").trim(); void upload.start(recording, {...(build ? {game_build: build} : {}), platform: "steam"}, undefined, true).then(result => {if (result) {setRevision(v => v + 1); setMessage("Recording received. Private playback is being prepared.");}});}}>
      <p>For your own permitted H.264 or HEVC MP4: 1080p SDR, nominal 60 fps, up to 10 minutes and 512 MiB. Timing gaps are retained for review.</p>
      <label htmlFor="playback-file">Recording file</label><input id="playback-file" ref={file} type="file" accept="video/mp4,.mp4" required/>
      <label htmlFor="playback-build">Game version, if known</label><input id="playback-build" name="build" maxLength={80} placeholder="For example, 3.02.02"/>
      <label><input type="checkbox" required/>I allow private processing of this recording and have permission to use it.</label>
      <button disabled={upload.busy}>Upload for playback</button><UploadProgress upload={upload}/>
    </form></details>
    {!recordings.length ? <p>No private recordings yet. Public match statistics do not include playable video.</p> : recordings.map(recording => {
      const preview = recording.preview ?? {state: "NOT_PREPARED", media_url: null};
      const quality = preview.quality;
      const trustedUrl = preview.media_url === `/api/assets/${recording.asset_id}/preview/media`;
      return <div className="result" key={recording.asset_id}>
        <p>{displayTime(recording.uploaded_at, zone)} · {(recording.bytes / 1024 ** 2).toFixed(1)} MiB</p>
        {preview.state === "READY" && trustedUrl ? <>
          <span className="tag">Playback ready</span><video controls preload="none" aria-label="Private converted recording" style={{display: "block", marginTop: 12, width: "100%", maxWidth: 960}} src={preview.media_url!}><track kind="captions"/>Your browser does not support video playback.</video>
          {quality && <div className="notice"><strong>Timing quality</strong><p>{quality.gaps_over_limit} large gaps · {quality.irregular_intervals} uneven intervals · longest gap {(quality.max_frame_gap_us / 1000).toFixed(1)} ms.</p><p>Frame-accurate coaching is unapproved. Recorded continuity cannot establish moves, uninterrupted playback or match attribution.</p>{quality.irregular_intervals > 0 && <button onClick={() => void gaps(recording.asset_id)}>Review timing positions</button>}</div>}
          {windows[recording.asset_id] && <details open><summary>Original recorded timing positions</summary><div style={{maxHeight: 320, overflow: "auto"}}><table><thead><tr><th>Recorded position</th><th>Interval</th><th>Quality</th></tr></thead><tbody>{windows[recording.asset_id].intervals.map((item, index) => <tr key={index}><td>{(item.start_us / 1e6).toFixed(3)}–{(item.end_us / 1e6).toFixed(3)} s</td><td>{(item.gap_us / 1000).toFixed(1)} ms</td><td>{item.reason === "FRAME_GAP" ? "Large gap" : "Uneven spacing"}</td></tr>)}</tbody></table></div>{windows[recording.asset_id].next_offset !== null && <button onClick={() => void gaps(recording.asset_id, windows[recording.asset_id].next_offset!)}>Next timing positions</button>}</details>}
          <button disabled={busy === recording.asset_id} onClick={() => void remove(recording.asset_id)}>Remove converted playback</button>
        </> : ["QUEUED", "WAITING_UPLOAD"].includes(preview.state) ? <><p role="status">Preparing private playback{preview.phase ? `: ${preview.phase.toLowerCase()}` : ""}. {preview.progress ?? 0}%</p><button disabled={busy === recording.asset_id} onClick={() => void remove(recording.asset_id)}>Cancel playback preparation</button></> : preview.state === "PURGING" ? <p role="status">Playback cleanup pending. Storage is retained until cleanup is confirmed.</p> : preview.state === "UNAVAILABLE" ? <p>Recording access is unavailable or expired.</p> : <><p>Playback has not been prepared, or this recording could not be converted within the supported limits.</p><button disabled={busy === recording.asset_id} onClick={() => void prepare(recording.asset_id)}>Prepare playback</button></>}
      </div>;
    })}
  </section>;
}
