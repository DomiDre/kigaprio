"""
Security integration tests for multi-institution data isolation.

These tests verify that institution admins CANNOT access other institutions' data
and that data isolation is properly enforced at the API level.
"""

import pytest


@pytest.mark.integration
class TestInstitutionDataIsolation:
    """Test that institution admins cannot access other institutions' data."""

    def test_institution_admin_cannot_see_other_institutions_users(
        self, test_app, pocketbase_admin_client
    ):
        """
        Test that institution admin A cannot see users from institution B.

        This is a CRITICAL security test.
        """
        # Create two institutions
        inst_a = pocketbase_admin_client.post(
            "/api/collections/institutions/records",
            json={
                "name": "Institution A",
                "short_code": "INST_A",
                "registration_magic_word": "MagicA123",
                "active": True,
            },
        ).json()

        inst_b = pocketbase_admin_client.post(
            "/api/collections/institutions/records",
            json={
                "name": "Institution B",
                "short_code": "INST_B",
                "registration_magic_word": "MagicB456",
                "active": True,
            },
        ).json()

        # Register user in Institution A
        user_a_response = test_app.post(
            "/api/v1/auth/register-qr",
            json={
                "identity": "user_a@insta.edu",
                "password": "PassA123!",
                "passwordConfirm": "PassA123!",
                "name": "User A",
                "magic_word": "MagicA123",
                "institution_short_code": "INST_A",
                "keep_logged_in": False,
            },
        )
        assert user_a_response.status_code == 200

        # Register institution admin in Institution A
        admin_a_response = test_app.post(
            "/api/v1/auth/register-qr",
            json={
                "identity": "admin_a@insta.edu",
                "password": "AdminA123!",
                "passwordConfirm": "AdminA123!",
                "name": "Admin A",
                "magic_word": "MagicA123",
                "institution_short_code": "INST_A",
                "keep_logged_in": True,
            },
        )
        assert admin_a_response.status_code == 200
        admin_a_user_id = admin_a_response.json()["user"]["id"]

        # Elevate admin A to institution_admin
        pocketbase_admin_client.patch(
            f"/api/collections/users/records/{admin_a_user_id}",
            json={"role": "institution_admin"},
        )

        # Register user in Institution B
        user_b_response = test_app.post(
            "/api/v1/auth/register-qr",
            json={
                "identity": "user_b@instb.edu",
                "password": "PassB123!",
                "passwordConfirm": "PassB123!",
                "name": "User B",
                "magic_word": "MagicB456",
                "institution_short_code": "INST_B",
                "keep_logged_in": False,
            },
        )
        assert user_b_response.status_code == 200
        user_b_data = user_b_response.json()["user"]

        # Login as admin A
        login_response = test_app.post(
            "/api/v1/auth/login",
            json={
                "identity": "admin_a@insta.edu",
                "password": "AdminA123!",
                "keep_logged_in": True,
            },
        )
        assert login_response.status_code == 200

        # Try to access user B's details (should fail - different institution)
        user_b_detail_response = test_app.get(
            f"/api/v1/admin/users/detail/{user_b_data['id']}"
        )
        assert user_b_detail_response.status_code == 403

        # Try to access user B by username (should return 404/no access)
        user_b_info_response = test_app.get(
            f"/api/v1/admin/users/info/{user_b_data['username']}"
        )
        assert user_b_info_response.status_code in [404, 403]

    def test_institution_admin_cannot_see_other_institutions_priorities(
        self, test_app, pocketbase_admin_client
    ):
        """
        Test that institution admin A cannot see priorities from institution B.

        This is a CRITICAL security test.
        """
        # Create two institutions
        inst_a = pocketbase_admin_client.post(
            "/api/collections/institutions/records",
            json={
                "name": "Institution A Priority Test",
                "short_code": "INST_A_PRIO",
                "registration_magic_word": "MagicA789",
                "active": True,
            },
        ).json()

        inst_b = pocketbase_admin_client.post(
            "/api/collections/institutions/records",
            json={
                "name": "Institution B Priority Test",
                "short_code": "INST_B_PRIO",
                "registration_magic_word": "MagicB789",
                "active": True,
            },
        ).json()

        # Create a priority for institution B directly in PocketBase
        priority_b = pocketbase_admin_client.post(
            "/api/collections/priorities/records",
            json={
                "userId": "test_user_b",
                "month": "2025-01",
                "institution_id": inst_b["id"],
                "manual": False,
                "identifier": None,
                "encrypted_fields": "encrypted_data_b",
            },
        ).json()

        # Register institution admin in Institution A
        admin_a_response = test_app.post(
            "/api/v1/auth/register-qr",
            json={
                "identity": "admin_a_prio@insta.edu",
                "password": "AdminA789!",
                "passwordConfirm": "AdminA789!",
                "name": "Admin A Priority",
                "magic_word": "MagicA789",
                "institution_short_code": "INST_A_PRIO",
                "keep_logged_in": True,
            },
        )
        assert admin_a_response.status_code == 200
        admin_a_user_id = admin_a_response.json()["user"]["id"]

        # Elevate admin A to institution_admin
        pocketbase_admin_client.patch(
            f"/api/collections/users/records/{admin_a_user_id}",
            json={"role": "institution_admin"},
        )

        # Login as admin A
        login_response = test_app.post(
            "/api/v1/auth/login",
            json={
                "identity": "admin_a_prio@insta.edu",
                "password": "AdminA789!",
                "keep_logged_in": True,
            },
        )
        assert login_response.status_code == 200

        # Get user submissions for 2025-01 (should NOT include institution B's priority)
        submissions_response = test_app.get("/api/v1/admin/users/2025-01")
        assert submissions_response.status_code == 200
        submissions = submissions_response.json()

        # Verify that institution B's priority is NOT in the results
        priority_ids = [s["priorityId"] for s in submissions]
        assert priority_b["id"] not in priority_ids

    def test_institution_admin_cannot_update_other_institutions_users(
        self, test_app, pocketbase_admin_client
    ):
        """
        Test that institution admin A cannot update users from institution B.

        This is a CRITICAL security test.
        """
        # Create two institutions
        inst_a = pocketbase_admin_client.post(
            "/api/collections/institutions/records",
            json={
                "name": "Institution A Update Test",
                "short_code": "INST_A_UPD",
                "registration_magic_word": "MagicA_upd",
                "active": True,
            },
        ).json()

        inst_b = pocketbase_admin_client.post(
            "/api/collections/institutions/records",
            json={
                "name": "Institution B Update Test",
                "short_code": "INST_B_UPD",
                "registration_magic_word": "MagicB_upd",
                "active": True,
            },
        ).json()

        # Register user in Institution B
        user_b_response = test_app.post(
            "/api/v1/auth/register-qr",
            json={
                "identity": "user_b_upd@instb.edu",
                "password": "PassB_upd!",
                "passwordConfirm": "PassB_upd!",
                "name": "User B Update",
                "magic_word": "MagicB_upd",
                "institution_short_code": "INST_B_UPD",
                "keep_logged_in": False,
            },
        )
        assert user_b_response.status_code == 200
        user_b_id = user_b_response.json()["user"]["id"]

        # Register institution admin in Institution A
        admin_a_response = test_app.post(
            "/api/v1/auth/register-qr",
            json={
                "identity": "admin_a_upd@insta.edu",
                "password": "AdminA_upd!",
                "passwordConfirm": "AdminA_upd!",
                "name": "Admin A Update",
                "magic_word": "MagicA_upd",
                "institution_short_code": "INST_A_UPD",
                "keep_logged_in": True,
            },
        )
        assert admin_a_response.status_code == 200
        admin_a_user_id = admin_a_response.json()["user"]["id"]

        # Elevate admin A to institution_admin
        pocketbase_admin_client.patch(
            f"/api/collections/users/records/{admin_a_user_id}",
            json={"role": "institution_admin"},
        )

        # Login as admin A
        login_response = test_app.post(
            "/api/v1/auth/login",
            json={
                "identity": "admin_a_upd@insta.edu",
                "password": "AdminA_upd!",
                "keep_logged_in": True,
            },
        )
        assert login_response.status_code == 200

        # Try to update user B (should fail - different institution)
        update_response = test_app.put(
            f"/api/v1/admin/users/{user_b_id}",
            json={"username": "hacked_username"},
        )
        assert update_response.status_code == 403

    def test_institution_admin_cannot_delete_other_institutions_users(
        self, test_app, pocketbase_admin_client
    ):
        """
        Test that institution admin A cannot delete users from institution B.

        This is a CRITICAL security test.
        """
        # Create two institutions
        inst_a = pocketbase_admin_client.post(
            "/api/collections/institutions/records",
            json={
                "name": "Institution A Delete Test",
                "short_code": "INST_A_DEL",
                "registration_magic_word": "MagicA_del",
                "active": True,
            },
        ).json()

        inst_b = pocketbase_admin_client.post(
            "/api/collections/institutions/records",
            json={
                "name": "Institution B Delete Test",
                "short_code": "INST_B_DEL",
                "registration_magic_word": "MagicB_del",
                "active": True,
            },
        ).json()

        # Register user in Institution B
        user_b_response = test_app.post(
            "/api/v1/auth/register-qr",
            json={
                "identity": "user_b_del@instb.edu",
                "password": "PassB_del!",
                "passwordConfirm": "PassB_del!",
                "name": "User B Delete",
                "magic_word": "MagicB_del",
                "institution_short_code": "INST_B_DEL",
                "keep_logged_in": False,
            },
        )
        assert user_b_response.status_code == 200
        user_b_id = user_b_response.json()["user"]["id"]

        # Register institution admin in Institution A
        admin_a_response = test_app.post(
            "/api/v1/auth/register-qr",
            json={
                "identity": "admin_a_del@insta.edu",
                "password": "AdminA_del!",
                "passwordConfirm": "AdminA_del!",
                "name": "Admin A Delete",
                "magic_word": "MagicA_del",
                "institution_short_code": "INST_A_DEL",
                "keep_logged_in": True,
            },
        )
        assert admin_a_response.status_code == 200
        admin_a_user_id = admin_a_response.json()["user"]["id"]

        # Elevate admin A to institution_admin
        pocketbase_admin_client.patch(
            f"/api/collections/users/records/{admin_a_user_id}",
            json={"role": "institution_admin"},
        )

        # Login as admin A
        login_response = test_app.post(
            "/api/v1/auth/login",
            json={
                "identity": "admin_a_del@insta.edu",
                "password": "AdminA_del!",
                "keep_logged_in": True,
            },
        )
        assert login_response.status_code == 200

        # Try to delete user B (should fail - different institution)
        delete_response = test_app.delete(f"/api/v1/admin/users/{user_b_id}")
        assert delete_response.status_code == 403

        # Verify user B still exists
        user_check = pocketbase_admin_client.get(
            f"/api/collections/users/records/{user_b_id}"
        )
        assert user_check.status_code == 200

    def test_institution_admin_total_users_count_is_filtered(
        self, test_app, pocketbase_admin_client
    ):
        """
        Test that institution admin only sees user count from their institution.

        This is a CRITICAL security test.
        """
        # Create two institutions
        inst_a = pocketbase_admin_client.post(
            "/api/collections/institutions/records",
            json={
                "name": "Institution A Count Test",
                "short_code": "INST_A_CNT",
                "registration_magic_word": "MagicA_cnt",
                "active": True,
            },
        ).json()

        inst_b = pocketbase_admin_client.post(
            "/api/collections/institutions/records",
            json={
                "name": "Institution B Count Test",
                "short_code": "INST_B_CNT",
                "registration_magic_word": "MagicB_cnt",
                "active": True,
            },
        ).json()

        # Register 2 users in Institution A
        for i in range(2):
            test_app.post(
                "/api/v1/auth/register-qr",
                json={
                    "identity": f"user_a{i}@insta.edu",
                    "password": f"PassA{i}!",
                    "passwordConfirm": f"PassA{i}!",
                    "name": f"User A{i}",
                    "magic_word": "MagicA_cnt",
                    "institution_short_code": "INST_A_CNT",
                    "keep_logged_in": False,
                },
            )

        # Register 3 users in Institution B
        for i in range(3):
            test_app.post(
                "/api/v1/auth/register-qr",
                json={
                    "identity": f"user_b{i}@instb.edu",
                    "password": f"PassB{i}!",
                    "passwordConfirm": f"PassB{i}!",
                    "name": f"User B{i}",
                    "magic_word": "MagicB_cnt",
                    "institution_short_code": "INST_B_CNT",
                    "keep_logged_in": False,
                },
            )

        # Register institution admin in Institution A
        admin_a_response = test_app.post(
            "/api/v1/auth/register-qr",
            json={
                "identity": "admin_a_cnt@insta.edu",
                "password": "AdminA_cnt!",
                "passwordConfirm": "AdminA_cnt!",
                "name": "Admin A Count",
                "magic_word": "MagicA_cnt",
                "institution_short_code": "INST_A_CNT",
                "keep_logged_in": True,
            },
        )
        assert admin_a_response.status_code == 200
        admin_a_user_id = admin_a_response.json()["user"]["id"]

        # Elevate admin A to institution_admin
        pocketbase_admin_client.patch(
            f"/api/collections/users/records/{admin_a_user_id}",
            json={"role": "institution_admin"},
        )

        # Login as admin A
        login_response = test_app.post(
            "/api/v1/auth/login",
            json={
                "identity": "admin_a_cnt@insta.edu",
                "password": "AdminA_cnt!",
                "keep_logged_in": True,
            },
        )
        assert login_response.status_code == 200

        # Get total users (should only count institution A users)
        total_users_response = test_app.get("/api/v1/admin/total-users")
        assert total_users_response.status_code == 200
        total_users_data = total_users_response.json()

        # Should see 2 users + 1 admin = 3 total for institution A
        assert total_users_data["totalUsers"] == 3


