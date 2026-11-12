"""Separate terminal retrieval, tie selection and recommendation losses."""

import argparse
from collections import Counter, defaultdict
import json
import math
from pathlib import Path

from check_inmap_loop_probe import audit


def read_scores(path):
    result = defaultdict(dict)
    for line in path.read_text().splitlines():
        entity, module, value = line.split('\t')
        assert module not in result[entity]
        score = float(value)
        assert math.isfinite(score)
        result[entity][module] = score
    return result


def classify(scores, highest, recommended):
    if not scores:
        return 'no_remaining_score'
    maximum = max(scores.values())
    ties = [module for module, score in scores.items() if score == maximum]
    if not highest:
        return 'maximum_tie_not_selected' if len(ties) > 1 else 'unique_maximum_not_selected'
    if not recommended:
        return 'selected_but_not_recommended'
    return 'terminal_recommendation_present'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path)
    args = parser.parse_args()
    root = args.run
    summary = audit(root)
    scores = read_scores(root / 'terminal-classModuleSimilarity_AffinityScores.tsv')
    copied = read_scores(root / 'terminal-classModule_AffinityScores.tsv')
    highest = read_scores(root / 'terminal-highestClassScoreMappings.tsv')
    recommended = read_scores(root / 'terminal-recommendedMappings.tsv')
    assert scores == copied
    state = dict(line.split('\t') for line in (root / 'terminal-state.tsv').read_text().splitlines())
    assert state['runMapping'] == 'false'
    rows = []
    for entity in summary['unmapped']:
        remaining = scores.get(entity, {})
        maximum = max(remaining.values()) if remaining else None
        rows.append({'entity': entity, 'label_available': entity not in summary['unlabelled'],
                     'previously_recommended': entity in summary['unmapped_previously_rejected'],
                     'remaining_scores_after_rejection': remaining,
                     'maximum_modules': sorted(module for module, value in remaining.items() if value == maximum),
                     'highest_selected': highest.get(entity, {}),
                     'recommended': recommended.get(entity, {}),
                     'classification': classify(remaining, highest.get(entity), recommended.get(entity))})
    assert classify({}, {}, {}) == 'no_remaining_score'
    assert classify({'first': 2, 'second': 2}, {}, {}) == 'maximum_tie_not_selected'
    assert classify({'first': 2, 'second': 1}, {}, {}) == 'unique_maximum_not_selected'
    assert classify({'first': 2}, {'first': 2}, {}) == 'selected_but_not_recommended'
    assert classify({'first': 2}, {'first': 2}, {'first': 2}) == 'terminal_recommendation_present'
    controls = root / 'terminal-selection-controls.tsv'
    if controls.exists():
        variant = json.loads((root / 'report.json').read_text()).get('selector_variant', 'original')
        observed = {parts[0]: int(parts[1]) for parts in
                    (line.split('\t') for line in controls.read_text().splitlines()[1:])}
        assert observed == {'unique_maximum': 1, 'early_lower_tie_then_unique_maximum': int(variant == 'unique-maximum-only'),
                            'maximum_tie': 0, 'lower_tie_after_maximum': 1}
    print(json.dumps({'scope': 'terminal snapshot only; scores are after rejected-pair removal',
                      'state': state, 'counts': dict(Counter(row['classification'] for row in rows)),
                      'entities': rows}, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
