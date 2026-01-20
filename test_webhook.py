import requests
import time

# Phone numbers list (same as in alert_sender.py)
phone_numbers = [
    "919884872483",
    "917604925112",
    "919884972483"
]

data = {
    "alert_type": "closing_tomorrow",
    "ipo_name": "KRM Ayurveda NSE SME",
    "price": "Rs.135",
    "subscription": "69.74x",
    "start_date": "21-Jan",
    "end_date": "23-Jan",
    "avg_gmp": 14.81,
    "gmp_history": [
        {"date": "18-Jan", "gmp": 12.5},
        {"date": "19-Jan", "gmp": 14.81}
    ],
    "recommendation": "PROCEED"
}

url = "https://n8n-n1cx.onrender.com/webhook/e19013f2-871d-497f-9446-733282cfbb7c"

print(f"Sending to {len(phone_numbers)} phone numbers...")

for phone in phone_numbers:
    data["phone"] = phone
    try:
        r = requests.post(url, json=data, timeout=60)
        print(f"Phone {phone}: Status {r.status_code}")
    except Exception as e:
        print(f"Phone {phone}: Error - {e}")
    time.sleep(1)

print("Done!")
