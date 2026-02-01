# Changelog

All notable changes to the Digital Article project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.14] - 2026-02-01

### Fixed
- **Notebook-wide figure/table numbering + duplication**
  - Root cause: numbering was being inferred from execution-time counters and/or LLM-provided labels (often restarting at `1` per cell), which breaks ordering and creates duplicate `Figure N` / `Table N` labels across a notebook.
  - Fix: moved numbering to a deterministic notebook-wide pass (`NotebookAssetNumberingService`) that renumbers based on **cell order**, preserves descriptions, and de-duplicates obvious repeated plot payloads.
  - Applied on notebook load, post-execution (before methodology), and before save to keep UI + exports consistent.
- **Article view showed intermediate DataFrames / stdout-parsed tables**
  - Root cause: backend captures variable DataFrames (`source="variable"`) and stdout-parsed DataFrames (`source="stdout"`) for debugging, and the ResultPanel was rendering them in the main article output.
  - Fix: article view now renders **only** `source="display"` tables. Debug tables remain available via Execution Details.
  - PDF export now includes **only** `source="display"` tables as well.
- **Scientific PDF export leaked markdown headers + mis-captioned assets**
  - Root cause: LLM article sections sometimes included markdown headers (`# Introduction`, `## ...`), which were embedded verbatim into the PDF, duplicating section titles and showing raw `#` markers.
  - Fix: added a lightweight markdown renderer for PDFs (`PDFMarkdownRenderer`) that strips redundant section headers and renders internal headings cleanly.
  - Also fixed figure/table captions to prefer the notebook’s explicit `Figure N:` / `Table N:` labels (instead of variable names like `displayed_result`), eliminating mismatched numbering like `Figure 3. Figure 5: ...`.
  - Ensured Plotly interactive figures can be rendered in PDFs by adding `kaleido` to the root package dependencies (not just the backend package).
  - Fixed “black square” glyphs in PDFs by converting common Unicode punctuation/superscripts (e.g., `10¹¹`, en-dash, rho) to ASCII-safe equivalents during PDF text cleaning.
- **Executing cell highlight no longer pulsing**
  - Restored the slow `animate-pulse` emphasis for currently executing cells to make the active cell obvious during long runs.

### Added
- **Notebook asset numbering regression test**
  - Added pytest coverage to ensure numbering is sequential across the notebook, robust to per-cell label resets, and resilient to legacy plot formats.

## [0.3.2]

### Added
- **Linting governance + mandatory quality gates**
  - Added [`ADR 0008`](docs/adr/0008-linting-and-quality-gates.md): mandatory lint/typecheck/test gates per backlog completion.
  - Added recurrent gate [`0012_lint_and_typecheck_quality_gates.md`](docs/backlog/recurrent/0012_lint_and_typecheck_quality_gates.md) and wired it into the backlog workflow (`docs/backlog/template.md`, `docs/backlog/README.md`).
- **Lint report surfaced during cell execution**
  - Backend now attaches a structured `lint_report` to execution results.
  - Frontend Execution Details modal includes a dedicated “Lint” tab.
- **Safe auto-fix during execution is now default-on (deterministic, offline)**
  - Runs **before validation and before the first execution attempt** to fix “silly mistakes” without spending LLM budget.
  - Autofix remains disable-able via an explicit “Execute without safe auto-fix” debug action.
  - When applied, the backend returns a diff (`autofix_report.diff`) and persists the executed code.
- **Clean rerun (upstream-only context) to prevent downstream state contamination**
  - Adds `clean_rerun` execution mode: rebuilds execution context from upstream cells only (ignores downstream globals).
  - Downstream cells are invalidated (marked **STALE**) after a successful rerun.
- **Guided rerun (keep context + user comment) for partial rewrites**
  - Adds `rerun_comment` to cell execution so users can request targeted changes (“keep what you did, but change X”).
  - Rerun comments are persisted in cell metadata for provenance and injected into code generation + retry prompts.
  - Frontend adds a guided rerun modal accessed via the Re-run dropdown.
- **Delete cells (UI + robust backend invalidation)**
  - Added an X delete control per cell with confirmation modal.
  - Backend deletion now invalidates semantic caches, records an audit event, and marks downstream cells STALE.
- **Scope guard to reduce LLM over-initiative**
  - Code generation prompts now include an explicit “do only what was asked” scope guard.
  - Retry (auto-fix) prompts also include a scope guard to avoid adding extra work while fixing failures.
- **Expanded file uploads (images + medical imaging)**
  - Frontend upload picker now supports: **PNG/JPG/TIFF**, **DICOM** (`.dcm/.dicom`), and **NIfTI** (`.nii/.nii.gz`).
  - Backend adds a **download** endpoint for workspace files and avoids attempting inline preview for DICOM/NIfTI (download-only for now).
  - Upload persistence is now path-safe and uses streaming copy to reduce memory pressure on large files.

### Fixed
- **Restored green Python test suite (trust baseline)**
  - Fixed pandas `KeyError` enhancement classification (column vs index/value) and prevented logical-coherence enhancement from masking real exception types.
  - Restored stdout DataFrame parsing (`print(df)`) into structured tables and fixed single-column stdout parsing.
  - Made variable-table capture robust to DataFrame reassignment (object identity + value checks).
  - Stabilized test imports via `tests/conftest.py` (ensures repo root on `sys.path`).
- **Frontend lint + typecheck drift**
  - Added `frontend/.eslintrc.cjs` so `npm run lint` is enforceable.
  - Resolved accumulated unused imports/vars and hook dependency issues; `npm run lint` and `npm run build:check` are green.
- **Consistent markdown rendering for user-facing LLM outputs**
  - Unified Abstract + inline review feedback rendering via `frontend/src/components/MarkdownRenderer.tsx`.
- **Save button UX**
  - Top-right Save is now a split button: left click saves; right chevron opens export options.
- **TokenTracker log spam during LLM status polling**
  - Root cause: `/api/llm/status` polls `TokenTracker.get_current_context_tokens()` regularly; “no generations yet / no provider usage metadata” is a normal zero-state but was logged as a WARNING.
  - Fix: return `0` silently for the normal zero-state; keep warnings only for true internal inconsistencies.
  - Added a backend pytest to prevent warning-level regressions.
- **Cell deletion UI affordance**
  - Replaced the red “X” delete-cell control with a trash icon styled consistently with the copy icon (less visually noisy, clearer intent).
- **Plotly outputs no longer truncated in cells**
  - Root cause: interactive Plotly figures were forced into a fixed `600px` container and could be clipped inside rounded cards.
  - Fix: infer Plotly container height from `figure.layout.height` (preferred) or `layout.grid.rows` (subplots), falling back to a sane default.
- **Realtime cell execution status messaging**
  - Root cause: the UI showed a single “Generating and executing…” message, but backend execution is a multi-step pipeline (context build, LLM calls, retries, methodology, post-processing).
  - Fix: backend now tracks `execution_phase` + `execution_message` in `cell.metadata["execution"]` and exposes it via `/api/cells/{cell_id}/status`; frontend polls this while `/cells/execute` is in-flight and renders the live message.
- **Figures always fit cell width (no horizontal overflow)**
  - Root cause: some Plotly figures included a fixed `layout.width`, causing the graph to exceed the cell width and be clipped by rounded containers.
  - Fix: frontend strips `layout.width` for interactive Plotly outputs and relies on autosizing/responsive sizing to fit the cell.
  - Also removed hard `max-h` constraints for static images so cells grow vertically with content while keeping width constrained.

### Changed
- **Documentation overhaul to eliminate “truth drift”**
  - Updated `README.md` and `docs/getting-started.md` to reflect the current packaging/config reality (pyproject-based installs, config surfaces, current Docker options).
  - Rebuilt `docs/architecture.md` with a canonical, code-grounded section + mermaid diagrams + links to component dive-ins.
  - Added a navigable documentation graph:
    - `docs/overview.md` (doc index)
    - `docs/data_flow.md` (key call graphs)
    - `docs/knowledge_base.md` (critical non-obvious insights; deprecated items tracked, never deleted)
    - `docs/troubleshooting.md` (common failures)
    - `docs/dive_ins/*` (critical component docs)
  - Marked historical planning/devnote docs explicitly as such to avoid misleading readers.


