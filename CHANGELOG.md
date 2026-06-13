# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/) and the project adheres to
[Semantic Versioning](https://semver.org/).

## [0.1.0] - 2026-06-13

### Added
- Framework-agnostic sliding-window flood detector (`AntiFlood`) with a
  deque-backed window (amortised O(1) per event).
- Optional temporary bans (`ban_time`) and permanent bans after N floods
  (`max_strikes`).
- `AntiFloodMiddleware` for aiogram 3.x with `on_flood` / `on_ban` callbacks
  and a customisable throttling key.
- Pluggable storage backends via `BaseStorage`; in-memory default
  (`MemoryStorage`).
- Test suite with a deterministic fake clock and CI across Python 3.9–3.13.
