"""
Iteration 13 - Verification of code review fixes:
- Admin auth via httpOnly cookie 'admin_token' (no localStorage)
- POST /api/admin/logout clears cookie
- get_current_admin accepts cookie OR Bearer header
- Fail-closed: dev password admin123 removed
"""
import os
import subprocess
from pathlib import Path

import pytest
import requests
from dotenv import dotenv_values

frontend_env = dotenv_values("/app/frontend/.env")
base_url = os.environ.get("REACT_APP_BACKEND_URL") or frontend_env.get("REACT_APP_BACKEND_URL")
if not base_url:
    raise RuntimeError("REACT_APP_BACKEND_URL missing")
BASE_URL = base_url.rstrip("/")

TEST_USER_EMAIL = os.environ.get("TEST_USER_EMAIL", "qa_review_jun26@test.com")
TEST_USER_PASSWORD = os.environ.get("TEST_USER_PASSWORD", "QaReview2026!")


@pytest.fixture(scope="session")
def admin_token():
    """Generate a valid admin token locally (real admin password unknown)."""
    cached = Path("/app/tests/.admin_token")
    if cached.exists():
        tok = cached.read_text().strip()
        if tok:
            return tok
    out = subprocess.run(
        ["python3", "-c",
         "from dotenv import load_dotenv; load_dotenv('.env'); "
         "from auth import create_admin_token; print(create_admin_token())"],
        cwd="/app/backend", capture_output=True, text=True
    )
    token = out.stdout.strip()
    if not token:
        pytest.fail(f"Could not generate admin token: {out.stderr[:300]}")
    return token


@pytest.fixture
def client():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


# ============== Admin cookie / header auth ==============
class TestAdminCookieAuth:
    def test_admin_config_with_cookie_200(self, client, admin_token):
        r = client.get(f"{BASE_URL}/api/admin/config",
                       cookies={"admin_token": admin_token})
        assert r.status_code == 200, r.text[:300]
        data = r.json()
        assert isinstance(data, dict)
        assert "_id" not in data

    def test_admin_config_with_bearer_200(self, client, admin_token):
        r = client.get(f"{BASE_URL}/api/admin/config",
                       headers={"Authorization": f"Bearer {admin_token}"})
        assert r.status_code == 200, r.text[:300]
        assert "_id" not in r.json()

    def test_admin_config_no_credentials_401(self, client):
        r = client.get(f"{BASE_URL}/api/admin/config")
        assert r.status_code == 401
        assert "detail" in r.json()

    def test_admin_config_invalid_cookie_401(self, client):
        r = client.get(f"{BASE_URL}/api/admin/config",
                       cookies={"admin_token": "not.a.valid.token"})
        assert r.status_code == 401

    def test_user_token_rejected_on_admin_endpoint(self, client):
        """A regular user JWT must not grant admin access (type != admin)."""
        login = client.post(f"{BASE_URL}/api/auth/login",
                            json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD})
        assert login.status_code == 200, login.text[:300]
        token = login.json().get("access_token")
        assert token
        r = client.get(f"{BASE_URL}/api/admin/config",
                       headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 401

    def test_admin_logout_clears_cookie(self, client, admin_token):
        r = client.post(f"{BASE_URL}/api/admin/logout",
                        cookies={"admin_token": admin_token})
        assert r.status_code == 200, r.text[:300]
        assert "message" in r.json()
        set_cookie = r.headers.get("set-cookie", "")
        assert "admin_token=" in set_cookie, set_cookie
        assert ("Max-Age=0" in set_cookie) or ('admin_token=""' in set_cookie) or \
               ("admin_token=;" in set_cookie), set_cookie
        assert "HttpOnly" in set_cookie, set_cookie

    def test_admin_users_and_count_with_cookie(self, client, admin_token):
        c = {"admin_token": admin_token}
        r = client.get(f"{BASE_URL}/api/admin/users?limit=5", cookies=c)
        assert r.status_code == 200, r.text[:300]
        users = r.json()
        assert isinstance(users, list)
        for u in users:
            assert "_id" not in u
            assert "password_hash" not in u
        rc = client.get(f"{BASE_URL}/api/admin/users/count", cookies=c)
        assert rc.status_code == 200
        assert isinstance(rc.json().get("count"), int)

    def test_admin_route_sheets_with_cookie_and_pagination(self, client, admin_token):
        c = {"admin_token": admin_token}
        r = client.get(f"{BASE_URL}/api/admin/route-sheets?limit=5", cookies=c)
        assert r.status_code == 200, r.text[:300]
        sheets = r.json()
        assert isinstance(sheets, list)
        assert len(sheets) <= 5
        for s in sheets:
            assert "_id" not in s
        # Cursor pagination headers still exposed
        assert "X-Total-Count" in r.headers or "x-total-count" in r.headers
        cursor = r.headers.get("X-Next-Cursor")
        if cursor and sheets:
            r2 = client.get(f"{BASE_URL}/api/admin/route-sheets?limit=5&cursor={cursor}",
                            cookies=c)
            assert r2.status_code == 200, r2.text[:300]
            ids1 = {s["id"] for s in sheets}
            ids2 = {s["id"] for s in r2.json()}
            assert not (ids1 & ids2), "Duplicate sheets across pages"

    def test_admin_pdf_download_with_cookie(self, client, admin_token):
        c = {"admin_token": admin_token}
        r = client.get(f"{BASE_URL}/api/admin/route-sheets?limit=1", cookies=c)
        assert r.status_code == 200
        sheets = r.json()
        if not sheets:
            pytest.skip("No route sheets available")
        sid = sheets[0]["id"]
        rp = client.get(f"{BASE_URL}/api/admin/route-sheets/{sid}/pdf", cookies=c)
        assert rp.status_code == 200, rp.text[:200]
        assert rp.headers.get("content-type", "").startswith("application/pdf")
        assert rp.content[:4] == b"%PDF"


# ============== Fail-closed dev password ==============
class TestFailClosedDevPassword:
    def test_default_dev_password_rejected(self, client):
        """Only ONE attempt (rate limit 5/5min)."""
        r = client.post(f"{BASE_URL}/api/admin/login",
                        json={"username": "admin", "password": "admin123"})
        assert r.status_code == 401, f"Expected 401, got {r.status_code}: {r.text[:300]}"
        assert "admin_token" not in r.headers.get("set-cookie", "")
        assert "access_token" not in r.text

    def test_admin_configured_in_health(self, client):
        r = client.get(f"{BASE_URL}/api/health")
        assert r.status_code == 200
        body = r.json()
        assert body.get("admin_configured") is True, body


# ============== Source-level guarantees ==============
class TestSourceGuarantees:
    def test_no_admin_token_in_localstorage_frontend(self):
        out = subprocess.run(
            ["grep", "-rn", "adminToken", "/app/frontend/src"],
            capture_output=True, text=True
        ).stdout
        for line in out.splitlines():
            if "localStorage.setItem" in line:
                pytest.fail(f"adminToken still written to localStorage: {line}")

    def test_bcrypt_hash_format(self):
        import sys
        sys.path.insert(0, "/app/backend")
        from dotenv import load_dotenv
        load_dotenv("/app/backend/.env")
        import importlib
        auth = importlib.import_module("auth")
        importlib.reload(auth)
        assert auth.ADMIN_PASSWORD_HASH.startswith("$2b$"), \
            f"hash prefix: {auth.ADMIN_PASSWORD_HASH[:6]}"

    def test_no_default_dev_password_constant(self):
        src = Path("/app/backend/auth.py").read_text()
        assert "DEFAULT_DEV_PASSWORD" not in src
        assert "admin123" not in src