## [0.3.13] - 2025-12-17

### Fixed
- **Execution Details Button Missing After Async Changes**
  - Root cause: AbstractCore's `agenerate()` didn't capture traces like sync `generate()` did
  - Button only showed when `cell.llm_traces.length > 0`, which was always empty with async
  - Fix 1: Button now shows when `execution_count > 0` OR traces exist
  - Fix 2: AbstractCore 2.6.8 adds trace capture to `agenerate()` for all providers
  - Files: `frontend/src/components/PromptEditor.tsx`

### Changed
- **Dependency Update: AbstractCore 2.6.8**
  - Includes fix for async generation tracing
  - Required for Execution Details button to show trace data


## [0.3.12] - 2025-12-17

### Fixed

- **Figure Display: Images Now Fit Within Cell Containers**
  - Root cause: Images had `max-w-full h-auto` CSS which only constrained width, not height
  - Tall figures (like multi-panel dashboards) exceeded viewport height and got clipped by `overflow-hidden`
  - Fix: Added `max-h-[80vh] object-contain` to all `<img>` elements
  - Images now constrained to 80% viewport height while maintaining aspect ratio
  - Files: `frontend/src/components/ResultPanel.tsx`

### Changed

- **Dependency Update: AbstractCore 2.6.8**
  - Updated abstractcore dependency from `>=2.6.2` to `>=2.6.8`
  - Includes latest provider fixes and improvements
  - Files: `backend/pyproject.toml`, `pyproject.toml`


## [0.3.11] - 2025-12-17

### Fixed

- **Chat Panel 400 Error on Remote Deployment**
  - Root cause: Frontend sends `id` and `loading` fields in ChatMessage that backend Pydantic model didn't expect
  - Pydantic V2 rejected extra fields with HTTP 400 error
  - Fix: Added `id: Optional[str]` and `loading: Optional[bool]` to ChatMessage model
  - Files: `backend/app/api/chat.py`

- **Docker ENV Variables Not Applied at Startup**
  - Root cause: Persisted `user_settings.json` from previous runs overrode Docker ENV vars
  - LLMService initialized with stale localhost URLs instead of Docker-provided URLs
  - Fix: Added `apply_env_var_overrides()` called at startup BEFORE LLMService initialization
  - Docker-provided base URLs (non-localhost) now take priority over saved settings
  - Files: `backend/app/services/user_settings_service.py`, `backend/app/services/shared.py`

- **LLMService Reinitialization on Settings Change**
  - When user changes base URLs in Settings UI, LLMService now reinitializes
  - Ensures chat/review/cell execution use updated URLs immediately
  - Files: `backend/app/api/settings.py`


## [0.3.10] - 2025-12-12

### Fixed

- **Figure Duplication Bug: Plotly Figures Re-captured Across Cells**
  - Root cause: `_capture_interactive_plots()` captured ALL Plotly figures in globals_dict
  - Figures from previous cells persisted in namespace and were re-captured
  - Fix: Track pre-execution Plotly figures by name AND object ID (memory address)
  - Only captures NEW figures: new variable names OR existing names reassigned to new objects
  - Same pattern as DataFrame tracking (pre_execution_vars, pre_execution_dataframes)
  - Files: `backend/app/services/execution_service.py`


## [0.3.9] - 2025-12-11

### Fixed

- **Abstract Generation: Complete Data Access**
  - Removed truncation that limited code to 200 chars, output to 300 chars, methodology to 400 chars
  - Abstract now receives full cell prompts, code, stdout, and scientific explanations
  - Added table metadata + 20-row preview (same format as cell code generation)
  - Added interactive plot metadata (titles, axes labels, trace types)
  - Added static plot labels and warnings
  - Files: `llm_service.py`, `notebook_service.py`


## [0.3.8] - 2025-12-11


## [0.3.7] - 2025-12-11

### Added

- **📁 Enhanced LLM File Context**
  - LLM now receives full metadata + sample data (20 rows) for uploaded files
  - Rich column analysis: semantic types, missing values, ranges, categorical distributions
  - Data dictionaries auto-detected and sent in full (no truncation)
  - Full content sent for txt, md, json, yaml files
  - JSON minified before sending to LLM (~40% token savings)
  - Large file warning modal (>25k tokens) with user confirmation
  - Files: `data_manager_clean.py`, `llm_service.py`, `FileContextPanel.tsx`

- **📊 Reviewer: Data Quality Assessment**
  - New first dimension in peer review: Provenance, Quality, Quantity, Appropriateness
  - Reviewer evaluates only what is explicitly stated in the article
  - Default persona changed from Generic to Clinical

- **📝 Unified Markdown Renderer**
  - New `MarkdownRenderer` component for consistent markdown across all panels
  - Syntax highlighting for code blocks via highlight.js
  - Copy button on code blocks
  - Three variants: default, compact (chat), inverted (user bubbles)
  - Files: `frontend/src/components/MarkdownRenderer.tsx`, `frontend/src/index.css`

### Changed

- **🐳 Docker: 2-Tiers as Default, OpenAI-Compatible Provider**
  - **Root Dockerfile**: Now uses 2-tiers configuration (lightweight, external LLM)
  - **Default Provider**: Changed from `ollama` to `openai-compatible`
  - **Default URL**: `http://host.docker.internal:1234/v1` (LMStudio default port)
  - **Build Fix**: Added `cmake make swig zlib1g-dev` + CFLAGS for GCC 14 compatibility with tellurium
  - **New 2-tiers variant**: `docker/2-tiers/` - Frontend + Backend only (~500MB vs ~2GB)
  - Files: `Dockerfile`, `docker/2-tiers/*`, `docker/monolithic/Dockerfile`,
    `docker/monolithic/Dockerfile.nvidia`, `docker/README.md`

### How to Configure

```bash
# Build-time (baked into image)
docker build --build-arg OPENAI_COMPATIBLE_BASE_URL=http://myserver:8080/v1 .

# Run-time (override at startup)
docker run -e OPENAI_COMPATIBLE_BASE_URL=http://host.docker.internal:8080/v1 ...
```


## [0.3.6] - 2025-12-11

### Added

- **🚀 vLLM and OpenAI-Compatible Provider Support**
  - **Upgrade**: AbstractCore dependency upgraded from 2.6.2 to 2.6.5
  - **vLLM Provider**: High-throughput GPU inference support for NVIDIA CUDA hardware
    - Default base URL: `http://localhost:8000/v1`
    - Environment variable: `VLLM_BASE_URL`
    - Optional API key via `VLLM_API_KEY`
    - Features: Guided decoding, Multi-LoRA adapters, beam search
  - **OpenAI-Compatible Provider**: Generic provider for any OpenAI-compatible API endpoint
    - Supports: llama.cpp, text-generation-webui, LocalAI, FastChat, Aphrodite, SGLang, custom proxies
    - Default base URL: `http://localhost:8080/v1`
    - Environment variable: `OPENAI_COMPATIBLE_BASE_URL`
    - Optional API key via `OPENAI_COMPATIBLE_API_KEY`
  - **Settings UI**: Both providers now configurable in Advanced Settings
    - Custom base URLs for vLLM and OpenAI-compatible endpoints
    - "Update" button to test connection and refresh model list (same as Ollama/LMStudio)
  - **Docker Support**: New environment variables documented for container deployments
  - **Docker Support**: Updated all Dockerfiles with new build ARGs and ENV variables
  - Files: `pyproject.toml`, `backend/app/config.py`, `backend/app/services/llm_service.py`,
    `backend/app/services/user_settings_service.py`, `backend/app/api/llm.py`,
    `frontend/src/components/SettingsModal.tsx`, `Dockerfile`, `docker-compose.yml`,
    `docker/monolithic/Dockerfile`, `docker/monolithic/Dockerfile.nvidia`, `docker/README.md`,
    `docker/monolithic/README.md`


