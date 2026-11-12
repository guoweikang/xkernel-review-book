"""Inventory publishable Git inputs, reject large files and high-confidence credential patterns."""

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
PATTERNS = [rb'-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----',
            rb'gh[pousr]_[A-Za-z0-9]{36,}', rb'github_pat_[A-Za-z0-9_]{70,}',
            rb'AKIA[0-9A-Z]{16}']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--output', type=Path)
    mode.add_argument('--verify', type=Path)
    args = parser.parse_args()
    if args.verify:
        snapshot = json.loads(args.verify.read_text())
        for record in snapshot['files']:
            path = ROOT / record['path']
            content = path.read_bytes()
            assert len(content) == record['bytes'] and hashlib.sha256(content).hexdigest() == record['sha256'], record['path']
        print('PASS snapshot:', len(snapshot['files']), 'files')
        return
    assert not args.output.exists(), 'Will not overwrite snapshot'
    paths = subprocess.check_output(['git', 'ls-files', '-z', '--cached', '--others', '--exclude-standard'], cwd=ROOT).decode().split('\0')
    records = []
    blocked = []
    for name in sorted(set(filter(None, paths))):
        if name.startswith('research/archive/snapshots/'):
            continue
        path = ROOT / name
        if not path.is_file():
            continue
        if path.is_symlink():
            blocked.append([name, 'symlink requires review'])
            continue
        content = path.read_bytes()
        if len(content) > 50 * 1024 * 1024:
            blocked.append([name, 'over 50MiB'])
        if any(re.search(pattern, content) for pattern in PATTERNS):
            blocked.append([name, 'potential credential; contents not printed'])
        records.append({'path': name, 'bytes': len(content), 'sha256': hashlib.sha256(content).hexdigest()})
    if blocked:
        raise SystemExit(json.dumps({'blocked': blocked}, indent=2))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    result = {'schema': 'public-research-snapshot/1',
              'scope': 'tracked and nonignored files, excluding snapshot manifests themselves; cache not included',
              'total_bytes': sum(record['bytes'] for record in records), 'files': records,
              'limits': 'Pattern scan is not exhaustive security or licensing review; hashes are not trusted timestamps'}
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'files': len(records), 'bytes': result['total_bytes']}))


if __name__ == '__main__':
    main()
