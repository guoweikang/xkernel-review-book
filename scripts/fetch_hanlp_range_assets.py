"""Bounded parallel range repair for the same frozen HanLP archives."""

import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import subprocess
import time
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--previous-run', required=True)
    args = parser.parse_args()
    if any(not re.fullmatch('[A-Za-z0-9_-]+', value) for value in (args.run_id, args.previous_run)):
        raise ValueError('invalid ID')
    folder = ROOT / 'research/evidence/runs' / args.run_id
    originals = ROOT / 'research/evidence/originals' / args.run_id
    folder.mkdir()
    originals.mkdir()
    plan_path = ROOT / 'research/protocols/hanlp-srl-smoke-v1.json'
    amendment_path = ROOT / 'research/protocols/hanlp-download-amendment-v1.json'
    plan, amendment = [json.loads(path.read_text()) for path in (plan_path, amendment_path)]
    for source, name in ((plan_path, 'protocol.json'), (amendment_path, 'amendment.json'), (Path(__file__), 'runner.py')):
        shutil.copy2(source, folder / name)
    started = time.monotonic()
    jobs = []
    for resource in plan['resources']:
        if resource['id'] == 'tokenizer':
            continue
        for start in range(0, resource['bytes'], amendment['chunk_bytes']):
            jobs.append((resource, start, min(start + amendment['chunk_bytes'], resource['bytes']) - 1))

    def fetch(job):
        resource, start, end = job
        name = f"{resource['id']}-{start:012d}"
        record = {'resource': resource['id'], 'start': start, 'end': end, 'success': False}
        try:
            if time.monotonic() - started > amendment['batch_schedule_deadline_seconds']:
                raise ValueError('scheduling deadline reached')
            output, headers = originals / f'{name}.part', folder / f'{name}.headers'
            with (folder / f'{name}.log').open('wb') as log:
                result = subprocess.run(['curl', '--fail', '--location', '--max-time', str(amendment['request_timeout_seconds']), '--max-filesize', str(end-start+1), '--range', f'{start}-{end}', '--dump-header', str(headers), resource['url'], '-o', str(output)], stdout=log, stderr=subprocess.STDOUT, timeout=amendment['request_timeout_seconds']+5)
            record['exit_code'] = result.returncode
            header_text = headers.read_text().lower()
            if result.returncode or output.stat().st_size != end-start+1:
                raise ValueError('range transfer failed')
            if f'content-range: bytes {start}-{end}/{resource["bytes"]}' not in header_text or not re.search(r'http/\S+ 206\b', header_text):
                raise ValueError('range headers mismatch')
            etags = re.findall(r'^etag:\s*(.+)$', header_text, re.MULTILINE)
            if not etags:
                raise ValueError('missing archive ETag')
            record.update({'etag': etags[-1].strip(), 'sha256': sha(output), 'file': output.name, 'success': True})
        except Exception as error:
            record['error'] = f'{type(error).__name__}: {error}'
        (folder / f'{name}.json').write_text(json.dumps(record, indent=2) + '\n')
        return record

    with ThreadPoolExecutor(max_workers=amendment['concurrency']) as pool:
        chunks = list(pool.map(fetch, jobs))
    resources = []
    for resource in plan['resources']:
        identity = resource['id']
        record = dict(resource, success=False)
        try:
            archive_path = originals / f'{identity}.zip'
            if identity == 'tokenizer':
                previous = ROOT / 'research/evidence/runs' / args.previous_run
                result = json.loads((previous / 'tokenizer-result.json').read_text())
                source = ROOT / 'research/evidence/originals' / args.previous_run / 'tokenizer.zip'
                if not result['success'] or sha(source) != result['sha256']:
                    raise ValueError('previous tokenizer invalid')
                shutil.copy2(source, archive_path)
            else:
                parts = [row for row in chunks if row['resource'] == identity]
                if not all(row['success'] for row in parts) or len({row.get('etag') for row in parts}) != 1:
                    raise ValueError('failed chunks or changed ETag')
                with archive_path.open('wb') as output:
                    for row in parts:
                        with (originals / row['file']).open('rb') as source:
                            shutil.copyfileobj(source, output)
            if archive_path.stat().st_size != resource['bytes']:
                raise ValueError('archive size mismatch')
            record['sha256'] = sha(archive_path)
            with zipfile.ZipFile(archive_path) as archive:
                if sum(info.file_size for info in archive.infolist()) > 3 * 1024**3:
                    raise ValueError('extraction budget')
                for info in archive.infolist():
                    path = PurePosixPath(info.filename)
                    if path.is_absolute() or '..' in path.parts or '\\' in info.filename or stat.S_ISLNK(info.external_attr >> 16):
                        raise ValueError('unsafe member')
                if archive.testzip():
                    raise ValueError('CRC mismatch')
                destination = originals / identity
                archive.extractall(destination)
                record['files'] = {str(path.relative_to(destination)): sha(path) for path in sorted(destination.rglob('*')) if path.is_file()}
            record['success'] = True
        except Exception as error:
            record['error'] = f'{type(error).__name__}: {error}'
        resources.append(record)
    report = {'scope': 'same-asset range repair', 'resources': resources, 'chunks': chunks, 'success': all(row['success'] for row in resources), 'inferences': 0}
    (folder / 'report.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps([dict(id=row['id'], success=row['success'], error=row.get('error')) for row in resources]))
    if not report['success']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
