# Backlog Item

## Title
Unify LLM configuration surfaces (provider/model/base URLs) into a single coherent precedence and storage model

## Backlog ID
0004

## Priority
- **P1**: configuration drift is a recurring correctness/UX issue and undermines traceability (ADR 0005) and reproducibility.

## Date / Time
2026-01-31T07:45:00 (local)

## Short Summary
Today the effective LLM configuration is derived from multiple stores: env vars, `config.json`, per-user settings JSON, and per-notebook fields. This creates drift and “settings saved but not applied” scenarios. We need a single coherent model with explicit precedence and minimal duplication.

## Key Goals
- Make provider/model/base URL resolution deterministic and explainable.
- Reduce configuration drift between UI settings, `config.json`, and runtime `LLMService`.
- Preserve Docker override behavior without surprising local workflows.

## Scope

### To do
- Inventory all current configuration reads/writes:
  - `backend/app/config.py`
  - `backend/app/services/user_settings_service.py`
  - `backend/app/services/llm_service.py`
  - `backend/app/api/settings.py` and `backend/app/api/llm.py`
  - `frontend/src/components/SettingsModal.tsx`
- Choose a unified precedence order and storage strategy.
- Implement migration plan (existing users’ settings must remain valid).

### NOT to do
- Do not remove Docker ENV overrides (must remain supported).
- Do not silently change effective provider/model without explicit UI feedback.

## Dependencies

### Backlog dependencies (ordering)
- Should follow: [`0003_fix_test_suite_regressions.md`](0003_fix_test_suite_regressions.md)

### ADR dependencies (must comply)
- **All ADRs are mandatory**: [`docs/adr/README.md`](../../adr/README.md)
- **Primary ADR dependencies**:
  - [`ADR 0002`](../../adr/0002-ab-testing-ladder.md)
  - [`ADR 0003`](../../adr/0003-truncation-compaction.md) (no truncation in ingest/query; explicit compaction rules)
  - [`ADR 0005`](../../adr/0005-perfect-observability.md) (config changes must be traceable/auditable)

### Points of vigilance (during execution)
- Avoid breaking Docker override behavior (`*_BASE_URL`, `LLM_PROVIDER`, `LLM_MODEL`).
- Avoid secrets leakage (API keys must stay masked and not logged).
- Ensure “what config was applied” is auditable (ties into observability).

## References (source of truth)
- `backend/app/config.py`
- `backend/app/services/user_settings_service.py`
- `backend/app/services/llm_service.py`
- `backend/app/api/settings.py`
- `backend/app/api/llm.py`
- `frontend/src/components/SettingsModal.tsx`

## Proposal (initial; invites deeper thought)

### Context / constraints
- `LLMService` currently loads provider/model from `Config` but base URLs from per-user settings.
- The UI currently updates both stores to compensate.

### Design options considered (with long-term consequences)
#### Option A: Make `config.json` the single source of truth for everything
- **Pros**: simple mental model; easy for headless deployments
- **Cons / side effects**: per-user settings (API keys, base URLs) becomes awkward; multi-user future blocked
- **Long-term consequences**: poor fit for multi-user; sensitive secrets in a shared file

#### Option B: Make per-user settings the single source of truth (recommended for future multi-user)
- **Pros**: supports per-user keys and endpoints; clear ownership; future multi-user-friendly
- **Cons / side effects**: need a “global default” story; local CLI workflows must remain easy
- **Long-term consequences**: cleaner path to auth and multi-user

#### Option C: Keep split but formalize it strictly (minimal change)
- **Pros**: minimal refactor
- **Cons / side effects**: drift remains; hard to reason about precedence; UI remains complex
- **Long-term consequences**: recurring bugs and documentation drift

### Recommended approach (current best choice)
Adopt per-user settings as the primary store for provider/model/base URLs and treat `config.json` as “boot defaults” only (with explicit precedence and migration).

### Testing plan (A/B/C)
> Follow `docs/adr/0002-ab-testing-ladder.md`.

- **A (mock / conceptual)**:
  - Document final precedence table and run through example scenarios (Docker, local, notebook override).
- **B (real code + real examples)**:
  - Ensure Settings UI changes immediately affect:
    - `/api/llm/status`
    - cell execution
    - review/chat
  - Validate persistence across backend restarts.
- **C (real-world / production-like)**:
  - Validate in:
    - 2-tiers container (external LLM)
    - 3-tiers compose (internal Ollama)
    - remote access scenario

## Acceptance Criteria (must be fully satisfied)
- A single documented precedence chain exists and matches implementation.
- No “settings saved but not applied” issues in standard flows.
- Existing installs migrate without losing settings or requiring manual edits.

## Implementation Notes (fill during execution)
TBD

## Full Report (fill only when moving to completed/)
TBD

