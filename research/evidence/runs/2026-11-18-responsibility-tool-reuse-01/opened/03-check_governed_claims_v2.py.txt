"""Audit claim artifacts against frozen Git sources and a repeated build."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', required=True)
    parser.add_argument('--repeat', required=True)
    parser.add_argument('--repo', required=True)
    args = parser.parse_args()
    run = ROOT / args.run
    repeat = ROOT / args.repeat
    report = json.loads((run / 'report.json').read_text())
    files = {str(path.relative_to(run)) for path in run.rglob('*') if path.is_file()}
    repeated_files = {str(path.relative_to(repeat)) for path in repeat.rglob('*') if path.is_file()}
    if files != repeated_files:
        raise ValueError('repeat file set differs')
    for relative in files:
        data = (run / relative).read_bytes()
        if data != (repeat / relative).read_bytes():
            raise ValueError(f'repeat differs: {relative}')
        if relative in report['artifact_sha256']:
            if hashlib.sha256(data).hexdigest() != report['artifact_sha256'][relative]:
                raise ValueError(f'artifact hash differs: {relative}')
    if files != set(report['artifact_sha256']) | {'report.json'}:
        raise ValueError('artifact inventory differs')
    plan = json.loads((run / 'protocol.json').read_text())
    claims = json.loads((run / 'claims.json').read_text())
    checked = set()
    for claim in claims:
        evidence = claim['evidence']
        if evidence is None:
            continue
        archived = ROOT / evidence['path']
        if claim['source'] == 'packet':
            packet = json.loads((ROOT / plan['parent_run'] / claim['packet'] / 'packet.json').read_text())
            source_path = packet['entity_identity']['path']
        else:
            source_path = evidence['path'].split('/same-revision/', 1)[1]
        identity = f"{claim['revision']}:{source_path}"
        original = subprocess.check_output(['git', '-C', args.repo, 'show', identity])
        if archived.read_bytes() != original:
            raise ValueError(f'Git source differs: {identity}')
        start, end = evidence['lines']
        if ''.join(original.decode().splitlines(keepends=True)[start - 1:end]) != evidence['excerpt']:
            raise ValueError(f'excerpt differs: {claim["id"]}')
        checked.add(identity)
    print(json.dumps({'repeat_identical_files': len(files), 'git_sources_verified': len(checked),
                      'claims': len(claims), 'semantic_truth_validated': False}, indent=2))


if __name__ == '__main__':
    main()
