"""Fetch bounded fixed-revision source archives; never execute them."""

import argparse
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import tarfile
import urllib.parse
import urllib.request


ROOT = Path(__file__).resolve().parents[1]
REVISION = 'cae17d87f8c17d8108d21abd41e0520b6ca65d7c'
PATHS = ('src', 'test-systems/Jabref/sources/3.7/src/main/java')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    cache = ROOT / '.tools/inmap' / REVISION
    cache.mkdir(parents=True, exist_ok=True)
    records = []
    for relative in PATHS:
        url = ('https://git.cs.kau.se/api/v4/projects/683/repository/archive.tar.gz?'
               + urllib.parse.urlencode({'sha': REVISION, 'path': relative}))
        with urllib.request.urlopen(url, timeout=120) as response:
            content = response.read(30 * 1024 * 1024 + 1)
        if len(content) > 30 * 1024 * 1024:
            raise ValueError('bounded archive size exceeded')
        archive_name = relative.replace('/', '__') + '.tar.gz'
        (cache / archive_name).write_bytes(content)
        files = []
        with tarfile.open(fileobj=io.BytesIO(content), mode='r:gz') as archive:
            total = 0
            for member in archive.getmembers():
                if member.isdir():
                    continue
                path = PurePosixPath(member.name)
                if not member.isfile() or '..' in path.parts or path.is_absolute():
                    raise ValueError(f'unsafe archive member: {member.name}')
                relative_path = PurePosixPath(*path.parts[1:])
                if not str(relative_path).startswith(relative + '/'):
                    raise ValueError(f'archive exceeds requested scope: {relative_path}')
                total += member.size
                if total > 100 * 1024 * 1024:
                    raise ValueError('unpacked size bound exceeded')
                source = archive.extractfile(member).read()
                destination = cache / 'source' / str(relative_path)
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(source)
                files.append({'path': str(relative_path), 'bytes': len(source),
                              'sha256': hashlib.sha256(source).hexdigest(),
                              'git_blob_sha1': hashlib.sha1(b'blob ' + str(len(source)).encode() + b'\0' + source).hexdigest()})
        records.append({'url': url, 'archive': str((cache / archive_name).relative_to(ROOT)),
                        'archive_sha256': hashlib.sha256(content).hexdigest(),
                        'bytes': len(content), 'files': files})
        (args.output / 'downloads.json').write_text(json.dumps(records, indent=2) + '\n')
        print(relative, len(files), 'files', len(content), 'archive bytes', flush=True)


if __name__ == '__main__':
    main()
