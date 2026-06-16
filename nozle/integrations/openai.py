from __future__ import annotations

import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from nozle.client import Nozle


def wrap_openai(client, nozle: Nozle, *, customer_id: str,
                metric_code: str = "llm_tokens", feature: str | None = None):
    original = client.chat.completions.create

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
                "input_tokens": getattr(usage, "prompt_tokens", 0),
                "output_tokens": getattr(usage, "completion_tokens", 0),
                "latency_ms": int((time.monotonic() - start) * 1000),
            }
            if feature:
                props["feature"] = feature
            nozle.track(customer_id, metric_code, metadata=props)
        return result

    client.chat.completions.create = wrapped_create
    return client


def _wrap_stream(stream, nozle, customer_id, metric_code, feature, model, start):
    usage = None
    for chunk in stream:
        if hasattr(chunk, "usage") and chunk.usage is not None:
            usage = chunk.usage
        yield chunk

    if usage:
        props = {
            "model": model,
            "input_tokens": getattr(usage, "prompt_tokens", 0),
            "output_tokens": getattr(usage, "completion_tokens", 0),
            "latency_ms": int((time.monotonic() - start) * 1000),
        }
        if feature:
            props["feature"] = feature
        nozle.track(customer_id, metric_code, metadata=props)
