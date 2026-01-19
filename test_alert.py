"""
Test script with updated settings: 5% threshold, 2 days GMP
"""
import os
import requests
from datetime import datetime, timedelta

TG_BOT_TOKEN = os.getenv("TG_BOT_TOKEN")
TG_CHANNEL_ID = os.getenv("TG_CHANNEL_ID", "@IPO_GMB_Tracker")

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TG_CHANNEL_ID, "text": message, "parse_mode": "Markdown"}
    response = requests.post(url, data=payload, timeout=10)
    return response.status_code == 200

def main():
    today = datetime.today().date()
    
    # Sample IPO - KRM Ayurveda (from screenshot: 14.81% GMP)
    ipo_name = "KRM Ayurveda NSE SME"
    price = "₹135"
    subscription = "69.74x"
    start_date = "21-Jan"
    end_date = "23-Jan"
    
    # Last 2 days GMP (above 5% threshold)
    gmp_history = [
        ("18-Jan", 12.5),
        ("19-Jan", 14.81),
    ]
    avg_gmp = sum([g[1] for g in gmp_history]) / len(gmp_history)
    
    gmp_lines = "\n".join([f"  • {date}: {gmp}%" for date, gmp in gmp_history])
    
    print("=== Sending 'Closing Tomorrow' Alert (5% threshold, 2 days) ===")
    
    message1 = (
        f"🟡 *IPO ALERT - CLOSING TOMORROW*\n\n"
        f"📌 *{ipo_name}*\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"💰 Price: {price}\n"
        f"📊 Subscription: {subscription}\n"
        f"📅 Start: {start_date}\n"
        f"📅 End: {end_date}\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"📈 *GMP History (Last 2 days):*\n{gmp_lines}\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"⭐ *Average GMP: {avg_gmp:.2f}%*\n\n"
        f"⏰ *Closing Tomorrow - Apply Today!*\n\n"
        f"✅ *Recommendation: PROCEED*"
    )
    
    if send_telegram_message(message1):
        print("✅ 'Closing Tomorrow' alert sent!")
    
    import time
    time.sleep(2)
    
    print("=== Sending 'Closing Today' Alert ===")
    
    message2 = (
        f"🔴 *IPO ALERT - CLOSING TODAY*\n\n"
        f"📌 *{ipo_name}*\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"💰 Price: {price}\n"
        f"📊 Subscription: {subscription}\n"
        f"📅 Start: {start_date}\n"
        f"📅 End: {end_date}\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"📈 *GMP History (Last 2 days):*\n{gmp_lines}\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"⭐ *Average GMP: {avg_gmp:.2f}%*\n\n"
        f"🚨 *LAST CHANCE - Closing Today!*\n\n"
        f"✅ *Recommendation: PROCEED*"
    )
    
    if send_telegram_message(message2):
        print("✅ 'Closing Today' alert sent!")
    
    print("\n=== Both Test Alerts Sent! ===")
    print(f"Settings: GMP threshold = 5%, GMP days = 2")

if __name__ == "__main__":
    main()
