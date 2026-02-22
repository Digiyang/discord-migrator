# Discord Migrator

Following Discord's age-verification changes, some communities are exploring alternative
platforms. Migrating manually is tedious — you have to recreate every role, category, and
channel by hand. This tool automates that: it reads your Discord server structure via the
Discord API and recreates it on a target platform with a single command.

The adapter architecture keeps the core migration logic platform-agnostic, so adding
support for a new destination is a matter of implementing one file.

---

## Features

- **Plugin architecture** — adding a new platform = one new file
- Migrates: server name, description, roles (with colours), categories, channels
  (text + voice), channel topics, and parent-channel relationships
- Graceful rate-limit handling for both Discord and target APIs
- Detailed migration report at the end

---

## Requirements

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

Python 3.10+ required (uses `X | Y` union type hints).

---

## Usage

```bash
python main.py
```

You will be prompted to:
1. Choose your target platform
2. Enter your **Discord Bot Token** + **Guild ID**
3. Enter credentials for the target platform

---

## Project Structure

```
discord_migrator/
├── models.py            ← neutral ServerSnapshot dataclasses
├── discord_reader.py    ← reads Discord → ServerSnapshot
├── migrator.py          ← platform-agnostic migration engine
├── adapters/
│   ├── base.py          ← abstract adapter interface
│   ├── stoat.py         ← Stoat adapter
│   ├── matrix.py        ← Matrix/Element adapter
│   └── guilded.py       ← Guilded stub  (TODO)
└── main.py              ← CLI entry point
```

---

## Adding a new platform

1. Copy `adapters/guilded.py` as a starting point
2. Implement `create_server`, `create_role`, `create_category`, `create_channel`
3. In `main.py`, add two lines:
   ```python
   from adapters.myplatform import MyAdapter
   ADAPTERS["3"]       = MyAdapter
   ADAPTER_LABELS["3"] = "My Platform (myplatform.com)"
   ```
4. Done — the migrator engine handles the rest.

---

## What is NOT migrated

| Item | Reason |
|---|---|
| Message history | Discord ToS + user privacy |
| Bot integrations | Platform-specific, need manual setup |
| Fine-grained permissions | No 1:1 mapping across platforms |
| Custom emojis | API limitations |
| Members | Cannot force users to join another platform |

---

## License

MIT
