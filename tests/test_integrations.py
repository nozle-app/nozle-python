from __future__ import annotations

import warnings
from types import SimpleNamespace
from typing import Any, AsyncIterator
from unittest.mock import Mock

import pytest

from nozle import NozleTrackingWarning, wrap_anthropic, wrap_openai


def client_with_create(create: Any, provider: str) -> Any:
    resource = SimpleNamespace(create=create)
    if provider == "openai":
        return SimpleNamespace(chat=SimpleNamespace(completions=resource))
    return SimpleNamespace(messages=resource)


def assert_tracking_contract(
    track: Mock, model: str, input_tokens: int, output_tokens: int
) -> None:
    track.assert_called_once()
    customer_id, metric_code = track.call_args.args
    properties = track.call_args.kwargs["metadata"]
    assert customer_id == "cust_1"
    assert metric_code == "llm_tokens"
    assert properties == {
        "model": model,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "latency_ms": properties["latency_ms"],
        "feature": "assistant",
    }
    assert isinstance(properties["latency_ms"], int)
    assert properties["latency_ms"] >= 0


def test_openai_sync_response_tracks_node_event_properties() -> None:
    response = SimpleNamespace(
        model="gpt-5",
        usage=SimpleNamespace(prompt_tokens=11, completion_tokens=7),
    )
    provider = client_with_create(lambda **_: response, "openai")
    tracker = SimpleNamespace(track=Mock())
    wrap_openai(provider, tracker, customer_id="cust_1", feature="assistant")

    returned = provider.chat.completions.create(model="gpt-5")

    assert returned is response
    assert_tracking_contract(tracker.track, "gpt-5", 11, 7)


def test_openai_sync_stream_tracks_usage_from_final_chunk() -> None:
    chunks = [
        SimpleNamespace(usage=None),
        SimpleNamespace(usage=SimpleNamespace(prompt_tokens=13, completion_tokens=9)),
    ]
    provider = client_with_create(lambda **_: iter(chunks), "openai")
    tracker = SimpleNamespace(track=Mock())
    wrap_openai(provider, tracker, customer_id="cust_1", feature="assistant")

    returned = list(provider.chat.completions.create(model="gpt-stream", stream=True))

    assert returned == chunks
    assert_tracking_contract(tracker.track, "gpt-stream", 13, 9)


@pytest.mark.asyncio
async def test_openai_async_response_tracks_without_corrupting_result() -> None:
    response = SimpleNamespace(
        model=None,
        usage=SimpleNamespace(prompt_tokens=17, completion_tokens=5),
    )

    async def create(**_: Any) -> Any:
        return response

    provider = client_with_create(create, "openai")
    tracker = SimpleNamespace(track=Mock())
    wrap_openai(provider, tracker, customer_id="cust_1", feature="assistant")

    returned = await provider.chat.completions.create(model="gpt-async")

    assert returned is response
    assert_tracking_contract(tracker.track, "gpt-async", 17, 5)


@pytest.mark.asyncio
async def test_openai_async_stream_tracks_final_usage() -> None:
    chunks = [
        SimpleNamespace(usage=None),
        SimpleNamespace(usage=SimpleNamespace(prompt_tokens=19, completion_tokens=8)),
    ]

    async def stream() -> AsyncIterator[Any]:
        for chunk in chunks:
            yield chunk

    async def create(**_: Any) -> Any:
        return stream()

    provider = client_with_create(create, "openai")
    tracker = SimpleNamespace(track=Mock())
    wrap_openai(provider, tracker, customer_id="cust_1", feature="assistant")

    returned_stream = await provider.chat.completions.create(model="gpt-stream", stream=True)
    returned = [chunk async for chunk in returned_stream]

    assert returned == chunks
    assert_tracking_contract(tracker.track, "gpt-stream", 19, 8)


def test_anthropic_sync_response_tracks_node_event_properties() -> None:
    response = SimpleNamespace(
        model="claude-sonnet",
        usage=SimpleNamespace(input_tokens=23, output_tokens=12),
    )
    provider = client_with_create(lambda **_: response, "anthropic")
    tracker = SimpleNamespace(track=Mock())
    wrap_anthropic(provider, tracker, customer_id="cust_1", feature="assistant")

    returned = provider.messages.create(model="claude-sonnet")

    assert returned is response
    assert_tracking_contract(tracker.track, "claude-sonnet", 23, 12)


