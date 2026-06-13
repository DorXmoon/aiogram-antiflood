# aiogram-antiflood

Flood control & anti-spam **middleware for [aiogram](https://github.com/aiogram/aiogram) 3.x**.

Stop users from hammering your bot: a sliding-window rate limiter with optional
temporary and permanent bans, ready to drop into the dispatcher's middleware
chain.

[![CI](https://github.com/DorXmoon/aiogram-antiflood/actions/workflows/ci.yml/badge.svg)](https://github.com/DorXmoon/aiogram-antiflood/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/aiogram-antiflood.svg)](https://pypi.org/project/aiogram-antiflood/)
[![Python](https://img.shields.io/pypi/pyversions/aiogram-antiflood.svg)](https://pypi.org/project/aiogram-antiflood/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## Why

Every bot eventually needs throttling, and everyone re-implements the same
per-user timestamp bookkeeping. `aiogram-antiflood` packages it once:

- **Sliding window**, not fixed buckets — no burst at the bucket edge.
- **Temporary bans** — repeat offenders get a cool-down instead of being
  silently ignored forever.
- **Permanent bans after N strikes** — kill obvious spam bots.
- **Pluggable storage** — in-memory by default, implement `BaseStorage` for
  Redis when you scale horizontally.
- **No hidden state in aiogram** — the detector is a plain, fully tested class
  you can use outside aiogram too.

## Install

```bash
pip install aiogram-antiflood
```

## Quick start

```python
from aiogram import Dispatcher
from aiogram_antiflood import AntiFloodMiddleware

dp = Dispatcher()

# Allow 5 messages per 3 seconds per user; extra messages are dropped.
dp.message.middleware(AntiFloodMiddleware(rate=5, per=3))
```

### Warn the user and ban repeat offenders

```python
from aiogram.types import Message
from aiogram_antiflood import AntiFloodMiddleware

async def on_flood(event: Message, data: dict):
    await event.answer("Too fast — slow down a little. ⏳")

dp.message.middleware(
    AntiFloodMiddleware(
        rate=5,
        per=3,
        ban_time=60,      # a flood mutes the user for 60s
        max_strikes=5,    # 5 floods -> permanent ban
        on_flood=on_flood,
    )
)
```

### Custom throttling key

Throttle per chat instead of per user, for example:

```python
def per_chat(event):
    chat = getattr(event, "chat", None)
    return chat.id if chat else None

dp.message.middleware(AntiFloodMiddleware(rate=20, per=10, key=per_chat))
```

Return `None` from the key function to skip throttling for that update.

## Using the detector without aiogram

The core has no aiogram dependency:

```python
from aiogram_antiflood import AntiFlood, Verdict

flood = AntiFlood(rate=3, per=10, ban_time=30)

verdict = await flood.check(user_id)
if verdict is Verdict.OK:
    ...        # handle normally
elif verdict is Verdict.FLOOD:
    ...        # just rate-limited
elif verdict is Verdict.BANNED:
    ...        # currently banned

await flood.reset(user_id)  # manual unban
```

## Configuration

| Option        | Default | Meaning                                                        |
|---------------|---------|----------------------------------------------------------------|
| `rate`        | `5`     | Max events allowed inside `per` seconds.                        |
| `per`         | `3.0`   | Sliding-window length, in seconds.                             |
| `ban_time`    | `0`     | Seconds of temporary ban on flood (`0` = throttle only).       |
| `max_strikes` | `0`     | Permanent ban after this many floods (`0` = never).            |
| `key`         | per user| Callable mapping an event to a throttling key (or `None`).     |
| `on_flood`    | `None`  | Sync/async callback `(event, data)` on a throttled event.      |
| `on_ban`      | `None`  | Sync/async callback `(event, data)` on a banned event.         |
| `storage`     | memory  | A `BaseStorage` backend shared by the detector.                |

## Custom storage backend

Implement `BaseStorage` to share state across processes (e.g. Redis):

```python
from aiogram_antiflood import BaseStorage

class RedisStorage(BaseStorage):
    async def hit(self, key, now, window): ...
    async def is_banned(self, key, now): ...
    async def ban(self, key, until): ...
    async def add_strike(self, key): ...
    async def reset(self, key): ...
```

## Development

```bash
pip install -e ".[dev]"
pytest
```

## License

MIT © DorXmoon
