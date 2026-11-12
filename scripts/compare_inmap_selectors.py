"""Compare only matched missing-feedback runs with different selectors."""

import argparse
import json
from pathlib import Path

from check_inmap_loop_probe import audit


def pairs(root, name):
    return {tuple(line.split('\t')) for line in (root / name).read_text().splitlines()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('original', type=Path)
    parser.add_argument('variant', type=Path)
    args = parser.parse_args()
    baseline = audit(args.original)
    variant = audit(args.variant)
    assert baseline['selector_variant'] == 'original'
    assert variant['selector_variant'] == 'unique-maximum-only'
    for name in ('config-single.txt', 'dependencies.json', 'oracle.tsv', 'filtered-classes.txt'):
        assert (args.original / name).read_bytes() == (args.variant / name).read_bytes(), name
    reports = [json.loads((root / 'report.json').read_text()) for root in (args.original, args.variant)]
    assert reports[0]['revision'] == reports[1]['revision']
    assert reports[0]['original_sources_modified'] is False
    assert reports[1]['original_sources_modified'] is True
    assert reports[1]['selector_change']['method'] == 'pickHighestClassScore'
    changes = {}
    for name in ('acceptedMappings.tsv', 'rejectedMappings.tsv'):
        before = pairs(args.original, name)
        after = pairs(args.variant, name)
        changes[name] = {'added': sorted(after - before), 'removed': sorted(before - after)}
    print(json.dumps({'scope': 'selector-only variant under missing-method-feedback; not semantic innovation',
                      'matched_inputs': ['config', 'dependencies', 'oracle', 'population', 'revision'],
                      'baseline': baseline, 'variant': variant, 'changes': changes}, indent=2))


if __name__ == '__main__':
    main()
