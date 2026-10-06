"use client";

import { useEffect, useState } from "react";
import AttachRecording, { type RecordingTarget } from "./attach-recording";
import { displayTime, workspaceRequest } from "./workspace-api";

type Device = {id: string; label: string; expires_at: string; revoked_at: string | null};
type Recording = {id: string; asset_id: string; availability: string; uploaded_at: string; bytes: number; media_url: string | null; match_id: string | null; attribution_state: string};
type Match = {id: string; played_at: string; mode: string; game_build: string | null; dataset_kind: string; can_attach_recording: boolean; recording_target: RecordingTarget};
type Devices = {enabled: boolean; policy_version: string; policy: string; devices: Device[]};
const initial: Devices = {enabled: false, policy_version: "", policy: "", devices: []};

export default function RecordingSync({csrf, zone = "UTC"}: {csrf: string; zone?: string}) {
  const [devices, setDevices] = useState<Devices>(initial);
  const [recordings, setRecordings] = useState<Recording[]>([]);
  const [matches, setMatches] = useState<Match[]>([]);
  const [reload, setReload] = useState(0);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [code, setCode] = useState<{pairing_code: string; expires_at: string} | null>(null);
  const [removing, setRemoving] = useState<string | null>(null);
  const [target, setTarget] = useState<Record<string, string>>({});
  const [attaching, setAttaching] = useState<string | null>(null);
  useEffect(() => {
    const controller = new AbortController();
    let loading = false;
    async function load() {
      if (loading) return;
      loading = true;
      try {
        const [d, r, m] = await Promise.all([
          workspaceRequest<Devices>(csrf, "recording-devices", "GET", undefined, controller.signal),
          workspaceRequest<{recordings: Recording[]}>(csrf, "synced-recordings", "GET", undefined, controller.signal),
          workspaceRequest<{matches: Match[]}>(csrf, "matches?limit=20", "GET", undefined, controller.signal),
        ]);
        if (!controller.signal.aborted) {setDevices({...initial, ...d, devices: d.devices ?? []}); setRecordings(r.recordings ?? []); setMatches((m.matches ?? []).filter(item => item.can_attach_recording && item.recording_target));}
      } catch (problem) {if (!controller.signal.aborted) setError(problem instanceof Error ? problem.message : "Recording sync unavailable");}
      finally {loading = false;}
    }
    void load();
    const timer = setInterval(() => {if (document.visibilityState === "visible") void load();}, 10000);
    return () => {controller.abort(); clearInterval(timer);};
  }, [csrf, reload]);
  useEffect(() => {
    if (!code) return;
    const timer = setTimeout(() => setCode(null), Math.max(0, new Date(code.expires_at).getTime() - Date.now()));
    return () => clearTimeout(timer);
  }, [code]);
  async function act(work: () => Promise<void>) {
    setBusy(true); setError(""); setMessage("");
    try {await work(); setReload(value => value + 1);}
    catch (problem) {setError(problem instanceof Error ? problem.message : "Request failed");}
    finally {setBusy(false);}
  }
  return <section className="wide" id="recording-sync" aria-labelledby="recording-sync-heading">
    <div className="eyebrow">Your PC → private workspace</div><h2 id="recording-sync-heading">Recording sync</h2>
    <p>Pair a Windows companion to sync completed recordings from a folder you choose. It starts paused and does not create recordings or control Tekken.</p>
    <p className="muted">Developer preview: Windows source helper; installer and hosted operation await qualification. A TEKKEN ID alone does not grant access to recordings.</p>
    {error && <p role="alert" className="notice error">{error}</p>}{message && <p role="status" className="notice">{message}</p>}
    {devices.enabled ? <form onSubmit={event => {event.preventDefault(); const form = new FormData(event.currentTarget); void act(async () => {setCode(null); setCode(await workspaceRequest(csrf, "recording-devices", "POST", {label: form.get("label"), sync_consent: form.get("sync_consent") === "on", policy_version: devices.policy_version}));});}}>
      <label htmlFor="recording-device-label">Computer label</label><input id="recording-device-label" name="label" maxLength={60} pattern="[A-Za-z0-9 ._-]+" required placeholder="My gaming PC"/>
      <label><input type="checkbox" name="sync_consent" required/>I allow this paired computer to sync my recordings. I understand remote deletion keeps my local originals.</label>
      <details><summary>Recording sync consent</summary><p>{devices.policy}</p></details><button disabled={busy}>Create pairing code</button>
    </form> : <p className="notice">Pairing is disabled until the local operator enables recording sync. Manual upload remains available.</p>}
    {code && <div className="notice" role="status"><p>Enter this one-use code in the Windows companion before {displayTime(code.expires_at, zone)}. Keep it private.</p><label htmlFor="device-pairing-code">Pairing code</label><input id="device-pairing-code" readOnly value={code.pairing_code} autoComplete="off"/><button onClick={() => setCode(null)}>Hide pairing code</button></div>}
    <h3>Paired computers</h3>{!devices.devices.length ? <p>No computers paired.</p> : devices.devices.map(device => <div className="result" key={device.id}><strong>{device.label}</strong><p>{device.revoked_at ? "Revoked" : new Date(device.expires_at) <= new Date() ? "Expired — pair again" : `Access expires ${displayTime(device.expires_at, zone)}`}</p>{!device.revoked_at && <button disabled={busy} onClick={() => void act(async () => {await workspaceRequest(csrf, `recording-devices/${device.id}`, "DELETE"); setCode(null); setMessage("Device revoked. Pending transfers stop; completed recordings remain private.");})}>Revoke {device.label}</button>}</div>)}
    <h3>Private synced recordings</h3><p className="muted">Latest 50 recordings. Upload time is separate from original match time. Gameplay approval remains separate from playback availability.</p>
    {!recordings.length ? <p>No synced recordings yet. Recording files are needed; public match history does not supply video.</p> : recordings.map(recording => {
      const match = matches.find(item => item.id === target[recording.id]);
      return <div className="result" key={recording.id}><span className="tag">{recording.availability}</span><p>{displayTime(recording.uploaded_at, zone)} · {(recording.bytes / 1024**2).toFixed(1)} MiB · {recording.attribution_state.replaceAll("_", " ")}</p>
        {recording.availability === "AVAILABLE" && recording.media_url?.startsWith("/api/assets/") && <video controls preload="none" aria-label="Private synced recording" style={{width: "100%", maxWidth: 720}} src={recording.media_url}><track kind="captions"/>Your browser does not support video playback.</video>}
        {recording.availability === "PENDING" && <p role="status">Transfer or media validation is pending. Playback is unavailable until validation succeeds.</p>}
        {["ERROR", "INCOMPATIBLE"].includes(recording.availability) && <p>Recording could not be validated for the supported capture profile.</p>}
        {recording.availability === "EXPIRED" && <p>Recording retention expired. Availability of an original game replay is separate.</p>}
        {!recording.match_id && recording.availability === "AVAILABLE" && <><label htmlFor={`synced-target-${recording.id}`}>Imported match for this recording</label><select id={`synced-target-${recording.id}`} value={target[recording.id] ?? ""} onChange={event => setTarget({...target, [recording.id]: event.target.value})}><option value="">Choose a match after checking the video</option>{matches.map(item => <option key={item.id} value={item.id}>{displayTime(item.played_at, zone)} · {item.mode} · {item.id.slice(0,8)}</option>)}</select><button disabled={!match || busy} onClick={() => setAttaching(recording.id)}>Confirm match attribution</button>{attaching === recording.id && match && <AttachRecording csrf={csrf} zone={zone} match={match} syncedSession={recording.id} onComplete={() => {setAttaching(null); setReload(value => value + 1); setMessage("Attribution submitted for visual review. Gameplay events were not created.");}} onCancel={() => setAttaching(null)}/>}</>}
        {recording.availability !== "REMOVED" && (removing === recording.id ? <><p>Delete this remote recording and its evidence? Your original PC file stays intact.</p><button disabled={busy} onClick={() => void act(async () => {await workspaceRequest(csrf, `assets/${recording.asset_id}`, "DELETE"); setRemoving(null); setMessage("Remote recording deleted; local original retained. Automatic sync will not restore the removed copy.");})}>Delete remote recording</button><button onClick={() => setRemoving(null)}>Keep recording</button></> : <button disabled={busy} onClick={() => setRemoving(recording.id)}>Remove synced recording</button>)}
      </div>;
    })}
  </section>;
}
