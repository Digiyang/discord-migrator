"""
discord_reader.py
─────────────────
Reads a Discord server via the Discord REST API and converts it into a
platform-neutral ServerSnapshot.

Requires a Discord bot token with at minimum:
  • View Channels
  • (Optional) Read Message History  ← only if you later add message export
"""

from __future__ import annotations
import time
import sys
import requests

from models import ServerSnapshot, Role, Category, Channel, ChannelType

DISCORD_API = "https://discord.com/api/v10"

# Discord channel type constants
_D_TEXT = 0
_D_VOICE = 2
_D_CATEGORY = 4
_D_ANNOUNCE = 5
_D_STAGE = 13
_D_FORUM = 15


def _get(endpoint: str, token: str):
    """GET from Discord API with rate-limit retry."""
    headers = {"Authorization": f"Bot {token}"}
    url = f"{DISCORD_API}{endpoint}"
    for _ in range(6):
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code == 429:
            wait = r.json().get("retry_after", 1.0)
            print(f"    ⏳ Discord rate-limit – waiting {wait:.1f}s …")
            time.sleep(float(wait) + 0.1)
            continue
        if r.status_code == 401:
            print("  ✘  Invalid Discord bot token.")
            sys.exit(1)
        if not r.ok:
            print(f"  ✘  Discord {r.status_code} on {endpoint}: {r.text[:200]}")
            return None
        return r.json()
    print(f"  ✘  Too many retries for {endpoint}")
    return None


def _discord_type_to_channel_type(dtype: int) -> ChannelType | None:
    return {
        _D_TEXT: ChannelType.TEXT,
        _D_VOICE: ChannelType.VOICE,
        _D_ANNOUNCE: ChannelType.ANNOUNCE,
        _D_FORUM: ChannelType.FORUM,
        _D_STAGE: ChannelType.VOICE,  # closest equivalent
    }.get(dtype)


class DiscordReader:
    def __init__(self, bot_token: str, guild_id: str):
        self.token = bot_token
        self.guild_id = guild_id

    def read(self) -> ServerSnapshot:
        print("\n📥  Reading Discord server …\n")

        # ── guild info ────────────────────────────────────────────────────
        guild = _get(f"/guilds/{self.guild_id}?with_counts=true", self.token)
        if not guild:
            print("  ✘  Could not fetch guild. Is the bot in the server?")
            sys.exit(1)
        has_icon = "✔" if guild.get("icon") else "✘"
        print(f"  ✔  Server: {guild['name']}  (icon: {has_icon})")

        # ── roles ─────────────────────────────────────────────────────────
        raw_roles = _get(f"/guilds/{self.guild_id}/roles", self.token) or []
        roles = [
            Role(
                id=r["id"],
                name=r["name"],
                color=r["color"] or None,
                position=r["position"],
                permissions=int(r.get("permissions", 0)),
            )
            for r in raw_roles
            if r["name"] != "@everyone"  # skip default role
        ]
        print(f"  ✔  Roles:    {len(roles)}")

        # ── channels ──────────────────────────────────────────────────────
        raw_channels = _get(f"/guilds/{self.guild_id}/channels", self.token) or []

        categories: list[Category] = []
        channels: list[Channel] = []

        for ch in raw_channels:
            dtype = ch["type"]

            if dtype == _D_CATEGORY:
                categories.append(
                    Category(
                        id=ch["id"],
                        name=ch["name"],
                        position=ch.get("position", 0),
                    )
                )
                continue

            ctype = _discord_type_to_channel_type(dtype)
            if ctype is None:
                continue  # DM, thread, etc. – skip

            channels.append(
                Channel(
                    id=ch["id"],
                    name=ch["name"],
                    type=ctype,
                    position=ch.get("position", 0),
                    topic=ch.get("topic") or None,
                    category_id=ch.get("parent_id"),
                    nsfw=ch.get("nsfw", False),
                )
            )

        categories.sort(key=lambda c: c.position)
        channels.sort(key=lambda c: c.position)

        print(f"  ✔  Categories: {len(categories)}")
        print(f"  ✔  Channels:   {len(channels)}")

        icon_url = None
        icon_hash = guild.get("icon")
        if icon_hash:
            ext = "gif" if icon_hash.startswith("a_") else "png"
            icon_url = f"https://cdn.discordapp.com/icons/{self.guild_id}/{icon_hash}.{ext}"

        return ServerSnapshot(
            name=guild["name"],
            description=guild.get("description") or None,
            icon_url=icon_url,
            roles=roles,
            categories=categories,
            channels=channels,
        )
