# Digital Article — overview

Digital Article turns computational work into a **living, auditable article**: you start from **intent**, the system produces **executable evidence** and **communication**, and every step can be **reviewed** (code, results, traces).

## The core loop

- **Intent**: what you ask for (prompt)
- **How**: the generated/edited code that implements it
- **What**: the resulting tables/figures/files/logs
- **Communication**: the methodology/narrative describing what was done

Digital Article couples these four parts so a reader can verify *what happened and why*.

## What you can do in the UI (fast mental model)

- **Write a prompt**: describe the outcome you want (tables, figures, exports).
- **Run**: the system generates code, executes it, and shows structured outputs.
- **Review**: inspect code + traces and optionally run the reviewer.
- **Iterate**: edit prompt/code and re-run. The article remains coherent and traceable.

## Evidence and trust

Digital Article is designed so a “good” result is not just plausible text:

- Results are **computed** (tables/figures/files) and are visible in the article.
- Code is always available for technical review and reproducibility.
- Traces make LLM behavior inspectable (prompts, responses, timing, settings).

