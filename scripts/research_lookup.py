"""Inventory and literal retrieval over local research assets without a stale cache."""

import argparse
from collections import Counter
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEXT_LIMIT = 2 * 1024 * 1024
TEXT_SUFFIXES = {'.md', '.json', '.jsonl', '.txt', '.log', '.py', '.rs',
                 '.sh', '.toml', '.csv', '.patch', '.yaml', '.yml', '.ini'}


def inventory(root):
    paths = set()
    for folder in ('research', 'chapters', 'scripts', '.agents'):
        for path in (root / folder).rglob('*'):
            relative = path.relative_to(root)
            if ('__pycache__' in relative.parts
                    or relative.parts[:3] == ('research', 'evidence', 'originals')):
                continue
            if path.is_file() or path.is_symlink():
                paths.add(relative.as_posix())
    if (root / 'AGENTS.md').exists():
        paths.add('AGENTS.md')
    topics = {}
    catalog = root / 'research/catalog.json'
    if catalog.exists():
        for group in json.loads(catalog.read_text())['groups']:
            for document in group['documents']:
                topics['research/' + document] = group['id']
    declarations = {}
    manifest = root / 'research/evidence/manifest.json'
    if manifest.exists():
        for number, record in enumerate(json.loads(manifest.read_text())['records']):
            if not record.get('path'):
                name = f'research/evidence/manifest.json#record-{number}'
                paths.add(name)
                declarations[name] = [record]
                continue
            relative = Path('research/evidence') / record['path']
            if relative.is_absolute() or '..' in relative.parts:
                raise ValueError('Unsafe manifest path: ' + str(relative))
            name = relative.as_posix()
            paths.add(name)
            declarations.setdefault(name, []).append(record)
    for name in sorted(paths):
        path = root / name
        source_records = declarations.get(name, [])
        kind = ('source' if source_records else 'run' if name.startswith('research/evidence/runs/')
                else 'tool' if name.startswith('scripts/') else 'document')
        topic = topics.get(name, '')
        metadata = json.dumps(source_records, ensure_ascii=False)
        text = ''
        size = None
        if source_records and not source_records[0].get('path'):
            status = 'no-local-path'
        elif not path.resolve().is_relative_to(root.resolve()):
            status = 'outside-root'
        elif path.is_symlink():
            status = 'symlink-not-read'
        elif not path.is_file():
            status = 'missing'
        else:
            size = path.stat().st_size
            if path.suffix.lower() not in TEXT_SUFFIXES:
                status = 'metadata-only-format'
            elif size > TEXT_LIMIT:
                status = 'metadata-only-size'
            else:
                try:
                    text = path.read_text(encoding='utf-8')
                    status = 'text'
                except (UnicodeError, OSError):
                    status = 'unreadable-text'
        yield {'path': name, 'kind': kind, 'topic': topic, 'status': status,
               'bytes': size, 'declarations': source_records, 'metadata': metadata,
               'text': text}


def retrieve(records, terms, topic='', kind='', require_all=False):
    folded = [term.casefold() for term in terms]
    hits = []
    for record in records:
        if topic and record['topic'] != topic:
            continue
        if kind and record['kind'] != kind:
            continue
        header = (record['path'] + ' ' + record['metadata']).casefold()
        body = record['text'].casefold()
        matched = [term for term in folded if term in header or term in body]
        if not matched or (require_all and len(matched) != len(folded)):
            continue
        excerpts = []
        for number, line in enumerate(record['text'].splitlines(), 1):
            positions = [line.casefold().find(term) for term in folded
                         if term in line.casefold()]
            if positions:
                start = max(0, min(positions) - 100)
                excerpts.append({'line': number, 'text': line[start:start + 360]})
            if len(excerpts) == 3:
                break
        hits.append({key: record[key] for key in ('path', 'kind', 'topic', 'status')}
                    | {'matched_terms': matched, 'excerpts': excerpts})
    return sorted(hits, key=lambda hit: (-len(hit['matched_terms']), hit['path']))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('terms', nargs='*', help='Literal terms; OR by default, supports Chinese')
    parser.add_argument('--all', action='store_true', dest='require_all')
    parser.add_argument('--topic', default='')
    parser.add_argument('--kind', choices=['document', 'source', 'run', 'tool'], default='')
    parser.add_argument('--limit', type=int, default=20)
    parser.add_argument('--inventory', action='store_true')
    args = parser.parse_args()
    if args.limit < 1 or (not args.inventory and not args.terms):
        parser.error('Use --inventory or search terms, and a positive --limit')
    records = list(inventory(ROOT))
    coverage = dict(Counter(record['status'] for record in records))
    documents = '\n'.join(record['text'] for record in records
                          if record['path'].endswith('.md') and record['kind'] == 'document')
    run_dirs = sorted({str(Path(record['path']).parent).split('/')[3]
                       for record in records if record['kind'] == 'run'})
    navigation_gaps = {
        'run_ids_not_mentioned_in_documents': [name for name in run_dirs if name not in documents],
        'tool_names_not_mentioned_in_documents': [record['path'] for record in records
                                                 if record['kind'] == 'tool'
                                                 and Path(record['path']).name not in documents],
    }
    report = {
        'schema': 'research-lookup/1',
        'query': vars(args),
        'assets': len(records), 'coverage': coverage,
        'navigation_gaps': navigation_gaps,
        'limits': ['Literal retrieval, not semantic recall or scientific verification.',
                   'Topics apply only to catalog documents, not inferred run/source topics.',
                   'Originals only enumerated via evidence/manifest.json; PDFs are metadata-only.',
                   '.build, .tools, dist, external repos and unregistered originals are excluded.',
                   'No cache; current files are read each invocation, not an atomic snapshot.',
                   'Manifest hashes/statuses are declarations, not reverified by this command.'],
    }
    if args.inventory:
        report['records'] = [{key: value for key, value in record.items()
                              if key not in ('text', 'metadata')} for record in records]
    else:
        hits = retrieve(records, args.terms, args.topic, args.kind, args.require_all)
        report.update({'total_hits': len(hits), 'returned': min(args.limit, len(hits)),
                       'omitted_hits': max(0, len(hits) - args.limit), 'hits': hits[:args.limit]})
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
