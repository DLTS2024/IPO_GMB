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
TG_CHANNEL_ID = os.getenv("TG_CHANNEL_ID")  # e.g., "@IPO_GMB_Tracker"

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


def get_working_days_before(end_date, num_days=2):
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
    """
    Check IPOs and send alerts:
    - Day before closing: Send 'Closing Tomorrow' alert, mark status='alerted_tomorrow'
    - On closing day: Send 'Closing Today' alert, mark status='alerted_today'
    """
    supabase = get_supabase()
    today = datetime.today().date()
    tomorrow = today + timedelta(days=1)
    
    logger.info(f"Checking for IPOs closing on {today} or {tomorrow}")
    
    # === PART 1: Send "Closing Tomorrow" alerts ===
    # Get IPOs closing tomorrow that haven't been alerted yet
    result_tomorrow = supabase.table('ipos').select('*').eq('end_date', str(tomorrow)).eq('status', 'tracking').execute()
    
    if result_tomorrow.data:
        logger.info(f"Found {len(result_tomorrow.data)} IPOs closing tomorrow")
        for ipo in result_tomorrow.data:
            process_and_alert(supabase, ipo, today, is_closing_today=False)
    
    # === PART 2: Send "Closing Today" alerts ===
    # Get IPOs closing today that were alerted yesterday (status='alerted_tomorrow')
    result_today = supabase.table('ipos').select('*').eq('end_date', str(today)).eq('status', 'alerted_tomorrow').execute()
    
    if result_today.data:
        logger.info(f"Found {len(result_today.data)} IPOs closing today")
        for ipo in result_today.data:
            process_and_alert(supabase, ipo, today, is_closing_today=True)
    
    # Also check tracking IPOs closing today (in case they weren't caught yesterday)
    result_today_new = supabase.table('ipos').select('*').eq('end_date', str(today)).eq('status', 'tracking').execute()
    
    if result_today_new.data:
        logger.info(f"Found {len(result_today_new.data)} new IPOs closing today")
        for ipo in result_today_new.data:
            process_and_alert(supabase, ipo, today, is_closing_today=True)


def process_and_alert(supabase, ipo, today, is_closing_today):
    """Process a single IPO and send alert if avg GMP > 5%"""
    ipo_id = ipo['id']
    ipo_name = ipo['name']
    end_date = datetime.strptime(ipo['end_date'], '%Y-%m-%d').date()
    
    logger.info(f"Processing IPO: {ipo_name} (ends {end_date})")
    
    # Get last 2 working days of GMP data
    working_days = get_working_days_before(end_date, 2)
    working_days_str = [str(d) for d in working_days]
    
    gmp_result = supabase.table('gmp_history').select('gmp, recorded_at').eq('ipo_id', ipo_id).in_('recorded_at', working_days_str).execute()
    
    if not gmp_result.data:
        logger.warning(f"No GMP history found for {ipo_name}")
        if is_closing_today:
            supabase.table('ipos').update({'status': 'expired'}).eq('id', ipo_id).execute()
        return
    
    # Calculate average GMP
    gmps = [record['gmp'] for record in gmp_result.data]
    avg_gmp = sum(gmps) / len(gmps)
    
    logger.info(f"IPO: {ipo_name}, GMP values: {gmps}, Average: {avg_gmp:.2f}%")
    
    # Check threshold
    if avg_gmp > 5:
        gmp_history_text = "\n".join([f"  • {r['recorded_at']}: {r['gmp']}%" for r in gmp_result.data])
        
        if is_closing_today:
            # Closing Today alert
            message = (
                f"🔴 *IPO ALERT - CLOSING TODAY*\n\n"
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
                f"🚨 *LAST CHANCE - Closing Today!*\n\n"
                f"✅ *Recommendation: PROCEED*"
            )
            new_status = 'alerted_today'
        else:
            # Closing Tomorrow alert
            message = (
                f"🟡 *IPO ALERT - CLOSING TOMORROW*\n\n"
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
                f"⏰ *Closing Tomorrow - Apply Today!*\n\n"
                f"✅ *Recommendation: PROCEED*"
            )
            new_status = 'alerted_tomorrow'
        
        if send_telegram_message(message):
            supabase.table('ipos').update({'status': new_status}).eq('id', ipo_id).execute()
            logger.info(f"Alert sent for {ipo_name} (status: {new_status})")
        
    else:
        logger.info(f"Skipping {ipo_name} - average GMP {avg_gmp:.2f}% is below threshold")
        if is_closing_today:
            supabase.table('ipos').update({'status': 'expired'}).eq('id', ipo_id).execute()


def main():
    """Main function to check and send alerts"""
    logger.info("=== Alert Checker Started ===")
    check_and_send_alerts()
    logger.info("=== Alert Checker Finished ===")


if __name__ == "__main__":
    main()
