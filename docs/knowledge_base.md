# Knowledge Base (critical insights and logics)

This file accumulates **non-obvious truths** about the system that we do not want to relearn. It is meant to reduce “documentation drift” and repeated debugging.

> **Rule:** critical insights are never deleted. If something becomes obsolete, move it to **DEPRECATED** with an explanation.

## Architecture invariants

- **Code is the source of truth**: docs must be grounded in [`backend/app/*`](../backend/app), [`frontend/src/*`](../frontend/src), [`docker/*`](../docker), and [`docker-compose.yml`](../docker-compose.yml).
- **Backend routers are mounted in [`backend/app/main.py`](../backend/app/main.py)**. If docs list endpoints, validate against that file.
- **Streaming uses SSE** for long-running tasks:
  - model download ([`backend/app/api/models.py`](../backend/app/api/models.py))
  - review streaming ([`backend/app/api/review.py`](../backend/app/api/review.py))
  - PDF/semantic export streaming ([`backend/app/api/notebooks.py`](../backend/app/api/notebooks.py))

## Configuration invariants (and pitfalls)

- **There are multiple config stores today**:
  - Project config: [`config.json`](../config.json) (read/write via [`backend/app/config.py`](../backend/app/config.py))
  - Per-user settings: `{WORKSPACE_DIR}/user_settings/{username}.json` ([`backend/app/services/user_settings_service.py`](../backend/app/services/user_settings_service.py))
  - Per-notebook fields: `Notebook.llm_provider` / `Notebook.llm_model` ([`backend/app/models/notebook.py`](../backend/app/models/notebook.py))
- **Provider/model vs base URLs are sourced differently** in the current implementation:
  - `LLMService` defaults provider/model from `Config` (ENV > [`config.json`](../config.json))
  - `_initialize_llm()` selects provider base URLs from per-user settings (fallback to env vars)
  - The Settings UI currently updates both stores to reduce drift ([`frontend/src/components/SettingsModal.tsx`](../frontend/src/components/SettingsModal.tsx))
- **Docker base-URL overrides** are applied at startup before services are initialized:
  - [`backend/app/services/shared.py`](../backend/app/services/shared.py) calls `UserSettingsService.apply_env_var_overrides()`

## Execution + retry invariants

- **Auto-retry max is 5** for execution failures (see `NotebookService.execute_cell()`).
- **Retry must use original generated code** as the fix target, not mutated retry variants (prevents compounding errors).
- **Execution runs in-process** (via `exec()`); production hardening requires sandboxing.

## Persistence invariants (current mismatch)

- **Workspace files** (uploads + user settings) use `Config.get_workspace_root()` (repo default: [`data/workspace`](../data/workspace)) via `DataManagerClean`.
- **Execution state snapshots** default to [`backend/notebook_workspace/`](../backend/notebook_workspace) via `StatePersistenceService`.
- This split is surprising and should be addressed (either unify under `WORKSPACE_DIR` or explicitly document and support both).

## Persona + review invariants

- Persona selection is stored in `notebook.metadata['personas']` and combined via `PersonaService.combine_personas()`.
- The `reviewer` persona exists as a system persona but is marked `is_active: false` (hidden from normal listing) while still used internally by `ReviewService` as a template source.

## DEPRECATED

- _None yet._

