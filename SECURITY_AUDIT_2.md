# Security Audit Report #2 - Additional Vulnerabilities
**Date:** 2025-11-18
**Status:** CRITICAL vulnerabilities found

## Executive Summary
After completing the first round of critical security fixes, a second comprehensive audit has revealed **3 additional CRITICAL vulnerabilities** and **3 HIGH severity issues** related to multi-institution data isolation.

## Critical Vulnerabilities (Severity: CRITICAL)

### 1. ⚠️ CRITICAL: User Vacation Days Endpoints Missing Institution Filtering
**Location:** `backend/src/priotag/api/routes/vacation_days.py`
**Affected Endpoints:**
- `GET /api/v1/vacation-days` (line 467)
- `GET /api/v1/vacation-days/range` (line 534)
- `GET /api/v1/vacation-days/{date}` (line 597)

**Vulnerability:**
All three user-facing vacation day endpoints are missing institution filtering. Users from Institution A can see vacation days from ALL institutions, including Institution B, C, etc.

**Impact:**
- Information disclosure across institutions
- Users can see vacation days they shouldn't have access to
- Violates multi-institution data isolation
- Could reveal sensitive information about other institutions' schedules

**Proof of Concept:**
```python
# User from Institution A
session = {"institution_id": "inst_a_id", "role": "user"}

# Can see vacation days from Institution B, C, etc.
GET /api/v1/vacation-days?year=2025
# Returns ALL vacation days from ALL institutions
```

**Fix Required:**
Add institution filtering to all three endpoints using the session's `institution_id`.

**Code Example (Fix):**
```python
@user_router.get("/vacation-days", response_model=list[VacationDayUserResponse])
async def get_vacation_days_for_users(
    token: str = Depends(get_current_token),
    session: SessionInfo = Depends(verify_token),  # ← Need session
    year: int | None = None,
    month: int | None = None,
    type: str | None = None,
):
    # Verify user has institution_id
    if not session.institution_id:
        raise HTTPException(400, "User not associated with an institution")

    async with httpx.AsyncClient() as client:
        # Build filter with institution filtering
        filters = []

        # Add institution filter
        filters.append(f'institution_id="{session.institution_id}"')

        if year and month:
            filters.append(f'date >= "{year}-{month:02d}-01" && date < "{year}-{month:02d}-32"')
        elif year:
            filters.append(f'date >= "{year}-01-01" && date <= "{year}-12-31"')

        if type:
            filters.append(f'type="{type}"')

        filter_str = " && ".join(filters)
        # ... rest of endpoint
```

---

### 2. ⚠️ CRITICAL: Admin Priority Update Missing Institution Filtering
**Location:** `backend/src/priotag/api/routes/admin.py:835`
**Affected Endpoint:** `PATCH /api/v1/admin/priorities/{priority_id}`

**Vulnerability:**
The `update_priority` endpoint allows institution admins to update ANY priority record by ID, even if it belongs to a different institution. No institution filtering is applied.

**Impact:**
- Institution admin from A can modify priorities from Institution B
- Cross-institution data tampering
- Complete bypass of multi-institution isolation

**Proof of Concept:**
```python
# Institution admin from Institution A
PATCH /api/v1/admin/priorities/{priority_id_from_institution_b}
{
  "encrypted_fields": "modified_data"
}
# ✗ Succeeds - can modify priorities from Institution B!
```

**Fix Required:**
1. Fetch the priority record first
2. Verify it belongs to the admin's institution (or allow if super_admin)
3. Then allow the update

**Code Example (Fix):**
```python
@router.patch("/priorities/{priority_id}")
async def update_priority(
    priority_id: str,
    request: UpdatePriorityRequest,
    token: str = Depends(get_current_token),
    session: SessionInfo = Depends(require_admin),  # ← Need session not _
):
    async with httpx.AsyncClient() as client:
        # Fetch priority first to verify institution
        get_response = await client.get(
            f"{POCKETBASE_URL}/api/collections/priorities/records/{priority_id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        if get_response.status_code == 404:
            raise HTTPException(404, "Prioritätsdatensatz nicht gefunden")

        if get_response.status_code != 200:
            raise HTTPException(500, "Fehler beim Abrufen der Priorität")

        priority = get_response.json()

        # Verify institution ownership (super admins bypass)
        if session.role != "super_admin":
            if priority.get("institution_id") != session.institution_id:
                raise HTTPException(403, "Keine Berechtigung für diese Priorität")

        # Now update
        response = await client.patch(
            f"{POCKETBASE_URL}/api/collections/priorities/records/{priority_id}",
            json={"encrypted_fields": request.encrypted_fields},
            headers={"Authorization": f"Bearer {token}"},
        )
        # ... rest
```

---

### 3. ⚠️ CRITICAL: Admin Priority Delete Missing Institution Filtering
**Location:** `backend/src/priotag/api/routes/admin.py:874`
**Affected Endpoint:** `DELETE /api/v1/admin/priorities/{priority_id}`

