import requests
import json

ROUTER_URL = "http://localhost:8000"

def get_trino_version():
    payload = {"sql": "SELECT node_version FROM system.runtime.nodes LIMIT 1", "force_engine": "trino"}
    try:
        response = requests.post(f"{ROUTER_URL}/query", json=payload)
        print(json.dumps(response.json(), indent=2))
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    get_trino_version()
