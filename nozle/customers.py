from __future__ import annotations

from typing import cast

from nozle._transport import HttpTransport
from nozle._validation import require_non_empty, require_secret_key
from nozle.types import CustomerUpsertResult


class CustomersNamespace:
    """Create or update customers through the backend-only API."""

    def __init__(self, transport: HttpTransport, api_key: str) -> None:
        self._transport = transport
        self._api_key = api_key

    def upsert(
        self,
        external_id: str,
        name: str | None = None,
        email: str | None = None,
    ) -> CustomerUpsertResult:
        operation = "customers.upsert"
        require_secret_key(self._api_key, operation)
        require_non_empty(external_id, "external_id", operation)
        customer = {"external_id": external_id}
        if name is not None:
            customer["name"] = name
        if email is not None:
            customer["email"] = email
        payload = self._transport.request(
            operation,
            "POST",
            "/api/v1/customers",
            json_body={"customer": customer},
        )
        return cast(CustomerUpsertResult, payload["customer"])
