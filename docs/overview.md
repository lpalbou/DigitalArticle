# Documentation Overview (map of docs)

This page is the **index** of documentation for Digital Article. The guiding rule is: **code is the source of truth** (see [`docs/architecture.md`](architecture.md) for the canonical map).

## Entry points (start here)

- [`README.md`](../README.md) — project overview + quick start + doc links
- [`docs/getting-started.md`](getting-started.md) — practical setup and first run

## Canonical docs (describe the current system)

- [`docs/architecture.md`](architecture.md) — canonical system map (routers, services, persistence, diagrams)
- [`docs/limitations.md`](limitations.md) — known limitations + production readiness expectations
- [`docs/troubleshooting.md`](troubleshooting.md) — common failure modes (LLM connectivity, Docker networking, SSE, exports)
- [`docs/error-handling.md`](error-handling.md) — ErrorAnalyzer + auto-retry architecture
- [`docs/export.md`](export.md) — export formats and endpoints (including streaming)
- [`docs/docker-containerization.md`](docker-containerization.md) — containerization rationale (canonical section) + legacy notes
- [`docs/variable-state-persistence.md`](variable-state-persistence.md) — execution state snapshot design + current storage nuance
- [`docs/persona-and-review-architecture.md`](persona-and-review-architecture.md) — personas + review system architecture
- [`docs/philosophy.md`](philosophy.md) — product principles and non-goals

## Dive-ins (critical components)

All dive-ins start with a summary, how the component fits in the bigger picture, and at least one diagram:

- [`docs/dive_ins/notebook_service.md`](dive_ins/notebook_service.md)
- [`docs/dive_ins/llm_service.md`](dive_ins/llm_service.md)
- [`docs/dive_ins/execution_service.md`](dive_ins/execution_service.md)
- [`docs/dive_ins/data_manager.md`](dive_ins/data_manager.md)
- [`docs/dive_ins/review_service.md`](dive_ins/review_service.md)
- [`docs/dive_ins/persona_system.md`](dive_ins/persona_system.md)

## Data-flow diagrams

- [`docs/data_flow.md`](data_flow.md) — call graphs / sequences for key user flows (execute, export, review, model downloads)

## Knowledge base (critical insights)

- [`docs/knowledge_base.md`](knowledge_base.md) — accumulated “do not forget” truths and pitfalls; deprecated insights are moved to a DEPRECATED section (never deleted)

## Semantic modeling references (optional)

- [`docs/semantic_models.md`](semantic_models.md) — ontology selection + JSON-LD context patterns (reference)

## Persona content (examples and workflows)

- [`examples/persona/persona-ms-examples.md`](../examples/persona/persona-ms-examples.md)
- [`examples/article/persona-ms-scenarios.md`](../examples/article/persona-ms-scenarios.md)

## Work-in-progress / proposal docs (not authoritative)

These are kept for historical context. Each file should clearly state its status.

- [`docs/aggregate-profile-portfolio.md`](aggregate-profile-portfolio.md) — proposal (not implemented)
- [`docs/backlog/completed/0031_digital_article_implementation_plan.md`](backlog/completed/0031_digital_article_implementation_plan.md)
- [`docs/backlog/completed/0030_critique_driven_retry_loop_proposal.md`](backlog/completed/0030_critique_driven_retry_loop_proposal.md)
- [`docs/backlog/completed/0029_cell_output_display_improvement_proposal.md`](backlog/completed/0029_cell_output_display_improvement_proposal.md)
- [`docs/backlog/completed/0028_async_llm_calls_smart_autosave.md`](backlog/completed/0028_async_llm_calls_smart_autosave.md)

## Historical investigations (legacy devnotes migrated to backlog)

The legacy `docs/devnotes/` folder was migrated into completed backlog items (so historical work lives under one governance system):

- [`docs/backlog/completed/0012_fix_traces_after_docker.md`](backlog/completed/0012_fix_traces_after_docker.md)
- [`docs/backlog/completed/0013_docker_external_ollama_fix.md`](backlog/completed/0013_docker_external_ollama_fix.md)
- [`docs/backlog/completed/0014_abstractcore_model_download_api.md`](backlog/completed/0014_abstractcore_model_download_api.md)
- [`docs/backlog/completed/0015_abstractcore_v262_upgrade.md`](backlog/completed/0015_abstractcore_v262_upgrade.md)
- [`docs/backlog/completed/0016_docker_one_image.md`](backlog/completed/0016_docker_one_image.md)
- [`docs/backlog/completed/0017_dynamic_library_loading.md`](backlog/completed/0017_dynamic_library_loading.md)
- [`docs/backlog/completed/0018_error_enhancement_system.md`](backlog/completed/0018_error_enhancement_system.md)
- [`docs/backlog/completed/0019_execution_context_persistence.md`](backlog/completed/0019_execution_context_persistence.md)
- [`docs/backlog/completed/0020_fix_asset_display.md`](backlog/completed/0020_fix_asset_display.md)
- [`docs/backlog/completed/0021_fix_retry_context.md`](backlog/completed/0021_fix_retry_context.md)
- [`docs/backlog/completed/0022_model_download_implementation_final.md`](backlog/completed/0022_model_download_implementation_final.md)
- [`docs/backlog/completed/0023_model_download_test_plan.md`](backlog/completed/0023_model_download_test_plan.md)
- [`docs/backlog/completed/0024_semantic_extractions.md`](backlog/completed/0024_semantic_extractions.md)
- [`docs/backlog/completed/0025_variable_reuse_enhancement.md`](backlog/completed/0025_variable_reuse_enhancement.md)

## Project planning and decisions

- **Backlog**: [`docs/backlog/README.md`](backlog/README.md) (planned items + completion reports)
- **ADRs**: [`docs/adr/README.md`](adr/README.md) (architecture decisions; includes A/B/C testing and truncation policy)

