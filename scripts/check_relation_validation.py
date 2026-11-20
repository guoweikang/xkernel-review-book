"""Check axis separation, source sampling, and rejection of incomplete traces."""

import argparse
import hashlib
import json
from pathlib import Path

from prepare_relation_validation import relations


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path)
    args = parser.parse_args()
    trace = (args.run / 'trace.csv').read_text()
    rows = json.loads((args.run / 'relation-cards.json').read_text())
    assert rows == relations(trace)
    assert len(rows) == 28
    assert sum(row['finite_output_equivalence']['label'] == 'positive' for row in rows) == 3
    assert all(row['local_mechanism_sharing']['label'] == 'unknown' for row in rows)
    for row in rows:
        result = row['finite_output_equivalence']
        if result['label'] == 'negative':
            assert result['witness']['outputs'][0] != result['witness']['outputs'][1]
    for invalid in ['', '\n'.join(trace.splitlines()[1:]), trace + trace.splitlines()[0] + '\n']:
        try:
            relations(invalid)
        except ValueError:
            continue
        raise AssertionError('Invalid domain accepted')
    for report in json.loads((args.run / 'source-inventory.json').read_text()):
        files = report['files']
        assert len(files) == report['rust_files'] == len({item['path'] for item in files})
        for item in files:
            expected = hashlib.sha256(('relation-validation-v1:' + report['revision'] + ':' + item['path']).encode()).hexdigest()
            assert item['order'] == expected
        assert report['selected_paths'] == [item['path'] for item in sorted(files, key=lambda item: item['order'])[:4]]
        assert report['independent_test_eligible'] is False and report['split'] == 'unassigned'
    print('PASS: 28 separated relation cards, 3 invalid-domain controls, deterministic source selection; no inferred holdout status')


if __name__ == '__main__':
    main()
