from __future__ import annotations

import asyncio
from collections.abc import Awaitable


def run_background(coro: Awaitable[None]) -> None:
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return
    loop.create_task(coro)

