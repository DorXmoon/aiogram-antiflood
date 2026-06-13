"""Flood control & anti-spam middleware for aiogram 3.x.

The package is split in two layers:

* :mod:`aiogram_antiflood.core` / :mod:`aiogram_antiflood.storage` -- a small,
  framework-agnostic sliding-window flood detector. It has no aiogram
  dependency and is fully unit-testable with a fake clock.
* :class:`aiogram_antiflood.AntiFloodMiddleware` -- a thin aiogram adapter that
  plugs the detector into the dispatcher's middleware chain.
"""

from typing import TYPE_CHECKING, Any

from .core import AntiFlood, Verdict
from .storage import BaseStorage, MemoryStorage

if TYPE_CHECKING:  # pragma: no cover - import only for type checkers
    from .middleware import AntiFloodMiddleware, default_key

__all__ = [
    "AntiFlood",
    "Verdict",
    "AntiFloodMiddleware",
    "default_key",
    "BaseStorage",
    "MemoryStorage",
]

__version__ = "0.1.0"

# ``AntiFloodMiddleware``/``default_key`` live in the only module that imports
# aiogram. Load them lazily so the framework-agnostic core stays importable
# even when aiogram is not installed.
_LAZY = {"AntiFloodMiddleware", "default_key"}


def __getattr__(name: str) -> Any:
    if name in _LAZY:
        from . import middleware

        return getattr(middleware, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
