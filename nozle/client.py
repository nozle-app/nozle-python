from __future__ import annotations

import warnings
from typing import Mapping, Optional, Union, cast
from urllib.parse import quote

import requests

from nozle._transport import HttpTransport
from nozle._validation import (
    require_catalog_key,
    require_non_empty,
    require_secret_key,
)
from nozle.can import can as _can
from nozle.credit_systems import CreditSystemsNamespace
from nozle.credits import CreditsNamespace
from nozle.customers import CustomersNamespace
from nozle.entities import EntitiesNamespace
from nozle.errors import NozleAPIError, NozleValidationError
from nozle.margin import MarginClient
from nozle.track import track as _track
from nozle.types import (
    CancellationPolicy,
    CancelSubscriptionResult,
    CanResult,
    CheckAndDeductResult,
    CheckoutResult,
    CustomerUpsertResult,
    JSONMapping,
    PingResult,
    Plan,
    SubscribeResult,
    SubscriptionTransitionParams,
    SubscriptionTransitionPreview,
    SubscriptionTransitionResult,
)
from nozle.usage import UsageNamespace


class Nozle:
    """Synchronous backend SDK for Nozle Engine and Core APIs."""

    def __init__(
        self,
        api_key: str,
        base_url: str = "http://localhost:8080",
        events_url: str = "http://localhost:3000",
        timeout: float = 10,
        *,
        _session: Optional[requests.Session] = None,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.events_url = events_url.rstrip("/")
        self.timeout = timeout
        self._session = _session or requests.Session()
        self._owns_session = _session is None
        self._engine = HttpTransport(
            self.base_url, self.api_key, timeout=self.timeout, session=self._session
        )
        self._events = HttpTransport(
            self.events_url, self.api_key, timeout=self.timeout, session=self._session
        )
        self.margin = MarginClient(
            self.base_url, self.api_key, timeout=self.timeout, _transport=self._engine
        )
        self.customers = CustomersNamespace(self._engine, self.api_key)
        self.credit_systems = CreditSystemsNamespace(self._events, self.api_key)
        self.credits = CreditsNamespace(self._engine, self.api_key)
        self.entities = EntitiesNamespace(self._engine, self.api_key)
        self.usage = UsageNamespace(self._engine, self.api_key)
        self._sub_cache: dict[str, str] = {}

    def track(
        self,
        customer_id: str,
        event: str,
        metadata: Optional[JSONMapping] = None,
        subscription_id: Optional[str] = None,
        transaction_id: Optional[str] = None,
        timestamp: Optional[str] = None,
    ) -> None:
        require_secret_key(self.api_key, "track")
        if not subscription_id:
            subscription_id = self._resolve_subscription(customer_id)
        _track(
            self._events,
            self.api_key,
            customer_id,
            event,
            metadata,
            subscription_id,
            transaction_id,
            timestamp,
        )

    def can(
        self,
        customer_id: str,
        feature: str,
        metadata: Optional[Mapping[str, str]] = None,
    ) -> CanResult:
        return _can(self._engine, self.api_key, customer_id, feature, metadata)

    def plans(self) -> list[Plan]:
        require_catalog_key(self.api_key)
        payload = self._engine.request("plans", "GET", "/api/v1/plans")
        if not isinstance(payload, Mapping):
            raise NozleAPIError("plans", 200, "response was not a JSON object")
        plans = payload.get("plans")
        if plans is None:
            plans = []
        if not isinstance(plans, list):
            raise NozleAPIError("plans", 200, "plans was not a list")
        return cast(list[Plan], plans)

    def checkout(
        self,
        customer_id: str,
        plan_code: str,
        return_url: Optional[str] = None,
        *,
        success_url: Optional[str] = None,
    ) -> CheckoutResult:
        operation = "checkout"
        require_secret_key(self.api_key, operation)
        require_non_empty(customer_id, "customer_id", operation)
        require_non_empty(plan_code, "plan_code", operation)
        if return_url is not None and success_url is not None and return_url != success_url:
            raise NozleValidationError(
                "checkout received conflicting return_url and deprecated success_url values"
            )
        resolved_return_url = return_url if return_url is not None else success_url
        if success_url is not None:
            warnings.warn(
                "success_url is deprecated; use return_url",
                DeprecationWarning,
                stacklevel=2,
            )
        body = {"plan_code": plan_code, "customer_id": customer_id}
        if resolved_return_url:
            body["return_url"] = resolved_return_url
        return cast(
            CheckoutResult,
            self._engine.request(operation, "POST", "/api/v1/checkout", json_body=body),
        )

    def subscribe(self, customer_id: str, plan_code: str) -> SubscribeResult:
        operation = "subscribe"
        require_secret_key(self.api_key, operation)
        require_non_empty(customer_id, "customer_id", operation)
        require_non_empty(plan_code, "plan_code", operation)
        return cast(
            SubscribeResult,
            self._engine.request(
                operation,
                "POST",
                "/api/v1/subscribe",
                json_body={"plan_code": plan_code, "customer_id": customer_id},
            ),
        )

    def cancel_subscription(
        self,
        customer_id: str,
        subscription_id: str,
        policy: CancellationPolicy = "end_of_period",
    ) -> CancelSubscriptionResult:
        operation = "cancel_subscription"
        require_secret_key(self.api_key, operation)
        require_non_empty(customer_id, "customer_id", operation)
        require_non_empty(subscription_id, "subscription_id", operation)
        if policy not in ("end_of_period", "immediate"):
            raise NozleValidationError(
                "cancel_subscription policy must be 'end_of_period' or 'immediate'"
            )

        return cast(
            CancelSubscriptionResult,
            self._engine.request(
                operation,
                "DELETE",
                f"/api/v1/subscriptions/{quote(subscription_id, safe='')}",
                params={
                    "customer_id": customer_id,
                    "cancellation_policy": policy,
                },
            ),
        )

    def preview_subscription_transition(
        self,
        params: SubscriptionTransitionParams,
    ) -> SubscriptionTransitionPreview:
        operation = "preview_subscription_transition"
        body = self._subscription_transition_body(params, operation)
        return cast(
            SubscriptionTransitionPreview,
            self._engine.request(
                operation,
                "POST",
                "/api/v1/subscriptions/transitions/preview",
                json_body=body,
            ),
        )

    def apply_subscription_transition(
        self,
        params: SubscriptionTransitionParams,
        *,
        idempotency_key: str,
    ) -> SubscriptionTransitionResult:
        operation = "apply_subscription_transition"
        body = self._subscription_transition_body(params, operation)
        require_non_empty(idempotency_key, "idempotency_key", operation)
        if len(idempotency_key.encode("utf-8")) > 255:
            raise NozleValidationError(
                "apply_subscription_transition idempotency_key must not exceed 255 bytes"
            )
        return cast(
            SubscriptionTransitionResult,
            self._engine.request(
                operation,
                "POST",
                "/api/v1/subscriptions/transitions",
                json_body=body,
                headers={"Idempotency-Key": idempotency_key},
            ),
        )

    def _subscription_transition_body(
        self,
        params: SubscriptionTransitionParams,
        operation_name: str,
    ) -> JSONMapping:
        require_secret_key(self.api_key, operation_name)
        customer_id = str(params.get("customer_id", "")).strip()
        subscription_id = str(params.get("subscription_id", "")).strip()
        require_non_empty(customer_id, "customer_id", operation_name)
        require_non_empty(subscription_id, "subscription_id", operation_name)

        transition_operation = params.get("operation")
        timing = params.get("timing")
        target_plan_code = str(params.get("target_plan_code", "")).strip()
        credit_action = params.get("credit_action", "none")
        final_invoice_action = params.get("final_invoice_action", "generate")
        if transition_operation not in ("cancel", "downgrade"):
            raise NozleValidationError("operation must be 'cancel' or 'downgrade'")
        if timing not in ("end_of_period", "immediate"):
            raise NozleValidationError("timing must be 'end_of_period' or 'immediate'")
        if credit_action not in ("credit", "refund", "offset", "none"):
            raise NozleValidationError(
                "credit_action must be 'credit', 'refund', 'offset', or 'none'"
            )
        if final_invoice_action not in ("generate", "skip"):
            raise NozleValidationError("final_invoice_action must be 'generate' or 'skip'")
        if transition_operation == "cancel" and target_plan_code:
            raise NozleValidationError("target_plan_code is forbidden for cancellation")
        if transition_operation == "downgrade" and not target_plan_code:
            raise NozleValidationError("target_plan_code is required for downgrade")
        if timing == "end_of_period" and credit_action != "none":
            raise NozleValidationError("end_of_period transitions require credit_action 'none'")

        return {
            "customer_id": customer_id,
            "subscription_id": subscription_id,
            "operation": transition_operation,
            "timing": timing,
            "target_plan_code": target_plan_code or None,
            "credit_action": credit_action,
            "final_invoice_action": final_invoice_action,
        }

    def ping(self) -> PingResult:
        require_secret_key(self.api_key, "ping")
        return cast(PingResult, self._engine.request("ping", "GET", "/api/v1/ping"))

    def check_and_deduct(
        self,
        customer_id: str,
        feature: str,
        credits: Union[int, float],
    ) -> CheckAndDeductResult:
        operation = "check_and_deduct"
        require_secret_key(self.api_key, operation)
        require_non_empty(customer_id, "customer_id", operation)
        require_non_empty(feature, "feature", operation)
        return cast(
            CheckAndDeductResult,
            self._engine.request(
                operation,
                "POST",
                "/api/v1/check-and-deduct",
                json_body={
                    "customer_id": customer_id,
                    "feature": feature,
                    "credits": credits,
                },
            ),
        )

    def close(self) -> None:
        if self._owns_session:
            self._session.close()

    def __enter__(self) -> Nozle:
        return self

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
        self.close()

    def _resolve_subscription(self, customer_id: str) -> str:
        operation = "track.subscription_lookup"
        require_secret_key(self.api_key, operation)
        require_non_empty(customer_id, "customer_id", operation)
        cached = self._sub_cache.get(customer_id)
        if cached:
            return cached

        payload = self._events.request(
            operation,
            "GET",
            "/api/v1/subscriptions",
            params={"external_customer_id": customer_id, "status[]": "active"},
        )
        if not isinstance(payload, Mapping):
            raise NozleAPIError(operation, 200, "response was not a JSON object")
        subscriptions = payload.get("subscriptions")
        if subscriptions is None:
            subscriptions = []
        if not isinstance(subscriptions, list):
            raise NozleAPIError(operation, 200, "subscriptions was not a list")
        if len(subscriptions) == 0:
            raise NozleAPIError(
                operation,
                200,
                f"no active subscription for customer {customer_id!r}",
            )
        if len(subscriptions) > 1:
            raise NozleAPIError(
                operation,
                200,
                (
                    f"customer {customer_id!r} has {len(subscriptions)} active subscriptions; "
                    "specify subscription_id"
                ),
            )
        subscription = subscriptions[0]
        if not isinstance(subscription, Mapping) or not isinstance(
            subscription.get("external_id"), str
        ):
            raise NozleAPIError(operation, 200, "subscription response was incomplete")
        external_id = cast(str, subscription["external_id"])
        self._sub_cache[customer_id] = external_id
        return external_id


__all__ = ["Nozle", "CustomerUpsertResult"]
