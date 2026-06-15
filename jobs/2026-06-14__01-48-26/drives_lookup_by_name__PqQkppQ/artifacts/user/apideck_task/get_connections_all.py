import os
import requests
import json

api_key = os.environ.get("APIDECK_API_KEY")
app_id = os.environ.get("APIDECK_APP_ID")
consumer_id = os.environ.get("APIDECK_CONSUMER_ID")

headers = {
    "Authorization": f"Bearer {api_key}",
    "x-apideck-app-id": app_id,
    "x-apideck-consumer-id": consumer_id,
    "Content-Type": "application/json"
}

# Try with no params, configured=true, configured=false
for conf in [None, 'true', 'false']:
    params = {}
    if conf:
        params['configured'] = conf
    url = "https://unify.apideck.com/vault/connections"
    print(f"Fetching connections with configured={conf}...")
    response = requests.get(url, headers=headers, params=params)
    print(f"Status Code: {response.status_code}")
    try:
        data = response.json()
        print(f"Count: {len(data.get('data', []))}")
        for conn in data.get('data', []):
            print(f"  - {conn.get('id')}: {conn.get('service_id')} ({conn.get('state')}/{conn.get('integration_state')})")
    except Exception as e:
        print("Failed to parse JSON:", e)
