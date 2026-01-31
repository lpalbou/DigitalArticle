# Backlog Item

## Title
Rationalize repo root folders (`data/`, `assets/`, `examples/`) to reduce confusion (static vs runtime)

## Backlog ID
0065

## Priority
- **P2 (completed)**: clarity/packaging hygiene improvement.

## Date / Time
2026-01-31T09:35:00 (local)

## Short Summary
Cleaned up the repository root semantics by clarifying what `data/`, `assets/`, and `examples/` mean, and by moving doc-like content out of `assets/` so it remains media-only. This reduces “what is committed vs runtime?” confusion and improves doc discoverability.

## Key Goals
- Make folder intent obvious (source-of-truth vs runtime output).
- Improve packaging/deploy clarity (avoid ambiguity).
- Reduce perceived root “clutter” without breaking code paths.

## Scope

### To do
- Add clear READMEs for repo-root folders.
- Ensure `assets/` is media-only.
- Ensure `examples/` is clearly “examples”, not canonical docs.

### NOT to do
- Do not move runtime persistence roots (that work is tracked elsewhere).
- Do not move personas without updating backend logic.

## Dependencies

### Backlog dependencies (ordering)
- Related to: [`0005_unify_persistence_roots.md`](../planned/0005_unify_persistence_roots.md)

### ADR dependencies (must comply)
- **All ADRs are mandatory**: [`docs/adr/README.md`](../../adr/README.md)

### Points of vigilance (during execution)
- Avoid breaking any code paths that expect `data/personas/**` to exist.
- Keep doc links valid; run link validator.

## References (source of truth)
- `.gitignore` (runtime paths ignored)
- [`backend/app/services/persona_service.py`](../../../backend/app/services/persona_service.py) (personas loaded from `data/personas/**`)

## Full Report

### What changed (files/folders)

- Added:
  - `data/README.md`
  - `assets/README.md`
  - `examples/README.md`
- Moved:
  - `assets/semantic-models.md` → `docs/semantic_models.md`
- Updated:
  - `docs/overview.md` to link the new `docs/semantic_models.md`

### Design chosen and why

- Implemented **Option A** (clarify intent) immediately, because it provides the best benefit/risk ratio.
- Implemented the safe portion of **Option B** by moving a doc-like markdown file out of `assets/` into `docs/`.
- Deferred the larger structural split of `data/` into “versioned resources vs runtime roots” to the persistence unification work (to avoid two disruptive migrations).

### A/B/C test evidence

- **A**: Verified folder semantics and documentation are explicit via the new READMEs.
- **B**: Ran `python tools/validate_markdown_links.py` and confirmed all relative doc links resolve.
- **C**: Not applicable for this docs/layout hygiene change (no runtime behavior changed).

### ADR compliance notes

- No truncation/compaction behavior was introduced.
- No runtime behavior was changed; only file layout and documentation were adjusted.

### Risks and follow-ups

- Future follow-up (bigger change): split `data/` into versioned resources vs runtime roots as part of persistence unification (`0005_unify_persistence_roots.md`).

