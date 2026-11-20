"""Check frozen cfg evidence, including deliberately failing controls."""

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    assert args.run_id and all(character.isalnum() or character in '-_' for character in args.run_id)
    folder = ROOT / 'research/evidence/runs' / args.run_id
    report = json.loads((folder / 'report.json').read_text())
    for path, expected in report['artifact_sha256'].items():
        assert hashlib.sha256((folder / path).read_bytes()).hexdigest() == expected, path
    manifest = json.loads((folder / 'manifest.json').read_text())
    source = (folder / 'sources/task/kspin/src/lock.rs').read_text()
    original = (folder / 'original.rs').read_text()
    for start, end in manifest['ranges'].values():
        assert source[start:end] in original
    records = json.loads((folder / 'executions.json').read_text())
    assert len(records) == 24 and len({row['id'] for row in records}) == 24
    for repeat in (1, 2):
        for variant in ('original', 'both_enabled', 'both_disabled'):
            rows = [row for row in records if row['repeat'] == repeat and row['variant'] == variant]
            assert {tuple(row['features']) for row in rows} == {(), ('smp',), ('stats',), ('stats', 'smp')}
            for row in rows:
                if variant == 'original':
                    assert row['compile_exit'] == row['execute_exit'] == 0
                    assert row['stdout'] == 'constructor assertions passed\n'
                else:
                    code = 'E0592' if variant == 'both_enabled' else 'E0599'
                    assert row['compile_exit'] != 0
                    assert code in (folder / (row['id'] + '.stderr')).read_text()
    print('PASS: source extraction, archive hashes, 24 compile outcomes, 8 executions, 16 expected failures')


if __name__ == '__main__':
    main()
