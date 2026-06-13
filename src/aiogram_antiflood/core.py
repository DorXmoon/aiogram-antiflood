"""Framework-agnostic sliding-window flood detector."""

from __future__ import annotations

import math
import time
from enum import Enum
from typing import Callable, Hashable, Optional

from .storage import BaseStorage, MemoryStorage

__all__ = ["AntiFlood", "Verdict"]


class Verdict(Enum):
    """Result of a single :meth:`AntiFlood.check`."""

    OK = "ok"
    """Event is within limits and should be handled normally."""

    FLOOD = "flood"
    """Event exceeded the rate limit (and triggered an optional temp ban)."""

    BANNED = "banned"
    """Key is currently banned; the event must be dropped."""


class AntiFlood:
    """Sliding-window rate limiter with optional temp/permanent bans.

    :param rate: max number of events allowed inside ``per`` seconds.
    :param per: length of the sliding window, in seconds.
    :param ban_time: when > 0, a flood puts the key on a temporary ban for this
        many seconds (further events return :attr:`Verdict.BANNED` instead of
        :attr:`Verdict.FLOOD`).
    :param max_strikes: when > 0, after this many floods the key is banned
        permanently.
    :param storage: backend to use; defaults to :class:`MemoryStorage`.
    :param clock: monotonic time source; overridable for tests.
    """

    def __init__(
        self,
        rate: int = 5,
        per: float = 3.0,
        ban_time: float = 0.0,
        max_strikes: int = 0,
        storage: Optional[BaseStorage] = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if rate < 1:
            raise ValueError("rate must be >= 1")
        if per <= 0:
            raise ValueError("per must be > 0")
        if ban_time < 0:
            raise ValueError("ban_time must be >= 0")
        if max_strikes < 0:
            raise ValueError("max_strikes must be >= 0")
        self.rate = rate
        self.per = per
        self.ban_time = ban_time
        self.max_strikes = max_strikes
        self.storage: BaseStorage = storage or MemoryStorage()
        self._clock = clock

    async def check(self, key: Hashable) -> Verdict:
        """Register an event for ``key`` and return the verdict."""
        now = self._clock()
        if await self.storage.is_banned(key, now):
            return Verdict.BANNED

        count = await self.storage.hit(key, now, self.per)
        if count <= self.rate:
            return Verdict.OK

        strikes = await self.storage.add_strike(key)
        if self.max_strikes and strikes >= self.max_strikes:
            await self.storage.ban(key, math.inf)
            return Verdict.BANNED
        if self.ban_time > 0:
            await self.storage.ban(key, now + self.ban_time)
        return Verdict.FLOOD

    async def reset(self, key: Hashable) -> None:
        """Clear all flood/ban/strike state for ``key`` (e.g. manual unban)."""
        await self.storage.reset(key)
