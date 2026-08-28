"""
General regression audit (iteration 11) - RutasFast
Covers: health/version, web auth, registration+approval, route sheets (3 types + validations),
timezone UTC-awareness, sequential numbering, PDF, annulment, pagination,
assistance companies CRUD, admin API.
"""
import os
import re
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import requests
from dotenv import dotenv_values

frontend_env = dotenv_values("/app/frontend/.env")
base_url = os.environ.get("REACT_APP_BACKEND_URL") or frontend_env.get("REACT_APP_BACKEND_URL")
if not base_url:
    raise RuntimeError("REACT_APP_BACKEND_URL missing")
BASE_URL = base_url.rstrip("/")
API = f"{BASE_URL}/api"

CRED_FILE = Path("/app/memory/test_credentials.md")
ADMIN_TOKEN_FILE = Path("/app/tests/.admin_token")


# ---------- fixtures ----------
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
    if r.status_code == 429:
        import time
        time.sleep(20)
        r = s.post(f"{API}/auth/login", json=creds, timeout=30)
    if r.status_code != 200:
        pytest.fail(f"login failed {r.status_code}: {r.text[:300]}")
    s.headers.update({"Authorization": f"Bearer {r.json()['access_token']}"})
    s.login_response = r
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


def sheet_payload(**over):
    base = {
        "prebooked_date": datetime.now().strftime("%Y-%m-%d"),
        "prebooked_locality": "Oviedo",
        "pickup_type": "OTHER",
        "pickup_address": "Calle Uria 1, Oviedo",
        "pickup_datetime": (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%dT15:30:00"),
        "destination": "Gijon",
        "passenger_info": "TEST_QA passenger",
        "contractor_phone": "600111222",
    }
    base.update(over)
    return base


# ---------- health ----------
class TestHealth:
    def test_health(self):
        r = requests.get(f"{API}/health", timeout=30)
        assert r.status_code == 200
        d = r.json()
        assert d["db_connected"] is True
        assert d["indexes_ok"] is True

    def test_version(self):
        r = requests.get(f"{API}/version", timeout=30)
        assert r.status_code == 200
        assert "api_version" in r.json()


# ---------- auth ----------
class TestAuth:
    def test_login_sets_httponly_refresh_cookie(self, client):
        r = client.login_response
        assert "refresh_token" in r.cookies
        raw = r.headers.get("set-cookie", "")
        assert "HttpOnly" in raw, f"cookie not httpOnly: {raw}"
        d = r.json()
        assert d["user"]["status"] == "APPROVED"
        assert "password_hash" not in d["user"]
        assert "_id" not in d["user"]

    def test_login_bad_password(self, creds):
        r = requests.post(f"{API}/auth/login",
                          json={"email": creds["email"], "password": "Wrong123!"}, timeout=30)
        assert r.status_code in (401, 429)

    def test_me_sheets_requires_auth(self):
        r = requests.get(f"{API}/route-sheets", timeout=30)
        assert r.status_code in (401, 403)


# ---------- registration + admin approval ----------
class TestRegistrationAndApproval:
    new_user = {}

    def test_register_pending(self):
        email = f"qa_audit_{uuid.uuid4().hex[:8]}@test.com"
        payload = {
            "full_name": "TEST_QA Audit User", "dni_cif": "12345678Z",
            "license_number": "L-999", "license_council": "Oviedo",
            "phone": "600999888", "email": email, "password": "QaAudit2026!",
            "vehicle_brand": "Seat", "vehicle_model": "Leon", "vehicle_plate": "1234ABC",
        }
        r = requests.post(f"{API}/auth/register", json=payload, timeout=30)
        assert r.status_code == 200, r.text[:300]
        d = r.json()
        assert "Pendiente de verificación" in d["message"]
        assert "user_id" in d
        TestRegistrationAndApproval.new_user = {"email": email, "password": payload["password"], "id": d["user_id"]}

    def test_register_missing_fields_422(self):
        r = requests.post(f"{API}/auth/register",
                          json={"email": f"x_{uuid.uuid4().hex[:6]}@t.com", "password": "Abc12345!"}, timeout=30)
        assert r.status_code == 422

    def test_pending_user_cannot_login(self):
        u = TestRegistrationAndApproval.new_user
        assert u, "registration test must run first"
        r = requests.post(f"{API}/auth/login",
                          json={"email": u["email"], "password": u["password"]}, timeout=30)
        assert r.status_code == 403, r.text[:200]
        assert "no ha sido verificado" in r.json()["detail"]

    def test_admin_lists_pending_and_approves(self, admin_headers):
        u = TestRegistrationAndApproval.new_user
        r = requests.get(f"{API}/admin/users?status=PENDING&limit=200", headers=admin_headers, timeout=30)
        assert r.status_code == 200
        users = r.json()
        assert isinstance(users, list)
        assert any(x["id"] == u["id"] for x in users), "new pending user not listed"
        assert all("_id" not in x and "password_hash" not in x for x in users)

        c = requests.get(f"{API}/admin/users/count?status=PENDING", headers=admin_headers, timeout=30)
        assert c.status_code == 200 and isinstance(c.json().get("count"), int)

        a = requests.post(f"{API}/admin/users/{u['id']}/approve", headers=admin_headers, timeout=60)
        assert a.status_code == 200, a.text[:300]

        g = requests.get(f"{API}/admin/users/{u['id']}", headers=admin_headers, timeout=30)
        assert g.status_code == 200 and g.json()["status"] == "APPROVED"

    def test_approved_user_can_login(self):
        u = TestRegistrationAndApproval.new_user
        import time
        r = requests.post(f"{API}/auth/login", json={"email": u["email"], "password": u["password"]}, timeout=30)
        if r.status_code == 429:
            time.sleep(20)
            r = requests.post(f"{API}/auth/login", json={"email": u["email"], "password": u["password"]}, timeout=30)
        assert r.status_code == 200, r.text[:300]
        assert r.json()["user"]["status"] == "APPROVED"

    def test_admin_401_with_bad_token(self):
        r = requests.get(f"{API}/admin/users", headers={"Authorization": "Bearer invalid.token.value"}, timeout=30)
        assert r.status_code == 401


# ---------- assistance companies CRUD ----------
class TestAssistanceCompanies:
    company_id = None

    def test_create_requires_contact(self, client):
        r = client.post(f"{API}/me/assistance-companies",
                        json={"name": "TEST_NoContact", "cif": "B00000000"}, timeout=30)
        assert r.status_code == 422, r.text[:200]

    def test_create_and_list(self, client):
        payload = {"name": "TEST_QA Asistencia", "cif": "B12345678",
                   "contact_phone": "985123456", "contact_email": "qa.asist@example.com"}
        r = client.post(f"{API}/me/assistance-companies", json=payload, timeout=30)
        assert r.status_code == 200, r.text[:300]
        d = r.json()
        assert "id" in d and "_id" not in d
        TestAssistanceCompanies.company_id = d["id"]

        lst = client.get(f"{API}/me/assistance-companies", timeout=30)
        assert lst.status_code == 200
        got = [c for c in lst.json() if c["id"] == d["id"]]
        assert got, "created company not in list"
        assert got[0]["name"] == payload["name"] and got[0]["cif"] == "B12345678"
        assert got[0]["contact_email"] == payload["contact_email"]
        assert "_id" not in got[0]

    def test_empty_string_email_rejected_repro_ui_bug(self, client):
        """Backend now normalizes contact_email:'' -> None (fix for old UI 422 bug)."""
        r = client.post(f"{API}/me/assistance-companies",
                        json={"name": "TEST_QA EmptyEmail", "cif": "B11111111",
                              "contact_phone": "985000111", "contact_email": ""}, timeout=30)
        assert r.status_code == 200, r.text[:300]
        client.delete(f"{API}/me/assistance-companies/{r.json()['id']}", timeout=30)

    def test_update(self, client):
        cid = TestAssistanceCompanies.company_id
        r = client.put(f"{API}/me/assistance-companies/{cid}",
                       json={"name": "TEST_QA Asistencia EDIT", "cif": "B12345678",
                             "contact_phone": "985999999"}, timeout=30)
        assert r.status_code == 200, r.text[:300]
        lst = client.get(f"{API}/me/assistance-companies", timeout=30).json()
        got = [c for c in lst if c["id"] == cid][0]
        assert got["name"] == "TEST_QA Asistencia EDIT"
        assert got["contact_phone"] == "985999999"


# ---------- route sheets ----------
class TestRouteSheets:
    created = []

    def test_airport_without_flight_fails(self, client):
        r = client.post(f"{API}/route-sheets", json=sheet_payload(pickup_type="AIRPORT"), timeout=30)
        assert r.status_code == 400
        assert "vuelo" in r.json()["detail"].lower()

    def test_roadside_without_company_fails(self, client):
        r = client.post(f"{API}/route-sheets",
                        json=sheet_payload(pickup_type="ROADSIDE", pickup_address="A-66 km 20"), timeout=30)
        assert r.status_code == 400
        assert "asistencia" in r.json()["detail"].lower()

    def test_no_contractor_contact_fails(self, client):
        p = sheet_payload()
        p.pop("contractor_phone")
        r = client.post(f"{API}/route-sheets", json=p, timeout=30)
        assert r.status_code == 400

    def test_create_airport(self, client):
        r = client.post(f"{API}/route-sheets",
                        json=sheet_payload(pickup_type="AIRPORT", flight_number="vy 1234", pickup_address=None),
                        timeout=30)
        assert r.status_code == 200, r.text[:300]
        d = r.json()
        assert re.match(r"^\d{3,}/\d{4}$", d["sheet_number"])
        TestRouteSheets.created.append(d)
        g = client.get(f"{API}/route-sheets/{d['id']}", timeout=30).json()
        assert g["flight_number"] == "VY1234"
        assert g["pickup_address"] == "Aeropuerto de Asturias"

    def test_create_other(self, client):
        r = client.post(f"{API}/route-sheets", json=sheet_payload(), timeout=30)
        assert r.status_code == 200, r.text[:300]
        TestRouteSheets.created.append(r.json())

    def test_create_roadside(self, client):
        cid = TestAssistanceCompanies.company_id
        assert cid, "assistance company tests must run first"
        r = client.post(f"{API}/route-sheets",
                        json=sheet_payload(pickup_type="ROADSIDE", pickup_address="A-66 km 20",
                                           assistance_company_id=cid), timeout=30)
        assert r.status_code == 200, r.text[:300]
        d = r.json()
        TestRouteSheets.created.append(d)
        g = client.get(f"{API}/route-sheets/{d['id']}", timeout=30).json()
        assert g["assistance_company_snapshot"]["cif"] == "B12345678"

    def test_sequential_numbering_no_duplicates(self, client):
        nums = [int(s["sheet_number"].split("/")[0]) for s in TestRouteSheets.created]
        assert len(set(nums)) == len(nums), f"duplicate numbers {nums}"
        assert nums == sorted(nums) and nums[-1] - nums[0] == len(nums) - 1, f"not sequential {nums}"

    def test_pickup_datetime_utc_aware_and_correct(self, client):
        sid = TestRouteSheets.created[0]["id"]
        # list endpoint
        r = client.get(f"{API}/route-sheets?limit=50", timeout=30)
        assert r.status_code == 200
        data = r.json()
        assert "sheets" in data and "next_cursor" in data
        sheet = [s for s in data["sheets"] if s["id"] == sid][0]
        pdt = sheet["pickup_datetime"]
        assert isinstance(pdt, str) and (pdt.endswith("Z") or "+00:00" in pdt), f"not UTC aware: {pdt}"
        # 15:30 Madrid in summer (CEST) -> 13:30 UTC
        parsed = datetime.fromisoformat(pdt.replace("Z", "+00:00"))
        assert parsed.tzinfo is not None
        assert (parsed.hour, parsed.minute) == (13, 30), f"expected 13:30Z got {parsed}"
        # detail endpoint
        det = client.get(f"{API}/route-sheets/{sid}", timeout=30).json()
        pdt2 = det["pickup_datetime"]
        assert pdt2.endswith("Z") or "+00:00" in pdt2, f"detail not UTC aware: {pdt2}"
        assert datetime.fromisoformat(pdt2.replace("Z", "+00:00")) == parsed
        assert "_id" not in det

    def test_created_at_utc_aware(self, client):
        det = client.get(f"{API}/route-sheets/{TestRouteSheets.created[0]['id']}", timeout=30).json()
        ca = det["created_at"]
        assert ca.endswith("Z") or "+00:00" in ca, f"created_at not UTC aware: {ca}"

    def test_pdf_single(self, client):
        sid = TestRouteSheets.created[0]["id"]
        r = client.get(f"{API}/route-sheets/{sid}/pdf", timeout=90)
        assert r.status_code == 200, r.text[:200]
        assert r.headers["content-type"].startswith("application/pdf")
        assert len(r.content) > 1000 and r.content[:4] == b"%PDF"

    def test_pdf_range(self, client):
        today = datetime.now().strftime("%Y-%m-%d")
        tomorrow = (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d")
        r = client.get(f"{API}/route-sheets/pdf/range?from_date={today}&to_date={tomorrow}", timeout=120)
        assert r.status_code == 200, r.text[:300]
        assert r.headers["content-type"].startswith("application/pdf")
        assert r.content[:4] == b"%PDF"

    def test_sheets_immutable_no_put(self, client):
        sid = TestRouteSheets.created[0]["id"]
        r = client.put(f"{API}/route-sheets/{sid}", json={"destination": "hack"}, timeout=30)
        assert r.status_code in (404, 405)

    def test_annul_and_history_filter(self, client):
        sid = TestRouteSheets.created[-1]["id"]
        r = client.post(f"{API}/route-sheets/{sid}/annul", json={"reason": "TEST_QA anulacion"}, timeout=30)
        assert r.status_code == 200, r.text[:300]
        # default list excludes annulled
        active = client.get(f"{API}/route-sheets?limit=100", timeout=30).json()["sheets"]
        assert all(s["id"] != sid for s in active)
        # include_annulled shows it
        allsheets = client.get(f"{API}/route-sheets?limit=100&include_annulled=true", timeout=30).json()["sheets"]
        got = [s for s in allsheets if s["id"] == sid]
        assert got and got[0]["status"] == "ANNULLED"
        assert got[0].get("annul_reason") == "TEST_QA anulacion"
        # double annul fails
        r2 = client.post(f"{API}/route-sheets/{sid}/annul", json={"reason": "again"}, timeout=30)
        assert r2.status_code == 400

    def test_annulled_pdf_still_downloadable(self, client):
        sid = TestRouteSheets.created[-1]["id"]
        r = client.get(f"{API}/route-sheets/{sid}/pdf", timeout=90)
        assert r.status_code == 200 and r.content[:4] == b"%PDF"

    def test_pagination_cursor(self, client):
        r = client.get(f"{API}/route-sheets?limit=2&include_annulled=true", timeout=30)
        assert r.status_code == 200
        d = r.json()
        assert d["count"] <= 2
        if d["next_cursor"]:
            r2 = client.get(f"{API}/route-sheets?limit=2&include_annulled=true&cursor={d['next_cursor']}", timeout=30)
            assert r2.status_code == 200
            ids1 = {s["id"] for s in d["sheets"]}
            ids2 = {s["id"] for s in r2.json()["sheets"]}
            assert not (ids1 & ids2), "cursor pagination returns duplicates"

    def test_limit_over_max_rejected(self, client):
        r = client.get(f"{API}/route-sheets?limit=500", timeout=30)
        assert r.status_code == 422

    def test_cross_user_isolation(self, client):
        r = client.get(f"{API}/route-sheets/{uuid.uuid4().hex}", timeout=30)
        assert r.status_code == 404


# ---------- admin data endpoints ----------
class TestAdminApi:
    def test_admin_users_pagination(self, admin_headers):
        r = requests.get(f"{API}/admin/users?limit=5&offset=0", headers=admin_headers, timeout=30)
        assert r.status_code == 200
        page1 = r.json()
        assert len(page1) == 5
        r2 = requests.get(f"{API}/admin/users?limit=5&offset=5", headers=admin_headers, timeout=30)
        assert r2.status_code == 200
        page2 = r2.json()
        assert not ({u["id"] for u in page1} & {u["id"] for u in page2}), "offset pagination overlaps"
        c = requests.get(f"{API}/admin/users/count", headers=admin_headers, timeout=30)
        assert c.status_code == 200 and c.json()["count"] >= len(page1) + len(page2)

    def test_admin_route_sheets_utc_aware_for_new_sheets(self, admin_headers):
        """Sheets created by this run (stored as BSON date) must be UTC-aware."""
        r = requests.get(f"{API}/admin/route-sheets?limit=100", headers=admin_headers, timeout=60)
        assert r.status_code == 200, r.text[:300]
        sheets = r.json()
        assert isinstance(sheets, list) and sheets
        new_ids = {s["id"] for s in TestRouteSheets.created}
        checked = 0
        for s in sheets:
            assert "_id" not in s
            if s["id"] in new_ids:
                pdt = s["pickup_datetime"]
                assert pdt.endswith("Z") or "+00:00" in pdt, f"new sheet not UTC aware: {pdt}"
                assert datetime.fromisoformat(pdt.replace("Z", "+00:00")).hour == 13
                checked += 1
        assert checked >= 1, "created sheets not found in admin listing"

    def test_admin_route_sheets_legacy_naive_dates(self, admin_headers):
        """KNOWN DATA ISSUE: legacy docs store pickup_datetime as naive STRING -> no tz suffix."""
        r = requests.get(f"{API}/admin/route-sheets?limit=200", headers=admin_headers, timeout=60)
        assert r.status_code == 200
        naive = [s["sheet_number"] for s in r.json()
                 if isinstance(s.get("pickup_datetime"), str)
                 and not (s["pickup_datetime"].endswith("Z") or "+" in s["pickup_datetime"])]
        assert not naive, (f"{len(naive)} sheets return naive pickup_datetime (stored as string in Mongo); "
                          f"examples: {naive[:5]} - needs data migration to BSON date")

    def test_admin_config(self, admin_headers):
        r = requests.get(f"{API}/admin/config", headers=admin_headers, timeout=30)
        assert r.status_code == 200
        d = r.json()
        assert "_id" not in d
        assert isinstance(d.get("hide_after_months"), int)
        assert isinstance(d.get("purge_after_months"), int)

    def test_admin_retention_last(self, admin_headers):
        r = requests.get(f"{API}/admin/retention-runs/last", headers=admin_headers, timeout=30)
        assert r.status_code in (200, 404)
        if r.status_code == 200:
            assert "_id" not in (r.json() or {})

    def test_admin_sheet_pdf(self, admin_headers):
        sheets = requests.get(f"{API}/admin/route-sheets?limit=1", headers=admin_headers, timeout=60).json()
        sid = sheets[0]["id"]
        r = requests.get(f"{API}/admin/route-sheets/{sid}/pdf", headers=admin_headers, timeout=90)
        assert r.status_code == 200, r.text[:200]
        assert r.content[:4] == b"%PDF"


# ---------- cleanup ----------
@pytest.fixture(scope="session", autouse=True)
def cleanup(request):
    yield
    # remove test assistance company (sheets are immutable by design; left annulled/active)
    try:
        import requests as rq
        cid = TestAssistanceCompanies.company_id
        if cid:
            creds_data = None
            if CRED_FILE.exists():
                c = CRED_FILE.read_text(encoding="utf-8")
                e = re.search(r'(?im)^\s*[-*]?\s*Email:\s*`?([^`\s]+)', c)
                p = re.search(r'(?im)^\s*[-*]?\s*Password:\s*`?([^`\s]+)', c)
                if e and p:
                    creds_data = {"email": e.group(1), "password": p.group(1)}
            if creds_data:
                lr = rq.post(f"{API}/auth/login", json=creds_data, timeout=30)
                if lr.status_code == 200:
                    tok = lr.json()["access_token"]
                    rq.delete(f"{API}/me/assistance-companies/{cid}",
                              headers={"Authorization": f"Bearer {tok}"}, timeout=30)
    except Exception:
        pass
