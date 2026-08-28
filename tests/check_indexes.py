import asyncio, os
from dotenv import load_dotenv
load_dotenv('/app/backend/.env')
from motor.motor_asyncio import AsyncIOMotorClient

async def main():
    c = AsyncIOMotorClient(os.environ['MONGO_URL'])
    db = c[os.environ['DB_NAME']]
    names = await db.list_collection_names()
    print("collections:", sorted(names))
    for coll in sorted(names):
        idx = await db[coll].index_information()
        ttl = {k: v for k, v in idx.items() if 'expireAfterSeconds' in v}
        cnt = await db[coll].count_documents({})
        print(f"\n== {coll} count={cnt}")
        print("   indexes:", list(idx.keys()))
        if ttl:
            print("   TTL:", {k: v['expireAfterSeconds'] for k, v in ttl.items()})
    rs = await db.route_sheets.index_information()
    print("\nroute_sheets full index info:", rs)

asyncio.run(main())
