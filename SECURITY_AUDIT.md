# Security Audit Report - Multi-Institution Implementation

**Date:** 2025-01-18
**Auditor:** Claude Code Security Review
**Scope:** Multi-institution data isolation and security vulnerabilities

---

## Executive Summary

This audit identified **2 CRITICAL** and **5 HIGH** priority security vulnerabilities in the multi-institution implementation. The most severe issues relate to vacation days endpoints completely bypassing institution isolation, allowing institution admins to access and modify data from other institutions.

**Status:** 🔴 **CRITICAL VULNERABILITIES FOUND**

---

## 🔴 CRITICAL VULNERABILITIES

### 1. Vacation Days Admin Endpoints - Complete Institution Isolation Bypass

**Severity:** CRITICAL
**File:** `backend/src/priotag/api/routes/vacation_days.py`
**CVSS Score:** 9.1 (Critical)

**Description:**
ALL admin vacation day endpoints (`/admin/vacation-days/*`) are missing institution_id filtering. Institution admins can create, view, update, and delete vacation days for ANY institution, not just their own.

**Affected Endpoints:**
- `POST /admin/vacation-days` (line 24) - Create vacation day
- `POST /admin/vacation-days/bulk` (line 85) - Bulk create
- `GET /admin/vacation-days` (line 153) - List all vacation days
- `GET /admin/vacation-days/{date}` (line 201) - Get specific vacation day
- `PUT /admin/vacation-days/{date}` (line 241) - Update vacation day
- `DELETE /admin/vacation-days/{date}` (line 313) - Delete vacation day

**Vulnerable Code Example:**
```python
# Line 153-198: No institution filtering!
@router.get("/vacation-days", response_model=list[VacationDayResponse])
async def get_all_vacation_days(
    token: str = Depends(get_current_token),
    _=Depends(require_admin),  # ❌ Only checks admin role
    year: int | None = None,
    type: str | None = None,
):
    # ❌ Fetches ALL vacation days from ALL institutions
    response = await client.get(
        f"{POCKETBASE_URL}/api/collections/vacation_days/records",
        params=params,
        headers={"Authorization": f"Bearer {token}"},
    )
```

