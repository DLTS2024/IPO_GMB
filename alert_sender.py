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
N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL", "https://n8n-n1cx.onrender.com/webhook/e19013f2-871d-497f-9446-733282cfbb7c")

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


def send_n8n_webhook(ipo_data, alert_type):
    """Send IPO alert data to N8N webhook for WhatsApp - to multiple numbers"""
    if not N8N_WEBHOOK_URL:
        logger.warning("N8N_WEBHOOK_URL not set, skipping webhook")
        return False
    
    # Phone numbers to send alerts to
    phone_numbers = [
        "919884872483",
        "917604925112",
        "919884972483"  # Add more numbers here
        # "917604925112",
        # "919884972483",
    ]
    
    success_count = 0
    for phone in phone_numbers:
        payload = {
            "alert_type": alert_type,  # "closing_tomorrow" or "closing_today"
            "phone": phone,  # Phone number for this message
            "ipo_name": ipo_data.get("name"),
            "price": ipo_data.get("price"),
            "subscription": ipo_data.get("subscription"),
            "start_date": ipo_data.get("start_date"),
            "end_date": ipo_data.get("end_date"),
            "avg_gmp": ipo_data.get("avg_gmp"),
            "gmp_history": ipo_data.get("gmp_history"),
            "recommendation": "PROCEED"
        }
        
        try:
            response = requests.post(N8N_WEBHOOK_URL, json=payload, timeout=15)
            if response.status_code == 200:
                logger.info(f"Webhook sent to N8N for phone {phone}")
                success_count += 1
            else:
                logger.error(f"N8N webhook error for {phone}: {response.status_code}")
        except Exception as e:
            logger.error(f"Failed to send webhook for {phone}: {e}")
    
    logger.info(f"Sent {success_count}/{len(phone_numbers)} webhooks successfully")
    return success_count > 0


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
    """Process a single IPO and send alert if avg GMP >= 0%"""
    ipo_id = ipo['id']
    ipo_name = ipo['name']
    end_date = datetime.strptime(ipo['end_date'], '%Y-%m-%d').date()
    
    logger.info(f"Processing IPO: {ipo_name} (ends {end_date})")
    
    # Get last 4 GMP records (2 days x 2 collections per day)
    # Order by recorded_at descending to get most recent first
    gmp_result = supabase.table('gmp_history').select('gmp, recorded_at').eq('ipo_id', ipo_id).order('recorded_at', desc=True).limit(4).execute()
    
    if not gmp_result.data:
        logger.warning(f"No GMP history found for {ipo_name}")
        if is_closing_today:
            supabase.table('ipos').update({'status': 'expired'}).eq('id', ipo_id).execute()
        return
    
    # Require minimum 2 GMP records to calculate average
    if len(gmp_result.data) < 2:
        logger.warning(f"Insufficient GMP data for {ipo_name} (need 2, have {len(gmp_result.data)})")
        return
    
    # Calculate average GMP from available records
    gmps = [record['gmp'] for record in gmp_result.data]
    avg_gmp = sum(gmps) / len(gmps)
    
    logger.info(f"IPO: {ipo_name}, GMP values: {gmps}, Average: {avg_gmp:.2f}% (from {len(gmps)} records)")
    
    # Check threshold
    if avg_gmp >= 0:
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
        
        # Send to Telegram
        if send_telegram_message(message):
            logger.info(f"Telegram alert sent for {ipo_name}")
        
        # Send to N8N webhook (for WhatsApp) - DISABLED FOR NOW
        # ipo_data = {
        #     "name": ipo_name,
        #     "price": ipo['price'],
        #     "subscription": ipo['subscription'],
        #     "start_date": ipo['start_date'],
        #     "end_date": ipo['end_date'],
        #     "avg_gmp": round(avg_gmp, 2),
        #     "gmp_history": [{"date": r['recorded_at'], "gmp": r['gmp']} for r in gmp_result.data]
        # }
        # alert_type = "closing_today" if is_closing_today else "closing_tomorrow"
        # send_n8n_webhook(ipo_data, alert_type)
        
        # Update status
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
