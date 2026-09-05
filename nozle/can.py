from __future__ import annotations

import json
from typing import Any, Mapping, Optional, cast

from nozle._transport import HttpTransport
from nozle._validation import require_non_empty, require_secret_key
from nozle.types import CanResult


def can(
    transport: HttpTransport,
    api_key: str,
    customer_id: str,
    feature: str,
    metadata: Optional[Mapping[str, Any]] = None,
) -> CanResult:
    operation = "can"
    require_secret_key(api_key, operation)
    require_non_empty(customer_id, "customer_id", operation)
    require_non_empty(feature, "feature", operation)
    params = {"customer_id": customer_id, "feature": feature}
    if metadata:
        params["metadata"] = json.dumps(metadata)
    return cast(
        CanResult,
        transport.request(
            operation,
            "GET",
            "/api/v1/can",
            params=params,
        ),
    )