## [0.3.5] - 2025-12-08

### Fixed

- **🛡️ CRITICAL: Robust Error Analysis & Table Metadata Extraction**
  - **Problem**: Three interconnected issues prevented effective auto-retry:
    1. **Error analyzer false positive**: Claimed pandas `.loc` indexer was a missing column name → "Column 'loc' doesn't exist" misleading error
    2. **Table shape extraction silent failure**: Console showed `[1 rows x 11 columns]` but insights extracted `Shape: 0 rows × 0 columns` → methodology LLM couldn't describe actual table structure
    3. **LLM oscillated between errors**: Same error repeated across all 5 retries because analyzer provided wrong diagnosis
  - **Impact**: Auto-retry mechanism failed repeatedly because error analysis was inaccurate. LLM wasted retry attempts trying to "fix" non-existent problems.
  - **Fix - Three General-Purpose Robust Solutions**:
    1. **Exclude pandas methods from column detection** (error_analyzer.py:313-334): Added comprehensive `false_positives` set including `.loc`, `.iloc`, `.at`, `.iat`, aggregation methods, and export methods. Now correctly identifies these as methods, not column names.
    2. **Robust table shape validation** (execution_service.py:1637-1671): Extract shape BEFORE serialization, add fallback serialization strategies, log validation warnings when shape doesn't match data. Shape is now preserved even if serialization fails.
    3. **Enhanced KeyError analysis** (error_analyzer.py:1029-1043): Already implemented - shows actual available DataFrame columns from context when column errors occur, helping LLM adapt to actual data structure.
  - **Result**:
    - Error analyzer no longer claims `.loc` is a missing column
    - Table shape correctly shows `1 rows × 11 columns` instead of `0 rows × 0 columns`
    - LLM receives accurate error messages with actual available columns
    - Auto-retry success rate dramatically improved
  - Files: `backend/app/services/error_analyzer.py`, `backend/app/services/execution_service.py`

- **📝 CRITICAL: Robust Methodology Generation - Never Fails**
  - **Problem**: When DataFrames had numeric column names (or column data was mistakenly extracted), methodology generation crashed with `TypeError: sequence item 0: expected str instance, int found`. The system retried 3 times and gave up, leaving cells **without methodology text** - breaking the publication-ready article output.
  - **Impact**: Cells executed successfully but had empty methodology sections. This is **unacceptable** for publication-ready articles.
  - **Fix - Three-Layer Defense**:
    1. **Robust Formatting**: Wrapped ALL formatting operations in defensive try-except blocks (execution_insights_extractor.py:280-409)
       - Convert all values to strings: `col_strs = [str(c) if c is not None else 'None' for c in cols]`
       - Per-table error handling: malformed tables don't break other sections
       - Guaranteed return: Always returns a string, even if empty
    2. **Fallback Methodology**: If LLM generation fails 3 times, generate basic methodology from execution data (notebook_service.py:1330-1363)
       - Includes: Analysis request, execution status, table count, plot count
       - Example: "**Analysis Request**: create dashboard **Execution**: Analysis completed successfully. **Output**: Generated 1 table. **Visualizations**: Created 7 figures."
    3. **Absolute Last Resort**: If even fallback fails, use minimal text: "Analysis completed successfully."
  - **Result**: Methodology section **NEVER empty** - always provides publication context, even if LLM fails.
  - **Philosophy**: It's better to have basic methodology than none. The article remains publication-ready in all scenarios.
  - Files: `backend/app/services/execution_insights_extractor.py`, `backend/app/services/notebook_service.py`

- **🔄 CRITICAL: Re-run Retry Counter Reset**
  - **Problem**: When a cell failed all 5 retry attempts, then user clicked re-run/regenerate, no new retries would happen because `retry_count` was still at 5 from the previous execution.
  - **Impact**: Users had to manually edit code after exhausting retries, defeating the purpose of auto-retry on re-run.
  - **Fix**: Reset `retry_count = 0` at the start of every cell execution (line 811 in notebook_service.py), ensuring fresh retry attempts for re-runs.
  - **Result**: Re-running a failed cell now gets a full 5 retry attempts, whether using normal re-run or regenerate.
  - Files: `backend/app/services/notebook_service.py`

- **📊 Unwanted 3D Visualizations in Dashboards**
  - **Problem**: When users requested "SOTA dashboard", the LLM automatically added 3D scatter plots without being asked. System prompt Example 3 showed 3D Plotly visualization, which LLM interpreted as "professional" dashboard visualization technique.
  - **Impact**: Dashboards included unwanted 3D UMAP/scatter plots that cluttered the output and weren't requested.
  - **Fix**: Replaced Example 3 with simple 2D Plotly scatter plot and added guidance "(2D - only use 3D if explicitly requested)".
  - **Result**: LLM now defaults to 2D visualizations for dashboards and only uses 3D when user explicitly requests multi-dimensional/3D plots.
  - Files: `backend/app/services/llm_service.py` (lines 367-372)

- **🎯 CRITICAL: Enhanced Error Traceback with Actual Code Lines**
  - **Problem**: When code execution failed, the traceback showed `File "<string>", line 37` without the actual code on that line. The LLM saw references to internal Digital Article code (`execution_service.py`) and library internals that it has no access to, but couldn't see its own generated code that caused the error.
  - **Impact**: LLM failed all 5 auto-retry attempts because it couldn't identify what needed to be fixed. Even clear error messages like "probabilities do not sum to 1" were useless when the LLM couldn't see the line with `p=[0.5, 0.4]`.
  - **Fix**: Traceback now includes the actual code from referenced lines:
    ```
    File "<string>", line 37, in <module>
    >>> 37:     response.append(np.random.choice(['CR', 'PR'], p=[0.5, 0.4]))
    ValueError: probabilities do not sum to 1
    ```
  - **Result**: LLM can now see its own code and self-correct errors effectively during auto-retry. This is a **general-purpose fix** that works for ALL errors, not just specific cases.
  - Files: `backend/app/services/llm_service.py` (added `_enhance_traceback_with_code()` method)

- **🔍 CRITICAL: Traceback Context for Multi-line Expressions**
  - **Problem**: When errors occurred in multi-line dict/list literals with f-string expressions, Python reports the error at the closing bracket (`}`, `]`, `)`). The enhanced traceback showed `>>> 19: }` which was USELESS - the LLM couldn't see the actual f-string expression that failed (which was several lines above). This caused all 5 retry attempts to fail with the same error.
  - **Impact**: LLM saw only `}` and had NO IDEA what the actual problem was. Example: `results_df.loc[...].values[0]` in an f-string on line 15 failed, but traceback only showed `>>> 19: }`.
  - **Fix**: When the error line is just a closing bracket, show 5 lines of context before it to reveal the actual expression:
    ```
    File "<string>", line 19, in <module>
    >>> Context around line 19 (error in multi-line expression):
        14:     "Model Type": "Supervised Classification",
        15:     "Performance (Mean Accuracy)": f"{results_df.loc[...].values[0]:.3f}",
        ...
    >>> 19: }
    IndexError: index 0 is out of bounds for axis 0 with size 0
    ```
  - **Result**: LLM can now SEE the actual f-string expression that caused the error and fix it during retry. This fix handles a Python language quirk where errors in multi-line expressions are reported at the wrong line.
  - Files: `backend/app/services/llm_service.py` (enhanced `_enhance_traceback_with_code()` method)

