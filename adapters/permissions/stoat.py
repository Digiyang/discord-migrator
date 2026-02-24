"""
adapters/permissions/stoat.py
──────────────────────────────
Stoat permission bit constants and Discord → Stoat permission mapping.
"""

from __future__ import annotations

# ── Stoat permission bits ─────────────────────────────────────────────────────
MANAGE_CHANNEL = 1
MANAGE_SERVER = 2
MANAGE_PERMISSIONS = 4
MANAGE_ROLE = 8
MANAGE_CUSTOMISATION = 16
KICK_MEMBERS = 64
BAN_MEMBERS = 128
TIMEOUT_MEMBERS = 256
ASSIGN_ROLES = 512
CHANGE_NICKNAME = 1024
MANAGE_NICKNAMES = 2048
CHANGE_AVATAR = 4096
REMOVE_AVATARS = 8192
VIEW_CHANNEL = 1048576
READ_MESSAGE_HISTORY = 2097152
SEND_MESSAGE = 4194304
MANAGE_MESSAGES = 8388608
MANAGE_WEBHOOKS = 16777216
INVITE_OTHERS = 33554432
SEND_EMBEDS = 67108864
UPLOAD_FILES = 134217728
MASQUERADE = 268435456
REACT = 536870912
CONNECT = 1073741824
SPEAK = 2147483648
VIDEO = 4294967296
MUTE_MEMBERS = 8589934592
DEAFEN_MEMBERS = 17179869184
MOVE_MEMBERS = 34359738368

ALL = (
    MANAGE_CHANNEL
    | MANAGE_SERVER
    | MANAGE_PERMISSIONS
    | MANAGE_ROLE
    | MANAGE_CUSTOMISATION
    | KICK_MEMBERS
    | BAN_MEMBERS
    | TIMEOUT_MEMBERS
    | ASSIGN_ROLES
    | CHANGE_NICKNAME
    | MANAGE_NICKNAMES
    | CHANGE_AVATAR
    | REMOVE_AVATARS
    | VIEW_CHANNEL
    | READ_MESSAGE_HISTORY
    | SEND_MESSAGE
    | MANAGE_MESSAGES
    | MANAGE_WEBHOOKS
    | INVITE_OTHERS
    | SEND_EMBEDS
    | UPLOAD_FILES
    | MASQUERADE
    | REACT
    | CONNECT
    | SPEAK
    | VIDEO
    | MUTE_MEMBERS
    | DEAFEN_MEMBERS
    | MOVE_MEMBERS
)

# Discord permission bit → Stoat permission bit(s)
_PERM_MAP = [
    (1 << 0,  INVITE_OTHERS),               # CREATE_INSTANT_INVITE
    (1 << 1,  KICK_MEMBERS),                # KICK_MEMBERS
    (1 << 2,  BAN_MEMBERS),                 # BAN_MEMBERS
    (1 << 3,  ALL),                         # ADMINISTRATOR → all
    (1 << 4,  MANAGE_CHANNEL),              # MANAGE_CHANNELS
    (1 << 5,  MANAGE_SERVER),               # MANAGE_GUILD
    (1 << 6,  REACT),                       # ADD_REACTIONS
    (1 << 10, VIEW_CHANNEL),                # VIEW_CHANNEL
    (1 << 11, SEND_MESSAGE),                # SEND_MESSAGES
    (1 << 13, MANAGE_MESSAGES),             # MANAGE_MESSAGES
    (1 << 14, SEND_EMBEDS),                 # EMBED_LINKS
    (1 << 15, UPLOAD_FILES),                # ATTACH_FILES
    (1 << 16, READ_MESSAGE_HISTORY),        # READ_MESSAGE_HISTORY
    (1 << 20, CONNECT),                     # CONNECT
    (1 << 21, SPEAK),                       # SPEAK
    (1 << 22, MUTE_MEMBERS),                # MUTE_MEMBERS
    (1 << 23, DEAFEN_MEMBERS),              # DEAFEN_MEMBERS
    (1 << 24, MOVE_MEMBERS),                # MOVE_MEMBERS
    (1 << 26, CHANGE_NICKNAME),             # CHANGE_NICKNAME
    (1 << 27, MANAGE_NICKNAMES),            # MANAGE_NICKNAMES
    (1 << 28, MANAGE_ROLE | ASSIGN_ROLES),  # MANAGE_ROLES
    (1 << 29, MANAGE_WEBHOOKS),             # MANAGE_WEBHOOKS
    (1 << 30, MANAGE_CUSTOMISATION),        # MANAGE_GUILD_EXPRESSIONS
]


def map_permissions(discord_perms: int) -> int:
    """Map a Discord role permission bitfield to its Stoat equivalent."""
    stoat_perms = 0
    for discord_bit, stoat_bits in _PERM_MAP:
        if discord_perms & discord_bit:
            stoat_perms |= stoat_bits
    return stoat_perms
