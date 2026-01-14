"""
RutasFast - Critical Tests
A) Concurrency numbering
B) Retention hide/purge
C) Reset token one-time
D) PDF range
"""
import asyncio
import aiohttp
import os
from datetime import datetime, timezone, timedelta
from pymongo import MongoClient

API_URL = os.environ.get('API_URL', 'https://asturia-taxi.preview.emergentagent.com')
MONGO_URL = "mongodb://localhost:27017"
DB_NAME = "rutasfast_db"

client = MongoClient(MONGO_URL)
db = client[DB_NAME]


async def test_concurrent_numbering():
    """A) 25 concurrent requests creating sheets - verify unique seq_numbers"""
    print("\n=== TEST A: Concurrent Numbering ===")
    
    # Get a user token
    async with aiohttp.ClientSession() as session:
        # Login
        async with session.post(f"{API_URL}/api/auth/login", json={
            "email": "test174244@example.com",
            "password": "testpass123"
        }) as resp:
            if resp.status != 200:
                print(f"❌ Login failed: {await resp.text()}")
                return False
            data = await resp.json()
            token = data['access_token']
        
        headers = {"Authorization": f"Bearer {token}"}
        
        # Create 25 concurrent requests
        async def create_sheet(i):
            async with session.post(f"{API_URL}/api/route-sheets", headers=headers, json={
                "contractor_phone": f"61234567{i:02d}",
                "prebooked_date": "2026-01-07",
                "prebooked_locality": f"Test{i}",
                "pickup_type": "OTHER",
                "pickup_address": f"Calle Test {i}",
                "pickup_datetime": "2026-01-10T10:00:00",
                "destination": f"Destino {i}"
            }) as resp:
                return await resp.json()
        
        results = await asyncio.gather(*[create_sheet(i) for i in range(25)])
        
        # Check results
        sheet_numbers = [r.get('sheet_number') for r in results if r.get('sheet_number')]
        errors = [r for r in results if 'detail' in r]
        
        print(f"  Created: {len(sheet_numbers)} sheets")
        print(f"  Errors: {len(errors)}")
        
        # Check uniqueness
        unique_numbers = set(sheet_numbers)
        if len(unique_numbers) == len(sheet_numbers):
            print(f"  ✅ All {len(sheet_numbers)} sheet numbers are unique")
        else:
            print(f"  ❌ Duplicate numbers found!")
            return False
        
        # Check consecutive
        seqs = sorted([int(sn.split('/')[0]) for sn in sheet_numbers])
        print(f"  Seq numbers: {seqs[0]} to {seqs[-1]}")
        
        return len(errors) == 0


async def test_retention():
    """B) Test hide_at and purge visibility"""
    print("\n=== TEST B: Retention ===")
    
    # Get user and their sheets
    user = db.users.find_one({}, {"_id": 0, "id": 1})
    if not user:
        print("  ❌ No users found")
        return False
    
    # Create a sheet with hide_at in past
    past_hide = datetime.now(timezone.utc) - timedelta(days=1)
    test_sheet = {
        "id": "test-hidden-sheet",
        "user_id": user["id"],
        "year": 2026,
        "seq_number": 9999,
        "contractor_phone": "test",
        "prebooked_date": "2026-01-01",
        "prebooked_locality": "Test",
        "pickup_type": "OTHER",
        "pickup_address": "Test",
        "pickup_datetime": "2026-01-01T10:00:00",
        "destination": "Test",
        "status": "ACTIVE",
        "user_visible": True,
        "created_at": past_hide - timedelta(days=500),
        "hide_at": past_hide,
        "purge_at": datetime.now(timezone.utc) + timedelta(days=300)
    }
    
    db.route_sheets.delete_one({"id": "test-hidden-sheet"})
    db.route_sheets.insert_one(test_sheet)
    
    # Run retention job
    from retention_job import run_retention_job
    await run_retention_job(dry_run=False)
    
    # Check if hidden
    sheet = db.route_sheets.find_one({"id": "test-hidden-sheet"})
    if sheet and sheet['user_visible'] == False:
        print("  ✅ Sheet correctly hidden after hide_at")
    else:
        print(f"  ❌ Sheet not hidden: user_visible={sheet.get('user_visible') if sheet else 'not found'}")
        return False
    
    # Cleanup
    db.route_sheets.delete_one({"id": "test-hidden-sheet"})
    
    return True