- **📚 CRITICAL: Methodology Generation Accuracy & Code Output Alignment**
  - **Problem**: Two interconnected issues prevented accurate methodology generation:
    1. **Statistical findings lost context**: Regex extraction showed just `accuracy: 0.700` without model names → methodology LLM had to GUESS which model → claimed "Random Forest achieved 70%" when it was actually 60%!
    2. **Code didn't display PRIMARY results**: When user asked for cross-validation, code only displayed feature importance (secondary result), not validation metrics (primary result user asked for)
    3. **Console output not included**: Methodology LLM never saw the full stdout with `Logistic Regression: Mean Accuracy = 0.700` → couldn't verify claims
  - **Impact**: Methodology sections contained **factually incorrect claims** about results. Code displayed wrong output. Critical for scientific accuracy!
  - **Fix - Four-Part Solution**:
    1. **Include raw console output in methodology prompt** (llm_service.py:1250-1253): Methodology LLM now sees FULL stdout with model names attached to metrics
    2. **Enhance statistical findings with context** (execution_insights_extractor.py:372-390): Shows "Mean Accuracy = 0.700 (+/- 0.322)" instead of just "accuracy: 0.700"
    3. **Add verification guidance** (llm_service.py:1212-1214): Tells methodology LLM to use EXACT values from output, never invent/guess
    4. **Add PRIMARY RESULT guidance** (llm_service.py:374-394, 402): Tells code generation to display main results FIRST with Example 4 showing cross-validation table before feature importance
  - **Result**:
    - Methodology now reports CORRECT values: "Logistic Regression and SVM achieved 70%, Random Forest achieved 60%"
    - Code now displays what user asked for (cross-validation results) first, secondary results (feature importance) second
    - Methodology claims are verified against actual console output
  - Files: `backend/app/services/llm_service.py`, `backend/app/services/execution_insights_extractor.py`

## [0.3.3] - 2025-12-08

### Fixed

- **🔧 Anti-Pattern Validation**: Fixed false positives blocking valid pandas code
  - Fixed regex to use word boundaries preventing substring matches
  - `summary_stats.columns = [...]` no longer incorrectly flagged
  - Comprehensive test suite added to prevent regression
  - Files: `backend/app/services/execution_service.py`, `backend/tests/validation/test_antipattern_false_positives.py`

- **🔄 Auto-Retry on Regenerate**: Fixed auto-retry mechanism not working when force_regenerate=True
  - Removed blocking condition preventing retries on regenerated code
  - Regenerated code that fails now gets full 5 retry attempts
  - Files: `backend/app/services/notebook_service.py`

### Enhanced

- **📊 M&S Persona Tuning**: Enhanced Modeling & Simulation persona with modern SciPy API guidance
  - Added critical constraint for trapezoid vs deprecated trapz
  - Three-layer defense: persona guidance + error analyzer + system prompt
  - Files: `data/personas/system/modeling-simulation.json`, `backend/app/services/error_analyzer.py`, `backend/app/services/llm_service.py`

- **📈 Interactive Visualization**: Improved LLM guidance for interactive 3D visualizations
  - Added explicit Plotly 3D example with proper usage
  - Common mistakes section clarifying matplotlib vs Plotly for interactive plots
  - UMAP import error handler added to error analyzer
  - Files: `backend/app/services/llm_service.py`, `backend/app/services/error_analyzer.py`

- **🔍 Critical Reviewer**: Enhanced article reviewer to be appropriately stringent
  - Principle-based critical thinking guidance vs prescriptive rules
  - Emphasis on data quality and scientific rigor
  - Appropriate skepticism for synthetic/test data vs real research
  - Files: `backend/app/services/review_service.py`

- **🔬 Semantic Extraction & Caching**: Improved semantic graph extraction with LLM-based analysis
  - Smart caching of semantic extraction results
  - Rich provenance tracking across cells
  - Progress modal for extraction feedback
  - Files: `backend/app/services/semantic_analysis_service.py`, `backend/app/services/llm_semantic_extractor.py`, `frontend/src/components/SemanticExtractionModal.tsx`

- **⚡ Async Progress Feedback**: Real-time modal feedback for long-running operations
  - Progress modals for PDF export, semantic extraction
  - Stage-based progress indicators
  - Files: `frontend/src/components/PDFExportModal.tsx`, `frontend/src/components/SemanticExtractionModal.tsx`

### Technical Details

**Ongoing Work - Logical Retry System**:
- Foundation laid for enhanced retry logic with better context passing
- LLM now receives full execution context during retries (available variables, DataFrames, previous cells)
- Error analyzer enhanced to show actual available data vs generic guidance
- Future enhancements planned for domain-specific retry strategies

## [0.3.1] - 2025-12-05

### Added

- **🗑️ Ollama Model Deletion**: Delete models to free disk space
  - Trash icon in model dropdown for Ollama models
  - Confirmation dialog before deletion
  - Refreshes model list after deletion
  - Toast notifications for success/error

### Fixed

- **💾 Model Selection Persistence**: Settings now persist across notebooks
  - Fixed: New notebook creation now reads from user settings (`/api/settings`)
  - Previously: Used global config which didn't persist user preferences
  - Model selection now persists across new notebooks, page refresh, and browser sessions

- **🔧 httpx DELETE API Fix**: Fixed model deletion endpoint
  - Changed from `client.delete(json=...)` to `client.request("DELETE", json=...)`
  - Resolves: "AsyncClient.delete() got an unexpected keyword argument"


## [0.3.0] - 2025-12-05

### Fixed

- **🔧 Docker Deployment**: Fixed missing personas in Docker containers
  - Added `COPY data/personas/system/` to all 4 Dockerfiles (monolithic, NVIDIA, 3-tier backend, root)
  - Added `libgomp1` runtime dependency for llama-cpp-python (AbstractCore HuggingFace provider)
  - Personas now properly included in Docker images, available in Settings UI
  - Backend no longer crashes with "libgomp.so.1: cannot open shared object file" error

- **🌐 Base URL Settings**: Fixed Ollama/LMStudio base URL not applied to LLM calls
  - LLM service now loads saved base URLs from `user_settings.json`
  - Priority: saved settings > environment variable > default
  - Provider discovery and LLM calls now use consistent base URL configuration
  - Docker deployments can still override via environment variables

- **📦 Docker Registry**: Switched 3-tier backend to AWS ECR Public
  - Eliminated Docker Hub rate limit warnings for Python base images
  - Consistent with monolithic Dockerfile (all use AWS ECR except Ollama)

### Changed

- **🎨 PDF Export**: Enhanced with Plotly figure support (from 0.2.5)
  - Added `kaleido==0.2.1` for Plotly → PNG conversion
  - Scientific PDFs now include all interactive visualizations as high-quality static images


## [0.2.5] - 2025-12-04

### Added

- **🎭 Persona System**: Domain-expert personas that shape article generation
  - **5 Built-in Personas**: Generic, Clinical, Genomics, RWD (Real-World Data), Medical Imaging
  - **Per-Notebook Selection**: Each notebook can have its own persona (stored in notebook metadata)
  - **Domain-Specific Guidance**: Personas inject expertise into code generation, methodology writing, and terminology
  - **Custom Personas**: Users can create and manage their own domain-specific personas
  - **Scope-Aware Prompts**: Different guidance for code generation, methodology, chat, abstract, and review
  - Files: `backend/app/models/persona.py`, `backend/app/services/persona_service.py`, `backend/app/api/personas.py`
  - UI: `PersonaTab.tsx`, `PersonaCard.tsx`, `PersonaEditor.tsx`

- **📝 Article Review System**: Automated peer-review quality control
  - **Dimensional Assessment**: Structured evaluation across 5 scientific dimensions
    - Research Question (relevance, clarity, scope)
    - Methodology (appropriateness, implementation, statistical rigor)
    - Results (accuracy, completeness, presentation)
    - Reproducibility (documentation, data access, code quality)
    - Communication (structure, language, visualization)
  - **3-Phase Review**: Intent review, Implementation review, Results review
  - **Severity Levels**: Info, Warning, Critical findings with actionable suggestions
  - **Article-Level Synthesis**: Overall assessment with key strengths and areas for improvement
  - Files: `backend/app/models/review.py`, `backend/app/services/review_service.py`, `backend/app/api/review.py`
  - UI: `ArticleReviewModal.tsx`, `ReviewPanel.tsx`, `ReviewSettingsTab.tsx`

