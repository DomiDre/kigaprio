# Security Audit Report #3 - Filter Injection Vulnerabilities
**Date:** 2025-11-18
**Status:** MEDIUM severity filter injection vulnerabilities found

## Executive Summary
After completing all CRITICAL security fixes from audits #1 and #2, a third comprehensive audit has revealed **4 MEDIUM severity filter injection vulnerabilities**. While these vulnerabilities are not as severe as the previous cross-institution data leaks, they could still allow attackers to bypass filters and potentially access unauthorized data.

## Filter Injection Vulnerabilities (Severity: MEDIUM)

### Background: What is Filter Injection?
PocketBase uses filter strings to query the database. These filters are similar to SQL WHERE clauses. If user input is directly interpolated into filter strings without validation, an attacker can inject malicious filter logic to:
- Bypass security checks
- Access unauthorized data
- Cause unexpected query behavior

**Example Attack:**
```python
# Vulnerable code:
filter = f'username="{user_id}"'

# If user_id = 'test" || userId="victim_id'
# The filter becomes:
# username="test" || userId="victim_id"
# This returns BOTH user "test" AND user "victim_id"!
```

---

### 1. MEDIUM: Filter Injection in Manual Entry Delete
**Location:** `backend/src/priotag/api/routes/admin.py:640`
**Affected Endpoint:** `DELETE /api/v1/admin/manual-entry/{month}/{identifier}`

**Vulnerability:**
Both `month` and `identifier` path parameters are directly interpolated into the filter string without sanitization or validation.

**Vulnerable Code:**
```python
@router.delete("/manual-entry/{month}/{identifier}")
async def delete_manual_entry(
    month: str,  # ← No validation!
    identifier: str,  # ← No validation!
    token: str = Depends(get_current_token),
    session: SessionInfo = Depends(require_admin),
):
    async with httpx.AsyncClient() as client:
        # Find the entry with institution filtering
        base_filter = f'manual = true && month="{month}" && identifier="{identifier}"'
        filter_str = build_institution_filter(session, base_filter)
```

**Impact:**
- Attacker could craft malicious `month` or `identifier` values to bypass filters
- Could delete unintended records
- Medium severity because:
  - ✓ Requires admin access
  - ✓ Still has institution filtering protection
  - ✗ But could bypass month/identifier logic

**Attack Example:**
```bash
DELETE /api/v1/admin/manual-entry/2025-01" || manual = false && userId="victim"/test
# This could match priorities that are NOT manual entries
```

**Fix Required:**
1. Validate `month` using `validate_month_format_and_range()`
2. Sanitize `identifier` - only allow alphanumeric, hyphens, underscores
3. Or use parameterized queries if PocketBase supports them

---

### 2. MEDIUM: Filter Injection in Manual Priority Create
**Location:** `backend/src/priotag/api/routes/admin.py:446`
**Affected Endpoint:** `POST /api/v1/admin/manual-priority`

**Vulnerability:**
The `identifier` field from the request body is only stripped, not sanitized. Special characters like quotes could allow filter injection.

**Vulnerable Code:**
```python
@router.post("/manual-priority")
async def create_manual_priority(
    request: ManualPriorityRequest,
    # ...
):
    # Validate and clean identifier
    identifier = request.identifier.strip()  # ← Only strips whitespace!
    if not identifier:
        raise HTTPException(status_code=422, detail="Identifier darf nicht leer sein")

    # ... later used in filter:
    base_check_filter = f'manual = true && month="{request.month}" && identifier="{identifier}"'
```

**Impact:**
- Attacker could craft malicious identifier to bypass duplicate checks
- Could create multiple records where there should be one
- Medium severity because:
  - ✓ Requires admin access
  - ✓ Has month validation
  - ✗ But could bypass duplicate detection

**Attack Example:**
```json
POST /api/v1/admin/manual-priority
{
  "identifier": "test\" || manual = false && userId=\"",
  "month": "2025-01",
  "weeks": [...]
}
```

**Fix Required:**
Sanitize `identifier` - only allow alphanumeric characters, hyphens, and underscores:
```python
import re

identifier = request.identifier.strip()
if not identifier:
    raise HTTPException(status_code=422, detail="Identifier darf nicht leer sein")

# Sanitize - only allow safe characters
if not re.match(r'^[a-zA-Z0-9_-]+$', identifier):
    raise HTTPException(
        status_code=422,
        detail="Identifier darf nur Buchstaben, Zahlen, Bindestriche und Unterstriche enthalten"
    )
```

---

### 3. MEDIUM: Filter Injection in Get User for Admin
**Location:** `backend/src/priotag/api/routes/admin.py:343`
**Affected Endpoint:** `GET /api/v1/admin/users/info/{user_id}`

