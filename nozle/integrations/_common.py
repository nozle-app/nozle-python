from __future__ import annotations

import asyncio
import warnings
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Mapping, Optional


class NozleTrackingWarning(RuntimeWarning):
    """A successful LLM response could not be reported to Nozle."""


@dataclass(frozen=True)
class ProviderTokenUsage:
    feature_input_tokens: int
    feature_output_tokens: int
    categories: tuple[tuple[str, int], ...]


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
    provider: str,
    model: Any,
    input_tokens: Any,
    output_tokens: Any,
    latency_ms: int,
    feature: Optional[str],
) -> Dict[str, Any]:
    properties: Dict[str, Any] = {
        "provider": provider,
        "model": model or "",
        "input_tokens": input_tokens or 0,
        "output_tokens": output_tokens or 0,
        "latency_ms": latency_ms,
    }
    if feature:
        properties["feature"] = feature
    return properties


def normalize_openai_usage(usage: Any) -> ProviderTokenUsage:
    total_input = token_count(value(usage, "prompt_tokens", value(usage, "input_tokens", 0)))
    input_details = value(
        usage,
        "prompt_tokens_details",
        value(usage, "input_tokens_details", None),
    )
    cached_input = min(total_input, token_count(value(input_details, "cached_tokens", 0)))
    total_output = token_count(value(usage, "completion_tokens", value(usage, "output_tokens", 0)))
    output_details = value(
        usage,
        "completion_tokens_details",
        value(usage, "output_tokens_details", None),
    )
    reasoning = min(total_output, token_count(value(output_details, "reasoning_tokens", 0)))

    return ProviderTokenUsage(
        feature_input_tokens=total_input,
        feature_output_tokens=total_output,
        categories=compact_categories(
            (
                ("input", total_input - cached_input),
                ("cached_input", cached_input),
                ("output", total_output - reasoning),
                ("reasoning", reasoning),
            )
        ),
    )


def normalize_anthropic_usage(usage: Any) -> ProviderTokenUsage:
    input_tokens = token_count(value(usage, "input_tokens", 0))
    cached_input = token_count(value(usage, "cache_read_input_tokens", 0))
    cache_write = token_count(value(usage, "cache_creation_input_tokens", 0))
    output_tokens = token_count(value(usage, "output_tokens", 0))

    return ProviderTokenUsage(
        feature_input_tokens=input_tokens + cached_input + cache_write,
        feature_output_tokens=output_tokens,
        categories=compact_categories(
            (
                ("input", input_tokens),
                ("cached_input", cached_input),
                ("cache_write", cache_write),
                ("output", output_tokens),
            )
        ),
    )


def safe_capture_provider_usage(
    nozle: Any,
    customer_id: str,
    feature_code: str,
    *,
    feature: Optional[str],
    cost_meter_code: Optional[str],
    provider: str,
    model: Any,
    request_id: Any,
    usage: ProviderTokenUsage,
    latency_ms: int,
) -> None:
    properties = tracking_properties(
        provider=provider,
        model=model,
        input_tokens=usage.feature_input_tokens,
        output_tokens=usage.feature_output_tokens,
        latency_ms=latency_ms,
        feature=feature,
    )
    if not cost_meter_code:
        safe_track(nozle, customer_id, feature_code, properties)
        return

    transaction_id = nozle.events.create_transaction_id()
    occurred_at = datetime.now(timezone.utc)
    try:
        nozle.track(
            customer_id,
            feature_code,
            metadata=properties,
            transaction_id=transaction_id,
            timestamp=occurred_at.isoformat(),
        )
    except Exception as error:  # tracking must not corrupt a successful provider response
        warn_tracking_failure(error)

    resolved_model = str(model or "")
    resolved_request_id = str(request_id) if request_id else None
    for token_type, tokens in usage.categories:
        try:
            nozle.cost_events.track(
                cost_meter_code=cost_meter_code,
                parent_transaction_id=transaction_id,
                request_id=resolved_request_id,
                operation_key=token_type,
                properties={
                    "tokens": tokens,
                    "provider": provider,
                    "model": resolved_model,
                    "type": token_type,
                },
                timestamp=occurred_at.timestamp(),
            )
        except Exception as error:  # tracking must not corrupt a successful provider response
            warn_tracking_failure(error)


async def safe_capture_provider_usage_async(
    nozle: Any,
    customer_id: str,
    feature_code: str,
    **kwargs: Any,
) -> None:
    await asyncio.to_thread(
        safe_capture_provider_usage,
        nozle,
        customer_id,
        feature_code,
        **kwargs,
    )


def safe_track(
    nozle: Any,
    customer_id: str,
    metric_code: str,
    properties: Dict[str, Any],
) -> None:
    try:
        nozle.track(customer_id, metric_code, metadata=properties)
    except Exception as error:  # tracking must not corrupt a successful provider response
        warn_tracking_failure(error)


async def safe_track_async(
    nozle: Any,
    customer_id: str,
    metric_code: str,
    properties: Dict[str, Any],
) -> None:
    await asyncio.to_thread(safe_track, nozle, customer_id, metric_code, properties)


def token_count(raw_value: Any) -> int:
    try:
        count = int(raw_value or 0)
    except (TypeError, ValueError, OverflowError):
        return 0
    return max(count, 0)


def compact_categories(categories: tuple[tuple[str, int], ...]) -> tuple[tuple[str, int], ...]:
    return tuple((token_type, tokens) for token_type, tokens in categories if tokens > 0)


def warn_tracking_failure(error: Exception) -> None:
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
