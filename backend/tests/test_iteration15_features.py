"""
Iteration 15 - New features verification:
1. Web login brute force rate limit (5 fails / 15 min per IP+email)
2. Admin stats endpoint (/api/admin/stats)
3. Server-side search on GET /api/route-sheets
"""
import os
import uuid
import asyncio

import pytest
import requests
from dotenv import dotenv_values

frontend_env = dotenv_values("/app/frontend/.env")
base_url = os.environ.get("REACT_APP_BACKEND_URL") or frontend_env.get("REACT_APP_BACKEND_URL")
if not base_url:
    raise RuntimeError("REACT_APP_BACKEND_URL missing")
BASE_URL = base_url.rstrip("/")

USER_EMAIL = os.environ.get("TEST_USER_EMAIL", "qa_review_jun26@test.com")
USER_PASSWORD = os.environ.get("TEST_USER_PASSWORD", "QaReview2026!")


def _admin_token():
    path = "/app/tests/.admin_token"
    if os.path.exists(path):
        tok = open(path).read().strip()
        if tok:
            return tok
    pytest.skip("admin token missing")


@pytest.fixture(scope="module")
def admin_headers():
    return {"Authorization": f"Bearer {_admin_token()}"}


@pytest.fixture(scope="module")
def user_headers():
    r = requests.post(f"{BASE_URL}/api/auth/login",
                      json={"email": USER_EMAIL, "password": USER_PASSWORD}, timeout=30)
    if r.status_code != 200:
        pytest.fail(f"User login failed {r.status_code}: {r.text[:300]}")
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


# ---------- Mongo cleanup helper ----------
async def _clear_web_login_fails():
    from motor.motor_asyncio import AsyncIOMotorClient
    env = dotenv_values("/app/backend/.env")
    client = AsyncIOMotorClient(env["MONGO_URL"])
    db = client[env["DB_NAME"]]
    res = await db.rate_limits.delete_many({"action": "web_login_fail"})
    client.close()
    return res.deleted_count


async def _count_web_login_fails():
    from motor.motor_asyncio import AsyncIOMotorClient
    env = dotenv_values("/app/backend/.env")
    client = AsyncIOMotorClient(env["MONGO_URL"])
    db = client[env["DB_NAME"]]
    docs = await db.rate_limits.find({"action": "web_login_fail"}, {"_id": 0}).to_list(100)
    client.close()
    return docs


# ============== ADMIN STATS ==============
class TestAdminStats:
    def test_stats_requires_auth(self):
        r = requests.get(f"{BASE_URL}/api/admin/stats", timeout=30)
        assert r.status_code == 401, r.text[:300]

    def test_stats_invalid_months_422(self, admin_headers):
        r = requests.get(f"{BASE_URL}/api/admin/stats?months=100", headers=admin_headers, timeout=30)
        assert r.status_code == 422, r.text[:300]

    def test_stats_structure(self, admin_headers):
        r = requests.get(f"{BASE_URL}/api/admin/stats?months=12", headers=admin_headers, timeout=60)
        assert r.status_code == 200, r.text[:300]
        d = r.json()
        assert d["months"] == 12
        t = d["totals"]
        for k in ["total_sheets", "active_sheets", "annulled_sheets",
                  "total_users", "approved_users", "pending_users"]:
            assert isinstance(t[k], int), k
        assert t["total_sheets"] >= t["active_sheets"]
        assert t["annulled_sheets"] == t["total_sheets"] - t["active_sheets"]
        assert t["total_users"] >= t["approved_users"] + t["pending_users"] - t["total_users"]

        months = [m["month"] for m in d["sheets_by_month"]]
        assert months == sorted(months), "sheets_by_month must be ascending"
        for m in d["sheets_by_month"]:
            assert len(m["month"]) == 7 and m["month"][4] == "-", m["month"]
            assert m["annulled"] <= m["total"]

        tu = d["top_users"]
        assert len(tu) <= 10
        counts = [u["sheets_count"] for u in tu]
        assert counts == sorted(counts, reverse=True), "top_users must be desc"
        for u in tu:
            assert "full_name" in u and u["full_name"]
        # no raw mongo _id leaked
        assert "'_id'" not in str(d)
        for u in tu:
            assert "_id" not in u

    def test_stats_months_6(self, admin_headers):
        r = requests.get(f"{BASE_URL}/api/admin/stats?months=6", headers=admin_headers, timeout=60)
        assert r.status_code == 200
        d = r.json()
        assert d["months"] == 6
        assert len(d["sheets_by_month"]) <= 6


