#!/usr/bin/env node
'use strict';

/**
 * Installer for the daily-report skill.
 *
 * Copies skills/daily-report/ from this package into the target skills
 * directory (default: ~/.hermes/skills/daily-report).
 *
 * Usage:
 *   npx github:JhinZhao/daily-report
 *   npx github:JhinZhao/daily-report --dir ~/.agents/skills/daily-report
 *   npx github:JhinZhao/daily-report --force
 *   npx github:JhinZhao/daily-report --print-dir
 *
 * No dependencies: Node standard library only.
 */

const fs = require('fs');
const path = require('path');
const os = require('os');

const PKG_ROOT = path.join(__dirname, '..');
const SKILL_SRC = path.join(PKG_ROOT, 'skills', 'daily-report');
const DEFAULT_DEST = path.join(os.homedir(), '.hermes', 'skills', 'daily-report');

const SKIP = new Set(['__pycache__', '.pytest_cache', '.DS_Store', 'node_modules']);

function parseArgs(argv) {
  const opts = { dest: DEFAULT_DEST, force: false, printDir: false, help: false };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === '--dir' || a === '-d') {
      opts.dest = expandHome(argv[++i] || '');
    } else if (a.startsWith('--dir=')) {
      opts.dest = expandHome(a.slice(6));
    } else if (a === '--force' || a === '-f') {
      opts.force = true;
    } else if (a === '--print-dir') {
      opts.printDir = true;
    } else if (a === '--help' || a === '-h') {
      opts.help = true;
    } else {
      console.error(`unknown option: ${a}`);
      process.exitCode = 2;
      opts.help = true;
    }
  }
  return opts;
}

function expandHome(p) {
  if (!p) return p;
  return p.startsWith('~') ? path.join(os.homedir(), p.slice(1)) : p;
}

function usage() {
  console.log(`
daily-report skill installer

Usage:
  npx github:JhinZhao/daily-report [options]

Options:
  -d, --dir <path>   Install into <path> (default: ~/.hermes/skills/daily-report)
  -f, --force        Overwrite an existing installation
      --print-dir    Print the resolved destination and exit
  -h, --help         Show this help

Examples:
  npx github:JhinZhao/daily-report
  npx github:JhinZhao/daily-report --dir ~/.agents/skills/daily-report
  npx github:JhinZhao/daily-report --force
`);
}

function copyDir(src, dest, stats) {
  fs.mkdirSync(dest, { recursive: true });
  for (const entry of fs.readdirSync(src, { withFileTypes: true })) {
    if (SKIP.has(entry.name)) continue;
    const s = path.join(src, entry.name);
    const d = path.join(dest, entry.name);
    if (entry.isDirectory()) {
      copyDir(s, d, stats);
    } else if (entry.isFile()) {
      fs.copyFileSync(s, d);
      stats.files += 1;
      stats.bytes += fs.statSync(d).size;
    }
  }
}

function main() {
  const opts = parseArgs(process.argv.slice(2));

  if (opts.printDir) {
    console.log(opts.dest);
    return;
  }
  if (opts.help) {
    usage();
    return;
  }

  if (!fs.existsSync(SKILL_SRC)) {
    console.error(`✗ skill source not found: ${SKILL_SRC}`);
    console.error('  This package looks incomplete. Reinstall it and try again.');
    process.exitCode = 1;
    return;
  }

  const dest = path.resolve(opts.dest);
  const alreadyThere = fs.existsSync(path.join(dest, 'SKILL.md'));

  if (alreadyThere && !opts.force) {
    console.error(`✗ ${dest} already contains a SKILL.md`);
    console.error('  Re-run with --force to overwrite, or pass --dir <other-path>.');
    process.exitCode = 1;
    return;
  }

  const stats = { files: 0, bytes: 0 };
  try {
    copyDir(SKILL_SRC, dest, stats);
  } catch (err) {
    console.error(`✗ install failed: ${err.message}`);
    process.exitCode = 1;
    return;
  }

  const kb = (stats.bytes / 1024).toFixed(1);
  console.log(`✓ daily-report skill installed (${stats.files} files, ${kb} KB)`);
  console.log(`  → ${dest}`);
  console.log('');
  console.log('Next steps');
  console.log('  1. Point it at your report folder (optional — it auto-detects):');
  console.log(`       cp "${path.join(dest, 'config.local.json.example')}" "${path.join(dest, 'config.local.json')}"`);
  console.log('       then edit daily_dir');
  console.log('  2. Check what it resolved:');
  console.log(`       python3 "${path.join(dest, 'scripts', 'resolve_daily_paths.py')}"`);
  console.log('  3. In your agent session, just say:');
  console.log('       【记录】finished the thing      → append to today\'s log');
  console.log('       下班                            → preview the daily report');
  console.log('       归档                            → write the final report');
  console.log('');
  console.log('Requires python3 (stdlib only). No third-party Python packages.');
}

main();
