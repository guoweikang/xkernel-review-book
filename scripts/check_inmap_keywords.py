"""Verify observed keyword-input behaviors without treating them as intended semantics."""

import argparse
import hashlib
import json
from pathlib import Path


def audit(root):
    report = json.loads((root / 'report.json').read_text())
    assert report['returncode'] == 0
    assert report['original_sources_modified'] is False
    assert report['scope'].startswith('controlled method-keyword extraction')
    for name, checksum in report['artifact_sha256'].items():
        assert hashlib.sha256((root / name).read_bytes()).hexdigest() == checksum, name
    def load(fixture, stage):
        rows = {}
        for line in (root / f'keyword-{fixture}-{stage}.tsv').read_text().splitlines():
            owner, methods = line.split('\t')
            assert owner not in rows
            rows[owner] = methods.split(',') if methods else []
        return rows
    first, second = 'fixture.First', 'fixture.Second'
    assert load('method-only', 'classMethods') == {first: ['alpha'], second: ['beta']}
    assert load('class-before-method', 'classMethods') == {first: ['alpha', 'beta'], second: ['alpha', 'beta']}
    assert load('class-after-method', 'classMethods') == {first: [], second: []}
    for fixture in ('method-only', 'class-before-method', 'class-after-method'):
        assert load(fixture, 'classMethods') == load(fixture, 'sanitizedClassMethods')
    assert load('unrelated-first', 'classMethods') == load('inner-first', 'classMethods')
    assert load('unrelated-first', 'sanitizedClassMethods') == {
        'fixture.Other': ['unrelatedMethod'], 'fixture.Outer': ['unrelatedMethod']}
    assert load('inner-first', 'sanitizedClassMethods') == {
        'fixture.Other': ['unrelatedMethod'], 'fixture.Outer': ['innerMethod']}
    return {'scope': report['scope'], 'fixtures': 5,
            'observed': ['method-only retains endpoint ownership',
                         'class-before-method shares the endpoint method sets',
                         'class-after-method erases earlier method sets',
                         'inner normalization depends on first map entry'],
            'not_measured': ['effect on original author graph', 'mapping accuracy', 'Rust transfer']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path)
    parser.add_argument('--repeat', type=Path)
    args = parser.parse_args()
    report = audit(args.run)
    if args.repeat:
        assert report == audit(args.repeat)
        names = {path.name for path in args.run.glob('keyword-*')}
        assert names == {path.name for path in args.repeat.glob('keyword-*')}
        for name in names:
            assert (args.run / name).read_bytes() == (args.repeat / name).read_bytes(), name
        report['repeat_inputs_outputs_byte_identical'] = True
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
