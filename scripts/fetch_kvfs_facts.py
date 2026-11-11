"""Fetch exactly the archived x86_64 kvfs facts identity, without disabling TLS checks."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess

from audit_facts_sample import audit


ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--repo', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    manifest_path = ROOT / 'research/evidence/originals/T11-ci-3885/kplat-x86_64-manifest.json'
    manifest = json.loads(manifest_path.read_text())
    entry = next(entry for entry in manifest['crates'] if entry['package'] == 'kvfs')
    if entry['sha256'] != '7f03f02be405737749cff559b5524a399b05bbbb0b055c7c55483966d49eb23a':
        raise ValueError('Expected kvfs identity changed')
    url = 'https://jenkins.openkylin.top/job/x-kernel-ci-test/3885/artifact/artifacts/facts/kplat-x86_64/' + entry['file']
    temporary = args.output / 'download.partial'
    command = ['curl', '-q', '--fail', '--silent', '--show-error', '--location',
               '--proto', '=https', '--proto-redir', '=https', '--max-time', '30',
               '--max-filesize', str(entry['compressed_bytes']), '--output', str(temporary), url]
    result = subprocess.run(command, capture_output=True)
    (args.output / 'curl.log').write_bytes(result.stderr + result.stdout)
    report = {'started_at_utc': datetime.now(timezone.utc).isoformat(), 'url': url,
              'command': command, 'exit_code': result.returncode, 'expected': entry,
              'status': 'retrieval_failed', 'tls_verification': 'enabled', 'attempts': 1,
              'facts_association': 'not_performed'}
    if result.returncode == 0:
        digest = hashlib.sha256(temporary.read_bytes()).hexdigest()
        report['download_sha256'] = digest
        if digest != entry['sha256'] or temporary.stat().st_size != entry['compressed_bytes']:
            report['status'] = 'identity_rejected'
        else:
            sample = args.output / 'kvfs-x86_64.jsonl.zst'
            temporary.rename(sample)
            try:
                checked = audit(args.repo, manifest_path, sample)
                (args.output / 'audit.json').write_text(json.dumps(checked, indent=2) + '\n')
                report['status'] = ('artifact_audited_with_limits' if not checked['duplicate_item_keys']
                                    and not checked['invalid_item_line_ranges'] else 'audit_gaps')
            except Exception as error:
                report['status'] = 'audit_failed'
                report['audit_error'] = str(error)
    if temporary.exists():
        report['rejected_partial_bytes'] = temporary.stat().st_size
        temporary.unlink()
    (args.output / 'manifest.json').write_bytes(manifest_path.read_bytes())
    (args.output / 'fetch.py').write_bytes(Path(__file__).read_bytes())
    report['artifact_sha256'] = {path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                                 for path in args.output.iterdir() if path.is_file()}
    (args.output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'status': report['status'], 'exit_code': result.returncode}))
    return 0 if report['status'] == 'artifact_audited_with_limits' else 1


if __name__ == '__main__':
    raise SystemExit(main())
