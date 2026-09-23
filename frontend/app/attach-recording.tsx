"use client";

import { useState } from "react";
import { displayTime } from "./workspace-api";

export type RecordingTarget = {
  metadata_revision: number; player_namespace: string; player_id: string; player_slot: number;
  opponent_ids: { namespace: string; value: string }[];
};

export default function AttachRecording({ csrf, match, onComplete, onCancel, zone = "UTC" }: {
  csrf: string;
  match: { id: string; played_at: string; mode: string; game_build: string | null; dataset_kind: string; recording_target: RecordingTarget };
  onComplete: () => void; onCancel: () => void;
  zone?: string;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [requestId, setRequestId] = useState(() => crypto.randomUUID());
  const opponent = match.recording_target.opponent_ids[0];
  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); setError("");
    const form = new FormData(event.currentTarget);
    const file = form.get("file") as File | null;
    if (!file || !file.name.toLowerCase().endsWith(".mp4") || file.size === 0 || file.size > 536870912) {
      setError("Choose an MP4 recording up to 512 MiB."); setBusy(false); return;
    }
    const body = new FormData();
    body.set("file", file); body.set("request_id", requestId); body.set("processing_consent", "true");
    body.set("metadata", JSON.stringify({
      ...match.recording_target, opponent_ids: undefined,
      player_id: form.get("player_id"), opponent_namespace: opponent?.namespace, opponent_id: form.get("opponent_id"),
      game_build: form.get("game_build"), played_at: match.played_at, source_kind: form.get("source_kind"),
      session_id: form.get("session_id"), dataset_kind: form.get("dataset_kind"), characters: ["jin", "jin"], attribution_confirmed: true,
    }));
    try {
      const response = await fetch(`/api/matches/${match.id}/recordings`, {
        method: "POST", credentials: "same-origin", headers: { "X-CSRFToken": csrf }, body,
      });
      const result = await response.json();
      if (!response.ok) throw new Error(typeof result.error === "string" ? result.error : "Check the recording details and try again.");
      onComplete();
    } catch (problem) { setError(problem instanceof Error ? problem.message : "Upload failed."); }
    finally { setBusy(false); }
  }

  return <div className="recording-panel" role="region" aria-label="Attach recording form">
    <h3>Attach gameplay recording</h3>
    <p>This recording will be linked to the selected match. A local operator must review the attribution before its gameplay evidence can be published.</p>
    <p className="muted">Current capture support: Jin vs Jin, 1080p, constant 60 fps, SDR H.264 MP4; one continuous match or practice block, up to 10 minutes / 512 MiB.</p>
    <p>Original match time: {displayTime(match.played_at, zone)}. Player slot: {match.recording_target.player_slot}. Match data is {match.dataset_kind}.</p>
    {error && <p className="notice error" role="alert">{error}</p>}
    <form onSubmit={submit} onChange={() => { if (!busy) setRequestId(crypto.randomUUID()); }}>
      <fieldset disabled={busy}>
        <label htmlFor="attached-file">Gameplay recording</label><input id="attached-file" type="file" name="file" accept="video/mp4" required />
        <div className="rows">
          <div><label htmlFor="recorded-player">Player ID visible in recording</label><input id="recorded-player" name="player_id" defaultValue={match.recording_target.player_id} required maxLength={200} /></div>
          <div><label htmlFor="recorded-opponent">Opponent ID visible in recording</label><input id="recorded-opponent" name="opponent_id" defaultValue={opponent?.value || ""} required maxLength={200} /></div>
          <div><label htmlFor="recorded-build">Recorded game build</label><input id="recorded-build" name="game_build" defaultValue={match.game_build || ""} placeholder="Exact build shown in the game" required maxLength={80} /></div>
          <div><label htmlFor="recorded-session">Recording session ID</label><input id="recorded-session" name="session_id" required maxLength={100} /></div>
          <div><label htmlFor="recorded-purpose">Recorded purpose</label><select id="recorded-purpose" name="source_kind" defaultValue={["ranked", "practice", "takeover"].includes(match.mode) ? match.mode : ""} required><option value="">Confirm the purpose</option><option value="ranked">Ranked match</option><option value="practice">Practice</option><option value="takeover">Replay takeover</option></select></div>
          <div><label htmlFor="recorded-kind">Recording content</label><select id="recorded-kind" name="dataset_kind" defaultValue="" required><option value="">Confirm the content</option><option value="real">Real gameplay</option><option value="synthetic">Synthetic test recording</option></select></div>
        </div>
        <label><input type="checkbox" required />I checked both players, their slots, the original play time, build and purpose. This recording shows Jin vs Jin and belongs to this match.</label>
        <label><input type="checkbox" required />I consent to processing and storing this recording for evidence review.</label>
        <button>{busy ? "Uploading recording…" : "Upload for attribution review"}</button>
        <button type="button" className="secondary" onClick={onCancel}>Cancel attachment</button>
      </fieldset>
    </form>
  </div>;
}
