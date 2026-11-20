import argparse
import hashlib
import json
from pathlib import Path
import shutil
import urllib.error
import urllib.request
import zipfile


ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', required=True)
    parser.add_argument('--inventory', required=True)
    args = parser.parse_args()
    run = ROOT / 'research/evidence/runs' / args.run
    run.mkdir(exist_ok=False)
    parent = ROOT / 'research/evidence/runs' / args.inventory
    summary = json.loads((parent / 'report.json').read_text())
    for name, expected in summary['artifacts_sha256'].items():
        assert hashlib.sha256((parent / name).read_bytes()).hexdigest() == expected
    archive = ROOT / 'research/evidence' / summary['archive']
    assert hashlib.sha256(archive.read_bytes()).hexdigest() == summary['archive_sha256']
    records = json.loads((parent / 'inventory.json').read_text())
    with zipfile.ZipFile(archive) as source:
        for row in records:
            data = source.read(row['path'])
            assert hashlib.sha256(data).hexdigest() == row['sha256']
            assert hashlib.sha1(f'blob {len(data)}\0'.encode() + data).hexdigest() == row['git_blob_sha1']
    version = (parent / 'rustc-version.txt').read_text()
    commit = next(line.split(': ', 1)[1] for line in version.splitlines() if line.startswith('commit-hash:'))
    shutil.copyfile(__file__, run / 'runner.py')
    (run / 'protocol.json').write_text(json.dumps({'parent': args.inventory, 'commit': commit, 'inventory_sha256': hashlib.sha256((parent / 'inventory.json').read_bytes()).hexdigest(), 'rule': 'Compare all 340 archived files with official commit library tree Git blob IDs. No source execution or independent-test certification. Preserve failed HTTP responses; at most two requests, 60s each.'}, indent=2) + '\n')

    def request_tree(identity, name, recursive=False):
        url = f'https://api.github.com/repos/rust-lang/rust/git/trees/{identity}' + ('?recursive=1' if recursive else '')
        request = urllib.request.Request(url, headers={'User-Agent': 'xkernel-review-research', 'Accept': 'application/vnd.github+json'})
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                data = response.read()
                (run / f'{name}-headers.txt').write_text(str(response.headers))
        except urllib.error.HTTPError as error:
            (run / f'{name}-error.txt').write_bytes(error.read())
            raise
        (run / f'{name}.json').write_bytes(data)
        result = json.loads(data)
        assert not result.get('truncated', False)
        return result

    try:
        tree = request_tree(commit, 'root')
        library = next(row['sha'] for row in tree['tree'] if row['path'] == 'library' and row['type'] == 'tree')
        contents = request_tree(library, 'library', True)
        lookup = {'library/' + row['path']: row for row in contents['tree']}
        mismatches = [row['path'] for row in records if row['path'] not in lookup or lookup[row['path']]['type'] != 'blob' or lookup[row['path']]['sha'] != row['git_blob_sha1']]
        result = {'status': 'verified' if not mismatches else 'mismatch', 'files_checked': len(records), 'mismatches': mismatches, 'commit': commit, 'independent_test_eligible': False}
    except (urllib.error.URLError, TimeoutError, AssertionError, KeyError, StopIteration) as error:
        result = {'status': 'not_verified', 'error': repr(error), 'commit': commit, 'independent_test_eligible': False}
    result['artifacts_sha256'] = {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in run.iterdir() if path.is_file()}
    (run / 'report.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
