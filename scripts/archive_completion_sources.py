"""Archive primary completion sources at one fixed revision, without executing tests."""

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--repo', required=True, type=Path)
    args = parser.parse_args()
    if not args.run_id or any(not (char.isalnum() or char in '-_') for char in args.run_id):
        raise ValueError('invalid ID')
    root = Path(__file__).resolve().parents[1]
    folder = root / 'research/evidence/runs' / args.run_id
    folder.mkdir()
    protocol = root / 'research/protocols/completion-responsibility-v1.json'
    plan = json.loads(protocol.read_text())
    shutil.copy2(protocol, folder / 'protocol.json')
    shutil.copy2(__file__, folder / 'archiver.py')
    sources = []
    for name, path in plan['sources'].items():
        specification = plan['revision'] + ':' + path
        result = subprocess.run(['git', '-C', str(args.repo), 'show', specification], capture_output=True, timeout=30)
        (folder / (name + '.stderr')).write_bytes(result.stderr)
        if result.returncode:
            raise RuntimeError('source acquisition failed: ' + path)
        (folder / name).write_bytes(result.stdout)
        blob = subprocess.check_output(['git', '-C', str(args.repo), 'rev-parse', specification], timeout=30).decode().strip()
        computed = hashlib.sha1(b'blob ' + str(len(result.stdout)).encode() + b'\0' + result.stdout).hexdigest()
        if computed != blob:
            raise ValueError('Git blob identity mismatch')
        sources.append({'path': path, 'file': name, 'git_blob': blob, 'sha256': hashlib.sha256(result.stdout).hexdigest()})
    snapshot = root / 'research/evidence/runs/2026-11-16-contract-sample-01/pair-4-1-source.rs'
    assert snapshot.read_bytes() == (folder / 'wrapper.rs').read_bytes()
    report = {'revision': plan['revision'], 'sources': sources, 'tests_executed': 0,
              'selected_wrapper_identity_verified': True,
              'artifact_sha256': {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(folder.iterdir())}}
    (folder / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'sources': len(sources), 'tests_executed': 0, 'git_blob_and_wrapper_checks': True}))


if __name__ == '__main__':
    main()
