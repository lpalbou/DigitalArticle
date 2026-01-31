# Backlog Item

## Title
Normalize documentation file references into clickable markdown links (starting with `docs/overview.md`)

## Backlog ID
0002

## Date / Time
2026-01-31T07:55:00 (local)

## Short Summary
In `docs/overview.md` and other documentation files, many references to local files were shown as plain text or inline code. Converted key hub docs and indexes into **clickable markdown links** and validated that all relative links resolve to existing files.

## Key Goals
- Make cross-references within docs consistently clickable.
- Prefer relative links that work in GitHub and local markdown viewers.
- Keep link text readable while being clickable.

## Scope

### To do
- Sweep `docs/overview.md` and the most common “hub” docs (`README.md`, `docs/getting-started.md`, backlog/ADR indexes).
- Replace non-clickable local file references with markdown links.
- Add a simple link validation check (relative paths resolve to existing files).

### NOT to do
- Do not rewrite content semantics; this is a **format/navigation** pass only.
- Do not change external URLs.

## Proposal (initial; invites deeper thought)

### Context / constraints
- The documentation is meant to be navigated as a graph; non-clickable file references break that.
- Relative links must remain stable even if rendered in GitHub.

### Design options considered (with long-term consequences)
#### Option A: Keep inline code paths only (status quo)
- **Pros**: minimal editing; consistent monospace styling
- **Cons / side effects**: readers can’t click; navigation cost stays high
- **Long-term consequences**: docs are “present but not usable”

#### Option B: Use clickable links for docs and code paths (recommended)
- **Pros**: frictionless navigation; easier onboarding; supports “documentation as graph”
- **Cons / side effects**: needs discipline to keep links correct; slightly more verbose markup
- **Long-term consequences**: docs become a durable, navigable knowledge system

#### Option C: Link only docs/*.md, keep code paths as inline code
- **Pros**: less editing; avoids linking to code lines
- **Cons / side effects**: still blocks “deep navigation” into source of truth for engineers
- **Long-term consequences**: limits the value of “code as truth” in docs

### Recommended approach (current best choice)
Option B: link documentation pages (and key referenced code files when cited as “source of truth”).

### Testing plan (A/B/C)
> Follow the project’s testing ADR: `docs/adr/0002-ab-testing-ladder.md`.

- **A (mock / conceptual)**:
  - Define the conversion rule and apply it to `docs/overview.md` as the reference example.
- **B (real code + real examples)**:
  - Run a local link validator across docs to ensure relative links resolve to existing files.
- **C (real-world / production-like)**:
  - Manual click-through in GitHub UI for the “hub” pages (README, overview, architecture).

## Acceptance Criteria (must be fully satisfied)
- `docs/overview.md` uses clickable links for the files it lists.
- `docs/backlog/README.md` and `docs/adr/README.md` indexes use clickable links.
- A link validator confirms all **relative** markdown links in docs resolve to existing files.

## Implementation Notes (fill during execution)
- Updated hub docs to use markdown links rather than non-clickable file citations.
- Added/ran a local validator to ensure relative markdown links resolve to existing files.

## Full Report (fill only when moving to completed/)

### What changed

- Converted file citations to markdown links in these hub/index files:
  - `docs/overview.md`
  - `docs/getting-started.md` (“Next docs” section)
  - `docs/backlog/README.md`
  - `docs/adr/README.md`
  - `docs/data_flow.md` (top-level map reference)
  - `docs/troubleshooting.md` (getting-started + architecture references)
  - `docs/knowledge_base.md` (linked `backend/app/main.py`)

### Broken links fixed (found via validator)

- `README.md` referenced `LICENSE` but there is **no** license file in the repo.
  - Fix (at the time): made the statement truthful (“License: TBD”) instead of linking to a non-existent file.
  - Note: the repository later added an MIT `LICENSE` file and `README.md` now links to it.
- `docs/backlog/completed/0014_abstractcore_model_download_api.md` referenced a non-existent backlog file.
  - Fix: pointed to current implementation references: `backend/app/api/models.py` and `docs/troubleshooting.md`.

### A/B/C test evidence

- **A**: Applied the linking rule to the doc index (`docs/overview.md`) as the reference example.
- **B**: Ran a local link validator that checks **relative** markdown links in `README.md` and `docs/*.md` resolve to existing files.
  - Script: [`tools/validate_markdown_links.py`](../../../tools/validate_markdown_links.py)
  - Result: **PASS** (“OK: all relative markdown links resolve to existing files.”)
- **C**: Manual click-through in GitHub/UI recommended for the hub pages; no runtime environment required.

### Side effects / long-term consequences

- Positive: documentation is now much easier to navigate; broken links are caught early.
- Ongoing requirement: whenever adding new doc references, prefer links and run the validator periodically (or wire it into CI later).

