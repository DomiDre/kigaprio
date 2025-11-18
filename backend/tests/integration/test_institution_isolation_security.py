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
        pocketbase_admin_client.post(
            "/api/collections/institutions/records",
            json={
                "name": "Institution A",
                "short_code": "INST_A",
                "registration_magic_word": "MagicA123",
                "active": True,
            },
        ).json()

        pocketbase_admin_client.post(
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
        pocketbase_admin_client.post(
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
        pocketbase_admin_client.post(
            "/api/collections/institutions/records",
            json={
                "name": "Institution A Update Test",
                "short_code": "INST_A_UPD",
                "registration_magic_word": "MagicA_upd",
                "active": True,
            },
        ).json()

        pocketbase_admin_client.post(
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
        pocketbase_admin_client.post(
            "/api/collections/institutions/records",
            json={
                "name": "Institution A Delete Test",
                "short_code": "INST_A_DEL",
                "registration_magic_word": "MagicA_del",
                "active": True,
            },
        ).json()

        pocketbase_admin_client.post(
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
        pocketbase_admin_client.post(
            "/api/collections/institutions/records",
            json={
                "name": "Institution A Count Test",
                "short_code": "INST_A_CNT",
                "registration_magic_word": "MagicA_cnt",
                "active": True,
            },
        ).json()

        pocketbase_admin_client.post(
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
        pocketbase_admin_client.post(
            "/api/collections/institutions/records",
            json={
                "name": "Institution A Super Test",
                "short_code": "INST_A_SUP",
                "registration_magic_word": "MagicA_sup",
                "active": True,
            },
        ).json()

        pocketbase_admin_client.post(
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
        pocketbase_admin_client.post(
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
        pocketbase_admin_client.post(
            "/api/collections/institutions/records",
            json={
                "name": "Institution A Total Test",
                "short_code": "INST_A_TOT",
                "registration_magic_word": "MagicA_tot",
                "active": True,
            },
        ).json()

        pocketbase_admin_client.post(
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
        pocketbase_admin_client.post(
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


@pytest.mark.integration
class TestVacationDaysIsolation:
    """Test that vacation days are properly isolated between institutions."""

    def test_institution_admin_cannot_see_other_institutions_vacation_days(
        self, test_app, pocketbase_admin_client
    ):
        """
        Test that institution admin A cannot see vacation days from institution B.

        This is a CRITICAL security test.
        """
        # Create two institutions
        pocketbase_admin_client.post(
            "/api/collections/institutions/records",
            json={
                "name": "Institution A Vacation Test",
                "short_code": "INST_A_VAC",
                "registration_magic_word": "MagicA_vac",
                "active": True,
            },
        ).json()

        inst_b = pocketbase_admin_client.post(
            "/api/collections/institutions/records",
            json={
                "name": "Institution B Vacation Test",
                "short_code": "INST_B_VAC",
                "registration_magic_word": "MagicB_vac",
                "active": True,
            },
        ).json()

        # Create vacation day for institution B directly in PocketBase
        vacation_b = pocketbase_admin_client.post(
            "/api/collections/vacation_days/records",
            json={
                "date": "2025-12-25",
                "type": "public_holiday",
                "description": "Christmas",
                "created_by": "admin_b",
                "institution_id": inst_b["id"],
            },
        ).json()

        # Register institution admin in Institution A
        admin_a_response = test_app.post(
            "/api/v1/auth/register-qr",
            json={
                "identity": "admin_a_vac@insta.edu",
                "password": "AdminAVac!",
                "passwordConfirm": "AdminAVac!",
                "name": "Admin A Vacation",
                "magic_word": "MagicA_vac",
                "institution_short_code": "INST_A_VAC",
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
                "identity": "admin_a_vac@insta.edu",
                "password": "AdminAVac!",
                "keep_logged_in": True,
            },
        )
        assert login_response.status_code == 200

        # Get all vacation days (should NOT include institution B's vacation day)
        vacation_response = test_app.get("/api/v1/admin/vacation-days")
        assert vacation_response.status_code == 200
        vacation_days = vacation_response.json()

        # Verify that institution B's vacation day is NOT in the results
        vacation_ids = [v["id"] for v in vacation_days]
        assert vacation_b["id"] not in vacation_ids

    def test_institution_admin_cannot_delete_other_institutions_vacation_days(
        self, test_app, pocketbase_admin_client
    ):
        """
        Test that institution admin A cannot delete vacation days from institution B.

        This is a CRITICAL security test.
        """
        # Create two institutions
        pocketbase_admin_client.post(
            "/api/collections/institutions/records",
            json={
                "name": "Institution A Delete Vac Test",
                "short_code": "INST_A_DEL_VAC",
                "registration_magic_word": "MagicA_del_vac",
                "active": True,
            },
        ).json()

        inst_b = pocketbase_admin_client.post(
            "/api/collections/institutions/records",
            json={
                "name": "Institution B Delete Vac Test",
                "short_code": "INST_B_DEL_VAC",
                "registration_magic_word": "MagicB_del_vac",
                "active": True,
            },
        ).json()

        # Create vacation day for institution B
        vacation_b = pocketbase_admin_client.post(
            "/api/collections/vacation_days/records",
            json={
                "date": "2025-07-04",
                "type": "public_holiday",
                "description": "Independence Day",
                "created_by": "admin_b",
                "institution_id": inst_b["id"],
            },
        ).json()

        # Register institution admin in Institution A
        admin_a_response = test_app.post(
            "/api/v1/auth/register-qr",
            json={
                "identity": "admin_a_del_vac@insta.edu",
                "password": "AdminADelVac!",
                "passwordConfirm": "AdminADelVac!",
                "name": "Admin A Delete Vac",
                "magic_word": "MagicA_del_vac",
                "institution_short_code": "INST_A_DEL_VAC",
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
                "identity": "admin_a_del_vac@insta.edu",
                "password": "AdminADelVac!",
                "keep_logged_in": True,
            },
        )
        assert login_response.status_code == 200

        # Try to delete institution B's vacation day (should fail)
        delete_response = test_app.delete("/api/v1/admin/vacation-days/2025-07-04")
        assert delete_response.status_code in [403, 404]

        # Verify vacation day still exists
        vac_check = pocketbase_admin_client.get(
            f"/api/collections/vacation_days/records/{vacation_b['id']}"
        )
        assert vac_check.status_code == 200

    def test_institution_admin_can_create_vacation_days_for_own_institution(
        self, test_app, pocketbase_admin_client
    ):
        """
        Test that institution admin can create vacation days for their own institution.
        """
        # Create institution
        inst = pocketbase_admin_client.post(
            "/api/collections/institutions/records",
            json={
                "name": "Institution Create Vac Test",
                "short_code": "INST_CREATE_VAC",
                "registration_magic_word": "MagicCreate_vac",
                "active": True,
            },
        ).json()

        # Register institution admin
        admin_response = test_app.post(
            "/api/v1/auth/register-qr",
            json={
                "identity": "admin_create_vac@inst.edu",
                "password": "AdminCreateVac!",
                "passwordConfirm": "AdminCreateVac!",
                "name": "Admin Create Vac",
                "magic_word": "MagicCreate_vac",
                "institution_short_code": "INST_CREATE_VAC",
                "keep_logged_in": True,
            },
        )
        assert admin_response.status_code == 200
        admin_user_id = admin_response.json()["user"]["id"]

        # Elevate to institution_admin
        pocketbase_admin_client.patch(
            f"/api/collections/users/records/{admin_user_id}",
            json={"role": "institution_admin"},
        )

        # Login as admin
        login_response = test_app.post(
            "/api/v1/auth/login",
            json={
                "identity": "admin_create_vac@inst.edu",
                "password": "AdminCreateVac!",
                "keep_logged_in": True,
            },
        )
        assert login_response.status_code == 200

        # Create vacation day (should succeed)
        create_response = test_app.post(
            "/api/v1/admin/vacation-days",
            json={
                "date": "2025-12-24",
                "type": "vacation",
                "description": "Christmas Eve",
            },
        )
        assert create_response.status_code == 200
        created_vacation = create_response.json()

        # Verify vacation day has correct institution_id
        vac_check = pocketbase_admin_client.get(
            f"/api/collections/vacation_days/records/{created_vacation['id']}"
        )
        assert vac_check.status_code == 200
        vac_data = vac_check.json()
        assert vac_data["institution_id"] == inst["id"]


@pytest.mark.integration
class TestPrioritiesHaveInstitutionId:
    """Test that priorities are created with institution_id."""

    def test_user_priority_save_includes_institution_id(
        self, test_app, pocketbase_admin_client
    ):
        """
        Test that when users save priorities, institution_id is included.
        """
        # Create institution
        inst = pocketbase_admin_client.post(
            "/api/collections/institutions/records",
            json={
                "name": "Institution Priority Test",
                "short_code": "INST_PRIO",
                "registration_magic_word": "MagicPrio123",
                "active": True,
            },
        ).json()

        # Register user
        user_response = test_app.post(
            "/api/v1/auth/register-qr",
            json={
                "identity": "user_prio@inst.edu",
                "password": "UserPrio123!",
                "passwordConfirm": "UserPrio123!",
                "name": "User Priority",
                "magic_word": "MagicPrio123",
                "institution_short_code": "INST_PRIO",
                "keep_logged_in": True,
            },
        )
        assert user_response.status_code == 200
        user_id = user_response.json()["user"]["id"]

        # Save priorities
        save_response = test_app.put(
            "/api/v1/priorities/2025-02",
            json=[
                {
                    "weekNumber": 1,
                    "monday": 1,
                    "tuesday": 2,
                    "wednesday": 3,
                    "thursday": 1,
                    "friday": 2,
                }
            ],
        )
        assert save_response.status_code == 200

        # Verify priority has institution_id
        priorities = pocketbase_admin_client.get(
            "/api/collections/priorities/records",
            params={"filter": f'userId="{user_id}" && month="2025-02"'},
        ).json()

        assert len(priorities["items"]) == 1
        assert priorities["items"][0]["institution_id"] == inst["id"]


@pytest.mark.integration
class TestUserVacationDaysIsolation:
    """Test that regular users cannot see vacation days from other institutions."""

    def test_user_cannot_see_other_institutions_vacation_days(
        self, test_app, pocketbase_admin_client
    ):
        """
        Test that regular user in Institution A cannot see vacation days from Institution B.

        This is a CRITICAL security test for user-facing vacation days endpoints.
        """
        # Create two institutions
        inst_a = pocketbase_admin_client.post(
            "/api/collections/institutions/records",
            json={
                "name": "Institution A User Vac Test",
                "short_code": "INST_A_USER_VAC",
                "registration_magic_word": "MagicAUserVac",
                "active": True,
            },
        ).json()

        inst_b = pocketbase_admin_client.post(
            "/api/collections/institutions/records",
            json={
                "name": "Institution B User Vac Test",
                "short_code": "INST_B_USER_VAC",
                "registration_magic_word": "MagicBUserVac",
                "active": True,
            },
        ).json()

        # Create vacation day for institution B
        pocketbase_admin_client.post(
            "/api/collections/vacation_days/records",
            json={
                "date": "2025-12-31",
                "type": "public_holiday",
                "description": "New Year's Eve",
                "created_by": "admin_b",
                "institution_id": inst_b["id"],
            },
        ).json()

        # Create vacation day for institution A
        pocketbase_admin_client.post(
            "/api/collections/vacation_days/records",
            json={
                "date": "2025-12-30",
                "type": "vacation",
                "description": "Institution A Vacation",
                "created_by": "admin_a",
                "institution_id": inst_a["id"],
            },
        ).json()

        # Register regular user in Institution A
        user_a_response = test_app.post(
            "/api/v1/auth/register-qr",
            json={
                "identity": "user_a_vac@insta.edu",
                "password": "UserAVac123!",
                "passwordConfirm": "UserAVac123!",
                "name": "User A Vac",
                "magic_word": "MagicAUserVac",
                "institution_short_code": "INST_A_USER_VAC",
                "keep_logged_in": True,
            },
        )
        assert user_a_response.status_code == 200

        # Get all vacation days as user A (should NOT include institution B's vacation day)
        vacation_response = test_app.get("/api/v1/vacation-days?year=2025")
        assert vacation_response.status_code == 200
        vacation_days = vacation_response.json()

        # Verify user A can only see their institution's vacation days
        vacation_dates = [v["date"] for v in vacation_days]
        assert "2025-12-30" in vacation_dates  # Institution A's vacation day
        assert (
            "2025-12-31" not in vacation_dates
        )  # Institution B's vacation day (MUST NOT be visible)

    def test_user_cannot_see_other_institution_vacation_days_by_date(
        self, test_app, pocketbase_admin_client
    ):
        """
        Test that regular user cannot query specific vacation days from other institutions.
        """
        # Create two institutions
        pocketbase_admin_client.post(
            "/api/collections/institutions/records",
            json={
                "name": "Institution A User Vac Single Test",
                "short_code": "INST_A_USER_VAC_SINGLE",
                "registration_magic_word": "MagicAUserVacSingle",
                "active": True,
            },
        ).json()

        inst_b = pocketbase_admin_client.post(
            "/api/collections/institutions/records",
            json={
                "name": "Institution B User Vac Single Test",
                "short_code": "INST_B_USER_VAC_SINGLE",
                "registration_magic_word": "MagicBUserVacSingle",
                "active": True,
            },
        ).json()

        # Create vacation day for institution B
        pocketbase_admin_client.post(
            "/api/collections/vacation_days/records",
            json={
                "date": "2025-11-20",
                "type": "public_holiday",
                "description": "Institution B Holiday",
                "created_by": "admin_b",
                "institution_id": inst_b["id"],
            },
        ).json()

        # Register regular user in Institution A
        user_a_response = test_app.post(
            "/api/v1/auth/register-qr",
            json={
                "identity": "user_a_vac_single@insta.edu",
                "password": "UserAVacSingle123!",
                "passwordConfirm": "UserAVacSingle123!",
                "name": "User A Vac Single",
                "magic_word": "MagicAUserVacSingle",
                "institution_short_code": "INST_A_USER_VAC_SINGLE",
                "keep_logged_in": True,
            },
        )
        assert user_a_response.status_code == 200

        # Try to get Institution B's vacation day by date (should fail)
        vacation_response = test_app.get("/api/v1/vacation-days/2025-11-20")
        assert (
            vacation_response.status_code == 404
        )  # Not found (filtered by institution)

    def test_user_vacation_days_range_endpoint_filters_by_institution(
        self, test_app, pocketbase_admin_client
    ):
        """
        Test that vacation days range endpoint filters by institution.
        """
        # Create two institutions
        inst_a = pocketbase_admin_client.post(
            "/api/collections/institutions/records",
            json={
                "name": "Institution A Range Test",
                "short_code": "INST_A_RANGE",
                "registration_magic_word": "MagicARange",
                "active": True,
            },
        ).json()

        inst_b = pocketbase_admin_client.post(
            "/api/collections/institutions/records",
            json={
                "name": "Institution B Range Test",
                "short_code": "INST_B_RANGE",
                "registration_magic_word": "MagicBRange",
                "active": True,
            },
        ).json()

        # Create vacation days for both institutions in same date range
        pocketbase_admin_client.post(
            "/api/collections/vacation_days/records",
            json={
                "date": "2025-06-01",
                "type": "vacation",
                "description": "Institution A June Vacation",
                "created_by": "admin_a",
                "institution_id": inst_a["id"],
            },
        )

        pocketbase_admin_client.post(
            "/api/collections/vacation_days/records",
            json={
                "date": "2025-06-15",
                "type": "vacation",
                "description": "Institution B June Vacation",
                "created_by": "admin_b",
                "institution_id": inst_b["id"],
            },
        )

        # Register user in Institution A
        user_a_response = test_app.post(
            "/api/v1/auth/register-qr",
            json={
                "identity": "user_a_range@insta.edu",
                "password": "UserARange123!",
                "passwordConfirm": "UserARange123!",
                "name": "User A Range",
                "magic_word": "MagicARange",
                "institution_short_code": "INST_A_RANGE",
                "keep_logged_in": True,
            },
        )
        assert user_a_response.status_code == 200

        # Get vacation days in range (should only see Institution A's)
        vacation_response = test_app.get(
            "/api/v1/vacation-days/range?start_date=2025-06-01&end_date=2025-06-30"
        )
        assert vacation_response.status_code == 200
        vacation_days = vacation_response.json()

        # Should only see Institution A's vacation day
        assert len(vacation_days) == 1
        assert vacation_days[0]["date"] == "2025-06-01"
        assert vacation_days[0]["description"] == "Institution A June Vacation"


@pytest.mark.integration
class TestAdminPriorityUpdateDeleteIsolation:
    """Test that admin priority update/delete operations respect institution boundaries."""

    def test_institution_admin_cannot_update_other_institution_priorities(
        self, test_app, pocketbase_admin_client
    ):
        """
        Test that institution admin from A cannot update priorities from Institution B.

        This is a CRITICAL security test.
        """
        # Create two institutions
        pocketbase_admin_client.post(
            "/api/collections/institutions/records",
            json={
                "name": "Institution A Priority Update Test",
                "short_code": "INST_A_PRIO_UPDATE",
                "registration_magic_word": "MagicAPrioUpdate",
                "active": True,
            },
        ).json()

        pocketbase_admin_client.post(
            "/api/collections/institutions/records",
            json={
                "name": "Institution B Priority Update Test",
                "short_code": "INST_B_PRIO_UPDATE",
                "registration_magic_word": "MagicBPrioUpdate",
                "active": True,
            },
        ).json()

        # Create user in Institution B and their priority
        user_b_response = test_app.post(
            "/api/v1/auth/register-qr",
            json={
                "identity": "user_b_prio_update@instb.edu",
                "password": "UserBPrioUpdate123!",
                "passwordConfirm": "UserBPrioUpdate123!",
                "name": "User B Priority Update",
                "magic_word": "MagicBPrioUpdate",
                "institution_short_code": "INST_B_PRIO_UPDATE",
                "keep_logged_in": True,
            },
        )
        assert user_b_response.status_code == 200
        user_b_id = user_b_response.json()["user"]["id"]

        # User B creates a priority
        priority_response = test_app.put(
            "/api/v1/priorities/2025-03",
            json=[
                {
                    "weekNumber": 1,
                    "monday": 1,
                    "tuesday": 2,
                    "wednesday": 3,
                    "thursday": 1,
                    "friday": 2,
                }
            ],
        )
        assert priority_response.status_code == 200

        # Get priority ID
        priorities = pocketbase_admin_client.get(
            "/api/collections/priorities/records",
            params={"filter": f'userId="{user_b_id}" && month="2025-03"'},
        ).json()
        priority_id = priorities["items"][0]["id"]

        # Logout user B
        test_app.post("/api/v1/auth/logout")

        # Register institution admin in Institution A
        admin_a_response = test_app.post(
            "/api/v1/auth/register-qr",
            json={
                "identity": "admin_a_prio_update@insta.edu",
                "password": "AdminAPrioUpdate123!",
                "passwordConfirm": "AdminAPrioUpdate123!",
                "name": "Admin A Priority Update",
                "magic_word": "MagicAPrioUpdate",
                "institution_short_code": "INST_A_PRIO_UPDATE",
                "keep_logged_in": True,
            },
        )
        assert admin_a_response.status_code == 200
        admin_a_user_id = admin_a_response.json()["user"]["id"]

        # Elevate to institution_admin
        pocketbase_admin_client.patch(
            f"/api/collections/users/records/{admin_a_user_id}",
            json={"role": "institution_admin"},
        )

        # Re-login as admin A to refresh session
        test_app.post("/api/v1/auth/logout")
        login_response = test_app.post(
            "/api/v1/auth/login",
            json={
                "identity": "admin_a_prio_update@insta.edu",
                "password": "AdminAPrioUpdate123!",
                "keep_logged_in": True,
            },
        )
        assert login_response.status_code == 200

        # Try to update Institution B's priority (should fail)
        update_response = test_app.patch(
            f"/api/v1/admin/priorities/{priority_id}",
            json={"encrypted_fields": "tampered_data"},
        )
        assert update_response.status_code == 403  # Forbidden

    def test_institution_admin_cannot_delete_other_institution_priorities(
        self, test_app, pocketbase_admin_client
    ):
        """
        Test that institution admin from A cannot delete priorities from Institution B.

        This is a CRITICAL security test.
        """
        # Create two institutions
        pocketbase_admin_client.post(
            "/api/collections/institutions/records",
            json={
                "name": "Institution A Priority Delete Test",
                "short_code": "INST_A_PRIO_DELETE",
                "registration_magic_word": "MagicAPrioDelete",
                "active": True,
            },
        ).json()

        pocketbase_admin_client.post(
            "/api/collections/institutions/records",
            json={
                "name": "Institution B Priority Delete Test",
                "short_code": "INST_B_PRIO_DELETE",
                "registration_magic_word": "MagicBPrioDelete",
                "active": True,
            },
        ).json()

        # Create user in Institution B and their priority
        user_b_response = test_app.post(
            "/api/v1/auth/register-qr",
            json={
                "identity": "user_b_prio_delete@instb.edu",
                "password": "UserBPrioDelete123!",
                "passwordConfirm": "UserBPrioDelete123!",
                "name": "User B Priority Delete",
                "magic_word": "MagicBPrioDelete",
                "institution_short_code": "INST_B_PRIO_DELETE",
                "keep_logged_in": True,
            },
        )
        assert user_b_response.status_code == 200
        user_b_id = user_b_response.json()["user"]["id"]

        # User B creates a priority
        priority_response = test_app.put(
            "/api/v1/priorities/2025-04",
            json=[
                {
                    "weekNumber": 1,
                    "monday": 1,
                    "tuesday": 2,
                    "wednesday": 3,
                    "thursday": 1,
                    "friday": 2,
                }
            ],
        )
        assert priority_response.status_code == 200

        # Get priority ID
        priorities = pocketbase_admin_client.get(
            "/api/collections/priorities/records",
            params={"filter": f'userId="{user_b_id}" && month="2025-04"'},
        ).json()
        priority_id = priorities["items"][0]["id"]

        # Logout user B
        test_app.post("/api/v1/auth/logout")

        # Register institution admin in Institution A
        admin_a_response = test_app.post(
            "/api/v1/auth/register-qr",
            json={
                "identity": "admin_a_prio_delete@insta.edu",
                "password": "AdminAPrioDelete123!",
                "passwordConfirm": "AdminAPrioDelete123!",
                "name": "Admin A Priority Delete",
                "magic_word": "MagicAPrioDelete",
                "institution_short_code": "INST_A_PRIO_DELETE",
                "keep_logged_in": True,
            },
        )
        assert admin_a_response.status_code == 200
        admin_a_user_id = admin_a_response.json()["user"]["id"]

        # Elevate to institution_admin
        pocketbase_admin_client.patch(
            f"/api/collections/users/records/{admin_a_user_id}",
            json={"role": "institution_admin"},
        )

        # Re-login as admin A to refresh session
        test_app.post("/api/v1/auth/logout")
        login_response = test_app.post(
            "/api/v1/auth/login",
            json={
                "identity": "admin_a_prio_delete@insta.edu",
                "password": "AdminAPrioDelete123!",
                "keep_logged_in": True,
            },
        )
        assert login_response.status_code == 200

        # Try to delete Institution B's priority (should fail)
        delete_response = test_app.delete(f"/api/v1/admin/priorities/{priority_id}")
        assert delete_response.status_code == 403  # Forbidden

        # Verify priority still exists
        verify_response = pocketbase_admin_client.get(
            f"/api/collections/priorities/records/{priority_id}"
        )
        assert verify_response.status_code == 200


@pytest.mark.integration
class TestInputValidationFilterInjection:
    """Test that input validation prevents filter injection attacks."""

    def test_manual_entry_delete_rejects_malicious_month(
        self, test_app, pocketbase_admin_client
    ):
        """
        Test that manual entry delete endpoint rejects malicious month parameter.
        """
        # Create institution and admin
        pocketbase_admin_client.post(
            "/api/collections/institutions/records",
            json={
                "name": "Institution Filter Injection Test",
                "short_code": "INST_FILTER",
                "registration_magic_word": "MagicFilter123",
                "active": True,
            },
        ).json()

        admin_response = test_app.post(
            "/api/v1/auth/register-qr",
            json={
                "identity": "admin_filter@inst.edu",
                "password": "AdminFilter123!",
                "passwordConfirm": "AdminFilter123!",
                "name": "Admin Filter",
                "magic_word": "MagicFilter123",
                "institution_short_code": "INST_FILTER",
                "keep_logged_in": True,
            },
        )
        assert admin_response.status_code == 200
        admin_user_id = admin_response.json()["user"]["id"]

        # Elevate to institution_admin
        pocketbase_admin_client.patch(
            f"/api/collections/users/records/{admin_user_id}",
            json={"role": "institution_admin"},
        )

        # Re-login as admin
        test_app.post("/api/v1/auth/logout")
        login_response = test_app.post(
            "/api/v1/auth/login",
            json={
                "identity": "admin_filter@inst.edu",
                "password": "AdminFilter123!",
                "keep_logged_in": True,
            },
        )
        assert login_response.status_code == 200

        # Try to delete with malicious month parameter (filter injection attempt)
        malicious_month = '2025-01" || manual = false && userId="'
        delete_response = test_app.delete(
            f"/api/v1/admin/manual-entry/{malicious_month}/test-id"
        )
        # Should reject with 422 (validation error), not execute the query
        assert delete_response.status_code == 422

    def test_manual_entry_delete_rejects_malicious_identifier(
        self, test_app, pocketbase_admin_client
    ):
        """
        Test that manual entry delete endpoint rejects malicious identifier parameter.
        """
        # Create institution and admin
        pocketbase_admin_client.post(
            "/api/collections/institutions/records",
            json={
                "name": "Institution Identifier Injection Test",
                "short_code": "INST_ID_INJ",
                "registration_magic_word": "MagicIdInj123",
                "active": True,
            },
        ).json()

        admin_response = test_app.post(
            "/api/v1/auth/register-qr",
            json={
                "identity": "admin_id_inj@inst.edu",
                "password": "AdminIdInj123!",
                "passwordConfirm": "AdminIdInj123!",
                "name": "Admin Id Injection",
                "magic_word": "MagicIdInj123",
                "institution_short_code": "INST_ID_INJ",
                "keep_logged_in": True,
            },
        )
        assert admin_response.status_code == 200
        admin_user_id = admin_response.json()["user"]["id"]

        # Elevate to institution_admin
        pocketbase_admin_client.patch(
            f"/api/collections/users/records/{admin_user_id}",
            json={"role": "institution_admin"},
        )

        # Re-login as admin
        test_app.post("/api/v1/auth/logout")
        login_response = test_app.post(
            "/api/v1/auth/login",
            json={
                "identity": "admin_id_inj@inst.edu",
                "password": "AdminIdInj123!",
                "keep_logged_in": True,
            },
        )
        assert login_response.status_code == 200

        # Try to delete with malicious identifier (filter injection attempt)
        malicious_identifier = 'test" || identifier!=""'
        delete_response = test_app.delete(
            f"/api/v1/admin/manual-entry/2025-01/{malicious_identifier}"
        )
        # Should reject with 422 (validation error)
        assert delete_response.status_code == 422

    def test_manual_priority_create_rejects_malicious_identifier(
        self, test_app, pocketbase_admin_client
    ):
        """
        Test that manual priority create endpoint rejects malicious identifier.
        """
        # Create institution and admin
        pocketbase_admin_client.post(
            "/api/collections/institutions/records",
            json={
                "name": "Institution Manual Priority Injection Test",
                "short_code": "INST_MANUAL_INJ",
                "registration_magic_word": "MagicManualInj123",
                "active": True,
            },
        ).json()

        admin_response = test_app.post(
            "/api/v1/auth/register-qr",
            json={
                "identity": "admin_manual_inj@inst.edu",
                "password": "AdminManualInj123!",
                "passwordConfirm": "AdminManualInj123!",
                "name": "Admin Manual Injection",
                "magic_word": "MagicManualInj123",
                "institution_short_code": "INST_MANUAL_INJ",
                "keep_logged_in": True,
            },
        )
        assert admin_response.status_code == 200
        admin_user_id = admin_response.json()["user"]["id"]

        # Elevate to institution_admin
        pocketbase_admin_client.patch(
            f"/api/collections/users/records/{admin_user_id}",
            json={"role": "institution_admin"},
        )

        # Re-login as admin
        test_app.post("/api/v1/auth/logout")
        login_response = test_app.post(
            "/api/v1/auth/login",
            json={
                "identity": "admin_manual_inj@inst.edu",
                "password": "AdminManualInj123!",
                "keep_logged_in": True,
            },
        )
        assert login_response.status_code == 200

        # Try to create manual priority with malicious identifier
        malicious_identifier = 'test" || manual = false && userId="'
        create_response = test_app.post(
            "/api/v1/admin/manual-priority",
            json={
                "identifier": malicious_identifier,
                "month": "2025-01",
                "weeks": [
                    {
                        "weekNumber": 1,
                        "monday": 1,
                        "tuesday": 2,
                        "wednesday": 3,
                        "thursday": 1,
                        "friday": 2,
                    }
                ],
            },
        )
        # Should reject with 422 (validation error)
        assert create_response.status_code == 422

    def test_get_user_for_admin_rejects_malicious_username(
        self, test_app, pocketbase_admin_client
    ):
        """
        Test that get user for admin endpoint rejects malicious username.
        """
        # Create institution and admin
        pocketbase_admin_client.post(
            "/api/collections/institutions/records",
            json={
                "name": "Institution Username Injection Test",
                "short_code": "INST_USER_INJ",
                "registration_magic_word": "MagicUserInj123",
                "active": True,
            },
        ).json()

        admin_response = test_app.post(
            "/api/v1/auth/register-qr",
            json={
                "identity": "admin_user_inj@inst.edu",
                "password": "AdminUserInj123!",
                "passwordConfirm": "AdminUserInj123!",
                "name": "Admin User Injection",
                "magic_word": "MagicUserInj123",
                "institution_short_code": "INST_USER_INJ",
                "keep_logged_in": True,
            },
        )
        assert admin_response.status_code == 200
        admin_user_id = admin_response.json()["user"]["id"]

        # Elevate to institution_admin
        pocketbase_admin_client.patch(
            f"/api/collections/users/records/{admin_user_id}",
            json={"role": "institution_admin"},
        )

        # Re-login as admin
        test_app.post("/api/v1/auth/logout")
        login_response = test_app.post(
            "/api/v1/auth/login",
            json={
                "identity": "admin_user_inj@inst.edu",
                "password": "AdminUserInj123!",
                "keep_logged_in": True,
            },
        )
        assert login_response.status_code == 200

        # Try to get user with malicious username (filter injection attempt)
        malicious_username = "test' || role='super_admin"
        user_response = test_app.get(f"/api/v1/admin/users/info/{malicious_username}")
        # Should reject with 422 (validation error)
        assert user_response.status_code == 422

    def test_get_manual_entries_rejects_invalid_month(
        self, test_app, pocketbase_admin_client
    ):
        """
        Test that get manual entries endpoint validates month parameter.
        """
        # Create institution and admin
        pocketbase_admin_client.post(
            "/api/collections/institutions/records",
            json={
                "name": "Institution Month Validation Test",
                "short_code": "INST_MONTH_VAL",
                "registration_magic_word": "MagicMonthVal123",
                "active": True,
            },
        ).json()

        admin_response = test_app.post(
            "/api/v1/auth/register-qr",
            json={
                "identity": "admin_month_val@inst.edu",
                "password": "AdminMonthVal123!",
                "passwordConfirm": "AdminMonthVal123!",
                "name": "Admin Month Validation",
                "magic_word": "MagicMonthVal123",
                "institution_short_code": "INST_MONTH_VAL",
                "keep_logged_in": True,
            },
        )
        assert admin_response.status_code == 200
        admin_user_id = admin_response.json()["user"]["id"]

        # Elevate to institution_admin
        pocketbase_admin_client.patch(
            f"/api/collections/users/records/{admin_user_id}",
            json={"role": "institution_admin"},
        )

        # Re-login as admin
        test_app.post("/api/v1/auth/logout")
        login_response = test_app.post(
            "/api/v1/auth/login",
            json={
                "identity": "admin_month_val@inst.edu",
                "password": "AdminMonthVal123!",
                "keep_logged_in": True,
            },
        )
        assert login_response.status_code == 200

        # Try to get manual entries with malicious month
        malicious_month = '2025-01" || manual != true'
        entries_response = test_app.get(
            f"/api/v1/admin/manual-entries/{malicious_month}"
        )
        # Should reject with 422 (validation error)
        assert entries_response.status_code == 422


@pytest.mark.integration
class TestSecurityAudit4Fixes:
    """Test fixes for vulnerabilities found in Security Audit #4."""

    def test_priority_get_rejects_malicious_month(
        self, test_app, pocketbase_admin_client
    ):
        """
        Test that GET /api/v1/priorities/{month} rejects malicious month values.

        Security Audit #4 Issue #1: Filter injection in priority GET endpoint.
        """
        # Create institution
        pocketbase_admin_client.post(
            "/api/collections/institutions/records",
            json={
                "name": "Test Institution",
                "short_code": "TEST_PRI_GET",
                "registration_magic_word": "TestMagic123",
                "active": True,
            },
        ).json()

        # Register a user
        register_response = test_app.post(
            "/api/v1/auth/register-qr",
            json={
                "identity": "user_pri_get@test.edu",
                "password": "TestPass123!",
                "passwordConfirm": "TestPass123!",
                "name": "Test User",
                "institution_short_code": "TEST_PRI_GET",
                "magic_word": "TestMagic123",
                "keep_logged_in": True,
            },
        )
        assert register_response.status_code == 200

        # Try to get priorities with malicious month value
        malicious_month = '2025-01" || userId!=""'
        get_response = test_app.get(f"/api/v1/priorities/{malicious_month}")

        # Should reject with 422 (validation error)
        assert get_response.status_code == 422
        assert (
            "Monat" in get_response.json()["detail"]
            or "format" in get_response.json()["detail"].lower()
        )

    def test_priority_delete_rejects_malicious_month(
        self, test_app, pocketbase_admin_client
    ):
        """
        Test that DELETE /api/v1/priorities/{month} rejects malicious month values.

        Security Audit #4 Issue #2: Filter injection in priority DELETE endpoint.
        """
        # Create institution
        pocketbase_admin_client.post(
            "/api/collections/institutions/records",
            json={
                "name": "Test Institution",
                "short_code": "TEST_PRI_DEL",
                "registration_magic_word": "TestMagic456",
                "active": True,
            },
        ).json()

        # Register a user
        register_response = test_app.post(
            "/api/v1/auth/register-qr",
            json={
                "identity": "user_pri_del@test.edu",
                "password": "TestPass456!",
                "passwordConfirm": "TestPass456!",
                "name": "Test User Delete",
                "institution_short_code": "TEST_PRI_DEL",
                "magic_word": "TestMagic456",
                "keep_logged_in": True,
            },
        )
        assert register_response.status_code == 200

        # Try to delete priorities with malicious month value
        malicious_month = '2025-01" || identifier!=null'
        delete_response = test_app.delete(f"/api/v1/priorities/{malicious_month}")

        # Should reject with 422 (validation error)
        assert delete_response.status_code == 422
        assert (
            "Monat" in delete_response.json()["detail"]
            or "format" in delete_response.json()["detail"].lower()
        )

    def test_vacation_day_get_rejects_malicious_date(
        self, test_app, pocketbase_admin_client
    ):
        """
        Test that GET /api/v1/admin/vacation-days/{date} rejects malicious date values.

        Security Audit #4 Issue #3: Filter injection in admin vacation day GET endpoint.
        """
        # Create institution
        institution = pocketbase_admin_client.post(
            "/api/collections/institutions/records",
            json={
                "name": "Test Institution VD",
                "short_code": "TEST_VD_GET",
                "registration_magic_word": "TestVDGet123",
                "active": True,
            },
        ).json()

        # Create institution admin
        pocketbase_admin_client.post(
            "/api/collections/users/records",
            json={
                "username": "admin_vd_get@inst.edu",
                "password": "AdminVD123!",
                "passwordConfirm": "AdminVD123!",
                "role": "institution_admin",
                "institution_id": institution["id"],
                "salt": "test_salt",
                "user_wrapped_dek": "test_dek",
                "admin_wrapped_dek": "test_admin_dek",
                "encrypted_fields": {},
            },
        ).json()

        # Login as admin
        login_response = test_app.post(
            "/api/v1/auth/login",
            json={
                "identity": "admin_vd_get@inst.edu",
                "password": "AdminVD123!",
                "keep_logged_in": True,
            },
        )
        assert login_response.status_code == 200

        # Try to get vacation day with malicious date
        malicious_date = '2025-01-01" || type="public_holiday'
        get_response = test_app.get(f"/api/v1/admin/vacation-days/{malicious_date}")

        # Should reject with 422 (validation error)
        assert get_response.status_code == 422
        assert "format" in get_response.json()["detail"].lower()

    def test_vacation_day_update_rejects_malicious_date(
        self, test_app, pocketbase_admin_client
    ):
        """
        Test that PUT /api/v1/admin/vacation-days/{date} rejects malicious date values.

        Security Audit #4 Issue #4: Filter injection in admin vacation day PUT endpoint.
        """
        # Create institution
        institution = pocketbase_admin_client.post(
            "/api/collections/institutions/records",
            json={
                "name": "Test Institution VD Update",
                "short_code": "TEST_VD_PUT",
                "registration_magic_word": "TestVDPut456",
                "active": True,
            },
        ).json()

        # Create institution admin
        pocketbase_admin_client.post(
            "/api/collections/users/records",
            json={
                "username": "admin_vd_put@inst.edu",
                "password": "AdminVDPut456!",
                "passwordConfirm": "AdminVDPut456!",
                "role": "institution_admin",
                "institution_id": institution["id"],
                "salt": "test_salt",
                "user_wrapped_dek": "test_dek",
                "admin_wrapped_dek": "test_admin_dek",
                "encrypted_fields": {},
            },
        ).json()

        # Login as admin
        login_response = test_app.post(
            "/api/v1/auth/login",
            json={
                "identity": "admin_vd_put@inst.edu",
                "password": "AdminVDPut456!",
                "keep_logged_in": True,
            },
        )
        assert login_response.status_code == 200

        # Try to update vacation day with malicious date
        malicious_date = '2025-01-01" || institution_id!=""'
        put_response = test_app.put(
            f"/api/v1/admin/vacation-days/{malicious_date}",
            json={"type": "public_holiday", "description": "Test"},
        )

        # Should reject with 422 (validation error)
        assert put_response.status_code == 422
        assert "format" in put_response.json()["detail"].lower()

    def test_vacation_day_delete_rejects_malicious_date(
        self, test_app, pocketbase_admin_client
    ):
        """
        Test that DELETE /api/v1/admin/vacation-days/{date} rejects malicious date values.

        Security Audit #4 Issue #4: Filter injection in admin vacation day DELETE endpoint.
        """
        # Create institution
        institution = pocketbase_admin_client.post(
            "/api/collections/institutions/records",
            json={
                "name": "Test Institution VD Delete",
                "short_code": "TEST_VD_DEL",
                "registration_magic_word": "TestVDDel789",
                "active": True,
            },
        ).json()

        # Create institution admin
        pocketbase_admin_client.post(
            "/api/collections/users/records",
            json={
                "username": "admin_vd_del@inst.edu",
                "password": "AdminVDDel789!",
                "passwordConfirm": "AdminVDDel789!",
                "role": "institution_admin",
                "institution_id": institution["id"],
                "salt": "test_salt",
                "user_wrapped_dek": "test_dek",
                "admin_wrapped_dek": "test_admin_dek",
                "encrypted_fields": {},
            },
        ).json()

        # Login as admin
        login_response = test_app.post(
            "/api/v1/auth/login",
            json={
                "identity": "admin_vd_del@inst.edu",
                "password": "AdminVDDel789!",
                "keep_logged_in": True,
            },
        )
        assert login_response.status_code == 200

        # Try to delete vacation day with malicious date
        malicious_date = '2025-01-01" || type=""'
        delete_response = test_app.delete(
            f"/api/v1/admin/vacation-days/{malicious_date}"
        )

        # Should reject with 422 (validation error)
        assert delete_response.status_code == 422
        assert "format" in delete_response.json()["detail"].lower()

    def test_change_password_invalidates_old_sessions(
        self, test_app, pocketbase_admin_client, redis_client
    ):
        """
        Test that changing password invalidates all old sessions.

        Security Audit #4 Issue #5: Session invalidation bug in change password.
        This is the MOST CRITICAL fix - ensures old sessions are invalidated.
        """
        # Create institution
        pocketbase_admin_client.post(
            "/api/collections/institutions/records",
            json={
                "name": "Test Institution PW",
                "short_code": "TEST_PW_CHANGE",
                "registration_magic_word": "TestPWChange123",
                "active": True,
            },
        ).json()

        # Register a user
        register_response = test_app.post(
            "/api/v1/auth/register-qr",
            json={
                "identity": "user_pw_change@test.edu",
                "password": "OldPassword123!",
                "passwordConfirm": "OldPassword123!",
                "name": "Test User PW",
                "institution_short_code": "TEST_PW_CHANGE",
                "magic_word": "TestPWChange123",
                "keep_logged_in": True,
            },
        )
        assert register_response.status_code == 200

        # Get the auth token from session 1
        session1_cookies = register_response.cookies

        # Verify session 1 works
        verify1_response = test_app.get("/api/v1/auth/verify")
        assert verify1_response.status_code == 200

        # Login again from "another device" (session 2)
        login2_response = test_app.post(
            "/api/v1/auth/login",
            json={
                "identity": "user_pw_change@test.edu",
                "password": "OldPassword123!",
                "keep_logged_in": True,
            },
        )
        assert login2_response.status_code == 200
        session2_cookies = login2_response.cookies

        # Verify both sessions work
        test_app.cookies.clear()
        test_app.cookies.update(session1_cookies)
        verify1_response = test_app.get("/api/v1/auth/verify")
        assert verify1_response.status_code == 200

        test_app.cookies.clear()
        test_app.cookies.update(session2_cookies)
        verify2_response = test_app.get("/api/v1/auth/verify")
        assert verify2_response.status_code == 200

        # Change password using session 2
        change_pw_response = test_app.post(
            "/api/v1/auth/change-password",
            json={
                "current_password": "OldPassword123!",
                "new_password": "NewPassword456!",
            },
        )
        assert change_pw_response.status_code == 200
        session3_cookies = (
            change_pw_response.cookies
        )  # New session after password change

        # Verify that session 1 (old session) is now INVALID
        test_app.cookies.clear()
        test_app.cookies.update(session1_cookies)
        verify_old_session_response = test_app.get("/api/v1/auth/verify")
        # Session 1 should be invalid (401 Unauthorized)
        assert verify_old_session_response.status_code == 401

        # Verify that session 2 (the one that changed password) is also INVALID
        # because it was replaced with session 3
        test_app.cookies.clear()
        test_app.cookies.update(session2_cookies)
        verify_pw_change_session_response = test_app.get("/api/v1/auth/verify")
        assert verify_pw_change_session_response.status_code == 401

        # Verify that the NEW session (session 3) works
        test_app.cookies.clear()
        test_app.cookies.update(session3_cookies)
        verify_new_session_response = test_app.get("/api/v1/auth/verify")
        assert verify_new_session_response.status_code == 200

        # Verify we can use the new password
        test_app.post("/api/v1/auth/logout")
        login_new_pw_response = test_app.post(
            "/api/v1/auth/login",
            json={
                "identity": "user_pw_change@test.edu",
                "password": "NewPassword456!",
                "keep_logged_in": True,
            },
        )
        assert login_new_pw_response.status_code == 200

    def test_account_deletion_rate_limiting(self, test_app, pocketbase_admin_client):
        """
        Test that account deletion endpoint has rate limiting.

        Security Audit #4 Issue #6: No rate limiting on account deletion.
        """
        # Create institution
        pocketbase_admin_client.post(
            "/api/collections/institutions/records",
            json={
                "name": "Test Institution Delete",
                "short_code": "TEST_DEL_RATE",
                "registration_magic_word": "TestDelRate123",
                "active": True,
            },
        ).json()

        # Register a user
        register_response = test_app.post(
            "/api/v1/auth/register-qr",
            json={
                "identity": "user_del_rate@test.edu",
                "password": "TestDelRate123!",
                "passwordConfirm": "TestDelRate123!",
                "name": "Test User Delete Rate",
                "institution_short_code": "TEST_DEL_RATE",
                "magic_word": "TestDelRate123",
                "keep_logged_in": True,
            },
        )
        assert register_response.status_code == 200

        # First deletion attempt
        delete1_response = test_app.delete("/api/v1/account/delete")
        # Should succeed (user deleted)
        assert delete1_response.status_code == 200

        # Register the same user again
        register2_response = test_app.post(
            "/api/v1/auth/register-qr",
            json={
                "identity": "user_del_rate@test.edu",
                "password": "TestDelRate456!",
                "passwordConfirm": "TestDelRate456!",
                "name": "Test User Delete Rate 2",
                "institution_short_code": "TEST_DEL_RATE",
                "magic_word": "TestDelRate123",
                "keep_logged_in": True,
            },
        )
        assert register2_response.status_code == 200

        # Immediate second deletion attempt (should be rate limited)
        delete2_response = test_app.delete("/api/v1/account/delete")
        # Should be rate limited (429 Too Many Requests)
        assert delete2_response.status_code == 429
        assert "viele" in delete2_response.json()["detail"].lower()
