"""Independently verify the frozen callback replay matrix and evidence identities."""

import argparse
import hashlib
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folder', type=Path)
    args = parser.parse_args()
    folder = args.folder
    report = json.loads((folder / 'report.json').read_text())
    for name, expected in report['artifact_sha256'].items():
        assert hashlib.sha256((folder / name).read_bytes()).hexdigest() == expected, name
    for name, expected in json.loads((folder / 'frozen.json').read_text()).items():
        assert hashlib.sha256((folder / name).read_bytes()).hexdigest() == expected, name
    results = json.loads((folder / 'results.json').read_text())
    assert len(results) == report['evaluations'] == 96
    identities = {(row['file'], row['declaration'], row['scenario'], row['adapter']) for row in results}
    assert len(identities) == 96
    counts = {'observed_satisfied': 0, 'counterexample': 0, 'outside_declared_domain': 0}
    reference = None
    for filename in report['groups']:
        raw = [json.loads(line) for line in (folder / filename).read_text().splitlines()]
        traces = {(row['scenario'], row['adapter']): row for row in raw}
        assert len(traces) == len(raw) == 12
        selected = [row for row in results if row['file'] == filename]
        normalized = [{key: value for key, value in row.items() if key != 'file'} for row in selected]
        if reference is not None:
            assert normalized == reference
        reference = normalized
        for row in selected:
            scenario, adapter = row['scenario'], row['adapter']
            trace = traces[(scenario, adapter)]
            if scenario in ('empty', 'oversize'):
                expected = 'outside_declared_domain'
                assert row['checks'] == {}
            else:
                passes = (row['declaration'] == 'once' and (adapter == 'command' or scenario in ('complete', 'callback_fault')))
                passes |= row['declaration'] == 'twice' and adapter == 'command' and scenario == 'short_then_fault'
                expected = 'observed_satisfied' if passes else 'counterexample'
                assert all(row['checks'].values()) == passes
                assert row['callbacks'] == len(trace['calls'])
                assert row['collection_failed'] == (scenario == 'short_then_fault')
                assert row['checks']['whole_payload'] == all(call['payload'] == [0, 1, 2, 3] for call in trace['calls'])
                if scenario == 'callback_fault':
                    assert trace['result'].startswith('Err') and len(trace['calls']) == 1
                    assert not row['collection_failed']
            assert row['status'] == expected
            counts[expected] += 1
    assert counts == {'observed_satisfied': 28, 'counterexample': 36, 'outside_declared_domain': 32}
    assert report['new_rust_executions'] == 0 and report['sharing'] == 'unknown'
    print(json.dumps({'counts': counts, 'mode_and_repeat_decisions_identical': True,
                      'callback_error_not_collection_error': True, 'new_rust_executions': 0}, indent=2))


if __name__ == '__main__':
    main()
