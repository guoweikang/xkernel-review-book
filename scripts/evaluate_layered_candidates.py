"""Score a frozen single-task reference without treating unknown labels as negatives."""

import argparse
from collections import Counter
import json
from pathlib import Path


def ratio(numerator, denominator):
    return numerator / denominator if denominator else None


def evaluate(dataset, run):
    if dataset['task'] not in {'functional_overlap', 'responsibility_boundary'} or run['task'] != dataset['task']:
        raise ValueError('Single matching task required')
    cases = {}
    families = {}
    for case in dataset['cases']:
        if case['id'] in cases:
            raise ValueError('Duplicate reference ID')
        if case['split'] not in {'development', 'test'} or not case['family']:
            raise ValueError('Explicit split and origin family required')
        previous = families.setdefault(case['family'], case['split'])
        if previous != case['split']:
            raise ValueError('Family crosses splits')
        if case['label'] not in {'positive', 'negative', 'unknown'}:
            raise ValueError('Unknown label value')
        if case['label'] == 'unknown':
            if case['label_basis'] != 'unlabelled':
                raise ValueError('Unknown requires unlabelled basis')
        elif case['label_basis'] not in {'independent_adjudication', 'controlled_fixture'}:
            raise ValueError('Researcher disposition is not a truth label')
        if not case['evidence'] or not case['configuration']:
            raise ValueError('Evidence and configuration scope required')
        cases[case['id']] = case
    if run['split'] not in {'development', 'test'}:
        raise ValueError('Invalid run split')
    reference = {key: value for key, value in cases.items() if value['split'] == run['split']}
    retrieved, ranking = run['retrieved'], run['ranking']
    if len(retrieved) != len(set(retrieved)) or not set(retrieved) <= reference.keys():
        raise ValueError('Duplicate or out-of-scope retrieved ID')
    if len(ranking) != len(set(ranking)) or set(ranking) != set(retrieved):
        raise ValueError('Ranking must be an explicit permutation of retrieved candidates')
    if type(run['budget']) is not int or run['budget'] < 1:
        raise ValueError('Positive integer candidate budget required')
    selected = ranking[:run['budget']]
    if set(run['decisions']) != set(selected):
        raise ValueError('Each budgeted candidate needs a decision or explicit abstention')
    positives = {key for key, case in reference.items() if case['label'] == 'positive'}
    counts = Counter(reference[key]['label'] for key in selected)
    judged = counts['positive'] + counts['negative']
    confusion = Counter()
    unknown_predictions = Counter()
    for key in selected:
        decision = run['decisions'][key]
        if decision not in {'positive', 'negative', 'abstain'}:
            raise ValueError('Invalid confirmation decision')
        label = reference[key]['label']
        if label == 'unknown':
            unknown_predictions[decision] += 1
        else:
            confusion[label + '/' + decision] += 1
    return {
        'task': dataset['task'], 'split': run['split'],
        'scope': 'frozen reference only; labels and family assignments require independent provenance review',
        'reference_cases': len(reference), 'reference_known_positives': len(positives),
        'retrieved': len(retrieved), 'budget': run['budget'], 'selected': len(selected),
        'candidate_known_positive_recall': ratio(len(positives & set(retrieved)), len(positives)),
        'top_k_known_positive_recall': ratio(len(positives & set(selected)), len(positives)),
        'top_k_relevance_bounds': [ratio(counts['positive'], len(selected)), ratio(counts['positive'] + counts['unknown'], len(selected))],
        'judged_precision': ratio(counts['positive'], judged),
        'judgment_coverage': ratio(judged, len(selected)),
        'confirmation_counts': dict(sorted(confusion.items())),
        'unknown_label_decisions': dict(sorted(unknown_predictions.items()))
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('dataset', type=Path)
    parser.add_argument('run', type=Path)
    args = parser.parse_args()
    print(json.dumps(evaluate(json.loads(args.dataset.read_text()), json.loads(args.run.read_text())), indent=2))


if __name__ == '__main__':
    main()
