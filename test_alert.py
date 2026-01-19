"""
Test script to send both "Closing Tomorrow" and "Closing Today" alerts
"""
import os
import requests
from datetime import datetime, timedelta
from supabase import create_client

# Config
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://ofcngucvrrmzvihjgjvz.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
TG_BOT_TOKEN = os.getenv("TG_BOT_TOKEN")
TG_CHANNEL_ID = os.getenv("TG_CHANNEL_ID", "@IPO_GMB_Tracker")

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TG_CHANNEL_ID, "text": message, "parse_mode": "Markdown"}
    response = requests.post(url, data=payload, timeout=10)
    return response.status_code == 200

def main():
    today = datetime.today().date()
    
    # Sample IPO data
    ipo_name = "Shyam Dhani Industries NSE SME"
    price = "₹133.00"
    subscription = "988.29x"
    start_date = "22-Dec"
    end_date = "24-Dec"
    
    # GMP history for last 3 working days
    gmp_history = [
        ("17-Jan", 45.0),
        ("18-Jan", 52.5),
        ("19-Jan", 48.0),
    ]
    avg_gmp = sum([g[1] for g in gmp_history]) / len(gmp_history)
    
    gmp_lines = "\n".join([f"  • {date}: {gmp}%" for date, gmp in gmp_history])
    
    print("=== Sending 'Closing Tomorrow' Alert ===")
    
    # Message 1: Closing Tomorrow
    message1 = (
        f"🟡 *IPO ALERT - CLOSING TOMORROW*\n\n"
        f"📌 *{ipo_name}*\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"💰 Price: {price}\n"
        f"📊 Subscription: {subscription}\n"
        f"📅 Start: {start_date}\n"
        f"📅 End: {end_date}\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"📈 *GMP History (Last 3 days):*\n{gmp_lines}\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"⭐ *Average GMP: {avg_gmp:.2f}%*\n\n"
        f"⏰ *Closing Tomorrow - Apply Today!*\n\n"
        f"✅ *Recommendation: PROCEED*"
    )
    
    if send_telegram_message(message1):
        print("✅ 'Closing Tomorrow' alert sent!")
    
    import time
    time.sleep(2)  # Small delay between messages
    
    print("=== Sending 'Closing Today' Alert ===")
    
    # Message 2: Closing Today
    message2 = (
        f"🔴 *IPO ALERT - CLOSING TODAY*\n\n"
        f"📌 *{ipo_name}*\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"💰 Price: {price}\n"
        f"📊 Subscription: {subscription}\n"
        f"📅 Start: {start_date}\n"
        f"📅 End: {end_date}\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"📈 *GMP History (Last 3 days):*\n{gmp_lines}\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"⭐ *Average GMP: {avg_gmp:.2f}%*\n\n"
        f"🚨 *LAST CHANCE - Closing Today!*\n\n"
        f"✅ *Recommendation: PROCEED*"
    )
    
    if send_telegram_message(message2):
        print("✅ 'Closing Today' alert sent!")
    
    print("\n=== Both Test Alerts Sent! ===")
    print("Check your Telegram channel!")

if __name__ == "__main__":
    main()
