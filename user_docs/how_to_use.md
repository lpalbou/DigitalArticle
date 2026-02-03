# How to use Digital Article (quick, actionable)

## Create a new article

- Click **New**
- Write a prompt describing your goal (be explicit about deliverables: “display a table”, “save a CSV”, “plot a histogram”).

## Run a cell

- Click **Run / Re-run** on the cell
- Watch **Execution Details** if something fails (traceback + logs + traces).

## Inspect what happened

- **Prompt**: the intent you provided
- **Code**: the exact code that ran (you can edit it)
- **Results**: tables/figures/files produced by execution
- **Traces**: LLM prompts/responses and timing (for audit/debugging)

## Iterate safely

- If you change an earlier cell, downstream cells may become **stale** (re-run them).
- Prefer small changes: one prompt/cell should do one thing.

## Use the reviewer (optional)

- Reviewer is for methodological critique and improvements.
- If you only need *correctness*, keep reviewer strictness low and focus on deliverables.

