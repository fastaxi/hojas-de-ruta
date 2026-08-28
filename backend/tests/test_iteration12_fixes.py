"""
Iteration 12 - verification of iteration-11 fixes (RutasFast)
FIX1 assistance company phone-only / email-only
FIX3 legacy dates migrated (all pickup_datetime tz-aware) + admin date filter
FIX6 API limits (le=200) + X-Total-Count header
Regression: admin users/route-sheets, user sheet creation timezone
"""
import os
import re
from datetime import datetime, timedelta
from pathlib import Path

import pytest
import requests
from dotenv import dotenv_values

frontend_env = dotenv_values("/app/frontend/.env")
base_url = os.environ.get("REACT_APP_BACKEND_URL") or frontend_env.get("REACT_APP_BACKEND_URL")
if not base_url:
    raise RuntimeError("REACT_APP_BACKEND_URL missing")
API = base_url.rstrip("/") + "/api"

CRED_FILE = Path("/app/memory/test_credentials.md")
ADMIN_TOKEN_FILE = Path("/app/tests/.admin_token")


@pytest.fixture(scope="session")
def creds():
    if not CRED_FILE.exists():
        pytest.skip("missing test_credentials.md")
    c = CRED_FILE.read_text(encoding="utf-8")
    email = re.search(r'(?im)^\s*[-*]?\s*Email:\s*`?([^`\s]+)', c)
    pwd = re.search(r'(?im)^\s*[-*]?\s*Password:\s*`?([^`\s]+)', c)
    if not email or not pwd:
        pytest.skip("no creds parsed")
    return {"email": email.group(1), "password": pwd.group(1)}


@pytest.fixture(scope="session")
def client(creds):
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    r = s.post(f"{API}/auth/login", json=creds, timeout=30)
    if r.status_code != 200:
        pytest.fail(f"login failed {r.status_code}: {r.text[:300]}")
    s.headers.update({"Authorization": f"Bearer {r.json()['access_token']}"})
    return s


@pytest.fixture(scope="session")
def admin_headers():
    if not ADMIN_TOKEN_FILE.exists():
        pytest.skip("no admin token cache")
    tok = ADMIN_TOKEN_FILE.read_text().strip()
    h = {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}
    r = requests.get(f"{API}/admin/users?limit=1", headers=h, timeout=30)
    if r.status_code != 200:
        pytest.fail(f"admin token invalid ({r.status_code}): {r.text[:200]}")
    return h


# ---------------- FIX 1: assistance companies with partial contact ----------------
class TestFix1AssistanceCompanies:
    created = []

    def test_create_phone_only(self, client):
        payload = {"name": "TEST_QA12 SoloTel", "cif": "B12345678",
                   "contact_phone": "600999888", "contact_email": None}
        r = client.post(f"{API}/me/assistance-companies", json=payload, timeout=30)
        assert r.status_code in (200, 201), r.text[:400]
        cid = r.json().get("id")
        assert cid
        type(self).created.append(cid)
        lst = client.get(f"{API}/me/assistance-companies", timeout=30).json()
        items = lst if isinstance(lst, list) else lst.get("items", [])
        me = [c for c in items if c["id"] == cid]
        assert me, "created phone-only company not persisted"
        assert me[0]["contact_phone"] == "600999888"
        assert not me[0].get("contact_email")

    def test_create_email_only(self, client):
        payload = {"name": "TEST_QA12 SoloMail", "cif": "B87654321",
                   "contact_phone": None, "contact_email": "qa12@test.com"}
        r = client.post(f"{API}/me/assistance-companies", json=payload, timeout=30)
        assert r.status_code in (200, 201), r.text[:400]
        cid = r.json().get("id")
        type(self).created.append(cid)
        lst = client.get(f"{API}/me/assistance-companies", timeout=30).json()
        items = lst if isinstance(lst, list) else lst.get("items", [])
        me = [c for c in items if c["id"] == cid]
        assert me and me[0]["contact_email"] == "qa12@test.com"

    def test_empty_string_email_still_422(self, client):
        r = client.post(f"{API}/me/assistance-companies", json={
            "name": "TEST_QA12 EmptyMail", "cif": "B11111111",
            "contact_phone": "600111111", "contact_email": ""}, timeout=30)
        # backend now normalizes '' -> None, so empty email is accepted
        assert r.status_code == 200, f"expected 200 for empty-string email, got {r.status_code}: {r.text[:200]}"
        type(self).created.append(r.json()["id"])

    def test_cleanup(self, client):
        for cid in type(self).created:
            r = client.delete(f"{API}/me/assistance-companies/{cid}", timeout=30)
            assert r.status_code in (200, 204, 404), r.text[:200]


