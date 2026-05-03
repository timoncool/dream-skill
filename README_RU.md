<div align="center">

# dream-skill

**Парные Claude Code скиллы для безопасной консолидации памяти — читаем, рефлексируем, применяем только то, что отметили галочкой.**

[![License](https://img.shields.io/github/license/timoncool/dream-skill?style=flat-square)](LICENSE)
[![Stars](https://img.shields.io/github/stars/timoncool/dream-skill?style=flat-square)](https://github.com/timoncool/dream-skill/stargazers)
[![Last Commit](https://img.shields.io/github/last-commit/timoncool/dream-skill?style=flat-square)](https://github.com/timoncool/dream-skill/commits)

**[English](README.md)** · **[Русский](README_RU.md)**

</div>

---

`dream` обходит папку памяти Claude Code, заметки в рабочей папке и README проектов, после чего синтезирует предложения по консолидации в HTML-отчёт с тёмной темой и чекбоксами. `wake` читает твой выбор и применяет только то, что ты явно отметил — никогда не меняет файлы вне выбранных, никогда не использует `rm`. Вдохновлён утечкой autoDream из внутренностей Claude Code, но с явным human approval gate, которого в оригинале нет.

## Возможности

- **Read-only обход** — dream пишет только файлы отчёта, не может случайно изменить память или заметки
- **Рефлексивный синтез** — Phase Reflect находит паттерны, дрейф, пробелы и противоречия между файлами (расширение поверх оригинального autoDream)
- **HTML UI с чекбоксами** — современная тёмная тема, цветовая кодировка действий (зелёный/красный/синий), чипы файлов, фильтр-пилюли, прогресс-бар, горячие клавиши
- **Надёжный JSON-block контракт** — proposals встроены как fenced JSON блоки в отчёт; wake парсит regex-ом, защищён от любого markdown drift
- **9 типов действий** — `update` / `merge` / `delete` / `soft_delete` / `create_new` / `extract` / `remove_links` / `shorten_lines` / `add_links`
- **Append-only лог заметок** — переживает компакшен контекста; Phase Reflect читает с диска, не из RAM
- **Win11 Git Bash совместимость** — `pwd -W` для slug, `cygpath` для путей в Python
- **Безопасен по дизайну** — `wake` делает `mv` только в `TRASH/` или `_archive/` (восстанавливаемо), никогда `rm`

## Быстрый старт

1. **Клонируем**
   ```bash
   git clone https://github.com/timoncool/dream-skill.git
   ```

2. **Устанавливаем** (рекомендую per-project; глобально тоже работает)
   ```bash
   cd <твой-проект>
   mkdir -p .claude/skills
   cp -r /path/to/dream-skill/dream .claude/skills/
   cp -r /path/to/dream-skill/wake .claude/skills/
   ```

3. **Запускаем** (сначала перезапусти Claude Code, чтобы скиллы подгрузились)
   ```
   поспи         # или "dream" / "consolidate memory"
   # ... открываешь HTML-отчёт, ставишь галочки, жмёшь Save choices ...
   проснулся    # или "wake" / "apply dream"
   ```

## Использование

### Dream — читай и рефлексируй

Триггер-фразы (RU/EN): `поспи`, `сон`, `режим сна`, `dream`, `консолидируй память`, `разберись с памятью`, `audit memory`, `consolidate memory`, `synthesize`.

Output:
- `<cwd>/.dream-notes-<date>.md` — append-only лог (per-file блоки, пишутся инкрементально)
- `<cwd>/.dream-payload-<date>.json` — input для `build_report.py`
- `<cwd>/DREAM-REPORT-<date>.md` — полный audit trail с одним fenced JSON блоком на proposal
- `<cwd>/DREAM-REPORT-<date>.html` — интерактивный UI

### HTML UI

Открой HTML в браузере:
- 🟢 **Конструктивные действия** (merge, create_new, extract) — зелёный оттенок
- 🔴 **Деструктивные действия** (delete, soft_delete) — красный оттенок
- 🔵 **Нейтральные действия** (update, операции с индексом) — синий оттенок

Фильтр по категории (M/N/I/O — memory/notes/index/other) или по типу действия. Кликаешь чекбоксы, жмёшь **💾 Save choices** — Chrome/Edge спросит куда сохранить, Firefox/Safari скачает в `~/Downloads/`.

Клавиатура: `Ctrl+A` — выбрать всё, `Esc` — сбросить, `Ctrl+S` — сохранить.

### Wake — применяет выбранное

Триггер: `проснулся`, `wake`, `apply dream`, `wake M1,M3,N2`, `wake all`.

Wake находит `DREAM-CHOICES-<date>.json` (cwd → `~/Downloads/` → `~/Desktop/`), парсит JSON блоки из отчёта, показывает summary, спрашивает один раз подтверждение, потом применяет только отмеченные пункты через `Edit`/`Write` и `mv` в `TRASH/`/`_archive/`. Дописывает секцию `## Wake log — <timestamp>` в отчёт для audit trail.

## Архитектура

```
dream/
├── SKILL.md                  # workflow + safety rules + path computation
├── references/
│   └── action_types.md       # JSON контракт для 9 типов действий
└── assets/
    ├── template.html         # тёмная тема UI, без external deps (~480 строк)
    └── build_report.py       # payload JSON → MD + HTML, с валидацией

wake/
└── SKILL.md                  # discover choices, parse JSON, summary gate, apply
```

### JSON-block контракт

Каждый proposal в MD отчёте — fenced JSON блок. Wake парсит их Python regex-ом, защищён от любого markdown drift:

```json
{
  "id": "M1",
  "category": "memory",
  "action": "merge",
  "title": "Merge handoff_pikabu_*.md в project_pikabu_mcp.md",
  "rationale": "3 session handoffs накопились, последний — канонический",
  "files": ["handoff_pikabu_2026_03_30.md", "handoff_pikabu_2026_04_01.md"],
  "target": "project_pikabu_mcp.md",
  "diff_preview": "Append session sections, потом mv источников в TRASH/"
}
```

Полная схема всех 9 типов действий — в [`dream/references/action_types.md`](dream/references/action_types.md).

## Гарантии безопасности

**dream** — пишет только четыре файла отчёта, ничего больше:

- Read / Grep / Glob — без ограничений
- Read-only Bash: `ls`, `find` (без `-delete`/`-exec`), `grep`, `cat`, `head`, `tail`, `wc`, `du`, `stat`, `python` (только для build_report.py)
- Write только в: `<cwd>/.dream-notes-<date>.md`, `<cwd>/.dream-payload-<date>.json`, `<cwd>/DREAM-REPORT-<date>.md`, `<cwd>/DREAM-REPORT-<date>.html`
- Никаких `rm`, `mv`, `cp`, redirect, `find -delete`, никаких Edit/Write вне файлов отчёта

**wake** — деструктивные операции ограничены:

- `Edit`/`Write` только в `<memory_dir>/` и явно перечисленных cwd notes из выбранных proposals
- `mv` только в `<memory_dir>/TRASH/` или `<cwd>/_archive/dream-applied-<date>/`
- Никогда `rm` (всегда `mv` = восстанавливаемо)
- Не работает с пунктами, которых нет в `selected`
- Не трогает папки проектов

## Зачем это нужно

В утечке Claude Code v2.1.88 есть `autoDream` — фоновый pass консолидации памяти. Запускается автономно раз в ~24 часа, когда накопилось достаточно сессий. Оригинал страдает от [issue #38493](https://github.com/anthropics/claude-code/issues/38493): *"writes inaccurately named, factually unverified, impossible-to-audit memories"* — потому что никто из людей не проверяет что было смерджено или удалено.

`dream` + `wake` решают это жёстким разделением: dream — read-only и пишет только отчёт; wake применяет только то, что человек явно отметил галочкой в HTML UI. Никаких автономных мутаций памяти.

## Вдохновение

- **autoDream** из утечки Claude Code v2.1.88 — `services/autoDream/consolidationPrompt.ts` (4-фазный Orient → Gather → Consolidate → Prune)
- **createAutoMemCanUseTool** restrictions — `services/extractMemories/extractMemories.ts:171`
- **Memory taxonomy** (user/feedback/project/reference) и `WHAT_NOT_TO_SAVE` — `memdir/memoryTypes.ts`
- **MEMORY.md лимиты** (200 строк / 25KB) — `memdir/memdir.ts`
- **Plan-then-apply паттерн** — `skills/bundled/remember.ts` ("present proposals, do NOT modify without approval")
- **Phase Reflect (синтез поверх консолидации)** — Karpathy [LLM Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f), идея lint-pass

## Другие проекты [@timoncool](https://github.com/timoncool)

| Проект | Описание |
|--------|----------|
| [telegram-api-mcp](https://github.com/timoncool/telegram-api-mcp) | Полный Telegram Bot API как MCP сервер |
| [civitai-mcp-ultimate](https://github.com/timoncool/civitai-mcp-ultimate) | Civitai API как MCP сервер |
| [trail-spec](https://github.com/timoncool/trail-spec) | TRAIL — cross-MCP протокол отслеживания контента |
| [ACE-Step Studio](https://github.com/timoncool/ACE-Step-Studio) | AI music studio — песни, вокал, каверы, видео |
| [GitLife](https://github.com/timoncool/gitlife) | Твоя жизнь в неделях — интерактивный календарь |
| [Bulka](https://github.com/timoncool/Bulka) | Платформа для live-coding музыки |
| [ScreenSavy.com](https://github.com/timoncool/ScreenSavy.com) | Генератор фоновых картинок |

## Авторы

- **Nerual Dreming** — [Telegram](https://t.me/nerual_dreming) | [neuro-cartel.com](https://neuro-cartel.com) | [ArtGeneration.me](https://artgeneration.me)

## Поддержать автора

Я делаю open-source софт и AI-ресёрч. Большинство того, что я создаю — бесплатно и доступно всем. Ваши донаты помогают мне продолжать творить, не думая о том, где взять деньги на следующий обед =)

**[Все способы доната](https://github.com/timoncool/ACE-Step-Studio/blob/master/DONATE.md)** | **[dalink.to/nerual_dreming](https://dalink.to/nerual_dreming)** | **[boosty.to/neuro_art](https://boosty.to/neuro_art)**

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
