from __future__ import annotations

import asyncio
import warnings
from typing import Any, Dict, Mapping, Optional


class NozleTrackingWarning(RuntimeWarning):
    """A successful LLM response could not be reported to Nozle."""


def value(source: Any, name: str, default: Any = None) -> Any:
    if isinstance(source, Mapping):
        return source.get(name, default)
    return getattr(source, name, default)


def call_parameter(args: tuple[Any, ...], kwargs: Dict[str, Any], name: str, default: Any) -> Any:
    if name in kwargs:
        return kwargs[name]
    if args and isinstance(args[0], Mapping):
        return args[0].get(name, default)
    return default


def tracking_properties(
    *,
    model: Any,
    input_tokens: Any,
    output_tokens: Any,
    latency_ms: int,
    feature: Optional[str],
) -> Dict[str, Any]:
    properties: Dict[str, Any] = {
        "model": model or "",
        "input_tokens": input_tokens or 0,
        "output_tokens": output_tokens or 0,
        "latency_ms": latency_ms,
    }
    if feature:
        properties["feature"] = feature
    return properties


def safe_track(
    nozle: Any,
    customer_id: str,
    metric_code: str,
    properties: Dict[str, Any],
) -> None:
    try:
        nozle.track(customer_id, metric_code, metadata=properties)
    except Exception as error:  # tracking must not corrupt a successful provider response
        try:
            warnings.warn(
                (f"Nozle tracking failed after a successful LLM response ({type(error).__name__})"),
                NozleTrackingWarning,
                stacklevel=3,
            )
        except NozleTrackingWarning:
            # Warning filters may promote warnings to exceptions; tracking still
            # must not replace a successful provider response.
            pass


async def safe_track_async(
    nozle: Any,
    customer_id: str,
    metric_code: str,
    properties: Dict[str, Any],
) -> None:
    await asyncio.to_thread(safe_track, nozle, customer_id, metric_code, properties)
