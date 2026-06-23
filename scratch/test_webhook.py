import requests

SUPABASE_URL = "https://uyptbypqzfkdsvpdvwyz.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InV5cHRieXBxemZrZHN2cGR2d3l6Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODAxNTA1ODAsImV4cCI6MjA5NTcyNjU4MH0.ZEZxlWA9H0u6iP3IHn97XjqNABUEl3kqVcsecx9GPKg"

headers = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}

r = requests.get(f"{SUPABASE_URL}/rest/v1/webhook_logs?limit=1", headers=headers)
print("Keys:", r.json()[0].keys() if r.status_code == 200 and r.json() else r.text)

r2 = requests.get(f"{SUPABASE_URL}/rest/v1/webhook_logs?order=id.desc&limit=500", headers=headers)
logs = r2.json() if r2.status_code == 200 else []
if logs:
    sale_logs = [l for l in logs if l.get('event_type') == 'sale.created']
    if sale_logs:
        print("Sale payload sample keys:", sale_logs[0]['payload'].keys())
        print("Sale client info:", sale_logs[0]['payload'].get('client'))

    # search Casan/Karwacka in these logs regardless of case
    casan_logs = [l for l in logs if 'casan' in str(l.get('payload')).lower()]
    karwacka_logs = [l for l in logs if 'karwacka' in str(l.get('payload')).lower()]
    print(f"Casan in logs (by text search): {len(casan_logs)}")
    print(f"Karwacka in logs (by text search): {len(karwacka_logs)}")

# Let's search the ENTIRE DB for them using Supabase text search on JSON
r3 = requests.get(f"{SUPABASE_URL}/rest/v1/webhook_logs?payload=cs.%7B%22client%22:%7B%22lastname%22:%22Casan%22%7D%7D", headers=headers)
print("Casan full DB search:", r3.json() if r3.status_code == 200 else r3.status_code)
