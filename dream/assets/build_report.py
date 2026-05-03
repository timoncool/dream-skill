#!/usr/bin/env python3
"""
Build dream report files (MD + HTML) from a payload JSON.

Usage:
    python build_report.py <payload.json>

Payload JSON schema:
{
  "date": "2026-05-02",
  "timestamp_iso": "2026-05-02T14:30:00Z",
  "memory_dir": "C:/Users/.../memory",
  "cwd": "D:/Projects/TEMP",
  "files_count": "12 memory + 5 cwd notes + 3 project READMEs",
  "insights": ["bullet 1", "bullet 2", ...],
  "proposals": [
    {
      "id": "M1",
      "category": "memory",
      "action": "merge",
      "title": "...",
      "rationale": "...",
      ...action-specific fields
    },
    ...
  ],
  "apply_order": ["M1", "M3", "N1", ...]   // recommended order
}

Outputs (relative to payload's cwd):
  DREAM-REPORT-<date>.md
  DREAM-REPORT-<date>.html
"""
import json
import sys
import os
import html
from pathlib import Path

CATEGORY_NAMES = {
    'M': 'Memory consolidation',
    'N': 'Notes integration',
    'I': 'MEMORY.md index rebuild',
    'O': 'Other',
}

# Per-action required fields (in addition to common: id, category, action, title, rationale)
ACTION_REQUIRED_FIELDS = {
    'update': ['target', 'diff_preview'],
    'merge': ['files', 'target', 'diff_preview'],
    'delete': ['target'],
    'soft_delete': ['files'],
    'create_new': ['target', 'content_template', 'type'],
    'extract': ['source_note', 'target_memory_file', 'what_to_extract', 'source_action'],
    'remove_links': ['links_to_remove'],
    'shorten_lines': ['lines_to_shorten'],
    'add_links': ['links_to_add'],
    'purge_trash': ['files'],
}

COMMON_REQUIRED = ['id', 'category', 'action', 'title', 'rationale']


def validate_proposal(p, idx):
    """Returns list of error strings (empty = valid)."""
    errors = []
    for f in COMMON_REQUIRED:
        if f not in p:
            errors.append(f"proposal #{idx} missing required field: {f}")
    action = p.get('action')
    if action and action in ACTION_REQUIRED_FIELDS:
        for f in ACTION_REQUIRED_FIELDS[action]:
            if f not in p:
                errors.append(f"proposal #{idx} ({p.get('id', '?')}) action='{action}' missing field: {f}")
    elif action:
        errors.append(f"proposal #{idx} ({p.get('id', '?')}) unknown action: '{action}' (allowed: {list(ACTION_REQUIRED_FIELDS.keys())})")
    # Validate content_template doesn't contain triple backticks (breaks wake regex)
    if action == 'create_new' and 'content_template' in p:
        if '```' in p['content_template']:
            errors.append(f"proposal #{idx} ({p.get('id', '?')}) content_template contains triple backticks — use ~~~~ or quadruple backticks instead")
    return errors


def build_md(payload):
    lines = [
        f"# Dream Report — {payload['date']}",
        f"**Generated:** {payload['timestamp_iso']}",
        f"**Memory dir:** {payload['memory_dir']}",
        f"**Cwd:** {payload['cwd']}",
        f"**Files reviewed:** {payload['files_count']}",
        "",
        "## Insights",
    ]
    for b in payload['insights']:
        lines.append(f"- {b}")
    lines.append("")
    lines.append("## Proposals")

    # Group by category prefix
    by_cat = {}
    for p in payload['proposals']:
        cat = p['id'][0]
        by_cat.setdefault(cat, []).append(p)

    for cat in ['M', 'N', 'I', 'O']:
        if cat not in by_cat:
            continue
        lines.append("")
        lines.append(f"### {cat} — {CATEGORY_NAMES[cat]}")
        for p in by_cat[cat]:
            lines.append("")
            lines.append(f"#### {p['id']}. {p.get('title', '(no title)')}")
            lines.append("")
            lines.append("```json")
            lines.append(json.dumps(p, indent=2, ensure_ascii=False))
            lines.append("```")

    if payload.get('apply_order'):
        lines.append("")
        lines.append("## Apply order recommendation")
        for i, group in enumerate(payload['apply_order'], 1):
            if isinstance(group, list):
                lines.append(f"{i}. {', '.join(group)}")
            else:
                lines.append(f"{i}. {group}")

    return '\n'.join(lines) + '\n'


