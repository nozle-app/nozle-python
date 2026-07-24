from __future__ import annotations

from typing import Optional
from uuid import uuid4

from nozle._transport import HttpTransport
from nozle._validation import require_non_empty, require_secret_key
from nozle.types import JSONMapping


def track(
    transport: HttpTransport,
    api_key: str,
    customer_id: str,
    event: str,
    metadata: Optional[JSONMapping] = None,
    subscription_id: Optional[str] = None,
    transaction_id: Optional[str] = None,
    timestamp: Optional[str] = None,
) -> None:
    operation = "track"
    require_secret_key(api_key, operation)
    require_non_empty(customer_id, "customer_id", operation)
    require_non_empty(event, "event", operation)
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

    transport.request(
        operation,
        "POST",
        "/api/v1/events",
        json_body={"event": body},
        expect_json=False,
    )
