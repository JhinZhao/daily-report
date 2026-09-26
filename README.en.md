# daily-report

**A cross-session daily report skill** for AI agents — jot down work items as you go, preview the report, then archive it as a proper daily note (Obsidian wikilinks or plain Markdown).

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![tests](https://img.shields.io/badge/tests-9%20passed-brightgreen.svg)](#development)
[![python](https://img.shields.io/badge/python-3.8%2B-blue.svg)](#requirements)
[![node](https://img.shields.io/badge/node-%E2%89%A516%20(npx%20only)-informational.svg)](#option-1-npx-one-liner)

> 中文说明见 [README.md](README.md). The skill's trigger phrases are Chinese (`【记录】`, `下班`, `归档`); edit `SKILL.md` to localize them.

---

## What it is

A workflow skill for AI coding agents (Hermes Agent, Claude Code, Codex, …) that makes daily reporting frictionless while keeping the data honest:

```
【记录】finished the login module integration    ← log a work item
【待办】verify the payment flow tomorrow          ← log a TODO
下班                                             ← agent shows you a preview
归档                                             ← only now does it write files
```

The point: **logging has to cost nothing, and the data must never be lost, jumbled, or invented.**

## Why

Most agent-written work logs fail in the same predictable ways. This skill closes each one:

| Failure | How it's handled |
|---|---|
| Records live only in the chat — gone next session | Every item is written to disk **immediately**; files are the only source of truth |
| The agent guesses the date and files today's log under yesterday | Real system time is read on the spot; file state is checked before every write |
| The agent "helpfully" invents work you never did | Only items you actually stated are used — fewer is better than fabricated |
| You say "show me the report" and it writes files | Preview and archive are separate steps; writing requires explicit confirmation |
| Archiving wipes existing content | Archived notes are appended to, never overwritten; raw logs are kept forever |
| Notes don't follow you to another machine | Everything lives in your own Markdown files — portable, inspectable, greppable |

## Features

- **No hardcoded paths** — auto-detects your report directory (env → local config → Obsidian `daily-notes.json` → common locations → fallback), so it keeps working across machines
- **Obsidian optional** — uses `frontmatter + [[wikilinks]]` inside a vault, and degrades to plain Markdown outside one (never writes `[[ ]]` into a plain file)
- **Two output formats** — a plain-text report for humans (`【project】`) and a wikilinked note for Obsidian, converted at write time
- **Backlog check** — the agent can prove which days were never archived from file evidence instead of "I think I did"
- **Optional external sync** — mirror reports into a table/database (Airtable, Notion, internal systems), off by default, with 8 idempotency rules
- **Stdlib only** — the one script uses the Python standard library, no third-party packages
- **No network** — sends nothing, uploads nothing, phones no one

## Install

### Option 1: npx (one-liner)

```bash
npx github:JhinZhao/daily-report
```

Installs into `~/.hermes/skills/daily-report` by default.

```bash
# into any agent's skills dir
npx github:JhinZhao/daily-report --dir ~/.agents/skills/daily-report

# overwrite an existing install
npx github:JhinZhao/daily-report --force

# just print the resolved destination
npx github:JhinZhao/daily-report --print-dir
```

Needs Node ≥ 16. npx fetches the package straight from GitHub — **no npm publish required**, no `npm install`.

### Option 2: Hermes Agent

```bash
git clone https://github.com/JhinZhao/daily-report.git /tmp/daily-report-src
cp -r /tmp/daily-report-src/skills/daily-report ~/.hermes/skills/

# or register this repo as a skill source
hermes skills tap add JhinZhao/daily-report
hermes skills search daily-report --source github
hermes skills install <identifier-from-the-search>
```

Verify: `hermes skills list | grep daily-report`

### Option 3: Manual (any agent framework)

1. Grab `daily-report-skill-v0.1.0.zip` from [Releases](https://github.com/JhinZhao/daily-report/releases), or clone the repo
2. Copy `skills/daily-report/` into your agent's skills directory
3. Confirm `SKILL.md` is there

Typical locations: `~/.hermes/skills/`, project-level `.hermes/skills/` or `.agents/skills/`, or whatever your framework documents.

## Quick start

See which directory it resolves:

```bash
python3 ~/.hermes/skills/daily-report/scripts/resolve_daily_paths.py
```

```json
{
  "mode": "obsidian",
  "vault": "/Users/you/Documents/Obsidian/MyVault",
  "daily_dir": "/Users/you/Documents/Obsidian/MyVault/日报",
  "off_work_dir": "/Users/you/Documents/Obsidian/MyVault/日报/.off-work",
  "source": "obsidian:daily-notes.json",
  "warnings": []
}
```

- `mode: obsidian` → archiving uses `[[wikilinks]]`
- `mode: plain` → plain Markdown, archiving uses `## Project` headings
- Wrong result → drop a `config.local.json` (see below) or just tell the agent your path

## Usage

No commands to memorize — talk to your agent:

| You say | Agent does | Writes files? |
|---|---|---|
| `【记录】finished the login integration` | Append to today's log | ✅ immediately |
| `【待办】verify payments tomorrow` | Add to "tomorrow's plan" | ✅ immediately |
| `下班` / "give me the report" | Show a preview | ❌ read-only |
| `归档` / "confirm" | Write the final note + check-out marker | ✅ |
| `去掉【that item】` | Remove an entry | ✅ |
| "which days did I not archive?" | Answer from file evidence | ❌ |

## Configuration

Optional — the script auto-detects. To pin it down:

```bash
cp ~/.hermes/skills/daily-report/config.local.json.example \
   ~/.hermes/skills/daily-report/config.local.json
```

```json
{
  "daily_dir": "/absolute/path/to/your/daily-reports",
  "off_work_subdir": ".off-work",
  "obsidian_vault": null,
  "projects": { "alias": "ProjectA" },
  "external_sync": null
}
```

`config.local.json` holds local paths — it is git-ignored here; never commit yours.

Environment variables also work: `DAILY_REPORT_HOME`, `OBSIDIAN_VAULT`, `DAILY_REPORT_VAULT`.

## How the directory is resolved

`scripts/resolve_daily_paths.py` tries, in order, and stops at the first hit:

1. Env vars `DAILY_REPORT_HOME` / `OBSIDIAN_VAULT` / `DAILY_REPORT_VAULT`
2. `daily_dir` in `config.local.json`
3. The vault's `.obsidian/daily-notes.json` (your daily-notes plugin `folder`)
4. Common locations: `~/Documents/Obsidian`, the iCloud Obsidian container, `~/Obsidian`, `~/vaults/*`
5. Candidate folder names inside any vault (`日报` / `daily` / `dailies` / `journal`…), scored by how many `YYYY-MM-DD.md` files they hold
6. Nothing found → falls back to `~/.local/share/daily-report` **and warns**, so the agent asks you

It always reports its `source`, so the conclusion is never a black box.

## FAQ

**Do I need Obsidian?** No. Without a vault it degrades to plain Markdown (`## Project` headings, no `[[ ]]`).

**Will it overwrite my notes?** No. Archived notes are appended to with a targeted patch, never rewritten wholesale; file state is read before every write. "Preview" writes nothing.

**Where is my data?** In your own Markdown files. This skill makes **no network requests** and uploads nothing.

**Windows?** Supported. The only platform difference is date retrieval: `date "+%Y-%m-%d"` on POSIX, `Get-Date -Format "yyyy-MM-dd dddd"` on Windows — both are documented in `SKILL.md`.

**How do I uninstall?** `rm -rf ~/.hermes/skills/daily-report`.

## Development

```bash
git clone https://github.com/JhinZhao/daily-report.git
cd daily-report
python3 -m pytest tests/ -q      # 9 passed
```

Coverage: vault autodetection, `daily-notes.json` precedence, env override, config override, plain-mode downgrade + warning, malformed-config tolerance, CLI JSON contract. Offline; fake vaults are built with `tmp_path`.

### Requirements

- Python ≥ 3.8 (stdlib only)
- Node ≥ 16 (**only** for the npx installer)
- Obsidian optional

### Repository layout

```
daily-report/
├── skills/daily-report/          # the skill itself (this is what gets installed)
├── bin/install.js                # npx installer
├── tests/                        # pytest suite
├── package.json
└── LICENSE
```

The skill follows the [Hermes Agent in-repo skill standards](https://github.com/NousResearch/hermes-agent) (frontmatter fields, section order, tool references, size and test expectations).

## License

**MIT** — use, copy, modify, merge, publish, distribute, sublicense and sell freely, provided the copyright notice and permission notice are retained. Provided "as is", without warranty.

See [LICENSE](LICENSE).
