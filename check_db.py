"""
Show all database data in detail (ASCII only)
"""
import os
from supabase import create_client

SUPABASE_URL = "https://ofcngucvrrmzvihjgjvz.supabase.co"
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Get all IPOs
ipos = supabase.table('ipos').select('*').order('end_date').execute()
gmp_data = supabase.table('gmp_history').select('*').execute()

# Create GMP lookup by IPO ID
gmp_lookup = {}
for g in gmp_data.data:
    ipo_id = g['ipo_id']
    if ipo_id not in gmp_lookup:
        gmp_lookup[ipo_id] = []
    gmp_lookup[ipo_id].append(g)

print(f"\n{'='*60}")
print(f"SUPABASE DATABASE - ALL IPOs ({len(ipos.data)} total)")
print(f"{'='*60}\n")

for i, ipo in enumerate(ipos.data, 1):
    print(f"[{i}] {ipo['name']}")
    print(f"    Price: {ipo['price']}")
    print(f"    Subscription: {ipo['subscription']}")
    print(f"    Start: {ipo['start_date']} | End: {ipo['end_date']}")
    print(f"    Status: {ipo['status']}")
    
    # Show GMP history for this IPO
    ipo_gmp = gmp_lookup.get(ipo['id'], [])
    if ipo_gmp:
        print(f"    GMP History:")
        for g in sorted(ipo_gmp, key=lambda x: x['recorded_at']):
            print(f"       - {g['recorded_at']}: {g['gmp']}%")
    else:
        print(f"    GMP History: No data yet")
    
    print()

print(f"{'='*60}")
print(f"Total IPOs: {len(ipos.data)} | Total GMP Records: {len(gmp_data.data)}")
print(f"{'='*60}")