**Vulnerability:**
The `delete_priority` endpoint allows institution admins to delete ANY priority record by ID, even if it belongs to a different institution. No institution filtering is applied.

**Impact:**
- Institution admin from A can delete priorities from Institution B
- Data loss for other institutions
- Complete bypass of multi-institution isolation

**Proof of Concept:**
```python
# Institution admin from Institution A
DELETE /api/v1/admin/priorities/{priority_id_from_institution_b}
# ✗ Succeeds - can delete priorities from Institution B!
```

**Fix Required:**
Add institution verification before allowing deletion (same pattern as update).

**Code Example (Fix):**
```python
@router.delete("/priorities/{priority_id}")
async def delete_priority(
    priority_id: str,
    token: str = Depends(get_current_token),
    session: SessionInfo = Depends(require_admin),  # ← Need session not _
):
    async with httpx.AsyncClient() as client:
        # Get priority details
        priority_response = await client.get(
            f"{POCKETBASE_URL}/api/collections/priorities/records/{priority_id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        if priority_response.status_code == 404:
            raise HTTPException(404, "Prioritätsdatensatz nicht gefunden")

        if priority_response.status_code != 200:
            raise HTTPException(500, "Fehler beim Abrufen des Prioritätsdatensatzes")

        priority_data = priority_response.json()

        # Verify institution ownership (super admins bypass)
        if session.role != "super_admin":
            if priority_data.get("institution_id") != session.institution_id:
                raise HTTPException(403, "Keine Berechtigung für diese Priorität")

        month = priority_data.get("month", "unknown")

        # Delete the priority record
        delete_response = await client.delete(
            f"{POCKETBASE_URL}/api/collections/priorities/records/{priority_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        # ... rest
```

---

## High Severity Issues

### 4. HIGH: Legacy Magic Word Endpoints May Conflict With Multi-Institution
**Location:** `backend/src/priotag/api/routes/admin.py:115-179`
**Affected Endpoints:**
- `GET /api/v1/admin/magic-word-info` (line 115)
- `POST /api/v1/admin/update-magic-word` (line 157)

**Vulnerability:**
These endpoints appear to be legacy code that manages a single global magic word via `system_settings` collection. This conflicts with the multi-institution model where each institution has its own magic word.

**Impact:**
- Confusion about which magic word system is in use
- Potential for institution admins to see/update global magic word
- Dead code that should be removed or clearly deprecated

**Recommendation:**
1. Verify if these endpoints are still in use
2. If not used, remove them
3. If used, add deprecation warnings and institution filtering
4. Update documentation to clarify institution-specific magic words

---

### 5. HIGH: User Vacation Days - No Rate Limiting
**Location:** `backend/src/priotag/api/routes/vacation_days.py:467-639`

**Vulnerability:**
The user vacation day endpoints have no rate limiting. An attacker could make thousands of requests to enumerate vacation days or cause resource exhaustion.

**Impact:**
- Resource exhaustion
- Information gathering via automated scanning
- Denial of service

**Fix Required:**
Add rate limiting similar to other endpoints (e.g., login has IP-based rate limiting).

---

### 6. HIGH: Change Password - Session Invalidation Race Condition
**Location:** `backend/src/priotag/api/routes/auth.py:824-857`

**Vulnerability:**
The change password endpoint invalidates sessions by scanning Redis with pattern matching. There's a race condition window where:
1. Old sessions are being invalidated
2. But new requests could still validate against PocketBase
3. Brief window where both old and new passwords could work

**Impact:**
- Brief window where compromised password could still be used
- Race condition in security-critical operation

**Recommendation:**
1. Consider blacklisting old password hash in Redis
2. Add PocketBase-level password change validation
3. Ensure atomic password + session invalidation

---

## Summary

### Critical Vulnerabilities Found: 3
1. User vacation days missing institution filtering (3 endpoints)
2. Admin priority update missing institution filtering
3. Admin priority delete missing institution filtering

### High Severity Issues: 3
4. Legacy magic word endpoints
5. Missing rate limiting on user endpoints
6. Change password race condition

### Recommended Fix Priority:
1. **IMMEDIATE:** Fix all 3 CRITICAL vulnerabilities (vacation days, priority update/delete)
2. **HIGH:** Add rate limiting to user vacation days endpoints
3. **MEDIUM:** Review and remove/deprecate legacy magic word endpoints
4. **LOW:** Improve change password session invalidation

## Testing Recommendations
After fixes are applied, add integration tests for:
1. Users cannot see vacation days from other institutions
2. Institution admins cannot update/delete priorities from other institutions
3. Rate limiting is enforced on user vacation day endpoints

---

**Audit Performed By:** Claude (AI Security Audit)
**Next Steps:** Fix critical vulnerabilities immediately and add comprehensive tests