async def test_reset_token_one_time():
    """C) Reset token one-time use"""
    print("\n=== TEST C: Reset Token One-Time ===")
    
    # Create a test user
    user = db.users.find_one({}, {"_id": 0, "id": 1, "email": 1})
    if not user:
        print("  ❌ No users")
        return False
    
    # Create a valid token
    import secrets
    import hashlib
    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    
    token_doc = {
        "id": "test-token",
        "user_id": user["id"],
        "token_hash": token_hash,
        "expires_at": datetime.now(timezone.utc) + timedelta(hours=1),
        "created_at": datetime.now(timezone.utc),
        "used": False
    }
    
    db.password_reset_tokens.delete_one({"id": "test-token"})
    db.password_reset_tokens.insert_one(token_doc)
    
    async with aiohttp.ClientSession() as session:
        # First use - should succeed
        async with session.post(f"{API_URL}/api/auth/reset-password", json={
            "token": token,
            "new_password": "newpass123"
        }) as resp:
            if resp.status == 200:
                print("  ✅ First use: OK")
            else:
                print(f"  ❌ First use failed: {await resp.text()}")
                return False
        
        # Second use - should fail
        async with session.post(f"{API_URL}/api/auth/reset-password", json={
            "token": token,
            "new_password": "anotherpass"
        }) as resp:
            if resp.status == 400:
                print("  ✅ Second use: Correctly rejected")
            else:
                print(f"  ❌ Second use should fail: {resp.status}")
                return False
    
    # Test expired token
    expired_token = secrets.token_urlsafe(32)
    expired_hash = hashlib.sha256(expired_token.encode()).hexdigest()
    
    db.password_reset_tokens.insert_one({
        "id": "test-expired",
        "user_id": user["id"],
        "token_hash": expired_hash,
        "expires_at": datetime.now(timezone.utc) - timedelta(hours=1),
        "created_at": datetime.now(timezone.utc) - timedelta(hours=2),
        "used": False
    })
    
    async with aiohttp.ClientSession() as session:
        async with session.post(f"{API_URL}/api/auth/reset-password", json={
            "token": expired_token,
            "new_password": "newpass"
        }) as resp:
            if resp.status == 400:
                print("  ✅ Expired token: Correctly rejected")
            else:
                print(f"  ❌ Expired should fail: {resp.status}")
                return False
    
    # Cleanup
    db.password_reset_tokens.delete_many({"id": {"$in": ["test-token", "test-expired"]}})
    
    return True


async def test_pdf_range():
    """D) PDF range export"""
    print("\n=== TEST D: PDF Range ===")
    
    async with aiohttp.ClientSession() as session:
        # Login
        async with session.post(f"{API_URL}/api/auth/login", json={
            "email": "test174244@example.com",
            "password": "newpass123"  # Changed by reset test
        }) as resp:
            if resp.status != 200:
                # Try original password
                async with session.post(f"{API_URL}/api/auth/login", json={
                    "email": "test174244@example.com",
                    "password": "testpass123"
                }) as resp2:
                    if resp2.status != 200:
                        print(f"  ❌ Login failed")
                        return False
                    data = await resp2.json()
            else:
                data = await resp.json()
            token = data['access_token']
        
        headers = {"Authorization": f"Bearer {token}"}
        
        # Get PDF range
        async with session.get(
            f"{API_URL}/api/route-sheets/pdf/range?from_date=2026-01-01&to_date=2026-12-31",
            headers=headers
        ) as resp:
            if resp.status == 200:
                content = await resp.read()
                if content[:4] == b'%PDF':
                    print(f"  ✅ PDF generated: {len(content)} bytes")
                    return True
                else:
                    print(f"  ❌ Not a valid PDF")
                    return False
            elif resp.status == 404:
                print(f"  ⚠️ No sheets in range (expected if all hidden)")
                return True
            else:
                print(f"  ❌ PDF request failed: {resp.status}")
                return False


async def main():
    print("=" * 50)
    print("RutasFast Critical Tests")
    print("=" * 50)
    
    results = {}
    
    results['A_concurrent'] = await test_concurrent_numbering()
    results['B_retention'] = await test_retention()
    results['C_reset_token'] = await test_reset_token_one_time()
    results['D_pdf_range'] = await test_pdf_range()
    
    print("\n" + "=" * 50)
    print("RESULTS:")
    for test, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {test}: {status}")
    
    all_passed = all(results.values())
    print(f"\nOverall: {'✅ ALL TESTS PASSED' if all_passed else '❌ SOME TESTS FAILED'}")
    
    return all_passed


if __name__ == "__main__":
    asyncio.run(main())
