"""python -m companion --server https://reviewed-service.example (Windows only)."""

import argparse
import hashlib
import os
import queue
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from companion.credentials import StateStore
from companion.sync import SyncEngine, Transport, server_origin


def main() -> None:
    parser = argparse.ArgumentParser(
        description="DojoPulse private recording sync; no automatic game capture"
    )
    parser.add_argument("--server", required=True, help="Explicit trusted DojoPulse service origin")
    parser.add_argument(
        "--local-development",
        action="store_true",
        help="Allow only http://127.0.0.1:8000 for local qualification",
    )
    args = parser.parse_args()
    if sys.platform != "win32":
        parser.error("The recording companion requires Windows per-user credential storage")
    origin = server_origin(args.server, args.local_development)
    root = Path(os.environ["LOCALAPPDATA"]) / "DojoPulse" / "companion"
    root.mkdir(parents=True, exist_ok=True)
    # One writer per Windows user/state path. The OS releases the mutex on process exit.
    import ctypes
    from ctypes import wintypes

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
    kernel.CreateMutexW.restype = wintypes.HANDLE
    mutex = kernel.CreateMutexW(
        None, False, "Local\\DojoPulse-" + hashlib.sha256(str(root).encode()).hexdigest()
    )
    if not mutex or ctypes.get_last_error() == 183:
        parser.error("DojoPulse recording sync is already open")
    store = StateStore(root / "state.dpapi")
    state = store.load()
    if state and state.get("origin") != origin:
        parser.error(
            "This companion is paired with a different service; revoke it before changing service"
        )
    transport = Transport(
        origin, state.get("credential", ""), local_development=args.local_development
    )
    engine = SyncEngine(store, transport)
    window = tk.Tk()
    window.title("DojoPulse • Private recording sync")
    window.geometry("670x570")
    status = tk.StringVar(value="Paused — no folders scanned until you start")
    folder = tk.StringVar(
        value="Selected folder configured" if state.get("folder") else "No folder selected"
    )
    consent, include = tk.BooleanVar(), tk.BooleanVar()
    frame = ttk.Frame(window, padding=20)
    frame.pack(fill="both", expand=True)
    ttk.Label(frame, text="DojoPulse recording companion", font=("Segoe UI", 18, "bold")).pack(
        anchor="w"
    )
    ttk.Label(
        frame,
        text="Sync existing MP4 recordings to your private web workspace.\nThis version does not control Tekken or create recordings.",
        wraplength=610,
    ).pack(anchor="w", pady=10)
    ttk.Label(frame, text="Service: " + origin).pack(anchor="w")
    ttk.Label(frame, text="One-use pairing code from the website’s Recording sync section").pack(
        anchor="w", pady=(12, 0)
    )
    code = ttk.Entry(frame, show="•", width=60)
    code.pack(anchor="w")
    messages: queue.Queue[str] = queue.Queue()
    stopped = threading.Event()
    working = threading.Event()

    def pair() -> None:
        if working.is_set() or engine.enabled:
            return
        try:
            result = transport.request(
                "POST", "/api/companion/pair", {"pairing_code": code.get().strip()}
            )
            if result.get("scope") != "recording-sync/1":
                raise ValueError("INVALID_DEVICE_SCOPE")
            if engine.state.get("owner_id") and engine.state["owner_id"] != result["owner_id"]:
                raise ValueError("USE_ORIGINAL_OWNER_OR_CLEAR_LOCAL_STATE")
            engine.state.update(
                {
                    "origin": origin,
                    "owner_id": result["owner_id"],
                    "device_id": result["device_id"],
                    "credential": result["credential"],
                    "credential_expires_at": result["expires_at"],
                }
            )
            transport.credential = result["credential"]
            store.save(engine.state)
            code.delete(0, tk.END)
            status.set("Paired. Select your gameplay folder and explicitly start sync.")
        except (ValueError, OSError) as error:
            status.set(str(error) if str(error).isupper() else "PAIRING_FAILED")
        except Exception:
            status.set("PAIRING_FAILED — check the code, service and local qualification")

    ttk.Button(frame, text="Pair this computer", command=pair).pack(anchor="w", pady=6)
    ttk.Checkbutton(
        frame, text="Include existing recordings when selecting a folder", variable=include
    ).pack(anchor="w")

    def choose() -> None:
        if working.is_set() or engine.enabled:
            status.set("Pause and wait for the current request before changing folders")
            return
        value = filedialog.askdirectory(
            parent=window, title="Choose a folder containing only your gameplay recordings"
        )
        if value:
            try:
                engine.select_folder(Path(value), include_existing=include.get())
                folder.set("Selected folder configured (stored privately on this PC)")
                status.set("Paused — folder selected")
            except (ValueError, OSError):
                status.set("FOLDER_REJECTED — use an ordinary folder with at most 500 files")

    ttk.Button(frame, text="Choose recording folder", command=choose).pack(anchor="w", pady=6)
    ttk.Label(frame, textvariable=folder).pack(anchor="w")
    ttk.Checkbutton(
        frame,
        text="I allow syncing my own continuous gameplay recordings from this folder.",
        variable=consent,
    ).pack(anchor="w", pady=10)
    ttk.Label(
        frame,
        text="Supported: finalized H.264 MP4, 1080p, constant 60 fps, SDR, ≤10 minutes / 512 MiB.\nOther files stay local. Match attribution and coaching review are separate.",
        wraplength=610,
    ).pack(anchor="w")
    buttons = ttk.Frame(frame)
    buttons.pack(anchor="w", pady=12)

    def start() -> None:
        if not consent.get() or not transport.credential or not engine.state.get("folder"):
            status.set("Pair, choose a folder and confirm sync permission first")
            return
        engine.enabled = True
        status.set("Sync started — selected folder only")

    def pause() -> None:
        engine.enabled = False
        status.set("Pausing after the current bounded request; receipts retained")

    def cancel() -> None:
        if transport.credential and engine.state.get("folder"):
            engine.cancel_requested = engine.enabled = True
            status.set("Cancelling the next pending transfer; local originals retained")

    ttk.Button(buttons, text="Start / resume", command=start).pack(side="left", padx=(0, 8))
    ttk.Button(buttons, text="Pause", command=pause).pack(side="left", padx=(0, 8))
    ttk.Button(buttons, text="Cancel pending transfer", command=cancel).pack(side="left")
    ttk.Label(frame, textvariable=status, wraplength=610).pack(anchor="w", pady=10)
    count = tk.StringVar(value="No pending receipts")
    ttk.Label(frame, textvariable=count, wraplength=610).pack(anchor="w")
    ttk.Label(
        frame,
        text="Close to stop syncing. Revoke this device or delete uploaded recordings on the website.\nRemote deletion never deletes your original local recordings.",
        wraplength=610,
    ).pack(anchor="w", pady=12)

    def worker() -> None:
        while not stopped.wait(2):
            if engine.enabled:
                working.set()
                try:
                    messages.put(engine.tick())
                except Exception:
                    engine.enabled = False
                    messages.put("SYNC_STOPPED — check folder access and restart deliberately")
                finally:
                    working.clear()

    def update() -> None:
        while not messages.empty():
            status.set(messages.get_nowait())
        states = [r["state"] for r in engine.state["receipts"].values()]
        count.set(
            f"Receipts: {len(states)} · transferred: {states.count('COMPLETE')} · rejected: {states.count('REJECTED')}"
        )
        window.after(500, update)

    def close() -> None:
        pause()
        stopped.set()
        window.destroy()

    window.protocol("WM_DELETE_WINDOW", close)
    threading.Thread(target=worker, daemon=True).start()
    update()
    try:
        window.mainloop()
    finally:
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel.CloseHandle(mutex)


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError):
        messagebox.showerror(
            "DojoPulse",
            "Companion configuration or protected storage is unavailable. No sync started.",
        )
