---
name: daily-report
description: "记录工作项、生成日报预览并归档到 Markdown 目录。"
version: 0.1.0
author: JhinZhao, Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [Daily-Report, Obsidian, Journaling, Workflow, Markdown]
    related_skills: [obsidian, weekly-review-planning]
---

# Daily Report Skill

把一天的工作项记录成一天一个 Markdown 文件，生成日报预览给用户确认，然后归档为正式日报（Obsidian 双链格式或普通 Markdown）。日报目录靠探测脚本定位，Obsidian 可选。

它不生成周报/月报（那是 `weekly-review-planning` 的活），也不处理报销——报销是独立流程。除一个纯标准库的 Python 探测脚本外无外部依赖。

## When to Use

- 用户说【记录】/【待办】——把工作项落到当天的记录文件
- 用户说"下班"/"给我日报"——整理出日报预览
- 用户说"归档"/"确认"/"用这个"——写正式日报
- 用户问"我哪天归没归档"/"看看 X 日的日报"——查文件状态
- 用户贴 git log 或聊天记录，要求整理成日报

**Don't use for:** 报销流程（独立工作流）；周报/月报生成（用 `weekly-review-planning`）；纯笔记整理（用 `obsidian`）。

## Prerequisites

- `python3` ≥ 3.8（探测脚本只用标准库）
- **日报目录**：由探测脚本或 `config.local.json` 决定，不需要预先写死路径
- **可选** Obsidian vault（检测不到就退化为普通 Markdown 模式）
- **可选** 外部台账同步（多维表格 / Notion 等），默认关闭，见 `references/syntax-and-integrations.md`

## How to Run

```python
# 1) 每个会话第一次处理日报时，定位日报目录
terminal(command="python3 scripts/resolve_daily_paths.py --json")

# 2) 任何日期判断之前，取真实日期（第一步，没有例外）
terminal(command='date "+%Y-%m-%d %A"')

# 3) 之后按 Procedure 走，文件读写一律用 Hermes 工具：
#    read_file / write_file / patch / search_files
```

Windows 上没有 POSIX `date` 时改用：

```python
terminal(command='Get-Date -Format "yyyy-MM-dd dddd"')
```

## Quick Reference

| 用户说法 | 动作 | 写文件？ |
|---|---|---|
| 【记录】xxx | 追加到当天记录文件 | 立即 |
| 【待办】xxx | 记入"明日计划" | 立即 |
| 下班 / 给我日报 | 输出日报预览 | 否 |
| 归档 / 确认 / 用这个 | 写正式日报 + 下班标记（+ 可选同步） | 是 |
| 去掉【xxx】 / X 改为 Y | 删除或替换条目 | 是 |
| 看日报 / 查 X 日 | 读文件后回答 | 否 |
| 【报销】xxx | **不属于本 skill** | — |

## Procedure

### Step 0 — 环境探测

运行 `scripts/resolve_daily_paths.py --json`，读返回的 `mode` / `vault` / `daily_dir` / `off_work_dir` / `source` / `warnings`。

- `warnings` 非空 → 先把内容转述给用户确认，再继续
- `mode=obsidian` → 归档用 frontmatter + `[[wikilink]]`
- `mode=plain` → 该目录不在 vault 内：**不要写 `[[ ]]`**，改用 `## 项目名` 标题
- `source=fallback` 或探测结果不可信 → **问用户**"日报存在哪个目录？"，把答案写进 `config.local.json`

完成标准：已知 `daily_dir` 的绝对路径，且 `mode` 已确定。

探测顺序（脚本自动执行，排障时按此人工核对）：环境变量 `DAILY_REPORT_HOME` / `OBSIDIAN_VAULT` → `config.local.json` → vault 的 `.obsidian/daily-notes.json`（`folder` 字段）→ 常见位置扫描（`~/Documents/Obsidian`、iCloud Obsidian 容器、`~/Obsidian`、`~/vaults/*`）→ 目录名候选按"含多少 `YYYY-MM-DD.md`"打分 → 兜底 `~/.local/share/daily-report`。

### Step 1 — 记录（【记录】/【待办】）

1. `terminal(command='date "+%Y-%m-%d"')` 取当天日期。自己判断归属日，不要问用户"算哪天"。
2. `search_files(pattern='YYYY-MM-DD.md', target='files', path='<daily_dir>')` 看当天文件在不在。
3. 不存在 → 用 `write_file` 新建，首行固定 `# YYYY-MM-DD 记录草稿`（模板 `templates/daily-draft.md`）。
4. 追加条目 `- 【项目】内容`：**用 `patch` 追加，不要 `write_file` 覆盖**；多会话环境下先 `read_file` 读最新内容再追加。
5. `read_file` 回读确认条目已写入。

完成标准：当天的记录文件里能看到刚追加的条目，且其它日期的文件未被改动。

### Step 2 — 生成日报预览（"下班"）

1. `date` 确认日期 → `read_file` 当天记录文件。
2. 只整理**当天**的条目，按 Output Formats 的纯文本格式输出预览。
3. **不写任何文件**：不建下班标记、不写正式日报、不同步外部台账。

完成标准：用户看到了预览；磁盘上除原始记录外没有新增任何文件。

### Step 3 — 归档（"归档"）

按顺序执行，一步都不能跳：

1. `date` 确认日期；`search_files` 确认当天文件状态。
2. `read_file(path='<daily_dir>/<日期>.md', limit=5)` 判断状态：
   - 首行 `# YYYY-MM-DD 记录草稿` → 草稿态，整理后写回
   - 首行 `---`（frontmatter）→ **已归档，不要 `write_file` 覆盖**；用 `patch` 在对应板块追加条目并更新 `updated` 字段
