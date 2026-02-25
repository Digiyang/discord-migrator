"""
adapters/matrix.py
──────────────────
Adapter for Matrix (matrix.org / Element).

Matrix model mapping:
  Discord server   → Matrix Space      (m.space)
  Discord category → Sub-Space         (m.space, nested)
  Discord channel  → Room              (private_chat preset)
  Discord role     → Power level tier  (100 Admin / 50 Mod / 0 User)
                     Buffered and reported at the end — must be assigned
                     to users manually in Element after migration.

API:   /_matrix/client/v3/…
Auth:  Bearer access_token

To get your access token in Element:
  Settings → Help & About → Advanced → Access Token
"""

from __future__ import annotations
import getpass
import math
import time
import sys
import requests
from urllib.parse import urlparse

from models import Role, Category, Channel, ChannelType, ServerSnapshot
from adapters.base import BaseAdapter
from adapters.permissions.matrix import map_permissions, ADMIN, MOD, USER


class MatrixAdapter(BaseAdapter):
    platform_name = "Matrix / Element"
    config_key = "matrix"

    def __init__(self):
        self.homeserver: str = ""
        self.token: str = ""
        self._mxid: str = ""
        # Buffered role info: list of (role_name, power_level)
        self._role_levels: list[tuple[str, int]] = []

    # ── credentials ──────────────────────────────────────────────────────

    def load_config(self, cfg: dict) -> None:
        self.homeserver = cfg.get("homeserver", "").rstrip("/")
        self.token = cfg.get("token", "")

    def prompt_credentials(self):
        if not self.homeserver or not self.token:
            print("\n  You need a Matrix access token.")
            print("  In Element: Settings → Help & About → Advanced → Access Token")
        if not self.homeserver:
            self.homeserver = (
                input("  Homeserver URL (e.g. https://matrix.org): ").strip().rstrip("/")
            )
            if not self.homeserver:
                print("  Homeserver URL is required.")
                sys.exit(1)
        if not self.token:
            self.token = getpass.getpass("  Access Token: ").strip()
            if not self.token:
                print("  Token is required.")
                sys.exit(1)
        self._fetch_mxid()
        if not self._mxid:
            print("  ✘  Could not verify token (whoami failed).")
            sys.exit(1)
        print(f"  ✔  Authenticated as {self._mxid}")

    # ── internal HTTP helpers ─────────────────────────────────────────────

    def _url(self, path: str) -> str:
        return f"{self.homeserver}/_matrix/client/v3{path}"

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

    def _handle_rate_limit(self, r) -> None:
        """Wait out a Matrix rate-limit, printing a countdown for long waits."""
        wait = r.json().get("retry_after_ms", 1000) / 1000
        if wait <= 5:
            print(f"    ⏳ Matrix rate-limit – waiting {wait:.1f}s …")
            time.sleep(wait + 0.1)
            return

        import datetime
        resume_at = datetime.datetime.now() + datetime.timedelta(seconds=wait)
        print(
            f"\n    ⏳ Matrix rate-limit: {wait:.0f}s ({wait/60:.1f} min)  "
            f"– resuming at {resume_at.strftime('%H:%M:%S')}  (Ctrl+C to cancel)\n"
        )
        interval = 30
        elapsed = 0
        while elapsed < wait:
            chunk = min(interval, wait - elapsed)
            time.sleep(chunk)
            elapsed += chunk
            remaining = math.ceil(wait - elapsed)
            if remaining > 0:
                print(f"      … {remaining}s remaining …")

    def _post(self, path: str, payload: dict) -> dict | None:
        for _ in range(5):
            r = requests.post(
                self._url(path), json=payload, headers=self._headers(), timeout=10
            )
            if r.status_code == 429:
                self._handle_rate_limit(r)
                continue
            if r.status_code in (401, 403):
                print(f"  ✘  Matrix auth error on {path}: {r.text[:200]}")
                sys.exit(1)
            if not r.ok:
                print(f"  ✘  Matrix {r.status_code} on {path}: {r.text[:200]}")
                return None
            return r.json()
        return None

    def _put(self, path: str, payload: dict) -> dict | None:
        for _ in range(5):
            r = requests.put(
                self._url(path), json=payload, headers=self._headers(), timeout=10
            )
            if r.status_code == 429:
                self._handle_rate_limit(r)
                continue
            if not r.ok:
                print(f"  ✘  Matrix PUT {r.status_code} on {path}: {r.text[:200]}")
                return None
            return r.json()
        return None

    # ── helpers ───────────────────────────────────────────────────────────

    def _via(self) -> list[str]:
        return [urlparse(self.homeserver).netloc]

    def _fetch_mxid(self) -> None:
        """Fetch and store the current user's Matrix ID."""
        r = requests.get(
            self._url("/account/whoami"), headers=self._headers(), timeout=10
        )
        if r.ok:
            self._mxid = r.json().get("user_id", "")

    def _power_levels(self) -> dict:
        """Default power level content applied to every room.
        The creator's MXID is explicitly set at 100 so that the initial_state
        event is not rejected when state_default is raised above 0.
        """
        pl: dict = {
            "ban": MOD,
            "kick": MOD,
            "redact": MOD,
            "invite": USER,
            "events_default": USER,
            "state_default": MOD,
            "users_default": USER,
            "events": {
                "m.room.name": MOD,
                "m.room.avatar": MOD,
                "m.room.topic": MOD,
                "m.room.power_levels": ADMIN,
                "m.room.history_visibility": ADMIN,
            },
        }
        if self._mxid:
            pl["users"] = {self._mxid: ADMIN}
        return pl

    def _create_space(
        self, name: str, topic: str | None = None, alias: str | None = None
    ) -> str | None:
        payload: dict = {
            "name": name,
            "creation_content": {"type": "m.space"},
            "visibility": "private",
            "preset": "private_chat",
            "initial_state": [
                {"type": "m.room.power_levels", "content": self._power_levels()}
            ],
        }
        if topic:
            payload["topic"] = topic
        if alias:
            safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in alias)
            payload["room_alias_name"] = safe

        result = self._post("/createRoom", payload)
        return result.get("room_id") if result else None

    def _create_room(
        self, name: str, topic: str | None = None, is_voice: bool = False
    ) -> str | None:
        payload: dict = {
            "name": name,
            "visibility": "private",
            "preset": "private_chat",
            "initial_state": [
                {"type": "m.room.power_levels", "content": self._power_levels()}
            ],
        }
        if topic:
            payload["topic"] = topic
        if is_voice:
            payload["creation_content"] = {"type": "m.voice"}

        result = self._post("/createRoom", payload)
        return result.get("room_id") if result else None

    def _add_child_to_space(self, space_id: str, child_id: str) -> bool:
        path = f"/rooms/{space_id}/state/m.space.child/{child_id}"
        result = self._put(path, {"via": self._via()})
        return result is not None

    # ── BaseAdapter interface ─────────────────────────────────────────────

    def create_server(self, snapshot: ServerSnapshot) -> str:
        space_id = self._create_space(
            name=snapshot.name,
            topic=snapshot.description,
        )
        if not space_id:
            print("  ✘  Failed to create Matrix Space.")
            sys.exit(1)
        print(f"  ✔  Space created (ID: {space_id})")
        return space_id

    def create_role(self, server_id: str, role: Role) -> str | None:
        level = map_permissions(role.permissions)
        self._role_levels.append((role.name, level))
        label = {ADMIN: "Admin", MOD: "Mod", USER: "User"}[level]
        print(f"    ↳ power level {level} ({label})")
        return role.id  # truthy stand-in — Matrix has no native role objects

    def create_category(self, server_id: str, category: Category) -> str | None:
        sub_space_id = self._create_space(name=category.name)
        time.sleep(2)
        if not sub_space_id:
            return None
        self._add_child_to_space(server_id, sub_space_id)
        time.sleep(2)
        return sub_space_id

    def create_channel(
        self,
        server_id: str,
        channel: Channel,
        category_map: dict[str, str],
    ) -> str | None:
        is_voice = channel.type == ChannelType.VOICE
        room_id = self._create_room(
            name=channel.name,
            topic=channel.topic,
            is_voice=is_voice,
        )
        time.sleep(2)
        if not room_id:
            return None

        parent_id = (
            category_map.get(channel.category_id) if channel.category_id else None
        )
        self._add_child_to_space(parent_id or server_id, room_id)
        time.sleep(2)
        return room_id

    def post_migration_message(self, server_id: str, snapshot: ServerSnapshot):
        print(f"\n  ℹ️  Matrix Space ID : {server_id}")
        print(f"     Share link      : matrix:roomid/{server_id.lstrip('!')}")

        if self._role_levels:
            print("\n  Role → Power Level mapping")
            print("  Assign these levels to users manually in Element:\n")
            for name, level in sorted(self._role_levels, key=lambda x: -x[1]):
                label = {ADMIN: "Admin", MOD: "Mod  ", USER: "User "}[level]
                print(f"    {level:>3}  ({label})  ←  {name}")
