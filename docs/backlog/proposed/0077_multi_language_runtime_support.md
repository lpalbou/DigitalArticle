# Backlog Item (Proposed)

## Title
Multi-Language Runtime Support (R, Julia, etc.)

## Backlog ID
0077

## Priority
- **P2 (proposed)**: Strategic capability for broader audience (bioinformatics, statistics), but requires significant architectural investment. Should be planned after core Python loop is stable and production-hardened.

## Date / Time
2026-02-01

## Short Summary
Today Digital Article executes only Python code. Many scientific domains (especially bioinformatics and classical statistics) heavily rely on R. Some HPC and numerical simulation workflows use Julia. This backlog item explores the architecture changes needed to support multiple language runtimes while preserving the article-first experience: intent → executable code → verified results → publishable methodology.

## Key Goals
- Define a language-agnostic execution interface that the existing orchestration layer (NotebookService) can use
- Preserve the "execution as source of truth" contract regardless of language
- Maintain inspectability (code, outputs, diffs, errors, traces) for all languages
- Avoid duplicating the entire service layer for each language

## Scope

### To do
- Survey current Python-specific coupling in:
  - `ExecutionService` (exec sandbox, globals capture, display hooks)
  - `LLMService` (code generation prompts, linting, autofix)
  - `NotebookService` (retry loop, methodology extraction)
  - Frontend (syntax highlighting, cell language indicator)
- Design a `LanguageRuntime` abstraction with:
  - `execute(code: str, context: dict) → ExecutionResult`
  - `lint(code: str) → LintReport`
  - `serialize_state() / deserialize_state()`
  - Language-specific metadata (name, file extension, syntax ID)
- Evaluate runtime options:
  - **R**: rpy2 (in-process), Rserve, or subprocess with Rscript
  - **Julia**: PyJulia, subprocess
  - **Polyglot kernels**: Jupyter kernel protocol as a unifying layer (e.g., jupyter_client)
- Prototype minimal R support behind a feature flag

### NOT to do
- Full production support for all languages in the first iteration
- Language-specific personas (out of scope; can be added later)
- Real-time collaboration (orthogonal)

## Dependencies

### Backlog dependencies (ordering)
- Should follow:
  - [`0010_production_hardening_execution_sandbox.md`](../planned/0010_production_hardening_execution_sandbox.md) — sandboxing must be language-agnostic
  - [`0007_perfect_observability_llm_agentic_tracing.md`](../planned/0007_perfect_observability_llm_agentic_tracing.md) — tracing must work for all runtimes

### ADR dependencies (must comply)
- **All ADRs are mandatory**: [`docs/adr/README.md`](../../adr/README.md)
- **Primary ADR dependencies**:
  - [`ADR 0001`](../../adr/0001-article-first-mixed-audience.md) — article-first must remain language-agnostic
  - [`ADR 0005`](../../adr/0005-perfect-observability.md) — observability must cover all runtimes
  - [`ADR 0007`](../../adr/0007-permissive-licenses-and-minimal-dependencies.md) — language bridges must be permissively licensed

### Points of vigilance (during execution)
- Avoid leaking language-specific logic into NotebookService; push it into LanguageRuntime adapters
- State persistence must handle language-specific objects (e.g., R data.frames, Julia arrays)
- LLM prompts must be language-aware without code duplication (use templates with language tokens)
- Linting/autofix must be pluggable per language

## References (source of truth)
- `backend/app/services/execution_service.py` — current Python-only execution
- `backend/app/services/llm_service.py` — code generation prompts
- `backend/app/services/notebook_service.py` — orchestration loop

## Proposal (initial; invites deeper thought)

### Context / constraints
- The current architecture is tightly coupled to Python:
  - `exec()` with a `globals()` dict
  - Matplotlib/Plotly display hooks
  - Ruff linting and autofix
  - Pickle for state persistence
- Adding R/Julia requires abstracting these into a `LanguageRuntime` interface

### Design options considered (with long-term consequences)

#### Option A: In-process bridges (rpy2, PyJulia)
- **Pros**: Low latency; shared memory; can pass objects between languages
- **Cons**: Complex installation (native libs); stability issues; hard to sandbox; license risks (rpy2 is GPL)
- **Long-term consequences**: Tight coupling to host environment; hard to containerize cleanly

#### Option B: Subprocess execution (Rscript, julia CLI)
- **Pros**: Simple; isolated; easy to sandbox; no GPL bridges
- **Cons**: No shared state between cells (must serialize/deserialize); higher latency
- **Long-term consequences**: Clean separation but loses interactive REPL feel

#### Option C: Jupyter kernel protocol (recommended for exploration)
- **Pros**: Mature ecosystem; kernels exist for R (IRkernel), Julia, and 50+ languages; handles display/output/errors uniformly; sandboxable via containers
- **Cons**: Adds Jupyter as a dependency; kernel lifecycle management; some overhead
- **Long-term consequences**: Leverages battle-tested infrastructure; enables plugin-style language support; aligns with industry standards

#### Option D: Hybrid (Python in-process, others via kernel)
- **Pros**: Keeps Python fast; adds languages incrementally; manageable complexity
- **Cons**: Two code paths to maintain
- **Long-term consequences**: Pragmatic; can migrate Python to kernel later if needed

### Recommended approach (current best choice)
**Option D (Hybrid)** for first iteration:
1. Keep Python execution as-is (in-process `exec()`)
2. Add a `LanguageRuntime` abstraction with a `PythonRuntime` wrapper around current code
3. Implement `RKernelRuntime` using `jupyter_client` + IRkernel
4. Feature-flag R support; validate with 1-2 real notebooks
5. Generalize to Julia and others once the abstraction is proven

### Testing plan (A/B/C)
> Follow [`docs/adr/0002-ab-testing-ladder.md`](../../adr/0002-ab-testing-ladder.md).

- **A (mock / conceptual)**:
  - Define `LanguageRuntime` interface; mock R execution; verify NotebookService doesn't break
- **B (real code + real examples)**:
  - Install IRkernel in Docker; run a real R cell (ggplot2 example); capture figure output
- **C (real-world / production-like)**:
  - Mixed Python + R notebook (e.g., Python data prep, R statistical modeling, Python visualization)

## Acceptance Criteria (must be fully satisfied)
- [ ] `LanguageRuntime` abstraction exists and Python execution is wrapped in `PythonRuntime`
- [ ] At least one non-Python language (R) can execute cells behind a feature flag
- [ ] Outputs (figures, tables, stdout) are captured and displayed uniformly
- [ ] State persistence works for R (variables survive across cells)
- [ ] No regressions in Python execution tests

## Implementation Notes (fill during execution)
TBD

## Full Report (fill only when moving to completed/)
TBD
