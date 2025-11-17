# Multi-Institution Support Migration Guide

This document provides instructions for migrating from the single-institution setup to the new multi-institution support.

## Overview

The multi-institution feature allows multiple institutions to use the same PrioTag instance with complete data isolation. Each institution has:
- Its own registration magic word
- Its own admin users (institution_admin role)
- Its own RSA key pair for admin decryption (optional)
- Isolated user data, priorities, and vacation days

## Architecture Changes

### Database Schema
- **New Collection**: `institutions` - Stores institution metadata
- **Updated Collections**: Added `institution_id` foreign key to:
  - `users` - Associates users with institutions
  - `priorities` - Isolates priority data by institution
  - `vacation_days` - Institution-specific vacation days
- **New User Roles**:
  - `super_admin` - Can manage all institutions and users
  - `institution_admin` - Can manage only their institution
  - `user` - Regular user (unchanged)

### API Changes
- **New Endpoints**:
  - `GET /api/v1/institutions` - List active institutions (public)
  - `GET /api/v1/institutions/{short_code}` - Get institution by code (public)
  - `POST /api/v1/admin/super/institutions` - Create institution (super admin only)
  - `GET /api/v1/admin/institution/info` - Get own institution details

- **Updated Endpoints**:
  - `POST /api/v1/auth/verify-magic-word` - Now requires `institution_short_code`
  - `POST /api/v1/auth/register` - Associates user with institution
  - `POST /api/v1/auth/register-qr` - Now requires `institution_short_code`

## Migration Steps

### 1. Backup Your Data

**IMPORTANT**: Before proceeding, backup your PocketBase database:

```bash
# Stop the application
docker-compose down

# Backup the PocketBase data directory
cp -r pocketbase/pb_data pocketbase/pb_data.backup.$(date +%Y%m%d)

# Restart the application
docker-compose up -d
```

### 2. Apply Database Migrations

The PocketBase migrations will be applied automatically on startup. The following migrations will run:

1. `1763420233_created_institutions.js` - Creates institutions collection
2. `1763420234_updated_users.js` - Adds institution_id to users
3. `1763420235_updated_priorities.js` - Adds institution_id to priorities
4. `1763420236_updated_vacation_days.js` - Adds institution_id to vacation_days
5. `1763420237_updated_system_settings.js` - Adds multi-institution settings
6. `1763420238_updated_users_role.js` - Updates user role enum

After migrations run, all `institution_id` fields will be `NULL` initially.

### 3. Run the Migration Script

The migration script will:
- Create a default institution
- Associate all existing users with the default institution
- Associate all existing priorities with the default institution
- Associate all existing vacation days with the default institution
- Convert legacy "admin" users to "institution_admin" role

```bash
# Navigate to the backend directory
cd backend

# Run the migration script
python -m priotag.scripts.migrate_to_multi_institution

# Follow the interactive prompts:
# - Enter default institution name (e.g., "Your Institution Name")
# - Enter short code (e.g., "DEFAULT" or "YOUR_ORG")
```

**Example Output**:
```
================================================================================
MULTI-INSTITUTION MIGRATION SCRIPT
================================================================================

This script will migrate your existing single-institution data
to the new multi-institution structure.

Enter default institution name: My University
Enter institution short code (e.g., 'DEFAULT', 'MIT'): MYUNI

[1/6] Fetching current system settings...
Using magic word: YourExistingMagicWord

[2/6] Creating default institution 'My University'...
✓ Institution created with ID: abc123def456

[3/6] Updating all users...
Found 25 users to update
  - john.doe: assigning to institution + converting to institution_admin
  - jane.smith: assigning to institution
  ...
✓ Updated 25 users

[4/6] Updating all priorities...
✓ Updated 150 priorities

[5/6] Updating all vacation days...
Found 10 vacation days to update
✓ Updated 10 vacation days

[6/6] Updating system settings...
✓ System settings updated

================================================================================
MIGRATION COMPLETE
================================================================================
Institution: My University (MYUNI)
Institution ID: abc123def456
Users migrated: 25
Priorities migrated: 150
Vacation days migrated: 10

Next steps:
1. Generate new QR codes with institution parameter
   python generate_qr_codes.py --institution MYUNI
2. Create additional institutions if needed
   python create_institution.py
3. Elevate users to super_admin if needed
   python elevate_user_to_super_admin.py
```

### 4. Generate New QR Codes

After migration, generate new QR codes that include the institution parameter:

```bash
cd scripts

# Generate QR code for the default institution
python generate_qr_code.py "YourMagicWord" "MYUNI" \
  --url "https://your-domain.com" \
  --output myuni_registration_qr.png
```

This will create:
- `myuni_registration_qr.png` - QR code image
- `myuni_registration_qr.json` - Metadata file

The QR code will encode:
```
https://your-domain.com/register?magic=YourMagicWord&institution=MYUNI
```

### 5. (Optional) Create Additional Institutions

To add more institutions to your system:

```bash
cd backend

# Run the institution creation script
python -m priotag.scripts.create_institution

# Follow the interactive prompts:
# - Enter institution name
# - Enter short code (uppercase, alphanumeric + underscore)
# - Choose to generate or enter custom magic word
# - Optionally provide institution-specific RSA public key
```

