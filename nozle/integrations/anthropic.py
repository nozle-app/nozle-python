from __future__ import annotations

import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from nozle.client import Nozle


def wrap_anthropic(client, nozle: Nozle, *, customer_id: str,
                   metric_code: str = "llm_tokens", feature: str | None = None):
    original = client.messages.create

    def wrapped_create(*args, **kwargs):
        start = time.monotonic()
        result = original(*args, **kwargs)
        stream = kwargs.get("stream", False)

        if stream:
            return _wrap_stream(result, nozle, customer_id, metric_code,
                                feature, kwargs.get("model", ""), start)

        usage = getattr(result, "usage", None)
        if usage:
            props = {
                "model": getattr(result, "model", kwargs.get("model", "")),
                "input_tokens": getattr(usage, "input_tokens", 0),
                "output_tokens": getattr(usage, "output_tokens", 0),
                "latency_ms": int((time.monotonic() - start) * 1000),
            }
            if feature:
                props["feature"] = feature
            nozle.track(customer_id, metric_code, metadata=props)
        return result

    client.messages.create = wrapped_create
    return client


def _wrap_stream(stream, nozle, customer_id, metric_code, feature, model, start):
    input_tokens = 0
    output_tokens = 0

    for event in stream:
        event_type = getattr(event, "type", "")
        if event_type == "message_start":
            msg = getattr(event, "message", None)
            if msg and hasattr(msg, "usage"):
                input_tokens = getattr(msg.usage, "input_tokens", 0)
        elif event_type == "message_delta":
            usage = getattr(event, "usage", None)
            if usage:
                output_tokens = getattr(usage, "output_tokens", 0)
        yield event

    if input_tokens or output_tokens:
        props = {
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "latency_ms": int((time.monotonic() - start) * 1000),
        }
        if feature:
            props["feature"] = feature
        nozle.track(customer_id, metric_code, metadata=props)
