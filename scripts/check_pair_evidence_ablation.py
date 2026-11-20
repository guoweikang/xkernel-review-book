"""Check pair identity, factorial completeness, and no unsupported upgrades."""

import argparse
import hashlib
import itertools
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folder', type=Path)
    args = parser.parse_args()
    folder = args.folder
    report = json.loads((folder / 'report.json').read_text())
    for name, digest in report['artifact_sha256'].items():
        assert hashlib.sha256((folder / name).read_bytes()).hexdigest() == digest
    for name, digest in json.loads((folder / 'frozen.json').read_text()).items():
        assert hashlib.sha256((folder / name).read_bytes()).hexdigest() == digest
    cases = json.loads((folder / 'cases.json').read_text())
    ids = {case['id'] for case in cases}
    assert len(ids) == 2
    for case in cases:
        card = json.loads((folder / (case['id'] + '-card.json')).read_text())
        assert [member['id'] for member in card['members']] == [member['id'] for member in case['members']]
        for index, member in enumerate(card['members'], 1):
            snippet = folder / f"{case['id']}-{index}.rs"
            assert hashlib.sha256(snippet.read_bytes()).hexdigest() == member['sha256']
            if case['common_domain'] is not None:
                assert snippet.read_text() in (folder / 'probe.rs').read_text()
    rows = json.loads((folder / 'result-1.json').read_text())
    assert len(rows) == 8
    assert {(row['id'], row['contracts_requested'], row['traces_requested']) for row in rows} == set(itertools.product(ids, (False, True), (False, True)))
    raw = [json.loads(line) for line in (folder / 'debug-1-execute.stdout').read_text().splitlines()]
    expected_events = {row['adapter']: row['calls'] for row in raw if row['scenario'] == 'short_success'}
    assert [len(call['payload']) for call in expected_events['scalar']] == [2, 2]
    assert [len(call['payload']) for call in expected_events['command']] == [4]
    for row in rows:
        assert row['local_sharing'] == 'unknown' and row['optimization_benefit'] == 'unverified'
        assert bool(row['declaration_differences']) == row['contracts_requested']
        available = row['traces_requested'] and row['id'] == 'DEV-STREAM-COMMAND'
        assert row['trace_available'] == available
        assert row['behavior_status'] == ('bounded_observed_difference' if available else 'unknown')
        if available:
            assert row['witness']['callback_events'] == expected_events
        else:
            assert row['witness'] is None
    assert (folder / 'result-1.json').read_bytes() == (folder / 'result-2.json').read_bytes()
    print(json.dumps({'pairs': 2, 'conditions': 8, 'repeat_identical': True,
                      'source_bodies_bound_to_trace_harness': True,
                      'unmapped_pair_not_upgraded': True, 'detector_accuracy_measured': False}))


if __name__ == '__main__':
    main()
