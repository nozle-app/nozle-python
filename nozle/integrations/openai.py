from __future__ import annotations

import inspect
import time
from typing import TYPE_CHECKING, Any, AsyncIterator, Iterator, Optional

from nozle.integrations._common import (
    call_parameter,
    safe_track,
    safe_track_async,
    tracking_properties,
    value,
)

if TYPE_CHECKING:
    from nozle.client import Nozle


def wrap_openai(
    client: Any,
    nozle: Nozle,
    *,
    customer_id: str,
    metric_code: str = "llm_tokens",
    feature: Optional[str] = None,
) -> Any:
    """Wrap synchronous or asynchronous OpenAI chat completions with safe tracking."""

    original = client.chat.completions.create

    def wrapped_create(*args: Any, **kwargs: Any) -> Any:
        started = time.monotonic()
        requested_model = call_parameter(args, kwargs, "model", "")
        is_stream = bool(call_parameter(args, kwargs, "stream", False))
        result = original(*args, **kwargs)
        if inspect.isawaitable(result):
            return _await_result(
                result,
                nozle,
                customer_id,
                metric_code,
                feature,
                requested_model,
                is_stream,
                started,
            )
        if is_stream:
            if hasattr(result, "__aiter__"):
                return _wrap_async_stream(
                    result,
                    nozle,
                    customer_id,
                    metric_code,
                    feature,
                    requested_model,
                    started,
                )
            return _wrap_sync_stream(
                result,
                nozle,
                customer_id,
                metric_code,
                feature,
                requested_model,
                started,
            )
        _track_response(
            result,
            nozle,
            customer_id,
            metric_code,
            feature,
            requested_model,
            started,
        )
        return result

    client.chat.completions.create = wrapped_create
    return client


async def _await_result(
    awaitable: Any,
    nozle: Nozle,
    customer_id: str,
    metric_code: str,
    feature: Optional[str],
    requested_model: Any,
    is_stream: bool,
    started: float,
) -> Any:
    result = await awaitable
    if is_stream:
        if hasattr(result, "__aiter__"):
            return _wrap_async_stream(
                result,
                nozle,
                customer_id,
                metric_code,
                feature,
                requested_model,
                started,
            )
        return _wrap_sync_stream(
            result,
            nozle,
            customer_id,
            metric_code,
            feature,
            requested_model,
            started,
        )
    usage = value(result, "usage")
    if usage is not None:
        await safe_track_async(
            nozle,
            customer_id,
            metric_code,
            _properties(result, usage, requested_model, feature, started),
        )
    return result


def _track_response(
    result: Any,
    nozle: Nozle,
    customer_id: str,
    metric_code: str,
    feature: Optional[str],
    requested_model: Any,
    started: float,
) -> None:
    usage = value(result, "usage")
    if usage is not None:
        safe_track(
            nozle,
            customer_id,
            metric_code,
            _properties(result, usage, requested_model, feature, started),
        )


def _properties(
    result: Any,
    usage: Any,
    requested_model: Any,
    feature: Optional[str],
    started: float,
) -> dict[str, Any]:
    response_model = value(result, "model")
    return tracking_properties(
        model=requested_model if response_model is None else response_model,
        input_tokens=value(usage, "prompt_tokens", 0),
        output_tokens=value(usage, "completion_tokens", 0),
        latency_ms=int((time.monotonic() - started) * 1000),
        feature=feature,
    )


def _wrap_sync_stream(
    stream: Any,
    nozle: Nozle,
    customer_id: str,
    metric_code: str,
    feature: Optional[str],
    model: Any,
    started: float,
) -> Iterator[Any]:
    usage = None
    for chunk in stream:
        chunk_usage = value(chunk, "usage")
        if chunk_usage is not None:
            usage = chunk_usage
        yield chunk
    if usage is not None:
        safe_track(
            nozle,
            customer_id,
            metric_code,
            tracking_properties(
                model=model,
                input_tokens=value(usage, "prompt_tokens", 0),
                output_tokens=value(usage, "completion_tokens", 0),
                latency_ms=int((time.monotonic() - started) * 1000),
                feature=feature,
            ),
        )


async def _wrap_async_stream(
    stream: Any,
    nozle: Nozle,
    customer_id: str,
    metric_code: str,
    feature: Optional[str],
    model: Any,
    started: float,
) -> AsyncIterator[Any]:
    usage = None
    async for chunk in stream:
        chunk_usage = value(chunk, "usage")
        if chunk_usage is not None:
            usage = chunk_usage
        yield chunk
    if usage is not None:
        await safe_track_async(
            nozle,
            customer_id,
            metric_code,
            tracking_properties(
                model=model,
                input_tokens=value(usage, "prompt_tokens", 0),
                output_tokens=value(usage, "completion_tokens", 0),
                latency_ms=int((time.monotonic() - started) * 1000),
                feature=feature,
            ),
        )
