"""Storage backends for the flood detector.

A backend keeps three pieces of per-key state: the sliding window of recent
event timestamps, the current ban expiry (if any) and the accumulated strike
count. The default :class:`MemoryStorage` keeps everything in process memory;
implement :class:`BaseStorage` to back it with Redis or another shared store
when running several bot instances.
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from typing import Deque, Dict, Hashable

__all__ = ["BaseStorage", "MemoryStorage"]


class BaseStorage(ABC):
    """Interface a storage backend must implement."""

    @abstractmethod
    async def hit(self, key: Hashable, now: float, window: float) -> int:
        """Record an event for ``key`` at ``now`` and return how many events
        fall inside the trailing ``window`` seconds (this one included)."""

    @abstractmethod
    async def is_banned(self, key: Hashable, now: float) -> bool:
        """Return ``True`` while ``key`` is banned. Expired temp bans are
        cleared as a side effect."""

    @abstractmethod
    async def ban(self, key: Hashable, until: float) -> None:
        """Ban ``key`` until the ``until`` timestamp (``float('inf')`` for a
        permanent ban)."""

    @abstractmethod
    async def add_strike(self, key: Hashable) -> int:
        """Increment and return the strike counter for ``key``."""

    @abstractmethod
    async def reset(self, key: Hashable) -> None:
        """Forget all state for ``key`` (events, ban, strikes)."""


class MemoryStorage(BaseStorage):
    """In-memory backend safe for concurrent use within one event loop.

    The sliding window is a :class:`collections.deque` trimmed from the left on
    every hit, so each event costs amortised O(1) instead of rescanning a list.
    """

    def __init__(self) -> None:
        self._events: Dict[Hashable, Deque[float]] = defaultdict(deque)
        self._bans: Dict[Hashable, float] = {}
        self._strikes: Dict[Hashable, int] = defaultdict(int)
        self._lock = asyncio.Lock()

    async def hit(self, key: Hashable, now: float, window: float) -> int:
        async with self._lock:
            q = self._events[key]
            q.append(now)
            boundary = now - window
            while q and q[0] <= boundary:
                q.popleft()
            return len(q)

    async def is_banned(self, key: Hashable, now: float) -> bool:
        async with self._lock:
            until = self._bans.get(key)
            if until is None:
                return False
            if until > now:  # inf compares greater than any finite "now"
                return True
            del self._bans[key]
            return False

    async def ban(self, key: Hashable, until: float) -> None:
        async with self._lock:
            self._bans[key] = until

    async def add_strike(self, key: Hashable) -> int:
        async with self._lock:
            self._strikes[key] += 1
            return self._strikes[key]

    async def reset(self, key: Hashable) -> None:
        async with self._lock:
            self._events.pop(key, None)
            self._bans.pop(key, None)
            self._strikes.pop(key, None)
