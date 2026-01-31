# Backlog (planning + execution workflow)

This folder is the **project management spine** for Digital Article’s technical work. Every recommendation, change, or non-trivial fix should be tracked as a backlog item.

> **CRITICAL:** Anyone executing backlog items MUST comply with **all ADRs** in [`docs/adr/README.md`](../adr/README.md).  
> Backlog items must explicitly list ADR dependencies and points of vigilance.

## Naming convention (enforced)

- **File name**: `{BACKLOG_ID}_{short_task_description}.md`
  - Example: `0003_fix_test_suite_regressions.md`
- **BACKLOG_ID**: a globally unique integer (recommend 4 digits) across **proposed**, **planned**, and **completed**
- **short_task_description**: snake_case, lower case (avoid dates in file names; date/time belongs inside the backlog file)

## Folder structure

- [`docs/backlog/template.md`](template.md) — **required** template for all backlog items
- [`docs/backlog/proposed/`](proposed/) — **uncertain** items needing review/user guidance before execution
- [`docs/backlog/planned/`](planned/) — items that are approved or proposed but not completed
- [`docs/backlog/completed/`](completed/) — items that are completed (must include a **Full Report**)
- [`docs/backlog/recurrent/`](recurrent/) — **recurrent** tasks/mechanisms that must be checked when their triggers apply

## Status tracking

### Proposed

- See [`docs/backlog/proposed/`](proposed/) for items that are not ready to execute yet.


#### Roadmap-derived epics (legacy; decomposed)

These were decomposed from legacy `ROADMAP.md` and require review before promotion to `planned/`:

- **Phase 1: Stabilization & Core Improvements (Q1-Q2 2025)**
  - [`0033_enhanced_error_handling_diagnostics.md`](proposed/0033_enhanced_error_handling_diagnostics.md)
  - [`0034_domain_specific_llm_prompt_templates.md`](proposed/0034_domain_specific_llm_prompt_templates.md)
  - [`0035_improved_scientific_methodology_generation.md`](proposed/0035_improved_scientific_methodology_generation.md)
  - [`0036_interactive_question_interface_for_published_articles.md`](proposed/0036_interactive_question_interface_for_published_articles.md)
  - [`0037_version_control_for_cells.md`](proposed/0037_version_control_for_cells.md)
  - [`0038_enhanced_export_formats.md`](proposed/0038_enhanced_export_formats.md)
  - [`0039_code_quality_improvements.md`](proposed/0039_code_quality_improvements.md)
  - [`0040_performance_optimization.md`](proposed/0040_performance_optimization.md)
  - [`0041_cell_dependency_management_intelligent_updates.md`](proposed/0041_cell_dependency_management_intelligent_updates.md)
  - [`0042_accessibility_improvements.md`](proposed/0042_accessibility_improvements.md)

- **Phase 2: Multi-User & Collaboration (Q3-Q4 2025)**
  - [`0043_user_authentication_authorization.md`](proposed/0043_user_authentication_authorization.md)
  - [`0044_database_migration.md`](proposed/0044_database_migration.md)
  - [`0045_real_time_collaboration.md`](proposed/0045_real_time_collaboration.md)
  - [`0046_notebook_sharing_permissions.md`](proposed/0046_notebook_sharing_permissions.md)
  - [`0047_live_article_publishing_exploration_platform.md`](proposed/0047_live_article_publishing_exploration_platform.md)
  - [`0048_comments_annotations.md`](proposed/0048_comments_annotations.md)
  - [`0049_notification_system.md`](proposed/0049_notification_system.md)

- **Phase 3: Advanced Features & Intelligence (2026+)**
  - [`0050_llm_suggested_analysis_strategies.md`](proposed/0050_llm_suggested_analysis_strategies.md)
  - [`0051_intelligent_question_generation_exploration_pathways.md`](proposed/0051_intelligent_question_generation_exploration_pathways.md)
  - [`0052_containerized_code_execution.md`](proposed/0052_containerized_code_execution.md)
  - [`0053_template_library_workflow_marketplace.md`](proposed/0053_template_library_workflow_marketplace.md)
  - [`0054_active_learning_from_user_corrections.md`](proposed/0054_active_learning_from_user_corrections.md)
  - [`0055_reproducibility_enhancements.md`](proposed/0055_reproducibility_enhancements.md)
  - [`0056_integration_with_data_sources.md`](proposed/0056_integration_with_data_sources.md)
  - [`0057_natural_language_queries_on_results.md`](proposed/0057_natural_language_queries_on_results.md)
  - [`0058_mobile_interface.md`](proposed/0058_mobile_interface.md)

