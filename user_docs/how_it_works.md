# How it works (for users)

Digital Article is designed to keep **intent**, **code**, **results**, and **methodology** connected.

## What happens when you run a cell

- The system uses your **prompt** (intent) to generate or improve **code**.
- The code is executed in the article’s environment.
- The UI shows structured **results** (tables/figures/files).
- A **methodology** section may be generated to explain what was done.

## Two self-correction loops (bounded and observable)

Digital Article can run two bounded loops to help you converge:

1. **Execution correction (syntax/runtime)**  
   If code fails to run, the system captures the error and attempts minimal fixes.

2. **Logic validation / correction (correctness vs intent)**  
   If code runs but doesn’t satisfy the prompt, the system can suggest or apply minimal corrections.

These loops are **bounded** (limited retries) and **observable** (you can inspect attempts and traces).

## Traces (why they matter)

Traces let you inspect what the AI did:

- The exact prompts sent to the model
- The model’s response
- Timing and settings

This makes the workflow auditable and easier to debug.

