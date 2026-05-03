---
name: wake
description: Применяет выбранные user'ом изменения из dream report. Парт 2 после skill `dream` — читает `DREAM-CHOICES-<date>.json` (созданный из HTML отчёта галочками) или ID в args (`wake M1,M3,N2` или `wake all`), парсит JSON-блоки в `DREAM-REPORT-<date>.md`, применяет ТОЛЬКО выбранные через Edit/Write в memory dir и согласованные cwd notes. Use whenever the user wants to "проснулся", "wake", "wake up", "проснись", "примени dream", "apply dream", "выполни dream", "сделай выбранное", "execute report", or after running `dream` skill. Это деструктивная часть — изменяет файлы, в отличие от dream который только читает. Никогда не запускается без явного выбора пользователя (через DREAM-CHOICES JSON или ID в args).
---

# Wake — применение выбранного из dream

После того как `dream` сделал отчёт и пользователь отметил галочками — `wake` подхватывает выбор и применяет.

## Принцип безопасности

`wake` **НИКОГДА** не изобретает что применять. Источники выбора (по приоритету):

1. **JSON файл** `DREAM-CHOICES-<date>.json` (из HTML кнопкой Save)
2. **Аргументы skill'а** — `wake M1,M3,N2` или `wake all`

Если ни один не задан — спрашивает пользователя что выбрать, не делает ничего.

## Workflow

### Phase 1 — Lock + найти отчёт и выбор

**Сначала lock против race** (как в dream/SKILL.md Phase 0). Если две сессии одновременно запустят wake на одном отчёте — Edit'ы перезатрут друг друга, MEMORY.md превратится в кашу.

```bash
LOCK_DIR="$CWD_BASH/.wake-lock"
if mkdir "$LOCK_DIR" 2>/dev/null; then
  echo $$ > "$LOCK_DIR/pid"
else
  LOCK_AGE=$(( $(date +%s) - $(stat -c %Y "$LOCK_DIR" 2>/dev/null || stat -f %m "$LOCK_DIR") ))
  if [ "$LOCK_AGE" -gt 3600 ]; then
    rm -rf "$LOCK_DIR" && mkdir "$LOCK_DIR" && echo $$ > "$LOCK_DIR/pid"
  else
    echo "WAKE ALREADY RUNNING (lock age ${LOCK_AGE}s) — abort"
    exit 0
  fi
fi
# В финале Phase 5: rm -rf "$LOCK_DIR"
```

**Сначала вычислить пути** (как в dream/SKILL.md — `_BASH` для bash команд, `_WIN` для Python):

```bash
# Compute paths (Win11 Git Bash)
CWD_BASH=$(pwd)                                    # /d/Projects/TEMP
CWD_WIN=$(pwd -W 2>/dev/null || pwd)               # D:/Projects/TEMP (на не-Windows fallback)
SLUG=$(echo "$CWD_WIN" | sed 's|[:/]|-|g')         # D--Projects-TEMP

MEMORY_DIR_BASH="$HOME/.claude/projects/$SLUG/memory"
MEMORY_DIR_WIN=$(cygpath -w "$MEMORY_DIR_BASH" 2>/dev/null | sed 's|\\|/|g' || echo "$MEMORY_DIR_BASH")

test -d "$MEMORY_DIR_BASH" && echo "OK $MEMORY_DIR_WIN" || { echo "MEMORY DIR NOT FOUND — wake cannot proceed without it"; }

# 1. Find latest dream report MD in cwd
LATEST_REPORT=$(ls "$CWD_BASH"/DREAM-REPORT-*.md 2>/dev/null | sort -r | head -1)
if [ -z "$LATEST_REPORT" ]; then
  echo "NO REPORT FOUND — run dream skill first to generate DREAM-REPORT-<date>.md"
  # Don't exit — Claude reads this output and stops the workflow itself
else
  echo "Report: $LATEST_REPORT"
fi

# Extract date from filename: DREAM-REPORT-2026-05-02.md → 2026-05-02
REPORT_DATE=$(basename "$LATEST_REPORT" | sed 's|DREAM-REPORT-||; s|\.md||')

# 2. Find choices JSON (priority: cwd → ~/Downloads/ → ~/Desktop/)
CHOICES=""
for path in "$CWD_BASH/DREAM-CHOICES-$REPORT_DATE.json" "$HOME/Downloads/DREAM-CHOICES-$REPORT_DATE.json" "$HOME/Desktop/DREAM-CHOICES-$REPORT_DATE.json"; do
  if [ -f "$path" ]; then CHOICES="$path"; break; fi
done

# Fallback: latest CHOICES regardless of date
if [ -z "$CHOICES" ]; then
  CHOICES=$(ls -t "$HOME/Downloads/DREAM-CHOICES-"*.json "$CWD_BASH/DREAM-CHOICES-"*.json 2>/dev/null | head -1)
fi
echo "Choices: ${CHOICES:-NOT FOUND}"
```

