# Agent Protocol

Only two production Agent roles exist:

- **Scene Lock Agent:** one `scenes[]` record per scene; it writes immutable production facts only.
- **Master Production Agent:** one T2V `shots[]` task per main shot, with `source_subshot_ids` for internal beats.

Workers write only `packet._batch_output_path`, then provenance is recorded. A running worker emits a heartbeat. Retries receive the validator issue store and patch only named fields of the owning main-shot task. No other Agent role or phase may be dispatched.

Before Editor Pass 2, the local `pre_editor_gate.py` writes one SHA-256-keyed
deterministic-plus-semantic audit artifact for the merged package. A
deterministic failure blocks dispatch; semantic findings are passed to Editor
for repair. Editor still performs Agent semantic review for every window:
`light` windows inspect the current shot plus carryover, while `high` windows
inspect the full bounded scene window. A light tier never waives an Agent pass,
final validation, or export QA.
