import requests

API_KEY = "a712eb126838aeb58223d70725227d84"
BASE_URL = "https://api.qweekle.io/api"
HEADERS = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}

r = requests.get(f"{BASE_URL}/bookings?page=1&per_page=100", headers=HEADERS)
if r.status_code == 200:
    data = r.json()
    meta = data.get("meta", {})
    total_pages = meta.get("pagination", {}).get("total_pages", 1)
    print(f"Total pages: {total_pages}")
    
    r2 = requests.get(f"{BASE_URL}/bookings?page={total_pages}&per_page=100", headers=HEADERS)
    if r2.status_code == 200:
        last_page_data = r2.json().get("data", [])
        print(f"\nBookings on last page ({total_pages}): {len(last_page_data)}")
        for b in last_page_data[-5:]:
            print(f"  {b.get('id')} | start_at={b.get('start_at')} | client={b.get('client',{}).get('lastname')}")
    else:
        print("Error last page", r2.status_code)
else:
    print("Error page 1", r.status_code, r.text)
