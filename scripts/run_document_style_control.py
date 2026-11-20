"""Exhaustive two-field wording assignments on frozen development fixtures."""

import argparse
from collections import Counter
import itertools
import json
from pathlib import Path
import shutil

from run_document_discovery_controls import ROOT, cosine, digest, dump, fit, transform


def execute(fixtures, protocol, positives):
    identities = sorted(item['id'] for item in fixtures)
    originals = {item['id']: item['fields'] for item in fixtures}
    variants = {identity: {style: originals[identity] | replacement
                           for style, replacement in protocol['styles'].items()} for identity in identities}
    fields = list(fixtures[0]['fields'])
    for identity in identities:
        for values in variants[identity].values():
            assert values['purpose'] == originals[identity]['purpose']
            assert values['output'] == originals[identity]['output']
    documents = [values for styles in variants.values() for values in styles.values()]
    full_weights = fit(['\n'.join(values.values()) for values in documents])
    field_weights = {field: fit([values[field] for values in documents]) for field in fields}
    encoded = {}
    for identity in identities:
        for style, values in variants[identity].items():
            encoded[identity, style] = {
                'full': transform('\n'.join(values.values()), full_weights),
                'fields': {field: transform(values[field], field_weights[field]) for field in fields}}
    results = []
    pair_scores = {method: {} for method in protocol['methods']}
    for assignment in itertools.product('AB', repeat=len(identities)):
        styles = dict(zip(identities, assignment))
        for method in protocol['methods']:
            ranking = []
            for left, right in itertools.combinations(identities, 2):
                first, second = encoded[left, styles[left]], encoded[right, styles[right]]
                if method == 'concatenated':
                    score = cosine(first['full'], second['full'])
                elif method == 'field_mean':
                    score = sum(cosine(first['fields'][field], second['fields'][field]) for field in fields) / len(fields)
                else:
                    score = cosine(first['fields']['output'], second['fields']['output'])
                score = round(score, 12)
                pair = (left, right)
                bins = pair_scores[method].setdefault(pair, {'same': [], 'different': []})
                bins['same' if styles[left] == styles[right] else 'different'].append(score)
                if score > 0:
                    ranking.append({'pair': list(pair), 'score': score})
            ranking.sort(key=lambda item: (-item['score'], item['pair']))
            results.append({'assignment': ''.join(assignment), 'method': method, 'ranking': ranking,
                            'hits_at_3': sum(item['pair'] in positives for item in ranking[:3])})
    effects = {}
    for method, pairs in pair_scores.items():
        effects[method] = []
        for pair, bins in pairs.items():
            assert len(bins['same']) == len(bins['different']) == 128
            effects[method].append({'pair': list(pair), 'finite_equal': list(pair) in positives,
                                    'same_minus_different': sum(bins['same']) / 128 - sum(bins['different']) / 128})
    output_rankings = [row['ranking'] for row in results if row['method'] == 'output_only']
    assert all(ranking == output_rankings[0] for ranking in output_rankings)
    return results, effects, variants


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['prepare', 'execute'])
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    output = args.output
    if args.action == 'prepare':
        output.mkdir(parents=True, exist_ok=False)
        prior = ROOT / 'research/evidence/runs/2026-11-16-document-controls-01'
        sources = {'protocol.json': ROOT / 'research/protocols/document-style-control-v1.json',
                   'fixtures.json': prior / 'fixtures.json', 'labels.json': prior / 'finite-domain-labels.json',
                   'trace.csv': prior / 'trace-0.csv', 'runner.py': Path(__file__),
                   'scoring.py': ROOT / 'scripts/run_document_discovery_controls.py'}
        for name, source in sources.items():
            shutil.copyfile(source, output / name)
        dump(output / 'freeze.json', {name: digest(output / name) for name in sources})
        return
    assert not (output / 'results-0.json').exists(), 'Refuse result overwrite'
    frozen = json.loads((output / 'freeze.json').read_text())
    assert all(digest(output / name) == value for name, value in frozen.items())
    assert digest(Path(__file__)) == frozen['runner.py']
    assert digest(ROOT / 'scripts/run_document_discovery_controls.py') == frozen['scoring.py']
    fixtures = json.loads((output / 'fixtures.json').read_text())
    protocol = json.loads((output / 'protocol.json').read_text())
    positives = json.loads((output / 'labels.json').read_text())['positive_pairs']
    traces = {}
    for line in (output / 'trace.csv').read_text().splitlines():
        identity, value, result = line.split(',')
        traces.setdefault(identity, {})[int(value)] = int(result)
    assert set(traces) == {item['id'] for item in fixtures}
    assert all(set(values) == set(range(256)) for values in traces.values())
    assert positives == [list(pair) for pair in itertools.combinations(sorted(traces), 2)
                         if traces[pair[0]] == traces[pair[1]]]
    runs = [execute(fixtures, protocol, positives) for _ in range(protocol['repeats'])]
    assert runs[0] == runs[1]
    for repeat, (results, effects, variants) in enumerate(runs):
        dump(output / f'results-{repeat}.json', results)
    dump(output / 'pair-effects.json', runs[0][1])
    dump(output / 'documents.json', runs[0][2])
    summary = {'assignments': 256, 'repeats_equal': True, 'output_negative_control': 'passed',
               'hits_at_3_distribution': {method: dict(Counter(row['hits_at_3'] for row in runs[0][0]
                                                              if row['method'] == method))
                                           for method in protocol['methods']},
               'mean_pair_style_delta': {method: sum(row['same_minus_different'] for row in values) / len(values)
                                         for method, values in runs[0][1].items()},
               'new_rust_executions': 0, 'independent_holdout': False}
    dump(output / 'summary.json', summary)
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
