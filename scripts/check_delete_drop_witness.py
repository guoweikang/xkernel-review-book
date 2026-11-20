"""Reconstruct the frozen Drop witness results from raw process output."""

import argparse
import hashlib
import json
from pathlib import Path


def check(root):
    result = json.loads((root / 'results.json').read_text())
    raw_runs = []
    for mode in ('debug', 'opt'):
        binary = root / mode / 'witness'
        if not binary.exists():
            relocation = json.loads((root / 'binary-relocation.json').read_text())
            binary = root / relocation[mode]['relative_destination']
        assert hashlib.sha256(binary.read_bytes()).hexdigest() == result['builds'][mode]['binary_sha256']
        rows = []
        for line in (root / mode / 'execute.stdout').read_text().splitlines():
            condition, variant, outcome, events = line.split('\t')
            rows.append({'condition': condition, 'variant': variant, 'outcome': outcome,
                         'events': events.split(',')})
        reported = [{key: row[key] for key in ('condition', 'variant', 'outcome', 'events')}
                    for row in result['builds'][mode]['observations']]
        assert rows == reported
        assert len(rows) == 6
        cases = {(row['condition'], row['variant']): row for row in rows}
        assert len(cases) == 6
        for condition in ('type_mismatch', 'callback_error', 'success'):
            original = cases[(condition, 'original')]
            naive = cases[(condition, 'naive')]
            assert original['outcome'] == naive['outcome']
            if condition == 'type_mismatch':
                assert original['outcome'] == 'WrongType'
                assert original['events'].index('may_drop') > original['events'].index('parent_unlock')
                assert naive['events'].index('may_drop') < naive['events'].index('victim_unlock')
                assert 'may_call' not in original['events'] + naive['events']
                assert 'backend' not in original['events'] + naive['events']
            else:
                assert original['events'] == naive['events']
        raw_runs.append(rows)
    assert raw_runs[0] == raw_runs[1]
    return {'observations': 12, 'raw_report_equal': True, 'debug_opt_equal': True,
            'same_type_error_different_drop_order': True, 'kernel_behavior_proven': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path)
    args = parser.parse_args()
    print(json.dumps(check(args.run), indent=2))
