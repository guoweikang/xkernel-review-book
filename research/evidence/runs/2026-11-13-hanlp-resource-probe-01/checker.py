"""Check bounded remote ZIP reader against local fixtures and saved hashes."""

import argparse
import hashlib
import io
import json
from pathlib import Path
import tempfile
from unittest.mock import patch
import zipfile

from probe_hanlp_resources import RemoteArchive


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folder', type=Path)
    args = parser.parse_args()
    report = json.loads((args.folder / 'report.json').read_text())
    plan = json.loads((args.folder / 'protocol.json').read_text())
    originals = args.folder.parents[1] / 'originals' / args.folder.name
    for entry in report['requests']:
        if 'file' in entry:
            data = (originals / entry['file']).read_bytes()
            assert len(data) == entry['end'] - entry['start'] + 1
            assert hashlib.sha256(data).hexdigest() == entry['sha256']
    for entry in report.get('metadata', []):
        data = (originals / entry['file']).read_bytes()
        assert hashlib.sha256(data).hexdigest() == entry['sha256']
        json.loads(data)
    assert sum(entry['end'] - entry['start'] + 1 for entry in report['requests'] if 'file' in entry) == report['range_bytes']
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('config.json', '{"test": true}')
        archive.writestr('model.pt', b'never-deserialize')
    payload = buffer.getvalue()
    fixture_plan = dict(plan, expected_archive_bytes_from_prior_head=len(payload))

    def response(request, timeout):
        start, end = map(int, request.headers['Range'].removeprefix('bytes=').split('-'))
        stream = io.BytesIO(payload[start:end + 1])
        stream.status = 206
        stream.url = request.full_url
        stream.headers = {'Content-Range': f'bytes {start}-{end}/{len(payload)}'}
        return stream

    with tempfile.TemporaryDirectory() as temp:
        remote = RemoteArchive(fixture_plan, Path(temp))
        with patch('urllib.request.urlopen', response):
            with zipfile.ZipFile(remote) as archive:
                assert json.loads(archive.read('config.json')) == {'test': True}
        rejected = 0
        for kind in ('ignored_range', 'wrong_range', 'short_body', 'request_budget'):
            probe = RemoteArchive(fixture_plan, Path(temp))

            def invalid(request, timeout):
                stream = response(request, timeout)
                if kind == 'ignored_range':
                    stream.status = 200
                elif kind == 'wrong_range':
                    stream.headers['Content-Range'] = 'bytes 1-2/3'
                else:
                    stream = io.BytesIO(b'')
                    stream.status = 206
                    stream.url = request.full_url
                    stream.headers = {'Content-Range': f'bytes 0-9/{len(payload)}'}
                return stream

            try:
                with patch('urllib.request.urlopen', invalid):
                    if kind == 'request_budget':
                        probe.plan = dict(fixture_plan, limits=dict(plan['limits'], max_request_bytes=5))
                    probe.read(10)
            except ValueError:
                rejected += 1
            else:
                raise AssertionError(kind)
        assert rejected == 4
    print(json.dumps({'saved_hashes_checked': True, 'zip_fixture': True,
                      'negative_controls': rejected, 'full_model_integrity_checked': False}))


if __name__ == '__main__':
    main()
