import argparse
import hashlib
import itertools
import json
from pathlib import Path

from audit_candidate_dependence import group


ROOT = Path(__file__).resolve().parents[1]


def check(run):
    report = json.loads((run / 'report.json').read_text())
    for name, expected in report['artifacts_sha256'].items():
        assert hashlib.sha256((run / name).read_bytes()).hexdigest() == expected
    cases = json.loads((run / 'cases.json').read_text())
    graphs = json.loads((run / 'graphs.json').read_text())
    previous = None
    for level, graph in graphs.items():
        adjacent = {case['case_id']: set() for case in cases}
        for left, right in itertools.combinations(cases, 2):
            linked = any(first['id'] == second['id'] or (level != 'endpoint' and first['sha256'] == second['sha256']) or (level == 'source_file' and (first['path'], first['source_sha256']) == (second['path'], second['source_sha256'])) for first in left['members'] for second in right['members'])
            if linked:
                adjacent[left['case_id']].add(right['case_id'])
                adjacent[right['case_id']].add(left['case_id'])
        remaining = set(adjacent)
        components = []
        while remaining:
            pending = [min(remaining)]
            reached = set()
            while pending:
                identity = pending.pop()
                if identity not in reached:
                    reached.add(identity)
                    pending.extend(adjacent[identity] - reached)
            remaining -= reached
            components.append(sorted(reached))
        assert sorted(components) == graph['components']
        assert report['graphs'][level]['sizes'] == sorted(map(len, components), reverse=True)
        if previous is not None:
            assert all(any(set(old) <= set(new) for new in components) for old in previous)
        previous = components
    controls = [
        {'case_id': 'first', 'members': [{'id': 'a', 'sha256': 'body-a', 'path': 'one', 'source_sha256': 'source-one'}]},
        {'case_id': 'bridge', 'members': [{'id': 'a', 'sha256': 'body-a', 'path': 'one', 'source_sha256': 'source-one'}, {'id': 'b', 'sha256': 'body-b', 'path': 'two', 'source_sha256': 'source-two'}]},
        {'case_id': 'last', 'members': [{'id': 'b', 'sha256': 'body-b', 'path': 'two', 'source_sha256': 'source-two'}]},
        {'case_id': 'copy', 'members': [{'id': 'c', 'sha256': 'body-b', 'path': 'three', 'source_sha256': 'source-three'}]},
        {'case_id': 'neighbor', 'members': [{'id': 'd', 'sha256': 'body-d', 'path': 'three', 'source_sha256': 'source-three'}]},
    ]
    assert [len(group(controls, level)['components']) for level in ('endpoint', 'exact_body', 'source_file')] == [3, 2, 1]
    try:
        group(controls + controls[:1], 'endpoint')
    except ValueError:
        pass
    else:
        raise AssertionError('Duplicate IDs accepted')
    print(f'PASS: {len(cases)} cases, three independently recomputed partitions, bridge/copy/file controls and duplicate rejection')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', required=True)
    args = parser.parse_args()
    check(ROOT / 'research/evidence/runs' / args.run)
