"""
migrator.py
───────────
The migration engine.

Takes a ServerSnapshot and any BaseAdapter implementation, then drives the
full migration sequence:
  1. Create server / workspace / space
  2. Create roles
  3. Create categories
  4. Create channels (placed in the right categories)
  5. Print a detailed report

Completely platform-agnostic — zero imports from Discord or any target platform.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from models import ServerSnapshot
from adapters.base import BaseAdapter

# ── ANSI colours ──────────────────────────────────────────────────────────────
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
CYAN = "\033[96m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"


def _ok(msg):
    print(f"  {GREEN}✔{RESET}  {msg}")


def _warn(msg):
    print(f"  {YELLOW}⚠{RESET}  {msg}")


def _head(msg):
    print(f"\n{BOLD}{msg}{RESET}")


# ── Migration report ──────────────────────────────────────────────────────────


@dataclass
class MigrationReport:
    platform: str
    server_id: str = ""

    roles_ok: list[str] = field(default_factory=list)
    roles_skipped: list[str] = field(default_factory=list)

    cats_ok: list[str] = field(default_factory=list)
    cats_skipped: list[str] = field(default_factory=list)

    channels_ok: list[str] = field(default_factory=list)
    channels_skipped: list[str] = field(default_factory=list)

    def print(self):
        _head("═══════════════════ Migration Report ═══════════════════")

        print(f"\n  Target platform : {BOLD}{self.platform}{RESET}")
        print(f"  Server ID       : {self.server_id}\n")

        sections = [
            ("Roles", self.roles_ok, self.roles_skipped),
            ("Categories", self.cats_ok, self.cats_skipped),
            ("Channels", self.channels_ok, self.channels_skipped),
        ]
        for label, ok_list, skip_list in sections:
            print(
                f"  {label:<12}"
                f"  {GREEN}{len(ok_list)} migrated{RESET}"
                + (f"   {YELLOW}{len(skip_list)} skipped{RESET}" if skip_list else "")
            )
            for name in skip_list:
                print(f"             {DIM}↳ skipped: {name}{RESET}")

        print(f"\n  {CYAN}Next steps:{RESET}")
        print("   1. Open the platform and find your new server")
        print("   2. Invite your community members manually")
        print("   3. Re-add any bots or integrations")
        print("   4. Review and adjust channel permissions as needed")

        if self.roles_skipped and "Matrix" in self.platform:
            print(f"\n  {YELLOW}Note:{RESET} Matrix doesn't support global roles.")
            print("   Power levels must be set per-room after migration.")
        print()


# ── Migrator ──────────────────────────────────────────────────────────────────


class Migrator:
    def __init__(self, adapter: BaseAdapter):
        self.adapter = adapter

    def run(self, snapshot: ServerSnapshot) -> MigrationReport:
        report = MigrationReport(platform=self.adapter.platform_name)

        print(f"\n🚀  Migrating to {BOLD}{self.adapter.platform_name}{RESET} …")
        print(f"    Source: {snapshot.summary()}\n")

        # 1. Create the server / space / workspace
        _head(f"[1/4] Creating server on {self.adapter.platform_name} …")
        server_id = self.adapter.create_server(snapshot)
        report.server_id = server_id

        # 2. Roles
        _head("[2/4] Migrating roles …")
        if not snapshot.roles:
            print("  —  No custom roles found.")
        for role in sorted(snapshot.roles, key=lambda r: r.position):
            result = self.adapter.create_role(server_id, role)
            if result:
                _ok(f"Role: {role.name}")
                report.roles_ok.append(role.name)
            else:
                _warn(f"Role skipped: {role.name}")
                report.roles_skipped.append(role.name)

        # 3. Categories
        _head("[3/4] Migrating categories …")
        category_map: dict[str, str] = {}  # snapshot ID → platform ID

        if not snapshot.categories:
            print("  —  No categories found.")
        for cat in snapshot.categories:
            result = self.adapter.create_category(server_id, cat)
            if result:
                category_map[cat.id] = result
                _ok(f"Category: {cat.name}")
                report.cats_ok.append(cat.name)
            else:
                _warn(f"Category skipped: {cat.name}")
                report.cats_skipped.append(cat.name)

        # 4. Channels
        _head("[4/4] Migrating channels …")
        if not snapshot.channels:
            print("  —  No channels found.")
        for ch in snapshot.channels:
            result = self.adapter.create_channel(server_id, ch, category_map)
            label = f"[{ch.type.value}] #{ch.name}"
            if result:
                _ok(label)
                report.channels_ok.append(ch.name)
            else:
                _warn(f"Skipped: {label}")
                report.channels_skipped.append(ch.name)

        # 5. Optional post-migration hook (welcome message, etc.)
        self.adapter.post_migration_message(server_id, snapshot)

        report.print()
        return report
