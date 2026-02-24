"""
adapters/base.py
────────────────
Abstract interface every platform adapter must implement.

To add a new platform:
  1. Create adapters/myplatform.py
  2. Subclass BaseAdapter
  3. Implement the three abstract methods
  4. Register it in main.py
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from models import ServerSnapshot, Role, Category, Channel


class BaseAdapter(ABC):
    """
    A platform adapter knows how to translate a ServerSnapshot into that
    platform's API calls.  It is stateful – it stores the mapping between
    snapshot IDs and platform-native IDs as it creates resources.
    """

    # Human-readable name shown in the CLI
    platform_name: str = "Unknown Platform"

    # Key used to look up this adapter's section in config.json
    config_key: str = ""

    # ── abstract interface ────────────────────────────────────────────────

    @abstractmethod
    def create_server(self, snapshot: ServerSnapshot) -> str:
        """
        Create (or locate) the destination server/space/workspace.
        Returns an opaque server ID used in subsequent calls.
        """

    @abstractmethod
    def create_role(self, server_id: str, role: Role) -> str | None:
        """
        Create a role/group on the server.
        Returns the platform-native role ID, or None on failure.
        """

    @abstractmethod
    def create_channel(
        self,
        server_id: str,
        channel: Channel,
        category_map: dict[str, str],  # snapshot cat ID → platform cat ID
    ) -> str | None:
        """
        Create a channel/room on the server.
        category_map lets the adapter place the channel in the right category.
        Returns the platform-native channel ID, or None on failure.
        """

    # ── optional hooks ────────────────────────────────────────────────────

    def create_category(self, server_id: str, category: Category) -> str | None:
        """
        Create a category / section on the server.
        Not all platforms have categories; the default is a no-op that returns None.
        """
        return None

    def post_migration_message(self, server_id: str, snapshot: ServerSnapshot):
        """
        Optionally send a welcome/info message after migration.
        Default: do nothing.
        """

    # ── credentials ───────────────────────────────────────────────────────

    def load_config(self, cfg: dict) -> None:
        """
        Pre-populate credentials from a config dict (e.g. parsed config.json).
        Override in subclasses. prompt_credentials() should only ask for
        fields that are still empty after this call.
        """

    @abstractmethod
    def prompt_credentials(self) -> None:
        """
        Interactively prompt the user for whatever credentials this adapter needs
        (token, homeserver URL, API key, etc.) and store them on self.
        """
