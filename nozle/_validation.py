from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import quote

from nozle.errors import NozleAuthenticationError, NozleValidationError

_TRANSFER_AMOUNT = re.compile(r"^(?:0|[1-9]\d{0,17})(?:\.\d{1,12})?$")
_ZERO_AMOUNT = re.compile(r"^0(?:\.0+)?$")
_ENTITY_STATUSES = {"active", "suspended", "deleted"}


def require_secret_key(api_key: str, operation: str) -> None:
    if not api_key.startswith("sk_"):
        raise NozleAuthenticationError(
            f"{operation} requires a secret key (sk_); publishable keys are catalog-only"
        )


def require_catalog_key(api_key: str) -> None:
    if not (api_key.startswith("pk_") or api_key.startswith("sk_")):
        raise NozleAuthenticationError("plans requires a publishable key (pk_) or secret key (sk_)")


def require_non_empty(value: str, field: str, operation: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise NozleValidationError(f"{operation} requires {field}")
    return value


def validate_entity_id(entity_id: str, operation: str) -> None:
    require_non_empty(entity_id, "entity_id", operation)
    if len(entity_id.strip().encode("utf-8")) > 255:
        raise NozleValidationError(f"{operation} entity_id must not exceed 255 UTF-8 bytes")


def validate_idempotency_key(idempotency_key: str, operation: str) -> None:
    if not isinstance(idempotency_key, str) or not idempotency_key.strip():
        raise NozleValidationError(f"{operation} requires a non-empty idempotency_key")
    if len(idempotency_key.encode("utf-8")) > 255:
        raise NozleValidationError(f"{operation} idempotency_key must not exceed 255 UTF-8 bytes")


def validate_page_limit(limit: Optional[int], operation: str) -> None:
    if limit is None:
        return
    if type(limit) is not int or limit < 1 or limit > 100:
        raise NozleValidationError(f"{operation} limit must be an integer between 1 and 100")


def validate_entity_status(status: str, operation: str) -> None:
    if status not in _ENTITY_STATUSES:
        raise NozleValidationError(f"{operation} status must be active, suspended, or deleted")


def validate_transfer_amount(amount: str, operation: str) -> None:
    if (
        not isinstance(amount, str)
        or _TRANSFER_AMOUNT.fullmatch(amount) is None
        or _ZERO_AMOUNT.fullmatch(amount) is not None
    ):
        raise NozleValidationError(
            f"{operation} amount must be a positive decimal string with at most 12 decimals"
        )


def path_segment(value: str) -> str:
    return quote(value, safe="")


def utc_now_rfc3339_milliseconds() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
