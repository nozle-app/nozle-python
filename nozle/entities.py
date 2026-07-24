from __future__ import annotations

from typing import Dict, List, Mapping, Optional, Sequence, Union, cast

from nozle._transport import HttpTransport
from nozle._validation import (
    path_segment,
    require_non_empty,
    require_secret_key,
    validate_entity_id,
    validate_entity_status,
    validate_idempotency_key,
    validate_page_limit,
)
from nozle.errors import NozleAPIError, NozleValidationError
from nozle.types import (
    CustomerEntity,
    CustomerEntityBulkMutationResult,
    CustomerEntityBulkUpsertItem,
    CustomerEntityMutationResult,
    CustomerEntityPage,
    CustomerEntityStatus,
    JSONMapping,
)


class EntitiesNamespace:
    """Read and idempotently manage customer Entities."""

    def __init__(self, transport: HttpTransport, api_key: str) -> None:
        self._transport = transport
        self._api_key = api_key

    def get(self, customer_id: str, entity_id: str) -> CustomerEntity:
        operation = "entities.get"
        require_secret_key(self._api_key, operation)
        self._validate_path(customer_id, entity_id, operation)
        payload = self._transport.request(
            operation,
            "GET",
            self._entity_path(customer_id, entity_id),
        )
        if not isinstance(payload, Mapping) or not isinstance(payload.get("entity"), Mapping):
            raise NozleAPIError(operation, 200, "response did not contain an entity")
        return cast(CustomerEntity, payload["entity"])

    def list(
        self,
        customer_id: str,
        *,
        status: Optional[CustomerEntityStatus] = None,
        limit: Optional[int] = None,
        cursor: Optional[str] = None,
    ) -> CustomerEntityPage:
        operation = "entities.list"
        require_secret_key(self._api_key, operation)
        require_non_empty(customer_id, "customer_id", operation)
        validate_page_limit(limit, operation)
        if status is not None:
            validate_entity_status(status, operation)
        params: Dict[str, Union[str, int]] = {}
        if status:
            params["status"] = status
        if limit is not None:
            params["limit"] = limit
        if cursor:
            params["cursor"] = cursor
        return cast(
            CustomerEntityPage,
            self._transport.request(
                operation,
                "GET",
                f"/api/v1/customers/{path_segment(customer_id)}/entities",
                params=params,
            ),
        )

    def upsert(
        self,
        customer_id: str,
        entity_id: str,
        *,
        status: CustomerEntityStatus,
        idempotency_key: str,
        name: Optional[str] = None,
        metadata: Optional[JSONMapping] = None,
    ) -> CustomerEntityMutationResult:
        operation = "entities.upsert"
        require_secret_key(self._api_key, operation)
        self._validate_path(customer_id, entity_id, operation)
        validate_entity_status(status, operation)
        validate_idempotency_key(idempotency_key, operation)
        return cast(
            CustomerEntityMutationResult,
            self._transport.request(
                operation,
                "PUT",
                self._entity_path(customer_id, entity_id),
                json_body={"name": name, "status": status, "metadata": metadata or {}},
                headers={"Idempotency-Key": idempotency_key},
            ),
        )

    def suspend(
        self,
        customer_id: str,
        entity_id: str,
        *,
        idempotency_key: str,
    ) -> CustomerEntityMutationResult:
        operation = "entities.suspend"
        require_secret_key(self._api_key, operation)
        self._validate_path(customer_id, entity_id, operation)
        validate_idempotency_key(idempotency_key, operation)
        current = self.get(customer_id, entity_id)
        return self.upsert(
            customer_id,
            entity_id,
            status="suspended",
            idempotency_key=idempotency_key,
            name=current.get("name"),
            metadata=current.get("metadata", {}),
        )

    def activate(
        self,
        customer_id: str,
        entity_id: str,
        *,
        idempotency_key: str,
    ) -> CustomerEntityMutationResult:
        operation = "entities.activate"
        require_secret_key(self._api_key, operation)
        self._validate_path(customer_id, entity_id, operation)
        validate_idempotency_key(idempotency_key, operation)
        current = self.get(customer_id, entity_id)
        return self.upsert(
            customer_id,
            entity_id,
            status="active",
            idempotency_key=idempotency_key,
            name=current.get("name"),
            metadata=current.get("metadata", {}),
        )

    def bulk_upsert(
        self,
        customer_id: str,
        entities: Sequence[CustomerEntityBulkUpsertItem],
        *,
        idempotency_key: str,
    ) -> CustomerEntityBulkMutationResult:
        operation = "entities.bulk_upsert"
        require_secret_key(self._api_key, operation)
        require_non_empty(customer_id, "customer_id", operation)
        validate_idempotency_key(idempotency_key, operation)
        if len(entities) < 1 or len(entities) > 500:
            raise NozleValidationError(f"{operation} requires between 1 and 500 entities")

        external_ids = set()
        body: List[JSONMapping] = []
        for entity in entities:
            external_id = entity.get("external_id")
            if not isinstance(external_id, str):
                raise NozleValidationError(f"{operation} requires every external_id")
            external_id = external_id.strip()
            validate_entity_id(external_id, operation)
            if external_id in external_ids:
                raise NozleValidationError(
                    f"{operation} contains duplicate external_id {external_id}"
                )
            external_ids.add(external_id)
            status = entity.get("status")
            if not isinstance(status, str):
                raise NozleValidationError(f"{operation} requires every status")
            validate_entity_status(status, operation)
            body.append(
                {
                    "external_id": external_id,
                    "name": entity.get("name"),
                    "status": status,
                    "metadata": entity.get("metadata") or {},
                }
            )

        return cast(
            CustomerEntityBulkMutationResult,
            self._transport.request(
                operation,
                "POST",
                f"/api/v1/customers/{path_segment(customer_id)}/entities/bulk-upsert",
                json_body={"entities": body},
                headers={"Idempotency-Key": idempotency_key},
            ),
        )

    @staticmethod
    def _validate_path(customer_id: str, entity_id: str, operation: str) -> None:
        require_non_empty(customer_id, "customer_id", operation)
        validate_entity_id(entity_id, operation)

    @staticmethod
    def _entity_path(customer_id: str, entity_id: str) -> str:
        return f"/api/v1/customers/{path_segment(customer_id)}/entities/{path_segment(entity_id)}"
