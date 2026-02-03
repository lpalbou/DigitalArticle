# Backlog Item (Proposed)

## Title
Role-Based Access Control (RBAC) with Three Roles: Admin, Compliance, User

## Backlog ID
0078

## Priority
- **P1 (proposed)**: Required for enterprise deployment, multi-user scenarios, and compliance features. Enables proper data isolation and audit capabilities.

## Date / Time
2026-02-01

## Short Summary
Implement role-based access control with three distinct roles:
- **User**: Can only see/edit/delete their own notebooks
- **Compliance/Manager**: Can view all notebooks (read-only), access audit logs/traces, cannot delete
- **Admin**: Full access to everything, user management

This also requires authentication infrastructure to identify users and their roles.

## Key Goals
- Define and enforce three permission levels across all API endpoints
- Integrate with external auth providers OR provide standalone auth
- Enable per-user data isolation (users see only their notebooks)
- Enable audit/compliance access to all data (read-only)
- Enable admin operations (user management, system config)
- Ensure observability/audit data is multi-tenant aware (traces attributed to a user)

## Scope

### To do
- Design auth abstraction layer (support multiple auth backends)
- Implement role model and permission checks
- Add middleware for role enforcement on all API routes
- Update notebook/cell APIs to filter by owner
- Add user management API (admin only)
- Wire TraceStore UI to compliance/admin roles only
- Attribute each TraceStore event to a user/tenant when auth is enabled (`user_id`, `username`, optional `tenant_id`)
- Add server-side config flags to enable/disable global audit querying features (compliance mode)

### NOT to do
- Full identity provider (OAuth server) - we integrate with external ones
- Complex permission matrices - keep it simple (3 roles)
- Row-level security beyond notebook ownership

## Dependencies

### Backlog dependencies (ordering)
- Should precede:
  - [`0079_reactivate_trace_viewer_for_compliance.md`](0079_reactivate_trace_viewer_for_compliance.md)
  - [`0043_user_authentication_authorization.md`](0043_user_authentication_authorization.md) (supersedes this legacy item)

### ADR dependencies (must comply)
- **All ADRs are mandatory**: [`docs/adr/README.md`](../../adr/README.md)
- **Primary ADR dependencies**:
  - [`ADR 0001`](../../adr/0001-article-first-mixed-audience.md) - Mixed audience includes compliance users
  - [`ADR 0005`](../../adr/0005-perfect-observability.md) - Traces must be accessible to compliance roles

### Points of vigilance (during execution)
- Never expose other users' notebooks to regular users
- Compliance role is strictly read-only (no writes, no deletes)
- Auth tokens must be validated on every request, not cached unsafely
- Role checks must happen server-side, never trust frontend
- TraceStore **must not** leak other users' traces in non-compliance mode
- Global trace query endpoints should be gated behind a server config + role checks

## References (source of truth)
- `backend/app/api/*.py` - All API routers need role enforcement
- `backend/app/services/notebook_service.py` - Needs owner filtering
- `backend/app/services/user_settings_service.py` - Currently single-user

## Proposal (initial; invites deeper thought)

### Context / constraints
- Digital Article currently assumes single-user (no auth, no isolation)
- Enterprise deployment requires multi-user with proper access control
- Must support both standalone auth AND external auth providers

### Design options considered (with long-term consequences)

#### Option A: Standalone JWT Auth (self-contained)
```
┌─────────────────────────────────────────────────────────────┐
│ Digital Article                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │ Auth Service │  │ User Store   │  │ Role Middleware  │  │
│  │ (JWT issuer) │  │ (JSON/SQLite)│  │ (FastAPI deps)   │  │
│  └──────────────┘  └──────────────┘  └──────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```
- **Pros**: Self-contained; works offline; no external dependencies
- **Cons**: Password management burden; not enterprise-ready; security risk
- **Long-term consequences**: Acceptable for small teams; not scalable

