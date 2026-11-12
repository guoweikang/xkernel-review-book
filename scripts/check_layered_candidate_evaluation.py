"""Contract controls, not clone detection or Rust effectiveness experiments."""

from copy import deepcopy
import json

from evaluate_layered_candidates import evaluate


def main():
    dataset = {'task': 'functional_overlap', 'cases': [
        {'id': name, 'family': name, 'split': 'development', 'label': label,
         'label_basis': 'unlabelled' if label == 'unknown' else 'controlled_fixture',
         'configuration': 'abstract evaluator fixture, no executable code', 'evidence': ['constructed arithmetic control']}
        for name, label in [('positive-a', 'positive'), ('negative-a', 'negative'), ('unknown-a', 'unknown'), ('missed-a', 'positive')]]}
    run = {'task': 'functional_overlap', 'split': 'development', 'retrieved': ['positive-a', 'negative-a', 'unknown-a'],
           'ranking': ['positive-a', 'negative-a', 'unknown-a'], 'budget': 3,
           'decisions': {'positive-a': 'positive', 'negative-a': 'abstain', 'unknown-a': 'positive'}}
    result = evaluate(dataset, run)
    assert result['candidate_known_positive_recall'] == 0.5
    assert result['judged_precision'] == 0.5
    assert result['top_k_relevance_bounds'] == [1 / 3, 2 / 3]
    assert result['judgment_coverage'] == 2 / 3
    assert result['unknown_label_decisions'] == {'positive': 1}
    assert result['confirmation_counts'] == {'negative/abstain': 1, 'positive/positive': 1}
    empty = dict(run, retrieved=[], ranking=[], decisions={})
    assert evaluate(dataset, empty)['judged_precision'] is None
    unknown = deepcopy(dataset)
    for case in unknown['cases']:
        case.update(label='unknown', label_basis='unlabelled')
    assert evaluate(unknown, run)['candidate_known_positive_recall'] is None
    assert evaluate(unknown, run)['top_k_relevance_bounds'] == [0, 1]
    failures = []
    mutations = {
        'task_mismatch': lambda data, output: output.update(task='responsibility_boundary'),
        'duplicate_retrieval': lambda data, output: output['retrieved'].append('positive-a'),
        'omitted_ranking': lambda data, output: output['ranking'].pop(),
        'family_leakage': lambda data, output: data['cases'].append(dict(data['cases'][0], id='copy', split='test')),
        'review_is_not_truth': lambda data, output: data['cases'][0].update(label_basis='agent_review'),
        'outside_population': lambda data, output: output['retrieved'].append('unseen'),
        'silent_abstention': lambda data, output: output['decisions'].pop('negative-a'),
        'missing_configuration': lambda data, output: data['cases'][0].update(configuration=''),
        'duplicate_reference': lambda data, output: data['cases'].append(data['cases'][0]),
        'zero_budget': lambda data, output: output.update(budget=0)
    }
    for name, mutate in mutations.items():
        data, output = deepcopy(dataset), deepcopy(run)
        mutate(data, output)
        try:
            evaluate(data, output)
        except ValueError:
            failures.append(name)
        else:
            raise AssertionError(name)
    print(json.dumps({'scope': 'constructed evaluator controls, not detection accuracy', 'positive_controls': 3,
                      'rejected_invalid_inputs': failures, 'example_result': result}, indent=2))


if __name__ == '__main__':
    main()
