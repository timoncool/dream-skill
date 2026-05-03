# dream + wake — Claude Code memory skills

Two paired Claude Code skills for **safe memory consolidation** with explicit human approval via HTML checkboxes.

Inspired by the leaked `autoDream` from Claude Code internals (`services/autoDream/consolidationPrompt.ts`), but with two key differences:

1. **Plan-then-apply gate** — original autoDream applies autonomously (issue [#38493](https://github.com/anthropics/claude-code/issues/38493): "writes inaccurately named, factually unverified, impossible-to-audit memories"). This split forces explicit human review.
2. **Extended scope** — reads memory dir + scattered cwd notes + project READMEs + global `~/.claude/CLAUDE.md` (autoDream covers only memory dir).

## What it does

**`dream`** (read-only):
- Walks memory dir (`~/.claude/projects/<slug>/memory/`), cwd notes, project READMEs, optionally JSONL transcripts
- Synthesizes patterns / drift / connections / gaps / insights (Phase Reflect — extension over original autoDream)
- Produces two artifacts: `DREAM-REPORT-<date>.md` (audit trail with JSON-block proposals) + `DREAM-REPORT-<date>.html` (modern dark-theme UI with checkboxes)
- **Never modifies anything except writing the report files**

**`wake`** (destructive):
- Reads `DREAM-CHOICES-<date>.json` (saved from HTML) or accepts `wake M1,M3,N2` / `wake all` args
- Parses fenced JSON blocks from the report (robust contract, not markdown headings)
- Shows summary, asks once for confirmation
- Applies only the selected items via `Edit`/`Write` in memory dir + `mv` to TRASH/`_archive` (never `rm`)
- Appends `## Wake log — <timestamp>` audit section to the report

## Install

```bash
# Per-project (recommended)
cd <your-project>
mkdir -p .claude/skills
git clone https://github.com/<you>/dream-skill /tmp/dream-skill
cp -r /tmp/dream-skill/dream .claude/skills/
cp -r /tmp/dream-skill/wake .claude/skills/

# Or globally for all sessions
mkdir -p ~/.claude/skills
cp -r dream wake ~/.claude/skills/
```

Restart Claude Code to load the skills.

## Usage

### 1. Run dream
```
поспи     # or "dream", "консолидируй память", "разберись с памятью"
```

The skill walks memory + notes + projects, builds a notes log (`<cwd>/.dream-notes-<date>.md`), synthesizes insights, then writes:
- `DREAM-REPORT-<date>.md` — full audit trail with one JSON block per proposal
- `DREAM-REPORT-<date>.html` — interactive UI (dark theme, action-coded colors, file chips, filter pills, progress bar, keyboard shortcuts)

### 2. Open HTML, pick what to apply

```
start DREAM-REPORT-<date>.html       # Windows
open DREAM-REPORT-<date>.html        # macOS
xdg-open DREAM-REPORT-<date>.html    # Linux
```

In the UI:
- 🟢 **Constructive actions** (merge / create_new / extract) — green tint
- 🔴 **Destructive actions** (delete / soft_delete) — red tint
- 🔵 **Neutral actions** (update / index ops) — blue tint

Filter by category (M/N/I/O) or by action type. Click checkboxes, hit **💾 Save choices** — Chrome/Edge prompts for save location, Firefox/Safari downloads to `~/Downloads/`.

Keyboard: `Ctrl+A` select all, `Esc` deselect, `Ctrl+S` save.

### 3. Run wake
```
проснулся    # or "wake", "apply dream"
# или с явными ID:
wake M1,M3,N2
wake all
```

Wake finds `DREAM-CHOICES-<date>.json`, parses report, shows summary, asks for confirmation, then applies only checked items.

## Architecture

```
dream/
├── SKILL.md                     — workflow + safety rules + path computation
├── references/
│   └── action_types.md          — JSON contract for proposals (9 action types)
└── assets/
    ├── template.html            — modern dark-theme UI (~480 lines, no deps)
    └── build_report.py          — payload JSON → MD + HTML (with validation)

wake/
└── SKILL.md                     — read choices, parse JSON blocks, summary gate, apply
```

### JSON-block contract

Each proposal in `DREAM-REPORT-<date>.md` is a fenced `\`\`\`json` block. Wake parses these via Python regex (not markdown headings — robust against formatting drift):

```json
{
  "id": "M1",
  "category": "memory",
  "action": "merge",
  "title": "...",
  "rationale": "...",
  "files": ["a.md", "b.md"],
  "target": "merged.md",
  "diff_preview": "..."
}
```

9 action types: `update`, `merge`, `delete`, `soft_delete`, `create_new`, `extract`, `remove_links`, `shorten_lines`, `add_links` — see [`dream/references/action_types.md`](dream/references/action_types.md).

## Safety guarantees

**dream** — single Write-allowed location pattern (literally only writes the report files):
- ✅ Read / Grep / Glob unrestricted
- ✅ Read-only Bash (`ls`, `find` without `-delete`/`-exec`, `grep`, `cat`, etc)
- ✅ Write only `<cwd>/.dream-notes-<date>.md`, `<cwd>/.dream-payload-<date>.json`, `<cwd>/DREAM-REPORT-<date>.md`, `<cwd>/DREAM-REPORT-<date>.html`
- ❌ No `rm`, `mv`, `cp`, redirect, `find -delete`, no Edit/Write outside report files

**wake** — restricted destructive ops:
- ✅ `Edit`/`Write` only in `<memory_dir>/` and explicitly-listed cwd notes from selected proposals
- ✅ `mv` only into `<memory_dir>/TRASH/` or `<cwd>/_archive/dream-applied-<date>/`
- ❌ No `rm` ever (always mv = recoverable)
- ❌ No work on items not in `selected`
- ❌ No project folder modifications (`.git`, `package.json` etc)

## Inspired by / based on

- **autoDream** from Claude Code v2.1.88 leak — `services/autoDream/consolidationPrompt.ts` (4-phase Orient → Gather → Consolidate → Prune)
- **createAutoMemCanUseTool** restrictions — `services/extractMemories/extractMemories.ts:171`
- **Memory taxonomy** (user/feedback/project/reference) and `WHAT_NOT_TO_SAVE` — `memdir/memoryTypes.ts`
- **MEMORY.md limits** (200 lines / 25KB) — `memdir/memdir.ts`
- **Plan-then-apply pattern** — `skills/bundled/remember.ts` ("present proposals, do NOT modify without approval")
- **Phase Reflect (synthesis over consolidation)** — Karpathy's [LLM Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) "lint pass" idea

## License

MIT