- **📖 Architecture Documentation**: Comprehensive documentation of the Persona and Review systems
  - File: `docs/persona-and-review-architecture.md`

### Changed

- **💬 Enhanced Chat Service**: Chat now supports mode-based operation (standard, review)
- **⚙️ Settings Modal**: New tabs for Persona selection and Review configuration
- **🔧 LLM Service**: Enhanced to support persona context injection

## [0.2.3] - 2025-12-02

### Changed

- **🔧 Centralized Version Management**: Single source of truth (`digitalarticle/_version.py`)
  - Backend imports version directly; Docker copies `digitalarticle/` folder
  - Frontend footer fetches version from `/api/system/version` endpoint
  - No more hardcoded versions across codebase


## [0.2.2] - 2025-11-27

### Added

- **🔧 Multi-Provider Docker Support**: Environment variable-driven LLM configuration for all AbstractCore providers
  - **Provider Selection**: `LLM_PROVIDER` env var supports `ollama`, `openai`, `anthropic`, `lmstudio`, `huggingface`
  - **Model Configuration**: `LLM_MODEL` env var to specify model name for any provider
  - **API Key Support**: `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `HUGGINGFACE_TOKEN` env vars for external providers
  - **Smart Startup**: Ollama server only starts when `LLM_PROVIDER=ollama`, saving resources for external providers
  - Files: `docker/monolithic/entrypoint.sh`, `docker/monolithic/supervisord.conf`, `docker/monolithic/Dockerfile`, `docker/monolithic/Dockerfile.nvidia`

### Enhanced

- **⚙️ Configuration Priority**: ENV > config.json > defaults (follows Docker/12-Factor conventions)
  - **Environment First**: Environment variables take precedence for container deployments
  - **Config File Second**: `config.json` used for local development when env vars not set
  - **Sensible Defaults**: Built-in defaults (`ollama`/`gemma3n:e2b`) when neither env nor config specified
  - Files: `backend/app/config.py`

- **📁 Local Development Paths**: Updated `config.json` to use relative paths for local development
  - **Before**: `/app/data/notebooks` (Docker absolute paths)
  - **After**: `data/notebooks` (relative paths for local dev)
  - **Rationale**: `config.json` is for local development; Docker uses env vars
  - Files: `config.json`

- **📖 Docker Documentation**: Comprehensive provider configuration documentation
  - **Provider Examples**: Usage examples for all supported providers (OpenAI, Anthropic, LMStudio, HuggingFace)
  - **Environment Reference**: Complete table of all configuration environment variables
  - **External Ollama**: Updated docs for using native Ollama on host machine
  - Files: `docker/monolithic/README.md`, `docker/README.md`

### Technical Details

**Configuration Priority Chain**:
```
1. Environment variables (LLM_PROVIDER, LLM_MODEL, etc.)
2. config.json file 
3. Built-in defaults (ollama, gemma3n:e2b)
```

**Provider-Aware Startup**:
- If `LLM_PROVIDER=ollama`: Start Ollama, wait for health, pull model
- If `LLM_PROVIDER=openai|anthropic|lmstudio|huggingface`: Skip Ollama entirely

**Example Usage**:
```bash
# OpenAI (no Ollama started)
docker run -p 80:80 \
    -e LLM_PROVIDER=openai \
    -e LLM_MODEL=gpt-4o \
    -e OPENAI_API_KEY=sk-... \
    digital-article:unified

# Ollama (default, with bundled server)
docker run -p 80:80 \
    -e LLM_MODEL=llama3.2:7b \
    digital-article:unified
```

## [0.2.1] - 2025-11-25

### Added

- **🐳 Unified Docker Image**: Single-container deployment consolidating all services
  - **All-in-One Container**: Backend (FastAPI) + Frontend (Nginx) + Ollama (LLM) in one image
  - **Supervisord Process Management**: Coordinated multi-service startup with health checks
  - **Smart Model Caching**: Models downloaded once at first run, persisted in named volume for subsequent starts
  - **Configurable Paths**: Environment variables override config.json for notebooks, workspace, and model storage
  - **Official Ollama Binary**: Uses binary from `ollama/ollama:latest` official Docker image for reliability
  - **Orchestrated Startup**: 9-step entrypoint sequence ensures services start in correct order with health verification
  - **Simplified Deployment**: Single `docker run` command vs 3-service docker-compose
  - **Production Ready**: Complete with health checks, resource limits, and comprehensive logging
  - Files: `docker/Dockerfile.unified`, `docker/entrypoint-unified.sh`, `docker/supervisord.conf`, `docker/nginx-unified.conf`

- **📦 Dual Deployment Options**: Flexibility to choose between unified or multi-container setup
  - **Unified Image** (recommended): Simplified deployment for most use cases with `digitalarticle:unified`
  - **Multi-Container**: Original 3-service architecture still available for advanced scenarios
  - **Named Volumes**: Both strategies use persistent volumes for notebooks and models
  - **Comprehensive Guides**: Separate documentation for each deployment approach
  - Files: `docker/monolithic/README.md`, `docker/3-tiers/README.md`

- **⚙️ Backend Path Configuration**: Dynamic path configuration with ENV > config.json > default cascade
  - **Configurable Notebooks Directory**: `NOTEBOOKS_DIR` env var or `paths.notebooks_dir` in config.json
  - **Configurable Workspace Root**: `WORKSPACE_DIR` env var or `paths.workspace_dir` in config.json
  - **Programmatic API**: `config.get_notebooks_dir()`, `config.get_workspace_root()`, `config.set_paths()`
  - **Docker Integration**: Backend automatically uses paths from environment variables in containers
  - Files: `backend/app/config.py`, `backend/app/services/shared.py`, `backend/app/services/data_manager_clean.py`

### Enhanced

- **📖 Comprehensive Deployment Documentation**
  - **Main Docs**: `docker/README.md` - Overview and decision tree
  - **Monolithic Guide**: `docker/monolithic/README.md` - Single container deployment
  - **3-Tier Guide**: `docker/3-tiers/README.md` - Multi-container deployment
  - **Technical Report**: `docs/devnotes/docker-one-image.md` - Implementation details

### Technical Details

**Unified Container Architecture**:
- **Multi-stage Build**: Frontend (Node 20 Alpine) → Backend (Python 3.12 Slim) → Runtime
- **Process Management**: Supervisord coordinates 3 services (Ollama priority 10, Backend priority 20, Nginx priority 30)
- **Service Communication**: Localhost networking (nginx → backend:8000, backend → ollama:11434)
- **Volume Strategy**: Two named volumes (notebooks/workspace data, Ollama models)
- **Startup Sequence**:
  1. Initialize directories from ENV vars
  2. Start supervisord
  3. Wait for Ollama readiness (30 retries × 2s)
  4. Check/download model (skip if cached in volume)
  5. Start backend via supervisorctl
  6. Wait for backend health (30 retries × 2s)
  7. Start nginx
  8. Display configuration summary
  9. Hand off to supervisord foreground mode

**Image Size & Performance**:
- **Base Image**: ~2.3-2.5GB (no models included)
- **First Startup**: 10-30 minutes (model download)
- **Subsequent Startups**: 90-120 seconds (models cached)
- **Resource Requirements**: 8GB RAM minimum, 32GB+ recommended for 30B models

**Deployment Comparison**:
```
Multi-Container (0.2.0):
  docker-compose up -d  # 3 containers

Unified Image (0.2.1):
  docker run -d -p 80:80 \
    -v digitalarticle-data:/app/data \
    -v digitalarticle-models:/models \
    digitalarticle:unified
