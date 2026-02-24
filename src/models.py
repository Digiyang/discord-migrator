"""
models.py
─────────
Platform-neutral data models.

A Discord server (or any source) is first converted into a ServerSnapshot.
Adapters then consume the snapshot to recreate the structure on their platform.
Nothing in here is Discord- or Stoat-specific.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum


class ChannelType(Enum):
    TEXT = "text"
    VOICE = "voice"
    CATEGORY = "category"
    FORUM = "forum"  # best-effort; adapters may fall back to text
    ANNOUNCE = "announce"  # best-effort; adapters may fall back to text


@dataclass
class Role:
    id: str  # original platform ID (for cross-referencing)
    name: str
    color: int | None  # 0xRRGGBB integer, or None
    position: int = 0  # lower = lower in hierarchy
    permissions: int = 0  # platform-neutral permission bitfield (Discord's)


@dataclass
class Channel:
    id: str
    name: str
    type: ChannelType
    position: int = 0
    topic: str | None = None  # description / topic text
    category_id: str | None = None  # refers to a Category.id in the same snapshot
    nsfw: bool = False


@dataclass
class Category:
    id: str
    name: str
    position: int = 0


@dataclass
class ServerSnapshot:
    """
    A complete, platform-neutral description of a server's structure.
    Produced by a reader (e.g. DiscordReader) and consumed by an adapter.
    """

    name: str
    description: str | None
    icon_url: str | None = None

    roles: list[Role] = field(default_factory=list)
    categories: list[Category] = field(default_factory=list)
    channels: list[Channel] = field(default_factory=list)

    def summary(self) -> str:
        return (
            f"'{self.name}' — "
            f"{len(self.roles)} roles, "
            f"{len(self.categories)} categories, "
            f"{len(self.channels)} channels"
        )
