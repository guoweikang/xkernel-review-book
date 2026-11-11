"""Check configuration audit artifacts and strict-reader controls."""

import argparse
import hashlib
import json
from pathlib import Path

from audit_inmap_config import audit, parse


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path)
    args = parser.parse_args()
    report = json.loads((args.run / 'report.json').read_text())
    original = (args.run / 'config-original.txt').read_bytes()
    selected = (args.run / 'config-single.txt').read_bytes()
    assert hashlib.sha256(original).hexdigest() == report['original_sha256']
    assert hashlib.sha256(selected).hexdigest() == report['selected_sha256']
    for key, value in audit(original.decode()).items():
        assert report[key] == value, key
    reduced = audit(selected.decode())
    assert reduced['configuration_count_decimal'] == 1
    assert reduced['mapping'] == report['mapping']
    assert reduced['ranges'] == report['single_configuration']
    assert parse('Key : "value"\nItems : {\n"one"\n}\n') == ({'Key': 'value'}, {'Items': ['one']})
    for text in ('Items : {\n"one"', 'Key : "a"\nKey : "b"', 'bad-setting', 'Items : {\nnot-quoted\n}'):
        try:
            parse(text)
        except ValueError:
            continue
        raise AssertionError(text)
    print('PASS: original/selected hashes; audit replay; one configuration; unchanged oracle; five parser controls')


if __name__ == '__main__':
    main()
