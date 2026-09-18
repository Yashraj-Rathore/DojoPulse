# Private golden dataset

No game footage belongs in Git. Set PTP_DATA_ROOT to a private directory; manifest paths must
be relative and resolve inside that root, including symlinks. Hash source bytes. Use pseudonymous
player/session IDs and retain consent evidence privately. The example manifest is NOT collected data.

Run python -m tools.validate_dataset manifest.json --root PRIVATE_ROOT to validate files,
hashes, annotation structure, split leakage and review consistency. Use --metadata-only for
manifest/split checks without claiming source validation. tools.annotate creates blank review
sidecars; humans supply labels. No template is valid evidence until reviewed.

Development tunes extraction; validation chooses thresholds; held-out test is evaluated once
per release decision. Store errors and exclusions, including unobservable cases, not only easy positives.

