# Multi-Institution Implementation - Improvement Plan

## Critical Issues (Security & Data Isolation)

### 🔴 CRITICAL: Admin routes missing institution_id filtering
**File:** `backend/src/priotag/api/routes/admin.py`

**Problem:** Admin endpoints query priorities, users, and other data WITHOUT filtering by `institution_id`. This means:
- Institution admins can see ALL users across ALL institutions
- Institution admins can see ALL priorities across ALL institutions
- Data isolation is BROKEN at the API level

**Impact:** HIGH - This is a critical security vulnerability

**Fix Required:**
```python
# Current (BROKEN):
params={"filter": f"manual = false && month='{month}'"}

# Should be (for institution_admin):
if session.role == "institution_admin":
    params={"filter": f"manual = false && month='{month}' && institution_id='{session.institution_id}'"}
else:  # super_admin
    params={"filter": f"manual = false && month='{month}'"}
```

**Affected endpoints:**
- `/admin/stats/{month}` - Line 136
- `/admin/manual-entries/{month}` - Line 403
- `/admin/user/{user_id}` - Line 229 (should verify user belongs to admin's institution)
- `/admin/delete-user/{user_id}` - Line 669 (should verify user belongs to admin's institution)
- All other admin endpoints that query users/priorities/vacation_days

### 🟡 MEDIUM: Super admin magic word update bug
**File:** `backend/src/priotag/api/routes/institutions.py:279`

**Problem:** When a super_admin tries to update a magic word, the code uses `session.institution_id` which is `None` for super admins.

**Current code:**
```python
institution = await InstitutionService.update_magic_word(
    session.institution_id,  # ❌ This is None for super_admin!
    data.magic_word,
    auth_token=token
)
```

**Fix Required:**
Add `institution_id` parameter to the request or endpoint path:
```python
@router.patch("/admin/institution/{institution_id}/magic-word")
async def update_institution_magic_word(
    institution_id: str,  # ✓ Explicit parameter
    data: UpdateMagicWordRequest,
    session: SessionInfo = Depends(require_institution_admin),
    token: str = Depends(get_current_token),
):
    # For institution_admin, verify they own the institution
    if session.role == "institution_admin" and session.institution_id != institution_id:
        raise HTTPException(status_code=403, detail="Cannot modify other institutions")

    institution = await InstitutionService.update_magic_word(
        institution_id, data.magic_word, auth_token=token
    )
```

## High Priority Improvements

### 🟠 Add institution_id validation middleware

Create a middleware that automatically enforces institution_id filtering for institution admins:

**File to create:** `backend/src/priotag/middleware/institution_isolation.py`

```python
async def enforce_institution_isolation(request: Request, call_next):
    """
    Middleware to enforce institution data isolation.

    For institution_admin users, automatically adds institution_id filter
    to PocketBase queries.
    """
    # Implementation here
    pass
```

### 🟠 Add database-level enforcement

While PocketBase API rules exist, we should verify they're comprehensive:

**File to check:** `pocketbase/pb_migrations/*_updated_*.js`

Ensure ALL collections with `institution_id` have proper API rules:
- Users can only see users from their institution
- Admins can only see data from their institution
- Super admins can see everything

### 🟠 Add institution context to all admin queries

**Files to update:**
- `backend/src/priotag/api/routes/admin.py` - All endpoints
- `backend/src/priotag/api/routes/priorities.py` - If any admin functionality
- `backend/src/priotag/api/routes/vacation_days.py` - If any admin functionality

**Pattern:**
```python
def build_filter(session: SessionInfo, base_filter: str) -> str:
    """Build filter with institution isolation."""
    if session.role == "super_admin":
        return base_filter
    elif session.institution_id:
        return f"{base_filter} && institution_id='{session.institution_id}'"
    else:
        raise HTTPException(400, "User not associated with institution")
```

## Medium Priority Improvements

### 🟡 Frontend: Add institution name to user profile

**File:** `frontend/src/lib/components/UserProfile.svelte` (or similar)

Show which institution the user belongs to in their profile.

### 🟡 Add institution switching for super admins

**File:** `frontend/src/lib/admin/InstitutionSwitcher.svelte` (new)

Allow super admins to switch context between institutions for management.

### 🟡 Add institution statistics endpoint

**File:** `backend/src/priotag/api/routes/institutions.py`

Add endpoint for institution admins to see their institution's statistics:
```python
@router.get("/admin/institution/stats")
async def get_institution_stats(
    session: SessionInfo = Depends(require_institution_admin),
):
    """Get statistics for the current institution."""
    # Return user count, active users, etc.
```

### 🟡 Add audit logging for institution changes

**File:** `backend/src/priotag/models/audit_log.py` (new)

Log when:
- Institutions are created/updated
- Magic words are changed
- Users are moved between institutions
- Admins are elevated

## Low Priority Improvements

### 🟢 Add institution logo support

**File:** `pocketbase/pb_migrations/*_add_institution_logo.js` (new)

Add `logo_url` field to institutions collection for branding.

### 🟢 Add institution-specific settings

**File:** `backend/src/priotag/models/institution.py`

Define proper structure for `settings` field:
```python
class InstitutionSettings(BaseModel):
    theme_color: Optional[str] = None
    max_users: Optional[int] = None
    features_enabled: dict[str, bool] = {}
```

### 🟢 Add bulk user import per institution

**File:** `backend/src/priotag/scripts/import_users.py`

Script to import users CSV with institution assignment.

### 🟢 Add institution-specific email templates

Allow institutions to customize registration emails, password resets, etc.

## Testing Improvements

### ✅ Add security tests

**File:** `backend/tests/integration/test_institution_isolation_security.py` (new)

Test that:
- Institution admins CANNOT access other institutions' data
- Institution admins CANNOT modify other institutions
- Cross-institution data leakage is prevented
- Super admins CAN access all institutions

### ✅ Add performance tests

Test with multiple institutions (10+) to ensure queries are efficient.

## Documentation Improvements

### 📝 Update MULTI_INSTITUTION_MIGRATION.md

Add section on:
- Security model and data isolation
- How to verify isolation is working
- Common pitfalls when adding new endpoints

### 📝 Create SECURITY.md

Document:
- Multi-institution security model
- Permission hierarchy
- Data isolation guarantees
- How to add new endpoints securely

### 📝 Update API documentation

Add OpenAPI tags and examples for:
- Institution selection during registration
- Institution admin vs super admin permissions
- Multi-institution data filtering

## Migration Script Improvements

### 🔧 Add validation to migrate_to_multi_institution.py

**File:** `backend/src/priotag/scripts/migrate_to_multi_institution.py`

Add checks:
- Verify all users are assigned to an institution
- Verify all priorities are assigned to an institution
- Verify no orphaned data
- Create rollback script

### 🔧 Add institution merge script

**File:** `backend/src/priotag/scripts/merge_institutions.py` (new)

For merging two institutions (migrate users, priorities, etc.).

## Summary

**Critical (Fix Immediately):**
1. ⚠️  Add institution_id filtering to ALL admin endpoints
2. ⚠️  Fix super admin magic word update endpoint

**High Priority:**
3. Add institution isolation middleware
4. Verify and strengthen PocketBase API rules
5. Add security tests for data isolation

**Medium Priority:**
6. Frontend institution display
7. Institution statistics
8. Audit logging

**Low Priority:**
9. Institution branding
10. Bulk user import
11. Email customization

## Estimated Effort

- **Critical fixes:** 4-6 hours
- **High priority:** 8-12 hours
- **Medium priority:** 12-16 hours
- **Low priority:** 16-24 hours

**Total:** ~40-58 hours for complete implementation
