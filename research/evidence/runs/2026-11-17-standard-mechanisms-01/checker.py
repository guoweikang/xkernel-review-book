import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import zipfile


ROOT = Path(__file__).resolve().parents[1]


def check(run):
    report = json.loads((run / 'report.json').read_text())
    for name, expected in report['artifacts_sha256'].items():
        assert hashlib.sha256((run / name).read_bytes()).hexdigest() == expected
    freeze = json.loads((run / 'freeze.json').read_text())
    archive = Path(freeze['archive'])
    assert hashlib.sha256(archive.read_bytes()).hexdigest() == freeze['archive_sha256']
    files = json.loads((run / 'files.json').read_text())
    units = json.loads((run / 'units.json').read_text())
    assert len({unit['id'] for unit in units}) == len(units) == report['body_functions']
    assert Counter(file['status'] for file in files) == report['statuses']
    indexed = {file['path']: file for file in files}
    parsed = {file['path']: json.loads((run / file['parsed']).read_text()) for file in files}
    with zipfile.ZipFile(archive) as sources:
        assert {name for name in sources.namelist() if name.endswith('.rs')} == set(indexed)
        for file in files:
            data = parsed[file['path']]
            assert file['status'] == data['status']
            if file['status'] != 'parsed_by_syn':
                assert not data['units'] and data['diagnostics']
            for index, unit in enumerate(data['units']):
                assert all(0 <= ancestor < index for ancestor in unit['ancestors'])
        for unit in units:
            source = sources.read(unit['path'])
            assert indexed[unit['path']]['status'] == 'parsed_by_syn'
            assert hashlib.sha256(source).hexdigest() == unit['source_sha256']
            begin, end = unit['range']
            snippet = source[begin:end]
            snippet.decode('utf-8')
            assert hashlib.sha256(snippet).hexdigest() == unit['sha256']
            syntax = parsed[unit['path']]['units'][unit['syntax_index']]
            assert [syntax['signature_range'][0], syntax['body_range'][1]] == unit['range']
            assert syntax['name'] == unit['name']
            assert source[syntax['body_range'][0]:syntax['body_range'][0]+1] == b'{'
            assert snippet[-1:] == b'}'
            assert unit['start_line'] == source[:begin].count(b'\n') + 1
            assert unit['end_line'] == source[:end-1].count(b'\n') + 1
            assert not unit['independent_test_eligible']
    assert report['failures'] == [file['path'] for file in files if file['status'] != 'parsed_by_syn']
    print(f"PASS: {len(files)} archived files accounted for; {len(units)} function ranges round-tripped; failures retained; no semantic completeness claim")


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', required=True)
    args = parser.parse_args()
    check(ROOT / 'research/evidence/runs' / args.run)
