# Backlog Item

## Title
Unify persistence roots (workspace files vs execution state snapshots)

## Backlog ID
0005

## Priority
- **P1**: a coherent persistence story is required for reliable backups, Docker volumes, and future publishing/provenance features.

## Date / Time
2026-01-31T07:45:00 (local)

## Short Summary
Workspace files (uploads, previews, user settings) are stored under `Config.get_workspace_root()` (default `data/workspace`), while execution state snapshots (pickle) default to `backend/notebook_workspace/`. This split is surprising and complicates backup/restore. Unify or explicitly parameterize these roots.

## Key Goals
- Make persistence locations predictable and configurable.
- Preserve backwards compatibility (existing state files should still load).
- Reduce operational burden for backups and Docker volumes.

## Scope

### To do
- Decide a canonical storage layout for:
  - uploads
  - per-user settings
  - execution state snapshots
- Implement path resolution that respects:
  - ENV overrides
  - `config.json` paths
  - Docker volume patterns
- Add migration and compatibility handling.

### NOT to do
- Do not introduce truncation in ingest/query paths (ADR 0003).
- Do not break existing notebooks/state snapshots without migration.

## Dependencies

### Backlog dependencies (ordering)
- Should follow: [`0003_fix_test_suite_regressions.md`](../completed/0003_fix_test_suite_regressions.md)
- Strongly related to: [`0004_unify_llm_config_surfaces.md`](0004_unify_llm_config_surfaces.md)

### ADR dependencies (must comply)
- **All ADRs are mandatory**: [`docs/adr/README.md`](../../adr/README.md)
- **Primary ADR dependencies**:
  - [`ADR 0002`](../../adr/0002-ab-testing-ladder.md)
  - [`ADR 0003`](../../adr/0003-truncation-compaction.md)
  - [`ADR 0005`](../../adr/0005-perfect-observability.md) (trace storage may live under the same persistence root)
  - [`ADR 0006`](../../adr/0006-publish-immutable-releases-doi-lineage.md) (publishing needs coherent persistence story)

### Points of vigilance (during execution)
- Backwards compatibility: legacy state snapshots must load or migrate transparently.
- Avoid data loss: no silent omission of artifacts; any omission must be explicit.
- Plan for future trace store + publish releases so the final layout doesn’t paint us into a corner.

## References (source of truth)
- `backend/app/config.py` (workspace root resolution)
- `docs/variable-state-persistence.md` (current documented split; must match code)
- `docs/architecture.md` (persistence map; must match implementation)

## Proposal (initial; invites deeper thought)

### Context / constraints
- State snapshots are critical for “resume after restart” UX.
- Operators need a single directory/volume to back up reliably.

### Design options considered (with long-term consequences)
#### Option A: Move state snapshots under `{WORKSPACE_DIR}` (likely best)
- **Pros**: single root; fits Docker volumes; simpler backup
- **Cons / side effects**: needs migration and fallback loading; must handle permissions and cleanup
- **Long-term consequences**: coherent operational story

#### Option B: Move uploads under `backend/notebook_workspace` (worse)
- **Pros**: fewer changes in state service
- **Cons / side effects**: mixes app code and data; complicates deployments
- **Long-term consequences**: brittle and confusing

### Recommended approach (current best choice)
Move state snapshots under `{WORKSPACE_DIR}` (or a new `STATE_DIR` derived from it), while supporting fallback reads from the legacy location.

### Testing plan (A/B/C)
> Follow `docs/adr/0002-ab-testing-ladder.md`.

- **A (mock / conceptual)**:
  - Define final directory layout and migration behavior.
- **B (real code + real examples)**:
  - Create notebook, execute cells, restart backend, confirm state loads.
  - Verify legacy state snapshots still load after upgrade.
- **C (real-world / production-like)**:
  - Validate in Docker (2-tiers + 3-tiers) with named volumes and restarts.

## Acceptance Criteria (must be fully satisfied)
- A single canonical persistence root is documented and implemented.
- State persists across restarts with no manual intervention.
- Legacy snapshots are still readable (or migrated automatically).

## Implementation Notes (fill during execution)
TBD

## Full Report (fill only when moving to completed/)
TBD

