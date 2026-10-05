# Capture acquisition and G1 observability assessment

M07.02-M07.05, M08.02-M08.05/M08.08 and M09.02-M09.04. Architecture 2.17.0.
This is a local evidence-assessment tool, not a released detector or an executed G1 study.

## Acquire original recordings

The preferred candidate route is the installed game's official replay viewer, recorded by
the player. This is USER_UPLOAD evidence with OFFICIAL in-client playback provenance, not
an official external replay API. No game-server transport, process-memory reader, controller
automation or third-party recorder code is added. See the dated
[source investigation](../research/capture-acquisition-2026-10-05.md).

Before collection, obtain the existing purpose-specific adult consent and retention agreement,
confirm applicable recording/processing rights, and assign a Tekken expert, two independent
reviewers and a third adjudicator. Do not enable gated real intake simply to make a test pass.
Record the installed **in-game version** and platform with evidence for expert review. A Steam
build number, upload date, channel title or latest patch announcement does not verify that version.

Use the original match's chronological replay, with HUD, both input histories, frame information
and in-battle status visible. Check that the installed version actually supplies those displays;
missing displays are unresolved evidence. Record 1920x1080, constant 60 fps, SDR H.264 MP4,
at most ten minutes/512 MiB per capture. No cuts, pauses, rewinds, speed changes, replay takeover,
cropping or streamer graphics. Record the build/settings evidence separately; it is not part of
an uncut gameplay recording. Keep originals private and out of Git.

For the initial 20 captures, predeclare player/session coverage and use multiple players and
sessions. Include both actor sides, successes, failures, no attempt, near misses, target-absent
controls, spacing, wall/axis/resource variants and occlusion. Record every candidate window,
including uncertain ones. Keep arranged practice/negative scenarios distinguishable from natural
ranked observations; they cannot establish natural target frequency. Pin original timestamps and
source hashes using existing capture tools. The provisional Jin/Jin uf+4 target and response
still require exact-build expert validation; this document supplies no frame facts or approval.

Use M07 knowledge review and M08 linked M18 consent/blinded review when their real-intake gates
have been satisfied. Freeze source membership, player/session splits and predictions before
held-out label access. Reviewers record conditions, visibility, elapsed time and explicit nullable
reference/frame timing; adjudicate disagreements independently. Exhaustive target inventory,
representativeness, reviewer qualifications and current rights need human verification.

## Assess without promoting

On a current owned dataset snapshot, **Assess observability** displays and downloads a hashed
`observability-assessment/1`. The API is
`GET /api/datasets/<dataset>/snapshots/<snapshot>/observability`. It shares the existing local
staff, session, consent, owner, restore quarantine, definition and live-input/retention checks.
Revocation or stale inputs erase/withhold the underlying snapshot before report access. Reports
are derived on demand; there is no new persistent table, copied label store or release command.

The same result is reproducible offline:

```powershell
.venv/Scripts/python.exe -m tools.assess_observability private_data/snapshot.json --output reports/g1-observability.json
```

The CLI accepts a bounded 16 MiB snapshot, validates its content hash, annotation/review/split/QA
contracts and assessment-specific labels, and refuses to overwrite that input. It never fetches
or decodes media. Its portable receipt cannot prove current consent or source bytes. Neither
downloaded report nor snapshot is exempt from retention/deletion duties.

Only ranked TARGET windows enter the critical denominator. TRIAL/practice sources remain
separate; target-absent controls increase capture/control counts without inventing resolvable
windows. Every unresolved target remains in the denominator. Resolvability requires final
RESOLVABLE visibility, explicit critical conditions, an identifiable eligible known outcome or
reviewed exclusion, and uncertainty within 16,667 microseconds. An exclusion cannot rescue an
unknown actor/move/build or incomplete window. Known success/failure is rederived through the
same provider-independent rule engine. Unknowns never become failures.

Complete dual/reference/frame timing is reported separately from resolvability. Reviewer timing
agreement is not proof of frame accuracy. Reports include aggregate reasons, categories,
captures/players/sessions, per-source minimum/median resolvability, per-split metrics, recorded
session states and review time. Source IDs, reviewer identities and individual labels are omitted.
Rates are null for zero windows. Duplicate tasks, invalid kinds or target/practice mixing fail.

The proposed numeric result is INSUFFICIENT_EVIDENCE below 20 ranked captures or with no critical
windows; MEETS_PROPOSED_THRESHOLD at >=90% resolvability; NARROW_REQUIRED above 20% unresolved;
otherwise REVIEW_REQUIRED. Exact integer comparisons preserve the 80%/90% boundaries. This
numeric description is independent of missing categories, multiple players/sessions, source QC,
timing completeness and the external rights/expert/protocol checks, all shown as blockers.
Even a perfect synthetic or real-labelled receipt retains G1 NOT_RUN and release_approval false.

Actual G1, approved exact-build facts, permitted real footage and qualified reviewers remain
required. G1 cannot establish G2 automatic accuracy. Do not tune on held-out evaluation data;
M09 observation implementations and calibration need a separately frozen unseen evaluation.
