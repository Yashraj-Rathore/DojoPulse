"use client";

import { useEffect, useRef, useState } from "react";
import { sha256 } from "@noble/hashes/sha2.js";
import { md5 } from "@noble/hashes/legacy.js";
import { bytesToHex } from "@noble/hashes/utils.js";

type Transfer = { id: string; state: string; received_bytes: number; bytes: number; chunk_bytes: number; storage_provider: string; upload_url?: string; error_code?: string; run_id?: string };
type Receipt = { fingerprint: string; requestId: string; id?: string };
const receiptKey = "dojopulse-pending-upload";
class UploadError extends Error {
  constructor(message: string, readonly status: number) { super(message); }
}

function savedReceipt(): Receipt | null {
  try { return JSON.parse(sessionStorage.getItem(receiptKey) || "null"); } catch { return null; }
}
function saveReceipt(receipt: Receipt | null) {
  try { if (receipt) sessionStorage.setItem(receiptKey, JSON.stringify(receipt)); else sessionStorage.removeItem(receiptKey); } catch { /* In-memory retries still work if storage is unavailable. */ }
}
function wait(ms: number, signal: AbortSignal) {
  return new Promise<void>((resolve, reject) => {
    const timer = setTimeout(() => { signal.removeEventListener("abort", abort); resolve(); }, ms);
    const abort = () => { clearTimeout(timer); reject(new DOMException("Paused", "AbortError")); };
    if (signal.aborted) abort(); else signal.addEventListener("abort", abort, { once: true });
  });
}

