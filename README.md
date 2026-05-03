<div align="center">

# dream-skill

**Two paired Claude Code skills for safe memory consolidation — read, reflect, then apply only what you check.**

[![License](https://img.shields.io/github/license/timoncool/dream-skill?style=flat-square)](LICENSE)
[![Stars](https://img.shields.io/github/stars/timoncool/dream-skill?style=flat-square)](https://github.com/timoncool/dream-skill/stargazers)
[![Last Commit](https://img.shields.io/github/last-commit/timoncool/dream-skill?style=flat-square)](https://github.com/timoncool/dream-skill/commits)

**[English](README.md)** · **[Русский](README_RU.md)**

</div>

---

`dream` walks your Claude Code memory directory, scattered notes and project READMEs, then synthesizes consolidation proposals into a dark-theme HTML report with checkboxes. `wake` reads your selection and applies only the items you explicitly checked — never modifies anything outside selected files, never uses `rm`. Inspired by the leaked autoDream from Claude Code internals, but with explicit human approval gate that the original lacks.

## Features

- **Read-only walk** — dream only writes the report files; can never modify memory or notes by accident
- **Reflective synthesis** — Phase Reflect surfaces patterns, drift, gaps, contradictions across files (extension over original autoDream)
- **HTML UI with checkboxes** — modern dark theme, action-coded colors (green/red/blue), file chips, filter pills, progress bar, keyboard shortcuts
- **Robust JSON-block contract** — proposals embedded as fenced JSON blocks in the report; wake parses with regex, immune to markdown formatting drift
- **9 action types** — `update` / `merge` / `delete` / `soft_delete` / `create_new` / `extract` / `remove_links` / `shorten_lines` / `add_links`
- **Append-only notes log** — survives context compaction; Phase Reflect reads from disk, not RAM
- **Win11 Git Bash aware** — handles `pwd -W` for slug computation, `cygpath` for Python paths
- **Safe by design** — `wake` only `mv` to `TRASH/` or `_archive/` (recoverable), never `rm`

## Quick Start

1. **Clone**
   ```bash
   git clone https://github.com/timoncool/dream-skill.git
   ```

2. **Install** (per-project recommended; global also works)
   ```bash
   cd <your-project>
   mkdir -p .claude/skills
   cp -r /path/to/dream-skill/dream .claude/skills/
   cp -r /path/to/dream-skill/wake .claude/skills/
   ```

3. **Run** (restart Claude Code first to load skills)
   ```
   поспи         # or "dream" / "consolidate memory"
   # ... open the HTML report, check boxes, hit Save choices ...
   проснулся    # or "wake" / "apply dream"
   ```

## Usage

### Dream — read & reflect

Trigger phrases (RU/EN): `поспи`, `сон`, `режим сна`, `dream`, `консолидируй память`, `разберись с памятью`, `audit memory`, `consolidate memory`, `synthesize`.

Output:
- `<cwd>/.dream-notes-<date>.md` — append-only log (per-file blocks, written incrementally)
- `<cwd>/.dream-payload-<date>.json` — input for `build_report.py`
- `<cwd>/DREAM-REPORT-<date>.md` — full audit trail with one fenced JSON block per proposal
- `<cwd>/DREAM-REPORT-<date>.html` — interactive UI

### HTML UI

Open the HTML in a browser:
- 🟢 **Constructive actions** (merge, create_new, extract) — green tint
- 🔴 **Destructive actions** (delete, soft_delete) — red tint
- 🔵 **Neutral actions** (update, index ops) — blue tint

Filter by category (M/N/I/O — memory/notes/index/other) or by action type. Click checkboxes, hit **💾 Save choices** — Chrome/Edge prompts for save location, Firefox/Safari downloads to `~/Downloads/`.

Keyboard: `Ctrl+A` select all · `Esc` deselect · `Ctrl+S` save.

### Wake — apply selected

Trigger: `проснулся`, `wake`, `apply dream`, `wake M1,M3,N2`, `wake all`.

Wake locates `DREAM-CHOICES-<date>.json` (cwd → `~/Downloads/` → `~/Desktop/`), parses report JSON blocks, shows summary, asks once for confirmation, then applies only checked items via `Edit`/`Write` and `mv` to `TRASH/`/`_archive/`. Appends a `## Wake log — <timestamp>` section to the report for audit trail.

## Architecture

```
dream/
├── SKILL.md                  # workflow + safety rules + path computation
├── references/
│   └── action_types.md       # JSON contract for 9 proposal action types
└── assets/
    ├── template.html         # dark-theme UI, no external deps (~480 lines)
    └── build_report.py       # payload JSON → MD + HTML, with validation

wake/
└── SKILL.md                  # discover choices, parse JSON blocks, summary gate, apply
```

### JSON-block contract

Each proposal in the MD report is a fenced JSON block. Wake parses these via Python regex — robust against any markdown formatting drift:

```json
{
  "id": "M1",
  "category": "memory",
  "action": "merge",
  "title": "Merge handoff_pikabu_*.md into project_pikabu_mcp.md",
  "rationale": "3 session handoffs accumulated, latest is canonical",
  "files": ["handoff_pikabu_2026_03_30.md", "handoff_pikabu_2026_04_01.md"],
  "target": "project_pikabu_mcp.md",
  "diff_preview": "Append session sections, then mv sources to TRASH/"
}
```

See [`dream/references/action_types.md`](dream/references/action_types.md) for full schema of all 9 action types.

## Safety guarantees

**dream** — only writes the four report files, nothing else:

- Read / Grep / Glob unrestricted
- Read-only Bash: `ls`, `find` (no `-delete`/`-exec`), `grep`, `cat`, `head`, `tail`, `wc`, `du`, `stat`, `python` (for build_report.py only)
- Write only: `<cwd>/.dream-notes-<date>.md`, `<cwd>/.dream-payload-<date>.json`, `<cwd>/DREAM-REPORT-<date>.md`, `<cwd>/DREAM-REPORT-<date>.html`
- No `rm`, `mv`, `cp`, redirect, `find -delete`, no Edit/Write outside report files

**wake** — restricted destructive ops:

- `Edit`/`Write` only in `<memory_dir>/` and explicitly-listed cwd notes from selected proposals
- `mv` only to `<memory_dir>/TRASH/` or `<cwd>/_archive/dream-applied-<date>/`
- No `rm` ever (always `mv` = recoverable)
- No work on items not in `selected`
- No project folder modifications

## Why this exists

The leaked Claude Code v2.1.88 has `autoDream` — a background memory consolidation pass. It runs autonomously every ~24 hours when enough sessions accumulate. The original suffers from [issue #38493](https://github.com/anthropics/claude-code/issues/38493): *"writes inaccurately named, factually unverified, impossible-to-audit memories"* — because no human reviews what gets merged or deleted.

`dream` + `wake` solve this with a hard split: dream is read-only and writes only the report; wake applies only what the human explicitly checked in the HTML UI. No autonomous mutations to memory ever.

## Inspired by

- **autoDream** from Claude Code v2.1.88 leak — `services/autoDream/consolidationPrompt.ts` (4-phase Orient → Gather → Consolidate → Prune)
- **createAutoMemCanUseTool** restrictions — `services/extractMemories/extractMemories.ts:171`
- **Memory taxonomy** (user/feedback/project/reference) and `WHAT_NOT_TO_SAVE` — `memdir/memoryTypes.ts`
- **MEMORY.md limits** (200 lines / 25KB) — `memdir/memdir.ts`
- **Plan-then-apply pattern** — `skills/bundled/remember.ts` ("present proposals, do NOT modify without approval")
- **Phase Reflect (synthesis over consolidation)** — Karpathy's [LLM Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) lint-pass idea

## Other Projects by [@timoncool](https://github.com/timoncool)

| Project | Description |
|---------|-------------|
| [telegram-api-mcp](https://github.com/timoncool/telegram-api-mcp) | Full Telegram Bot API as MCP server |
| [civitai-mcp-ultimate](https://github.com/timoncool/civitai-mcp-ultimate) | Civitai API as MCP server |
| [trail-spec](https://github.com/timoncool/trail-spec) | TRAIL — cross-MCP content tracking protocol |
| [ACE-Step Studio](https://github.com/timoncool/ACE-Step-Studio) | AI music studio — songs, vocals, covers, videos |
| [GitLife](https://github.com/timoncool/gitlife) | Your life in weeks — interactive calendar |
| [Bulka](https://github.com/timoncool/Bulka) | Live-coding music platform |
| [ScreenSavy.com](https://github.com/timoncool/ScreenSavy.com) | Ambient screen generator |

## Authors

- **Nerual Dreming** — [Telegram](https://t.me/nerual_dreming) | [neuro-cartel.com](https://neuro-cartel.com) | [ArtGeneration.me](https://artgeneration.me)

## Support the Author

I build open-source software and do AI research. Most of what I create is free and available to everyone. Your donations help me keep creating without worrying about where the next meal comes from =)

**[All donation methods](https://github.com/timoncool/ACE-Step-Studio/blob/master/DONATE.md)** | **[dalink.to/nerual_dreming](https://dalink.to/nerual_dreming)** | **[boosty.to/neuro_art](https://boosty.to/neuro_art)**

- **BTC:** `1E7dHL22RpyhJGVpcvKdbyZgksSYkYeEBC`
- **ETH (ERC20):** `0xb5db65adf478983186d4897ba92fe2c25c594a0c`
- **USDT (TRC20):** `TQST9Lp2TjK6FiVkn4fwfGUee7NmkxEE7C`

## Star History

<a href="https://www.star-history.com/?repos=timoncool%2Fdream-skill&type=date&legend=top-left">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=timoncool/dream-skill&type=date&theme=dark&legend=top-left" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=timoncool/dream-skill&type=date&legend=top-left" />
   <img alt="Star History Chart" src="https://api.star-history.com/svg?repos=timoncool/dream-skill&type=date&legend=top-left" />
 </picture>
</a>

## License

MIT
