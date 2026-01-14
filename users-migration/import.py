import requests
import json
import sys
import urllib3
import time

# ==== CONFIG ====
KEYCLOAK_URL = "https://-----.com"  # target Keycloak
REALM = "<realm-name>"
USERNAME = "<admin>"        # master realm admin
PASSWORD = "*****"   # master realm admin password
CLIENT_ID = "admin-cli"
INPUT_FILE = "users.json"
VERIFY_SSL = False         # True if your CA is valid
TEMP_PASSWORD = "<Temp_passwd>" # Only used if user has no credentials
DELAY = 0.2               # seconds between requests
MAX_RETRIES = 3           # retries for token refresh or connection errors

# Suppress SSL warnings for self-signed certs
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


# ==== GET ADMIN TOKEN ====
def get_admin_token():
    url = f"{KEYCLOAK_URL}/realms/master/protocol/openid-connect/token"
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    data = {
        "client_id": CLIENT_ID,
        "grant_type": "password",
        "username": USERNAME,
        "password": PASSWORD
    }
    r = requests.post(url, headers=headers, data=data, verify=VERIFY_SSL, timeout=30)
    if r.status_code != 200:
        print("❌ Failed to get token:", r.text)
        sys.exit(1)
    return r.json()["access_token"]


# ==== CLEAN USER PAYLOAD ====
def clean_user(user):
    """Remove read-only fields from exported user JSON"""
    for key in ["id", "createdTimestamp", "serviceAccountClientId", "federationLink", "notBefore", "access"]:
        user.pop(key, None)
    return user


# ==== SAFE REQUEST WITH RETRY ====
def safe_request(func, url, **kwargs):
    """Retry request on 401 or connection error"""
    for attempt in range(MAX_RETRIES):
        try:
            r = func(url, **kwargs)
            if r.status_code == 401:
                print("⚠ Token expired or unauthorized, refreshing token...")
                kwargs["headers"]["Authorization"] = f"Bearer {get_admin_token()}"
                time.sleep(1)
                continue
            return r
        except requests.exceptions.ConnectionError:
            print(f"⚠ Connection failed, retrying ({attempt+1}/{MAX_RETRIES})...")
            time.sleep(2)
    raise ConnectionError(f"Failed to connect to {url} after {MAX_RETRIES} retries")


# ==== CREATE USER ====
def create_user(user, token):
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    url = f"{KEYCLOAK_URL}/admin/realms/{REALM}/users"

    r = safe_request(requests.post, url, headers=headers, json=user, verify=VERIFY_SSL)
    if r.status_code == 201:
        print(f"✅ User created: {user.get('username')}")
        return True, token
    elif r.status_code == 409:
        print(f"⚠ User already exists: {user.get('username')}")
        return False, token
    else:
        print(f"❌ Failed to create {user.get('username')}: {r.status_code} {r.text}")
        return False, token


# ==== SET TEMP PASSWORD ====
def set_temp_password(username, token):
    headers = {"Authorization": f"Bearer {token}"}

    # Get user ID
    url = f"{KEYCLOAK_URL}/admin/realms/{REALM}/users?username={username}"
    r = safe_request(requests.get, url, headers=headers, verify=VERIFY_SSL)
    if r.status_code != 200 or not r.json():
        print(f"❌ Cannot find user {username} to set password")
        return token
    user_id = r.json()[0]["id"]

    # Set password
    url = f"{KEYCLOAK_URL}/admin/realms/{REALM}/users/{user_id}/reset-password"
    payload = {"type": "password", "temporary": False, "value": TEMP_PASSWORD}
    r2 = safe_request(requests.put, url, headers={**headers, "Content-Type": "application/json"}, json=payload, verify=VERIFY_SSL)
    if r2.status_code == 204:
        print(f"🔑 Password set for {username}")
    else:
        print(f"❌ Failed to set password for {username}: {r2.status_code} {r2.text}")
    return token


# ==== MAIN LOOP ====
def main():
    token = get_admin_token()
    print("✅ Admin token obtained")

    # Load users
    with open(INPUT_FILE, "r") as f:
        users = json.load(f)

    print(f"🔄 Importing {len(users)} users into realm '{REALM}'...\n")

    for user in users:
        user = clean_user(user)
        created, token = create_user(user, token)
        if created:
            # Set password only if user has no credentials
            if "credentials" not in user or not user["credentials"]:
                token = set_temp_password(user.get("username"), token)
        time.sleep(DELAY)

    print("\n🎉 User import completed.")


if __name_