from __future__ import annotations

from typing import Any, Literal, Mapping, Optional

from nozle._transport import HttpTransport
from nozle._validation import require_secret_key


class MarginClient:
    """Backend-only margin reporting namespace."""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        timeout: float = 10,
        *,
        _transport: Optional[HttpTransport] = None,
    ) -> None:
        self._api_key = api_key
        self._transport = _transport or HttpTransport(base_url, api_key, timeout)

    def summary(self, **params: Optional[str]) -> Any:
        return self._get("summary", "/summary", params)

    def by_customer(self, **params: Optional[str]) -> Any:
        return self._get("by_customer", "/customers", params)

    def by_metric(self, **params: Optional[str]) -> Any:
        return self._get("by_metric", "/metrics", params)

    def by_plan(self, **params: Optional[str]) -> Any:
        return self._get("by_plan", "/plans", params)

    def by_model(self, **params: Optional[str]) -> Any:
        return self._get("by_model", "/models", params)

    def trend(
        self,
        granularity: Literal["hour", "day", "week", "month"] = "day",
        **params: Optional[str],
    ) -> Any:
        query = {key: value for key, value in params.items() if value is not None}
        query["granularity"] = granularity
        return self._get("trend", "/trend", query)

    def close(self) -> None:
        self._transport.close()

    def _get(self, name: str, path: str, params: Mapping[str, Optional[str]]) -> Any:
        operation = f"margin.{name}"
        require_secret_key(self._api_key, operation)
        query = {key: value for key, value in params.items() if value is not None}
        return self._transport.request(
            operation,
            "GET",
            f"/api/v1/margin{path}",
            params=query,
        )
