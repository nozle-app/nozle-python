from uuid import uuid4

import requests


def track(lago_url, api_key, customer_id, event, metadata=None,
          subscription_id=None, transaction_id=None, timestamp=None):
    body = {
        "transaction_id": transaction_id or str(uuid4()),
        "external_customer_id": customer_id,
        "code": event,
        "properties": metadata or {},
    }

    if subscription_id:
        body["external_subscription_id"] = subscription_id

    if timestamp:
        body["timestamp"] = timestamp

    requests.post(
        f"{lago_url}/api/v1/events",
        headers={"Authorization": f"Bearer {api_key}"},
        json={"event": body},
        timeout=10,
    )
