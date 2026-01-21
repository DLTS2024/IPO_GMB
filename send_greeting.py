"""
Send greeting message to Telegram channel
"""
import os
import requests

TG_BOT_TOKEN = os.getenv("TG_BOT_TOKEN")
TG_CHANNEL_ID = os.getenv("TG_CHANNEL_ID", "@IPO_GMB_Tracker")

if not TG_BOT_TOKEN:
    print("❌ Error: TG_BOT_TOKEN environment variable not set!")
    exit(1)

message = """
🎉 *Welcome to IPO GMB Tracker!*

We will provide best IPO listings for you.

📊 *What you'll get:*
• Daily IPO alerts with GMP data
• "Closing Tomorrow" reminders
• "Closing Today" final alerts
• Average GMP from last 2 days

Stay tuned for daily alerts! 🚀

✅ *Subscribe and never miss a high-potential IPO!*
"""

url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage"
payload = {
    "chat_id": TG_CHANNEL_ID,
    "text": message,
    "parse_mode": "Markdown"
}

try:
    response = requests.post(url, data=payload, timeout=10)
    if response.status_code == 200:
        print("✅ Greeting sent to Telegram channel!")
    else:
        print(f"❌ Error: {response.text}")
except Exception as e:
    print(f"❌ Failed: {e}")