**Date verify:** если `report_date` в JSON ≠ дата из имени MD-файла → WARN, спроси пользователя:

> ⚠️ Дата в DREAM-CHOICES (2026-05-01) не совпадает с последним DREAM-REPORT (2026-05-02). Использовать всё равно или прервать? (apply/cancel)

Если нет ни args, ни JSON:
> Не нашёл `DREAM-CHOICES-*.json` и нет ID в аргументах. Варианты:
> 1. Открой HTML отчёт `DREAM-REPORT-<date>.html`, отметь галочки, нажми 💾 Save choices
> 2. Или дай ID в чате: `wake M1,M3,N2` или `wake all`

### Phase 2 — Read report + parse JSON blocks

Read `DREAM-REPORT-<date>.md` целиком. JSON contract proposals — см. `D:/Projects/TEMP/.claude/skills/dream/references/action_types.md`.

**Парсинг (надёжный contract):** ищи fenced code blocks с языком `json`. Каждый — отдельный proposal.

**Используй Python для парсинга** (надёжнее awk с backticks через shells):

```python
import re, json, sys
content = open(report_path, encoding='utf-8').read()
# Pattern: triple-backtick + json + newline + content + newline + triple-backtick
pattern = r'```json\n(.*?)\n```'
blocks = re.findall(pattern, content, re.DOTALL)
proposals = []
malformed_indices = []
for i, block in enumerate(blocks):
    try:
        proposals.append(json.loads(block))
    except json.JSONDecodeError as e:
        print(f"WARN: malformed JSON block #{i}: {e}", file=sys.stderr)
        malformed_indices.append(i)
        # Add to failed[] later — record block index for the apply log
```

Получишь массив объектов с обязательными полями:
- `id` (string, например "M1")
- `category` ("memory" | "notes" | "index" | "other")
- `action` (один из: update, merge, delete, soft_delete, create_new, extract, remove_links, shorten_lines, add_links, purge_trash)
- Action-specific поля (см. dream/SKILL.md секцию "Action types")

Построй map `{id: proposal}`.

**Read selected:**
- Если есть JSON файл → `selected = json.selected` (массив ID)
- Если args = `all` → `selected = все ID из map`
- Если args = `M1,M3,N2` → split по запятой (trim spaces)

Verify: каждый ID в `selected` есть в map. Если нет — warn, пропусти, добавь в "skipped".

### Phase 3 — Confirm summary (один gate)

Покажи в чат:

