import csv
import hashlib
import json
import re
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / 'corrected'


def main():
    assert not (HERE / 'inspection.json').exists()
    tree = json.loads((DATA / 'tree.json').read_text())
    assert tree['truncated'] is False
    tables = {}
    for path in sorted(DATA.glob('*.csv')):
        rows = list(csv.DictReader(path.open(encoding='utf-8-sig')))
        tables[path.name] = {'parsed_rows': len(rows), 'columns': list(rows[0]),
                             'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
        if path.name.startswith('biggroum'):
            tables[path.name]['rows'] = [{'row': index, 'title': row['title'],
                                        'has_code': bool(row['code_snippet']),
                                        'reported_result': row['recommendation_result'],
                                        'source_url': row['recommendation_code_snippet_url']}
                                       for index, row in enumerate(rows, 1)]
            first = next((index, row) for index, row in enumerate(rows, 1)
                         if row['recommendation_code_snippet_url'])
    row_number, row = first
    link = row['recommendation_code_snippet_url']
    match = re.fullmatch(r'https://github.com/([^/]+/[^/]+)/blob/([0-9a-f]{40})/(.+)#L(\d+),L(\d+)', link)
    assert match, link
    repo, commit, filename, start, end = match.groups()
    raw = f'https://raw.githubusercontent.com/{repo}/{commit}/{filename}'
    origin = {'row': row_number, 'url': link, 'raw_url': raw, 'range_inclusive': [int(start), int(end)]}
    try:
        with urllib.request.urlopen(raw, timeout=40) as response:
            source = response.read(1_000_001)
        assert len(source) <= 1_000_000
        (HERE / 'first-result-source.java').write_bytes(source)
        selected = ''.join(source.decode('utf-8').splitlines(keepends=True)[int(start)-1:int(end)])
        (HERE / 'first-result-lines.txt').write_text(selected)
        origin.update(status='downloaded', sha256=hashlib.sha256(source).hexdigest(), bytes=len(source))
    except Exception as error:
        origin.update(status='failed', error=repr(error))
    result = {'tree_truncated': False, 'tree_entries': len(tree['tree']),
              'json_blobs': [entry['path'] for entry in tree['tree'] if entry['type'] == 'blob' and entry['path'].endswith('.json')],
              'tables': tables, 'first_result_source': origin,
              'algorithm_runs': 0, 'limitation': 'CSV labels are published original-corpus outcomes, not replay scores or ground truth for a new corpus.'}
    (HERE / 'inspection.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({key: value for key, value in result.items() if key != 'tables'}, indent=2))


if __name__ == '__main__':
    main()