- **Phase 4: Enterprise & Scale (2027+)**
  - [`0059_plugin_architecture.md`](proposed/0059_plugin_architecture.md)
  - [`0060_knowledge_networks_scientific_discovery_platform.md`](proposed/0060_knowledge_networks_scientific_discovery_platform.md)
  - [`0061_enterprise_authentication.md`](proposed/0061_enterprise_authentication.md)
  - [`0062_governance_compliance.md`](proposed/0062_governance_compliance.md)
  - [`0063_high_availability_scalability.md`](proposed/0063_high_availability_scalability.md)
  - [`0064_cost_management_monitoring.md`](proposed/0064_cost_management_monitoring.md)

### Planned

- See [`docs/backlog/planned/`](planned/) for all active items.

### Completed

- See [`docs/backlog/completed/`](completed/) for completed items with full reports.

## Current backlog items

### Proposed (needs review)

- [`docs/backlog/proposed/0026_add_lint_report_to_cell_execution.md`](proposed/0026_add_lint_report_to_cell_execution.md)
- [`docs/backlog/proposed/0027_auto_fix_safe_lint_issues.md`](proposed/0027_auto_fix_safe_lint_issues.md)

### Planned (active)

- [`docs/backlog/planned/0003_fix_test_suite_regressions.md`](planned/0003_fix_test_suite_regressions.md)
- [`docs/backlog/planned/0004_unify_llm_config_surfaces.md`](planned/0004_unify_llm_config_surfaces.md)
- [`docs/backlog/planned/0005_unify_persistence_roots.md`](planned/0005_unify_persistence_roots.md)
- [`docs/backlog/planned/0006_truncation_compaction_compliance_sweep.md`](planned/0006_truncation_compaction_compliance_sweep.md)
- [`docs/backlog/planned/0007_perfect_observability_llm_agentic_tracing.md`](planned/0007_perfect_observability_llm_agentic_tracing.md)
- [`docs/backlog/planned/0008_publish_immutable_releases_doi_lineage.md`](planned/0008_publish_immutable_releases_doi_lineage.md)
- [`docs/backlog/planned/0009_logic_self_correction_loop.md`](planned/0009_logic_self_correction_loop.md)
- [`docs/backlog/planned/0010_production_hardening_execution_sandbox.md`](planned/0010_production_hardening_execution_sandbox.md)

### Completed

- [`docs/backlog/completed/0001_backlog_and_adr_governance.md`](completed/0001_backlog_and_adr_governance.md)
- [`docs/backlog/completed/0002_doc_link_normalization.md`](completed/0002_doc_link_normalization.md)
- [`docs/backlog/completed/0012_fix_traces_after_docker.md`](completed/0012_fix_traces_after_docker.md) (legacy devnote migration)
- [`docs/backlog/completed/0013_docker_external_ollama_fix.md`](completed/0013_docker_external_ollama_fix.md) (legacy devnote migration)
- [`docs/backlog/completed/0014_abstractcore_model_download_api.md`](completed/0014_abstractcore_model_download_api.md) (legacy devnote migration)
- [`docs/backlog/completed/0015_abstractcore_v262_upgrade.md`](completed/0015_abstractcore_v262_upgrade.md) (legacy devnote migration)
- [`docs/backlog/completed/0016_docker_one_image.md`](completed/0016_docker_one_image.md) (legacy devnote migration)
- [`docs/backlog/completed/0017_dynamic_library_loading.md`](completed/0017_dynamic_library_loading.md) (legacy devnote migration)
- [`docs/backlog/completed/0018_error_enhancement_system.md`](completed/0018_error_enhancement_system.md) (legacy devnote migration)
- [`docs/backlog/completed/0019_execution_context_persistence.md`](completed/0019_execution_context_persistence.md) (legacy devnote migration)
- [`docs/backlog/completed/0020_fix_asset_display.md`](completed/0020_fix_asset_display.md) (legacy devnote migration)
- [`docs/backlog/completed/0021_fix_retry_context.md`](completed/0021_fix_retry_context.md) (legacy devnote migration)
- [`docs/backlog/completed/0022_model_download_implementation_final.md`](completed/0022_model_download_implementation_final.md) (legacy devnote migration)
- [`docs/backlog/completed/0023_model_download_test_plan.md`](completed/0023_model_download_test_plan.md) (legacy devnote migration)
- [`docs/backlog/completed/0024_semantic_extractions.md`](completed/0024_semantic_extractions.md) (legacy devnote migration)
- [`docs/backlog/completed/0025_variable_reuse_enhancement.md`](completed/0025_variable_reuse_enhancement.md) (legacy devnote migration)
- [`docs/backlog/completed/0028_async_llm_calls_smart_autosave.md`](completed/0028_async_llm_calls_smart_autosave.md) (legacy planning migration)
- [`docs/backlog/completed/0029_cell_output_display_improvement_proposal.md`](completed/0029_cell_output_display_improvement_proposal.md) (legacy planning migration)
- [`docs/backlog/completed/0030_critique_driven_retry_loop_proposal.md`](completed/0030_critique_driven_retry_loop_proposal.md) (legacy planning migration)
- [`docs/backlog/completed/0031_digital_article_implementation_plan.md`](completed/0031_digital_article_implementation_plan.md) (legacy planning migration)

