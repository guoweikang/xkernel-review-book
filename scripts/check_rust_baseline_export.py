"""Check export range guards and independently round-trip every emitted unit."""

import argparse
import json
import zipfile
from copy import deepcopy
from pathlib import Path

from export_rust_baseline_corpus import digest, extract


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, required=True)
    args = parser.parse_args()
    source = 'fn sample() { "中文"; }'.encode()
    opening = source.index(b'{')
    unit = {'range': [0, len(source)], 'signature_range': [0, opening - 1],
            'body_range': [opening, len(source)]}
    assert extract(source, unit)[0] == source
    for field, replacement in [('body_range', [opening, len(source) + 1]),
                               ('signature_range', [-1, opening]),
                               ('body_range', [opening + 1, len(source)])]:
        changed = deepcopy(unit)
        changed[field] = replacement
        try:
            extract(source, changed)
        except ValueError:
            continue
        raise AssertionError('Invalid range was accepted')
    report = json.loads((args.run / 'report.json').read_text())
    assert report['passed']
    for name, checksum in report['artifacts_sha256'].items():
        assert digest((args.run / name).read_bytes()) == checksum, name
    records = json.loads((args.run / 'units.json').read_text())
    assert len({record['id'] for record in records}) == len(records) == report['units']
    with zipfile.ZipFile(args.run / 'units.zip') as units, zipfile.ZipFile(args.run / 'sources.zip') as sources:
        assert set(units.namelist()) == {record['entry'] for record in records}
        for record in records:
            source = sources.read(record['path'])
            snippet = units.read(record['entry'])
            begin, end = record['range']
            assert source[begin:end] == snippet
            assert digest(source) == record['source_sha256']
            assert digest(snippet) == record['sha256']
            assert record['start_line'] == source[:begin].count(b'\n') + 1
            assert record['end_line'] == source[:end - 1].count(b'\n') + 1
    print(f'PASS: UTF-8 fixture, three rejected ranges, {len(records)} source round-trips; not semantic validation')


if __name__ == '__main__':
    main()
