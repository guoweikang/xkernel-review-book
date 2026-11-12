"""Audit syntax-only declared-method inventory and exact top-level population joins."""

import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path)
    parser.add_argument('--population-run', required=True, type=Path)
    parser.add_argument('--previous', type=Path)
    args = parser.parse_args()
    root = args.run
    report = json.loads((root / 'report.json').read_text())
    assert report['returncode'] == 0 and not report['original_sources_modified']
    for name, checksum in report['artifact_sha256'].items():
        assert hashlib.sha256((root / name).read_bytes()).hexdigest() == checksum, name
    population_report = json.loads((args.population_run / 'report.json').read_text())
    population_file = args.population_run / 'filtered-classes.txt'
    assert hashlib.sha256(population_file.read_bytes()).hexdigest() == population_report['artifact_sha256']['filtered-classes.txt']
    population = set(population_file.read_text().splitlines())
    assert report['revision'] == population_report['revision']
    types = {}
    for line in (root / 'declared-method-types.tsv').read_text().splitlines():
        owner, source = line.split('\t')
        assert owner not in types
        types[owner] = source
    methods = defaultdict(set)
    rows = (root / 'declared-methods.tsv').read_text().splitlines()
    for line in rows:
        owner, name, source = line.split('\t')
        assert owner in types and types[owner] == source
        assert '<' not in name and '$' not in name
        methods[owner].add(name)
    top_level = {owner for owner in types if '$' not in owner}
    matched = population & top_level
    nonempty = {owner for owner in matched if methods[owner]}
    summary = dict(line.split('\t') for line in (root / 'declared-method-summary.tsv').read_text().splitlines())
    assert int(summary['parse_errors']) == 0
    assert int(summary['method_declarations']) == len(rows)
    assert summary['source_files'] == summary['parsed_units']
    if args.previous:
        assert (args.previous / 'declared-methods.tsv').read_bytes() == (root / 'declared-methods.tsv').read_bytes()
    print(json.dumps({'scope': report['scope'], 'source_files': int(summary['source_files']),
                      'named_types': len(types), 'top_level_types': len(top_level),
                      'declarations_before_overload_dedup': len(rows),
                      'population': len(population), 'matched_top_level_types': len(matched),
                      'nonempty_top_level_types': len(nonempty),
                      'matched_top_level_method_pairs': sum(len(methods[owner]) for owner in matched),
                      'matched_empty_types': sorted(matched - nonempty),
                      'population_without_matching_declaration': sorted(population - matched),
                      'top_level_types_outside_population': sorted(top_level - population),
                      'previous_method_rows_identical': args.previous is not None}, indent=2))


if __name__ == '__main__':
    main()
