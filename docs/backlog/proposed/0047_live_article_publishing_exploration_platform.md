# Backlog Item (Proposed; decomposed from legacy ROADMAP)

## Title
Live Article Publishing & Exploration Platform

## Backlog ID
0047

## Priority
- **P2 (proposed)**: decomposed from legacy `ROADMAP.md` (Phase 2: Multi-User & Collaboration (Q3-Q4 2025), High Priority). Requires review before promotion to `planned/`.

## Date / Time
2026-01-31 (decomposed from legacy roadmap; needs re-estimation)

## Short Summary
This backlog item was decomposed from legacy `ROADMAP.md` section **2.5**. The legacy roadmap is archived at [`docs/backlog/completed/0032_legacy_roadmap.md`](../completed/0032_legacy_roadmap.md).

## Key Goals
- Turn a legacy roadmap epic into a backlog item that can be reviewed, prioritized, and executed.
- Clarify dependencies and ADR constraints before implementation.

## Scope

### To do
- Review the legacy epic details below.
- Decide whether to:
  - keep as-is and promote to `planned/`,
  - split into smaller backlog items, or
  - deprecate if already implemented or no longer aligned with mission.

### NOT to do
- Do not treat this legacy epic text as authoritative implementation documentation.

## Dependencies

### Backlog dependencies (ordering)
- **None** (to be determined during review)

### ADR dependencies (must comply)
- **All ADRs are mandatory**: [`docs/adr/README.md`](../../adr/README.md)
- **Primary ADR dependencies**:
- [`ADR 0001`](../../adr/0001-article-first-mixed-audience.md)
- [`ADR 0002`](../../adr/0002-ab-testing-ladder.md)
- [`ADR 0006`](../../adr/0006-publish-immutable-releases-doi-lineage.md)

### Points of vigilance (during execution)
- This is legacy roadmap material: verify against current code and docs before acting.
- Avoid duplicating existing backlog items; merge/supersede where appropriate.

## References (source of truth)
- Legacy roadmap archive: [`docs/backlog/completed/0032_legacy_roadmap.md`](../completed/0032_legacy_roadmap.md)
- Canonical planning: [`docs/backlog/README.md`](../README.md)

## Proposal (initial; invites deeper thought)

### Context / constraints
- This epic comes from an outdated roadmap (Jan 2025). It must be reconciled with the current codebase.

### Recommended approach (current best choice)
- Treat this file as a starting point for review; if accepted, split into small, executable items.

### Testing plan (A/B/C)
> Follow [`docs/adr/0002-ab-testing-ladder.md`](../../adr/0002-ab-testing-ladder.md).

- **A (mock / conceptual)**:
  - clarify requirements and constraints; enumerate design options
- **B (real code + real examples)**:
  - implement the smallest safe increment; add tests
- **C (real-world / production-like)**:
  - validate in realistic notebooks/Docker scenarios

## Acceptance Criteria (must be fully satisfied)
- This roadmap epic is either:
  - promoted to a concrete `planned/` backlog item (or split into planned items), or
  - explicitly deprecated with rationale.

## Full Report (legacy ROADMAP extract: 2.5)

#### 2.5 Live Article Publishing & Exploration Platform
**Status**: 🔴 Not Started
**Complexity**: High
**Impact**: Very High

**Tasks**:
- [ ] Create public article gallery with search and filtering
- [ ] Implement "Explore this Article" interface for published works
- [ ] Add article forking and derivative tracking (citation network)
- [ ] Enable persistent URLs for specific explorations and parameter sets
- [ ] Build community rating and review system for published articles
- [ ] Add "Build Upon This" workflow for creating derivative analyses

**User Story**: *"I want to publish my digital article so others can explore it, ask questions, and build upon my work, creating a living network of scientific knowledge"*

### Medium Priority

