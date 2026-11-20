"""Fetch fixed public archives with bounded size/time and preserve all outcomes."""

import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    if not re.fullmatch('[A-Za-z0-9_-]+', args.run_id):
        raise ValueError('invalid ID')
    folder = ROOT / 'research/evidence/runs' / args.run_id
    folder.mkdir()
    originals = ROOT / 'research/evidence/originals' / args.run_id
    originals.mkdir()
    protocol = ROOT / 'research/protocols/hanlp-srl-smoke-v1.json'
    plan = json.loads(protocol.read_text())
    shutil.copy2(protocol, folder / 'protocol.json')
    shutil.copy2(__file__, folder / 'runner.py')

    def fetch(resource):
        identity = resource['id']
        archive_path = originals / f'{identity}.zip'
        record = dict(resource, success=False)
        try:
            with (folder / f'{identity}-download.log').open('wb') as log:
                result = subprocess.run(['curl', '--fail', '--location', '--max-time', '600', '--max-filesize', str(resource['bytes']), '--dump-header', str(folder / f'{identity}-headers.txt'), resource['url'], '--output', str(archive_path)], stdout=log, stderr=subprocess.STDOUT, timeout=620)
            record['exit_code'] = result.returncode
            if result.returncode or archive_path.stat().st_size != resource['bytes']:
                raise ValueError('download failed or wrong size')
            with archive_path.open('rb') as stream:
                record['sha256'] = hashlib.file_digest(stream, 'sha256').hexdigest()
            with zipfile.ZipFile(archive_path) as archive:
                if sum(info.file_size for info in archive.infolist()) > 3 * 1024**3:
                    raise ValueError('uncompressed size budget')
                for info in archive.infolist():
                    path = PurePosixPath(info.filename)
                    if path.is_absolute() or '..' in path.parts or '\\' in info.filename or stat.S_ISLNK(info.external_attr >> 16):
                        raise ValueError('unsafe archive member')
                failure = archive.testzip()
                if failure:
                    raise ValueError(f'CRC failure: {failure}')
                destination = originals / identity
                archive.extractall(destination)
                record['files'] = {str(path.relative_to(destination)): hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(destination.rglob('*')) if path.is_file()}
            record['success'] = True
        except Exception as error:
            record['error'] = f'{type(error).__name__}: {error}'
        (folder / f'{identity}-result.json').write_text(json.dumps(record, indent=2) + '\n')
        return record

    with ThreadPoolExecutor(max_workers=3) as pool:
        results = list(pool.map(fetch, plan['resources']))
    report = {'scope': 'resource acquisition only', 'resources': results, 'success': all(row['success'] for row in results), 'inferences': 0}
    (folder / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps([{key: value for key, value in row.items() if key != 'files'} for row in results], indent=2))
    if not report['success']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
