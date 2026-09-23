# Prospective pilot protocol / 1

Status: PREPARED, NOT RUN. One target, one draft drill, no participant data collected.
Owner: project technical owner; gameplay expert and independent reviewers not yet assigned.
Decision basis: Architecture V2, ADR-011/012 and the six gates in experiment-plan.md.

## Enrollment and consent

Recruit only consenting adult Tekken 8 Steam PC players initially. Collect no user data until
the participant agrees to service processing, study retention and the specified study purpose.
Training/research reuse is a separate optional consent, off by default. Use participant
pseudonyms; store contact/consent identity separately from media and annotation IDs.
Give participants withdrawal/deletion instructions. Do not imply gameplay is anonymous.

First verify the player's exact installed build and rights to provide their own footage.
The discovery build 3.02.01 is provisional, not a claim that every participant runs it.
If the game updates or licensing/recording permission is unclear, stop affected enrollment.

## Stage A: observable target and reviewed drill (G1/G4)

Acquire 20 representative full captures across multiple players/sessions under the strict
profile, including the target and negative controls. Include both sides, success, failure,
no attempt, unreachable spacing, wall/off-axis, resource changes, occlusion and uncertainty.
Record all target candidates; do not collect only obvious successes.
Natural-ranked captures and arranged practice controls must be separately identified.

Two reviewers independently annotate eligibility/outcome and confidence with elapsed time.
Use a third reviewer for disagreement. Review original frames and source timestamps.
Record whether required overlays are visible in the installed build, how indicator timing
relates to contact, and whether replay export preserves the original play chronology.
Do not treat an overlay string alone as proof of this actor's opportunity.

A Tekken expert must verify move identity, response startup/reach, timing windows, wall/axis
exclusions, and randomized practice alternatives before publishing new approved versions.
The single draft drill is the only proposed exercise; no fabricated expert sign-off.
For practice measurement collect 10 players × at least 40 attempts, preserving invalid/unknown
trials and their denominators. Count valid reviewed practice, not a self-reported completion.

G1 success: >=90% windows resolvable; failure: >20% unobservable.
G4 success: >=90% practice coverage and >=95% outcome agreement; failure: <80% coverage
or a systematic outcome bias. Intermediate outcomes require a recorded narrowing decision.

## Stage B: extraction and capture friction (G2/G3)

Freeze capture, knowledge and label contracts after Stage A. Keep players/sessions/captures
disjoint across development, validation and held-out test. Tune only on development; choose
thresholds on validation; do not repeatedly tune on the held-out test.
Preserve near misses and target-absent recordings. A new detector requires a new version.

Report precision, recall, F1, abstention, outcome coverage and timestamp error; score success
and failure separately. Require >=300 accepted critical held-out predictions plus representative
negatives, and enough predictions in each critical outcome slice to evaluate its confidence
bound. Global sample size alone cannot pass an underrepresented failure slice.
G2 acceptance: precision >=.98 with one-sided 95% lower >=.95 and recall >=.60 in both slices.
Stop automatic judgments if precision remains <.95 at recall >=.50 after two iterations.
Manual measurement may continue under an explicit human-reviewed pilot decision.

Ask 15–20 players to follow the capture guide without live coaching. Log steps, failures,
setup duration, export duration and support time. G3 acceptance: >=80% valid captures and
median setup <=10 minutes; <50% after a revision means change ingestion.
No particular capture profile can be called supported until these checks run.

## Stage C: natural frequency and complete comparison (G5/G6)

Enroll 20 prospective histories for four weeks once human measurement is accepted.
Record usual play and practice first. Keep an all-session play log including sessions with
zero target opportunities and all excluded/missing captures. Avoid targeted farming in
ranked follow-up; practice footage is separately tagged.
Frequency uses eligible opportunities / reviewed playable minutes; missing duration stays unknown.

For each player:
1. Review complete baseline sessions and diagnose the one observed weakness using counts,
   unknowns, coverage and uncertainty. Avoid selecting a target after inspecting follow-up.
2. Freeze the plan, baseline IDs/hashes, exact definitions, context, windows and stop policy.
3. Compare the structured drill with native replay tips and the player's existing method
   using an opt-in delayed-start pilot. Record allocation before follow-up; balance observation
   windows and capture instructions. Record other coaching/practice and rank/context changes.
4. Review and link at least 40 known eligible practice attempts after the plan is frozen.
5. Collect all subsequent target evidence in the fixed later window; aim for at least
   40 known opportunities and 5 independent sessions per period.
6. Evaluate once the window ends. Insufficient exposure, incompatibility and uncertainty are
   outcomes, not reasons to extend the window until the result becomes positive.
7. Ask whether the measurement changed the next practice decision and whether the added time
   was useful compared with native tools. Record time to insight, clarity, adherence and
   measured comparison coverage; assess actual willingness to pay only through a separately
   approved offer. Do not invent a price or claim causal efficacy.

G5/G6 exploratory success: >=60% meet their feasibility/evaluability targets.
<30% after the fixed observation period means change target or stop the proposition.
If native tools produce equally useful decisions with substantially less effort, revise
differentiation before expanding product scope. Do not use a p-value to rescue low utility.

## Cost and reproducibility record

Store private manifest revision, source hashes, exact builds/capture/knowledge/detector/drill
versions, plan/result hashes, selected/excluded memberships and reviewer/adjudicator pseudonyms.
Record CPU seconds, wall seconds, peak memory, source/derived bytes, transferred bytes if
measured, failures/retries, review/support minutes and contracted rates.
Calculate per capture, completed analysis, completed loop and comparable evaluation cost.
Unknown rates/invoices remain null; a local synthetic run does not estimate cloud economics.

For each G1–G6 result copy experiment-results/gate-template.json, fill actual denominators,
confidence bounds, source hashes, exclusions, review cost, decision and decision owner.
Maintain held-out test integrity and retain adverse outcomes.
Media must remain available for the complete follow-up plus audit, within the consented
maximum 60 days or an explicitly agreed extension. Expiry/withdrawal invalidates dependencies.

## Current handoff

Needed now: consented private captures, exact in-game build/settings evidence, pseudonymous
player/session/played-at logs, two independent reviewers plus adjudicator, and a Tekken expert
for the single drill. No footage needs to be committed or sent to an external service.
Hosted upload work waits for actual parser isolation, private-object IAM, resumable cancellation,
late-finalization, backup/deletion, cost and concurrency-cap rehearsals.
