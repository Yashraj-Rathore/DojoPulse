# Private Windows recording sync (local developer preview)

This source helper syncs completed MP4s you create. It does not control Tekken,
download native replays, contact a game endpoint, or create gameplay measurements.
The website remains the private playback/training workspace. There is no signed
installer, automatic updater or activated hosted service yet.

## Run locally

Use the repository's Python 3.12 virtual environment and installed requirements;
Windows Tkinter and FFmpeg/FFprobe on PATH are required. Keep the existing API,
PostgreSQL and worker running as described in the [root README](../README.md).
In the API's terminal explicitly enable both local gates before restarting it:

```powershell
$env:LOCAL_OPERATOR_UPLOADS = '1'
$env:LOCAL_RECORDING_COMPANION = '1'
.\.venv\Scripts\python.exe manage.py migrate --noinput
.\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
```

Sign into the website as your existing local operator. In **Recording sync**,
review consent, enter a computer label and generate a one-use code. Then, from
the repository root in another terminal:

```powershell
.\.venv\Scripts\python.exe -m companion --server http://127.0.0.1:8000 --local-development
```

Enter the private code, pair, choose a folder containing only your own continuous
gameplay captures, and explicitly start sync. Existing files are excluded unless
you select **Include existing recordings** before choosing the folder. The helper
starts paused on every launch; press Start/resume to recover accepted offsets.
It is nonrecursive and supports finalized H.264 MP4, 1920×1080, constant 60 fps,
SDR, at most 600 seconds / 512 MiB. Unsupported/growing files stay local. A stable
size alone does not prove completion: finalized boxes, readable media profile,
byte hashes and server verification are checked separately.

Private synced recordings appear on the website after upload integrity and media
validation. Confirm the original match and its participants, slot, play time,
build, mode and session before submitting attribution. The imported UUID is
preserved, and operator visual review remains required. No match facts are inferred
from filename/file creation time; unassigned videos create no canonical Match.

## Controls and limits

- Pause/close stops after the current bounded request. Cancel stops the next pending
  transfer. Revoking the device on the website fences pending transfers; completed
  recordings remain private. Account recovery/logout-all and processing/sync
  withdrawal also revoke device access. Re-pair explicitly; old credentials never resume.
- Delete remote recordings on the website. Original PC files remain intact. A keyed
  server suppression receipt stops auto-sync from restoring a removed byte copy.
- DPAPI encrypts credentials, selected folder and receipts under the current Windows
  user in `%LOCALAPPDATA%\DojoPulse\companion\state.dpapi`. No account password or
  provider key is stored. Never share that file or a pairing code.
- Codes expire after ten minutes; device credentials expire after 30 days. At most
  five active devices, one owner upload, 500 folder entries, 256 local receipts and
  2,000 server byte receipts are admitted. Terminal local receipts expire after 90
  days; server suppression persists with the account. A reached cap stops admission.
- Transfers are serial, use at most 8 MiB chunks, respect owner quotas and Retry-After,
  and stop automatic retries after eight consecutive failures. An exhausted receipt
  remains rejected; no new upload is silently manufactured. Network calls timeout
  after 20 seconds. Credentials and upload URLs never cross origins or redirects.
- Only explicitly selected service origins are accepted. HTTPS is required except
  the explicit local-development option for `http://127.0.0.1:8000`. Hosted storage
  and external companion admission remain disabled pending qualification.

To remove the local helper, close it, revoke its device on the website, and remove
its protected local state folder yourself. That does not erase uploaded recordings;
delete those on the website separately. Installation/signing, independent privacy
review, real supported recorder/game fixtures and hosted performance remain M22.07–08.
