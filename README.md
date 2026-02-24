# Discord Migrator

Following Discord's age-verification changes, some communities are exploring alternative
platforms. Migrating manually is tedious — you have to recreate every role, category, and
channel by hand. This tool automates that: it reads your Discord server structure via the
Discord API and recreates it on a target platform with a single command.

The adapter architecture keeps the core migration logic platform-agnostic, so adding
support for a new destination is a matter of implementing one file.

---

## What is migrated

| Item | Details |
|---|---|
| Server name & icon | Applied to the destination server |
| Roles | Name, colour, and permission mapping |
| Categories | Recreated and linked to their channels |
| Text channels | Name and topic |
| Voice channels | Name |

## What is NOT migrated

| Item | Reason |
|---|---|
| Message history | Discord ToS + user privacy |
| Members | Cannot force users to join another platform |
| Bot integrations | Platform-specific, need manual setup |
| Fine-grained channel permissions | No 1:1 mapping across platforms |
| Custom emojis | API limitations |

---

## Requirements

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

Python 3.10+ required (uses `X | Y` union type hints).

---

## Configuration

To avoid entering credentials on every run, create a `config.json` file at the project
root (it is gitignored and will never be committed):

```json
{
  "discord": {
    "token": "your-discord-bot-token",
    "guild_id": "your-server-id"
  },
  "stoat": {
    "token": "your-stoat-bot-token",
    "server_id": "your-stoat-server-id"
  }
}
```

Any field present in the file is used silently. Missing fields fall back to an interactive
prompt at runtime.

---

## Usage

```bash
python main.py
```

You will be prompted to choose a target platform, then confirm or enter credentials.

---

## Platform Setup

### Stoat

1. Create a bot at https://stoat.chat/settings/bots and copy the **Bot Token**
2. Create your destination server on stoat.chat and invite the bot to it
3. Go to **Server Settings → Roles** and create a role (e.g. `bot`) with at minimum:
   - Manage Server
   - Manage Channels
   - Manage Roles
   - Manage Permissions
4. Go to **Server Settings → Members**, find your bot, and assign it that role
5. Find your **Server ID**: open the server in the Stoat web app — the URL looks like
   `https://stoat.chat/server/SERVER_ID/...` — copy that value

### Discord (source)

1. Go to https://discord.com/developers/applications → **New Application** → **Bot**
2. Copy the **Bot Token**
3. Enable **View Channels** permission and invite the bot to your server
4. Find your **Server ID**: in Discord settings go to **Advanced**, enable
   **Developer Mode**, then right-click your server icon and select **Copy Server ID**

---

## Project Structure

```
discord_migrator/
├── models.py                         ← platform-neutral ServerSnapshot dataclasses
├── discord_reader.py                 ← reads Discord → ServerSnapshot
├── migrator.py                       ← platform-agnostic migration engine
├── adapters/
│   ├── base.py                       ← abstract adapter interface
│   ├── stoat.py                      ← Stoat adapter
│   └── permissions/
│       └── stoat.py                  ← Discord → Stoat permission mapping
└── main.py                           ← CLI entry point
```

---

## Adding a new platform

1. Copy `adapters/guilded.py` as a starting point
2. Implement `create_server`, `create_role`, `create_category`, `create_channel`
3. If the platform has its own permission system, add a mapping file under
   `adapters/permissions/myplatform.py`
4. Register it in `main.py`:
   ```python
   from adapters.myplatform import MyAdapter
   ADAPTERS["3"]       = MyAdapter
   ADAPTER_LABELS["3"] = "My Platform (myplatform.com)"
   ```

The migrator engine handles the rest automatically.

---

## Contributing

Contributions are welcome — especially new platform adapters.

- **Bug reports & feature requests:** open an issue on
  [GitHub](https://github.com/Digiyang/discord-migrator/issues)
- **Pull requests:** fork the repo, make your changes on a feature branch, and open a PR
  against `main`
- Keep adapters self-contained — all platform-specific logic stays inside its adapter file
- If adding a platform with a permission system, add a mapping file under
  `adapters/permissions/`

---

## License

MIT
