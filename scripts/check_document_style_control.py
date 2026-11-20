"""Dense recomputation of every frozen wording-control ranking."""

import argparse
import itertools
import json
import math
from pathlib import Path

from check_document_discovery_controls import dense_scores, vectors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path)
    args = parser.parse_args()
    documents = json.loads((args.run / 'documents.json').read_text())
    fixtures = json.loads((args.run / 'fixtures.json').read_text())
    styles = json.loads((args.run / 'protocol.json').read_text())['styles']
    for fixture in fixtures:
        for style, values in documents[fixture['id']].items():
            assert values == fixture['fields'] | styles[style]
    expanded = {identity + style: values for identity, variants in documents.items()
                for style, values in variants.items()}
    full = {key: '\n'.join(values.values()) for key, values in expanded.items()}
    full_vectors = vectors(full, *dense_scores(full))
    field_vectors = {}
    for field in fixtures[0]['fields']:
        texts = {key: values[field] for key, values in expanded.items()}
        field_vectors[field] = vectors(texts, *dense_scores(texts))
    first = json.loads((args.run / 'results-0.json').read_text())
    assert first == json.loads((args.run / 'results-1.json').read_text())
    expected_assignments = {''.join(values) for values in itertools.product('AB', repeat=8)}
    assert len(first) == 768
    assert {(row['assignment'], row['method']) for row in first} == {
        (assignment, method) for assignment in expected_assignments
        for method in ('concatenated', 'field_mean', 'output_only')}
    positives = json.loads((args.run / 'labels.json').read_text())['positive_pairs']
    for row in first:
        assignment = dict(zip(sorted(documents), row['assignment']))
        ranking = []
        for left, right in itertools.combinations(sorted(documents), 2):
            first_key, second_key = left + assignment[left], right + assignment[right]
            def dot(mapping):
                return math.fsum(first_value * second_value for first_value, second_value in
                                 zip(mapping[first_key], mapping[second_key]))
            score = {'concatenated': dot(full_vectors),
                     'field_mean': math.fsum(dot(mapping) for mapping in field_vectors.values()) / 4,
                     'output_only': dot(field_vectors['output'])}[row['method']]
            score = round(score, 12)
            if score > 0:
                ranking.append({'pair': [left, right], 'score': score})
        ranking.sort(key=lambda item: (-item['score'], item['pair']))
        assert ranking == row['ranking']
        assert row['hits_at_3'] == sum(item['pair'] in positives for item in ranking[:3])
    print('PASS: 768 unique condition rankings densely recomputed; 2 repeats equal; frozen two-field interventions')


if __name__ == '__main__':
    main()
