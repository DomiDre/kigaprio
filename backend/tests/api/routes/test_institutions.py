"""
Tests for institution API routes.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

from priotag.main import app


client = TestClient(app)


class TestPublicInstitutionEndpoints:
    """Test public institution endpoints (no auth required)."""

    @patch("priotag.api.routes.institutions.InstitutionService.list_institutions")
    def test_list_institutions_success(
        self, mock_list, sample_institution_data, sample_institution_data_2
    ):
        """Test listing active institutions."""
        # Mock the service
        from priotag.models.pocketbase_schemas import InstitutionRecord

        mock_list.return_value = [
            InstitutionRecord(**sample_institution_data),
            InstitutionRecord(**sample_institution_data_2),
        ]

        # Test
        response = client.get("/api/v1/institutions")

        # Verify
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["short_code"] == "TEST_UNIV"
        assert data[1]["short_code"] == "SECOND_UNIV"
        # Verify only public fields are returned
        assert "id" in data[0]
        assert "name" in data[0]
        assert "short_code" in data[0]
        assert "active" in data[0]
        assert "created" in data[0]
        assert "updated" in data[0]
        # Verify sensitive fields are NOT returned
        assert "registration_magic_word" not in data[0]
        assert "admin_public_key" not in data[0]
        assert "settings" not in data[0]

    @patch("priotag.api.routes.institutions.InstitutionService.get_by_short_code")
    def test_get_institution_by_short_code_success(
        self, mock_get, sample_institution_data
    ):
        """Test getting institution by short code."""
        from priotag.models.pocketbase_schemas import InstitutionRecord

        mock_get.return_value = InstitutionRecord(**sample_institution_data)

        # Test
        response = client.get("/api/v1/institutions/TEST_UNIV")

        # Verify
        assert response.status_code == 200
        data = response.json()
        assert data["short_code"] == "TEST_UNIV"
        assert data["name"] == "Test University"
        # Verify sensitive fields are NOT returned
        assert "registration_magic_word" not in data

    @patch("priotag.api.routes.institutions.InstitutionService.get_by_short_code")
    def test_get_institution_by_short_code_not_found(self, mock_get):
        """Test getting non-existent institution returns 404."""
        from fastapi import HTTPException

        mock_get.side_effect = HTTPException(status_code=404, detail="Not found")

        # Test
        response = client.get("/api/v1/institutions/NONEXISTENT")

        # Verify
        assert response.status_code == 404


class TestSuperAdminInstitutionEndpoints:
    """Test super admin institution endpoints."""

    @patch("priotag.api.routes.institutions.InstitutionService.list_institutions")
    @patch("priotag.utils.verify_token")
    @patch("priotag.utils.get_current_token")
    def test_list_all_institutions_as_super_admin(
        self,
        mock_get_token,
        mock_verify,
        mock_list,
        sample_super_admin_session_info,
        sample_institution_data,
    ):
        """Test super admin can list all institutions with detailed info."""
        from priotag.models.pocketbase_schemas import InstitutionRecord

        mock_get_token.return_value = "super_admin_token"
        mock_verify.return_value = sample_super_admin_session_info
        mock_list.return_value = [InstitutionRecord(**sample_institution_data)]

        # Test
        response = client.get(
            "/api/v1/admin/super/institutions",
            cookies={"auth_token": "super_admin_token"},
        )

        # Verify
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        # Verify detailed fields ARE returned for super admin
        assert "registration_magic_word" in data[0]
        assert "admin_public_key" in data[0]
        assert "settings" in data[0]

    @patch("priotag.utils.verify_token")
    @patch("priotag.utils.get_current_token")
    def test_list_all_institutions_as_regular_user_forbidden(
        self, mock_get_token, mock_verify, sample_session_info
    ):
        """Test regular user cannot list all institutions."""
        mock_get_token.return_value = "user_token"
        mock_verify.return_value = sample_session_info

        # Test
        response = client.get(
            "/api/v1/admin/super/institutions", cookies={"auth_token": "user_token"}
        )

        # Verify
        assert response.status_code == 403

    @patch("priotag.api.routes.institutions.InstitutionService.create_institution")
    @patch("priotag.utils.verify_token")
    @patch("priotag.utils.get_current_token")
    def test_create_institution_as_super_admin(
        self,
        mock_get_token,
        mock_verify,
        mock_create,
        sample_super_admin_session_info,
        sample_institution_data,
    ):
        """Test super admin can create institutions."""
        from priotag.models.pocketbase_schemas import InstitutionRecord

        mock_get_token.return_value = "super_admin_token"
        mock_verify.return_value = sample_super_admin_session_info
        mock_create.return_value = InstitutionRecord(**sample_institution_data)

        # Test
        response = client.post(
            "/api/v1/admin/super/institutions",
            json={
                "name": "New University",
                "short_code": "NEW_UNIV",
                "registration_magic_word": "NewMagic123",
            },
            cookies={"auth_token": "super_admin_token"},
        )

        # Verify
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test University"  # From mock

    @patch("priotag.api.routes.institutions.InstitutionService.update_institution")
    @patch("priotag.utils.verify_token")
    @patch("priotag.utils.get_current_token")
    def test_update_institution_as_super_admin(
        self,
        mock_get_token,
        mock_verify,
        mock_update,
        sample_super_admin_session_info,
        sample_institution_data,
    ):
        """Test super admin can update institutions."""
        from priotag.models.pocketbase_schemas import InstitutionRecord

        updated_data = sample_institution_data.copy()
        updated_data["name"] = "Updated University"

        mock_get_token.return_value = "super_admin_token"
        mock_verify.return_value = sample_super_admin_session_info
        mock_update.return_value = InstitutionRecord(**updated_data)

        # Test
        response = client.put(
            "/api/v1/admin/super/institutions/institution_123",
            json={"name": "Updated University"},
            cookies={"auth_token": "super_admin_token"},
        )

        # Verify
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated University"


class TestInstitutionAdminEndpoints:
    """Test institution admin endpoints."""

    @patch("priotag.api.routes.institutions.InstitutionService.get_institution")
    @patch("priotag.utils.verify_token")
    @patch("priotag.utils.get_current_token")
    def test_get_own_institution_as_institution_admin(
        self,
        mock_get_token,
        mock_verify,
        mock_get,
        sample_admin_session_info,
        sample_institution_data,
    ):
        """Test institution admin can view their own institution."""
        from priotag.models.pocketbase_schemas import InstitutionRecord

        mock_get_token.return_value = "admin_token"
        mock_verify.return_value = sample_admin_session_info
        mock_get.return_value = InstitutionRecord(**sample_institution_data)

        # Test
        response = client.get(
            "/api/v1/admin/institution/info", cookies={"auth_token": "admin_token"}
        )

        # Verify
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "institution_123"
        # Institution admin can see magic word
        assert "registration_magic_word" in data

    @patch("priotag.utils.verify_token")
    @patch("priotag.utils.get_current_token")
    def test_get_own_institution_without_institution_id(
        self, mock_get_token, mock_verify
    ):
        """Test user without institution_id gets error."""
        from priotag.models.auth import SessionInfo

        session_without_inst = SessionInfo(
            id="user_123",
            username="user",
            is_admin=False,
            role="user",
            institution_id=None,
        )

        mock_get_token.return_value = "user_token"
        mock_verify.return_value = session_without_inst

        # Test
        response = client.get(
            "/api/v1/admin/institution/info", cookies={"auth_token": "user_token"}
        )

        # Verify
        assert response.status_code == 400

    @patch("priotag.api.routes.institutions.InstitutionService.update_magic_word")
    @patch("priotag.utils.verify_token")
    @patch("priotag.utils.get_current_token")
    def test_update_magic_word_as_institution_admin(
        self,
        mock_get_token,
        mock_verify,
        mock_update,
        sample_admin_session_info,
        sample_institution_data,
    ):
        """Test institution admin can update their institution's magic word."""
        from priotag.models.pocketbase_schemas import InstitutionRecord

        updated_data = sample_institution_data.copy()
        updated_data["registration_magic_word"] = "NewMagic999"

        mock_get_token.return_value = "admin_token"
        mock_verify.return_value = sample_admin_session_info
        mock_update.return_value = InstitutionRecord(**updated_data)

        # Test
        response = client.patch(
            "/api/v1/admin/institution/magic-word",
            json={"magic_word": "NewMagic999"},
            cookies={"auth_token": "admin_token"},
        )

        # Verify
        assert response.status_code == 200
        data = response.json()
        assert data["registration_magic_word"] == "NewMagic999"

    @patch("priotag.utils.verify_token")
    @patch("priotag.utils.get_current_token")
    def test_update_magic_word_as_regular_user_forbidden(
        self, mock_get_token, mock_verify, sample_session_info
    ):
        """Test regular user cannot update magic word."""
        mock_get_token.return_value = "user_token"
        mock_verify.return_value = sample_session_info

        # Test
        response = client.patch(
            "/api/v1/admin/institution/magic-word",
            json={"magic_word": "NewMagic"},
            cookies={"auth_token": "user_token"},
        )

        # Verify
        assert response.status_code == 403
