"""Independently recompute dense cosine rankings and finite trace relations."""

import argparse
from collections import Counter
import itertools
import json
import math
from pathlib import Path
import re


def dense_scores(texts):
    counts = {identity: Counter(re.findall(r'(?u)\b\w\w+\b', text.lower()))
              for identity, text in texts.items()}
    words = sorted({word for bag in counts.values() for word in bag})
    weights = [1 + math.log((len(counts) + 1) / (1 + sum(word in bag for bag in counts.values())))
               for word in words]
    return words, weights


def vectors(texts, words, weights):
    result = {}
    for identity, text in texts.items():
        bag = Counter(re.findall(r'(?u)\b\w\w+\b', text.lower()))
        vector = [bag[word] * weight for word, weight in zip(words, weights)]
        norm = math.hypot(*vector)
        result[identity] = [value / norm if norm else 0 for value in vector]
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path)
    args = parser.parse_args()
    fixtures = json.loads((args.run / 'fixtures.json').read_text())
    inputs = json.loads((args.run / 'document-inputs.json').read_text())
    for item in fixtures:
        identity = item['id']
        fields = item['fields']
        assert inputs['complete'][identity] == '\n'.join(fields.values())
        assert inputs['no_docs'][identity] == ''
        assert inputs['without_output'][identity] == '\n'.join(value for key, value in fields.items() if key != 'output')
        assert inputs['wrong_output'][identity] == '\n'.join(
            item['wrong_output'] if key == 'output' else value for key, value in fields.items())
    traces = {}
    for line in (args.run / 'trace-0.csv').read_text().splitlines():
        identity, value, result = line.split(',')
        traces.setdefault(identity, {})[int(value)] = int(result)
    assert all(set(trace) == set(range(256)) for trace in traces.values())
    assert (args.run / 'trace-0.csv').read_bytes() == (args.run / 'trace-1.csv').read_bytes()
    positives = []
    counterexamples = []
    for left, right in itertools.combinations(sorted(traces), 2):
        differing = [value for value in range(256) if traces[left][value] != traces[right][value]]
        if differing:
            value = differing[0]
            counterexamples.append({'pair': [left, right], 'input': value,
                                    'outputs': [traces[left][value], traces[right][value]]})
        else:
            positives.append([left, right])
    assert positives == json.loads((args.run / 'finite-domain-labels.json').read_text())['positive_pairs']
    bodies = {item['id']: item['body'] for item in fixtures}
    code = vectors(bodies, *dense_scores(bodies))
    doc_basis = dense_scores(inputs['complete'])
    results = json.loads((args.run / 'results.json').read_text())
    assert len(results) == 24
    for row in results:
        docs = vectors(inputs[row['arm']], *doc_basis)
        ranked = []
        for left, right in itertools.combinations(sorted(bodies), 2):
            code_score = math.fsum(first * second for first, second in zip(code[left], code[right]))
            doc_score = math.fsum(first * second for first, second in zip(docs[left], docs[right]))
            score = round({'code': code_score, 'doc': doc_score,
                           'mean_fusion': (code_score + doc_score) / 2}[row['method']], 12)
            if score > 0:
                ranked.append({'pair': [left, right], 'score': score})
        ranked.sort(key=lambda item: (-item['score'], item['pair']))
        assert ranked == row['ranking']
        assert row['hits_at_3'] == sum(item['pair'] in positives for item in ranked[:3])
    output = {'dense_recomputed_conditions': len(results), 'positive_pairs': positives,
              'unequal_pair_witnesses': counterexamples,
              'limits': 'Shared lexical specification; independent arithmetic, not independent scientific labels.'}
    (args.run / 'independent-check.json').write_text(json.dumps(output, indent=2) + '\n')
    print('PASS: 24 dense ranking recomputations, 3 equal pairs, 25 unequal-pair witnesses, intervention checks')


if __name__ == '__main__':
    main()
