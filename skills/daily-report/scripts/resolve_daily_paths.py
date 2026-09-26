#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Locate where daily reports live — without hard-coding any user path.

Usage:
    python3 resolve_daily_paths.py            # human-readable + JSON
    python3 resolve_daily_paths.py --json     # JSON only (for agents to parse)

Resolution order (first hit wins, later stages only fill gaps):
    1. env vars     DAILY_REPORT_HOME / OBSIDIAN_VAULT / DAILY_REPORT_VAULT
    2. config.local.json  (next to this script; always wins if it sets a field)
    3. Obsidian      <vault>/.obsidian/daily-notes.json  -> "folder" / "format"
    4. autodetect    common vault locations, then candidate daily folders scored
                     by how many YYYY-MM-DD files they hold
    5. fallback      ~/.local/share/daily-report  (plain Markdown mode)

Output fields:
    mode          "obsidian" when the daily folder lives in a vault, else "plain"
    vault         vault root or null
    daily_dir     absolute path of the daily-report folder
    off_work_dir  <daily_dir>/.off-work  (flag directory for "checked out / archived")
    date_pattern  filename pattern of one report, e.g. YYYY-MM-DD.md
    wikilinks     whether the archive format can use Obsidian [[wikilinks]]
    source        which stage produced daily_dir
    candidates    top scored (vault, folder, score) triples, for transparency
    warnings      non-fatal notes the agent should surface to the user

