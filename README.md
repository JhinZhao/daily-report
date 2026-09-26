# daily-report

**跨会话的日报 skill** —— 把一天的工作项随手记下，一键生成日报预览，确认后归档成正式日报（Obsidian 双链格式或普通 Markdown）。

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![tests](https://img.shields.io/badge/tests-9%20passed-brightgreen.svg)](#开发与测试)
[![python](https://img.shields.io/badge/python-3.8%2B-blue.svg)](#依赖)
[![node](https://img.shields.io/badge/node-%E2%89%A516%20(npx%20only)-informational.svg)](#方式-1npx一行搞定)

> English version: [README.en.md](README.en.md)

---

## 这是什么

给 AI agent（Hermes Agent、Claude Code、Codex 等）用的一个**日报工作流 skill**。它规定了 agent 该怎么陪你写日报：

```
【记录】完成登录模块联调          ← 随口记一条
【记录】下午和产品对了个需求
【待办】明天验证支付链路
下班                             ← agent 整理成日报给你看
归档                             ← 你说一声，才写进文件
```

核心是一件事：**让"记录"零摩擦，同时保证数据不丢、不乱、不瞎编。**

## 为什么需要它

用过 AI 助手记工作日志的人，大概都踩过这些坑。这个 skill 就是逐条堵住它们的：

| 坑 | 它怎么处理 |
|---|---|
| agent 把记录只存在对话里，新开会话就没了 | 每条记录**立刻落盘**，文件是跨会话唯一的真相 |
| agent 把日期搞错，今天的内容写进昨天的文件 | 强制现场取系统时间，写文件前必须确认目标文件状态 |
| agent 顺手"帮你补全"，编出你没干过的工作 | 严格只用你实际说过的条目，宁少不编 |
| 你说"给我看看日报"，它直接写成文件了 | "预览"和"归档"是两道独立工序，写文件必须显式确认 |
| 归档把原来的内容覆盖没了 | 已归档的日报只追加不覆盖；原始记录永久保留 |
| 换个电脑或终端，记录就找不着了 | 全都存在你自己的 Markdown 文件里，随时可查可迁移 |

## 功能

- **零硬编码路径**：自动探测你的日报目录（环境变量 → 本地配置 → Obsidian 的 `daily-notes.json` → 常见位置扫描 → 兜底目录），换机器不用改配置
- **Obsidian 可选**：检测到 vault 就用 `frontmatter + [[wikilink]]` 归档；没有 Obsidian 就自动退化成普通 Markdown，**不会**往纯文本文件里塞 `[[ ]]`
- **两套输出格式**：给人看的纯文本日报（`【项目】`），和给 Obsidian 用的双链格式（`[[项目]]`），写入时自动转换
- **欠账检查**：忘了归档的日子，agent 靠文件证据查出来提醒你，而不是靠"我记得"
- **可选的外部台账同步**：想把日报同步到多维表格 / Notion / 内部系统？提供配置位和 8 条幂等性约束（默认关闭）
- **纯标准库**：唯一的脚本只用 Python 标准库，不装任何第三方包
- **不联网**：没有任何网络请求，不发送任何数据

## 安装

### 方式 1：npx（一行搞定）

```bash
npx github:JhinZhao/daily-report
```

默认装到 `~/.hermes/skills/daily-report`。想装到别处：

```bash
# 装到任意 agent 的 skills 目录
npx github:JhinZhao/daily-report --dir ~/.agents/skills/daily-report

# 已存在时覆盖
npx github:JhinZhao/daily-report --force

# 只看会装到哪里（不实际安装）
npx github:JhinZhao/daily-report --print-dir
```

> 需要 Node.js ≥ 16。npx 直接从 GitHub 取包并运行安装器，**不需要**先发布到 npm，也不需要 `npm install`。

### 方式 2：Hermes Agent

```bash
git clone https://github.com/JhinZhao/daily-report.git /tmp/daily-report-src
cp -r /tmp/daily-report-src/skills/daily-report ~/.hermes/skills/

# 验证
hermes skills list | grep daily-report
```

> 本 skill 被 Hermes 官方仓库收录后，可直接 `hermes skills install official/productivity/daily-report`。在那之前请用 npx（方式 1）或上面的 clone 方式。

### 方式 3：手动（任何 agent 框架）

1. 从 [Releases](https://github.com/JhinZhao/daily-report/releases) 下载 `daily-report-skill-v0.1.0.zip`，或 `git clone` 本仓库
2. 把 `skills/daily-report/` 整个目录复制到你 agent 的 skills 目录
3. 确认目标目录里有 `SKILL.md`

常见位置：Hermes 是 `~/.hermes/skills/`；项目级可用 `.hermes/skills/` 或 `.agents/skills/`；其他框架按各自文档。

## 快速开始

装完先让脚本探一下它会用哪个目录：

```bash
python3 ~/.hermes/skills/daily-report/scripts/resolve_daily_paths.py
```

输出示例：

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

- `mode: obsidian` → 归档会用 `[[双链]]`
- `mode: plain` → 普通 Markdown 目录，归档用 `## 项目名` 标题
- 结果不对 → 写个 `config.local.json`（见下方「配置」），或直接告诉 agent 你的目录在哪

## 使用说明

装好之后不用敲命令，直接跟 agent 说人话：

| 你说 | agent 做什么 | 会写文件吗 |
|---|---|---|
| `【记录】完成登录模块联调` | 追加到今天的记录文件 | ✅ 立刻 |
| `【待办】明天验证支付` | 记进"明日计划" | ✅ 立刻 |
| `下班` / `给我日报` | 整理成日报预览给你看 | ❌ 只看不写 |
| `归档` / `确认` | 写成正式日报 + 下班标记 | ✅ |
| `去掉【登录模块】那条` | 从那天的记录里删掉 | ✅ |
| `归档 3.5 和 3.6` | 两个日期分别归档 | ✅ |
| `我哪天没归档？` | 查文件证据，列出欠账 | ❌ |

### 一个完整的工作流

**早上开工**，你随手记：

```
你：【记录】完成不采用 AI 核查结果原因功能联调、测试、修复
    【记录】配合导出第二波测试数据
    【待办】明天验证交存平台

agent：✓ 已追加到 2025-03-05.md（共 3 条）
```

**下班前**：

```
你：下班

agent：
2025.3.5 日报

一、工作简要

【项目A】
1. 完成不采用 AI 核查结果原因功能联调、测试、修复
2. 配合导出第二波测试数据

二、存在问题
暂无

三、明日计划
1. 明天验证交存平台

（这只是预览，还没写文件。确认无误就说"归档"）
```

**你说"归档"**，agent 才会写正式日报 + 下班标记，并把记录整理成 Obsidian 双链格式。

### 日报格式

预览格式（给人看，纯文本，不用 Markdown 语法）：

```
2025.3.5 日报

一、工作简要

【项目A】
1. 第一条内容
2. 第二条内容

二、存在问题
暂无

三、明日计划
1. 待办一
```

归档格式（Obsidian 模式）：

```markdown
---
title: 工作日报 2025年3月5日
date: 2025-03-05
type: daily-report
projects:
  - "[[项目A]]"
tags: [project, work, daily-report]
---

## 一、工作简要

### [[项目A]]
1. 第一条内容

## 二、存在问题
暂无

## 三、明日计划
1. 待办一
```

## 配置

配置是可选的 —— 探测脚本会自动找你的日报目录。想固定下来就：

```bash
cp ~/.hermes/skills/daily-report/config.local.json.example \
   ~/.hermes/skills/daily-report/config.local.json
```

```json
{
  "daily_dir": "/absolute/path/to/your/daily-reports",
  "off_work_subdir": ".off-work",
  "obsidian_vault": null,
  "projects": {
    "平台别名": "项目A"
  },
  "external_sync": null
}
```

| 字段 | 说明 |
|---|---|
| `daily_dir` | 日报根目录（绝对路径）。设了就优先用它 |
| `off_work_subdir` | 下班标记目录名，默认 `.off-work` |
| `obsidian_vault` | vault 根目录；留 `null` 自动推断 |
| `projects` | 你说的别名 → 正式项目名 的映射 |
| `external_sync` | 外部台账同步配置，`null` = 关闭 |

> `config.local.json` 含你的本地路径，**不要提交到公开仓库**（本仓库 `.gitignore` 已排除它）。

也可以用环境变量：

```bash
export DAILY_REPORT_HOME="/path/to/日报"    # 直接指定日报目录
export OBSIDIAN_VAULT="/path/to/vault"      # 指定 vault 根目录
```

## 它是怎么找到你的日报目录的

`scripts/resolve_daily_paths.py` 按顺序尝试，第一个命中就停：

1. 环境变量 `DAILY_REPORT_HOME` / `OBSIDIAN_VAULT` / `DAILY_REPORT_VAULT`
2. `config.local.json` 里的 `daily_dir`
3. Obsidian vault 的 `.obsidian/daily-notes.json`（读你日记插件配的 `folder`）
4. 扫描常见位置：`~/Documents/Obsidian`、iCloud 的 Obsidian 容器、`~/Obsidian`、`~/vaults/*`
5. 在找到的 vault 里按目录名找候选（`日报` / `daily` / `dailies` / `journal`…），按"里面有多少个 `YYYY-MM-DD.md`"打分，选最像的那个
6. 全都没命中 → 兜底 `~/.local/share/daily-report`，并**明确告警**让 agent 找你确认

它每次都会报告 `source` 字段，告诉你结论是怎么来的 —— 没有黑盒。

## 常见问题

**没有 Obsidian，能用吗？**
能。会自动退化成普通 Markdown 模式：归档用 `## 项目名` 标题，不写 `[[ ]]`。

**会不会把我的日报覆盖掉？**
不会。已归档的日报只会**追加**，不会整体覆盖；写文件前先读文件判断状态。"下班"只说预览、不写文件。

**记录和正式日报是同一个文件吗？**
默认是。归档 = 把记录整理成正式日报格式写回当天文件，原始记录作为日志保留。

**支持 Windows 吗？**
支持。唯一的平台差异是取日期：POSIX 用 `date "+%Y-%m-%d"`，Windows 用 `Get-Date -Format "yyyy-MM-dd dddd"`，SKILL.md 里两种都写了。

**数据存哪儿？会上传吗？**
全部存在你自己的 Markdown 文件里。这个 skill **不发任何网络请求**，不上传任何数据。

**怎么卸载？**
删目录即可：`rm -rf ~/.hermes/skills/daily-report`。

**能改成英文触发词吗？**
能。触发词只是约定，编辑 `SKILL.md` 里的 Quick Reference 表即可（纯 Markdown）。

## 开发与测试

```bash
git clone https://github.com/JhinZhao/daily-report.git
cd daily-report
python3 -m pytest tests/ -q      # 9 passed
```

测试覆盖探测脚本的全部分支：vault 自动发现、`daily-notes.json` 配置优先、环境变量覆盖、配置文件覆盖、无 Obsidian 的降级与告警、配置损坏容错、CLI JSON 契约。**不联网**，用 `tmp_path` 造假 vault。

### 依赖

- Python ≥ 3.8（**仅标准库**，无第三方包）
- Node ≥ 16（**只**用于 npx 安装器；不用 npx 就完全不需要）
- 可选：Obsidian（没有也能用）

### 仓库结构

```
daily-report/
├── skills/daily-report/          # skill 本体（安装时复制的就是它）
│   ├── SKILL.md                  # agent 读的工作流定义
│   ├── scripts/                  # 目录探测脚本
│   ├── templates/                # 记录 / 预览 / 归档模板
│   ├── references/               # 踩坑复盘 + 语法速查
│   └── config.local.json.example
├── bin/install.js                # npx 安装器
├── tests/                        # pytest 用例
├── package.json
└── LICENSE
```

### 投稿 / 二次分发

本 skill 遵循 [Hermes Agent 的 in-repo skill 规范](https://github.com/NousResearch/hermes-agent)（frontmatter 字段、section 顺序、Hermes 工具引用、体积与测试要求）。投稿到官方仓库时：

1. 把 `skills/daily-report/` 放到 `optional-skills/productivity/daily-report/`
2. 把 `tests/test_daily_report_skill.py` 放到 `tests/skills/`
3. 确认 `related_skills` 引用的 skill 在目标分支存在（当前引用 `obsidian`、`weekly-review-planning`）

## 许可

**MIT** —— 你可以自由使用、复制、修改、合并、发布、分发、商用，**惟须保留版权声明与许可声明**（转载或分发时随附 `LICENSE` 即可）。软件按"原样"提供，不附带任何担保。

详见 [LICENSE](LICENSE)。
