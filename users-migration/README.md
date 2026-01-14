You can export users through script/ or curl request.
##
import users to destination need script (keycloak doesnt export users passwd) and need to set default password or blank.
##
The export script contains:
### ✅ Features
1. **Skips users that already exist** (`409 Conflict`)
2. **Sets temporary password** only if `credentials` field is missing in JSON
3. **Retries** on:
    - 401 Unauthorized (refreshes token automatically)
    - ConnectionError (like `Errno 111`)
4. Small **delay** between requests to avoid overloading Keycloak
5. Logs **every success, warning, and failure**
6. Add **small delay between requests**: `DELAY = 0.2` or `0.5` seconds.