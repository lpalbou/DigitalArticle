# Backlog Item (Proposed; decomposed from legacy ROADMAP)

## Title
Cost Management & Monitoring

## Backlog ID
0064

## Priority
- **P2 (proposed)**: decomposed from legacy `ROADMAP.md` (Phase 4: Enterprise & Scale (2027+), Medium Priority). Requires review before promotion to `planned/`.

## Date / Time
2026-01-31 (decomposed from legacy roadmap; needs re-estimation)

## Short Summary
This backlog item was decomposed from legacy `ROADMAP.md` section **4.6**. The legacy roadmap is archived at [`docs/backlog/completed/0032_legacy_roadmap.md`](../completed/0032_legacy_roadmap.md).

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

## Full Report (legacy ROADMAP extract: 4.6)

#### 4.6 Cost Management & Monitoring
**Status**: 🔴 Not Started
**Complexity**: Medium
**Impact**: Medium (for cloud deployments)

**Tasks**:
- [ ] Usage metrics (API calls, LLM tokens, storage)
- [ ] Cost attribution (per user, per team)
- [ ] Quota management
- [ ] Prometheus/Grafana dashboards
- [ ] Alerting (PagerDuty, Opsgenie)

**User Story**: *"As an admin, I need visibility into system usage and costs"*

---

## Community & Ecosystem

### Documentation
- [ ] Video tutorials (YouTube series)
- [ ] Interactive playground (try without installing)
- [ ] Example notebook gallery
- [ ] API reference (auto-generated from OpenAPI)
- [ ] Developer guide for contributors

### Research & Publications
- [ ] Peer-reviewed paper describing the system
- [ ] Case studies from early adopters
- [ ] User studies (usability, effectiveness)
- [ ] Benchmark comparisons with Jupyter/other tools

### Community Building
- [ ] Discord/Slack community
- [ ] Monthly office hours
- [ ] Conference presentations (JupyterCon, SciPy, etc.)
- [ ] Hackathons and challenges
- [ ] Ambassador program (active community members)

---

## Technical Debt & Refactoring

### Known Issues to Address

1. **Code Execution Safety**: Currently executes in same process as server
   - **Fix**: Containerized execution (Phase 3.2)

2. **JSON File Storage**: Not scalable beyond ~1000 notebooks
   - **Fix**: Database migration (Phase 2.2)

3. **No LLM Concurrency**: Single model instance
   - **Fix**: Job queue system (Phase 3.2)

4. **Limited Test Coverage**: <20% currently
   - **Fix**: Comprehensive testing (Phase 1.6)

5. **Hardcoded Configurations**: LLM provider in code
   - **Fix**: Environment-based configuration

6. **No Observability**: Difficult to debug production issues
   - **Fix**: Structured logging, tracing (Phase 4.5)

---

## Success Metrics

How we'll measure progress:

### User Adoption
- **Beta Goal**: 100 active users by Q2 2025
- **Stable Goal**: 1,000 active users by Q4 2025
- **Enterprise Goal**: 10 organizations by 2026

### User Satisfaction
- **Prompt Success Rate**: >80% of prompts generate working code
- **Auto-Retry Success**: >60% of errors fixed automatically
- **Net Promoter Score**: >40

### Performance
- **Time to First Result**: <10s (prompt → executed result)
- **LLM Response Time**: <5s for code generation
- **Uptime**: >99.5% for production deployments

### Scientific Impact
- **Publications**: 5+ papers citing Digital Article by 2026
- **Methodology Quality**: User survey rating >4/5 for publication-readiness
- **Time Savings**: 50% reduction in analysis-to-manuscript time

### Communication & Exploration
- **Article Exploration Rate**: >30% of published articles actively explored by readers
- **Follow-up Questions**: Average 10+ meaningful questions asked per published article
- **Knowledge Building**: >20% of articles spawn derivative analyses or replications
- **Community Engagement**: >60% of published articles receive community feedback or citations

---

## How to Contribute

Want to help shape the roadmap?

1. **Prioritization**: Comment on GitHub Issues with your use case
2. **Feature Requests**: Open new issues tagged "enhancement"
3. **Implementation**: Pick an issue and submit a PR
4. **Feedback**: Try beta features and report bugs
5. **Evangelism**: Share your Digital Articles and workflows

**Roadmap Reviews**: We'll update this roadmap quarterly based on user feedback and technical developments.

---

## Disclaimer

This roadmap is subject to change based on:
- User feedback and requests
- Technical feasibility discoveries
- Resource availability
- Emerging LLM capabilities
- Community contributions

Timelines are estimates; actual delivery may vary. Features may be added, removed, or reprioritized.

**Current Focus**: Phase 1 (Stabilization & Core Improvements)

For questions or suggestions, open an issue or discussion on GitHub.



Others
- How to see the existing notebooks
- Export
   - fix export json
   - improve export pdf
- Code
   - should be able to edit it
- Code execution
   - should be able to cancel an execution
   - How to force a re-run of a cell (and invalidate the next ones)
- Variables in context vs files in context
   - LLM might confuses a file and a variable (when trying to access it)
   - files : do we even need the subfolder data/ ? especially as it creates potential issues ?
- if the X retries failed, it should output a custom error panel
   - human readable message on what was the problem
   - error stack
   - what was attempted ?
   - CRITICAL : make sure that each attempt becomes part of the context, so that the AI doesn’t try the same solution twice
- Article Abstract : button to generate it
    - take into account (prompt, code, methodology, result) of all cells (that’s potentially a lot ?)
        - might need to do it sequentially
- Rules : how a user could give specific rules beyond the cells
    - eg system prompt like rules

"""5 - scientific validity : this is really the main concern, but that's why users have access to the code, so that a non-technical expert can share its digital article to a technical expert who can validate or correct the analysis"""
=> we need an ability to put side note / comments

- what about scientific references as well ?

- need to set and keep a seed

- 6 - templates for common analysis is a good idea, but for later

- invite a colleague to review (especially non technical -> technical)

- be careful, a non VL model can't directly use the plot. but they can use the underlying data.

- include a "plan" tab ? (that's an expert mode, i don't want to clutter the UI)

- have better "claude skills" like for different scenarios; eg single cell, spatial transcriptomics analysis

- give model ability to ask refining questions (when needed)

- starting point : "I am interested in xxx" => would create a bibliography that could help further guide the LLM

- create R environment

- retry with comments

