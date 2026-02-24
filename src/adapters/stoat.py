"""
adapters/stoat.py
─────────────────
Adapter for Stoat (stoat.chat) — formerly Revolt.

API base: https://api.stoat.chat
Auth:     x-bot-token header
Docs:     https://developers.stoat.chat
"""

from __future__ import annotations
import getpass
import time
import sys
import uuid
import requests

from models import Role, Category, Channel, ChannelType, ServerSnapshot
from adapters.base import BaseAdapter
from adapters.permissions.stoat import map_permissions

STOAT_API = "https://stoat.chat/api"
AUTUMN_API = "https://cdn.stoatusercontent.com"

# Stoat channel type strings
_STOAT_TEXT = "Text"
_STOAT_VOICE = "Voice"

_CHANNEL_TYPE_MAP = {
    ChannelType.TEXT: _STOAT_TEXT,
    ChannelType.VOICE: _STOAT_VOICE,
    ChannelType.ANNOUNCE: _STOAT_TEXT,  # no native equivalent → text
    ChannelType.FORUM: _STOAT_TEXT,  # no native equivalent → text
}


class StoatAdapter(BaseAdapter):
    platform_name = "Stoat"
    config_key = "stoat"

    def __init__(self):
        self.token: str = ""
        self.server_id: str = ""
        # Buffered categories: stoat_cat_id → title
        self._category_buffer: dict[str, str] = {}
        # Channel→category assignments collected during create_channel
        self._channel_categories: list[
            tuple[str, str]
        ] = []  # (stoat_cat_id, channel_id)

    # ── credentials ──────────────────────────────────────────────────────

    def load_config(self, cfg: dict) -> None:
        self.token = cfg.get("token", "")
        self.server_id = cfg.get("server_id", "")

    def prompt_credentials(self):
        if not self.token or not self.server_id:
            print("\n  Create a bot at https://stoat.chat/settings/bots")
            print(
                "  Then create a server manually, invite the bot, and paste its ID below."
            )
        if not self.token:
            self.token = getpass.getpass("  Stoat Bot Token: ").strip()
            if not self.token:
                print("  Token is required.")
                sys.exit(1)
        if not self.server_id:
            self.server_id = input("  Stoat Server ID: ").strip()
            if not self.server_id:
                print("  Server ID is required.")
                sys.exit(1)

    # ── internal HTTP helpers ─────────────────────────────────────────────

    def _headers(self) -> dict:
        return {
            "x-bot-token": self.token,
            "Content-Type": "application/json",
        }

    def _post(self, endpoint: str, payload: dict) -> dict | None:
        url = f"{STOAT_API}{endpoint}"
        for _ in range(5):
            r = requests.post(url, json=payload, headers=self._headers(), timeout=10)
            if r.status_code == 429:
                wait = r.json().get("retry_after", 1000) / 1000
                print(f"    ⏳ Stoat rate-limit – waiting {wait:.1f}s …")
                time.sleep(wait + 0.1)
                continue
            if r.status_code == 401:
                print("  ✘  Invalid Stoat bot token.")
                sys.exit(1)
            if not r.ok:
                print(f"  ✘  Stoat {r.status_code} on {endpoint}: {r.text[:200]}")
                return None
            return r.json()
        return None

    def _patch(self, endpoint: str, payload: dict) -> dict | None:
        url = f"{STOAT_API}{endpoint}"
        for _ in range(5):
            r = requests.patch(url, json=payload, headers=self._headers(), timeout=10)
            if r.status_code == 429:
                wait = r.json().get("retry_after", 1000) / 1000
                print(f"    ⏳ Stoat rate-limit – waiting {wait:.1f}s …")
                time.sleep(wait + 0.1)
                continue
            if r.status_code == 401:
                print("  ✘  Invalid Stoat bot token.")
                sys.exit(1)
            if not r.ok:
                print(f"  ✘  Stoat {r.status_code} on {endpoint}: {r.text[:200]}")
                return None
            return r.json()
        return None

    def _put(self, endpoint: str, payload: dict) -> dict | None:
        url = f"{STOAT_API}{endpoint}"
        for _ in range(5):
            r = requests.put(url, json=payload, headers=self._headers(), timeout=10)
            if r.status_code == 429:
                wait = r.json().get("retry_after", 1000) / 1000
                print(f"    ⏳ Stoat rate-limit – waiting {wait:.1f}s …")
                time.sleep(wait + 0.1)
                continue
            if r.status_code == 401:
                print("  ✘  Invalid Stoat bot token.")
                sys.exit(1)
            if not r.ok:
                print(f"  ✘  Stoat {r.status_code} on {endpoint}: {r.text[:200]}")
                return None
            return r.json()
        return None

    def _upload_icon(self, icon_url: str) -> str | None:
        """Download icon from Discord CDN and upload to Stoat's file service."""
        try:
            r = requests.get(icon_url, timeout=10)
            if not r.ok:
                print(f"  ⚠  Could not download server icon: {r.status_code}")
                return None
            content_type = r.headers.get("Content-Type", "image/png")
            ext = "gif" if "gif" in content_type else "png"
            upload = requests.post(
                f"{AUTUMN_API}/icons",
                files={"file": (f"icon.{ext}", r.content, content_type)},
                headers={"x-bot-token": self.token},
                timeout=15,
            )
            if not upload.ok:
                print(f"  ⚠  Icon upload failed: {upload.status_code} {upload.text[:100]}")
                return None
            return upload.json().get("id")
        except Exception as e:
            print(f"  ⚠  Icon upload error: {e}")
            return None

    # ── BaseAdapter interface ─────────────────────────────────────────────

    def create_server(self, snapshot: ServerSnapshot) -> str:
        patch: dict = {"name": snapshot.name}

        if snapshot.icon_url:
            print("  Uploading server icon …")
            icon_id = self._upload_icon(snapshot.icon_url)
            if icon_id:
                patch["icon"] = icon_id
                print(f"  ✔  Icon uploaded (ID: {icon_id})")

        self._patch(f"/servers/{self.server_id}", patch)
        print(f"  ✔  Server updated — name & icon applied (ID: {self.server_id})")
        return self.server_id

    def create_role(self, server_id: str, role: Role) -> str | None:
        # Step 1: create — POST only accepts name at creation time
        result = self._post(f"/servers/{server_id}/roles", {"name": role.name})
        if not result:
            return None

        role_id = result.get("id")
        if not role_id:
            print(f"    ⚠  No role ID in response: {result}")
            return None

        # Step 2: colour — must be set via PATCH after creation
        if role.color is not None:
            colour_hex = f"#{role.color:06X}"
            colour_result = self._patch(
                f"/servers/{server_id}/roles/{role_id}",
                {"colour": colour_hex},
            )
            if colour_result is not None:
                print(f"    ↳ colour {colour_hex} applied")
            else:
                print("    ↳ colour PATCH failed")

        # Step 3: permissions — set via PUT /servers/{id}/permissions/{role_id}
        stoat_perms = map_permissions(role.permissions)
        if stoat_perms:
            print(
                f"    ↳ permissions: Discord={role.permissions:#010x}  Stoat={stoat_perms:#010x}"
            )
            perm_result = self._put(
                f"/servers/{server_id}/permissions/{role_id}",
                {"permissions": {"allow": stoat_perms, "deny": 0}},
            )
            if perm_result is not None:
                print("    ↳ permissions applied")
            else:
                print("    ↳ permissions PUT failed")
        else:
            print(f"    ↳ no permissions to migrate (Discord={role.permissions})")

        return role_id

    def create_category(self, server_id: str, category: Category) -> str | None:
        # Generate a local ID now and buffer; applied in post_migration_message.
        cat_id = uuid.uuid4().hex
        self._category_buffer[cat_id] = category.name
        return cat_id

    def create_channel(
        self,
        server_id: str,
        channel: Channel,
        category_map: dict[str, str],
    ) -> str | None:
        stoat_type = _CHANNEL_TYPE_MAP.get(channel.type, _STOAT_TEXT)

        payload: dict = {
            "name": channel.name,
            "type": stoat_type,
        }
        if channel.topic:
            payload["description"] = channel.topic

        result = self._post(f"/servers/{server_id}/channels", payload)
        if not result:
            return None

        channel_id = result.get("_id")
        if channel_id and channel.category_id and channel.category_id in category_map:
            stoat_cat_id = category_map[channel.category_id]
            self._channel_categories.append((stoat_cat_id, channel_id))

        return channel_id

    def post_migration_message(self, server_id: str, snapshot: ServerSnapshot):
        # Apply categories: build the full structure and PATCH the server once.
        if self._category_buffer:
            print("\n  Applying categories to server …")
            cats: dict[str, dict] = {
                cat_id: {"id": cat_id, "title": title, "channels": []}
                for cat_id, title in self._category_buffer.items()
            }
            for stoat_cat_id, channel_id in self._channel_categories:
                if stoat_cat_id in cats:
                    cats[stoat_cat_id]["channels"].append(channel_id)

            result = self._patch(
                f"/servers/{server_id}",
                {"categories": list(cats.values())},
            )
            if result is not None:
                print(f"  ✔  {len(cats)} categories applied")
            else:
                print("  ✘  Failed to apply categories")

        print(f"\n  ℹ️  Stoat Server ID: {server_id}")