def build_html(payload, template_path):
    template = Path(template_path).read_text(encoding='utf-8')

    # __INSIGHTS_HTML__: <ul><li>escaped</li></ul>
    insights_html = '<ul>' + ''.join(
        f'<li>{html.escape(b)}</li>' for b in payload['insights']
    ) + '</ul>'

    # __PROPOSALS_JSON__: convert proposals to user-friendly shape
    # - Russian field names
    # - Short summary on top, technical details collapsed
    # - Long values truncated with "..."
    ACTION_LABELS = {
        'update': 'Обновить файл',
        'merge': 'Слить файлы в один',
        'delete': 'Удалить (очистить контент)',
        'soft_delete': 'Переместить в TRASH',
        'create_new': 'Создать новый файл',
        'extract': 'Извлечь часть в memory',
        'remove_links': 'Удалить ссылки из индекса',
        'shorten_lines': 'Сократить строки индекса',
        'add_links': 'Добавить ссылки в индекс',
        'purge_trash': 'Очистить TRASH (>30 дней)',
    }
    # Semantic class for color coding + icon (modern UI)
    ACTION_META = {
        'update': ('neutral', '✎'),
        'merge': ('constructive', '⊕'),
        'delete': ('destructive', '⌫'),
        'soft_delete': ('destructive', '↩'),
        'create_new': ('constructive', '✨'),
        'extract': ('constructive', '⇲'),
        'remove_links': ('neutral', '−'),
        'shorten_lines': ('neutral', '✂'),
        'add_links': ('neutral', '+'),
        'purge_trash': ('destructive', '🗑'),
    }
    KEY_LABELS = {
        'action': 'Действие',
        'rationale': 'Зачем',
        'files': 'Файлы',
        'target': 'Куда',
        'project': 'Проект',
        'type': 'Тип memory',
        'diff_preview': 'Что изменится',
        'content_template': 'Содержимое нового файла',
        'links_to_remove': 'Ссылки',
        'links_to_add': 'Ссылки',
        'lines_to_shorten': 'Строки',
        'source_note': 'Источник',
        'target_memory_file': 'Цель',
        'what_to_extract': 'Извлечь',
        'source_action': 'С источником',
    }
    PRIMARY_KEYS = ['action', 'project', 'files', 'target', 'rationale']  # show first
    COLLAPSED_KEYS = {'content_template', 'diff_preview', 'lines_to_shorten', 'links_to_add', 'links_to_remove'}  # in <details>

    def truncate(s, limit=300):
        s = str(s)
        if len(s) <= limit:
            return s
        return s[:limit].rstrip() + ' …'

    def render_value_text(v):
        if isinstance(v, list):
            return v
        if isinstance(v, dict):
            return [f'{k}: {val}' for k, val in v.items()]
        return str(v) if v is not None else ''

    ui_proposals = []
    for p in payload['proposals']:
        # Build summary line: action label + main object
        action = p.get('action', '')
        action_label = ACTION_LABELS.get(action, action)
        main_obj = p.get('target') or (p.get('files', [None])[0] if p.get('files') else '')
        if isinstance(main_obj, str) and main_obj:
            summary = f'{action_label} → {main_obj}'
        else:
            summary = action_label

        # Build details: primary first, then rest, then collapsed
        primary = []
        secondary = []
        collapsed = []
        for k in p:
            if k in ('id', 'title', 'category', 'action'):
                continue
            label = KEY_LABELS.get(k, k)
            v = p[k]
            entry = {'label': label, 'key': k}
            if isinstance(v, list):
                entry['type'] = 'list'
                items = []
                for x in v:
                    if isinstance(x, dict):
                        items.append(' | '.join(f'{kk}: {vv}' for kk, vv in x.items()))
                    else:
                        items.append(str(x))
                entry['items'] = items
            elif isinstance(v, dict):
                entry['type'] = 'list'
                entry['items'] = [f'{kk}: {vv}' for kk, vv in v.items()]
            else:
                text = str(v) if v is not None else ''
                if k in COLLAPSED_KEYS and len(text) > 300:
                    entry['type'] = 'longtext'
                    entry['preview'] = truncate(text, 200)
                    entry['full'] = text
                else:
                    entry['type'] = 'text'
                    entry['text'] = truncate(text, 500) if k not in COLLAPSED_KEYS else text
            if k in COLLAPSED_KEYS:
                collapsed.append(entry)
            elif k in PRIMARY_KEYS:
                primary.append(entry)
            else:
                secondary.append(entry)

        meta_class, meta_icon = ACTION_META.get(action, ('neutral', '•'))
        # File count for chip display
        files = p.get('files', [])
        file_count = len(files) if isinstance(files, list) else 0

        ui_proposals.append({
            'id': p['id'],
            'title': p.get('title', '(no title)'),
            'summary': summary,
            'action_class': meta_class,
            'action_icon': meta_icon,
            'action_label': action_label,
            'file_count': file_count,
            'project': p.get('project', ''),  # global mode: project slug for filter
            'primary': primary,
            'secondary': secondary,
            'collapsed': collapsed,
        })

    # JSON + sanitize </ for inline-script safety
    proposals_json = json.dumps(ui_proposals, ensure_ascii=False).replace('</', '<\\/')

    mode = payload.get('mode', 'cwd')   # 'cwd' (default) or 'global'

    output = (
        template
        .replace('__DATE__', payload['date'])
        .replace('__MODE__', mode)
        .replace('__MEMORY_DIR__', html.escape(payload['memory_dir']))
        .replace('__CWD__', html.escape(payload['cwd']))
        .replace('__FILES_COUNT__', html.escape(payload['files_count']))
        .replace('__INSIGHTS_HTML__', insights_html)
        .replace('__PROPOSALS_JSON__', proposals_json)
    )
    return output


