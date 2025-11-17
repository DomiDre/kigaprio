#!/usr/bin/env python3
"""
Migration script to convert single-institution database to multi-institution.

This script:
1. Creates a default institution
2. Associates all existing users with the default institution
3. Associates all existing priorities with the default institution
4. Associates all existing vacation days with the default institution
5. Converts existing "admin" users to "institution_admin"
"""

import asyncio
import os
import sys
from pathlib import Path

import httpx

# Add parent directory to path to import priotag modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from priotag.services.pocketbase_service import POCKETBASE_URL
from priotag.services.service_account import authenticate_service_account


async def migrate_to_multi_institution():
    """Main migration function."""
    print("=" * 80)
    print("MULTI-INSTITUTION MIGRATION SCRIPT")
    print("=" * 80)
    print()

    # Get configuration from user
    print("This script will migrate your existing single-institution data")
    print("to the new multi-institution structure.")
    print()

    institution_name = input("Enter default institution name: ").strip()
    if not institution_name:
        print("Error: Institution name cannot be empty")
        return

    institution_short_code = input(
        "Enter institution short code (e.g., 'DEFAULT', 'MIT'): "
    ).strip().upper()
    if not institution_short_code:
        print("Error: Short code cannot be empty")
        return

    # Get current magic word from system_settings
    async with httpx.AsyncClient() as client:
        service_token = await authenticate_service_account(client)
        if not service_token:
            print("Error: Failed to authenticate service account")
            return

        headers = {"Authorization": f"Bearer {service_token}"}

        # Get system settings to retrieve current magic word
        print("\n[1/6] Fetching current system settings...")
        response = await client.get(
            f"{POCKETBASE_URL}/api/collections/system_settings/records",
            headers=headers,
        )

        if response.status_code != 200:
            print(f"Error fetching system settings: {response.text}")
            return

        settings_data = response.json()
        items = settings_data.get("items", [])
        if not items:
            print("Error: No system settings found")
            return

        current_magic_word = items[0].get("registration_magic_word", "")
        if not current_magic_word:
            print("Warning: No current magic word found in system settings")
            current_magic_word = input("Enter magic word for default institution: ").strip()

        print(f"Using magic word: {current_magic_word}")

        # Create default institution
        print(f"\n[2/6] Creating default institution '{institution_name}'...")
        institution_data = {
            "name": institution_name,
            "short_code": institution_short_code,
            "registration_magic_word": current_magic_word,
            "active": True,
            "settings": {},
        }

        response = await client.post(
            f"{POCKETBASE_URL}/api/collections/institutions/records",
            json=institution_data,
            headers=headers,
        )

        if response.status_code != 200:
            print(f"Error creating institution: {response.text}")
            return

        institution = response.json()
        institution_id = institution["id"]
        print(f"✓ Institution created with ID: {institution_id}")

        # Update all users
        print("\n[3/6] Updating all users...")
        response = await client.get(
            f"{POCKETBASE_URL}/api/collections/users/records",
            params={"perPage": 500},
            headers=headers,
        )

        if response.status_code != 200:
            print(f"Error fetching users: {response.text}")
            return

        users_data = response.json()
        users = users_data.get("items", [])
        print(f"Found {len(users)} users to update")

        for user in users:
            user_id = user["id"]
            username = user.get("username", "unknown")

            # Update user with institution_id and migrate role if needed
            update_data = {"institution_id": institution_id}

            # Convert legacy "admin" role to "institution_admin"
            if user.get("role") == "admin":
                update_data["role"] = "institution_admin"
                print(f"  - {username}: assigning to institution + converting to institution_admin")
            else:
                print(f"  - {username}: assigning to institution")

            response = await client.patch(
                f"{POCKETBASE_URL}/api/collections/users/records/{user_id}",
                json=update_data,
                headers=headers,
            )

            if response.status_code != 200:
                print(f"    Error updating user {username}: {response.text}")

        print(f"✓ Updated {len(users)} users")

        # Update all priorities
        print("\n[4/6] Updating all priorities...")
        page = 1
        total_priorities = 0

        while True:
            response = await client.get(
                f"{POCKETBASE_URL}/api/collections/priorities/records",
                params={"page": page, "perPage": 500},
                headers=headers,
            )

            if response.status_code != 200:
                print(f"Error fetching priorities: {response.text}")
                break

            priorities_data = response.json()
            priorities = priorities_data.get("items", [])

            if not priorities:
                break

            for priority in priorities:
                priority_id = priority["id"]

                response = await client.patch(
                    f"{POCKETBASE_URL}/api/collections/priorities/records/{priority_id}",
                    json={"institution_id": institution_id},
                    headers=headers,
                )

                if response.status_code != 200:
                    print(f"Error updating priority {priority_id}: {response.text}")

            total_priorities += len(priorities)
            page += 1

        print(f"✓ Updated {total_priorities} priorities")

        # Update all vacation days
        print("\n[5/6] Updating all vacation days...")
        response = await client.get(
            f"{POCKETBASE_URL}/api/collections/vacation_days/records",
            params={"perPage": 500},
            headers=headers,
        )

        if response.status_code == 200:
            vacation_days_data = response.json()
            vacation_days = vacation_days_data.get("items", [])
            print(f"Found {len(vacation_days)} vacation days to update")

            for vacation_day in vacation_days:
                vacation_day_id = vacation_day["id"]

                response = await client.patch(
                    f"{POCKETBASE_URL}/api/collections/vacation_days/records/{vacation_day_id}",
                    json={"institution_id": institution_id},
                    headers=headers,
                )

                if response.status_code != 200:
                    print(f"Error updating vacation day {vacation_day_id}: {response.text}")

            print(f"✓ Updated {len(vacation_days)} vacation days")
        else:
            print("No vacation days collection found or error fetching (skipping)")

        # Update system settings with default institution
        print("\n[6/6] Updating system settings...")
        settings_id = items[0]["id"]
        response = await client.patch(
            f"{POCKETBASE_URL}/api/collections/system_settings/records/{settings_id}",
            json={"default_institution_id": institution_id},
            headers=headers,
        )

        if response.status_code == 200:
            print("✓ System settings updated")
        else:
            print(f"Warning: Could not update system settings: {response.text}")

        # Summary
        print("\n" + "=" * 80)
        print("MIGRATION COMPLETE")
        print("=" * 80)
        print(f"Institution: {institution_name} ({institution_short_code})")
        print(f"Institution ID: {institution_id}")
        print(f"Users migrated: {len(users)}")
        print(f"Priorities migrated: {total_priorities}")
        print(f"Vacation days migrated: {len(vacation_days) if vacation_days else 0}")
        print("\nNext steps:")
        print("1. Generate new QR codes with institution parameter")
        print(f"   python generate_qr_codes.py --institution {institution_short_code}")
        print("2. Create additional institutions if needed")
        print("   python create_institution.py")
        print("3. Elevate users to super_admin if needed")
        print("   python elevate_user_to_super_admin.py")
        print()


if __name__ == "__main__":
    asyncio.run(migrate_to_multi_institution())
