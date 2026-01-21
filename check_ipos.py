"""
Check GMP history for IPOs closing tomorrow
"""
from supabase import create_client
import os
from datetime import datetime, timedelta

supabase = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_KEY'))

tomorrow = datetime.today().date() + timedelta(days=1)
print(f"Tomorrow: {tomorrow}")

# Get IPOs closing tomorrow
ipos = supabase.table('ipos').select('id, name, status').eq('end_date', str(tomorrow)).execute()
print(f"\nIPOs closing {tomorrow}: {len(ipos.data)}")

for ipo in ipos.data:
    print(f"\n  IPO: {ipo['name']}")
    print(f"  Status: {ipo['status']}")
    
    gmp = supabase.table('gmp_history').select('gmp, recorded_at').eq('ipo_id', ipo['id']).order('recorded_at', desc=True).execute()
    print(f"  GMP records: {len(gmp.data)}")
    for g in gmp.data[:5]:
        print(f"    - {g['recorded_at']}: {g['gmp']}%")
