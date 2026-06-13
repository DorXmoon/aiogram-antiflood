import asyncio
from types import SimpleNamespace

import pytest

# The middleware imports aiogram; skip the whole module if it isn't installed
# (the core is tested separately and needs no aiogram).
pytest.importorskip("aiogram")

from aiogram_antiflood import AntiFloodMiddleware  # noqa: E402


def event(user_id):
    return SimpleNamespace(from_user=SimpleNamespace(id=user_id))


def run(coro):
    return asyncio.run(coro)


def test_passes_through_under_limit():
    calls = []

    async def handler(ev, data):
        calls.append(ev)
        return "handled"

    mw = AntiFloodMiddleware(rate=2, per=100)

    async def scenario():
        return [await mw(handler, event(1), {}) for _ in range(2)]

    results = run(scenario())
    assert results == ["handled", "handled"]
    assert len(calls) == 2


def test_drops_flooding_update_and_fires_callback():
    handled = []
    flooded = []

    async def handler(ev, data):
        handled.append(ev)
        return "handled"

    def on_flood(ev, data):
        flooded.append(ev)

    mw = AntiFloodMiddleware(rate=1, per=100, on_flood=on_flood)

    async def scenario():
        await mw(handler, event(1), {})        # handled
        return await mw(handler, event(1), {})  # dropped

    dropped = run(scenario())
    assert dropped is None
    assert len(handled) == 1
    assert len(flooded) == 1


def test_updates_without_user_are_never_blocked():
    handled = []

    async def handler(ev, data):
        handled.append(ev)
        return "handled"

    mw = AntiFloodMiddleware(rate=1, per=100)
    no_user = SimpleNamespace(from_user=None)

    async def scenario():
        for _ in range(5):
            await mw(handler, no_user, {})

    run(scenario())
    assert len(handled) == 5
