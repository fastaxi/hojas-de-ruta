import asyncio, os, json
from dotenv import load_dotenv
load_dotenv('/app/backend/.env')
from motor.motor_asyncio import AsyncIOMotorClient

EMAIL = "test_reg_ui_900331@test.com"

async def main():
    c = AsyncIOMotorClient(os.environ['MONGO_URL'])
    db = c[os.environ['DB_NAME']]
    u = await db.users.find_one({"email": EMAIL}, {"_id": 0, "password_hash": 0})
    print("USER:", json.dumps(u, default=str)[:800])
    drivers = await db.drivers.find({"user_id": u["id"]}, {"_id": 0}).to_list(50) if u else []
    print("DRIVERS COLLECTION:", json.dumps(drivers, default=str))
    embedded = (u or {}).get("drivers")
    print("EMBEDDED DRIVERS:", json.dumps(embedded, default=str))
    for d in (drivers or []) + (embedded or []):
        assert "_key" not in d, "LEAKED _key in driver: %s" % d
    print("OK: no _key leaked")

asyncio.run(main())
