# Backlog Item (Proposed)

## Title
Reactivate Global Trace Viewer for Compliance/Admin Roles

## Backlog ID
0079

## Priority
- **P2 (proposed)**: Depends on RBAC (0078). Provides audit/compliance visibility once roles are in place.

## Date / Time
2026-02-01

## Short Summary
Reactivate the global TraceViewerModal for users with **compliance** or **admin** roles. Regular users should not see this feature (they use the per-cell Execution Details modal). The global trace viewer enables cross-notebook audit visibility.

This feature should also be **server-config gated** so it can be turned off entirely in non-compliance deployments.

## Key Goals
- Show TraceViewer icon in header only for compliance/admin roles
- Enable compliance officers to audit all LLM interactions across all notebooks
- Preserve the clean UI for regular users (no clutter)
- Ensure cross-user trace browsing is only possible when both:
  - server config enables global trace queries, and
  - user role is compliance/admin

## Scope

### To do
- Add role check in Header.tsx to conditionally show Activity icon
- Update TraceViewerModal to show cross-user traces (for compliance/admin)
- Add "user" filter to trace queries (compliance can filter by user)
- Gate global trace API endpoints behind a server flag (default off)

### NOT to do
- Change the per-cell Execution Details modal (remains for all users)
- Add new trace storage - use existing TraceStore backend

## Dependencies

### Backlog dependencies (ordering)
- **Requires**:
  - [`0078_role_based_access_control.md`](0078_role_based_access_control.md) - Must have roles first

### ADR dependencies (must comply)
- **All ADRs are mandatory**: [`docs/adr/README.md`](../../adr/README.md)
- **Primary ADR dependencies**:
  - [`ADR 0005`](../../adr/0005-perfect-observability.md) - This enables the compliance use case

### Points of vigilance (during execution)
- Role check must happen both frontend (hide icon) AND backend (API rejects unauthorized)
- Compliance role should see all traces but with user attribution
- Never show admin-only features to compliance
- Enforce server-side config gating: UI hiding is not sufficient

## References (source of truth)
- `frontend/src/components/Header.tsx` - Where to add role check
- `frontend/src/components/TraceViewerModal.tsx` - Already built, just needs role gate
- `backend/app/api/traces.py` - May need role enforcement
- `backend/app/services/trace_store.py` - Already handles persistence

## Proposal (initial; invites deeper thought)

### Context / constraints
- TraceViewerModal was built but removed from header to avoid clutter for regular users
- Once RBAC is in place, compliance/admin users need this cross-notebook audit view
- Regular users continue to use per-cell Execution Details (which is better for their use case)

### Recommended approach (current best choice)

1. **Header.tsx**: Conditionally render Activity icon
```tsx
const { user } = useAuth()  // From RBAC context

{(user.role === 'admin' || user.role === 'compliance') && (
  <button onClick={() => setShowTraceViewer(true)} title="Audit Traces">
    <Activity />
  </button>
)}
```

2. **TraceViewerModal**: Add user filter for compliance
```tsx
// Show "Filter by user" dropdown for compliance/admin
{(user.role === 'admin' || user.role === 'compliance') && (
  <UserFilter onSelect={setFilterUser} />
)}
```

3. **Backend /api/traces/***: Add role enforcement
```python
@router.get("/traces/query")
@require_role(Role.COMPLIANCE, Role.ADMIN)
async def query_traces(...):
    # Only compliance/admin can query all traces
    ...
```

### Testing plan (A/B/C)

- **A (mock / conceptual)**:
  - Mock auth context; verify icon visibility based on role
- **B (real code + real examples)**:
  - Test with SimpleAuth: admin sees icon, user doesn't
  - Test API rejects trace queries from regular users
- **C (real-world / production-like)**:
  - Test with OIDC integration
  - Verify audit log shows all user activity for compliance

## Acceptance Criteria (must be fully satisfied)
- [ ] Regular users do not see the Trace Viewer icon
- [ ] Compliance users see the icon and can view all traces
- [ ] Admin users see the icon and can view all traces
- [ ] API endpoints for traces reject requests from regular users
- [ ] Compliance can filter traces by user

## Implementation Notes (fill during execution)
TBD

## Full Report (fill only when moving to completed/)
TBD