### Recurrent (always active; trigger-based)

- [`docs/backlog/recurrent/0011_documentation_sync_after_backlog_completion.md`](recurrent/0011_documentation_sync_after_backlog_completion.md)

## How to work with the backlog

### 1) Create (or pick) one backlog item

- If uncertain / blocked / needs user guidance, create under [`docs/backlog/proposed/`](proposed/) using [`docs/backlog/template.md`](template.md).
- If ready to execute, create under [`docs/backlog/planned/`](planned/) using [`docs/backlog/template.md`](template.md).
- Keep the title outcome-based and small enough to complete without risky scope creep.

### 2) Think in designs, not patches

Before writing code, enumerate **at least two design options** and explicitly call out:

- Long-term consequences (operational cost, complexity, tech debt)
- Side effects (latency, reliability, backwards compatibility)
- Security implications (especially for code execution and data handling)

### 3) Tie implementation to ADRs

Architecture decisions should be recorded in `docs/adr/`.

- ADR index: [`docs/adr/README.md`](../adr/README.md)
- Default testing ladder ADR: [`docs/adr/0002-ab-testing-ladder.md`](../adr/0002-ab-testing-ladder.md)
- Truncation/compaction ADR: [`docs/adr/0003-truncation-compaction.md`](../adr/0003-truncation-compaction.md)

### 4) Implement with cleanliness constraints

Default standard:

- Clean, simple, robust, efficient code
- Prefer explicit interfaces and small units of work
- Avoid “silent” behavior (especially around truncation/compaction; see ADR)

### 5) Test using A/B/C ladder (required)

Each backlog item must include an A/B/C testing plan and should execute at least:

- **A** (mock / conceptual) and **B** (real code + real examples) **by default**
- **C** (real-world) whenever feasible

See: [`docs/adr/0002-ab-testing-ladder.md`](../adr/0002-ab-testing-ladder.md).

### 6) Fix until tests pass

Backlog items are only considered complete when:

- Acceptance criteria are met
- The item’s A/B (and C when feasible) tests are executed and documented
- The project test suite is green (when the item touches code)

### 7) Move to completed + write the Full Report

When done:

1. Move the item file from `docs/backlog/planned/` → `docs/backlog/completed/`
2. Append a **Full Report** section at the end, including:
   - What changed (files/functions)
   - Design chosen and why
   - A/B/C test evidence
   - Risks and follow-ups

### 8) Ultimate step (mandatory): run recurrent tasks

Before finally declaring the work “done”, check [`docs/backlog/recurrent/`](recurrent/) and execute any recurrent tasks whose triggers apply.

- **Minimum requirement**: run the documentation sync recurrent task:
  - [`docs/backlog/recurrent/0011_documentation_sync_after_backlog_completion.md`](recurrent/0011_documentation_sync_after_backlog_completion.md)
  - (includes running the link validator: [`tools/validate_markdown_links.py`](../../tools/validate_markdown_links.py))

## Recurrent mechanisms (when to trigger and why)

Some work recurs. For recurrent work, the triggering condition must be explicit so it is not forgotten.

### Documentation sync (prevent documentation drift)
- See recurrent backlog item:
  - [`docs/backlog/recurrent/0011_documentation_sync_after_backlog_completion.md`](recurrent/0011_documentation_sync_after_backlog_completion.md)

## Quick rules (hard constraints)

- **No truncation for data ingest/querying**: truncation is only acceptable for rendering/layout (ADR: `docs/adr/0003-truncation-compaction.md`)
- **Any truncation/compaction must be explicit and logged**:
  - `#TRUNCATION_NOTICE: <reason>` or `#COMPACTION_NOTICE: <reason>`
  - log at INFO when truncation/compaction happens

