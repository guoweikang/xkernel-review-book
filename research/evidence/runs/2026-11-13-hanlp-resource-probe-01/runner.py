"""Read bounded ZIP metadata via HTTP ranges without downloading model weights."""

import argparse
import hashlib
import io
import json
from pathlib import Path
import re
import shutil
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]


class RemoteArchive(io.RawIOBase):
    def __init__(self, plan, folder):
        self.plan = plan
        self.folder = folder
        self.position = 0
        self.size = plan['expected_archive_bytes_from_prior_head']
        self.transferred = 0
        self.requests = []

    def seekable(self):
        return True

    def seek(self, offset, whence=0):
        self.position = offset if whence == 0 else self.position + offset if whence == 1 else self.size + offset
        if not 0 <= self.position <= self.size:
            raise ValueError('seek outside archive')
        return self.position

    def tell(self):
        return self.position

    def read(self, size=-1):
        size = self.size - self.position if size < 0 else min(size, self.size - self.position)
        if not size:
            return b''
        limits = self.plan['limits']
        if size > limits['max_request_bytes'] or self.transferred + size > limits['max_total_range_bytes']:
            raise ValueError('range budget exceeded')
        start, end = self.position, self.position + size - 1
        request = urllib.request.Request(self.plan['model_url'], headers={'Range': f'bytes={start}-{end}', 'Accept-Encoding': 'identity'})
        with urllib.request.urlopen(request, timeout=limits['request_timeout_seconds']) as response:
            entry = {'start': start, 'end': end, 'status': response.status, 'url': response.url, 'headers': dict(response.headers)}
            self.requests.append(entry)
            if response.status != 206 or response.headers.get('Content-Range') != f'bytes {start}-{end}/{self.size}':
                raise ValueError('server did not honor exact range; no full-download fallback')
            data = response.read(size + 1)
            if len(data) != size:
                raise ValueError('unexpected range length')
        self.transferred += size
        self.position += size
        name = f'range-{len(self.requests):02d}.bin'
        (self.folder / name).write_bytes(data)
        entry.update({'file': name, 'sha256': hashlib.sha256(data).hexdigest()})
        return data


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
    protocol = ROOT / 'research/protocols/hanlp-runtime-preflight-v1.json'
    plan = json.loads(protocol.read_text())
    shutil.copy2(protocol, folder / 'protocol.json')
    shutil.copy2(__file__, folder / 'runner.py')
    remote = RemoteArchive(plan, originals)
    report = {'scope': plan['scope'], 'success': False, 'model_loaded': False}
    try:
        with zipfile.ZipFile(remote) as archive:
            members = [{'name': info.filename, 'compressed_bytes': info.compress_size, 'bytes': info.file_size, 'crc': info.CRC} for info in archive.infolist()]
            (folder / 'members.json').write_text(json.dumps(members, indent=2) + '\n')
            selected = []
            for info in archive.infolist():
                if Path(info.filename).name not in {'config.json', 'meta.json'}:
                    continue
                if info.file_size > plan['limits']['max_json_uncompressed_bytes']:
                    raise ValueError('metadata exceeds budget')
                data = archive.read(info)
                json.loads(data)
                name = f'metadata-{len(selected):02d}.json'
                (originals / name).write_bytes(data)
                selected.append({'member': info.filename, 'file': name, 'sha256': hashlib.sha256(data).hexdigest()})
            report.update({'success': True, 'metadata': selected})
    except Exception as error:
        report['error'] = f'{type(error).__name__}: {error}'
    report.update({'requests': remote.requests, 'range_bytes': remote.transferred})
    (folder / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({key: value for key, value in report.items() if key != 'requests'}, indent=2))
    if not report['success']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