**Vulnerability:**
The `user_id` path parameter (which is actually a username) is directly interpolated into the filter without validation.

**Vulnerable Code:**
```python
@router.get("/users/info/{user_id}")
async def get_user_for_admin(
    user_id: str,  # ← No validation! Actually a username
    token: str = Depends(get_current_token),
    session: SessionInfo = Depends(require_admin),
):
    async with httpx.AsyncClient() as client:
        try:
            # Build filter with institution isolation
            base_filter = f"username='{user_id}'"  # ← Direct interpolation!
            filter_str = build_institution_filter(session, base_filter)
```

**Impact:**
- Attacker could craft malicious username to bypass filters
- Could potentially access multiple users
- Medium severity because:
  - ✓ Requires admin access
  - ✓ Has institution filtering
  - ✗ But could bypass username logic

**Attack Example:**
```bash
GET /api/v1/admin/users/info/test' || role='super_admin
# Could match any super_admin instead of specific user
```

**Fix Required:**
Validate username format - only allow safe characters:
```python
import re

# Validate username format (email-like)
if not re.match(r'^[a-zA-Z0-9.@_-]+$', user_id):
    raise HTTPException(
        status_code=422,
        detail="Invalid username format"
    )
```

---

### 4. MEDIUM: Filter Injection in Get Manual Entries
**Location:** `backend/src/priotag/api/routes/admin.py:535`
**Affected Endpoint:** `GET /api/v1/admin/manual-entries/{month}`

**Vulnerability:**
The `month` path parameter is directly interpolated without validation.

**Vulnerable Code:**
```python
@router.get("/manual-entries/{month}")
async def get_manual_entries(
    month: str,  # ← No validation!
    token: str = Depends(get_current_token),
    session: SessionInfo = Depends(require_admin),
):
    async with httpx.AsyncClient() as client:
        # Build filter with institution isolation
        base_filter = f'manual = true && month="{month}" && identifier!=null'
        filter_str = build_institution_filter(session, base_filter)
```

**Impact:**
- Attacker could craft malicious month value
- Medium severity because:
  - ✓ Requires admin access
  - ✓ Has institution filtering
  - ✗ But could bypass month logic

**Fix Required:**
Add month validation:
```python
from priotag.models.priorities import validate_month_format_and_range

@router.get("/manual-entries/{month}")
async def get_manual_entries(
    month: str,
    token: str = Depends(get_current_token),
    session: SessionInfo = Depends(require_admin),
):
    # Validate month format
    try:
        validate_month_format_and_range(month)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e

    # ... rest of endpoint
```

---

## Other Security Observations (Informational)

### Good Security Practices Found:
1. ✅ **Rate limiting** is implemented on auth endpoints (login, magic word)
2. ✅ **Input validation** exists for dates (`validate_date_format`) and most month parameters
3. ✅ **Type safety** with Pydantic models and Literal types
4. ✅ **HttpOnly cookies** for auth tokens and DEKs
5. ✅ **Session management** with Redis and token blacklisting
6. ✅ **Multi-institution isolation** is properly enforced (after fixes #1 and #2)
7. ✅ **Encryption** for sensitive data (priorities, user fields)
8. ✅ **CSRF protection** with SameSite=strict cookies

### Remaining Minor Issues:
1. **INFO:** No rate limiting on user vacation days endpoints (as noted in SECURITY_AUDIT_2.md)
2. **INFO:** Legacy magic word endpoints still present (as noted in SECURITY_AUDIT_2.md)
3. **INFO:** Change password race condition (as noted in SECURITY_AUDIT_2.md)

---

## Summary

### Filter Injection Vulnerabilities Found: 4
1. Manual entry delete - `month` and `identifier` parameters
2. Manual priority create - `identifier` parameter
3. Get user for admin - `user_id` (username) parameter
4. Get manual entries - `month` parameter

### Risk Level: MEDIUM
- All vulnerabilities require admin access (mitigating factor)
- All have institution filtering in place (mitigating factor)
- Could still allow filter bypasses and unintended data access

### Recommended Fix Priority:
1. **HIGH:** Add identifier sanitization (alphanumeric + hyphen/underscore only)
2. **HIGH:** Add month validation to all endpoints using month parameters
3. **MEDIUM:** Add username format validation
4. **LOW:** Consider switching to parameterized queries if PocketBase supports them

### Next Steps:
1. Implement input sanitization for identifiers
2. Add month validation to remaining endpoints
3. Add username validation
4. Consider comprehensive input validation middleware

---

**Audit Performed By:** Claude (AI Security Audit #3)
**Status:** 4 MEDIUM severity filter injection vulnerabilities identified
**Previous Audits:** CRITICAL issues from audits #1 and #2 have been resolved
