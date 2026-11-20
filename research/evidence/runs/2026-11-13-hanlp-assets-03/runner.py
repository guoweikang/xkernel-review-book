"""Repair one frozen incomplete range in a new immutable asset run."""

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    protocol = ROOT / 'research/protocols/hanlp-tail-repair-v1.json'
    plan = json.loads(protocol.read_text())
    old_run = ROOT / 'research/evidence/runs' / plan['previous_run']
    old_files = ROOT / 'research/evidence/originals' / plan['previous_run']
    folder = ROOT / 'research/evidence/runs/2026-11-13-hanlp-assets-03'
    originals = ROOT / 'research/evidence/originals/2026-11-13-hanlp-assets-03'
    folder.mkdir()
    originals.mkdir()
    shutil.copy2(protocol, folder / 'protocol.json')
    shutil.copy2(__file__, folder / 'runner.py')
    old = json.loads((old_run / 'report.json').read_text())
    report = {'scope': 'one suffix repair; same model resources', 'success': False, 'inferences': 0}
    try:
        failed = [row for row in old['chunks'] if not row['success']]
        assert len(failed) == 1
        entry = failed[0]
        assert entry['resource'] == plan['resource'] and entry['start'] == plan['start'] and entry['end'] == plan['end']
        prefix_name = f"encoder-{plan['start']:012d}"
        prefix = old_files / f'{prefix_name}.part'
        assert prefix.stat().st_size == plan['observed_prefix_bytes']
        report['prefix_sha256'] = sha(prefix)
        (folder / 'prefix-identity.json').write_text(json.dumps({'sha256': report['prefix_sha256'], 'bytes': prefix.stat().st_size}) + '\n')
        encoder = next(row for row in old['resources'] if row['id'] == 'encoder')
        etags = {row['etag'] for row in old['chunks'] if row['resource'] == 'encoder' and row['success']}
        assert len(etags) == 1
        etag = etags.pop()
        old_headers = (old_run / f'{prefix_name}.headers').read_text().lower()
        assert ' 206 ' in old_headers and f'etag: {etag}' in old_headers
        assert f'content-range: bytes {plan["start"]}-{plan["end"]}/{encoder["bytes"]}' in old_headers
        start = plan['start'] + prefix.stat().st_size
        suffix = originals / 'suffix.bin'
        with (folder / 'suffix.log').open('wb') as log:
            result = subprocess.run(['curl', '-fL', '--range', f'{start}-{plan["end"]}', '--max-time', str(plan['timeout_seconds']), '--max-filesize', str(plan['tail_bytes']), '--dump-header', str(folder / 'suffix.headers'), encoder['url'], '-o', str(suffix)], stdout=log, stderr=subprocess.STDOUT, timeout=65)
        assert result.returncode == 0 and suffix.stat().st_size == plan['tail_bytes']
        headers = (folder / 'suffix.headers').read_text().lower()
        assert ' 206 ' in headers and f'etag: {etag}' in headers
        assert f'content-range: bytes {start}-{plan["end"]}/{encoder["bytes"]}' in headers
        report['suffix_sha256'] = sha(suffix)
        records = []
        for resource in old['resources']:
            identity = resource['id']
            archive_path = originals / f'{identity}.zip'
            if identity != 'encoder':
                assert resource['success'] and sha(old_files / f'{identity}.zip') == resource['sha256']
                os.link(old_files / f'{identity}.zip', archive_path)
                for path, digest in resource['files'].items():
                    assert sha(old_files / identity / path) == digest
                shutil.copytree(old_files / identity, originals / identity, copy_function=os.link)
                records.append(resource)
                continue
            with archive_path.open('wb') as output:
                for chunk in (row for row in old['chunks'] if row['resource'] == 'encoder'):
                    if chunk['success']:
                        source = old_files / chunk['file']
                        assert sha(source) == chunk['sha256']
                        with source.open('rb') as stream:
                            shutil.copyfileobj(stream, output)
                    else:
                        assert sha(prefix) == report['prefix_sha256']
                        for source in (prefix, suffix):
                            with source.open('rb') as stream:
                                shutil.copyfileobj(stream, output)
            assert archive_path.stat().st_size == resource['bytes']
            with zipfile.ZipFile(archive_path) as archive:
                assert sum(info.file_size for info in archive.infolist()) < 3 * 1024**3
                for info in archive.infolist():
                    path = Path(info.filename)
                    assert not path.is_absolute() and '..' not in path.parts and '\\' not in info.filename
                    assert ((info.external_attr >> 16) & 0o170000) != 0o120000
                assert archive.testzip() is None
                archive.extractall(originals / identity)
            records.append({'id': identity, 'url': resource['url'], 'bytes': resource['bytes'], 'success': True,
                            'sha256': sha(archive_path), 'files': {str(path.relative_to(originals / identity)): sha(path) for path in sorted((originals / identity).rglob('*')) if path.is_file()}})
        report.update({'resources': records, 'success': True})
    except Exception as error:
        report['error'] = f'{type(error).__name__}: {error}'
    (folder / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({key: value for key, value in report.items() if key != 'resources'}))
    if not report['success']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
