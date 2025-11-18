# Security Audit Report #4 - Final Comprehensive Audit
**Date:** 2025-11-18
**Status:** 4 MEDIUM severity vulnerabilities + 1 LOW severity issue found

## Executive Summary
After completing all CRITICAL and MEDIUM severity fixes from audits #1, #2, and #3, a fourth and final comprehensive audit has revealed **4 MEDIUM severity filter injection vulnerabilities** and **1 LOW severity issue** that were missed in previous audits. Additionally, **1 MEDIUM severity session invalidation bug** was found in the change password flow.

All previously identified CRITICAL issues have been resolved. The application now has strong multi-institution isolation. However, some path parameters are not validated before being used in PocketBase filter strings, creating filter injection risks.

---

## Filter Injection Vulnerabilities (Severity: MEDIUM)

### Background: What Was Missed?
Previous audits (SECURITY_AUDIT_3.md) fixed filter injection in admin endpoints by validating request body parameters. However, **path parameters** in some endpoints were not validated and can still be exploited.

---

### 1. MEDIUM: Filter Injection in Priority GET Endpoint
**Location:** `backend/src/priotag/api/routes/priorities.py:94-168`
**Affected Endpoint:** `GET /api/v1/priorities/{month}`

**Vulnerability:**
The `month` path parameter is directly interpolated into the filter string without validation.

**Vulnerable Code:**
```python
@router.get("/{month}", response_model=PriorityResponse)
async def get_priority(
    month: str,  # ← No validation!
    auth_data: SessionInfo = Depends(verify_token),
    token: str = Depends(get_current_token),
    dek: bytes = Depends(get_current_dek),
):
    user_id = auth_data.id

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{POCKETBASE_URL}/api/collections/priorities/records",
            headers={"Authorization": f"Bearer {token}"},
            params={
                "filter": f'userId = "{user_id}" && month = "{month}" && identifier = null',  # ← Direct interpolation!
            },
        )
```

**Impact:**
- Authenticated users could craft malicious month values
- Could potentially access priorities from other months
- Medium severity because:
  - ✓ User is authenticated
  - ✓ Filter includes userId check
  - ✗ But could bypass month logic

**Attack Example:**
```bash
GET /api/v1/priorities/2025-01" || userId="victim_id
# Could potentially match other users' priorities if combined with other exploits
```

**Fix Required:**
Add month validation at the start of the function:
```python
from priotag.models.priorities import validate_month_format_and_range

@router.get("/{month}", response_model=PriorityResponse)
async def get_priority(
    month: str,
    auth_data: SessionInfo = Depends(verify_token),
    token: str = Depends(get_current_token),
    dek: bytes = Depends(get_current_dek),
):
    # Validate month format to prevent filter injection
    try:
        validate_month_format_and_range(month)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e

    # ... rest of endpoint
```

---

### 2. MEDIUM: Filter Injection in Priority DELETE Endpoint
**Location:** `backend/src/priotag/api/routes/priorities.py:350-417`
**Affected Endpoint:** `DELETE /api/v1/priorities/{month}`

**Vulnerability:**
The `month` path parameter is directly interpolated into the filter string without validation.

**Vulnerable Code:**
```python
@router.delete("/{month}")
async def delete_priority(
    month: str,  # ← No validation!
    auth_data: SessionInfo = Depends(verify_token),
    token: str = Depends(get_current_token),
):
    user_id = auth_data.id

    async with httpx.AsyncClient() as client:
        check_response = await client.get(
            f"{POCKETBASE_URL}/api/collections/priorities/records",
            headers={"Authorization": f"Bearer {token}"},
            params={
                "filter": f'userId = "{user_id}" && month = "{month}" && identifier = null',  # ← Direct interpolation!
            },
        )
```

**Impact:**
- Same as issue #1
- Users could craft malicious month values
- Medium severity with same mitigations

