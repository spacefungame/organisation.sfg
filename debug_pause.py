"""Test break_time - direct API call bypassing Streamlit secrets."""
import datetime
import requests
import json
import sys
sys.path.insert(0, '.')

from modules.supabase_client import activities_to_reservations, _utc_to_local

SUPABASE_URL = 'https://uyptbypqzfkdsvpdvwyz.supabase.co'
SUPABASE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InV5cHRieXBxemZrZHN2cGR2d3l6Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODAxNTA1ODAsImV4cCI6MjA5NTcyNjU4MH0.ZEZxlWA9H0u6iP3IHn97XjqNABUEl3kqVcsecx9GPKg'

target = datetime.date(2026, 6, 13)

# Fetch activities directly
r = requests.get(
    f"{SUPABASE_URL}/rest/v1/booking_activities",
    headers={
        'apikey': SUPABASE_KEY,
        'Authorization': f'Bearer {SUPABASE_KEY}',
    },
    params=[
        ('start_at', f'gte.{target.isoformat()}T00:00:00Z'),
        ('start_at', f'lt.{(target + datetime.timedelta(days=1)).isoformat()}T23:59:59Z'),
        ('order', 'order_id,pack_step.asc'),
    ],
    timeout=10,
)

acts = r.json()
print(f"Got {len(acts)} activities for {target}")

# Check table activities
for a in acts:
    label = (a.get('label', '') or '').lower()
    if 'table' in label:
        print(f"  TABLE: label={a['label']!r}, start={a.get('start_at','')[:19]}, order={a.get('order_id','')[:20]}")

# Build reservations
reservations = activities_to_reservations(acts, target, birthday_only=True)
print(f"\n{len(reservations)} reservations built:")
for r in reservations:
    print(f"  {r.client_name}: break_time='{r.break_time}' | {r.start_time}-{r.end_time} | {r.nb_persons}p")
