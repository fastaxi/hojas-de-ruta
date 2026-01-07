"""
RutasFast - Retention Job
Run daily (e.g., 03:30 via cron) to:
1. Hide sheets older than hide_after_months (user_visible=false)
2. Purge sheets older than purge_after_months (hard delete)

Usage:
  python retention_job.py          # Run once
  python retention_job.py --dry-run # Preview without changes

Note: MongoDB TTL index on purge_at handles auto-delete,
but this job ensures hide_at logic works correctly.
"""
import os
import sys
import asyncio
import logging
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# MongoDB connection
mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
db_name = os.environ.get('DB_NAME', 'rutasfast_db')


async def run_retention_job(dry_run: bool = False):
    """
    Execute retention policies:
    1. Set user_visible=false for sheets where hide_at <= now AND user_visible=true
    2. Delete sheets where purge_at <= now (backup to TTL index)
    
    Note: Annulled sheets (status=ANNULLED) are also subject to retention,
    but admin can always see them until purge.
    """
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]
    
    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()
    
    logger.info(f"Starting retention job at {now_iso}")
    logger.info(f"Dry run: {dry_run}")
    
    try:
        # 1. HIDE: Set user_visible=false for expired sheets
        hide_query = {
            "hide_at": {"$lte": now},  # datetime comparison
            "user_visible": True
        }
        
        sheets_to_hide = await db.route_sheets.count_documents(hide_query)
        logger.info(f"Sheets to hide (>hide_at): {sheets_to_hide}")
        
        if sheets_to_hide > 0 and not dry_run:
            result = await db.route_sheets.update_many(
                hide_query,
                {"$set": {"user_visible": False}}
            )
            logger.info(f"Hidden {result.modified_count} sheets")
        
        # 2. PURGE: Delete sheets past purge_at (backup to TTL)
        # TTL index should handle this, but we run it anyway as safety
        purge_query = {
            "purge_at": {"$lte": now}  # datetime comparison
        }
        
        sheets_to_purge = await db.route_sheets.count_documents(purge_query)
        logger.info(f"Sheets to purge (>purge_at): {sheets_to_purge}")
        
        if sheets_to_purge > 0 and not dry_run:
            # Log which sheets will be deleted
            sheets = await db.route_sheets.find(
                purge_query, 
                {"_id": 0, "id": 1, "user_id": 1, "year": 1, "seq_number": 1}
            ).to_list(100)
            
            for s in sheets:
                logger.info(f"Purging sheet: {s['seq_number']:03d}/{s['year']} (user: {s['user_id'][:8]}...)")
            
            result = await db.route_sheets.delete_many(purge_query)
            logger.info(f"Purged {result.deleted_count} sheets")
        
        # 3. STATS: Report current state
        total_sheets = await db.route_sheets.count_documents({})
        visible_sheets = await db.route_sheets.count_documents({"user_visible": True})
        hidden_sheets = await db.route_sheets.count_documents({"user_visible": False})
        annulled_sheets = await db.route_sheets.count_documents({"status": "ANNULLED"})
        
        logger.info(f"Stats: total={total_sheets}, visible={visible_sheets}, hidden={hidden_sheets}, annulled={annulled_sheets}")
        
        logger.info("Retention job completed successfully")
        
    except Exception as e:
        logger.error(f"Retention job failed: {e}")
        raise
    finally:
        client.close()


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    asyncio.run(run_retention_job(dry_run=dry_run))