#### Option B: External Auth Provider Integration (OAuth2/OIDC)
```
┌─────────────────┐       ┌─────────────────────────────────┐
│ Identity Provider│       │ Digital Article                 │
│ (Keycloak, Auth0,│       │  ┌──────────────────────────┐  │
│  Azure AD, Okta) │◄─────►│  │ Auth Middleware          │  │
│                  │       │  │ (validate token, extract │  │
│                  │       │  │  roles from claims)      │  │
└─────────────────┘       │  └──────────────────────────┘  │
                          │  ┌──────────────────────────┐  │
                          │  │ Role Enforcement         │  │
                          │  │ (per-endpoint checks)    │  │
                          │  └──────────────────────────┘  │
                          └─────────────────────────────────┘
```
- **Pros**: Enterprise-ready; SSO; password management delegated; proven security
- **Cons**: Requires external infra; more complex setup
- **Long-term consequences**: Best for enterprise; industry standard

#### Option C: Hybrid (Recommended)
```
┌─────────────────────────────────────────────────────────────┐
│ Digital Article                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Auth Abstraction Layer                               │  │
│  │  - AuthProvider interface                            │  │
│  │  - get_current_user() → User(id, role, email)       │  │
│  └──────────────────────────────────────────────────────┘  │
│           │                    │                    │       │
│           ▼                    ▼                    ▼       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │ NoAuth       │  │ SimpleAuth   │  │ OIDCAuth         │  │
│  │ (dev mode)   │  │ (standalone) │  │ (enterprise)     │  │
│  │ → admin user │  │ → local JWT  │  │ → external IdP   │  │
│  └──────────────┘  └──────────────┘  └──────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```
- **Pros**: Flexible; works in dev (no auth), standalone, and enterprise
- **Cons**: More code paths; need to test all backends
- **Long-term consequences**: Best balance; can evolve with deployment needs

### Recommended approach (current best choice)

**Option C (Hybrid)** with these components:

1. **AuthProvider Protocol**
```python
class AuthProvider(Protocol):
    async def get_current_user(self, request: Request) -> User: ...
    async def validate_token(self, token: str) -> User | None: ...

@dataclass
class User:
    id: str
    email: str
    role: Role  # admin | compliance | user
    display_name: str
```

2. **Role Enum**
```python
class Role(str, Enum):
    ADMIN = "admin"           # Full access
    COMPLIANCE = "compliance" # Read-all, write-none
    USER = "user"             # Own notebooks only
```

3. **Permission Decorators**
```python
@require_role(Role.ADMIN)
async def delete_user(...): ...

@require_role(Role.COMPLIANCE, Role.ADMIN)
async def get_all_traces(...): ...

@require_owner_or_role(Role.ADMIN)
async def delete_notebook(...): ...
```

4. **Configuration**
```yaml
# config.json or env vars
auth:
  provider: "none" | "simple" | "oidc"
  oidc:
    issuer: "https://auth.company.com"
    client_id: "digital-article"
    role_claim: "roles"  # Where to find roles in token

# Observability / audit gates (server-side)
observability:
  trace_store_enabled: true                 # keep JSONL traces
  global_trace_query_enabled: false         # default off; enable for compliance deployments
  require_auth_for_trace_queries: true      # reject anonymous global queries
```

### Testing plan (A/B/C)
> Follow [`docs/adr/0002-ab-testing-ladder.md`](../../adr/0002-ab-testing-ladder.md).

- **A (mock / conceptual)**:
  - Define User, Role, AuthProvider models
  - Mock auth middleware; verify role checks block/allow correctly
- **B (real code + real examples)**:
  - Implement NoAuth (dev) and SimpleAuth (standalone)
  - Test notebook isolation: user A cannot see user B's notebooks
  - Test compliance can view but not delete
- **C (real-world / production-like)**:
  - Test with Keycloak or Auth0 in Docker
  - Verify SSO flow end-to-end
  - Penetration test role boundaries

## Acceptance Criteria (must be fully satisfied)
- [ ] Three roles (admin, compliance, user) are enforced on all API endpoints
- [ ] Users can only see/edit/delete their own notebooks
- [ ] Compliance can view all notebooks and traces but cannot modify
- [ ] Admin can do everything including user management
- [ ] At least two auth providers work: NoAuth (dev) and one real (OIDC or SimpleAuth)
- [ ] Auth is configurable via config.json or environment variables

## Implementation Notes (fill during execution)
TBD

## Full Report (fill only when moving to completed/)
TBD
