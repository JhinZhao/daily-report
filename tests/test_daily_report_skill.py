#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for scripts/resolve_daily_paths.py.

Stdlib + pytest only, no network. Run:
    pytest tests/test_daily_report_skill.py -q

When contributing this skill upstream, this file belongs at
tests/skills/test_daily_report_skill.py in the hermes-agent repo.
"""

import importlib.util
import json
import os
import shutil
import sys
from pathlib import Path
from unittest import mock

SKILL_ROOT = Path(__file__).resolve().parent.parent
SCRIPT_PATH = SKILL_ROOT / "scripts" / "resolve_daily_paths.py"


def load_module(path=SCRIPT_PATH, name="resolve_daily_paths"):
    """Load the resolver as a module (it lives outside any package)."""
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def fake_home(tmp_path, env=None):
    """Context manager patching Path.home() inputs to a throwaway HOME."""
    home = tmp_path / "home"
    home.mkdir(parents=True, exist_ok=True)
    variables = {"HOME": str(home), "USERPROFILE": str(home)}
    if env:
        variables.update(env)
    return mock.patch.dict(os.environ, variables, clear=False)


def make_vault(root, name="MyVault", folder="日报", count=3):
    """Create an Obsidian-looking vault with a daily folder."""
    vault = root / name
    (vault / ".obsidian").mkdir(parents=True, exist_ok=True)
    daily = vault / folder
    daily.mkdir(parents=True, exist_ok=True)
    for i in range(count):
        (daily / ("2025-03-0%d.md" % (i + 1))).write_text("x", encoding="utf-8")
    return vault, daily


# --------------------------------------------------------------------------
# Regex / pure helpers
# --------------------------------------------------------------------------

def test_date_file_regex_accepts_expected_names():
    mod = load_module()
    assert mod.DATE_FILE_RE.match("2025-03-05.md")
    assert mod.DATE_FILE_RE.match("2025-03-05.markdown")
    assert not mod.DATE_FILE_RE.match("2025-03-05.txt")
    assert not mod.DATE_FILE_RE.match("notes-2025-03-05.md")


def test_score_daily_dir_counts_matching_files(tmp_path):
    mod = load_module()
    daily = tmp_path / "daily"
    daily.mkdir()
    (daily / "2025-01-01.md").write_text("x")
    (daily / "2025-01-02.md").write_text("x")
    (daily / "readme.md").write_text("x")
    assert mod.score_daily_dir(daily) == 2
    assert mod.score_daily_dir(tmp_path / "missing") == 0


# --------------------------------------------------------------------------
# Detection branches
# --------------------------------------------------------------------------

def test_autodetects_vault_and_daily_folder(tmp_path):
    mod = load_module()
    with fake_home(tmp_path):
        home = Path(os.environ["HOME"])
        _, daily = make_vault(home / "Documents", name="Obsidian", folder="日报", count=5)
        info = mod.resolve(SKILL_ROOT)

    assert info["mode"] == "obsidian"
    assert Path(info["daily_dir"]) == daily
    assert info["off_work_dir"] == str(daily / ".off-work")
    assert info["wikilinks"] is True
    assert info["file_count"] == 5
    assert info["source"].startswith("autodetect")


def test_daily_notes_json_folder_wins(tmp_path):
    mod = load_module()
    with fake_home(tmp_path):
        home = Path(os.environ["HOME"])
        vault = home / "Documents" / "Obsidian"
        wanted = vault / "journal" / "daily"
        wanted.mkdir(parents=True)
        (vault / ".obsidian").mkdir(parents=True, exist_ok=True)
        (vault / ".obsidian" / "daily-notes.json").write_text(
            json.dumps({"folder": "journal/daily", "format": "YYYY-MM-DD"}), encoding="utf-8"
        )
        (wanted / "2025-01-01.md").write_text("x", encoding="utf-8")
        # decoy folder with a higher file count — config must still win
        decoy = vault / "日报"
        decoy.mkdir()
        for i in range(9):
            (decoy / ("2025-02-0%d.md" % (i + 1))).write_text("x", encoding="utf-8")
        info = mod.resolve(SKILL_ROOT)

    assert Path(info["daily_dir"]) == wanted
    assert info["source"] == "obsidian:daily-notes.json"


def test_env_var_overrides_everything(tmp_path):
    mod = load_module()
    target = tmp_path / "custom-reports"
    target.mkdir()
    with fake_home(tmp_path, env={"DAILY_REPORT_HOME": str(target)}):
        info = mod.resolve(SKILL_ROOT)

    assert Path(info["daily_dir"]) == target
    assert info["source"] == "env:DAILY_REPORT_HOME"
    assert info["mode"] == "plain"  # not inside any vault


def test_config_file_beats_autodetection(tmp_path):
    skill_copy = tmp_path / "skill"
    skill_copy.mkdir()
    shutil.copy(SCRIPT_PATH, skill_copy / "resolve_daily_paths.py")
    configured = tmp_path / "configured-reports"
    configured.mkdir()
    (skill_copy / "config.local.json").write_text(
        json.dumps({"daily_dir": str(configured)}, ensure_ascii=False), encoding="utf-8"
    )
    mod = load_module(skill_copy / "resolve_daily_paths.py", name="resolver_cfg")

    with fake_home(tmp_path):
        home = Path(os.environ["HOME"])
        make_vault(home / "Documents", name="Obsidian", count=4)  # would be detected otherwise
        info = mod.resolve(skill_copy)

    assert Path(info["daily_dir"]) == configured
    assert info["source"] == "config:config.local.json"


def test_falls_back_to_plain_mode_without_obsidian(tmp_path):
    mod = load_module()
    with fake_home(tmp_path):
        info = mod.resolve(SKILL_ROOT)

    assert info["mode"] == "plain"
    assert info["vault"] is None
    assert info["source"] == "fallback"
    assert info["wikilinks"] is False
    assert Path(info["daily_dir"]).exists()  # fallback dir is created
    assert info["warnings"], "fallback must warn so the agent asks the user"


def test_malformed_config_is_reported_not_fatal(tmp_path):
    skill_copy = tmp_path / "skill"
    skill_copy.mkdir()
    shutil.copy(SCRIPT_PATH, skill_copy / "resolve_daily_paths.py")
    (skill_copy / "config.local.json").write_text("{ not json", encoding="utf-8")
    mod = load_module(skill_copy / "resolve_daily_paths.py", name="resolver_badcfg")

    with fake_home(tmp_path):
        info = mod.resolve(skill_copy)

    assert any("cannot parse" in w for w in info["warnings"])
    assert info["daily_dir"]  # still returns a usable path


# --------------------------------------------------------------------------
# CLI contract
# --------------------------------------------------------------------------

def test_cli_json_output_is_parseable(tmp_path):
    import subprocess

    with fake_home(tmp_path):
        home = Path(os.environ["HOME"])
        _, daily = make_vault(home / "Documents", name="Obsidian", count=2)
        result = subprocess.run(
            [sys.executable, str(SCRIPT_PATH), "--json"],
            capture_output=True, text=True, check=True, env=dict(os.environ),
        )
    info = json.loads(result.stdout)
    for key in ("mode", "vault", "daily_dir", "off_work_dir", "date_pattern", "wikilinks", "source"):
        assert key in info
    assert Path(info["daily_dir"]) == daily
