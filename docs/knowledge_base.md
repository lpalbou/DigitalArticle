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
- **Cell execution returns a structured lint report**:
  - Backend attaches `ExecutionResult.lint_report` (built-in, deterministic, offline) to support better debugging and self-correction.
  - Frontend surfaces this in `ExecutionDetailsModal` (“Lint” tab).
- **Safe autofix is default-on and must be transparent**:
  - API: `CellExecuteRequest.autofix` defaults to `true` and enables deterministic safe rewrites.
  - Backend returns `ExecutionResult.autofix_report` (before/after + diff) and persists the executed code to the cell (only when a rewrite actually occurs).
- **Clean rerun prevents downstream-state contamination**:
  - API: `CellExecuteRequest.clean_rerun` rebuilds the in-memory execution context from upstream cells only (ignores downstream globals).
  - Backend records details in `cell.metadata.execution.clean_rerun` and marks downstream cells **STALE** after a successful rerun.
- **Stdout DataFrame parsing must preserve leading whitespace**:
  - Pandas uses indentation for alignment (notably single-column headers). Avoid global `stdout.strip()` before parsing; it breaks detection.
  - See: `backend/app/services/execution_service.py::_parse_pandas_stdout`.
- **DataFrame “what changed in this execution” capture must consider object identity**:
  - Value-based `.equals()` alone misses “reassigned to a new DataFrame with identical values”.
  - State persistence can rehydrate prior notebook globals; identity checks prevent false “no changes” conclusions.
  - See: `backend/app/services/execution_service.py::_capture_tables`.

## Testing invariants (for reliability)

- **Test imports must not depend on the current working directory**:
  - Some environments / pytest import modes do not reliably place the repo root on `sys.path`.
  - `tests/conftest.py` ensures the repo root is on `sys.path` so `import backend.app.*` remains deterministic.

## Persistence invariants (current mismatch)

- **Workspace files** (uploads + user settings) use `Config.get_workspace_root()` (repo default: [`data/workspace`](../data/workspace)) via `DataManagerClean`.
- **Execution state snapshots** default to [`backend/notebook_workspace/`](../backend/notebook_workspace) via `StatePersistenceService`.
- This split is surprising and should be addressed (either unify under `WORKSPACE_DIR` or explicitly document and support both).

## Persona + review invariants

- Persona selection is stored in `notebook.metadata['personas']` and combined via `PersonaService.combine_personas()`.
- The `reviewer` persona exists as a system persona but is marked `is_active: false` (hidden from normal listing) while still used internally by `ReviewService` as a template source.

## DEPRECATED

- _None yet._

