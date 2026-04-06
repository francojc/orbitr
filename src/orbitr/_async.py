"""Async runner utility.

Typer is synchronous. Each command wraps its async implementation with
`run()` so the event loop is created and torn down per invocation.
`asyncio.gather()` is used inside async impls for concurrent multi-source
queries.
"""

from __future__ import annotations

import asyncio
from collections.abc import Coroutine
from typing import Any, TypeVar

T = TypeVar("T")


def run(coro: Coroutine[Any, Any, T]) -> T:
    """Run a coroutine to completion in a new event loop.

    Args:
        coro: Coroutine to execute.

    Returns:
        The coroutine's return value.
    """
    return asyncio.run(coro)
