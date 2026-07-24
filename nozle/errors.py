from __future__ import annotations

from typing import Any, Optional


class NozleError(Exception):
    """Base exception for the Nozle SDK."""


class NozleValidationError(NozleError, ValueError):
    """Raised before network I/O when a local SDK contract is invalid."""


class NozleAuthenticationError(NozleValidationError):
    """Raised when an operation is attempted with the wrong key type."""


class NozleTransportError(NozleError):
    """Raised when an HTTP request could not reach Nozle."""

    def __init__(self, operation: str) -> None:
        self.operation = operation
        super().__init__(f"{operation} request failed before receiving an HTTP response")


class NozleAPIError(NozleError):
    """Structured, credential-safe error returned by a Nozle HTTP API."""

    def __init__(
        self,
        operation: str,
        status_code: int,
        response_details: Optional[Any] = None,
    ) -> None:
        self.operation = operation
        self.status_code = status_code
        self.response_details = response_details
        detail = ""
        if response_details not in (None, "", {}):
            detail = f": {response_details!r}"
        super().__init__(f"{operation} failed with HTTP {status_code}{detail}")
