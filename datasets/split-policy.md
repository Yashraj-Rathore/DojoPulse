# Split policy

Default split unit is player: all captures and sessions for a player remain in one of
development, validation, held-out. Never split adjacent frames or re-encodes of the same
capture across splits. Also enforce unique source hashes and single-split session IDs.
If player-held-out is impossible, document a separate session-held-out study; do not silently
weaken this default or claim unseen-player performance. Thresholds are frozen on validation.

Manifest validator rejects player/session/source leakage and duplicate source IDs. A test
fixture may be synthetic; dataset_kind must stay synthetic throughout reports and results.

