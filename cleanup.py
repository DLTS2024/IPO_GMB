import os
import logging
from datetime import datetime, timedelta
from supabase import create_client, Client

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Supabase config
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://ofcngucvrrmzvihjgjvz.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

def get_supabase() -> Client:
    """Get Supabase client"""
    if not SUPABASE_KEY:
        raise ValueError("SUPABASE_KEY environment variable not set!")
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def cleanup_old_data():
    """Delete IPOs and GMP history older than 2 weeks"""
    supabase = get_supabase()
    today = datetime.today().date()
    cutoff_date = today - timedelta(weeks=2)
    
    logger.info(f"Cleaning up data older than {cutoff_date}")
    
    # Delete old IPOs (CASCADE will delete related gmp_history)
    result = supabase.table('ipos').delete().lt('end_date', str(cutoff_date)).execute()
    
    deleted_count = len(result.data) if result.data else 0
    logger.info(f"Deleted {deleted_count} old IPO records")
    
    return deleted_count


def main():
    """Main cleanup function"""
    logger.info("=== Cleanup Started ===")
    cleanup_old_data()
    logger.info("=== Cleanup Finished ===")


if __name__ == "__main__":
    main()
