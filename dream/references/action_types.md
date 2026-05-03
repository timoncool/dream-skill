# Action types — JSON contract для proposals

Каждый proposal в `DREAM-REPORT-<date>.md` — fenced JSON block. Поле `action` строго один из ниже. Wake skill парсит эти блоки и выполняет соответствующие операции.

## Memory actions (category: "memory")

### `update`
Edit existing файла без структурных изменений.
- **target** (string) — путь к файлу относительно memory_dir
- **diff_preview** (string) — что именно изменится

### `merge`
Слить N source файлов в один target.
- **files** (array of strings) — source файлы (mv в TRASH после merge)
- **target** (string) — куда мерджить (existing или new)
- **diff_preview** (string) — какие секции откуда

### `delete`
Edit для очистки контента, оставить frontmatter с заметкой о удалении.
- **target** (string) — путь к файлу

### `soft_delete`
mv файл(ов) в memory_dir/TRASH/.
- **files** (array of strings) — что переместить

### `create_new`
Write новый memory файл.
- **target** (string) — имя нового файла
- **content_template** (string) — содержимое. **НЕ ВКЛЮЧАЙ тройные бэктики** — wake парсит JSON блоки внешнего отчёта по паттерну ` ```json...``` ` и non-greedy regex обрежется на первом ` ``` ` внутри payload. Если нужен код-блок в memory файле — используй четыре бэктика или `~~~` или генерируй через wake вручную.
- **type** (string) — `user` | `feedback` | `project` | `reference`

## Notes actions (category: "notes")

### `extract`
Извлечь часть cwd note в memory.
- **source_note** (string) — путь к note в cwd
- **target_memory_file** (string) — куда писать (existing или new)
- **what_to_extract** (string) — какие секции/контент
- **source_action** (string) — `keep` | `delete` | `move-to-archive`

## Index actions (category: "index", target всегда MEMORY.md)

### `remove_links`
Удалить указанные ссылки. Wake находит по **substring** (не exact match всей строки) и удаляет всю строку MEMORY.md где найден substring.
- **links_to_remove** (array of strings) — substring каждой ссылки, например `"[Old handoff](handoff_old.md)"`. Wake ищет эту substring в MEMORY.md и удаляет всю строку.

Пример:
```json
{
  "id": "I1", "category": "index", "action": "remove_links",
  "title": "...", "rationale": "...",
  "links_to_remove": ["(handoff_old.md)", "(stale_plan.md)"]
}
```

### `shorten_lines`
Заменить указанные длинные строки на сокращённые. Wake делает Edit с заменой `original` → `replacement`.
- **lines_to_shorten** (array of objects) — каждый объект `{original: string, replacement: string}`

Пример:
```json
{
  "id": "I2", "category": "index", "action": "shorten_lines",
  "title": "...", "rationale": "...",
  "lines_to_shorten": [
    {
      "original": "- [Project X with very long description that takes more than 200 chars](project_x.md) — full hook text here that is way too long",
      "replacement": "- [Project X](project_x.md) — short hook"
    }
  ]
}
```

### `add_links`
Добавить ссылки в указанные секции. Wake вставляет `line` после строки заголовка указанной `section`.
- **links_to_add** (array of objects) — каждый `{section: string, line: string}` где `section` это точный markdown заголовок (например `"## Feedback"`), `line` это полная markdown строка для вставки.

Пример:
```json
{
  "id": "I3", "category": "index", "action": "add_links",
  "title": "...", "rationale": "...",
  "links_to_add": [
    {
      "section": "## Feedback",
      "line": "- [New feedback](feedback_new.md) — short hook under 150 chars"
    }
  ]
}
```

## Other (category: "other")

### `purge_trash`
**Второй уровень корзины.** Финально вынести из `memory/TRASH/` старые файлы (>30 дней без обращения) в архив проекта `_archive/trash-purged-<date>/`. По-прежнему **никакого `rm`** — wake делает только `mv`, файлы recoverable. Юзер потом может `rm` руками когда уверен.

- **files** (array of strings) — basename файлов в TRASH, например `["old_handoff.md", "stale_plan.md"]`. Wake mv их из `<memory_dir>/TRASH/` в `<cwd>/_archive/trash-purged-<date>/`.

Когда генерировать (dream Phase 2): для каждого TRASH файла с `mtime > 30 дней` собрать в один O-proposal. Не предлагать если TRASH пустой или все файлы свежие.

Пример:
```json
{
  "id": "O1", "category": "other", "action": "purge_trash",
  "title": "Очистить TRASH — 12 файлов старше 30 дней",
  "rationale": "За месяц ни один не был восстановлен, MEMORY_backup keep как точка возврата",
  "files": ["handoff_old_2026_03_01.md", "stale_plan_2026_02_15.md", "..."]
}
```

### Custom other actions

Должны иметь явный `description` поле и не использовать необычные tools.

## Required fields для всех

- **id** (string) — `M1`, `N1`, `I1`, `O1` etc. Префикс = категория.
- **category** (string) — `memory` | `notes` | `index` | `other`
- **action** (string) — один из выше
- **title** (string) — короткое название для UI
- **rationale** (string) — почему это предлагается

## Example полный proposal

```json
{
  "id": "M1",
  "category": "memory",
  "action": "merge",
  "title": "Merge handoff_pikabu_* в один summary",
  "files": ["handoff_pikabu_mcp_2026_03_30.md", "handoff_pikabu_mcp_2026_04_01.md"],
  "target": "project_pikabu_mcp.md",
  "diff_preview": "Append sections '## Session 04-01' к существующему target",
  "rationale": "Серия завершилась 04-04, отдельные handoff'ы не нужны"
}
```
