"""
adapters/permissions/matrix.py
────────────────────────────────
Discord permission bits → Matrix power level mapping.

Matrix power levels:
  100  Admin  — full control
   50  Mod    — kick, ban, redact, manage messages
    0  User   — send messages, read history
"""

from __future__ import annotations

ADMIN = 100
MOD   = 50
USER  = 0

_ADMIN_BITS = (
    1 << 3,   # ADMINISTRATOR
)

_MOD_BITS = (
    1 << 1,   # KICK_MEMBERS
    1 << 2,   # BAN_MEMBERS
    1 << 4,   # MANAGE_CHANNELS
    1 << 5,   # MANAGE_GUILD
    1 << 13,  # MANAGE_MESSAGES
    1 << 27,  # MANAGE_NICKNAMES
    1 << 28,  # MANAGE_ROLES
    1 << 29,  # MANAGE_WEBHOOKS
)


def map_permissions(discord_perms: int) -> int:
    """Map a Discord role permission bitfield to a Matrix power level."""
    for bit in _ADMIN_BITS:
        if discord_perms & bit:
            return ADMIN
    for bit in _MOD_BITS:
        if discord_perms & bit:
            return MOD
    return USER
