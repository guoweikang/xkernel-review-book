"""Check research navigation coverage and rejection of invalid registrations."""

import copy
import json

from build import RESEARCH, validate_catalog


def main():
    actual = {source.relative_to(RESEARCH).as_posix() for source in RESEARCH.rglob('*.md')
              if not source.is_relative_to(RESEARCH / 'evidence/originals')
              and not source.is_relative_to(RESEARCH / 'evidence/runs')}
    catalog = json.loads((RESEARCH / 'catalog.json').read_text())
    validate_catalog(actual, catalog)
    invalid = []
    missing = copy.deepcopy(catalog)
    missing['groups'][0]['documents'].pop()
    invalid.append(missing)
    duplicate = copy.deepcopy(catalog)
    duplicate['groups'][1]['documents'].append(duplicate['groups'][0]['documents'][0])
    invalid.append(duplicate)
    stale = copy.deepcopy(catalog)
    stale['groups'][0]['documents'].append('does-not-exist.md')
    invalid.append(stale)
    duplicate_topic = copy.deepcopy(catalog)
    duplicate_topic['groups'][1]['id'] = duplicate_topic['groups'][0]['id']
    invalid.append(duplicate_topic)
    unsafe_topic = copy.deepcopy(catalog)
    unsafe_topic['groups'][0]['id'] = '../outside'
    invalid.append(unsafe_topic)
    for candidate in invalid:
        try:
            validate_catalog(actual, candidate)
        except SystemExit:
            continue
        raise AssertionError('Invalid catalog accepted')
    print(f'PASS: {len(actual)} documents, {len(catalog["groups"])} topics; five negative controls')


if __name__ == '__main__':
    main()