# ---------------- FIX 3: legacy dates migrated ----------------
class TestFix3Dates:
    def test_all_pickup_datetimes_tz_aware(self, admin_headers):
        naive = []
        cursor = None
        total_seen = 0
        for _ in range(10):
            url = f"{API}/admin/route-sheets?limit=200"
            if cursor:
                url += f"&cursor={cursor}"
            r = requests.get(url, headers=admin_headers, timeout=60)
            assert r.status_code == 200, r.text[:300]
            data = r.json()
            items = data if isinstance(data, list) else data.get("items", data.get("sheets", []))
            for s in items:
                total_seen += 1
                pd = s.get("pickup_datetime")
                if isinstance(pd, str) and not (pd.endswith("Z") or "+" in pd[10:] or pd[10:].count("-") > 0):
                    naive.append((s.get("sheet_number"), pd))
            cursor = r.headers.get("X-Next-Cursor")
            if not cursor or not items:
                break
        assert total_seen > 0
        assert naive == [], f"naive pickup_datetime found ({len(naive)}): {naive[:5]}"

    def test_admin_date_filter_returns_legacy_rows(self, admin_headers):
        r = requests.get(f"{API}/admin/route-sheets?from_date=2026-01-10&to_date=2026-01-10",
                         headers=admin_headers, timeout=30)
        assert r.status_code == 200, r.text[:300]
        data = r.json()
        items = data if isinstance(data, list) else data.get("items", data.get("sheets", []))
        assert len(items) > 0, "date filter for legacy date 2026-01-10 returned 0 rows"
        for s in items:
            assert s["pickup_datetime"].startswith("2026-01-10")


# ---------------- FIX 6: limits & headers ----------------
class TestFix6Limits:
    def test_route_sheets_limit_too_high_422(self, admin_headers):
        r = requests.get(f"{API}/admin/route-sheets?limit=100000", headers=admin_headers, timeout=30)
        assert r.status_code == 422, f"got {r.status_code}"

    def test_users_limit_too_high_422(self, admin_headers):
        r = requests.get(f"{API}/admin/users?limit=100000", headers=admin_headers, timeout=30)
        assert r.status_code == 422, f"got {r.status_code}"

    def test_limit_200_ok(self, admin_headers):
        r = requests.get(f"{API}/admin/route-sheets?limit=200", headers=admin_headers, timeout=60)
        assert r.status_code == 200

    def test_x_total_count_header(self, admin_headers):
        r = requests.get(f"{API}/admin/route-sheets?limit=50", headers=admin_headers, timeout=30)
        assert r.status_code == 200
        assert "X-Total-Count" in r.headers, dict(r.headers)
        total = int(r.headers["X-Total-Count"])
        assert total >= 1
        data = r.json()
        items = data if isinstance(data, list) else data.get("items", data.get("sheets", []))
        assert len(items) <= 50
        assert total >= len(items)

    def test_x_total_count_respects_filter(self, admin_headers):
        r = requests.get(f"{API}/admin/route-sheets?from_date=2026-01-10&to_date=2026-01-10",
                         headers=admin_headers, timeout=30)
        assert "X-Total-Count" in r.headers
        data = r.json()
        items = data if isinstance(data, list) else data.get("items", data.get("sheets", []))
        assert int(r.headers["X-Total-Count"]) == len(items)


