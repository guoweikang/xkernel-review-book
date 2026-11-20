"""Recount executions and replay reported first counterexamples without generator."""

import argparse
import hashlib
import itertools
import json
from pathlib import Path
import re


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folder', type=Path)
    args = parser.parse_args()
    folder = args.folder
    report = json.loads((folder / 'report.json').read_text())
    for name, digest in report['artifact_sha256'].items():
        assert hashlib.sha256((folder / name).read_bytes()).hexdigest() == digest, name
    for name, digest in json.loads((folder / 'frozen.json').read_text()).items():
        assert hashlib.sha256((folder / name).read_bytes()).hexdigest() == digest, name
    observations = report['observations']
    expected_cells = set(itertools.product(('role', 'well_formed_role_swap'), ('original', 'drop_preserved_type'), ('debug', 'release'), (1, 2)))
    assert {(row['declaration'], row['variant'], row['mode'], row['repeat']) for row in observations} == expected_cells
    assert len(observations) == 16
    witnesses = {}
    for row in observations:
        succeeds = row['declaration'] == 'role' and row['variant'] == 'original'
        assert row['returncode'] == row['expected_returncode'] == (0 if succeeds else 101)
        assert row['matched_expectation']
        text = (folder / (row['id'] + '.stdout')).read_text()
        assert ('1 passed; 0 failed' if succeeds else '0 passed; 1 failed') in text
        if succeeds:
            continue
        match = re.search(r'preserve:(\w+) bits=(\d+) permission=(\d+)\s+left: (\d+)\s+right: (\d+)', text)
        assert match, row['id']
        field, bits, permission, actual, expected = match.groups()
        bits, permission, actual, expected = map(int, (bits, permission, actual, expected))
        assert 0 <= bits <= 65535 and permission in (0, 1, 0o644, 0o755, 0o4000, 0o7777)
        mask = {'permission_bits': 0o7777, 'file_type_bits': 0o170000}[field]
        result = permission & 0o7777
        if row['variant'] == 'original':
            result |= bits & 0o170000
        assert actual == result & mask and expected == bits & mask and actual != expected
        cell = row['declaration'] + '/' + row['variant']
        witness = [field, bits, permission, actual, expected]
        if cell in witnesses:
            assert witnesses[cell] == witness
        witnesses[cell] = witness
    assert len(report['rejected_inputs']) == 2
    assert {row['id'] for row in report['rejected_inputs']} == {'missing_preserve', 'unmapped_field'}
    assert report['success'] and report['sharing'] == 'unknown'
    print(json.dumps({'executions': 16, 'bounded_passes': 4, 'counterexample_runs': 12,
                      'replayed_counterexamples': witnesses, 'repeat_and_mode_witnesses_match': True,
                      'production_correctness_proven': False}, indent=2))


if __name__ == '__main__':
    main()
