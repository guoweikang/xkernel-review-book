"""Recompute per-page method counts from frozen inputs and accepted snapshots."""

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read_counts(value):
    assert value.startswith('{') and value.endswith('}')
    if value == '{}':
        return {}
    result = {}
    for item in value[1:-1].split(', '):
        name, count = item.rsplit('=', 1)
        assert name not in result
        result[name] = int(count)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('batch', type=Path)
    args = parser.parse_args()
    batch = args.batch
    manifest = json.loads((batch / 'manifest.json').read_text())
    assert hashlib.sha256((batch / 'manifest.json').read_bytes()).hexdigest() == (batch / 'manifest.sha256').read_text().strip()
    vocabulary = {}
    for line in (batch / 'declared-method-input.tsv').read_text().splitlines():
        owner, methods = line.split('\t')
        vocabulary[owner] = set(methods.split(',')) if methods else set()
    reports = []
    for run in manifest['runs']:
        root = ROOT / 'research/evidence/runs' / run['id']
        accepted = defaultdict(lambda: defaultdict(set))
        for line in (root / 'trace-accepted.tsv').read_text().splitlines():
            page, module, owner = line.split('\t')
            assert owner not in accepted[int(page)][module]
            accepted[int(page)][module].add(owner)
        pages = [int(line) for line in (root / 'trace-pages.tsv').read_text().splitlines()]
        assert pages == list(range(1, len(pages) + 1)) and len(pages) <= 200
        seen = set()
        query_count = 0
        capacity = {}
        for line in (root / 'trace-queries.tsv').read_text().splitlines():
            page_text, module, size, budget, serialized, raw, parsed = line.split('\t')
            page = int(page_text)
            assert (page, module) not in seen
            seen.add((page, module))
            owners = accepted[page][module]
            assert int(size) == len(owners)
            expected = Counter()
            if run['condition'].endswith('D'):
                for owner in owners:
                    expected.update(vocabulary[owner])
            assert read_counts(serialized) == dict(expected), (run['id'], page, module)
            if module in capacity:
                assert capacity[module] == int(budget) + len(owners)
            capacity[module] = int(budget) + len(owners)
            assert raw and parsed
            query_count += 1
        assert query_count == len(pages) * 6
        final_pairs = {tuple(line.split('\t')) for line in (root / 'acceptedMappings.tsv').read_text().splitlines()}
        snapshot_pairs = {(owner, module) for module, owners in accepted[pages[-1]].items() for owner in owners}
        assert snapshot_pairs == final_pairs
        reports.append({'run': run['id'], 'pages_including_terminal': len(pages),
                        'queries': query_count, 'recomputed_counts_match': True})
    assert read_counts('{}') == {}
    assert read_counts('{read=2, write=1}') == {'read': 2, 'write': 1}
    try:
        read_counts('{read=1, read=2}')
    except AssertionError:
        pass
    else:
        raise AssertionError('Duplicate method count accepted')
    print(json.dumps({'runs': reports, 'scope': 'trace consistency, not semantic correctness'}, indent=2))


if __name__ == '__main__':
    main()
