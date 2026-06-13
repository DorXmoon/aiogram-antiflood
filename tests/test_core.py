import asyncio

import pytest

from aiogram_antiflood import AntiFlood, Verdict


class FakeClock:
    """Deterministic monotonic clock for tests."""

    def __init__(self) -> None:
        self.t = 0.0

    def __call__(self) -> float:
        return self.t

    def advance(self, seconds: float) -> None:
        self.t += seconds


def run(coro):
    return asyncio.run(coro)


def test_allows_events_under_the_limit():
    af = AntiFlood(rate=3, per=10, clock=FakeClock())

    async def scenario():
        return [await af.check("u") for _ in range(3)]

    assert run(scenario()) == [Verdict.OK, Verdict.OK, Verdict.OK]


def test_flags_flood_when_limit_exceeded():
    af = AntiFlood(rate=3, per=10, clock=FakeClock())

    async def scenario():
        for _ in range(3):
            await af.check("u")
        return await af.check("u")

    assert run(scenario()) is Verdict.FLOOD


def test_window_slides_and_resets():
    clock = FakeClock()
    af = AntiFlood(rate=2, per=10, clock=clock)

    async def scenario():
        await af.check("u")
        await af.check("u")
        flooded = await af.check("u")  # 3rd inside window
        clock.advance(11)  # old events fall out of the window
        recovered = await af.check("u")
        return flooded, recovered

    flooded, recovered = run(scenario())
    assert flooded is Verdict.FLOOD
    assert recovered is Verdict.OK


def test_temp_ban_blocks_then_expires():
    clock = FakeClock()
    af = AntiFlood(rate=1, per=10, ban_time=60, clock=clock)

    async def scenario():
        await af.check("u")            # ok
        first = await af.check("u")    # flood -> temp ban for 60s
        banned = await af.check("u")   # within ban window
        clock.advance(61)
        freed = await af.check("u")    # ban expired
        return first, banned, freed

    first, banned, freed = run(scenario())
    assert first is Verdict.FLOOD
    assert banned is Verdict.BANNED
    assert freed is Verdict.OK


def test_max_strikes_leads_to_permanent_ban():
    clock = FakeClock()
    af = AntiFlood(rate=1, per=10, max_strikes=2, clock=clock)

    async def scenario():
        await af.check("u")          # ok
        s1 = await af.check("u")     # flood, strike 1
        s2 = await af.check("u")     # flood, strike 2 -> permaban
        clock.advance(10_000)        # time cannot heal a permaban
        later = await af.check("u")
        return s1, s2, later

    s1, s2, later = run(scenario())
    assert s1 is Verdict.FLOOD
    assert s2 is Verdict.BANNED
    assert later is Verdict.BANNED


def test_reset_clears_state():
    af = AntiFlood(rate=1, per=10, max_strikes=2, clock=FakeClock())

    async def scenario():
        await af.check("u")
        await af.check("u")          # strike 1
        banned = await af.check("u")  # strike 2 -> permaban
        await af.reset("u")
        return banned, await af.check("u")

    banned, after_reset = run(scenario())
    assert banned is Verdict.BANNED
    assert after_reset is Verdict.OK


def test_keys_are_independent():
    af = AntiFlood(rate=1, per=10, clock=FakeClock())

    async def scenario():
        await af.check("a")
        a_flood = await af.check("a")
        b_ok = await af.check("b")
        return a_flood, b_ok

    a_flood, b_ok = run(scenario())
    assert a_flood is Verdict.FLOOD
    assert b_ok is Verdict.OK


@pytest.mark.parametrize(
    "kwargs",
    [
        {"rate": 0},
        {"per": 0},
        {"ban_time": -1},
        {"max_strikes": -1},
    ],
)
def test_invalid_config_rejected(kwargs):
    with pytest.raises(ValueError):
        AntiFlood(**kwargs)
