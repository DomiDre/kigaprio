# Backend Tests

[![codecov](https://codecov.io/gh/DomiDre/priotag/graph/badge.svg?token=1XUOS5Y6GF)](https://codecov.io/gh/DomiDre/priotag)

This directory contains comprehensive tests for the PrioTag backend application, including both unit tests and integration tests.

## Test Structure

```
tests/
├── conftest.py              # Shared pytest fixtures for unit tests
├── test_main.py             # Basic application tests
├── test_utils.py            # Tests for utility functions (auth, session management)
├── services/
│   ├── __init__.py
│   └── test_encryption.py   # Encryption service tests
└── integration/
    ├── __init__.py
    ├── conftest.py          # Integration test fixtures (Redis, PocketBase containers)
    ├── helpers.py           # Test helper utilities
    └── test_auth_integration.py  # Integration tests for auth routes
```

## Test Types

### Unit Tests
Unit tests use mocked dependencies (FakeRedis, mocked HTTP clients) for fast, isolated testing. They run by default with `uv run pytest`.

### Integration Tests
Integration tests use real Redis and PocketBase containers via testcontainers. These tests verify the full application flow with actual external dependencies.

**Running integration tests:**
```bash
# Run integration tests only
uv run pytest -m integration

# Run all tests (unit + integration)
uv run pytest -m ""
```

**Requirements for integration tests:**
- Docker must be running (testcontainers will start containers automatically)
- First run may be slow as Docker images are pulled

## Test Coverage

### Unit Tests

#### Authentication & Authorization Tests (`test_utils.py`)
**22 tests covering utility functions:**
- Token extraction from cookies (get_current_token, get_current_dek)
- Session verification and Redis caching
- Admin authorization checks
- Session info extraction from PocketBase records
- Client IP detection from request headers
- Last seen timestamp updates with throttling

#### Encryption Service (`services/test_encryption.py`)
**45 tests covering encryption functionality:**
- DEK and salt generation
- PBKDF2 password-based key derivation
- AES-256-GCM encryption/decryption
- RSA-OAEP key wrapping with admin public key
- Field-level encryption for dictionaries
- Password change with DEK preservation
- Security tests (tampering detection, proper iterations, etc.)

### Integration Tests

#### Authentication Integration (`integration/test_auth_integration.py`)
Integration tests for the full authentication flow:
- User registration with real PocketBase database
- Login flow with actual token generation and Redis session storage
- Session verification with real dependencies
- Logout and session cleanup
- Invalid credential handling

**Total Unit Tests: 67 | Integration Tests: 3**

## Running Tests

```bash
# Run only unit tests (default - fast)
uv run pytest

# Run integration tests (requires Docker)
uv run pytest -m integration

# Run all tests (unit + integration)
uv run pytest -m ""

# Run specific test file
uv run pytest tests/test_utils.py

# Run specific test class
uv run pytest tests/test_utils.py::TestVerifyToken

# Run with coverage report
uv run pytest --cov=src/priotag --cov-report=html
```

## Test Fixtures

### Unit Test Fixtures (`conftest.py`)
- `fake_redis` - FakeRedis instance for testing without real Redis
- `admin_rsa_keypair` - RSA keypair for encryption testing
- `sample_user_data` - Sample user record data
- `sample_admin_data` - Sample admin user record data
- `sample_priority_data` - Sample priority record data
- `sample_session_info` - Sample session information
- `test_dek` - Test Data Encryption Key

### Integration Test Fixtures (`integration/conftest.py`)
- `redis_container` - Real Redis container via testcontainers
- `redis_client` - Connected Redis client
- `clean_redis` - Redis instance that's flushed before/after each test
- `pocketbase_container` - Real PocketBase container
- `pocketbase_url` - URL to PocketBase instance
- `pocketbase_admin_client` - Authenticated admin client for PocketBase
- `setup_pocketbase_schema` - Automatically creates collections schema
- `test_app` - FastAPI TestClient with real dependencies

## Test Philosophy

### Unit Tests
- Each test is isolated and independent
- External dependencies (Redis, PocketBase) are mocked
- Tests focus on single units of functionality
- Fast execution (no real network calls or database operations)
- Comprehensive edge case coverage

### Integration Tests
- Test the full application flow with real dependencies
- Use Docker containers for Redis and PocketBase
- Verify actual encryption, database operations, and caching
- Slower but provide high confidence that the system works end-to-end
- Automatically managed containers (start/stop handled by testcontainers)
