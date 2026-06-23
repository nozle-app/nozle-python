import requests


def can(basera_url, api_key, customer_id, feature, metadata=None, timeout=10):
    params = {"customer_id": customer_id, "feature": feature}
    if metadata:
        import json
        params["metadata"] = json.dumps(metadata)
    resp = requests.get(
        f"{basera_url}/api/v1/can",
        headers={"Authorization": f"Bearer {api_key}"},
        params=params,
        timeout=timeout,
    )
    resp.raise_for_status()
    return resp.json()