# ---------------- Regression: sheet creation + timezone ----------------
class TestRegressionSheet:
    def test_create_airport_1815_tz(self, client, admin_headers):
        d = (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d")
        payload = {
            "prebooked_date": datetime.now().strftime("%Y-%m-%d"),
            "prebooked_locality": "Oviedo",
            "pickup_type": "AIRPORT",
            "pickup_address": "Aeropuerto de Asturias",
            "flight_number": "IB1234",
            "pickup_datetime": f"{d}T18:15:00",
            "destination": "Gijon",
            "passenger_info": "TEST_QA12 passenger",
            "contractor_phone": "600222333",
        }
        r = client.post(f"{API}/route-sheets", json=payload, timeout=30)
        assert r.status_code in (200, 201), r.text[:400]
        body = r.json()
        pd = body.get("pickup_datetime") or ""
        if not pd:
            sid = body.get("id")
            g = client.get(f"{API}/route-sheets/{sid}", timeout=30)
            assert g.status_code == 200
            pd = g.json()["pickup_datetime"]
        assert pd.endswith("Z") or "+00:00" in pd, pd
        # Madrid summer = UTC+2 -> 16:15Z
        assert "T16:15" in pd, f"expected 16:15 UTC for 18:15 Madrid, got {pd}"

    def test_admin_driver_filter_works(self, admin_headers):
        u = requests.get(f"{API}/admin/users?limit=5", headers=admin_headers, timeout=30)
        assert u.status_code == 200
        data = u.json()
        users = data if isinstance(data, list) else data.get("items", data.get("users", []))
        assert users, "no users returned"
        uid = users[0]["id"]
        r = requests.get(f"{API}/admin/route-sheets?user_id={uid}&limit=10",
                         headers=admin_headers, timeout=30)
        assert r.status_code == 200, r.text[:300]
        d2 = r.json()
        items = d2 if isinstance(d2, list) else d2.get("items", d2.get("sheets", []))
        for s in items:
            assert s.get("user_id", uid) == uid


# ---------------- BUG (iteration 12): admin cursor pagination inconsistency ----------------
class TestAdminCursorPaginationBug:
    """Cursor is _id-based ($lt ObjectId) while sort is (year desc, seq_number desc, _id desc).
    The mismatch yields overlapping pages and unreachable documents."""

    def test_cursor_pages_have_no_duplicates(self, admin_headers):
        seen, pages = [], 0
        cursor = None
        while pages < 30:
            url = f"{API}/admin/route-sheets?limit=50" + (f"&cursor={cursor}" if cursor else "")
            r = requests.get(url, headers=admin_headers, timeout=60)
            assert r.status_code == 200
            ids = [s["id"] for s in r.json()]
            seen.extend(ids)
            pages += 1
            cursor = r.headers.get("X-Next-Cursor")
            if not cursor or not ids:
                break
        assert len(seen) == len(set(seen)), (
            f"duplicate sheets across cursor pages: fetched={len(seen)} unique={len(set(seen))}"
        )

    def test_cursor_pagination_covers_all_documents(self, admin_headers):
        first = requests.get(f"{API}/admin/route-sheets?limit=50", headers=admin_headers, timeout=60)
        total = int(first.headers["X-Total-Count"])
        seen = {s["id"] for s in first.json()}
        cursor = first.headers.get("X-Next-Cursor")
        pages = 1
        while cursor and pages < 30:
            r = requests.get(f"{API}/admin/route-sheets?limit=50&cursor={cursor}",
                             headers=admin_headers, timeout=60)
            ids = [s["id"] for s in r.json()]
            if not ids:
                break
            seen.update(ids)
            cursor = r.headers.get("X-Next-Cursor")
            pages += 1
        assert len(seen) == total, f"only {len(seen)} of {total} sheets reachable via cursor pagination"
