# Review reconciliation

The source review is the complete 28-part adversarial response in the project conversation,
dated 2026-09-18, with final decision MODIFY. This is its implementation traceability extract,
not a fabricated separate review or verbatim transcript. V1 was read in full in that review
and consulted again before implementation. The only original repository file was
`docs/architecture.md`; ADRs existed inside its section 33, not separate files.

| Required change | V2 resolution | Evidence/release dependency |
|---|---|---|
| Loop-first objective | architecture-v2 and improvement-loop | G6; no positive result required |
| Recognition scope | one Jin/Jin blocked uf+4 situation | ADR-011; provisional pending G1/G5 |
| Observable contracts | situation JSON and event model | G1/G2 |
| EvaluationPlan/result | frozen membership and comparison services | invariant and API tests |
| Verified practice first | recorded practice + two-reviewer adjudication | ADR-012; G4 |
| Freeze definitions | immutable contract/version/hash references | schema and historical tests |
| Study retention | through follow-up/audit, consent bound | ADR-009; deletion tests |
| Native comparator | prospective pilot protocol | G3/G6 |

Other high findings: separate detection and outcome coverage; audit memory at maximum
accepted input; cancel pending upload sessions and reconcile late objects; record human
review economics. Cloud deployment remains withheld until these operational gates pass.

Preserved: monolith, PostgreSQL, private artifacts, explicit unknowns, knowledge pinning,
stable identities, revisioned publication, counts/Bayes, separate jobs and optional adapters.
Original ADR numbering is historical; the new `docs/adr` numbering follows the implementation brief.
