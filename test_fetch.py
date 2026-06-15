import datetime
from app import _fetch_reservations
from modules.supabase_client import is_configured

try:
    print(f"Supabase configured: {is_configured()}")
    # Fetch for 20th of June
    date = datetime.date(2026, 6, 20)
    reservations = _fetch_reservations(date, "supabase", "test_hash")
    print(f"Success! {len(reservations)} reservations fetched.")
except Exception as e:
    import traceback
    traceback.print_exc()