def main():
    if len(sys.argv) < 2:
        print("Usage: python build_report.py <payload.json>", file=sys.stderr)
        sys.exit(1)

    payload_path = sys.argv[1]
    payload = json.loads(Path(payload_path).read_text(encoding='utf-8'))

    # Validate required payload fields
    required = ['date', 'timestamp_iso', 'memory_dir', 'cwd', 'files_count', 'insights', 'proposals']
    missing = [f for f in required if f not in payload]
    if missing:
        print(f"Payload missing required fields: {missing}", file=sys.stderr)
        sys.exit(1)

    # Per-proposal validation
    all_errors = []
    for idx, p in enumerate(payload['proposals']):
        all_errors.extend(validate_proposal(p, idx))
    if all_errors:
        print("Proposal validation errors:", file=sys.stderr)
        for err in all_errors:
            print(f"  - {err}", file=sys.stderr)
        sys.exit(2)

    # Resolve template path: same dir as this script
    script_dir = Path(__file__).parent
    template_path = script_dir / 'template.html'
    if not template_path.exists():
        print(f"Template not found: {template_path}", file=sys.stderr)
        sys.exit(1)

    cwd = payload['cwd']
    date = payload['date']

    md_path = Path(cwd) / f"DREAM-REPORT-{date}.md"
    html_path = Path(cwd) / f"DREAM-REPORT-{date}.html"

    md_path.write_text(build_md(payload), encoding='utf-8')
    html_path.write_text(build_html(payload, template_path), encoding='utf-8')

    print(f"Wrote: {md_path}")
    print(f"Wrote: {html_path}")
    print(f"Proposals: {len(payload['proposals'])}, Insights: {len(payload['insights'])}")


if __name__ == '__main__':
    main()
