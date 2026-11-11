"""Check a small explicit-entity implementation of the FSE95 projection definition."""

import argparse
import hashlib
import json
from pathlib import Path


def project(high_edges, source_edges, rules, mode):
    if mode not in {'first', 'all'}:
        raise ValueError('Mapping mode must be explicit')

    def targets(entity):
        matched = [set(rule['targets']) for rule in rules if rule['source'] == entity]
        if not matched:
            return set()
        return matched[0] if mode == 'first' else set().union(*matched)

    evidence = {}
    unmapped = set()
    for source, target in set(map(tuple, source_edges)):
        source_targets, target_targets = targets(source), targets(target)
        if not source_targets or not target_targets:
            unmapped.add((source, target))
        for high_source in source_targets:
            for high_target in target_targets:
                evidence.setdefault((high_source, high_target), set()).add((source, target))
    declared = set(map(tuple, high_edges))
    observed = set(evidence)
    convergence, divergence, absence = declared & observed, observed - declared, declared - observed
    assert not (convergence & divergence or convergence & absence or divergence & absence)
    assert convergence | divergence == observed
    return {'convergence': sorted(convergence), 'divergence': sorted(divergence),
            'absence': sorted(absence), 'unmapped': sorted(unmapped),
            'evidence': [{'edge': edge, 'sources': sorted(contributors)}
                         for edge, contributors in sorted(evidence.items())]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    high = [('A', 'B'), ('B', 'C')]
    source = [('a', 'b'), ('b', 'a')]
    rules = [{'source': 'a', 'targets': ['A']}, {'source': 'b', 'targets': ['B']}]
    fixtures = []

    def check(name, high_edges, source_edges, mapping, mode, expected):
        result = project(high_edges, source_edges, mapping, mode)
        for key, value in expected.items():
            assert result[key] == value, (name, key, result[key], value)
        fixtures.append({'name': name, 'high_edges': high_edges, 'source_edges': source_edges,
                         'rules': mapping, 'mode': mode, 'expected': expected, 'actual': result})

    check('basic', high, source, rules, 'first', {
        'convergence': [('A', 'B')], 'divergence': [('B', 'A')],
        'absence': [('B', 'C')], 'unmapped': []})
    check('missing_mapping', high, source, rules[:1], 'first', {
        'convergence': [], 'divergence': [], 'absence': high, 'unmapped': source})
    multiple = [rules[0], {'source': 'a', 'targets': ['C']}, rules[1]]
    check('first_match', high, source, multiple, 'first', {
        'convergence': [('A', 'B')], 'divergence': [('B', 'A')], 'absence': [('B', 'C')]})
    check('all_matches', high, source, multiple, 'all', {
        'convergence': high, 'divergence': [('B', 'A'), ('C', 'B')], 'absence': []})
    check('reordered_first', high, source, [multiple[1], multiple[0], multiple[2]], 'first', {
        'convergence': [('B', 'C')], 'divergence': [('C', 'B')], 'absence': [('A', 'B')]})
    check('contributors_and_duplicate', [('A', 'B')], [('a', 'b'), ('a', 'b'), ('c', 'b')],
          rules + [{'source': 'c', 'targets': ['A']}], 'all', {
              'convergence': [('A', 'B')], 'divergence': [], 'absence': [],
              'evidence': [{'edge': ('A', 'B'), 'sources': [('a', 'b'), ('c', 'b')]}]})
    try:
        project(high, source, rules, 'unspecified')
    except ValueError:
        invalid_mode_rejected = True
    else:
        raise AssertionError('Invalid mode accepted')
    script = Path(__file__).read_bytes()
    report = {'method': 'FSE95 section 3 explicit-entity projection reimplementation',
              'original_tool_run': False, 'original_results_reproduced': False,
              'semantic_accuracy_measured': False, 'passed': True,
              'fixtures': fixtures, 'invalid_mode_rejected': invalid_mode_rejected,
              'script_sha256': hashlib.sha256(script).hexdigest()}
    (args.output / 'runner.py').write_bytes(script)
    (args.output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(f'PASS: {len(fixtures)} hand-specified fixtures; invalid mapping mode rejected')


if __name__ == '__main__':
    main()
