from __future__ import annotations

import time
from secrets import token_bytes
from uuid import UUID


def _uuid7() -> str:
    raw = bytearray(token_bytes(16))
    timestamp_ms = int(time.time_ns() // 1_000_000)
    raw[0:6] = timestamp_ms.to_bytes(6, "big")
    raw[6] = (raw[6] & 0x0F) | 0x70
    raw[8] = (raw[8] & 0x3F) | 0x80
    return str(UUID(bytes=bytes(raw)))


def create_transaction_id() -> str:
    return _uuid7()


def create_cost_event_id() -> str:
    return _uuid7()
