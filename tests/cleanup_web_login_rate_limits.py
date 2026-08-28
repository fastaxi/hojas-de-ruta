"""Cleanup helper: remove residual web_login_fail rate limit docs after brute-force tests."""
import asyncio
from dotenv import dotenv_values
from motor.motor_asyncio import AsyncIOMotorClient


async def main():
    env = dotenv_values("/app/backend/.env")
    client = AsyncIOMotorClient(env["MONGO_URL"])
    db = client[env["DB_NAME"]]
    before = await db.rate_limits.count_documents({"action": "web_login_fail"})
    res = await db.rate_limits.delete_many({"action": "web_login_fail"})
    print(f"web_login_fail docs before={before} deleted={res.deleted_count}")
    remaining = await db.rate_limits.count_documents({"action": "web_login_fail"})
    print("remaining:", remaining)
    client.close()


asyncio.run(main())
