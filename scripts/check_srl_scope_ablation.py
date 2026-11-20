"""Independently recount frozen scope-ablation results without calling its scorer."""

import argparse
import hashlib
import json
from pathlib import Path


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folder', type=Path)
    parser.add_argument('frozen_inputs', type=Path)
    args = parser.parse_args()
    folder = args.folder
    report = json.loads((folder / 'report.json').read_text())
    for name, expected in report['artifact_sha256'].items():
        assert digest(folder / name) == expected, name
    frozen = json.loads((args.frozen_inputs / 'report.json').read_text())
    assert digest(folder / 'evaluator.py') == frozen['artifact_sha256']['evaluate_srl_scope.py']
    assert digest(folder / 'protocol.json') == frozen['artifact_sha256']['srl-scope-ablation-v1.json']
    assert digest(folder / 'cases.json') == frozen['artifact_sha256']['cases.json']
    cases = json.loads((folder / 'cases.json').read_text())
    reference = {row['id']: row for row in cases}
    checked_groups = 0
    for repeat in (1, 2):
        result = json.loads((folder / f'result-{repeat}.json').read_text())
        for arm, rows in result['rows'].items():
            assert [row['id'] for row in rows] == [row['id'] for row in cases]
            for row in rows:
                assert row['gold'] == reference[row['id']]['gold']
                assert row['family'] == reference[row['id']]['family']
                assert row['prediction'] in {None, 'positive', 'negative'}
            groups = [(rows, result['metrics'][arm])] + [([row for row in rows if row['family'] == family], metrics) for family, metrics in result['families'][arm].items()]
            for group, metrics in groups:
                answers = [row for row in group if row['prediction'] is not None]
                correct = [row for row in answers if row['prediction'] == row['gold']]
                assert metrics['total'] == len(group)
                assert metrics['answered'] == len(answers)
                assert metrics['correct'] == len(correct)
                assert metrics['wrong'] == len(answers)-len(correct)
                assert metrics['coverage'] == len(answers)/len(group)
                assert metrics['selective_accuracy'] == (len(correct)/len(answers) if answers else None)
                assert metrics['unconditional_accuracy'] == len(correct)/len(group)
                assert metrics['promotion'] == sum(row['prediction'] == 'positive' and row['gold'] == 'unknown' for row in group)
                assert metrics['lost_positives'] == sum(row['prediction'] is None and row['gold'] == 'positive' for row in group)
                checked_groups += 1
            if arm != 'flat':
                base = result['rows']['flat']
                withheld = [baseline for baseline, variant in zip(base, rows, strict=True) if baseline['prediction'] is not None and variant['prediction'] is None]
                for baseline, variant in zip(base, rows, strict=True):
                    assert variant['prediction'] is None or variant['prediction'] == baseline['prediction']
                expected = {'withheld': len(withheld), 'withheld_correct': sum(row['prediction'] == row['gold'] for row in withheld), 'withheld_wrong': sum(row['prediction'] != row['gold'] for row in withheld)}
                assert result['comparisons_to_flat'][arm] == expected
        assert result['metrics'] == report['metrics']
        assert result['comparisons_to_flat'] == report['comparisons']
    identical = (folder / 'result-1.json').read_bytes() == (folder / 'result-2.json').read_bytes()
    assert report['repeat_identical'] == identical
    print(json.dumps({'frozen_evaluator_unchanged': True, 'frozen_references_unchanged': True,
                      'recounted_groups': checked_groups, 'repeat_identical': identical,
                      'independent_human_labels': False}))


if __name__ == '__main__':
    main()
