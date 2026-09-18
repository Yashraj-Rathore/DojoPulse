# Capture contract V1

Status: specified, not gameplay-validated. Exact machine limits: contracts/capture-profile-v1.json.
Steam/Windows, English, 1920x1080, 16:9, SDR, constant 60 fps, original playback speed,
H.264 MP4, <=10 minutes, <=512 MiB. One continuous match or practice block; separate files.
Both input histories, HUD, frame information and in-battle status must remain visible.
Do not crop/scale/letterbox, add face cams/subtitles, hide HUD or edit speed. No pauses,
rewinds, takeover or cuts in match analysis. Camera effects inherent to the game are allowed
only if the target window remains observable; cinematic/occluded windows are unknown.

Build confirmation and participant identity are mandatory operator review fields. Capture
metadata alone cannot certify an overlay or exact frame synchronization. Nominal 60 fps is
checked against actual presentation timestamps; it still does not prove simulation alignment.
A source can pass technical validation and still be REVIEW_REQUIRED for gameplay.

Valid example (hypothetical): uninterrupted replay at native speed, full overlays, confirmed
build, complete block/contact/response window. Invalid: phone recording, 30 fps stream,
variable-speed replay, missing input region, wall/off-axis target, unidentified build. No
actual valid example footage exists in this repository.

Official v2.00.01 documents PUNISH/COUNTER/combo indicators. Current behavior including
text duration, actor attribution and visibility must be observed in G1. No absent indicator
establishes a failure. Draft region coordinates and templates must be calibrated from private
fixtures; none are invented as verified presets.

