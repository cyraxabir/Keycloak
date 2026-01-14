import requests
import json
import sys
from time import sleep

KEYCLOAK_URL = "https://------.com"
REALM = "<export-users-realm-name>"
USERNAME = "<master-admin"
PASSWORD = "*******"
CLIENT_ID = "admin-cli"

PAGE_SIZE = 100
OUTPUT_FILE = "users.json"
VERIFY_SSL = False   # set True if valid CA

def get_admin_token():
    url = f"{KEYCLOAK_URL}/realms/master/protocol/openid-connect/token"
    data = {
        "client_id": CLIENT_ID,
        "grant_type": "password",
        "username": USERNAME,
        "password": PASSWORD,
    }

    r = requests.post(url, data=data, verify=VERIFY_SSL)
    r.raise_for_status()
    return r.json()["access_token"]

def export_users(token):
    headers = {
        "Authorization": f"Bearer {token}"
    }

    users = []
    first = 0

    while True:
        url = f"{KEYCLOAK_URL}/admin/realms/{REALM}/users"
        params = {
            "first": first,
            "max": PAGE_SIZE
        }

        r = requests.get(url, headers=headers, params=params, verify=VERIFY_SSL)
        r.raise_for_status()

        batch = r.json()
        if not batch:
            break

        users.extend(batch)
        first += PAGE_SIZE

        print(f"Exported {len(users)} users...")
        sleep(0.1)  # avoid rate limiting

    return users

def main():
    try:
        print("Getting admin token...")
        token = get_admin_token()

        print("Exporting users...")
        users = export_users(token)

        with open(OUTPUT_FILE, "w") as f:
            json.dump(users, f, indent=2)

        print(f"\n✅ Export complete")
        print(f"Total users: {len(users)}")
        print(f"Saved to: {OUTPUT_FILE}")

    except requests.exceptions.HTTPError as e:
        print("❌ HTTP error:", e.response.text)
        sys.exit(1)
    except Exception as e:
        print("❌ Error:", str(e))
        sys.exit(1)

if __name__ == "__main__":
    main()