**Example**:
```
================================================================================
CREATE NEW INSTITUTION
================================================================================

Enter institution name: Stanford University
Enter institution short code (uppercase, e.g., 'MIT', 'STANFORD'): STANFORD

Magic word options:
1. Generate random magic word
2. Enter custom magic word
Choose option (1 or 2): 1
Generated magic word: Phoenix4782

Admin public key (optional, press Enter to skip):
[paste RSA public key or press Enter]

================================================================================
CONFIRM INSTITUTION DETAILS
================================================================================
Name: Stanford University
Short Code: STANFORD
Magic Word: Phoenix4782
Admin Public Key: (using global)

Create this institution? (yes/no): yes

Creating institution...

================================================================================
✓ INSTITUTION CREATED SUCCESSFULLY
================================================================================
ID: xyz789abc123
Name: Stanford University
Short Code: STANFORD
Magic Word: Phoenix4782
Active: True

Next steps:
1. Generate QR codes for registration:
   python generate_qr_codes.py --institution STANFORD --magic-word "Phoenix4782"
2. Elevate users to institution_admin for this institution:
   python elevate_user_to_admin.py --institution-id xyz789abc123
```

### 6. Elevate Users to Admin Roles

#### Elevate to Institution Admin

To make a user an admin for a specific institution:

```bash
cd backend

python -m priotag.scripts.elevate_user_to_admin

# Follow prompts:
# - Enter PocketBase superuser credentials
# - Enter username to elevate
# - The script will show the user's current institution
# - Confirm elevation to institution_admin
```

#### Elevate to Super Admin

To make a user a super admin (can manage all institutions):

```bash
cd backend

python -m priotag.scripts.elevate_user_to_admin --super

# Follow prompts:
# - Enter PocketBase superuser credentials
# - Enter username to elevate
# - Confirm elevation to super_admin
```

**Note**: Super admins have no institution_id (set to NULL) and can access all institutions.

## Testing the Migration

### 1. Test Institution List

Visit the frontend and check that institutions load correctly:

```bash
curl http://localhost:8000/api/v1/institutions
```

Expected response:
```json
[
  {
    "id": "abc123def456",
    "name": "My University",
    "short_code": "MYUNI",
    "active": true,
    "created": "2024-01-01T00:00:00Z",
    "updated": "2024-01-01T00:00:00Z"
  }
]
```

### 2. Test Registration Flow

1. Navigate to `/register` in your browser
2. You should see the institution selector
3. Select your institution
4. Enter the magic word
5. Complete registration

### 3. Test Data Isolation

1. Create users in different institutions
2. Log in as each user
3. Verify they only see their institution's data

### 4. Test Admin Roles

**Institution Admin**:
- Can view/edit users in their institution only
- Can update their institution's magic word
- Cannot see other institutions' data

**Super Admin**:
- Can view all institutions
- Can create new institutions
- Can view/edit users across all institutions
- Can elevate users to any admin role

## Rollback Procedure

If you need to rollback the migration:

1. Stop the application:
```bash
docker-compose down
```

2. Restore the backup:
```bash
rm -rf pocketbase/pb_data
cp -r pocketbase/pb_data.backup.YYYYMMDD pocketbase/pb_data
```

3. Checkout the previous version:
```bash
git checkout <previous-commit-hash>
```

4. Restart the application:
```bash
docker-compose up -d
```

## Breaking Changes

### For End Users

- **Registration**: Must now select an institution before entering magic word
- **QR Codes**: Old QR codes without institution parameter will not work

### For Admins

- **Admin Role**: Legacy "admin" role converted to "institution_admin"
- **Magic Word**: Now institution-specific (each institution has its own)
- **Admin UI**: Shows only institution's data unless super_admin

### For API Clients

- **`POST /auth/verify-magic-word`**: Now requires `institution_short_code` field
- **`POST /auth/register-qr`**: Now requires `institution_short_code` field
- **All admin endpoints**: Automatically filter by institution unless super_admin

## Troubleshooting

### Migration Script Fails

**Issue**: Migration script fails with "Institution not found"

**Solution**: Check that PocketBase migrations have run successfully:
```bash
docker-compose logs pocketbase | grep migration
```

### Users Can't See Institutions

**Issue**: Frontend shows "No institutions available"

**Solution**:
1. Check that institutions were created: `curl http://localhost:8000/api/v1/institutions`
2. Verify institution is marked as `active: true`
3. Check browser console for errors

### Registration Fails

**Issue**: "Institution nicht gefunden" error

**Solution**:
1. Verify institution short_code matches exactly (case-sensitive)
2. Check institution is active
3. Verify magic word is correct for that institution

### Admin Can't See Users

**Issue**: Institution admin sees empty user list

**Solution**:
1. Verify admin has correct role: `institution_admin` or `super_admin`
2. Check that users have matching `institution_id`
3. Verify admin's `institution_id` matches users' `institution_id`

## Support

For issues or questions:
1. Check the commit messages for implementation details
2. Review the API documentation in the code
3. Consult the PocketBase logs: `docker-compose logs pocketbase`
4. Review FastAPI logs: `docker-compose logs backend`

## Summary

After completing these steps, you will have:
- ✅ A default institution with all existing data migrated
- ✅ Institution-specific magic words
- ✅ Updated admin roles (institution_admin, super_admin)
- ✅ Complete data isolation between institutions
- ✅ New QR codes with institution parameters
- ✅ Ability to create and manage multiple institutions

Your system is now ready for multi-institution use!
