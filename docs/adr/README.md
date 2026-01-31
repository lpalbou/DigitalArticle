# ADRs (Architecture Decision Records)

This directory contains **architecture decisions** for Digital Article.

## Why ADRs

ADRs reduce “tribal knowledge” and prevent repeated debate by capturing:

- The problem context
- The chosen decision
- Alternatives considered (with long-term consequences)
- Implications and testing approach

## Process

1. Draft an ADR using [`docs/adr/template.md`](template.md)
2. Link the ADR from relevant backlog items in [`docs/backlog/planned/`](../backlog/planned/)
3. When accepted, set ADR **Status** to `Accepted`
4. When replaced, create a new ADR and mark the old one `Superseded` (never delete)

## Index

- [`0001-article-first-mixed-audience.md`](0001-article-first-mixed-audience.md) — mission and notebook structure (intent↔code↔results↔methodology)
- [`0002-ab-testing-ladder.md`](0002-ab-testing-ladder.md) — A/B/C testing ladder requirements
- [`0003-truncation-compaction.md`](0003-truncation-compaction.md) — truncation/compaction rules + mandatory code markers + INFO logs
- [`0004-recursive-self-correction-loop.md`](0004-recursive-self-correction-loop.md) — execution self-correction + logic/persona self-correction loop
- [`0005-perfect-observability.md`](0005-perfect-observability.md) — end-to-end tracing for LLM + agentic calls (ethics + compliance)
- [`0006-publish-immutable-releases-doi-lineage.md`](0006-publish-immutable-releases-doi-lineage.md) — publish immutable releases with DOI + lineage/derivation
- [`0007-permissive-licenses-and-minimal-dependencies.md`](0007-permissive-licenses-and-minimal-dependencies.md) — permissive OSS dependency policy + minimize dependency surface
- [`0008-linting-and-quality-gates.md`](0008-linting-and-quality-gates.md) — mandatory lint/typecheck/test gates per backlog completion

