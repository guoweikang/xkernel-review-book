"""Audit original-loop outputs without treating oracle agreement as design quality."""

import argparse
import csv
import hashlib
import json
from pathlib import Path


def audit(root):
    report = json.loads((root / 'report.json').read_text())
    assert report['returncode'] == 0
    assert report['scope'].startswith(('explicit missing-method-feedback control', 'source-declared method feedback variant'))
    for name, checksum in report['artifact_sha256'].items():
        assert hashlib.sha256((root / name).read_bytes()).hexdigest() == checksum, name
    population = set((root / 'filtered-classes.txt').read_text().splitlines())
    def pairs(name):
        rows = [tuple(row.split('\t')) for row in (root / name).read_text().splitlines()]
        assert all(len(row) == 2 for row in rows)
        assert len(rows) == len(set(rows))
        return set(rows)
    oracle = pairs('oracle.tsv')
    accepted = pairs('acceptedMappings.tsv')
    rejected = pairs('rejectedMappings.tsv')
    assert accepted <= oracle
    assert not rejected & oracle
    assert not accepted & rejected
    assert {entity for entity, module in accepted | rejected} <= population
    assert len({entity for entity, module in accepted}) == len(accepted)
    with (root / 'pages.tsv').open() as stream:
        pages = list(csv.DictReader(stream, delimiter='\t'))
    accepted_events = sum(int(page['numberOfAcceptedClasses']) for page in pages)
    recommendation_events = sum(int(page['numberOfRecommendations']) for page in pages)
    assert accepted_events == len(accepted)
    assert recommendation_events == len(accepted) + len(rejected)
    assert int(pages[-1]['numOfMappedClasses']) == len(accepted)
    unmapped = population - {entity for entity, module in accepted}
    unlabelled = population - {entity for entity, module in oracle}
    return {'population': len(population), 'pages': len(pages),
            'selector_variant': report.get('selector_variant', 'original'),
            'method_feedback': report.get('method_feedback', 'none'),
            'accepted': len(accepted), 'rejected': len(rejected),
            'recommendations': recommendation_events,
            'oracle_agreement_precision': len(accepted) / recommendation_events,
            'population_mapping_fraction': len(accepted) / len(population),
            'unmapped': sorted(unmapped), 'unlabelled': sorted(unlabelled),
            'labelled_unmapped': sorted(unmapped - unlabelled),
            'unmapped_previously_rejected': sorted(unmapped & {entity for entity, module in rejected}),
            'never_recommended': sorted(unmapped - {entity for entity, module in rejected}),
            'scope': report['scope']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path)
    parser.add_argument('--repeat', type=Path)
    args = parser.parse_args()
    result = audit(args.run)
    if args.repeat:
        assert result == audit(args.repeat)
        for name in ('pages.tsv', 'acceptedMappings.tsv', 'rejectedMappings.tsv', 'filtered-classes.txt', 'oracle.tsv'):
            assert (args.run / name).read_bytes() == (args.repeat / name).read_bytes(), name
        result['repeat_core_outputs_byte_identical'] = True
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
