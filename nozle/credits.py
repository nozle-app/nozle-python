from __future__ import annotations

from typing import Dict, Optional, Union, cast

from nozle._transport import HttpTransport
from nozle._validation import (
    path_segment,
    require_non_empty,
    require_secret_key,
    validate_entity_id,
    validate_idempotency_key,
    validate_page_limit,
    validate_transfer_amount,
)
from nozle.types import (
    CreditBalance,
    CreditBalances,
    CreditOperationPage,
    EntityCreditBalance,
    EntityCreditBalances,
    EntityCreditOperationPage,
    EntityCreditTransferResult,
)


class CreditsNamespace:
    """Read customer and Entity ledgers and transfer top-up credits."""

    def __init__(self, transport: HttpTransport, api_key: str) -> None:
        self._transport = transport
        self._api_key = api_key

    def get_balance(self, customer_id: str, credit_system_code: str) -> CreditBalance:
        operation = "credits.get_balance"
        require_secret_key(self._api_key, operation)
        require_non_empty(customer_id, "customer_id", operation)
        require_non_empty(credit_system_code, "credit_system_code", operation)
        return cast(
            CreditBalance,
            self._transport.request(
                operation,
                "GET",
                (
                    f"/api/v1/customers/{path_segment(customer_id)}/credit-systems/"
                    f"{path_segment(credit_system_code)}/balance"
                ),
            ),
        )

    def list_balances(self, customer_id: str) -> CreditBalances:
        operation = "credits.list_balances"
        require_secret_key(self._api_key, operation)
        require_non_empty(customer_id, "customer_id", operation)
        return cast(
            CreditBalances,
            self._transport.request(
                operation,
                "GET",
                f"/api/v1/customers/{path_segment(customer_id)}/credit-systems",
            ),
        )

    def list_operations(
        self,
        customer_id: str,
        *,
        credit_system_code: Optional[str] = None,
        limit: Optional[int] = None,
        cursor: Optional[str] = None,
    ) -> CreditOperationPage:
        operation = "credits.list_operations"
        require_secret_key(self._api_key, operation)
        require_non_empty(customer_id, "customer_id", operation)
        validate_page_limit(limit, operation)
        params: Dict[str, Union[str, int]] = {}
        if credit_system_code:
            params["credit_system_code"] = credit_system_code
        if limit is not None:
            params["limit"] = limit
        if cursor:
            params["cursor"] = cursor
        return cast(
            CreditOperationPage,
            self._transport.request(
                operation,
                "GET",
                f"/api/v1/customers/{path_segment(customer_id)}/credit-operations",
                params=params,
            ),
        )

    def get_entity_balance(
        self,
        customer_id: str,
        entity_id: str,
        credit_system_code: str,
    ) -> EntityCreditBalance:
        operation = "credits.get_entity_balance"
        require_secret_key(self._api_key, operation)
        self._validate_entity_path(customer_id, entity_id, operation)
        require_non_empty(credit_system_code, "credit_system_code", operation)
        return cast(
            EntityCreditBalance,
            self._transport.request(
                operation,
                "GET",
                (
                    f"{self._entity_credit_path(customer_id, entity_id)}/"
                    f"{path_segment(credit_system_code)}/balance"
                ),
            ),
        )

    def list_entity_balances(
        self,
        customer_id: str,
        entity_id: str,
    ) -> EntityCreditBalances:
        operation = "credits.list_entity_balances"
        require_secret_key(self._api_key, operation)
        self._validate_entity_path(customer_id, entity_id, operation)
        return cast(
            EntityCreditBalances,
            self._transport.request(
                operation,
                "GET",
                self._entity_credit_path(customer_id, entity_id),
            ),
        )

    def list_entity_operations(
        self,
        customer_id: str,
        entity_id: str,
        *,
        credit_system_code: Optional[str] = None,
        limit: Optional[int] = None,
        cursor: Optional[str] = None,
    ) -> EntityCreditOperationPage:
        operation = "credits.list_entity_operations"
        require_secret_key(self._api_key, operation)
        self._validate_entity_path(customer_id, entity_id, operation)
        validate_page_limit(limit, operation)
        params: Dict[str, Union[str, int]] = {}
        if credit_system_code:
            params["credit_system_code"] = credit_system_code
        if limit is not None:
            params["limit"] = limit
        if cursor:
            params["cursor"] = cursor
        return cast(
            EntityCreditOperationPage,
            self._transport.request(
                operation,
                "GET",
                (
                    f"/api/v1/customers/{path_segment(customer_id)}/entities/"
                    f"{path_segment(entity_id)}/credit-operations"
                ),
                params=params,
            ),
        )

    def allocate(
        self,
        customer_id: str,
        entity_id: str,
        *,
        credit_system_code: str,
        amount: str,
        idempotency_key: str,
    ) -> EntityCreditTransferResult:
        return self._transfer(
            "allocate",
            customer_id,
            entity_id,
            credit_system_code,
            amount,
            idempotency_key,
        )

    def deallocate(
        self,
        customer_id: str,
        entity_id: str,
        *,
        credit_system_code: str,
        amount: str,
        idempotency_key: str,
    ) -> EntityCreditTransferResult:
        return self._transfer(
            "deallocate",
            customer_id,
            entity_id,
            credit_system_code,
            amount,
            idempotency_key,
        )

    def _transfer(
        self,
        action: str,
        customer_id: str,
        entity_id: str,
        credit_system_code: str,
        amount: str,
        idempotency_key: str,
    ) -> EntityCreditTransferResult:
        operation = f"credits.{action}"
        require_secret_key(self._api_key, operation)
        self._validate_entity_path(customer_id, entity_id, operation)
        require_non_empty(credit_system_code, "credit_system_code", operation)
        validate_transfer_amount(amount, operation)
        validate_idempotency_key(idempotency_key, operation)
        suffix = "credit-allocations" if action == "allocate" else "credit-deallocations"
        return cast(
            EntityCreditTransferResult,
            self._transport.request(
                operation,
                "POST",
                (
                    f"/api/v1/customers/{path_segment(customer_id)}/entities/"
                    f"{path_segment(entity_id)}/{suffix}"
                ),
                json_body={"credit_system": credit_system_code, "amount": amount},
                headers={"Idempotency-Key": idempotency_key},
            ),
        )

    @staticmethod
    def _validate_entity_path(customer_id: str, entity_id: str, operation: str) -> None:
        require_non_empty(customer_id, "customer_id", operation)
        validate_entity_id(entity_id, operation)

    @staticmethod
    def _entity_credit_path(customer_id: str, entity_id: str) -> str:
        return (
            f"/api/v1/customers/{path_segment(customer_id)}/entities/"
            f"{path_segment(entity_id)}/credit-systems"
        )