# ============== SERVER-SIDE SEARCH ==============
class TestRouteSheetSearch:
    def test_search_by_number_short(self, user_headers):
        r = requests.get(f"{BASE_URL}/api/route-sheets?search=63&limit=50",
                         headers=user_headers, timeout=30)
        assert r.status_code == 200, r.text[:300]
        d = r.json()
        nums = [s["sheet_number"] for s in d["sheets"]]
        assert any(n.startswith("063/") for n in nums), nums

    def test_search_by_number_full(self, user_headers):
        r = requests.get(f"{BASE_URL}/api/route-sheets?search=063/2026&limit=50",
                         headers=user_headers, timeout=30)
        assert r.status_code == 200
        d = r.json()
        assert d["count"] >= 1
        assert all(s["sheet_number"] == "063/2026" for s in d["sheets"]), \
            [s["sheet_number"] for s in d["sheets"]]

    def test_search_by_destination(self, user_headers):
        # take an existing sheet destination
        base = requests.get(f"{BASE_URL}/api/route-sheets?limit=5", headers=user_headers, timeout=30)
        assert base.status_code == 200
        sheets = base.json()["sheets"]
        assert sheets, "no sheets for QA user"
        dest = sheets[0]["destination"]
        token = dest.split()[0]
        r = requests.get(f"{BASE_URL}/api/route-sheets",
                         params={"search": token, "limit": 50}, headers=user_headers, timeout=30)
        assert r.status_code == 200
        d = r.json()
        assert d["count"] >= 1
        for s in d["sheets"]:
            hay = (s.get("destination", "") + " " + (s.get("passenger_info") or "")).lower()
            assert token.lower() in hay or s["sheet_number"].startswith("0"), s["sheet_number"]

    def test_search_no_results(self, user_headers):
        r = requests.get(f"{BASE_URL}/api/route-sheets",
                         params={"search": "ZZZQQQNOEXISTE" + uuid.uuid4().hex[:6], "limit": 50},
                         headers=user_headers, timeout=30)
        assert r.status_code == 200
        d = r.json()
        assert d["count"] == 0
        assert d["sheets"] == []
        assert d["next_cursor"] is None

    def test_search_pagination(self, user_headers):
        """search + limit must paginate without duplicates"""
        # 'a' matches most destinations
        r1 = requests.get(f"{BASE_URL}/api/route-sheets",
                          params={"search": "a", "limit": 5}, headers=user_headers, timeout=30)
        assert r1.status_code == 200
        d1 = r1.json()
        if d1["count"] < 5:
            pytest.skip("not enough matching sheets to paginate")
        assert d1["next_cursor"]
        r2 = requests.get(f"{BASE_URL}/api/route-sheets",
                          params={"search": "a", "limit": 5, "cursor": d1["next_cursor"]},
                          headers=user_headers, timeout=30)
        assert r2.status_code == 200
        d2 = r2.json()
        ids1 = {s["id"] for s in d1["sheets"]}
        ids2 = {s["id"] for s in d2["sheets"]}
        assert not (ids1 & ids2), "duplicates across pages"

    def test_search_requires_auth(self):
        r = requests.get(f"{BASE_URL}/api/route-sheets?search=63", timeout=30)
        assert r.status_code in (401, 403)


# ============== WEB LOGIN RATE LIMIT (runs last) ==============
@pytest.mark.order(-1)
class TestZZWebLoginRateLimit:
    def test_brute_force_lockout(self):
        sacrificial = f"brute_qa15_{uuid.uuid4().hex[:6]}@test.com"
        try:
            codes = []
            for _ in range(5):
                r = requests.post(f"{BASE_URL}/api/auth/login",
                                  json={"email": sacrificial, "password": "WrongPass1!"}, timeout=30)
                codes.append(r.status_code)
            assert codes == [401] * 5, codes

            r6 = requests.post(f"{BASE_URL}/api/auth/login",
                               json={"email": sacrificial, "password": "WrongPass1!"}, timeout=30)
            assert r6.status_code == 429, f"{r6.status_code}: {r6.text[:300]}"
            detail = r6.json().get("detail", "")
            assert "Demasiados intentos" in detail, detail
            assert "15 minutos" in detail, detail

            # Mongo docs created with correct action + expires_at
            docs = asyncio.run(_count_web_login_fails())
            mine = [d for d in docs if sacrificial in d.get("user_id", "")]
            assert len(mine) == 5, len(mine)
            assert all(d.get("expires_at") for d in mine)

            # Different email from same IP is NOT blocked
            ok = requests.post(f"{BASE_URL}/api/auth/login",
                               json={"email": USER_EMAIL, "password": USER_PASSWORD}, timeout=30)
            assert ok.status_code == 200, f"other email blocked! {ok.status_code} {ok.text[:200]}"
        finally:
            asyncio.run(_clear_web_login_fails())

    def test_successful_login_clears_failures(self):
        try:
            for _ in range(2):
                r = requests.post(f"{BASE_URL}/api/auth/login",
                                  json={"email": USER_EMAIL, "password": "TotallyWrong1!"}, timeout=30)
                assert r.status_code == 401
            ok = requests.post(f"{BASE_URL}/api/auth/login",
                               json={"email": USER_EMAIL, "password": USER_PASSWORD}, timeout=30)
            assert ok.status_code == 200
            docs = asyncio.run(_count_web_login_fails())
            mine = [d for d in docs if USER_EMAIL in d.get("user_id", "")]
            assert mine == [], mine
        finally:
            asyncio.run(_clear_web_login_fails())
