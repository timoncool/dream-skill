---
name: dream
description: Режим сна Claude — РЕФЛЕКСИВНОЕ ЧТЕНИЕ памяти, заметок и проектов с консолидацией предложений и синтезом insights. **ТОЛЬКО ЧТЕНИЕ** — никаких изменений файлов кроме записи отчёта. Output — два файла: `DREAM-REPORT-<date>.md` (детальный audit trail с JSON-блоками для каждого proposal) и `DREAM-REPORT-<date>.html` (UI в браузере с чекбоксами для выбора что применить). Пользователь открывает HTML, выбирает галочками, нажимает Save → создаётся `DREAM-CHOICES-<date>.json`, потом запускает `wake` skill для применения. Auto mode («поспи сам», «автосон», «autodream») — независимый агент-валидатор проверяет proposals вместо юзера и сразу запускает wake; full auto («полный автосон», «поспи сам полностью») — валидатор решает всё включая delete/purge_trash, ничего не остаётся на ручное решение. Use whenever the user wants to "поспи", "сон", "режим сна", "dream", "поспи сам", "автосон", "autodream", "разберись с памятью", "пройдись по памяти", "обработай заметки", "консолидируй память", "audit memory", "consolidate memory", "reflect on", "что нового я узнал", "что забыл", "synthesize", "сделай выводы из". Reads memory directory + scattered notes in working folder + skims project READMEs/docs as context. Does NOT modify anything except writing the two report files. Расширенная версия autoDream из утечки Claude Code.
---

# Dream — режим сна (read-only)

Рефлексивный pass по памяти, заметкам, проектам. Адаптация `autoDream` из утечки Claude Code (`services/autoDream/consolidationPrompt.ts`):

1. **Никаких изменений** кроме записи двух файлов отчёта
2. **Phase Reflect** — синтез insights и новых идей
3. **HTML-чекбоксы** для выбора что применить
4. Применяет — отдельный skill `wake` (не этот)

## Объекты skill — что читаем