def test_anthropic_sync_stream_tracks_start_and_delta_usage() -> None:
    events = [
        SimpleNamespace(
            type="message_start",
            message=SimpleNamespace(usage=SimpleNamespace(input_tokens=29)),
        ),
        SimpleNamespace(type="message_delta", usage=SimpleNamespace(output_tokens=14)),
    ]
    provider = client_with_create(lambda **_: iter(events), "anthropic")
    tracker = SimpleNamespace(track=Mock())
    wrap_anthropic(provider, tracker, customer_id="cust_1", feature="assistant")

    returned = list(provider.messages.create(model="claude-stream", stream=True))

    assert returned == events
    assert_tracking_contract(tracker.track, "claude-stream", 29, 14)


@pytest.mark.asyncio
async def test_anthropic_async_response_and_stream_are_supported() -> None:
    response = SimpleNamespace(
        model="claude-async",
        usage=SimpleNamespace(input_tokens=31, output_tokens=16),
    )

    async def create_response(**_: Any) -> Any:
        return response

    response_provider = client_with_create(create_response, "anthropic")
    response_tracker = SimpleNamespace(track=Mock())
    wrap_anthropic(
        response_provider,
        response_tracker,
        customer_id="cust_1",
        feature="assistant",
    )
    returned = await response_provider.messages.create(model="claude-async")
    assert returned is response
    assert_tracking_contract(response_tracker.track, "claude-async", 31, 16)

    events = [
        {
            "type": "message_start",
            "message": {"usage": {"input_tokens": 37}},
        },
        {"type": "message_delta", "usage": {"output_tokens": 18}},
    ]

    async def stream() -> AsyncIterator[Any]:
        for event in events:
            yield event

    async def create_stream(**_: Any) -> Any:
        return stream()

    stream_provider = client_with_create(create_stream, "anthropic")
    stream_tracker = SimpleNamespace(track=Mock())
    wrap_anthropic(
        stream_provider,
        stream_tracker,
        customer_id="cust_1",
        feature="assistant",
    )
    returned_stream = await stream_provider.messages.create(model="claude-stream", stream=True)
    assert [event async for event in returned_stream] == events
    assert_tracking_contract(stream_tracker.track, "claude-stream", 37, 18)


def test_tracking_failure_warns_without_changing_successful_llm_response() -> None:
    response = SimpleNamespace(
        model="gpt-5",
        usage=SimpleNamespace(prompt_tokens=1, completion_tokens=1),
    )
    provider = client_with_create(lambda **_: response, "openai")
    tracker = SimpleNamespace(track=Mock(side_effect=RuntimeError("sk_must_not_leak")))
    wrap_openai(provider, tracker, customer_id="cust_1")

    with pytest.warns(NozleTrackingWarning) as warnings:
        returned = provider.chat.completions.create(model="gpt-5")

    assert returned is response
    assert "sk_must_not_leak" not in str(warnings[0].message)


def test_tracking_failure_cannot_replace_success_when_warnings_are_errors() -> None:
    response = SimpleNamespace(
        model="gpt-5",
        usage=SimpleNamespace(prompt_tokens=1, completion_tokens=1),
    )
    provider = client_with_create(lambda **_: response, "openai")
    tracker = SimpleNamespace(track=Mock(side_effect=RuntimeError("tracking unavailable")))
    wrap_openai(provider, tracker, customer_id="cust_1")

    with warnings.catch_warnings():
        warnings.simplefilter("error", NozleTrackingWarning)
        returned = provider.chat.completions.create(model="gpt-5")

    assert returned is response


def test_provider_failure_is_propagated_without_tracking() -> None:
    def create(**_: Any) -> Any:
        raise RuntimeError("provider unavailable")

    provider = client_with_create(create, "anthropic")
    tracker = SimpleNamespace(track=Mock())
    wrap_anthropic(provider, tracker, customer_id="cust_1")

    with pytest.raises(RuntimeError, match="provider unavailable"):
        provider.messages.create(model="claude")
    tracker.track.assert_not_called()