3. **先给用户看归档后的样子**，用户确认后才落盘。
4. 写入正式日报（格式见 Output Formats）。
5. 保留原始记录作为日志（不要删）。
6. 创建下班标记：`write_file(path='<off_work_dir>/<日期>.md')`。
7. 配置了 `external_sync` 时执行同步；**任何一步失败都要如实告知用户，不能报"归档完成"**。

完成标准：正式日报已写入且格式正确；原始记录仍在；下班标记存在；外部同步（若启用）成功或失败已被明确报告。归档前若怀疑其它会话同时改过同一文件，先 `read_file` 合并再写。

### Step 4 — 欠账检查

用户问"归没归档"时，用证据回答，不要凭会话记忆：

```python
terminal(command='date "+%Y-%m-%d %A"')
search_files(pattern='*.md', target='files', path='<daily_dir>', order='modified', limit=8)  # 最近动过的文件
search_files(pattern='*.md', target='files', path='<off_work_dir>', limit=5)                # 真归档过的日子
read_file(path='<daily_dir>/<某日期>.md', limit=1)                                           # 首行是不是"记录草稿"
```

三条证据都对上再报状态。攒着没归档的日期主动列成表格提醒用户。

完成标准：状态结论有文件证据支撑，而不是"我记得"。

## Output Formats

### 预览版（纯文本，给用户看）

```
2025.3.5 日报

一、工作简要

【项目A】
1. 第一条内容
2. 第二条内容

【项目B】
1. 第一条内容

二、存在问题
暂无

三、明日计划
1. 待办一
```

铁律：序号必须给（只有一条也写 `1.`）；`【项目名】` 后不空行；一、二、三 板块之间要空行；不用 markdown 语法（无 `##`/`**`/`-`）；日期格式 `2025.3.5`；"存在问题"是强制板块，没有也写"暂无"。

### 归档版（Obsidian，`mode=obsidian`）

见 `templates/daily-archived.md`。要点：frontmatter 含 `title` / `date` / `created` / `updated` / `type: daily-report` / `projects`（`[[wikilink]]`）/ `tags`；正文用 `### [[项目A]]` 作分类标题，**项目标题下不再重复项目名前缀**。

### 归档版（普通 Markdown，`mode=plain`）

同 Obsidian 版，但 `### [[项目A]]` → `### 项目A`，frontmatter 的 `projects` 用纯字符串列表。**没有 Obsidian 就不要写 `[[ ]]`**——那是纯文本，只会污染文件。

预览用 `【项目】`、归档用 `[[项目]]`，写入时做格式转换。项目名由用户在 `config.local.json` 的 `projects` 里定义；跨项目会议统一归"会议"，杂项归"其他"；有歧义时问一句，不要自己发明新项目名。

## Pitfalls

- **不要擅自归档**：用户没说"归档"就永远不写正式日报。
- **不要凭空补内容**：草稿/归档只用用户实际说过的条目。绝不合并前几天内容、不按印象补全。用户强调"只要今天的"时，立刻回头核对当天文件。
- **不要把基建工作塞进日报**：维护 agent 能力、调试工具链路这类工作，用户没主动【记录】就不加。判断标准：**用户能不能向上汇报**。
- **不要漏"存在问题"**：没有也写"暂无"。
- **不要跨天**：写文件前一律 `date` + `search_files` + `read_file` 确认目标文件是当天的、是草稿态还是已归档态。
- **不要 `write_file` 覆盖已归档日报**：会丢 frontmatter 和已有板块，只能 `patch` 追加。
- **不要删记录文件**：归档后原始记录作为日志保留。
- **不要在会话内存里重建历史记录**：一律 `read_file` 从文件读。文件是跨会话、跨设备唯一的真相。
- **不要用裸 `ls` / `grep` / `head`**：列目录用 `search_files(target='files')`，读文件用 `read_file`，检索用 `search_files`。
- **周报/月报 ≠ 日报**：周报从日报目录读各天日报整理，别把日报草稿当周报归档；同步外部台账的一般只有日报。
- **周末/节假日没记录是正常的**：不要为了"补齐"而反推，除非用户明确说"反推"。
- **Windows 上 `date "+%Y-%m-%d"` 不可用**：改用 `Get-Date -Format "yyyy-MM-dd dddd"`；其余流程（pathlib + Hermes 工具）跨平台。

## Verification

- [ ] `resolve_daily_paths.py --json` 的 `daily_dir` 与用户认知一致（有疑问已确认过）
- [ ] 每条【记录】都能在当天的记录文件里读到，且没有污染其它日期
- [ ] "下班"之后磁盘上没有新增正式日报或下班标记
- [ ] 归档后：正式日报格式正确（板块齐全、frontmatter 完整）、原始记录仍在、下班标记存在
- [ ] 给已归档日报追加内容时，原有 frontmatter 与板块没有丢失
- [ ] 用户问"归没归档"时，结论由文件证据支撑
- [ ] 启用了外部同步时，成功或失败被如实报告

## 支持文件

- `scripts/resolve_daily_paths.py` — 目录探测，纯标准库
- `templates/daily-draft.md` / `report-plain.txt` / `daily-archived.md` — 三类模板
- `references/syntax-and-integrations.md` — 短指令语法、git 记录整理、外部台账同步
- `references/workflow-lessons.md` — 踩坑复盘（日期错位、跨会话丢数据、覆盖丢内容…）
