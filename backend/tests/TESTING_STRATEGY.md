# Testing Strategy for Multi-Institution Support

This document outlines the testing approach for the multi-institution functionality.

## Testing Philosophy

We follow a **minimal mocking** approach:
- **Unit tests** mock only external dependencies (httpx for PocketBase API calls)
- **Integration tests** use real infrastructure (PocketBase + Redis in containers)
- **No redundant tests** - we removed API route tests that duplicated integration test coverage

## Test Structure

### Unit Tests (Fast, Isolated)

#### `tests/services/test_institution.py` (13 tests)
Tests the InstitutionService business logic in isolation.

**What we mock:** Only `httpx.AsyncClient` (external HTTP calls to PocketBase)

**What we test:**
- Institution CRUD operations
- Error handling (404, 400, 500)
- Service account authentication fallback
- Query parameter construction
- Response parsing

**Why:** These tests verify service layer logic without spinning up containers. They're fast and can run anywhere.

#### `tests/test_permissions.py` (20 tests)
Tests the permission system and role hierarchy.

**What we mock:** Nothing - pure Python logic

**What we test:**
- `require_admin()` accepts all admin types
- `require_institution_admin()` enforcement
- `require_super_admin()` strict enforcement
- Role hierarchy (super_admin > institution_admin > user)
- Data isolation logic
- SessionInfo model behavior

**Why:** Permission logic is pure Python with no external dependencies.

### Integration Tests (Real Infrastructure)

#### `tests/integration/test_multi_institution_integration.py` (9 tests)
End-to-end tests with real PocketBase and Redis.

**What we mock:** Nothing - uses real containers via testcontainers

**What we test:**
- Creating institutions in PocketBase
- Querying institutions by short code
- Public API endpoints (list, get by short code)
- Magic word verification flow
- User registration with institutions
- Data isolation between institutions
- Redis token storage

**Why:** These verify the entire system works together. They catch integration issues, database schema problems, and API contract violations that unit tests can't find.

**Fixtures used:**
- `pocketbase_container` - Real PocketBase in Docker
- `redis_container` - Real Redis in Docker
- `pocketbase_admin_client` - Authenticated admin HTTP client
- `test_app` - FastAPI TestClient with real dependencies
- `clean_redis` - Fresh Redis instance per test

## Running Tests

```bash
# Run all tests
uv run pytest

# Run only fast unit tests
uv run pytest tests/services tests/test_permissions.py -v

# Run only integration tests (requires Docker)
uv run pytest tests/integration -v -m integration

# Run without coverage for faster execution
uv run pytest --no-cov
```

## What We Don't Test

We intentionally removed:
- `tests/api/routes/test_institutions.py` - Redundant with integration tests
- `tests/api/routes/test_auth_multi_institution.py` - Redundant with integration tests

These were heavily mocked API route tests that provided no value over integration tests.

## Test Coverage

### Unit Tests Cover:
✓ Service layer business logic
✓ Permission enforcement
✓ Error handling
✓ Edge cases

### Integration Tests Cover:
✓ Database operations
✓ API contracts
✓ Authentication flows
✓ Data isolation
✓ Redis integration
✓ End-to-end scenarios

## Adding New Tests

**For new service methods:**
Add unit tests in `tests/services/test_institution.py` that mock httpx calls.

**For new API endpoints:**
Add integration tests in `tests/integration/test_multi_institution_integration.py` that use real containers.

**For new permission logic:**
Add unit tests in `tests/test_permissions.py`.

## CI/CD Considerations

Unit tests run quickly and should run on every commit.
Integration tests require Docker and should run on PRs and main branch.

Consider separating:
```bash
# Fast feedback (< 5 seconds)
pytest tests/services tests/test_permissions.py

# Full validation (requires Docker, ~30 seconds)
pytest tests/integration
```