No third-party dependencies. Python 3.8+.
"""

import json
import os
import re
import sys
from pathlib import Path

DATE_FILE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}\.(md|markdown)$", re.IGNORECASE)

# Folder names that commonly hold one-file-per-day notes.
DAILY_DIR_NAMES = [
    "日报", "工作日报", "日记", "daily", "dailies", "daily-notes", "journal",
    "journals", "notes/daily", "reports/daily",
]

CONFIG_NAME = "config.local.json"
FALLBACK_DIR = Path.home() / ".local" / "share" / "daily-report"
MAX_VAULT_DEPTH = 4


def load_config(script_dir: Path):
    cfg = {}
    path = script_dir / CONFIG_NAME
    if path.is_file():
        try:
            cfg = json.loads(path.read_text(encoding="utf-8")) or {}
        except Exception as exc:  # malformed config must not crash the resolver
            cfg = {"_error": "cannot parse %s: %s" % (path, exc)}
    return cfg


def safe_iterdir(path: Path):
    try:
        return sorted(p for p in path.iterdir() if p.is_dir())
    except (PermissionError, OSError):
        return []


def find_vaults(home: Path, env_vault):
    """Return candidate Obsidian vault roots (dirs containing .obsidian)."""
    roots = []
    if env_vault:
        p = Path(env_vault).expanduser()
        if p.is_dir():
            roots.append(p)

    for base in (
        home / "Documents" / "Obsidian",
        home / "Documents",
        home / "Obsidian",
        home / "vaults",
        home,
        home / "Library" / "Mobile Documents" / "iCloud~md~obsidian" / "Documents",
    ):
        if base.is_dir():
            roots.append(base)

    found, seen = [], set()
    for root in roots:
        if not root.is_dir():
            continue
        # The root itself may be a vault.
        stack = [(root, 0)]
        while stack:
            cur, depth = stack.pop()
            if depth > MAX_VAULT_DEPTH:
                continue
            if (cur / ".obsidian").is_dir():
                key = str(cur.resolve())
                if key not in seen:
                    seen.add(key)
                    found.append(cur)
                # Nested vaults still exist under a vault (e.g. vault/inner-vault),
                # so keep descending a little.
            for child in safe_iterdir(cur):
                if child.name.startswith(".") or child.name in (
                    "node_modules", "Library", "Applications", "Music", "Movies",
                    "Pictures", "Desktop", "Downloads",
                ):
                    continue
                stack.append((child, depth + 1))
    return found


def score_daily_dir(path: Path):
    """How many YYYY-MM-DD files does this folder hold? (cheap heuristic)"""
    try:
        return sum(1 for p in path.iterdir() if DATE_FILE_RE.match(p.name))
    except (PermissionError, OSError):
        return 0


def daily_notes_folder(vault: Path):
    """Read Obsidian daily-notes plugin config for the configured folder."""
    cfg_path = vault / ".obsidian" / "daily-notes.json"
    if not cfg_path.is_file():
        return None, None
    try:
        cfg = json.loads(cfg_path.read_text(encoding="utf-8")) or {}
    except Exception:
        return None, None
    folder = (cfg.get("folder") or "").strip()
    fmt = (cfg.get("format") or "").strip() or None
    if not folder:
        return None, fmt
    cand = (vault / folder).expanduser()
    return (cand if cand.is_dir() else None), fmt


def collect_candidates(vaults):
    """Return [(score, vault_or_None, daily_dir)] sorted by score desc."""
    out = []
    for vault in vaults:
        cfg_dir, _ = daily_notes_folder(vault)
        if cfg_dir is not None:
            out.append((score_daily_dir(cfg_dir) + 1000, vault, cfg_dir))  # explicit config wins
        for name in DAILY_DIR_NAMES:
            cand = vault / name
            if cand.is_dir():
                out.append((score_daily_dir(cand), vault, cand))
    out.sort(key=lambda t: t[0], reverse=True)
    return out


def resolve(script_dir: Path):
    home = Path.home()
    warnings = []
    cfg = load_config(script_dir)

    env_daily = os.environ.get("DAILY_REPORT_HOME")
    env_vault = os.environ.get("OBSIDIAN_VAULT") or os.environ.get("DAILY_REPORT_VAULT")

    vaults = find_vaults(home, env_vault)
    candidates = collect_candidates(vaults)
    debug = [{"score": s, "vault": str(v) if v else None, "dir": str(d)} for s, v, d in candidates[:5]]

    # 1) explicit env override for the daily folder
    if env_daily and Path(env_daily).expanduser().is_dir():
        daily_dir = Path(env_daily).expanduser()
        vault = next((v for s, v, d in candidates if str(d) == str(daily_dir)), None)
        if vault is None:
            vault = next((v for v in vaults if str(daily_dir).startswith(str(v))), None)
        source = "env:DAILY_REPORT_HOME"
        mode = "obsidian" if vault else "plain"

    # 2) config file wins over autodetection
    elif cfg.get("daily_dir") and Path(str(cfg["daily_dir"])).expanduser().is_dir():
        daily_dir = Path(str(cfg["daily_dir"])).expanduser()
        vault = Path(str(cfg["obsidian_vault"])).expanduser() if cfg.get("obsidian_vault") else None
        if vault is None:
            vault = next((v for v in vaults if str(daily_dir).startswith(str(v))), None)
        source = "config:%s" % CONFIG_NAME
        mode = "obsidian" if vault else "plain"

    # 3) autodetected best candidate (Obsidian daily-notes config scored +1000)
    elif candidates:
        score, vault, daily_dir = candidates[0]
        if score >= 1000:
            source = "obsidian:daily-notes.json"
        elif score > 0:
            source = "autodetect:date-file-density"
        else:
            source = "autodetect:folder-name"
            warnings.append(
                "找到了疑似日报目录 %s，但里面没有 YYYY-MM-DD 格式的文件——"
                "请跟用户确认这是不是日报根目录。" % daily_dir
            )
        mode = "obsidian"

    # 4) fallback: plain directory, no Obsidian required
    else:
        daily_dir = Path(cfg.get("daily_dir")).expanduser() if cfg.get("daily_dir") else FALLBACK_DIR
        vault = None
        mode = "plain"
        source = "fallback"
        warnings.append(
            "没有检测到 Obsidian vault，也没有配置日报目录；将使用 %s（纯 Markdown 模式）。"
            "请跟用户确认，并把确认后的路径写进 %s。" % (daily_dir, CONFIG_NAME)
        )

    if cfg.get("_error"):
        warnings.append(cfg["_error"])

    daily_dir.mkdir(parents=True, exist_ok=True)
    off_work = daily_dir / (cfg.get("off_work_subdir") or ".off-work")

    return {
        "mode": mode,
        "vault": str(vault) if vault else None,
        "daily_dir": str(daily_dir),
        "off_work_dir": str(off_work),
        "date_pattern": "YYYY-MM-DD.md",
        "wikilinks": mode == "obsidian",
        "source": source,
        "exists": daily_dir.is_dir(),
        "file_count": score_daily_dir(daily_dir),
        "candidates": debug,
        "warnings": warnings,
    }


def main(argv):
    script_dir = Path(__file__).resolve().parent
    # allow running from inside scripts/ or from the skill root
    if script_dir.name == "scripts":
        script_dir = script_dir.parent
    info = resolve(script_dir)
    if "--json" in argv:
        print(json.dumps(info, ensure_ascii=False, indent=2))
        return 0
    print("daily-report 路径解析")
    print("  mode        : %s" % info["mode"])
    print("  vault       : %s" % (info["vault"] or "-"))
    print("  daily_dir   : %s" % info["daily_dir"])
    print("  off_work_dir: %s" % info["off_work_dir"])
    print("  wikilinks   : %s" % info["wikilinks"])
    print("  source      : %s" % info["source"])
    print("  existing    : %s 个日报文件" % info["file_count"])
    for w in info["warnings"]:
        print("  ! %s" % w)
    print()
    print(json.dumps(info, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