export function useResumableUpload(csrf: string) {
  const controller = useRef<AbortController | null>(null);
  const receipt = useRef<Receipt | null>(null);
  const inFlight = useRef(false);
  const [busy, setBusy] = useState(false), [phase, setPhase] = useState("");
  const [percent, setPercent] = useState(0), [error, setError] = useState("");
  const [sessionId, setSessionId] = useState("");
  useEffect(() => () => controller.current?.abort(), []);

  async function api(path: string, method = "GET", body?: object, signal?: AbortSignal): Promise<Transfer> {
    const response = await fetch(`/api/upload-sessions${path}`, {
      method, credentials: "same-origin", cache: "no-store", signal,
      headers: { "X-CSRFToken": csrf, "Content-Type": "application/json" },
      body: body ? JSON.stringify(body) : undefined,
    });
    const data = await response.json();
    if (!response.ok) throw new UploadError(typeof data.error === "string" ? data.error : typeof data.detail === "string" ? data.detail : "Check the recording details and try again.", response.status);
    return data;
  }

  async function start(file: File, metadata: object, matchId?: string) {
    if (inFlight.current) return null;
    if (!file.name.toLowerCase().endsWith(".mp4") || !file.size || file.size > 536870912) { setError("Choose an MP4 up to 512 MiB."); setPhase("Upload interrupted"); return null; }
    inFlight.current = true;
    const control = new AbortController(); controller.current = control;
    const signal = control.signal;
    setBusy(true); setError(""); setPhase("Preparing file"); setPercent(0);
    try {
      const sha = sha256.create(), checksum = md5.create();
      // Small reads keep browser memory bounded even for the maximum capture profile.
      for (let offset = 0; offset < file.size; offset += 1024 * 1024) {
        signal.throwIfAborted();
        const block = new Uint8Array(await file.slice(offset, offset + 1024 * 1024).arrayBuffer());
        sha.update(block); checksum.update(block);
        setPercent(Math.min(100, Math.round((offset + block.length) / file.size * 100)));
      }
      signal.throwIfAborted();
      const sourceHash = bytesToHex(sha.digest());
      const md5Hash = btoa(String.fromCharCode(...checksum.digest()));
      const fingerprint = bytesToHex(sha256(new TextEncoder().encode(JSON.stringify({ sourceHash, bytes: file.size, metadata, matchId }))));
      const prior = receipt.current || savedReceipt();
      if (prior?.id) setSessionId(prior.id);
      if (prior && prior.fingerprint !== fingerprint) throw new Error("Resume the same file and details, or cancel the existing upload before starting another.");
      const saved = prior || { fingerprint, requestId: crypto.randomUUID() };
      receipt.current = saved; saveReceipt(saved);
      setPhase("Opening upload"); setPercent(0);
      let transfer = await api("", "POST", {
        request_id: saved.requestId, filename: file.name, bytes: file.size, sha256: sourceHash, md5: md5Hash,
        processing_consent: true, single_continuous: true, metadata, ...(matchId ? { match_id: matchId } : {}),
      }, signal);
      saved.id = transfer.id; setSessionId(transfer.id); saveReceipt(saved);
      const path = `/${transfer.id}`;
      function validateProgress(value: Transfer) {
        if (value.state === "UPLOADING" && (value.bytes !== file.size || !Number.isInteger(value.received_bytes) || value.received_bytes < 0 || value.received_bytes > file.size || !Number.isInteger(value.chunk_bytes) || value.chunk_bytes < 262144 || value.chunk_bytes > 8 * 1024 * 1024 || !["LOCAL", "GCS"].includes(value.storage_provider))) throw new Error("Upload progress is unavailable.");
      }
      validateProgress(transfer);
      let failures = 0;
      while (transfer.state === "UPLOADING" && transfer.received_bytes < file.size) {
        signal.throwIfAborted(); setPhase("Uploading recording");
        const offset = transfer.received_bytes;
        if (!Number.isInteger(offset) || offset < 0 || offset > file.size || transfer.chunk_bytes < 262144 || transfer.chunk_bytes > 8 * 1024 * 1024) throw new Error("Upload progress is unavailable.");
        const end = Math.min(file.size, offset + transfer.chunk_bytes);
        try {
          const cloud = transfer.storage_provider === "GCS";
          const target = cloud ? transfer.upload_url : `/api/upload-sessions${path}/chunk`;
          if (!target) throw new Error("Upload transfer is unavailable.");
          if (cloud) {
            const destination = new URL(target);
            if (destination.origin !== "https://storage.googleapis.com" || !destination.pathname.startsWith("/upload/storage/v1/b/")) throw new Error("Upload transfer is unavailable.");
          }
          const response = await fetch(target, {
            method: "PUT", signal, credentials: cloud ? "omit" : "same-origin", redirect: "error", referrerPolicy: "no-referrer", cache: "no-store",
            headers: cloud ? { "Content-Range": `bytes ${offset}-${end - 1}/${file.size}`, "Content-Type": "video/mp4" } : { "X-CSRFToken": csrf, "Content-Type": "application/octet-stream", "Upload-Offset": String(offset) },
            body: file.slice(offset, end),
          });
          if (!response.ok && response.status !== 308) {
            if (response.status === 429) await wait(Math.min(60000, Math.max(1000, Number(response.headers.get("Retry-After") || 1) * 1000)), signal);
            throw new Error("Transfer interrupted. Resume to check the bytes already received.");
          }
          // The server's observed offset is authoritative, including lost-response retries.
          transfer = await api(path, "GET", undefined, signal);
          validateProgress(transfer);
          if (transfer.received_bytes <= offset) throw new Error("Transfer has not advanced.");
          failures = 0;
          setPercent(Math.round(transfer.received_bytes / file.size * 100));
        } catch (problem) {
          if (signal.aborted) throw problem;
          if (++failures >= 3) throw new Error("Transfer interrupted. Choose Resume upload to continue from confirmed progress.");
          await wait(1000 * failures, signal);
          transfer = await api(path, "GET", undefined, signal);
          validateProgress(transfer);
          setPercent(Math.round(transfer.received_bytes / file.size * 100));
        }
      }
      if (transfer.state === "UPLOADING") transfer = await api(`${path}/complete`, "POST", {}, signal);
      setPhase("Checking recording integrity"); setPercent(100);
      for (let attempt = 0; transfer.state === "VERIFYING" && attempt < 180; attempt++) {
        await wait(1000, signal); transfer = await api(path, "GET", undefined, signal);
      }
      if (transfer.state !== "COMPLETE") throw new Error(transfer.state === "VERIFYING" ? "Verification is still queued. Resume later to check its result." : "This upload is unavailable. Cancel it before starting a new recording.");
      receipt.current = null; saveReceipt(null); setSessionId(""); setPhase("Recording queued for review");
      return transfer;
    } catch (problem) {
      if (signal.aborted) { setPhase("Upload paused"); return null; }
      const message = problem instanceof Error ? problem.message : "Upload interrupted. Resume to continue.";
      setError(message); setPhase("Upload interrupted"); return null;
    } finally { inFlight.current = false; setBusy(false); }
  }

  async function cancel() {
    controller.current?.abort();
    const saved = receipt.current || savedReceipt();
    const id = saved?.id || sessionId;
    if (!id) {
      setError("Resume once to retrieve the upload receipt before cancelling a pending transfer.");
      return;
    }
    setBusy(true); setError("");
    try {
      try { await api(`/${id}`, "DELETE"); }
      catch (problem) { if (!(problem instanceof UploadError) || problem.status !== 404) throw problem; }
      receipt.current = null; saveReceipt(null); setSessionId(""); setPhase("Upload cancelled"); setPercent(0);
    } catch (problem) { setError(problem instanceof Error ? problem.message : "Cancellation cleanup will be retried. Resume to inspect its state."); }
    finally { setBusy(false); }
  }

  return { start, busy, phase, percent, error, sessionId, pause: () => controller.current?.abort(), cancel };
}

export function UploadProgress({ upload }: { upload: ReturnType<typeof useResumableUpload> }) {
  if (!upload.phase) return null;
  return <div className="upload-progress" role="region" aria-label="Upload progress">
    <p role="status">{upload.phase}{["Preparing file", "Uploading recording"].includes(upload.phase) ? `: ${upload.percent}%` : ""}</p>
    <progress max={100} value={upload.percent} aria-label={upload.phase} />
    {upload.error && <p role="alert" className="notice error">{upload.error}</p>}
    {upload.busy && <button type="button" className="secondary" onClick={upload.pause}>Pause upload</button>}
    {upload.sessionId && !upload.busy && <button type="button" className="secondary" onClick={() => void upload.cancel()}>Cancel upload</button>}
    {["Upload paused", "Upload interrupted"].includes(upload.phase) && <p className="muted">Keep or reselect the same file and details, then choose Resume upload. Upload reservations expire after one hour.</p>}
  </div>;
}