@pytest.mark.integration
class TestSuperAdminAccess:
    """Test that super admins CAN access all institutions' data."""

    def test_super_admin_can_see_all_institutions_users(
        self, test_app, pocketbase_admin_client
    ):
        """
        Test that super admin can see users from all institutions.
        """
        # Create two institutions
        inst_a = pocketbase_admin_client.post(
            "/api/collections/institutions/records",
            json={
                "name": "Institution A Super Test",
                "short_code": "INST_A_SUP",
                "registration_magic_word": "MagicA_sup",
                "active": True,
            },
        ).json()

        inst_b = pocketbase_admin_client.post(
            "/api/collections/institutions/records",
            json={
                "name": "Institution B Super Test",
                "short_code": "INST_B_SUP",
                "registration_magic_word": "MagicB_sup",
                "active": True,
            },
        ).json()

        # Register user in Institution A
        user_a_response = test_app.post(
            "/api/v1/auth/register-qr",
            json={
                "identity": "user_a_sup@insta.edu",
                "password": "PassA_sup!",
                "passwordConfirm": "PassA_sup!",
                "name": "User A Super",
                "magic_word": "MagicA_sup",
                "institution_short_code": "INST_A_SUP",
                "keep_logged_in": False,
            },
        )
        assert user_a_response.status_code == 200
        user_a_id = user_a_response.json()["user"]["id"]

        # Register user in Institution B
        user_b_response = test_app.post(
            "/api/v1/auth/register-qr",
            json={
                "identity": "user_b_sup@instb.edu",
                "password": "PassB_sup!",
                "passwordConfirm": "PassB_sup!",
                "name": "User B Super",
                "magic_word": "MagicB_sup",
                "institution_short_code": "INST_B_SUP",
                "keep_logged_in": False,
            },
        )
        assert user_b_response.status_code == 200
        user_b_id = user_b_response.json()["user"]["id"]

        # Create super admin directly in PocketBase (no institution)
        super_admin = pocketbase_admin_client.post(
            "/api/collections/users/records",
            json={
                "username": "super_admin_test",
                "password": "SuperAdmin123!",
                "passwordConfirm": "SuperAdmin123!",
                "role": "super_admin",
                "institution_id": None,
            },
        ).json()

        # Login as super admin
        login_response = test_app.post(
            "/api/v1/auth/login",
            json={
                "identity": "super_admin_test",
                "password": "SuperAdmin123!",
                "keep_logged_in": True,
            },
        )
        assert login_response.status_code == 200

        # Super admin should be able to access user A
        user_a_detail = test_app.get(f"/api/v1/admin/users/detail/{user_a_id}")
        assert user_a_detail.status_code == 200

        # Super admin should be able to access user B
        user_b_detail = test_app.get(f"/api/v1/admin/users/detail/{user_b_id}")
        assert user_b_detail.status_code == 200

    def test_super_admin_total_users_includes_all_institutions(
        self, test_app, pocketbase_admin_client
    ):
        """
        Test that super admin sees total user count across all institutions.
        """
        # Create two institutions
        inst_a = pocketbase_admin_client.post(
            "/api/collections/institutions/records",
            json={
                "name": "Institution A Total Test",
                "short_code": "INST_A_TOT",
                "registration_magic_word": "MagicA_tot",
                "active": True,
            },
        ).json()

        inst_b = pocketbase_admin_client.post(
            "/api/collections/institutions/records",
            json={
                "name": "Institution B Total Test",
                "short_code": "INST_B_TOT",
                "registration_magic_word": "MagicB_tot",
                "active": True,
            },
        ).json()

        # Register 2 users in Institution A
        for i in range(2):
            test_app.post(
                "/api/v1/auth/register-qr",
                json={
                    "identity": f"user_a_tot{i}@insta.edu",
                    "password": f"PassA_tot{i}!",
                    "passwordConfirm": f"PassA_tot{i}!",
                    "name": f"User A Tot {i}",
                    "magic_word": "MagicA_tot",
                    "institution_short_code": "INST_A_TOT",
                    "keep_logged_in": False,
                },
            )

        # Register 3 users in Institution B
        for i in range(3):
            test_app.post(
                "/api/v1/auth/register-qr",
                json={
                    "identity": f"user_b_tot{i}@instb.edu",
                    "password": f"PassB_tot{i}!",
                    "passwordConfirm": f"PassB_tot{i}!",
                    "name": f"User B Tot {i}",
                    "magic_word": "MagicB_tot",
                    "institution_short_code": "INST_B_TOT",
                    "keep_logged_in": False,
                },
            )

        # Create super admin directly in PocketBase (no institution)
        super_admin = pocketbase_admin_client.post(
            "/api/collections/users/records",
            json={
                "username": "super_admin_total_test",
                "password": "SuperAdminTotal123!",
                "passwordConfirm": "SuperAdminTotal123!",
                "role": "super_admin",
                "institution_id": None,
            },
        ).json()

        # Login as super admin
        login_response = test_app.post(
            "/api/v1/auth/login",
            json={
                "identity": "super_admin_total_test",
                "password": "SuperAdminTotal123!",
                "keep_logged_in": True,
            },
        )
        assert login_response.status_code == 200

        # Get total users (should include all institutions)
        total_users_response = test_app.get("/api/v1/admin/total-users")
        assert total_users_response.status_code == 200
        total_users_data = total_users_response.json()

        # Should see at least 2 + 3 = 5 users (could be more from other tests)
        assert total_users_data["totalUsers"] >= 5
