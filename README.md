# daily-report — 通用日报工作流 skill

一个可移植的日报 skill：**记录 → 预览 → 确认 → 归档**，支持 Obsidian vault 和任意纯 Markdown 目录两种模式。

## 特性

- **零硬编码路径**：`scripts/resolve_daily_paths.py` 自动探测日报目录（环境变量 → 本地配置 → Obsidian `daily-notes.json` → 常见位置扫描 → 兜底目录）。
- **Obsidian 可选**：检测到 vault 就用 `frontmatter + [[wikilink]]` 归档；没有 Obsidian 就退化成普通 Markdown（不写 `[[ ]]`）。
- **日期安全**：强制取真实日期（`date` / `Get-Date`），附带日期错位的完整复盘。
- **不丢数据**：记录立即落盘；归档后保留原始记录；多会话冲突用 `read_file` + `patch` 而不是覆盖。
- **可扩展**：可选的外部台账同步（多维表格 / Airtable / Notion / 内部系统），附幂等与校验约束。

## 安装

Hermes Agent：

```bash
mkdir -p ~/.hermes/skills/daily-report
cp -r daily-report/. ~/.hermes/skills/daily-report/
```

其他 agent 框架：把 `daily-report/` 整个目录放到你的 skills 目录即可，`SKILL.md` 是入口。

## 快速开始

```bash
# 1. 看看日报被定位到哪个目录
python3 scripts/resolve_daily_paths.py

# 2. 结果不对？写个本地配置（不要提交）
cp config.local.json.example config.local.json
$EDITOR config.local.json     # 至少填 daily_dir
```

然后在会话里直接用：

- `【记录】完成 XX 功能联调` → 追加到当天记录
- `【待办】明天验证 XX` → 记入明日计划
- `下班` → 输出日报预览（不写文件）
- `归档` → 确认后写正式日报 + 下班标记

## 目录结构

```
daily-report/
├── SKILL.md                          # 主工作流（agent 入口）
├── README.md
├── LICENSE                           # MIT
├── config.local.json.example         # 配置模板
├── scripts/
│   └── resolve_daily_paths.py        # 目录探测，纯标准库
├── templates/
│   ├── daily-draft.md                # 记录文件模板
│   ├── report-plain.txt              # 纯文本日报模板
│   └── daily-archived.md             # 归档模板（Obsidian / plain）
├── tests/
│   └── test_daily_report_skill.py    # 探测脚本的测试
└── references/
    ├── syntax-and-integrations.md    # 短指令语法、git 整理、外部同步
    └── workflow-lessons.md           # 踩坑复盘
```

## 配置项（config.local.json）

| 字段 | 说明 |
|---|---|
| `daily_dir` | 日报根目录（绝对路径）。设了就优先用它 |
| `off_work_subdir` | 下班标记子目录名，默认 `.off-work` |
| `obsidian_vault` | vault 根目录；留 `null` 时自动推断 |
| `projects` | 项目别名 → 正式项目名 的映射 |
| `external_sync` | 外部台账同步配置，默认 `null`（关闭） |

## 测试

```bash
python3 -m pytest tests/ -q
```

只依赖 pytest（测试代码本身用 stdlib + `unittest.mock`，不联网）。覆盖：vault 自动探测、`daily-notes.json` 配置优先、环境变量覆盖、`config.local.json` 覆盖、无 Obsidian 的降级与告警、配置损坏容错、CLI JSON 契约。

## 发布前请填

包内的占位符已填为署名 `JhinZhao`。若你改用别的名字，需要同步这三处：

| 位置 | 当前值 | 说明 |
|---|---|---|
| `SKILL.md` frontmatter | `author: JhinZhao, Hermes Agent` | 官方规范要求人类贡献者排在 `Hermes Agent` 之前 |
| `LICENSE` | `Copyright (c) 2026 JhinZhao` | 版权行 |
| git commit 身份 | `JhinZhao <JhinZhao@users.noreply.github.com>` | 仓库局部配置，用 GitHub noreply 邮箱避免公开私人邮箱 |

## 投稿 Hermes 官方仓库

本包按官方 in-repo 标准（见 `hermes-agent-skill-authoring`）组织，投稿时：

1. skill 目录放 `optional-skills/productivity/daily-report/`（可选层：垂直场景，先进 optional 再谈 bundled）。
2. 测试文件移到仓库的 `tests/skills/test_daily_report_skill.py`。
3. 跑 `python website/scripts/generate-skill-docs.py` 生成文档页，注意只提交自己那一页 + catalog 一行 + `website/sidebars.ts` 一行，其余 `git checkout --` 掉。
4. frontmatter 里 `related_skills` 引用了 `obsidian` 和 `weekly-review-planning`，投稿前确认二者在目标分支存在。
5. 平台声明：`platforms: [linux, macos, windows]`；Windows 的日期命令差异已写进 Pitfalls。

## 设计取舍

- **预览用 `【项目】`，归档用 `[[项目]]`**：两种输出面向不同读者（人 vs Obsidian 双链），写入时转换。
- **"下班"不等于"归档"**：生成预览是零副作用的操作，写文件必须显式确认。
- **记录文件永不删除**：它是跨设备、跨会话唯一的追溯来源。
- **外部同步默认关闭**：不同人的台账系统差别太大，本 skill 只提供约束和检查清单，不内置具体平台 SDK。

## 隐私

本包不含任何个人路径、账号、凭据或真实项目名；示例中的"项目A/项目B"、路径、ID 均为占位符。使用时请把 `config.local.json` 加入 `.gitignore`，不要提交。

## License

**MIT** — 见 `LICENSE`。

可以任意使用、复制、修改、合并、发布、分发、再许可、销售，包括商用；**惟须保留版权声明与许可声明**（转载或分发时随附 `LICENSE` 即可）。软件按"原样"提供，不附带任何担保。
