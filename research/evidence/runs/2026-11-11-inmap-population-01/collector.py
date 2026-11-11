"""Compute a path-based label-coverage bound, not runtime recall."""

import argparse
import hashlib
import json
from pathlib import Path
import shutil

from audit_inmap_config import SOURCE, audit, parse


ROOT = Path(__file__).resolve().parents[1]
PATHS = ROOT / 'research/evidence/runs/2026-11-11-inmap-data-readiness-01/java-source-paths.json'
PREFIX = 'test-systems/Jabref/sources/3.7/src/main/java/'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    _, arrays = parse(SOURCE.read_text())
    mapping = audit(SOURCE.read_text())['mapping']
    oracle = {entity for entities in mapping.values() for entity in entities}
    names = set()
    for path in json.loads(PATHS.read_text()):
        assert path.startswith(PREFIX) and path.endswith('.java')
        names.add(path[len(PREFIX):-5].replace('/', '.'))
    excluded = {}
    for name in names:
        matches = [rule for rule in arrays['PackageExclusion']
                   if rule.split('*', 1)[0] and name.startswith(rule.split('*', 1)[0])]
        if matches:
            excluded[name] = matches
    retained = names - set(excluded)
    covered = retained & oracle
    report = {'scope': 'path-derived population with source-defined prefix filter; not executed InMap',
              'inputs': {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
                         for path in (SOURCE, PATHS)},
              'source_names': len(names), 'oracle_names': len(oracle),
              'excluded': dict(sorted(excluded.items())), 'retained_names': len(retained),
              'oracle_covered': len(covered),
              'retained_without_oracle': sorted(retained - oracle),
              'oracle_without_retained_path': sorted(oracle - retained),
              'conditional_coverage_ceiling': len(covered) / len(retained),
              'assumptions': ['runtime indexed entities equal these retained path-derived names',
                              'runtime uses this unchanged exact-name oracle',
                              'no other name transformation changes these sets']}
    shutil.copy2(__file__, args.output / 'collector.py')
    (args.output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
