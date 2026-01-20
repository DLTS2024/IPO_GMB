import requests

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

url = "https://n8n-n1cx.onrender.com/webhook-test/e19013f2-871d-497f-9446-733282cfbb7c"

try:
    r = requests.post(url, json=data, timeout=15)
    print(f"Status: {r.status_code}")
    print(f"Response: {r.text}")
except Exception as e:
    print(f"Error: {e}")
