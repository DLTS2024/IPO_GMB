import os
import logging
import requests
from datetime import datetime, timedelta
from supabase import create_client, Client

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Config
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://ofcngucvrrmzvihjgjvz.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
TG_BOT_TOKEN = os.getenv("TG_BOT_TOKEN")
TG_CHANNEL_ID = os.getenv("TG_CHANNEL_ID")  # e.g., "@ipo_alerts_channel"

def get_supabase() -> Client:
    """Get Supabase client"""
    if not SUPABASE_KEY:
        raise ValueError("SUPABASE_KEY environment variable not set!")
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def send_telegram_message(message):
    """Send message to Telegram channel"""
    if not TG_BOT_TOKEN or not TG_CHANNEL_ID:
        logger.error("TG_BOT_TOKEN or TG_CHANNEL_ID not set!")
        return False
    
    url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TG_CHANNEL_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    
    try:
        response = requests.post(url, data=payload, timeout=10)
        if response.status_code == 200:
            logger.info("Message sent to Telegram channel successfully")
            return True
        else:
            logger.error(f"Telegram API error: {response.text}")
            return False
    except Exception as e:
        logger.error(f"Failed to send Telegram message: {e}")
        return False


def get_working_days_before(end_date, num_days=3):
    """Get the last N working days before end_date (excluding weekends)"""
    working_days = []
    current = end_date - timedelta(days=1)
    
    while len(working_days) < num_days:
        # 0=Monday, 5=Saturday, 6=Sunday
        if current.weekday() < 5:  # Monday to Friday
            working_days.append(current)
        current -= timedelta(days=1)
    
    return working_days


def check_and_send_alerts():
    """Check IPOs closing tomorrow/today and send alerts if avg GMP > 30%"""
    supabase = get_supabase()
    today = datetime.today().date()
    tomorrow = today + timedelta(days=1)
    
    logger.info(f"Checking for IPOs closing on {today} or {tomorrow}")
    
    # Get IPOs closing today or tomorrow that are still tracking
    result = supabase.table('ipos').select('*').eq('status', 'tracking').or_(
        f'end_date.eq.{today},end_date.eq.{tomorrow}'
    ).execute()
    
    if not result.data:
        logger.info("No IPOs closing today or tomorrow")
        return
    
    for ipo in result.data:
        ipo_id = ipo['id']
        ipo_name = ipo['name']
        end_date = datetime.strptime(ipo['end_date'], '%Y-%m-%d').date()
        
        logger.info(f"Processing IPO: {ipo_name} (ends {end_date})")
        
        # Get last 3 working days of GMP data
        working_days = get_working_days_before(end_date, 3)
        working_days_str = [str(d) for d in working_days]
        
        gmp_result = supabase.table('gmp_history').select('gmp, recorded_at').eq('ipo_id', ipo_id).in_('recorded_at', working_days_str).execute()
        
        if not gmp_result.data:
            logger.warning(f"No GMP history found for {ipo_name}")
            # Mark as expired since we can't calculate
            supabase.table('ipos').update({'status': 'expired'}).eq('id', ipo_id).execute()
            continue
        
        # Calculate average GMP
        gmps = [record['gmp'] for record in gmp_result.data]
        avg_gmp = sum(gmps) / len(gmps)
        
        logger.info(f"IPO: {ipo_name}, GMP values: {gmps}, Average: {avg_gmp:.2f}%")
        
        # Check threshold
        if avg_gmp > 30:
            # Prepare alert message
            closing_text = "🔴 CLOSING TODAY!" if end_date == today else "🟡 Closing Tomorrow"
            gmp_history_text = "\n".join([f"  • {r['recorded_at']}: {r['gmp']}%" for r in gmp_result.data])
            
            message = (
                f"🚀 *IPO ALERT - PROCEED*\n\n"
                f"📌 *{ipo_name}*\n"
                f"━━━━━━━━━━━━━━━━\n"
                f"💰 Price: {ipo['price']}\n"
                f"📊 Subscription: {ipo['subscription']}\n"
                f"📅 Start: {ipo['start_date']}\n"
                f"📅 End: {ipo['end_date']}\n"
                f"━━━━━━━━━━━━━━━━\n"
                f"📈 *GMP History (Last 3 days):*\n{gmp_history_text}\n"
                f"━━━━━━━━━━━━━━━━\n"
                f"⭐ *Average GMP: {avg_gmp:.2f}%*\n\n"
                f"{closing_text}\n\n"
                f"✅ *Recommendation: PROCEED*"
            )
            
            if send_telegram_message(message):
                # Mark as alerted
                supabase.table('ipos').update({'status': 'alerted'}).eq('id', ipo_id).execute()
                logger.info(f"Alert sent for {ipo_name}")
            
        else:
            logger.info(f"Skipping {ipo_name} - average GMP {avg_gmp:.2f}% is below threshold")
            # Mark as expired
            supabase.table('ipos').update({'status': 'expired'}).eq('id', ipo_id).execute()


def main():
    """Main function to check and send alerts"""
    logger.info("=== Alert Checker Started ===")
    check_and_send_alerts()
    logger.info("=== Alert Checker Finished ===")


if __name__ == "__main__":
    main()
