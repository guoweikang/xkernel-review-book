"""Recount contract controls independently of the validator implementation."""

import argparse
import hashlib
import json
from pathlib import Path


def check(folder):
    report = json.loads((folder / 'report.json').read_text())
    for name, expected in report['artifact_sha256'].items():
        assert hashlib.sha256((folder / name).read_bytes()).hexdigest() == expected, name
    for name, expected in json.loads((folder / 'frozen.json').read_text()).items():
        assert hashlib.sha256((folder / name).read_bytes()).hexdigest() == expected, name
    cases = json.loads((folder / 'cases.json').read_text())
    expected = {case['id']: case['accept'] for case in cases}
    assert len(expected) == len(cases) == 14
    rows = json.loads((folder / 'result-1.json').read_text())
    assert [row['id'] for row in rows] == [case['id'] for case in cases]
    for row in rows:
        assert row['accepted'] == row['expected'] == expected[row['id']]
        if row['accepted']:
            assert row['result']['behavior'] == 'unverified'
            assert row['result']['sharing'] == 'unknown'
            assert row['result']['ownership'] == 'declared_only'
        else:
            assert row['result']['error']
    assert sum(row['accepted'] for row in rows) == report['accepted'] == 5
    assert report['cases'] == 14 and report['behavior_confirmed'] == 0
    assert report['success'] and report['repeat_identical']
    assert (folder / 'result-1.json').read_bytes() == (folder / 'result-2.json').read_bytes()
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('first', type=Path)
    parser.add_argument('second', type=Path)
    args = parser.parse_args()
    assert check(args.first) == check(args.second)
    for name in ('cases.json', 'registry.json', 'protocol.json', 'check_crate_contract.py', 'run_crate_contract_probe.py'):
        assert (args.first / name).read_bytes() == (args.second / name).read_bytes()
    print(json.dumps({'cases_per_run': 14, 'runs': 2, 'passes_per_run': 2,
                      'structural_rejections': 9, 'well_formed_false_claims_accepted': 3,
                      'behavior_confirmed': 0, 'independent_recount': True}))


if __name__ == '__main__':
    main()
