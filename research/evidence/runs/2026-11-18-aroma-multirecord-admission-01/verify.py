import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / 'corrected'
tree = json.loads((DATA / 'tree.json').read_text())
entries = {entry['path']: entry for entry in tree['tree']}
report = []
for row in json.loads((DATA / 'downloads.json').read_text()):
    assert row['status'] == 'downloaded'
    content = (DATA / row['file']).read_bytes()
    assert hashlib.sha256(content).hexdigest() == row['sha256']
    if row['file'] == 'tree.json':
        continue
    upstream = ('reference/' if row['file'] == 'pom.xml' else 'datasets/') + row['file']
    identity = hashlib.sha1(f'blob {len(content)}\0'.encode() + content).hexdigest()
    assert identity == entries[upstream]['sha']
    report.append({'path': upstream, 'git_blob_sha1': identity, 'passed': True})
source = (HERE / 'first-result-source.java').read_bytes()
inspection = json.loads((HERE / 'inspection.json').read_text())
assert hashlib.sha256(source).hexdigest() == inspection['first_result_source']['sha256']
assert ''.join(source.decode().splitlines(keepends=True)[58:78]) == (HERE / 'first-result-lines.txt').read_text()
result = {'official_blobs': report, 'source_slice_equal': True,
          'algorithm_runs': 0, 'limitations': 'Source link identity is pinned URL plus downloaded hash, not an independently fetched Git tree for the third-party repository.'}
(HERE / 'verification.json').write_text(json.dumps(result, indent=2) + '\n')
print('Four official blobs and first source slice verified')
