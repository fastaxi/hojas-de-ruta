"""Seed a PENDING user via API for admin approval UI test (iteration 13)."""
import json
import time
import requests
from dotenv import dotenv_values

BASE = dotenv_values("/app/frontend/.env")["REACT_APP_BACKEND_URL"].rstrip("/")
sfx = str(int(time.time()))[-6:]
payload = {
    "full_name": f"TEST Approve {sfx}",
    "dni_cif": f"A{sfx}Z",
    "license_number": f"LICAP{sfx}",
    "license_council": "Madrid",
    "phone": "600111222",
    "email": f"test_approve_{sfx}@test.com",
    "password": "TestApprove2026!",
    "vehicle_brand": "Seat",
    "vehicle_model": "Ibiza",
    "vehicle_plate": f"AP{sfx}",
}
r = requests.post(f"{BASE}/api/auth/register", json=payload)
print(r.status_code, r.text[:400])
print(json.dumps({"email": payload["email"], "name": payload["full_name"]}))