> 🌅 Wake готов применить **N items** из dream report `<date>`:
>
> **Memory consolidation:**
> - M1. Merge handoff_pikabu_* → project_pikabu_mcp.md (3 source files)
> - M3. Soft-delete TRASH/* (старше месяца)
>
> **Notes integration:**
> - N2. Извлечь runware audit → reference_runware_audit_2026_04.md
>
> **Index rebuild:**
> - I1. Remove dead links: 4 ссылки
>
> Skipped (нет в отчёте): <list если есть>
>
> Применить? Скажи "да" / "go" / "apply". Откажешься — "stop" / "отмена".

Жди подтверждения. Это финальный gate — после него apply без вопросов.

Почему один gate а не каждый item: пользователь уже подумал галочками. Дополнительный approve раздражает. Но summary важен — могло измениться что-то с момента dream.

### Phase 4 — Apply (по подтверждению)

**Cross-project resolution (global mode).** Если proposal имеет поле `project: <slug>` — target memory dir = `~/.claude/projects/<slug>/memory/`, не текущий `$MEMORY_DIR_BASH`. Если поля нет (default mode) — используй `$MEMORY_DIR_BASH`.

```python
def resolve_memory_dir(proposal, default_dir):
    proj = proposal.get('project')
    if proj:
        return os.path.expanduser(f'~/.claude/projects/{proj}/memory')
    return default_dir
```

**Verify cross-project access:** для каждого уникального `project` в selected — проверь `os.path.isdir(target_dir)` до начала apply'а. Если нет → fail весь cross-project item с reason "memory dir not found for project=<slug>".

**Подготовь dest директории один раз перед началом:**

```bash
mkdir -p "$MEMORY_DIR_BASH/TRASH"
mkdir -p "$CWD_BASH/_archive/dream-applied-$REPORT_DATE"
mkdir -p "$CWD_BASH/_archive/trash-purged-$REPORT_DATE"   # для purge_trash items
# Per-project TRASH dirs создавай on-demand при apply (не все проекты в selected)
```

Для каждого item в `selected`, в порядке Apply order recommendation из MD-отчёта (по умолчанию M → N → I → O):

#### action: update
- Read `target` файл
- `diff_preview` — natural-language описание изменения (например "Append section '## Session 04-01' к существующему контенту"). Это не структурированный diff.
- **Best-effort applicability check:** если `diff_preview` упоминает конкретные substring (`'## Session 04-01'`, `'feedback_X.md'`, etc) — substring check `if substring in current_content`. Если упомянутая substring явно должна быть в файле но нет → fail с reason "target content drifted: '<missing snippet>' not found"
- Если уверен что изменение применимо — Edit. Если непонятно как именно изменить (расплывчатый diff_preview) — fail с reason "diff_preview too vague to apply automatically", добавь в `failed[]`.

#### action: merge
- Read все `files`, Read `target` (если existing)
- Build merged content: existing target + sections из source files
- Write в `target`
- Для каждого source: `mv "$MEMORY_DIR_BASH/<source>" "$MEMORY_DIR_BASH/TRASH/"`

#### action: delete
- Edit `target` для очистки контента (оставить frontmatter с заметкой `<!-- deleted YYYY-MM-DD by wake -->`)

#### action: soft_delete
- Для каждого file в `files`: `mv "$MEMORY_DIR_BASH/<file>" "$MEMORY_DIR_BASH/TRASH/"`

#### action: create_new
- Write `target` с frontmatter (type из proposal) + `content_template`

#### action: extract (notes)
- Read `source_note` из cwd
- Read `target_memory_file` (если existing) или подготовить с frontmatter
- Edit/Write target с добавлением `what_to_extract` секции
- Source action:
  - `keep` — ничего не делать с source
  - `delete` — `mv "$CWD_BASH/<source_note>" "$CWD_BASH/_archive/dream-applied-$REPORT_DATE/"`
  - `move-to-archive` — то же самое, mv

#### action: remove_links
- Read `MEMORY.md`
- Для каждой substring в `links_to_remove`:
  - Найти строку(и) где встречается substring
  - Удалить целиком всю строку (не только substring)
- Edit `MEMORY.md` с обновлённым содержимым
- Если substring не найдена ни в одной строке → log warning "link not found in MEMORY.md: <substring>", продолжай (не fail весь item)

#### action: shorten_lines
- Read `MEMORY.md`
- Для каждого объекта `{original, replacement}` в `lines_to_shorten`:
  - Substring check: `original` должна быть в content
  - Edit: заменить `original` → `replacement`
- Если original не найден → warning, skip этот item, продолжай

#### action: add_links
- Read `MEMORY.md`
- Для каждого `{section, line}` в `links_to_add`:
  - Найти строку с `section` (точный markdown заголовок)
  - Вставить `line` непосредственно после строки заголовка
- Edit `MEMORY.md`
- Если `section` не найден → warning, skip, продолжай

#### action: purge_trash (второй уровень корзины)
- Для каждого file в `files`:
  - Source: `$MEMORY_DIR_BASH/TRASH/<file>`
  - Dest:   `$CWD_BASH/_archive/trash-purged-$REPORT_DATE/<file>`
  - Если source не существует (юзер уже грохнул руками) → warning, skip, продолжай
  - Если в dest уже есть файл с таким именем → переименовать dest как `<file>.<unix_ts>` (избежать перезаписи)
  - `mv "$MEMORY_DIR_BASH/TRASH/<file>" "$CWD_BASH/_archive/trash-purged-$REPORT_DATE/<file>"`
- **Никогда `rm`** — даже здесь. Файлы доезжают до `_archive/`, юзер сам решает когда финально удалить.

После каждого item — короткий лог в чат: `✓ M1 applied (3 files merged → project_pikabu_mcp.md)`.

При ошибке (Read failed, Edit conflict, file missing) — НЕ останавливайся, добавь в `failed[]` с reason, продолжи.

### Phase 5 — Verify and report

```bash
echo "=== Memory dir state ==="
wc -l "$MEMORY_DIR_BASH/MEMORY.md"
ls "$MEMORY_DIR"/*.md | wc -l
ls "$MEMORY_DIR_BASH/TRASH/" 2>/dev/null | wc -l

# Broken link check in MEMORY.md (через Python — надёжнее с пробелами в путях)
python -c "
import re, os
content = open(r'$MEMORY_DIR_BASH/MEMORY.md', encoding='utf-8').read()
links = re.findall(r'\(([^)]+\.md)\)', content)
for link in links:
    full = os.path.join(r'$MEMORY_DIR', link)
    if not os.path.isfile(full):
        print(f'BROKEN: {link}')
"
```

Если есть BROKEN — добавь финальный auto-fix: Edit MEMORY.md, удалить broken links, сообщи user.

**MEMORY.md лимит check:** если `wc -l` > 200 после apply — warn user'у "MEMORY.md превысил лимит после apply, рекомендую запустить dream ещё раз для prune".

**Финальный отчёт в чат:**

```
✅ Wake завершил.
Applied: N items (M: K, N: L, I: M, O: P)
Failed: <list with reasons or "none">
Skipped: <list или "none">
Memory dir: X → Y файлов, MEMORY.md: A → B строк
Choices: <path JSON> (можно архивировать)
```

**Release lock** в самом конце (после написания audit log в отчёт):

```bash
rm -rf "$CWD_BASH/.wake-lock"
```

**Audit trail в MD-отчёте:** добавить новую секцию в КОНЕЦ `DREAM-REPORT-<date>.md`.

Реализация (Edit не подходит — нужен append, Write перезапишет — нужна композиция):

```python
import sys
report_path = sys.argv[1]
log_block = """
## Wake log — """ + iso_timestamp + """
Applied: """ + ", ".join(applied_ids) + """
Failed:
""" + "\n".join(f"- {fid}: {reason}" for fid, reason in failed) + """
Skipped:
""" + "\n".join(f"- {sid}: {reason}" for sid, reason in skipped) + """
"""
existing = open(report_path, encoding='utf-8').read()
open(report_path, 'w', encoding='utf-8').write(existing.rstrip() + "\n" + log_block + "\n")
```

Или проще через Read tool + Write tool в Claude:
1. Read `DREAM-REPORT-<date>.md` (получишь текущий контент)
2. Build new content = existing + "\n" + log_block
3. Write `DREAM-REPORT-<date>.md` целиком с новым контентом

ISO 8601 UTC формат timestamp: `YYYY-MM-DDTHH:MM:SSZ` (например `2026-05-02T15:42:33Z`).

Пример log_block:
```markdown
## Wake log — 2026-05-02T15:42:33Z
Applied: M1, M3, N2, I1
Failed:
- M5: target file no longer exists (was renamed?)
Skipped:
- X9: not in report (typo in args?)
```

При повторных запусках wake — каждый добавляет свой `## Wake log — <timestamp>` блок в конец, не перезаписывая предыдущие.

## Safety rules

**Разрешено:**
- `Read`, `Grep`, `Glob` — без ограничений
- Read-only Bash для inventory + verify
- `Edit`/`Write` — **ТОЛЬКО** в `<memory_dir>/` и **ТОЛЬКО** в источниках/целях явно перечисленных в выбранных proposals
- `mv` — **ТОЛЬКО** в:
  - `<memory_dir>/TRASH/` (для memory soft-delete)
  - `<cwd>/_archive/dream-applied-<date>/` (для cwd notes archive)
  - `<cwd>/_archive/trash-purged-<date>/` (для purge_trash из memory/TRASH/)
- `mkdir -p` — для dest директорий перед mv

**Запрещено:**
- Любая работа над items НЕ в `selected`
- `rm` (используй `mv` в TRASH/_archive — при ошибке можно вернуть)
- `mv` куда-либо кроме двух разрешённых dest
- Изменение проектных папок (с .git/, package.json)
- Изменение чего-либо вне явных file paths из выбранных proposals

**Если уверен что нужно сделать что-то не в списке:** STOP, спроси пользователя.

## Edge cases

- **Файл proposals изменился между dream и wake** (ты сам редактировал memory вручную): Read актуальное состояние перед Edit, проверь что `diff_preview` ещё applicable. Если нет — пропусти, добавь в `failed[]`.
- **JSON старше отчёта по времени:** уже есть date verify в Phase 1
- **Несколько отчётов в cwd:** возьми latest по mtime, в чате укажи какой используешь
- **`wake` без args и без JSON:** STOP, инструкция как сделать
- **Choices содержит ID которого нет в отчёте:** warn, добавь в `skipped[]`
- **MEMORY.md превысил лимит после apply:** warn, рекомендуй повторный dream
- **Args с пробелами:** `wake M1, M3, N2` → trim каждый элемент
- **JSON блок невалидный** (broken JSON в proposal): warn, пропусти этот item, добавь в `failed[]` с reason "malformed JSON in proposal"

## Anti-patterns

- **Apply не из selected** — никогда. Даже если "очевидно нужно".
- **rm вместо mv** — никогда. mv в TRASH/_archive можно вернуть.
- **Apply без summary gate** — всегда показывай что будет сделано
- **Тихий пропуск failed items** — всегда репорти в финальном отчёте
- **Cleanup проектов** — out of scope. Wake работает только с memory + согласованные cwd notes.
- **Парсинг markdown headings** — НЕ полагайся на `#### M1.` формат. Парси ТОЛЬКО fenced JSON blocks с `json` тегом.

## Source attribution

- Парный skill — `dream` (записывает report и UI)
- canUseTool restrictions imitation — `services/extractMemories/extractMemories.ts:171`
- Memory file format — `memdir/memoryTypes.ts`
- MEMORY.md лимиты — `memdir/memdir.ts`
- Split dream+wake с HTML чекбоксами + JSON-block contract — твоё уточнение 2026-05-02
