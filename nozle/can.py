import requests


def can(basera_url, api_key, customer_id, feature):
    resp = requests.get(
        f"{basera_url}/v1/can",
        headers={"Authorization": f"Bearer {api_key}"},
        params={"customer_id": customer_id, "feature": feature},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()