**Impact:**
- Institution Admin A can view vacation days from Institution B
- Institution Admin A can modify/delete Institution B's vacation days
- No data isolation for vacation days
- Potential business disruption (deleting competitor's vacation days)

**Exploitation:**
```bash
# Institution Admin A can delete Institution B's vacation days
curl -X DELETE https://api.example.com/api/v1/admin/vacation-days/2025-12-25 \
  -H "Cookie: session=institution_a_admin_token"
```

**Remediation:**
Add the same institution filtering pattern used in admin.py:
```python
@router.get("/vacation-days", response_model=list[VacationDayResponse])
async def get_all_vacation_days(
    token: str = Depends(get_current_token),
    session: SessionInfo = Depends(require_admin),  # ✓ Get session
    year: int | None = None,
    type: str | None = None,
):
    # Build filter with institution isolation
    from priotag.api.routes.admin import build_institution_filter

    base_filter = ""
    if year:
        base_filter = f'date >= "{year}-01-01" && date <= "{year}-12-31"'
    if type:
        type_filter = f'type="{type}"'
        base_filter = f"{base_filter} && {type_filter}" if base_filter else type_filter

    filter_str = build_institution_filter(session, base_filter)

    params = {"perPage": 500, "sort": "date"}
    if filter_str:
        params["filter"] = filter_str

    # ✓ Now filtered by institution
    response = await client.get(...)
```

**Priority:** 🔴 **FIX IMMEDIATELY**

---

### 2. Priority Save Missing institution_id

**Severity:** CRITICAL
**File:** `backend/src/priotag/api/routes/priorities.py`
**Line:** 295-302

**Description:**
When users save priorities, the endpoint doesn't add `institution_id` to the record. This means priorities created after multi-institution migration won't have institution_id set.

**Vulnerable Code:**
```python
# Line 295-302
encrypted_priority = {
    "userId": user_id,
    "month": month,
    "encrypted_fields": encrypted_data,
    "identifier": None,
    "manual": False,
    # ❌ MISSING: "institution_id": session.institution_id
}
```

**Impact:**
- Priorities created by new users won't have institution_id
- Admin queries filtering by institution_id will miss these records
- Inconsistent data state
- Data integrity issues

**Remediation:**
```python
encrypted_priority = {
    "userId": user_id,
    "month": month,
    "encrypted_fields": encrypted_data,
    "identifier": None,
    "manual": False,
    "institution_id": auth_data.institution_id,  # ✓ Add this
}
```

**Priority:** 🔴 **FIX IMMEDIATELY**

---

## 🟠 HIGH PRIORITY VULNERABILITIES

### 3. PocketBase Filter Injection Risk

**Severity:** HIGH
**Files:** Multiple admin endpoints
**CVSS Score:** 7.5 (High)

**Description:**
Several endpoints construct PocketBase filter strings using user input without proper sanitization. While PocketBase has some protections, this could lead to filter injection attacks.

**Vulnerable Code Examples:**
```python
# admin.py:230 - User input in filter
base_filter = f"username='{user_id}'"  # ❌ user_id from URL path

# admin.py:446 - Identifier in filter
base_check_filter = f'manual = true && month="{request.month}" && identifier="{identifier}"'
# ❌ identifier from user input

# vacation_days.py:221 - Date in filter
params={"filter": f'date ~ "{date}"'}  # ❌ date from URL path
```

**Attack Scenario:**
```bash
# Potential filter injection via username
curl https://api.example.com/api/v1/admin/users/info/admin" || @request.auth.id != ""
```

**Impact:**
- Potential unauthorized data access
- Filter bypass
- Information disclosure

**Remediation:**
1. Use parameterized queries or prepared statements if available
2. Validate and sanitize all user input
3. Use allowlists for valid characters in identifiers
4. Add input validation:

```python
import re

def sanitize_filter_value(value: str) -> str:
    """Sanitize user input for PocketBase filters."""
    # Only allow alphanumeric, dash, underscore, dot
    if not re.match(r'^[a-zA-Z0-9_\-\.@]+$', value):
        raise HTTPException(400, "Invalid characters in input")
    # Escape quotes
    return value.replace('"', '\\"').replace("'", "\\'")

# Usage
base_filter = f"username='{sanitize_filter_value(user_id)}'"
```

**Priority:** 🟠 **FIX SOON**

---

### 4. Information Disclosure via Error Messages

**Severity:** HIGH
**Files:** Multiple endpoints
**CVSS Score:** 6.5 (Medium-High)

**Description:**
Error messages reveal sensitive information about the system's internal state, database structure, and data existence.

**Examples:**
```python
# admin.py:91 - Reveals user existence
raise HTTPException(status_code=404, detail="Benutzer nicht gefunden")

# admin.py:250 - Reveals whether user exists vs no permission
detail="Benutzer nicht gefunden oder keine Berechtigung"

# vacation_days.py:55 - Reveals vacation day existence
detail=f"Urlaubstag für {request.date} existiert bereits"
```

**Impact:**
- User enumeration attacks
- Information about system state
- Reveals data existence to unauthorized users
- Assists in reconnaissance for further attacks

**Remediation:**
Use generic error messages for unauthorized access:

```python
# ❌ BAD: Reveals different information
if user_not_found:
    raise HTTPException(404, "User not found")
if no_permission:
    raise HTTPException(403, "No permission")

# ✓ GOOD: Generic message
if user_not_found or no_permission:
    raise HTTPException(404, "Resource not found")  # Same for both
```

**Priority:** 🟠 **FIX SOON**

---

### 5. Missing Rate Limiting on Admin Endpoints

**Severity:** HIGH
**Files:** All admin routes
**CVSS Score:** 6.5 (Medium-High)

**Description:**
Admin endpoints lack rate limiting, allowing brute force attacks, enumeration attacks, and potential DoS.

**Vulnerable Endpoints:**
- `/admin/users/detail/{user_id}` - Can enumerate all user IDs
- `/admin/vacation-days/{date}` - Can enumerate all dates
- `/admin/delete-user/{user_id}` - Can attempt mass deletion
- All other admin endpoints

**Attack Scenarios:**
1. **User Enumeration:**
```python
# Try all possible user IDs
for user_id in range(1000000):
    response = requests.get(f"/admin/users/detail/{user_id}")
    if response.status_code == 200:
        print(f"Found user: {user_id}")
```

2. **DoS via Admin Operations:**
```python
# Spam admin endpoints to exhaust resources
while True:
    requests.get("/admin/users/2025-01")  # Heavy query
```

**Impact:**
- User enumeration
- Data harvesting
- Resource exhaustion
- Denial of service

**Remediation:**
Implement rate limiting using Redis:

```python
from fastapi import Request
import time

async def rate_limit_admin(
    request: Request,
    session: SessionInfo,
    redis_client: redis.Redis,
):
    """Rate limit admin endpoints: 100 requests per minute."""
    key = f"rate_limit:admin:{session.id}:{int(time.time() / 60)}"
    count = redis_client.incr(key)
    redis_client.expire(key, 60)

    if count > 100:
        raise HTTPException(429, "Rate limit exceeded. Try again in a minute.")

    return session

# Apply to all admin endpoints
@router.get("/admin/users/{month}")
async def get_user_submissions(
    session: SessionInfo = Depends(rate_limit_admin),  # ✓ Add rate limit
    ...
```

**Priority:** 🟠 **FIX SOON**

---

### 6. Vacation Days Missing institution_id on Creation

**Severity:** HIGH
**File:** `backend/src/priotag/api/routes/vacation_days.py`
**Lines:** 59-64, 123-128

**Description:**
When admins create vacation days, the endpoint doesn't add `institution_id` to the record.

**Vulnerable Code:**
```python
# Line 59-64
vacation_data = {
    "date": request.date,
    "type": request.type,
    "description": request.description,
    "created_by": session_info.username,
    # ❌ MISSING: "institution_id": session_info.institution_id
}
```

**Impact:**
- New vacation days won't be associated with an institution
- Data integrity issues
- Orphaned records

**Remediation:**
```python
vacation_data = {
    "date": request.date,
    "type": request.type,
    "description": request.description,
    "created_by": session_info.username,
    "institution_id": session_info.institution_id,  # ✓ Add this
}
```

**Priority:** 🟠 **FIX SOON**

---

### 7. Session Management - No Automatic Logout on Permission Change

**Severity:** HIGH
**Files:** Auth system
**CVSS Score:** 6.5 (Medium-High)

**Description:**
When a user's role or institution is changed, existing sessions are not invalidated. A demoted admin or moved user retains their old permissions until session expires.

**Attack Scenario:**
1. User is institution_admin for Institution A
2. User logs in, gets session token
3. Super admin changes user to regular user
4. User's session STILL has institution_admin permissions cached
5. User can continue performing admin operations

**Impact:**
- Privilege escalation after demotion
- Access to old institution after transfer
- Stale permission cache

**Remediation:**
1. Invalidate sessions on permission change:
```python
# In user update endpoint
async def update_user_role(user_id, new_role):
    # Update role in database
    ...

    # Invalidate all sessions for this user
    pattern = f"session:*"
    for key in redis_client.scan_iter(pattern):
        session_data = redis_client.get(key)
        if session_data:
            data = json.loads(session_data)
            if data.get("user_id") == user_id:
                redis_client.delete(key)
```

2. Add session version to detect stale sessions:
```python
# Store version in Redis
user_session_version = f"user_session_version:{user_id}"
redis_client.incr(user_session_version)

# Check on every request
stored_version = redis_client.get(f"user_session_version:{session.id}")
if session.version != stored_version:
    raise HTTPException(401, "Session invalid. Please login again.")
```

**Priority:** 🟠 **FIX SOON**

---

## 🟡 MEDIUM PRIORITY ISSUES

### 8. Missing Input Validation on Dates

**Severity:** MEDIUM
**Files:** vacation_days.py, admin.py
**CVSS Score:** 5.3 (Medium)

**Description:**
Date parameters are not consistently validated before use in queries.

**Examples:**
```python
# vacation_days.py:221 - No validation
response = await client.get(
    params={"filter": f'date ~ "{date}"'}  # ❌ date not validated
)

# admin.py:148 - Only format check, no range check
base_filter = f"manual = false && month='{month}'"  # ❌ Could be "9999-99"
```

**Remediation:**
```python
from datetime import datetime

def validate_date(date_str: str) -> str:
    """Validate date format and range."""
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        if dt.year < 2000 or dt.year > 2100:
            raise ValueError("Year out of range")
        return date_str
    except ValueError as e:
        raise HTTPException(422, f"Invalid date format: {e}")

# Usage
date = validate_date(date)
```

**Priority:** 🟡 **Address Soon**

---

### 9. Admin Magic Word Endpoint Returns Too Much Information

**Severity:** MEDIUM
**File:** `backend/src/priotag/api/routes/admin.py`
**Lines:** 28-67

**Description:**
The `/admin/magic-word-info` endpoint returns the current magic word in plaintext. This should be removed or restricted.

**Vulnerable Code:**
```python
return {
    "current_magic_word": magic_word,  # ❌ Exposes secret
    "last_updated": last_updated,
    "last_updated_by": last_updated_by,
}
```

**Impact:**
- If admin account is compromised, attacker gets magic word
- Magic word can be used to register new accounts
- Insider threat risk

**Remediation:**
Either remove this endpoint or return masked value:
```python
return {
    "current_magic_word": "***" + magic_word[-4:],  # ✓ Masked
    "last_updated": last_updated,
    "last_updated_by": last_updated_by,
}
```

**Priority:** 🟡 **Address Soon**

---

### 10. Insufficient Logging of Security Events

**Severity:** MEDIUM
**Files:** All admin endpoints
**CVSS Score:** 5.0 (Medium)

**Description:**
Critical security events are not logged, making incident response and forensics difficult.

**Missing Logs:**
- Admin login/logout
- User deletion (who deleted whom)
- Permission changes
- Failed authorization attempts
- Bulk operations
- Data exports

**Impact:**
- No audit trail
- Cannot detect insider threats
- Difficult incident response
- Compliance issues (GDPR, etc.)

**Remediation:**
Add structured logging:

```python
import logging
import json

security_logger = logging.getLogger("security_audit")

# Log security events
security_logger.info(json.dumps({
    "event": "user_deletion",
    "actor": session.username,
    "actor_id": session.id,
    "target_user_id": user_id,
    "target_username": username,
    "institution_id": session.institution_id,
    "timestamp": datetime.now().isoformat(),
    "ip": request.client.host,
}))
```

**Priority:** 🟡 **Address Soon**

---

## 🟢 LOW PRIORITY ISSUES

### 11. No CSRF Protection on State-Changing Operations

**Severity:** LOW
**CVSS Score:** 4.3 (Medium-Low)

**Description:**
State-changing operations (POST, PUT, DELETE) lack CSRF tokens, relying only on httpOnly cookies.

**Recommendation:**
Implement CSRF tokens for state-changing operations.

---

### 12. Predictable Record IDs

**Severity:** LOW
**CVSS Score:** 3.7 (Low)

**Description:**
If PocketBase uses sequential IDs, this enables enumeration attacks.

**Recommendation:**
Verify PocketBase uses UUIDs or random IDs for all collections.

---

## Summary of Findings

| Severity | Count | Status |
|----------|-------|--------|
| 🔴 Critical | 2 | **IMMEDIATE ACTION REQUIRED** |
| 🟠 High | 5 | Fix within 1 week |
| 🟡 Medium | 3 | Fix within 1 month |
| 🟢 Low | 2 | Fix when convenient |
| **TOTAL** | **12** | |

---

## Recommended Action Plan

### Phase 1: Critical Fixes (Week 1)
1. ✅ **DONE:** Fix admin.py institution filtering (completed)
2. 🔴 **TODO:** Fix vacation_days.py institution filtering
3. 🔴 **TODO:** Add institution_id to priority save
4. 🔴 **TODO:** Add institution_id to vacation day creation

### Phase 2: High Priority (Week 2)
5. Add filter injection protection
6. Implement rate limiting on admin endpoints
7. Fix session invalidation on permission changes
8. Reduce information disclosure in errors

### Phase 3: Medium Priority (Week 3-4)
9. Add comprehensive security logging
10. Add input validation
11. Review magic word endpoint
12. Add security tests for new fixes

### Phase 4: Low Priority (Ongoing)
13. Add CSRF protection
14. Review all ID generation

---

## Testing Requirements

For each fix, add security tests:

```python
@pytest.mark.integration
def test_institution_admin_cannot_access_other_vacation_days():
    """Verify vacation day isolation between institutions."""
    # Create two institutions with vacation days
    # Login as institution A admin
    # Try to access institution B vacation day
    # Should return 404 or 403
    assert response.status_code in [403, 404]
```

---

## Compliance Impact

**GDPR:**
- ✅ Data isolation fixes improve Article 32 (Security) compliance
- ⚠️  Logging gaps violate Article 30 (Records of processing)

**ISO 27001:**
- ⚠️  Access control weaknesses (A.9.2)
- ⚠️  Security logging gaps (A.12.4)

---

## Conclusion

The multi-institution implementation has **critical security vulnerabilities** that must be addressed immediately. The vacation days endpoints represent a complete bypass of institution isolation, allowing cross-institution data access and modification.

**Overall Security Rating:** 🔴 **CRITICAL - Not Production Ready**

After implementing Phase 1 fixes: 🟡 **Acceptable with Monitoring**

---

**Report Generated:** 2025-01-18
**Next Review:** After Phase 1 completion
