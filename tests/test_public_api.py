from __future__ import annotations

import nozle


def test_every_declared_public_symbol_is_importable() -> None:
    for name in nozle.__all__:
        assert getattr(nozle, name) is not None
