import requests

API_KEY = "a712eb126838aeb58223d70725227d84"
BASE_URL = "https://api.qweekle.io/v1"
HEADERS = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}

# 1. Fetch orders page 1 to see metadata
r = requests.get(f"{BASE_URL}/orders?page=1&per_page=1", headers=HEADERS)
if r.status_code == 200:
    data = r.json()
    meta = data.get("meta", {})
    print("Meta page 1:", meta)
    
    total_pages = meta.get("pagination", {}).get("total_pages", 1)
    
    # 2. Fetch the LAST page of orders
    r2 = requests.get(f"{BASE_URL}/orders?page={total_pages}&per_page=100", headers=HEADERS)
    if r2.status_code == 200:
        last_page_data = r2.json().get("data", [])
        print(f"\nOrders on last page ({total_pages}): {len(last_page_data)}")
        for o in last_page_data[-5:]:  # Last 5
            print(f"  {o.get('number')} | created={o.get('created_at')} | {o.get('client_id')}")
    else:
        print("Error last page", r2.status_code)

else:
    print("Error page 1", r.status_code, r.text)
