import getpass
import sys

import requests

from kigaprio.services.pocketbase_service import POCKETBASE_URL

superuser_login = input("Enter superuser login: ")
superuser_password = getpass.getpass()
target_user = input("Enter username to elevate: ")

try:
    pb_response = requests.post(
        f"{POCKETBASE_URL}/api/collections/_superusers/auth-with-password",
        json={
            "identity": superuser_login,
            "password": superuser_password,
        },
    )
    response_body = pb_response.json()
    token = response_body["token"]
except Exception:
    sys.exit("Failed to login as superuser")


response = requests.get(
    f"{POCKETBASE_URL}/api/collections/users/records",
    params={"filter": f'username="{target_user}"'},
    headers={"Authorization": f"Bearer {token}"},
)
assert response.status_code == 200, "Failed to find user"
user_data = response.json()["items"][0]
requests.patch(
    f"{POCKETBASE_URL}/api/collections/users/records/{user_data['id']}",
    json={
        "role": "admin",
    },
    headers={"Authorization": f"Bearer {token}"},
)
assert response.status_code == 200, "Failed to update user"
