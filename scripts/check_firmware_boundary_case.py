"""Verify archive integrity and deterministic collection, not semantic labels."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--repo', type=Path, required=True)
    args = parser.parse_args()
    report_bytes = (args.run / 'report.json').read_bytes()
    report = json.loads(report_bytes)
    count = 0
    for label, snapshot in report['snapshots'].items():
        for item in snapshot['files']:
            content = (args.run / label / item['path']).read_bytes()
            assert len(content) == item['bytes']
            assert hashlib.sha256(content).hexdigest() == item['sha256']
            count += 1
    for filename, key in [('historical.patch', 'patch_sha256'),
                          ('collector.py', 'collector_sha256')]:
        assert hashlib.sha256((args.run / filename).read_bytes()).hexdigest() == report[key]
    with tempfile.TemporaryDirectory() as temporary:
        output = Path(temporary) / 'repeat'
        command = [sys.executable, str(args.run / 'collector.py'), '--repo', str(args.repo),
                   '--current', report['revisions']['current'], '--output', str(output)]
        subprocess.run(command, check=True, stdout=subprocess.DEVNULL)
        assert (output / 'report.json').read_bytes() == report_bytes
        repeated = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        assert repeated.returncode != 0
        assert (output / 'report.json').read_bytes() == report_bytes
    print(f'PASS: {count} source hashes; patch/collector hashes; repeat identity; overwrite refused')


if __name__ == '__main__':
    main()
