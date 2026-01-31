# ADR 0007: Permissive-licensed dependencies and minimal dependency surface

## ADR
ADR 0007

## Title
Permissive-licensed dependencies (MIT/Apache/BSD by default) + minimal dependency surface

## Date / Time
2026-01-31T12:45:00 (local)

## Status
Accepted

## Context
Digital Article is intended for distribution and long-term maintenance. Dependency choices affect:

- legal/compliance posture (license compatibility, redistribution)
- supply-chain security and auditability
- operational reliability and attack surface
- developer velocity and maintainability

The project already has a broad feature surface (backend execution, LLM providers, export formats, frontend UI). Without explicit policy, dependency growth and license drift are likely.

The user also wants a future capability for **secure user-installed libraries** (Jupyter-like workflows) which further increases the importance of a clear dependency and licensing policy.

## Decision drivers
- **Compliance / redistribution**: prefer permissive OSS licensing; avoid copyleft surprises.
- **Security**: smaller dependency surface reduces risk and improves auditability.
- **Maintainability**: fewer dependencies means fewer breaking changes and simpler upgrades.
- **User trust**: dependency policy should be explicit, reviewable, and enforced.

## Non-goals
- This ADR does **not** fully audit the current dependency tree (Python + Node + Docker base images). That audit is a follow-up backlog item.
- This ADR does **not** implement enforcement tooling (CI checks, SBOM generation, etc.). That is a follow-up backlog item.
- This ADR does **not** implement “user-installed libraries” (that is a separate backlog item with security design).

## Decision
1. **Project-maintained dependencies MUST use permissive licenses**.
   - **Primary allowlist (preferred)**: **MIT**, **Apache-2.0**, **BSD-2-Clause**, **BSD-3-Clause**.
   - **Secondary permissive allowlist (allowed, but keep small and justify)**:
     - **ISC** (common in the JS ecosystem)
     - **PSF / Python-2.0** (common in the Python ecosystem)
   - **Default denylist**: copyleft or reciprocal licenses (e.g., **GPL**, **AGPL**, **LGPL**, **MPL**) and “unknown/unverified” licenses.
   - **Exception process**: any dependency outside the allowlists requires explicit review and documentation (backlog item + recorded decision) before adoption.

2. **We actively minimize dependency surface**.
   - New dependencies require justification (why existing deps/stdlib cannot solve it).
   - Prefer extending existing, already-approved libraries over adding new ones.
   - Remove unused dependencies and avoid overlapping libraries (duplicate functionality).

3. **User-installed libraries (future)** must comply with this policy unless we explicitly decide otherwise.
   - Any “install package” feature must enforce an allowlist and run in an isolated environment with strong security controls.

## Options considered (with consequences)
### Option A: No explicit dependency/license policy (status quo)
- **Pros**: lowest friction for contributors.
- **Cons / side effects**: license drift; hard-to-audit supply chain; dependency bloat.
- **Long-term consequences**: higher compliance risk; more frequent regressions and upgrades.

### Option B: Default allow MIT/Apache/BSD + enforce minimal dependency growth (recommended)
- **Pros**: strong compliance posture; scalable governance; reduces bloat.
- **Cons / side effects**: may require occasional exception workflows.
- **Long-term consequences**: sustainable and auditable dependency evolution.

### Option C: Strictly MIT/Apache/BSD only (no exceptions)
- **Pros**: simplest legal/compliance story.
- **Cons / side effects**: may block valuable dependencies that are still permissive but not in the set (requires careful audit of the full transitive tree).
- **Long-term consequences**: could slow development or force re-implementation of standard capabilities.

## Implications
- We need enforcement mechanisms:
  - Python dependency license scanning (runtime + dev deps)
  - Node dependency license scanning
  - optional SBOM generation for releases
- We need a documented exception mechanism (review gate) for any non-allowlisted license.
- Any future “user installs libraries” feature must be designed as a security boundary (not “just run pip”).

## Testing strategy (A/B/C)
Follow [`ADR 0002`](0002-ab-testing-ladder.md).

- **A**: define default allowlist/denylist + exception process and document it.
- **B**: implement automated license scanning and run it against the current dependency set.
- **C**: enforce in CI and validate that non-compliant deps are blocked, while exceptions are traceable/auditable.

## References (code/docs)
- Python deps:
  - [`pyproject.toml`](../../pyproject.toml)
  - [`backend/pyproject.toml`](../../backend/pyproject.toml)
- Frontend deps:
  - [`frontend/package.json`](../../frontend/package.json)
  - [`frontend/package-lock.json`](../../frontend/package-lock.json)
- Backlog governance:
  - [`docs/backlog/README.md`](../backlog/README.md)

## Follow-ups
- Backlog: enforce dependency license policy + dependency minimization guardrails  
  - [`docs/backlog/proposed/0070_dependency_license_policy_and_minimize_deps.md`](../backlog/proposed/0070_dependency_license_policy_and_minimize_deps.md)
- Backlog: audit current dependency tree for license compliance + simplify dependency footprint  
  - [`docs/backlog/proposed/0073_dependency_audit_and_simplification.md`](../backlog/proposed/0073_dependency_audit_and_simplification.md)
- Backlog: secure user-installed libraries feature (allowlisted, sandboxed)  
  - [`docs/backlog/proposed/0071_secure_user_library_installation.md`](../backlog/proposed/0071_secure_user_library_installation.md)

