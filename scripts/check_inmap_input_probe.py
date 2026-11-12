"""Validate actual original input-pipeline outputs against pinned source/oracle sets."""

import argparse
import hashlib
import json
import math
from pathlib import Path

from audit_inmap_config import SOURCE, audit


ROOT = Path(__file__).resolve().parents[1]
PREFIX = 'test-systems/Jabref/sources/3.7/src/main/java/'


def check(run):
    report = json.loads((run / 'report.json').read_text())
    assert report['returncode'] == 0
    for name, expected in report['artifact_sha256'].items():
        assert hashlib.sha256((run / name).read_bytes()).hexdigest() == expected, name
    stderr = (run / 'stderr.txt').read_text()
    assert 'Exception' not in stderr and '\tat ' not in stderr
    source_run = ROOT / 'research/evidence/runs/2026-11-11-inmap-data-readiness-01'
    source_paths = json.loads((source_run / 'java-source-paths.json').read_text())
    source_names = {path[len(PREFIX):-5].replace('/', '.') for path in source_paths}
    population = json.loads((ROOT / 'research/evidence/runs/2026-11-11-inmap-population-01/report.json').read_text())
    expected_filtered = source_names - set(population['excluded'])
    filtered = (run / 'filtered-classes.txt').read_text().splitlines()
    assert len(filtered) == len(set(filtered)) == 842
    assert set(filtered) == expected_filtered
    indexed = (run / 'indexed-paths.txt').read_text().splitlines()
    indexed_names = {path[len(PREFIX):-5].replace('/', '.') for path in indexed}
    assert all(path.startswith(PREFIX) and path.endswith('.jvtp') for path in indexed)
    assert len(indexed) == len(indexed_names) == 843
    assert indexed_names == source_names
    mapping = audit(SOURCE.read_text())['mapping']
    oracle = {entity for entities in mapping.values() for entity in entities}
    assert sorted(set(filtered) - oracle) == population['retained_without_oracle']
    scores = {}
    for line in (run / 'initial-ir-scores.tsv').read_text().splitlines():
        entity, module, value = line.split('\t')
        assert entity in indexed_names and module in mapping
        assert (entity, module) not in scores
        score = float(value)
        assert math.isfinite(score)
        scores[(entity, module)] = score
    retrieval_limit = report.get('retrieval_limit_override') or 842
    assert len(scores) == retrieval_limit * 6
    scored_entities = {entity for entity, module in scores}
    summary = {'runtime_index_documents': len(indexed), 'runtime_filtered_entities': len(filtered),
               'runtime_filtered_without_oracle': sorted(set(filtered) - oracle),
               'original_initial_ir_pairs': len(scores),
               'scored_entities': len(scored_entities),
               'scored_outside_filtered_population': sorted(scored_entities - expected_filtered),
               'incomplete_entity_rows': {entity: sorted(module for candidate, module in scores if candidate == entity)
                                          for entity in sorted(scored_entities)
                                          if sum(candidate == entity for candidate, module in scores) != len(mapping)},
               'scored_unlabelled_entities': {entity: {module: scores[(entity, module)] for module in mapping}
                                            for entity in sorted(set(filtered) - oracle)},
               'scope': 'original input pipeline and initial IR only; no final recall measured'}
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path)
    parser.add_argument('--repeat', type=Path)
    parser.add_argument('--limit-control', type=Path)
    args = parser.parse_args()
    summary = check(args.run)
    if args.repeat:
        assert check(args.repeat) == summary
        for name in ('filtered-classes.txt', 'indexed-paths.txt', 'initial-ir-scores.tsv'):
            assert (args.run / name).read_bytes() == (args.repeat / name).read_bytes()
    if args.limit_control:
        control = check(args.limit_control)
        def read_scores(path):
            return {tuple(row[:2]): float(row[2]) for row in
                    (line.split('\t') for line in (path / 'initial-ir-scores.tsv').read_text().splitlines())}
        before, after = read_scores(args.run), read_scores(args.limit_control)
        assert set(before) <= set(after)
        assert all(value == after[key] for key, value in before.items())
        added = sorted(set(after) - set(before))
        assert len(added) == 6 and control['original_initial_ir_pairs'] == 5058
        summary['retrieval_limit_control'] = {'added_pairs': added, 'common_scores_unchanged': True}
    print(json.dumps(summary, indent=2))
    print('PASS: hashes, no exception stack, exact runtime populations, finite original scores, repeat if supplied')


if __name__ == '__main__':
    main()