**Fix Required:**
Add month validation (same as issue #1):
```python
try:
    validate_month_format_and_range(month)
except ValueError as e:
    raise HTTPException(status_code=422, detail=str(e)) from e
```

---

### 3. MEDIUM: Filter Injection in Admin Vacation Day GET Endpoint
**Location:** `backend/src/priotag/api/routes/vacation_days.py:272-316`
**Affected Endpoint:** `GET /api/v1/admin/vacation-days/{date}`

**Vulnerability:**
The `date` path parameter is directly interpolated into the filter string without validation.

**Vulnerable Code:**
```python
@router.get("/vacation-days/{date}", response_model=VacationDayResponse)
async def get_vacation_day(
    date: str,  # ← No validation!
    token: str = Depends(get_current_token),
    session: SessionInfo = Depends(require_admin),
):
    async with httpx.AsyncClient() as client:
        base_filter = f'date ~ "{date}"'  # ← Direct interpolation!
        filter_str = build_institution_filter(session, base_filter)
```

**Impact:**
- Admins could craft malicious date values
- Could bypass date logic
- Medium severity because:
  - ✓ Requires admin access
  - ✓ Has institution filtering
  - ✗ But could bypass date filter

**Attack Example:**
```bash
GET /api/v1/admin/vacation-days/2025-01-01" || type="admin_leave
# Could match unintended records
```

**Fix Required:**
Add date format validation:
```python
from priotag.models.vacation_days import validate_date_format

@router.get("/vacation-days/{date}", response_model=VacationDayResponse)
async def get_vacation_day(
    date: str,
    token: str = Depends(get_current_token),
    session: SessionInfo = Depends(require_admin),
):
    # Validate date format to prevent filter injection
    try:
        validate_date_format(date)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e

    # ... rest of endpoint
```

---

### 4. MEDIUM: Filter Injection in Admin Vacation Day UPDATE and DELETE Endpoints
**Location:**
- `backend/src/priotag/api/routes/vacation_days.py:319-395` (PUT)
- `backend/src/priotag/api/routes/vacation_days.py:398-459` (DELETE)

**Affected Endpoints:**
- `PUT /api/v1/admin/vacation-days/{date}`
- `DELETE /api/v1/admin/vacation-days/{date}`

**Vulnerability:**
Both endpoints use the `date` path parameter without validation (same pattern as issue #3).

**Vulnerable Code (PUT endpoint):**
```python
@router.put("/vacation-days/{date}", response_model=VacationDayResponse)
async def update_vacation_day(
    date: str,  # ← No validation!
    request: VacationDayUpdate,
    token: str = Depends(get_current_token),
    session: SessionInfo = Depends(require_admin),
):
    async with httpx.AsyncClient() as client:
        base_filter = f'date ~ "{date}"'  # ← Direct interpolation!
        filter_str = build_institution_filter(session, base_filter)
```

**Impact:**
- Same as issue #3
- Admins could inject filter logic

**Fix Required:**
Add date validation to both endpoints (same pattern as issue #3).

---

## Session Management Vulnerability (Severity: MEDIUM)

### 5. MEDIUM: Session Invalidation Bug in Change Password
**Location:** `backend/src/priotag/api/routes/auth.py:824-875`
**Affected Endpoint:** `POST /api/v1/auth/change-password`

**Vulnerability:**
The session invalidation code on password change checks for a `user_id` key in session data, but all sessions are created with an `id` key. This causes old sessions to NOT be invalidated when users change their password.

**Vulnerable Code:**
```python
# Line 848: Checks for "user_id" key
if session_info.get("user_id") == current_session.id:
    redis_client.delete(key_str)
    invalidated_count += 1
```

But sessions are created with "id" key, not "user_id":
```python
# Lines 322-327 (registration):
session_info = {
    "id": auth_data["record"]["id"],  # ← Uses "id" not "user_id"
    "username": auth_data["record"]["username"],
    "role": auth_data["record"]["role"],
    "is_admin": auth_data["record"]["role"] in ["admin", "institution_admin", "super_admin"],
    "institution_id": auth_data["record"].get("institution_id"),
}

# Lines 510-516 (QR registration): Same pattern with "id"
# Lines 631-632 (login): Uses extract_session_info_from_record which returns SessionInfo with "id"
```

But on line 860-865 (in change password), a new session is created with "user_id":
```python
# Line 860-865: Inconsistently uses "user_id"
session_info = {
    "user_id": current_session.id,  # ← Should be "id"
    "username": current_session.username,
    "role": "admin" if current_session.is_admin else "user",
    "is_admin": current_session.is_admin,
}
```

**Impact:**
- When users change password, their old sessions are NOT invalidated
- Old sessions remain valid until they naturally expire
- Compromised sessions could still be used after password change
- High severity because this defeats the purpose of password change

**Proof of Concept:**
1. User logs in, gets session A
2. Attacker steals session A token
3. User suspects compromise, changes password
4. Code attempts to invalidate old sessions but checks for "user_id" key
5. Sessions have "id" key, so condition on line 848 is always false
6. Attacker's session A remains valid!

**Fix Required:**
1. Fix line 848 to check for "id" instead of "user_id":
```python
if session_info.get("id") == current_session.id:
    redis_client.delete(key_str)
    invalidated_count += 1
```

2. Fix line 860-865 to use "id" instead of "user_id":
```python
session_info = {
    "id": current_session.id,  # ← Changed from "user_id"
    "username": current_session.username,
    "role": "admin" if current_session.is_admin else "user",
    "is_admin": current_session.is_admin,
    "institution_id": current_session.institution_id,  # ← Also add this for consistency
}
```

---

## Rate Limiting Gaps (Severity: LOW)

### 6. LOW: No Rate Limiting on Account Deletion
**Location:** `backend/src/priotag/api/routes/account.py:166-254`
**Affected Endpoint:** `DELETE /api/v1/account/delete`

**Vulnerability:**
The account deletion endpoint has no rate limiting. While authentication is required, an attacker could:
- Rapidly delete/recreate accounts to cause database churn
- DoS by forcing database operations
- Enumerate valid accounts (timing attacks)

**Impact:**
- DoS potential
- Database resource exhaustion
- Low severity because authentication is required

**Recommendation:**
Add rate limiting similar to login (e.g., 1 deletion per minute per user):
```python
from priotag.services.redis_service import get_redis

@router.delete("/delete")
async def delete_account(
    response: Response,
    token: str = Depends(get_current_token),
    session: SessionInfo = Depends(verify_token),
    redis_client: redis.Redis = Depends(get_redis),
):
    # Rate limit: 1 deletion attempt per minute
    rate_limit_key = f"rate_limit:delete_account:{session.id}"
    if redis_client.exists(rate_limit_key):
        raise HTTPException(
            status_code=429,
            detail="Zu viele Versuche. Bitte warten Sie eine Minute.",
        )

    redis_client.setex(rate_limit_key, 60, "deleting")

    # ... rest of endpoint
```

---

## Other Security Observations (Informational)

### Good Security Practices Found:
1. ✅ **Multi-institution isolation** is properly enforced after fixes from audits #1, #2, #3
2. ✅ **Rate limiting** on auth endpoints (login, magic word, registration)
3. ✅ **Input validation** exists for most parameters (dates, identifiers in admin endpoints)
4. ✅ **Type safety** with Pydantic models and dependency injection
5. ✅ **HttpOnly cookies** for auth tokens and DEKs
6. ✅ **Session management** with Redis and token blacklisting
7. ✅ **Encryption** for sensitive data (priorities, user fields)
8. ✅ **CSRF protection** with SameSite=strict cookies
9. ✅ **Authorization checks** on all protected endpoints
10. ✅ **Error handling** doesn't leak sensitive information

### Remaining Minor Issues:
1. **INFO:** Legacy magic word endpoints still present (admin.py:115, 157) - should be deprecated
2. **INFO:** No rate limiting on admin endpoints (acceptable trade-off)
3. **INFO:** No rate limiting on user vacation days endpoints (noted in SECURITY_AUDIT_2.md)

---

## Summary

### Vulnerabilities Found: 6
1. **MEDIUM:** Filter injection in priority GET endpoint - month parameter
2. **MEDIUM:** Filter injection in priority DELETE endpoint - month parameter
3. **MEDIUM:** Filter injection in admin vacation day GET endpoint - date parameter
4. **MEDIUM:** Filter injection in admin vacation day PUT/DELETE endpoints - date parameter
5. **MEDIUM:** Session invalidation bug in change password - wrong key checked
6. **LOW:** No rate limiting on account deletion

### Risk Level: MEDIUM
- Filter injection vulnerabilities are mitigated by:
  - ✓ Authentication required on all endpoints
  - ✓ userId or institution_id filters in place
  - ✗ But path parameter validation is missing
- Session invalidation bug is a real security issue that defeats password change protection

### Recommended Fix Priority:
1. **HIGH:** Fix session invalidation bug (issue #5) - critical for password change security
2. **HIGH:** Add month validation to priority GET/DELETE endpoints (issues #1, #2)
3. **MEDIUM:** Add date validation to vacation day admin endpoints (issues #3, #4)
4. **LOW:** Add rate limiting to account deletion (issue #6)

### Next Steps:
1. Implement input validation for all path parameters
2. Fix session invalidation in change password endpoint
3. Add rate limiting to account deletion
4. Consider comprehensive input validation middleware for all endpoints
5. Remove or deprecate legacy magic word endpoints

---

## Code Quality Observations

### Excellent:
- Consistent use of helper functions (build_institution_filter, verify_user_belongs_to_institution)
- Clear separation of concerns (admin vs user endpoints)
- Good error messages in German for user-facing errors
- Comprehensive encryption using DEK wrapping pattern

### Could Improve:
- Inconsistent session key naming ("id" vs "user_id") caused the bug in issue #5
- Path parameter validation should be mandatory in a middleware or decorator
- Consider using Pydantic validators for path parameters

---

**Audit Performed By:** Claude (AI Security Audit #4 - Final Comprehensive Audit)
**Status:** 4 MEDIUM + 1 MEDIUM + 1 LOW severity vulnerabilities identified
**Previous Audits:** All CRITICAL issues from audits #1, #2, and #3 have been resolved
**Recommendation:** Fix the 6 issues identified in this audit to achieve excellent security posture
