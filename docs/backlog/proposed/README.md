# Proposed backlog items (needs review before execution)

This folder contains backlog items that are **not ready to execute** yet.

## When to use `proposed/`

Create an item in `proposed/` when:

- multiple major design paths are plausible and you need explicit review
- the AI needs guidance from the user to choose trade-offs
- the requirements are ambiguous or risky

## Promotion rule (proposed → planned)

An item can be moved from `proposed/` to `planned/` when:

- key open questions are answered
- ADR dependencies are clear (and any missing ADRs are added)
- the scope is tight enough to execute safely

## Naming convention (enforced)

Use: `{BACKLOG_ID}_{short_task_description}.md` (snake_case)  
Example: `0011_example_item.md`

