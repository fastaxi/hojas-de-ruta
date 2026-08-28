"""Iteration 14 - Regresión post-fixes de deployment (CORS, TTL eliminado, retención)."""
import os
import asyncio

import pytest
import requests
from dotenv import dotenv_values

frontend_env = dotenv_values("/app/frontend/.env")
backend_env = dotenv_values("/app/backend/.env")
base_url = os.environ.get("REACT_APP_BACKEND_URL") or frontend_env.get("REACT_APP_BACKEND_URL")
if not base_url:
    raise RuntimeError("REACT_APP_BACKEND_URL missing")
BASE_URL = base_url.rstrip("/")

USER_EMAIL = os.environ.get("TEST_USER_EMAIL", "qa_review_jun26@test.com")
USER_PASSWORD = os.environ.get("TEST_USER_PASSWORD", "QaReview2026!")


@pytest.fixture(scope="module")
def admin_token():
    with open("/app/tests/.admin_token") as fh:
        return fh.read().strip()


@pytest.fixture(scope="module")
def user_token():
    r = requests.post(f"{BASE_URL}/api/auth/login",
                      json={"email": USER_EMAIL, "password": USER_PASSWORD}, timeout=30)
    if r.status_code != 200:
        pytest.fail(f"User login failed {r.status_code}: {r.text[:300]}")
    return r.json()["access_token"]


# ---------- CORS ----------
class TestCors:
    def test_cors_allows_credentials(self):
        """El edge público devuelve ACAO:* (ver informe iteración 14); el backend
        directo refleja el Origin. Ambas variantes se aceptan aquí."""
        r = requests.get(f"{BASE_URL}/api/health",
                         headers={"Origin": BASE_URL, "Cookie": "refresh_token=x"}, timeout=30)
        assert r.status_code == 200
        acao = r.headers.get("access-control-allow-origin")
        assert acao in ("*", BASE_URL), acao
        assert r.headers.get("access-control-allow-credentials") == "true"

    def test_expose_headers_present(self):
        r = requests.get(f"{BASE_URL}/api/health", headers={"Origin": BASE_URL}, timeout=30)
        exposed = (r.headers.get("access-control-expose-headers") or "")
        assert "X-Total-Count" in exposed and "X-Next-Cursor" in exposed


# ---------- Índices / TTL ----------
class TestIndexes:
    def test_route_sheets_has_no_ttl_index(self):
        from motor.motor_asyncio import AsyncIOMotorClient

        async def check():
            db = AsyncIOMotorClient(backend_env["MONGO_URL"])[backend_env["DB_NAME"]]
            info = await db.route_sheets.index_information()
            count = await db.route_sheets.count_documents({})
            return info, count

        info, count = asyncio.run(check())
        ttl = {k: v for k, v in info.items() if "expireAfterSeconds" in v}
        assert ttl == {}, f"route_sheets tiene índices TTL: {ttl}"
        assert "purge_at_1" in info
        assert "expireAfterSeconds" not in info["purge_at_1"]
        assert count >= 165, f"Se perdieron hojas: {count}"

    def test_ephemeral_ttls_still_present(self):
        from motor.motor_asyncio import AsyncIOMotorClient

        async def check():
            db = AsyncIOMotorClient(backend_env["MONGO_URL"])[backend_env["DB_NAME"]]
            out = {}
            for c in ["password_reset_tokens", "rate_limits", "pdf_cache", "mobile_refresh_tokens"]:
                info = await db[c].index_information()
                out[c] = [k for k, v in info.items() if "expireAfterSeconds" in v]
            return out

        out = asyncio.run(check())
        for coll, ttls in out.items():
            assert ttls, f"{coll} perdió su índice TTL"


# ---------- Retención explícita ----------
class TestRetention:
    def test_retention_last_run(self, admin_token):
        r = requests.get(f"{BASE_URL}/api/admin/retention-runs/last",
                         headers={"Authorization": f"Bearer {admin_token}"}, timeout=30)
        assert r.status_code == 200
        d = r.json()
        assert "status" in d and "last_run_at" in d

    def test_retention_dry_run_does_not_delete(self, admin_token):
        h = {"Authorization": f"Bearer {admin_token}"}
        before = requests.get(f"{BASE_URL}/api/admin/route-sheets?limit=1", headers=h, timeout=30)
        total_before = int(before.headers["X-Total-Count"])

        r = requests.post(f"{BASE_URL}/api/admin/run-retention?dry_run=true", headers=h, timeout=60)
        assert r.status_code == 200
        d = r.json()
        assert d["dry_run"] is True
        assert "to_purge" in d and "to_hide" in d

        after = requests.get(f"{BASE_URL}/api/admin/route-sheets?limit=1", headers=h, timeout=30)
        assert int(after.headers["X-Total-Count"]) == total_before


# ---------- Paginación admin (headers expuestos) ----------
class TestAdminPagination:
    def test_cursor_pagination_no_duplicates(self, admin_token):
        h = {"Authorization": f"Bearer {admin_token}"}
        r1 = requests.get(f"{BASE_URL}/api/admin/route-sheets?limit=20", headers=h, timeout=30)
        assert r1.status_code == 200
        assert "X-Total-Count" in r1.headers
        cursor = r1.headers.get("X-Next-Cursor")
        assert cursor, "Falta X-Next-Cursor en la primera página"
        ids1 = [s["id"] for s in r1.json()]
        assert len(ids1) == 20

        r2 = requests.get(f"{BASE_URL}/api/admin/route-sheets?limit=20&cursor={cursor}",
                          headers=h, timeout=30)
        assert r2.status_code == 200
        ids2 = [s["id"] for s in r2.json()]
        assert set(ids1).isdisjoint(set(ids2)), "Paginación devuelve duplicados"
        assert all("_id" not in s for s in r2.json())


# ---------- Brute force web login ----------
class TestWebLoginBruteForce:
    def test_web_login_rate_limit_after_5_failures(self):
        statuses = []
        try:
            for _ in range(7):
                r = requests.post(f"{BASE_URL}/api/auth/login",
                                  json={"email": "TEST_nonexistent_bf@test.com", "password": "wrong"},
                                  timeout=30)
                statuses.append(r.status_code)
            assert 429 in statuses, (
                f"/api/auth/login NO tiene lockout por fuerza bruta; statuses={statuses}"
            )
        finally:
            # Clean sacrifice-email lockout so reruns within 15 min don't misbehave
            from pymongo import MongoClient
            db = MongoClient('mongodb://localhost:27017')['rutasfast_db']
            db.rate_limits.delete_many({'action': 'web_login_fail'})
