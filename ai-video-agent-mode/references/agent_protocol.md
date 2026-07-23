# Agent Protocol

The supervisor owns the pipeline loop. It executes deterministic local phases
and asks the Codex host to dispatch Agent packets only when
`workflow_supervisor.py` returns `host_dispatch_required`. The host must resume
the same supervisor after recording verified provenance; it must not treat a
worker completion as a user-confirmation point.

Only three dispatch roles exist:

- **Scene Lock Agent:** one `scenes[]` record per scene; it writes immutable production facts only.
- **Master Production Agent:** one T2V `shots[]` task per main shot, with `source_subshot_ids` for internal beats.
- **Editor Pass 2 Agent:** one bounded scene-window review per packet; it writes only `windows[]` review records and may request field-scoped repairs.

Workers write only `packet._batch_output_path`, then provenance is recorded. A running worker emits a heartbeat. Retries receive the validator issue store and patch only named fields of the owning main-shot task. No other Agent role or phase may be dispatched.

For every packet returned by the supervisor, the host performs exactly this
sequence: spawn one worker, call `register_dispatch_agent.py`, record at least
one `record_dispatch_heartbeat.py` result while running, wait for a parseable
batch file, call `record_batch_provenance.py`, then resume the supervisor.

Before Editor Pass 2, the local `pre_editor_gate.py` writes one SHA-256-keyed
deterministic-plus-semantic audit artifact for the merged package. A
deterministic failure blocks dispatch; semantic findings are passed to Editor
for repair. Editor still performs Agent semantic review for every window:
`light` windows inspect the current shot plus carryover, while `high` windows
inspect the full bounded scene window. A light tier never waives an Agent pass,
final validation, or export QA.
