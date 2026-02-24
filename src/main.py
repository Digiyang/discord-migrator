"""
main.py
───────
CLI entry point for the Discord → Platform migration tool.

To add a new platform:
  1. Write your adapter in adapters/myplatform.py
  2. Import it here
  3. Add it to ADAPTERS dict below
  That's it — the migrator engine handles the rest automatically.
"""

from __future__ import annotations
import getpass
import json
import os
import sys

from discord_reader import DiscordReader
from migrator import Migrator

# ── Register adapters here ────────────────────────────────────────────────────
from adapters.stoat import StoatAdapter

ADAPTERS = {
    "1": StoatAdapter,
    # "2": MatrixAdapter,
    # "3": GuildedAdapter,       ← add future adapters here
    # "4": MattermostAdapter,
    # "5": ZulipAdapter,
}

ADAPTER_LABELS = {
    "1": "Stoat          (stoat.chat)",
    "2": "Matrix/Element (self-hosted or matrix.org)",
}

# ── ANSI ──────────────────────────────────────────────────────────────────────
BOLD = "\033[1m"
CYAN = "\033[96m"
YELLOW = "\033[93m"
RESET = "\033[0m"


def banner():
    print(f"""
{BOLD}╔══════════════════════════════════════════════════╗
║   Discord → Platform Migration Tool  v1.0        ║
║   Extensible · Plugin-based · Privacy-first      ║
╚══════════════════════════════════════════════════╝{RESET}

Migrates your Discord server structure to another platform.

{YELLOW}What is migrated:{RESET}
  ✔ Server name & description
  ✔ Roles (with colours)
  ✔ Categories (in order)
  ✔ Text channels, voice channels (with topics)

{YELLOW}What is NOT migrated:{RESET}
  ✘ Message history  (Discord ToS + privacy)
  ✘ Bot integrations (must be set up manually)
  ✘ Fine-grained permissions (mapped as best-effort)
""")


def pick_adapter():
    print(f"{BOLD}Choose your target platform:{RESET}\n")
    for key, label in ADAPTER_LABELS.items():
        print(f"  [{key}]  {label}")
    print()

    while True:
        choice = input("  Enter number: ").strip()
        if choice in ADAPTERS:
            return ADAPTERS[choice]()
        print("  Please enter a valid number.")


def prompt(label: str, secret: bool = False) -> str:
    while True:
        val = (
            getpass.getpass(f"  {label}: ") if secret else input(f"  {label}: ")
        ).strip()
        if val:
            return val
        print("  (required)")


def load_config() -> dict:
    path = os.path.join(os.path.dirname(__file__), "config.json")
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return {}


def main():
    banner()

    config = load_config()

    # ── Pick target platform ──────────────────────────────────────────────
    adapter = pick_adapter()

    # ── Discord credentials ───────────────────────────────────────────────
    discord_cfg = config.get("discord", {})
    discord_token = discord_cfg.get("token", "")
    guild_id = discord_cfg.get("guild_id", "")

    if not discord_token or not guild_id:
        print(f"\n{BOLD}Discord source credentials:{RESET}")
        print("  Create a bot at https://discord.com/developers/applications")
        print("  Give it 'View Channels' permission and invite it to your server.\n")
    if not discord_token:
        discord_token = prompt("Discord Bot Token", secret=True)
    if not guild_id:
        guild_id = prompt("Discord Server (Guild) ID")

    # ── Target platform credentials ───────────────────────────────────────
    adapter.load_config(config.get(adapter.config_key, {}))
    print(f"\n{BOLD}{adapter.platform_name} credentials:{RESET}")
    adapter.prompt_credentials()

    # ── Run migration ──────────────────────────────────────────────────────
    reader = DiscordReader(bot_token=discord_token, guild_id=guild_id)
    snapshot = reader.read()

    migrator = Migrator(adapter)
    migrator.run(snapshot)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n  Migration cancelled.")
        sys.exit(0)
