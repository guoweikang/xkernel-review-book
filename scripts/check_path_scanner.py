import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / 'research/evidence/runs/2026-11-17-path-scanner-02'
CORPUS = ROOT / 'research/evidence/runs/2026-11-05-rust-baseline-corpus-01'
manifest = json.loads((RUN / 'manifest.json').read_text())
with zipfile.ZipFile(CORPUS / 'sources.zip') as archive:
    source = archive.read('fs/kvfs/src/path.rs')
    host = archive.read('fs/kvfs/tests/host/path.rs')
with zipfile.ZipFile(CORPUS / 'units.zip') as archive:
    for unit in manifest['units']:
        assert hashlib.sha256(source).hexdigest() == unit['source_sha256']
        assert archive.read(unit['entry']) in source
inputs = [bytes.fromhex(line).decode() for line in (RUN / 'inputs.hex').read_text().splitlines()]
rows = [line.split('\t') for line in (RUN / 'debug-0.tsv').read_text().splitlines()]
observed = {}
for value, row in zip(inputs, rows, strict=True):
    def decode(span):
        if span == 'none':
            return None
        start, end = map(int, span.split(':'))
        return value.encode()[start:end].decode()
    observed[value] = (decode(row[1]), decode(row[2]))
expected = {'': (None, None), '/': (None, None), '///': (None, None), 'a': ('a', ''), 'a/': ('a', ''), '/a/': ('a', '/'), '.': (None, ''), './': (None, ''), '/.': (None, None), '/./': (None, None), 'a/b/.': ('b', 'a'), 'a/..': (None, 'a'), '..': (None, ''), 'a//b///': ('b', 'a/'), '///a': ('a', '//'), '目录/文件/': ('文件', '目录')}
for value, result in expected.items():
    assert observed[value] == result, (value, observed[value], result)
result = {'source_snippets_verified': 2, 'explicit_boundary_checks': len(expected), 'host_test_source_sha256': hashlib.sha256(host).hexdigest(), 'limits': 'Post-run independent boundary decoding; not an additional prospective experiment or full original test-suite run.'}
(RUN / 'independent-check.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result))