```

## [0.2.0] - 2025-11-21

### Added

- **🐳 Docker Containerization**: Complete production-ready Docker deployment with 3-service architecture
  - **Backend Container**: FastAPI application with automatic health checks and fail-safe startup
  - **Frontend Container**: Nginx-served React application with optimized production build
  - **Ollama Container**: Dedicated LLM service with automatic model download and GPU support
  - **Named Volumes**: Zero-setup deployment with automatic directory creation for notebooks, data, and logs
  - **Resource Management**: Configurable memory limits and CPU allocation for each service
  - **Comprehensive Documentation**: 593-line deployment guide covering all scenarios from quick test to production
  - Files: `docker/Dockerfile.backend`, `docker/Dockerfile.frontend`, `docker-compose.yml`, `docker-compose.dev.yml`, `docker/entrypoint.sh`, `docker/ollama-entrypoint.sh`, `docker/nginx.conf`, `docker/README.md`

- **🚀 Automatic Model Setup**: Intelligent model management with zero manual intervention
  - **Config-Driven**: Reads model name from `config.json` for consistent deployment
  - **Automatic Download**: Ollama container downloads models during startup if not present
  - **Health Checks**: Extended health check periods (40 minutes) to accommodate large model downloads
  - **Graceful Startup**: Backend waits for Ollama to be ready before serving requests
  - **Progress Tracking**: Model download progress visible in container logs
  - Files: `docker/ollama-entrypoint.sh`, `docker/entrypoint.sh`, `config.json`

- **📦 Dependency Management**: Unified dependency management using `pyproject.toml` as single source of truth
  - **SOTA Best Practice**: Eliminated duplicate dependency definitions in `requirements.txt`
  - **Consistent Versions**: All dependencies defined once in `pyproject.toml`
  - **Docker Integration**: Dockerfile installs directly from `pyproject.toml`
  - **Missing Dependencies**: Added `python-multipart` for file upload support
  - Files: `pyproject.toml`, `docker/Dockerfile.backend`

### Enhanced

- **🔧 Robust Entrypoint Scripts**: Production-grade startup scripts with comprehensive error handling
  - **Fail-Safe Backend**: Waits for Ollama health before starting, with timeout and retry logic
  - **Clean Separation**: Each container manages its own concerns (backend=API, ollama=models, frontend=UI)
  - **Logging**: Detailed startup logs for debugging and monitoring
  - **Non-Blocking**: Services start independently without blocking each other
  - Files: `docker/entrypoint.sh`, `docker/ollama-entrypoint.sh`

- **⚙️ Configuration Management**: Versioned configuration with sensible defaults
  - **Default Ollama Settings**: Pre-configured for `ollama` provider with `qwen3-coder:30b` model
  - **No Setup Required**: Works out-of-the-box with `docker-compose up`
  - **Customizable**: Easy to modify provider, model, and connection settings
  - Files: `config.json`

### Changed

- **📁 Data Management**: Removed automatic sample data copying for cleaner deployments
  - **User Responsibility**: Users must upload their own data or manually copy sample data
  - **Cleaner Builds**: Reduced image size and deployment complexity
  - **Clear Documentation**: Instructions for data management in Docker guide
  - Files: `docker/Dockerfile.backend`, `docker/README.md`

### Fixed

- **🔌 Ollama Connection**: Corrected AbstractCore parameter from `api_base` to `base_url`
  - **Root Cause**: AbstractCore uses `base_url` parameter, not `api_base`
  - **Impact**: Ollama provider now connects correctly in Docker environment
  - Files: `backend/app/services/llm_service.py`

- **🏗️ Docker Build**: Fixed build order to copy application code before pip install
  - **Root Cause**: Dockerfile tried to install package before copying source code
  - **Solution**: Reorganized Dockerfile to copy `app/` directory before running `pip install`
  - Files: `docker/Dockerfile.backend`

- **🏥 Health Checks**: Removed blocking model downloads from backend health checks
  - **Problem**: Backend downloaded 17GB models before passing health checks (15-30 min timeout)
  - **Solution**: Moved model downloads to Ollama container startup
  - **Result**: Backend starts in ~15 seconds, health checks pass immediately
  - Files: `docker/entrypoint.sh`, `docker/ollama-entrypoint.sh`

### Technical Details

**Docker Architecture**:
- **3-Service Design**: Frontend (Nginx) → Backend (FastAPI) → Ollama (LLM)
- **Port Mapping**: Frontend (80), Backend (8000), Ollama (11434)
- **Network**: Custom bridge network for inter-container communication
- **Volumes**: Named volumes for persistence (notebooks, data, logs, ollama-models)
- **Resource Limits**: Ollama (32GB/8 cores), Backend (4GB/2 cores), Frontend (unlimited)

**Deployment Options**:
1. **Quick Test**: Frontend + Backend only (~2 minutes, no LLM)
2. **Full Deployment**: All services with automatic model download (~20-40 minutes first time)
3. **Development Mode**: Hot-reload enabled with `docker-compose.dev.yml`
4. **Production**: Optimized builds with health checks and resource limits

**System Requirements**:
- Memory: 16-32GB RAM for qwen3-coder:30b (or 8GB for qwen3-coder:4b)
- Disk: 25GB minimum (images + models)
- Docker: Version 20.10+ with Compose v2

## [0.0.8] - 2025-10-28

### Added

- **🧬 State-of-the-Art H5 File Support**: Comprehensive support for HDF5 files with interactive visualization
  - **H5/HDF5 Files**: Full support for standard HDF5 files with hierarchical structure analysis
  - **H5AD (AnnData) Files**: Specialized support for single-cell genomics data with scanpy integration
  - **Interactive Preview**: Tree-based file structure browser with metadata and sample data display
  - **Memory Efficient Processing**: Smart sampling for large datasets to provide previews without memory issues
  - **Robust Error Handling**: Graceful fallbacks and comprehensive error reporting
  - **Dependencies**: Added h5py>=3.10.0, anndata>=0.10.0, and tables>=3.9.0 to requirements
  - Files: `backend/app/services/h5_service.py`, `frontend/src/components/H5FileViewer.tsx`, `backend/app/services/data_manager_clean.py`, `frontend/src/components/FileViewerModal.tsx`, `frontend/src/components/FileContextPanel.tsx`, `requirements.txt`, `docs/getting-started.md`

## [0.0.7] - 2025-10-26

### Updated

- **AbstractCore 2.5.2 Integration**: Updated to AbstractCore version 2.5.2 for improved stability and performance
  - **Version Consistency**: Updated all version references from 2.4.6/2.4.8 to 2.5.2 across codebase
  - **Dependency Updates**: Updated `requirements.txt` and `pyproject.toml` to require `abstractcore[all]>=2.5.2`
  - **Comment Updates**: Updated all AbstractCore version references in code comments to reflect current version
  - Files: `requirements.txt`, `pyproject.toml`, `backend/app/services/llm_service.py`, `backend/app/api/llm.py`, `backend/app/services/token_tracker.py`, `backend/app/models/notebook.py`, `frontend/src/types/index.ts`

## [0.0.6] - 2025-10-22

### Fixed

- **Files in Context UI**: Removed redundant eye button from Files in Context section since it's already a collapsible section
- **Enhanced File Awareness**: Significantly improved LLM awareness of available files with comprehensive metadata and previews
  - **Rich File Previews**: Added detailed previews for CSV (columns, shape, sample data), JSON (schema analysis), Excel (sheet names), and text files
  - **Smart JSON Schema Analysis**: Automatically analyzes JSON structure to provide object/array type information and property schemas
  - **LLM Context Integration**: Files are now prominently displayed in LLM prompts with full metadata, making the LLM aware of available data
  - **File Size Formatting**: Human-readable file sizes (B, KB, MB, GB) in both UI and LLM context
  - **Structured Information**: LLM receives file paths, types, sizes, and content previews for better code generation
  - Files: `frontend/src/components/FileContextPanel.tsx`, `backend/app/services/llm_service.py`, `backend/app/services/data_manager_clean.py`


## [0.0.5] - 2025-10-22

### Enhanced

- **AbstractCore 2.4.8 Integration**: Updated to latest AbstractCore version with improved token counting and generation time tracking
  - **Accurate Token Counts**: Now uses proper `input_tokens`, `output_tokens`, `total_tokens` from AbstractCore 2.4.8+ (with backward compatibility for legacy field names)
  - **Generation Time Display**: Added discrete generation time display for each cell in iPhone message style (e.g., "14:32 | 1.2s")
  - **Timestamp Tracking**: Added execution timestamps to cells showing when each cell was last executed
  - **Fixed Footer Token Display**: Resolved issue where footer showed "0 / 262.1k" instead of actual tokens used in methodology generation
  - Files: `backend/app/services/token_tracker.py`, `backend/app/services/llm_service.py`, `backend/app/services/notebook_service.py`, `frontend/src/components/PromptEditor.tsx`, `frontend/src/types/index.ts`

- **Enhanced Library Support & Error Handling**: Comprehensive improvements to library management and auto-retry system
  - **Essential Libraries Added**: Added `umap-learn`, `scanpy`, and `openpyxl` for bioinformatics and data parsing (removed over-engineered libraries like opencv, xgboost, biopython)
  - **Smart Import Error Detection**: Added intelligent error analyzer that suggests alternatives when users try unavailable libraries (e.g., suggests sklearn for tensorflow, PIL for opencv)
  - **Matplotlib Color Error Fix**: Added specific error analyzer for categorical data color mapping issues with targeted solutions (color_map, seaborn, factorize)
  - **Enhanced Auto-Retry System**: Increased max retries from 3 to 5 attempts with improved visual progress indicators showing "correcting code x/5"
  - **Complete Error Context**: LLM now receives full error details including original message, stack trace, and domain-specific guidance for better auto-fixes
  - **Simplified Architecture**: Replaced complex import interception system with elegant keyword-based suggestions for maintainability

### Changed

- **Data Management**: Removed automatic sample data copying; users must now upload their own data or manually copy sample data


## [0.0.4] - 2025-10-21

### Enhanced
- **Provider Health Check**: Upgraded to use AbstractCore 2.4.6's native `provider.health()` method
  - **Real Health Status**: Now uses actual provider health checks instead of basic initialization checks
  - **Better Error Messages**: More detailed health status information from AbstractCore
  - **Automatic Updates**: Health status refreshes every 60 seconds in the UI (reasonable frequency)
  - Files: `backend/app/services/llm_service.py`, `backend/app/api/llm.py`, `frontend/src/components/LLMStatusFooter.tsx`

- **Dual Seed Management**: Implemented comprehensive seed management using both AbstractCore and execution environment
  - **LLM Generation Seeds**: Uses AbstractCore's native SEED parameter for consistent code generation
  - **Execution Environment Seeds**: Maintains global random state management for consistent code execution results
  - **Provider Support**: AbstractCore SEED works with all providers except Anthropic (as per AbstractCore 2.4.6 spec)
  - **Consistent Results**: Each notebook gets deterministic seeds based on notebook ID hash for both LLM and execution
  - **Clean Code Generation**: LLM no longer generates `np.random.seed(42)` in code - system handles all reproducibility
  - **Two-Layer Approach**: LLM seed ensures consistent code generation, execution seed ensures consistent random data
  - Files: `backend/app/services/llm_service.py`, `backend/app/services/execution_service.py`

- **User-Controlled Seed UI**: Added intuitive seed control interface for reproducibility management
  - **LLM Settings Integration**: Seed control integrated into LLM Settings modal (gear icon)
  - **Educational Tooltip**: Comprehensive tooltip explaining seeds and reproducibility for non-technical users
  - **Smart Defaults**: Automatic seed generation based on notebook ID, with option for custom seeds
  - **Random Generation**: One-click random seed generation with shuffle button
  - **Dual Application**: Custom seeds affect both LLM generation and execution environment
  - **Validation**: Input validation ensures seeds are within valid range (0-2,147,483,647)
  - **Persistent Storage**: Custom seeds are saved with notebook metadata
  - Files: `frontend/src/components/LLMSettingsModal.tsx`, `frontend/src/components/Header.tsx`, `backend/app/api/notebooks.py`, `backend/app/services/notebook_service.py`

### Removed
- **Redundant Seed Methods**: Eliminated some custom seed management methods in favor of cleaner dual approach
  - Removed: `reset_random_state()`, `execute_code_with_fresh_random()` methods (complex state switching)
  - Simplified: Cleaner separation between LLM seeds (AbstractCore) and execution seeds (environment)
  - Cleaner: LLM prompts no longer need to instruct against seed usage

## [0.0.3] - 2025-10-21

### Fixed
- **JSON Export Bug**: Fixed critical issue where JSON export was downloading `"[object Object]"` instead of proper JSON content
  - Root cause: Axios was auto-parsing JSON responses, then the parsed object was being incorrectly converted to string
  - Solution: Enhanced frontend API client to detect auto-parsed JSON responses and re-stringify them properly
  - File: `frontend/src/services/api.ts`

### Enhanced
- **JSON Export Structure**: Completely redesigned JSON export format for better usability and actionability
  - **Clean Structure**: Removed internal application state (execution flags, retry counters, etc.)
  - **Organized Sections**: Clear separation between metadata, configuration, and content
  - **Cell Content Focus**: Each cell now has a clean `content` object with `prompt`, `code`, and `methodology`
  - **Execution Summary**: Lightweight execution status without heavy data (plots, tables stored as boolean flags)
  - **Export Metadata**: Added export timestamp and version tracking
  - **Improved Readability**: Structured for easy parsing and human readability

### Added
- **Export Documentation**: New `docs/export.md` documenting the export system and JSON structure
- **Version Tracking**: Export files now include Digital Article version and export timestamp

### Technical Details

**New JSON Export Structure**:
```json
{
  "digital_article": {
    "version": "0.0.3",
    "export_timestamp": "2025-10-21T07:53:25.083962"
  },
  "metadata": {
    "title": "Article Title",
    "description": "Article Description", 
    "author": "Author Name",
    "created_at": "...",
    "updated_at": "..."
  },
  "configuration": {
    "llm_provider": "lmstudio",
    "llm_model": "qwen/qwen3-next-80b"
  },
  "cells": [
    {
      "type": "prompt",
      "content": {
        "prompt": "Natural language prompt",
        "code": "Generated Python code",
        "methodology": "Scientific explanation"
      },
      "execution": {
        "status": "success",
        "has_plots": true,
        "has_tables": false
      }
    }
  ]
}
```

## [0.0.2] - 2025-10-20

### Documentation
- **Added** comprehensive documentation suite:
  - `docs/architecture.md` - Complete system architecture documentation with diagrams
  - `docs/philosophy.md` - Design principles and philosophical foundations
  - `docs/getting-started.md` - Step-by-step installation and tutorial guide
  - `docs/backlog/README.md` - Canonical planning backlog (supersedes legacy roadmap)
  - Updated `README.md` - Comprehensive project overview with feature comparison

### Summary

This release represents the first stable beta version of Digital Article with complete documentation. The system is functional for single-user or small team deployment, featuring natural language to code generation, automatic scientific methodology writing, and rich output capture.

**Current Capabilities**:
- Natural language prompts → Python code generation via LLM
- Automatic code execution with matplotlib/plotly/pandas output capture
- Auto-retry error correction (up to 3 attempts with LLM self-debugging)
- Scientific article-style methodology generation
- Multi-format export (JSON, HTML, Markdown, PDF)
- Workspace isolation with file management
- Persistent execution context across cells

**Known Limitations**:
- Single-user deployment only (no authentication)
- Code executes in same process as server (not production-safe)
- JSON file storage (not scalable)
- No real-time collaboration
- See docs/backlog/README.md for planned improvements

## [0.1.0] - 2025-10-16

### Changed
- Renamed project from "Reverse Analytics Notebook" to "Digital Article"
- Updated all references, documentation, and UI elements to reflect new name

### Fixed
- Save and export functionality now working
- Improved error handling and logging

### Known Issues
- PDF export has occasional rendering issues with complex plots
- Auto-retry may fail on certain syntax errors
- File upload limited to 100MB

## [0.0.0] - 2025-10-15

### Added - Initial Implementation

#### Core Architecture
- **Backend**: FastAPI + Python with AbstractCore LLM integration
- **Frontend**: React + TypeScript with Vite build system
- **LLM Integration**: AbstractCore with LMStudio provider using qwen/qwen3-next-80b model

#### Natural Language Interface
- Prompt-based cell system for natural language analysis requests
- Automatic Python code generation from prompts
- Dual view mode (toggle between prompt and generated code)
- Real-time code execution with comprehensive output capture

#### Visualization & Output Capture
- Matplotlib static plots (PNG export via base64)
- Plotly interactive visualizations (JSON serialization)
- Pandas DataFrame rendering (HTML tables + JSON data)
- Image display capabilities
- Full Python stdout/stderr capture
- Complete error tracebacks with type information

#### Cell & Notebook Management
- Complete CRUD operations for notebooks and cells
- Multiple cell types:
  - **Prompt cells**: Natural language → code
  - **Code cells**: Direct Python coding
  - **Markdown cells**: Documentation
  - **Methodology cells**: Scientific explanations
- Cell execution tracking (execution count, status, timing)
- Auto-save functionality (2-second debounce)

#### Export Capabilities
- **JSON export**: Full notebook with all data
- **HTML export**: Standalone web page with interactive plots
- **Markdown export**: Plain text format for version control
- **PDF export**: Scientific article style with methodology sections

#### Data Management
- Sample datasets included (gene_expression, patient_data, protein_levels, drug_response)
- File upload and management system
- Notebook-specific workspaces (isolated data directories)
- Data file context panel with previews

#### Error Handling & Recovery
- Comprehensive error capture with full tracebacks
- Auto-retry mechanism with LLM-based error fixing (up to 3 attempts)
- Detailed error logging for debugging
- User-friendly error messages in UI

#### Developer Tools
- CLI commands: `da-backend` and `da-frontend` for easy startup
- Automatic port management (kills existing processes)
- Development mode with hot reload
- OpenAPI documentation at `/docs` endpoint

#### Technical Components

**Backend Services** (`backend/app/services/`):
- `llm_service.py` - LLM code generation and explanation
- `execution_service.py` - Python code execution sandbox
- `notebook_service.py` - Notebook orchestration and persistence
- `data_manager_clean.py` - Workspace and file management
- `pdf_service_scientific.py` - Scientific PDF generation

**Frontend Components** (`frontend/src/components/`):
- `NotebookContainer.tsx` - Main notebook orchestration
- `NotebookCell.tsx` - Individual cell rendering
- `ResultPanel.tsx` - Rich output display
- `FileContextPanel.tsx` - Data file management
- `PDFGenerationModal.tsx` - Export progress UI

**API Endpoints**:
- `/api/notebooks/` - Notebook CRUD operations
- `/api/cells/` - Cell CRUD and execution
- `/api/llm/` - Direct LLM interactions
- `/api/files/` - File upload/download/management
- `/api/system/` - System information and health

#### Key Features

**Prompt-Code Mapping**:
- Every prompt generates exactly one code implementation
- Code is always visible and editable
- Context-aware generation (considers previous cells, available variables, data files)

**Intelligent Code Generation**:
- System prompts enforce data path conventions (`data/` directory)
- Automatic library imports
- Error handling with try/except blocks
- Variable and data context injection

**Multi-Format Output Support**:
- Text: stdout/stderr streams
- Static plots: matplotlib/seaborn (base64 PNG)
- Interactive plots: Plotly (JSON with full interactivity)
- Tables: Pandas DataFrames (HTML + JSON)
- Errors: Full Python tracebacks with syntax highlighting

**Scientific Methodology Generation**:
- LLM generates article-style explanations after successful execution
- High-impact journal writing style (Nature/Science/Cell)
- Includes quantitative results and statistical measures
- 2-4 sentence concise paragraphs

**Production Ready Features**:
- Comprehensive error handling throughout stack
- Structured logging for debugging
- Type safety with Pydantic models (backend) and TypeScript (frontend)
- Modular architecture for extensibility

### Dependencies

**Python** (`requirements.txt`):
- abstractcore[all]>=2.4.1 - LLM provider abstraction
- fastapi>=0.104.1 - Web framework
- uvicorn[standard]>=0.24.0 - ASGI server
- pandas>=2.1.4, numpy>=1.26.0 - Data analysis
- matplotlib>=3.8.2, plotly>=5.17.0, seaborn>=0.13.0 - Visualization
- scikit-learn>=1.3.2, scipy>=1.11.4 - Machine learning and stats
- reportlab>=4.0.7, weasyprint>=60.0 - PDF generation
- pydantic>=2.5.2 - Data validation

**Node.js** (`frontend/package.json`):
- react@18.2.0, react-dom@18.2.0 - UI framework
- typescript@5.2.2 - Type safety
- vite@4.5.0 - Build tool
- tailwindcss@3.3.6 - Styling
- axios@1.6.2 - HTTP client
- @monaco-editor/react@4.6.0 - Code viewer
- plotly.js@2.27.1, react-plotly.js@2.6.0 - Interactive plots
- marked@16.4.0 - Markdown rendering

### Architecture Highlights
- **Modular design**: Clear separation between services, components, and data models
- **Scalable structure**: Easily extensible for new features and providers
- **Security conscious**: Safe code execution with error boundaries
- **Performance optimized**: Efficient rendering and state management
- **User experience focused**: Intuitive interface for non-technical users

### Files Added

**Backend**:
- Complete FastAPI application in `backend/app/`
- Service layer with LLM, execution, and notebook services
- Pydantic data models for type safety
- API routers for all endpoints
- Data manager for workspace isolation

**Frontend**:
- React application with TypeScript in `frontend/src/`
- Component-based architecture
- API client with error handling
- Rich output display components
- File management UI

**Configuration**:
- `pyproject.toml` - Python package configuration
- `requirements.txt` - Python dependencies
- `frontend/package.json` - Node.js dependencies
- `frontend/tsconfig.json` - TypeScript configuration
- `frontend/tailwind.config.js` - Tailwind CSS configuration

**Data & Scripts**:
- Sample datasets in `sample_data/`
- CLI scripts in `digitalarticle/`
- Build and dist directories for package distribution

### Initial Release Notes

This initial release (v0.0.0) provided a complete, working implementation of the revolutionary Digital Article concept, enabling domain experts to perform sophisticated data analysis through natural language interaction. The system successfully demonstrates the "article-first" paradigm where narrative descriptions generate executable code and scientific methodology text.

**Target Users**: Researchers, biologists, clinicians, data scientists who want to focus on analysis rather than coding.

**Deployment**: Suitable for single-user local deployment or small team shared server. Not yet ready for production multi-user environments.

---

## Future Plans

See [`docs/backlog/README.md`](docs/backlog/README.md) for canonical planning.

**Near-term priorities**:
- Enhanced error diagnostics
- Domain-specific prompt templates
- Version control for cells
- Improved scientific methodology generation
- Comprehensive test coverage

**Medium-term goals**:
- Multi-user authentication
- Database storage (PostgreSQL)
- Real-time collaboration
- Containerized code execution

**Long-term vision**:
- LLM-suggested analysis strategies
- Active learning from user corrections
- Plugin architecture
- Enterprise features (SSO, compliance, HA)

---

## Notes

- This project follows semantic versioning
- Breaking changes will be clearly documented
- Beta versions (1.x) may have breaking changes between minor versions
- Stable versions (2.x+) will maintain backward compatibility within major versions

For detailed change history, see git commit log.
For bug reports and feature requests, see GitHub Issues.
