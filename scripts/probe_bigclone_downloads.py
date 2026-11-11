"""Probe official dataset entrypoints with bounded reads; do not claim dataset download."""

import argparse
import datetime
import hashlib
import json
from pathlib import Path
import shutil
import urllib.error
import urllib.request


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    entries = {
        'bigclonebench': 'https://1drv.ms/u/s!AhXbM6MKt_yLj_NwwVacvUzmi6uorA?e=eMu0P4',
        'ijadataset': 'https://1drv.ms/u/s!AhXbM6MKt_yLj_N15CewgjM7Y8NLKA?e=cScoRJ',
    }
    records = []
    for name, url in entries.items():
        record = {'name': name, 'url': url,
                  'recorded_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  'max_read_bytes': 65536, 'timeout_seconds': 20}
        request = urllib.request.Request(url, headers={
            'User-Agent': 'rust-review-research', 'Range': 'bytes=0-65535'})
        try:
            response = urllib.request.urlopen(request, timeout=20)
        except urllib.error.HTTPError as error:
            response = error
        except Exception as error:
            record.update(status='request_failed', error=str(error))
            records.append(record)
            continue
        with response:
            body = response.read(65536)
            record.update(http_status=response.status, final_url=response.url,
                          content_type=response.headers.get('Content-Type'),
                          content_length=response.headers.get('Content-Length'),
                          content_range=response.headers.get('Content-Range'),
                          bytes_read=len(body), sha256=hashlib.sha256(body).hexdigest(),
                          status='bounded_response_only', archive_magic=body[:2] == b'\x1f\x8b')
        (args.output / f'{name}.response').write_bytes(body)
        records.append(record)
    shutil.copyfile(__file__, args.output / 'probe.py')
    report = {'source_readme': 'https://github.com/jeffsvajlenko/BigCloneEval/blob/6d393ec8adb1d71493d09881ba520659b6c2c68e/ReadMe.md',
              'records': records, 'dataset_downloaded': False, 'authentication_used': False,
              'limitations': 'Only official share entrypoints checked; no conclusion about other mirrors or global availability'}
    (args.output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
