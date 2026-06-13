"""aiogram 3.x adapter around :class:`aiogram_antiflood.core.AntiFlood`."""

from __future__ import annotations

import inspect
from typing import Any, Awaitable, Callable, Dict, Hashable, Optional

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from .core import AntiFlood, Verdict
from .storage import BaseStorage

__all__ = ["AntiFloodMiddleware", "default_key"]

KeyFunc = Callable[[TelegramObject], Optional[Hashable]]
Handler = Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]]
Callback = Callable[[TelegramObject, Dict[str, Any]], Any]


def default_key(event: TelegramObject) -> Optional[Hashable]:
    """Throttle per Telegram user id. Returns ``None`` (skip) when the update
    carries no user, so service updates are never blocked."""
    user = getattr(event, "from_user", None)
    return user.id if user is not None else None


async def _maybe_await(result: Any) -> Any:
    if inspect.isawaitable(result):
        return await result
    return result


class AntiFloodMiddleware(BaseMiddleware):
    """Drop updates from users who send messages too quickly.

    Register it on whichever observer you want to protect::

        dp.message.middleware(AntiFloodMiddleware(rate=5, per=3))

    :param rate: max events per ``per`` seconds before a user is throttled.
    :param per: sliding window length in seconds.
    :param ban_time: optional temporary ban (seconds) applied on flood.
    :param max_strikes: optional permanent ban after this many floods.
    :param key: callable mapping an event to a throttling key (or ``None`` to
        skip). Defaults to :func:`default_key` (per user id).
    :param on_flood: optional callback ``(event, data)`` run when an event is
        throttled. May be sync or async.
    :param on_ban: optional callback ``(event, data)`` run when an event is
        dropped because the key is banned. May be sync or async.
    :param storage: storage backend shared by the detector.
    :param antiflood: a pre-built :class:`AntiFlood` to reuse across several
        middlewares (overrides the rate/per/... arguments).
    """

    def __init__(
        self,
        rate: int = 5,
        per: float = 3.0,
        ban_time: float = 0.0,
        max_strikes: int = 0,
        key: KeyFunc = default_key,
        on_flood: Optional[Callback] = None,
        on_ban: Optional[Callback] = None,
        storage: Optional[BaseStorage] = None,
        antiflood: Optional[AntiFlood] = None,
    ) -> None:
        self.key_func = key
        self.on_flood = on_flood
        self.on_ban = on_ban
        self.antiflood = antiflood or AntiFlood(
            rate=rate,
            per=per,
            ban_time=ban_time,
            max_strikes=max_strikes,
            storage=storage,
        )

    async def __call__(
        self,
        handler: Handler,
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        key = self.key_func(event)
        if key is None:
            return await handler(event, data)

        verdict = await self.antiflood.check(key)
        if verdict is Verdict.OK:
            return await handler(event, data)

        if verdict is Verdict.FLOOD and self.on_flood is not None:
            await _maybe_await(self.on_flood(event, data))
        elif verdict is Verdict.BANNED and self.on_ban is not None:
            await _maybe_await(self.on_ban(event, data))
        return None