| Объект | Действие |
|---|---|
| Memory dir текущего cwd (`~/.claude/projects/<slug>/memory/`) | **Read only** |
| **Memory dirs ВСЕХ проектов** (`~/.claude/projects/*/memory/`) — если cross-project обзор полезен | **Read only** (опционально) |
| **Глобальный `~/.claude/CLAUDE.md`** — user instructions для всех cwd | **Read only** (обязательно — помогает dedup feedback'ов) |
| **Проектный `<cwd>/CLAUDE.md`** если есть | **Read only** |
| Заметки в cwd (`*.md`, `*.txt` в корне рабочей папки) | **Read only** |
| Проекты в cwd (подпапки с маркерами) | **Read only** (README + docs/) |
| JSONL транскрипты сессий | **Narrow grep only** (не читать целиком) |
| Глобальный `~/.claude/skills/` каталог | **List only** (orientation, не Read контента) |
| Staging second-nature (`~/.claude/second-nature/staging/`) + его state.db | **Read only** (если есть — Phase 2 п.7 Skill harvest) |
| Код, исходники, JSON dumps, логи | Не трогаем |

**Единственная Write-операция:** запись двух файлов отчёта в `<cwd>/`.

## Файлы skill

- **`SKILL.md`** (этот файл) — workflow + safety rules
- **`references/action_types.md`** — JSON contract для proposals (читай перед Phase 4)
- **`assets/template.html`** — HTML шаблон отчёта (используется build_report.py)
- **`assets/build_report.py`** — helper script: payload JSON → MD + HTML (используется в Phase 4)

## Как вычислить пути (Win11 Git Bash)

Memory dir: `C:\Users\<user>\.claude\projects\<slug>\memory\`

`<slug>` = Windows-style cwd с заменой `:` и `/` на `-`. Пример: cwd `D:\Projects\TEMP\` → `D:/Projects/TEMP` (через `pwd -W`) → slug `D--Projects-TEMP`.

**КРИТИЧНО:** в Git Bash `pwd` возвращает Unix-mount (`/d/Projects/TEMP`) — не работает для slug. Нужен `pwd -W` для Windows-style.

Также для Python (build_report.py, broken-link check) пути должны быть Windows-style (`C:/Users/...`), не bash-mount (`/c/Users/...`). Python на Windows не понимает `/c/`.

Заводи **две** переменные пути:

```bash
# Bash-mount (для bash команд: ls/find/grep/cat и т.п.)
CWD_BASH=$(pwd)                                    # /d/Projects/TEMP
CWD_WIN=$(pwd -W)                                  # D:/Projects/TEMP
SLUG=$(echo "$CWD_WIN" | sed 's|[:/]|-|g')         # D--Projects-TEMP

MEMORY_DIR_BASH="$HOME/.claude/projects/$SLUG/memory"        # /c/Users/.../memory
MEMORY_DIR_WIN=$(cygpath -w "$MEMORY_DIR_BASH" | sed 's|\\|/|g')  # C:/Users/.../memory

PROJECTS_DIR_BASH="$HOME/.claude/projects/$SLUG"
PROJECTS_DIR_WIN=$(cygpath -w "$PROJECTS_DIR_BASH" | sed 's|\\|/|g')

test -d "$MEMORY_DIR_BASH" && echo "OK $MEMORY_DIR_WIN" || echo "NOT FOUND"
```

Используй `_BASH` пути в bash-командах (`ls`, `find`, `grep`, `cat`). Используй `_WIN` пути в **payload JSON** для build_report.py и в любых **inline Python** скриптах через `python -c`.

JSONL транскрипты в `$PROJECTS_DIR_BASH/*.jsonl`.

Edge case: если cwd сам внутри memory dir — пиши отчёт и notes-log в `<cwd>/../` чтобы не подмешать в indexer.

## Modes

### Default mode (cwd-only)
Триггеры: `поспи`, `сон`, `dream`, `консолидируй память`. Scope: текущий cwd memory dir + cwd notes + projects в cwd.

### Global mode (cross-project)
Триггеры: `поспи глобально`, `dream global`, `audit all memory`, `консолидируй всю память`. Scope: **все** `~/.claude/projects/*/memory/` директории.

Зачем: найти **межпроектные дубли feedback'ов** (один и тот же `feedback_X.md` скопирован в 3 проекта без учёта эволюции), устаревшие memory dirs от давно мёртвых проектов, паттерны drift между проектами.

В global mode:
- Phase 1 inventory расширяется на все проекты
- Phase 2 читает memory всех проектов с тэгом `[project=<slug>]` в notes log
- Phase 4 payload получает `mode: "global"`, каждый proposal затрагивающий memory имеет поле `project: <slug>` (см. `references/action_types.md`)
- HTML UI добавляет фильтр-пилюли по проектам
- Cwd notes / projects в global mode **не сканируются** — слишком дорого, фокус на memory dirs

### Auto mode (autodream) — валидатор вместо юзера

Триггеры: `поспи сам`, `автосон`, `autodream`, `поспи и примени`, `сам всё реши и примени`.

Полный цикл без ручных галочек: dream (Phase 0–4 как обычно, отчёт и HTML пишутся — audit trail обязателен) → независимый валидатор → wake. Человеческий гейт **заменяется** адверсариальной проверкой, а не пропускается.

**Phase 5 (только auto mode) — независимый валидатор:**

1. После Phase 4 spawn **отдельный Agent** (subagent_type: general-purpose). Модель — уровень основной сессии (Fable/Opus), **НИКОГДА Sonnet и ниже**. Свежий контекст обязателен: сессия, которая писала proposals, их же и одобрит — это не проверка.
2. Промпт валидатора: «Ты — представитель юзера, дефолт — отклонить. Для каждого proposal из `DREAM-REPORT-<date>.md`: Read затронутые файлы, перепроверь evidence из rationale сам (`test -e`, `grep` — не верь rationale на слово), вынеси вердикт. Отклоняй если: факт непроверяем; merge теряет nuance; итоговый текст содержит мета-нарративы; файл изменился с момента отчёта; сомневаешься. Верни JSON: `{"verdicts": {"M1": {"verdict": "approve|reject", "reason": "..."}}}`». Валидатор read-only — ничего не применяет.
3. **Автостоп-лист** — валидатор НЕ имеет права одобрить, только юзер вручную:
   - `[UNVERIFIED]` в title
   - action=`delete` (очистка контента — единственное частично необратимое)
   - action=`purge_trash` (второй уровень корзины)
   - proposals по конфликтам из Phase 3
4. Собери approved → Write `DREAM-CHOICES-<date>.json`: `{"report_date": "<date>", "selected": [approved IDs], "auto": true, "validator_verdicts": {...}}`
5. Запусти `wake` — он видит `auto: true` и применяет без ожидания подтверждения (см. wake SKILL.md).
6. Финал в чат: применено / отклонено валидатором (с причинами) / осталось на ручное решение (автостоп-лист). HTML-отчёт остаётся — недорешённое можно добить галочками как обычно.

**Full auto (полный автосон)** — триггеры: `полный автосон`, `поспи сам полностью`, `full autodream`, «сам всё провери, заапрувь и разрули». Отличия от обычного auto mode:

- Автостоп-лист для **actions снимается**: валидатор может одобрять `delete` и `purge_trash`. Компенсация: wake в full auto делает pre-delete backup файла в TRASH перед очисткой контента (см. wake SKILL.md) — необратимого не остаётся вовсе.
- `[UNVERIFIED]` и неразрешимые конфликты валидатор **разруливает сам, консервативно**: verdict=reject с reason `«непроверяемо — оставлено как есть»`. Решение принято (= не трогать), юзеру ничего не откладывается; такие айтемы перечисляются отдельным блоком в финальном summary и всплывут в следующем dream, если протухнут окончательно.
- Choices JSON получает `"auto": true, "auto_level": "full"`.
- В финале каждый proposal имеет исход: applied / rejected-by-validator / kept-as-unverifiable. Пустой раздел «на ручное решение» — критерий успеха full auto.
- Страховка: wake перед apply всегда делает полный snapshot памяти в `_archive/wake-backup-*/`; регресс после автосна откатывается фразой «откати сон» (wake Rollback). В финальном summary укажи путь snapshot'а.

Anti-pattern: валидировать в той же сессии без Agent'а. Смысл гейта — независимый контекст, а не ещё один проход тем же взглядом.

## Workflow — 4 фазы

### Phase 0 — Lock + Init notes log (КРИТИЧНО, делать первым шагом)

**Сначала lock против race condition.** Если юзер запустит `dream` в двух терминалах одновременно — append'ы в notes log поедут, отчёт превратится в кашу. Inspired by autoDream's `.consolidate-lock`.

```bash
LOCK_DIR="$CWD_BASH/.dream-lock"
DATE_TODAY=$(date +%Y-%m-%d)

# Atomic mkdir = filesystem-level lock primitive
if mkdir "$LOCK_DIR" 2>/dev/null; then
  echo $$ > "$LOCK_DIR/pid"
  echo "$DATE_TODAY" > "$LOCK_DIR/date"
  echo "LOCK acquired"
else
  # Lock exists — check if stale (>1h old by mtime)
  LOCK_AGE=$(( $(date +%s) - $(stat -c %Y "$LOCK_DIR" 2>/dev/null || stat -f %m "$LOCK_DIR") ))
  if [ "$LOCK_AGE" -gt 3600 ]; then
    echo "STALE LOCK (${LOCK_AGE}s old) — removing and re-acquiring"
    rm -rf "$LOCK_DIR" && mkdir "$LOCK_DIR" && echo $$ > "$LOCK_DIR/pid"
  else
    echo "DREAM ALREADY RUNNING (lock age ${LOCK_AGE}s) — abort"
    # Claude reads this and stops the workflow
    exit 0
  fi
fi
```

**В финале Phase 4** (или при любой ошибке) — release: `rm -rf "$LOCK_DIR"`. Если dream упал — следующий запуск через 1 час сам подберёт stale lock.

**Это единственное `rm` разрешённое в dream — и только для собственного lock-каталога.**

Дальше — notes log. Создай `<cwd>/.dream-notes-<YYYY-MM-DD>.md` через Write tool. Это append-only лог в который ты пишешь после **каждого** прочитанного файла. Без него Phase 3 reflect не сработает на больших корпусах: контекст растёт линейно, ранние reads забываются после compaction.

Шаблон notes log:

```markdown
# Dream notes — <YYYY-MM-DD>
**Started:** <ISO timestamp>

## Inventory
- Memory: surveyed N files (will fill in Phase 1)
- Cwd notes: surveyed M
- Projects: surveyed P

## Per-file notes (filled during Phase 2 reading)
<один блок на каждый прочитанный файл>

## Cross-file observations (filled during Phase 3)
<patterns, drift, conflicts, mergeable, deletions>
```

Формат записи per-file (3-7 строк, не больше):

```markdown
### <filename>
- **Type/age:** feedback / 30 days
- **Topic:** одна строка что про что
- **Key facts:** 1-3 bullets конкретного контента
- **Issues:** дубль с X / устарело / нечётко / конфликт с Y / null
- **Action hint:** keep / merge-with-X / soft_delete / shorten-in-MEMORY.md / null
```

После каждого Read'а memory/cwd/project README — **append** в notes log через Edit (Read existing → append → Write). Не пихай всё в context — лог это твоя долговременная память для этой сессии.

### Phase 1 — Orient (read-only inventory)

Цель — **ОБОЙТИ ВСЁ**. Cheap inventory + frontmatter scan для memory + recursive find для cwd. Не читать файлы полностью, только счётчики.

Веди в notes log: **Surveyed** (всё что узнал из ls/find/grep — это «обошёл») и **Read** (детально прочитал — обновляется в Phase 2).

```bash
# === MEMORY DIR — обойти ВСЁ (через frontmatter scan, не Read) ===
ls "$MEMORY_DIR_BASH"
ls "$MEMORY_DIR_BASH/TRASH/" 2>/dev/null
wc -l "$MEMORY_DIR_BASH/MEMORY.md"   # лимит 200 строк / 25 KB
du -sh "$MEMORY_DIR_BASH"

# Frontmatter scan ВСЕХ memory файлов (cheap — только name/description/type строки)
# Без temp файлов и rm — один pipe прямо в output Bash'а
for f in "$MEMORY_DIR_BASH"/*.md; do
  printf '=== %s (%s lines) ===\n' "$(basename "$f")" "$(wc -l < "$f")"
  grep -E '^(name|description|type):' "$f" 2>/dev/null | head -3
done

# === GLOBAL MODE only — обойти ВСЕ memory dirs ===
# (пропусти если default mode — экономь turns)
for proj_dir in "$HOME/.claude/projects"/*/; do
  proj_slug=$(basename "$proj_dir")
  proj_mem="$proj_dir/memory"
  test -d "$proj_mem" || continue
  test "$proj_mem" = "$MEMORY_DIR_BASH" && continue   # уже сканили выше
  count=$(ls "$proj_mem"/*.md 2>/dev/null | wc -l)
  age=$(stat -c '%Y' "$proj_mem" 2>/dev/null || stat -f '%m' "$proj_mem")
  printf 'PROJECT %s: %d files, mtime=%s\n' "$proj_slug" "$count" "$age"
done | sort -k4 -rn | head -20   # 20 самых свежих проектов

# TRASH — возраст файлов (для D1 кандидатов на final delete)
find "$MEMORY_DIR_BASH/TRASH/" -name "*.md" -mtime +30 2>/dev/null

# === Относительные даты и point-in-time статусы (кандидаты на update) ===
grep -rnE "вчера|сегодня|завтра|на днях|недавно|сейчас|пока не|прошлой неделе|yesterday|today|last week|recently|currently|still running" "$MEMORY_DIR_BASH" --include="*.md" | grep -v "/TRASH/"

# === Orphan-файлы: есть на диске, нет хука в MEMORY.md (кандидаты на add_links) ===
for f in "$MEMORY_DIR_BASH"/*.md; do
  b=$(basename "$f")
  [ "$b" = "MEMORY.md" ] && continue
  grep -q "$b" "$MEMORY_DIR_BASH/MEMORY.md" || echo "ORPHAN: $b"
done

# === CWD — рекурсивный обход notes (1 уровень глубины) ===
find "$CWD_BASH" -maxdepth 2 \( -name "*.md" -o -name "*.txt" \) -not -path "*/node_modules/*" -not -path "*/.git/*" -not -path "*/_archive/*" 2>/dev/null

# === CWD PROJECTS — обойти ВСЕ проекты (по маркерам) ===
for dir in "$CWD_BASH"/*/; do
  if [ -d "$dir/.git" ] || [ -f "$dir/package.json" ] || [ -f "$dir/Cargo.toml" ] || [ -f "$dir/pyproject.toml" ] || [ -f "$dir/composer.json" ] || [ -f "$dir/go.mod" ] || [ -f "$dir/README.md" ]; then
    mtime=$(stat -c '%Y' "$dir" 2>/dev/null || stat -f '%m' "$dir")
    echo "PROJECT $mtime: $dir"
  fi
done | sort -rn
```

Read `MEMORY.md` целиком — твой index, маленький. (Read counter += 1, Surveyed += число memory файлов из frontmatter scan + cwd notes найденные find'ом + проекты)

### Phase 2 — Read EVERYTHING in scope, log as you go

**Цель: прочитать ВСЁ полное содержимое каждого файла в scope.** Никаких лимитов "10-15 файлов". User в этом скилле явно запрашивает полное покрытие, контекст управляется через **notes log** (Phase 0).

**TodoWrite для прогресса** (рекомендуется при >30 файлов): создай TodoWrite список с одним пунктом на каждую группу:
- "Memory files (N штук)"
- "Cwd notes (M штук)"
- "Project READMEs (P штук)"
- "JSONL grep (если нужен)"

Помечай `in_progress` перед группой, `completed` после. Юзер видит реальный прогресс в footer pill — на 100+ файлах это критично, иначе кажется что висишь.

После каждого Read'а — сразу Edit notes log (per-file блок 3-7 строк). Не пихай контент в context — лог это твоя долговременная память. Compaction может выкинуть ранние reads, но лог остаётся на диске.

Порядок чтения (читай ВСЁ в каждой группе):

1. **MEMORY.md** — целиком, лог: количество строк, broken links, длинные строки (>200 chars = утечка контента), дубли descriptions
2. **Все memory files** в порядке user → feedback → project → reference → handoff → other:
   - Read каждый
   - После каждого Read'а → Edit notes log с per-file блоком (file/type/age/topic/key facts/issues/action hint)
   - Если файл огромный (500+ строк) — Read с offset/limit по частям, в логе пометь
   - Относительные даты («вчера», «на прошлой неделе», hits из Phase 1 grep'а) → кандидат на `update` proposal с конвертацией в абсолютную дату; якорь — mtime файла, не дата отчёта
3. **Все cwd root .md/.txt** — Read каждый, log
4. **Cwd подпапки .md/.txt** (recursive maxdepth 2, исключая .git/node_modules/_archive) — Read каждый, log
5. **Все проекты в cwd** — каждая подпапка с маркером (.git/package.json/Cargo.toml/pyproject.toml/composer.json/go.mod/README.md), без top-N лимита:
   - Read README.md
   - Read package.json / pyproject.toml / Cargo.toml (что есть)
   - Read CHANGELOG.md если есть
   - ls docs/ + Read 1-3 топ-файла оттуда
   - НЕ лезть в `src/`, `node_modules/`, `vendor/`, `.next/`, `build/`, `dist/`
   - После каждого Read'а → Edit notes log
6. **Транскрипты JSONL — narrow grep** только под конкретные quotes из других файлов:
   ```bash
   grep -rn "<narrow term>" "$PROJECTS_DIR_BASH/" --include="*.jsonl" | tail -50
   ```

7. **Skill harvest (second-nature)** — если существует `~/.claude/second-nature/staging/`: Read каждый `staging/*/SKILL.md` (они маленькие) + телеметрия read-only: `python -c` по `~/.claude/second-nature/state.db` (`SELECT name,use_count,last_used,staged_ts,pinned_project FROM skill_usage`). Для каждого драфта — proposal категории S (см. action_types.md): `promote_skill` (триггер внятный `Use when...`, содержимое проверяемо, дубля в активных скиллах нет — grep по `~/.claude/skills` и `D:\Projects\claude-skills`) / `retire_skill` (протух >30д без использования, дубль активного, мусор) / keep. Evidence policy действует и здесь.

8. **TRASH purge candidates** — для каждого файла в `memory/TRASH/` с mtime >30 дней (из find в Phase 1) собери список. В Phase 4 это станет proposal `id=O1, action=purge_trash` (см. `references/action_types.md`). Пропусти если TRASH пустой или нет старых файлов. **Сохрани файлы которые юзер явно помечал как точки возврата** (например `MEMORY_backup_*`) — упомяни в rationale что keep.

**Лимита нет.** Read EVERYTHING. Контекст-управление через notes log — не пропускай ни одного файла, не пропускай ни одной log-записи.

В отчёте укажи: `Files reviewed: surveyed N total (memory: M, cwd notes: K, projects: P) / read in full: <count log entries>`.

### Phase 3 — Reflect & Synthesize (read-only, ~2-3 turns)

Сердце skill. Не просто consolidate — отрефлексируй:

- **Patterns** — что повторяется?
- **Drift** — где память противоречит свежему контексту?
- **Connections** — какие связи не были явно сказаны?
- **Gaps** — какие важные темы НЕ задокументированы?
- **Insights** — какие новые наблюдения / выводы / идеи? Не пересказ, синтез.
- **Stale** — что устарело?
- **Conflicts** — противоречия между записями. Разрешимо по evidence → proposal с новым значением; неразрешимо → insight с ⚠️ и вопросом юзеру. НЕ выбирай сторону только чтобы память выглядела чистой.

Эту секцию **показывай юзеру в чат сразу** — это самое ценное.

#### Evidence policy — верификация перед stale/delete/merge

Пометка «устарело» — это утверждение о мире, его надо проверить, а не почувствовать. Перед каждым proposal с `delete`/`soft_delete`/`merge` по причине устаревания:

```bash
test -e "<путь из записи>"                        # файл/папка ещё существует?
grep -rn --fixed-strings "<символ/флаг/команда>"  # ещё встречается в проекте?
```

- **Проверил и подтвердил** → полноценный proposal; в `rationale` обязательно: какая проверка выполнена и результат (`test -e ветка feat-x → отсутствует`).
- **Локально непроверяемо** (удалённые хосты, деплои, внешние сервисы, MR-статусы, «сейчас работает») → title с префиксом `[UNVERIFIED]`, в `rationale` — что именно нельзя проверить. Это кандидат на подтверждение юзером, не решение.
- Возраст файла сам по себе — не evidence. «Выглядит старым» — не причина для delete.

### Phase 4 — Write report (два файла)

Используем helper script `assets/build_report.py` чтобы избежать escape-багов и multi-line `python -c` сложностей. Claude НЕ генерит MD/HTML руками — только готовит payload JSON.

**Чёткий порядок шагов:**

1. **Read** `references/action_types.md` — JSON contract для proposals
2. **Build payload JSON** в памяти со всем содержимым:
   ```json
   {
     "date": "2026-05-02",
     "timestamp_iso": "2026-05-02T14:30:00Z",
     "memory_dir": "C:/Users/user/.claude/projects/D--Projects-TEMP/memory",
     "cwd": "D:/Projects/TEMP",
     "files_count": "12 memory + 5 cwd notes + 3 project READMEs",
     "insights": ["bullet 1", "bullet 2", ...],
     "proposals": [
       {
         "id": "M1", "category": "memory", "action": "merge",
         "title": "...", "rationale": "...",
         ...action-specific fields per action_types.md
       },
       ...
     ],
     "apply_order": [["M1", "M3"], ["N1", "N2"], ["I1", "I2"]]
   }
   ```
3. **Write payload** через Write tool в `<cwd>/.dream-payload-<date>.json` (точка в начале — hidden, не зацепится `wake` поиском DREAM-CHOICES)
4. **Найти путь к build_report.py** относительно cwd:
   ```bash
   SCRIPT="$CWD_BASH/.claude/skills/dream/assets/build_report.py"
   test -f "$SCRIPT" || SCRIPT="$HOME/.claude/skills/dream/assets/build_report.py"
   ```
5. **Run script**:
   ```bash
   python "$SCRIPT" "$CWD_BASH/.dream-payload-<date>.json"
   ```
   Скрипт пишет MD + HTML атомарно в cwd, валидирует payload, делает все escape для HTML/JSON.
6. STOP, summary в чат

`build_report.py` сам делает:
- Build MD с fenced JSON blocks для каждого proposal
- Build HTML через replace placeholders в template + правильный escape (`html.escape` для текста, `json.dumps` + `</` → `<\/` для inline-script)
- Validation обязательных полей в payload

Если скрипт упал — read stderr, исправь payload, повтори. Не редактируй MD/HTML руками — это нарушит контракт с wake.

Payload файл `.dream-payload-<date>.json` остаётся в cwd как audit trail генерации (можно удалить вручную позже).

#### Финальное сообщение в чат

> 💤 Dream завершил.
> **Insights:** <3-5 bullets из Phase 3>
> **Отчёт:** `DREAM-REPORT-<date>.md` (audit trail) + `DREAM-REPORT-<date>.html` (UI)
>
> **Открыть HTML:**
> - Windows: `start D:\Projects\TEMP\DREAM-REPORT-<date>.html`
> - Через preview tool в Claude Code (если доступен): я могу открыть сам, скажи "открой preview"
>
> **Дальше:** отметь галочками → 💾 Save choices → скажи `wake` (он найдёт JSON автоматически).

Опционально: если доступен `mcp__Claude_Preview__preview_start` — предложи запустить.

## Safety rules

**Разрешено:**
- `Read`, `Grep`, `Glob` — без ограничений
- Read-only Bash: `ls`, `find` (без `-delete`/`-exec`), `grep`, `cat`, `head`, `tail`, `wc`, `du`, `stat`, `file`, `sort`, `uniq`, `cut`, `awk`, `sed` (без `-i`), `pwd`, `date`, `python` (для запуска build_report.py), `jq`
- `Write` / `Edit` — **ТОЛЬКО** четыре файла:
  - `<cwd>/.dream-notes-<date>.md` (append-only log, обновляется после каждого Read'а в Phase 2)
  - `<cwd>/.dream-payload-<date>.json` (input для build_report.py)
  - `<cwd>/DREAM-REPORT-<date>.md` (создаётся скриптом)
  - `<cwd>/DREAM-REPORT-<date>.html` (создаётся скриптом)

**Запрещено:**
- Любой `Edit`/`Write` в memory dir, проекты, заметки cwd (это работа `wake` skill)
- `rm` где угодно **кроме `<cwd>/.dream-lock/`** (собственный lock-каталог skill'а — release в финале + stale recovery)
- `mv`, `cp`, `chmod`, redirect `>`/`>>`, `tee`, `truncate`
- `find -delete`, `find -exec rm/mv`

Split на dream+wake существует именно потому что между «прочитать» и «изменить» обязательно осознанный выбор человеком галочками. Без этого — autoDream issue #38493 (hallucinated audit, factually unverified memories).

## Memory file format

Файлы в memory dir имеют frontmatter (из `memdir/memoryTypes.ts` утечки):

```yaml
---
name: <короткое имя темы>
description: <одна строка>
type: user | feedback | project | reference
---
<контент. Для feedback/project: rule/fact, потом **Why:** и **How to apply:**>
```

**Что НЕ должно быть в memory** (`WHAT_NOT_TO_SAVE`): code patterns, git history, debug solutions, дубли CLAUDE.md, ephemeral state. Кандидаты на removal (action=delete или soft_delete).

**Output hygiene — запрет мета-нарративов.** Итоговый текст записей в proposals (`content_template`, `diff_preview`, replacement-строки) не должен содержать: «юзер поправлял N раз», «выучено после ошибки», session ID, историю неудачных попыток, «дубль удалён / не повторяется здесь». Техническая причинность остаётся, если меняет будущее поведение:

- ✅ `Не использовать git add -A — зацепит несвязанные изменения юзера.`
- ❌ `Юзер трижды исправлял это, поэтому запомнить: не использовать git add -A.`

Рассуждения и история — в rationale отчёта, не в памяти.

## MEMORY.md лимиты

`MAX_ENTRYPOINT_LINES = 200`, `MAX_ENTRYPOINT_BYTES ≈ 25 000`, каждая строка ≤ 150 chars.

**Норматив хука в индексе: 80–150 символов.** Хук отвечает на «когда открывать этот файл», а не пересказывает содержимое. Короче 80 — обычно бесполезен («см. файл»), длиннее 150 — утечка контента в индекс → proposal `shorten_lines` (детали остаются в recall-файле).

## Anti-patterns

- **Автономный apply** (autoDream #38493) — split dream+wake предотвращает
- **Чтение без notes log** — после 50+ файлов compaction выкинет ранние reads, Phase 3 reflect будет пустой. ВСЕГДА append per-file блок в notes log сразу после Read'а.
- **`pwd` без `-W` на Win11 Git Bash** — даст `/d/Projects/TEMP`, slug посчитается неправильно (`d-Projects-TEMP` вместо `D--Projects-TEMP`), memory dir не найдётся
- **Bash-mount пути в Python (`/c/Users/...`)** — Python на Windows не понимает, нужны Windows-style (`C:/Users/...`) через `cygpath -w`
- **Фейковые консолидации** — не теряй nuance, не уверен → не предлагай merge
- **Stale по наитию** — delete/soft_delete без `test -e`/`grep` верификации (см. Evidence policy). Непроверяемое → `[UNVERIFIED]` в title.
- **Запись отчёта в memory dir** — попадёт в indexer, ВСЕГДА в cwd
- **Изменение чего-либо** — это wake, не dream
- **Markdown-only proposals** — wake не парсит надёжно. ВСЕГДА embed JSON block.
- **Ручная генерация HTML/JSON** — пропустишь escape, используй Python.

## Когда НЕ использовать

- Применить уже готовое — это `wake`
- Почистить файлы / папки → не существует skill, делается вручную
- Код-ревью → `simplify` / `code-review`
- Обновить CLAUDE.md → `claude-md-management:revise-claude-md`

## Source attribution

- 4 фазы — `services/autoDream/consolidationPrompt.ts` (утечка v2.1.88)
- canUseTool restrictions imitation — `services/extractMemories/extractMemories.ts:171`
- Memory taxonomy и WHAT NOT TO SAVE — `memdir/memoryTypes.ts`
- MEMORY.md лимиты — `memdir/memdir.ts`
- Plan-then-apply — `skills/bundled/remember.ts`
- Phase Reflect — Karpathy LLM Wiki "lint pass"
- Split dream+wake с HTML чекбоксами + JSON-block contract — твоё уточнение 2026-05-02
