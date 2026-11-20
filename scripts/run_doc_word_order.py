"""Fixed word-order sensitivity experiment, not semantic relevance evaluation."""

import argparse
from collections import Counter
import json
import math
from pathlib import Path
import platform
import re
import shutil

import numpy as np
import sklearn

from run_doc_tfidf import ROOT, make_vectorizer, rank_pairs, sha


def controls(base):
    texts = ['change permission preserve type', 'change type preserve permission',
             'change permission preserve type', 'keep type while replacing permissions',
             'do not change permission preserve type', '', 'type permission preserve change']
    vectorizer = make_vectorizer(base)
    actual = vectorizer.fit_transform(texts).toarray()
    vocabulary = vectorizer.get_feature_names_out().tolist()
    counts = []
    low, high = base['vectorizer']['ngram_range']
    for text in texts:
        tokens = re.findall(base['vectorizer']['token_pattern'], text.lower())
        counts.append(Counter(' '.join(tokens[start:start + size]) for size in range(low, high + 1)
                              for start in range(len(tokens) - size + 1)))
    expected = []
    for count in counts:
        weights = [count[word] * (math.log((1 + len(texts)) / (1 + sum(word in row for row in counts))) + 1)
                   for word in vocabulary]
        norm = math.sqrt(sum(value * value for value in weights))
        expected.append([value / norm if norm else 0 for value in weights])
    np.testing.assert_allclose(actual, expected, rtol=1e-12, atol=1e-12)
    similarity = actual @ actual.T
    assert abs(similarity[0, 2] - 1) < 1e-12 and not actual[5].any()
    if high == 1:
        assert abs(similarity[0, 1] - 1) < 1e-12
    return {'texts': texts, 'matrix': similarity.tolist(), 'formula_matches': True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    assert args.run_id and all(character.isalnum() or character in '-_' for character in args.run_id)
    output = ROOT / 'research/evidence/runs' / args.run_id
    output.mkdir()
    protocol_path = ROOT / 'research/protocols/doc-word-order-v1.json'
    protocol = json.loads(protocol_path.read_text())
    base_path = ROOT / protocol['base_protocol']
    baseline = json.loads(base_path.read_text())
    inputs = ROOT / 'research/evidence/runs/2026-11-09-source-doc-inventory-02/bindings.json'
    assert sha(inputs) == baseline['input_sha256'] and sklearn.__version__ == '1.7.2'
    docs = sorted(json.loads(inputs.read_text()), key=lambda row: row['unit_id'])
    assert len(docs) == 2180 and len({row['unit_id'] for row in docs}) == 2180
    queue_path = ROOT / 'research/evidence/runs/2026-11-09-doc-tfidf-01/review-queue.json'
    queue = json.loads(queue_path.read_text())
    manifest = {'scope': protocol['status'], 'python': platform.python_version(), 'sklearn': sklearn.__version__,
                'numpy': np.__version__, 'sha256': {str(path.relative_to(ROOT)): sha(path) for path in [protocol_path, base_path, inputs, queue_path, Path(__file__), ROOT / 'scripts/run_doc_tfidf.py']}}
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    shutil.copy2(protocol_path, output / 'protocol.json')
    shutil.copy2(__file__, output / 'runner.py')
    identities = [row['unit_id'] for row in docs]
    summaries = {}
    for repeat in range(1, protocol['repeats'] + 1):
        for condition, ngrams in protocol['conditions'].items():
            options = json.loads(json.dumps(baseline))
            options['vectorizer']['ngram_range'] = ngrams
            control = controls(options)
            vectorizer = make_vectorizer(options)
            matrix = vectorizer.fit_transform([row['doc_text'] for row in docs])
            similarities = (matrix @ matrix.T).toarray()
            pairs = rank_pairs(identities, similarities)
            positions = {(left, right): (rank, score) for rank, (score, left, right) in enumerate(pairs, 1)}
            diagnostics = []
            for pair in queue:
                key = tuple(sorted(pair['unit_ids']))
                rank, score = positions.get(key, (None, 0))
                diagnostics.append({'prior_rank': pair['rank'], 'unit_ids': list(key), 'rank': rank, 'score': score})
            top = [{'rank': rank, 'unit_ids': [left, right], 'cosine_rounded': score}
                   for rank, (score, left, right) in enumerate(pairs[:100], 1)]
            if condition == 'unigram':
                assert top[:20] == [{key: pair[key] for key in ('rank', 'unit_ids', 'cosine_rounded')} for pair in queue]
            result = {'condition': condition, 'ngrams': ngrams, 'documents': len(docs),
                      'nonzero': int(np.count_nonzero(matrix.getnnz(axis=1))), 'features': matrix.shape[1],
                      'positive_pairs': len(pairs), 'diagnostics': diagnostics, 'top100': top, 'controls': control}
            path = output / f'{condition}-{repeat}.json'
            path.write_text(json.dumps(result, indent=2) + '\n')
            if repeat > 1:
                assert path.read_bytes() == (output / f'{condition}-1.json').read_bytes()
            summaries[condition] = result
    before = {tuple(pair['unit_ids']) for pair in summaries['unigram']['top100'][:20]}
    after = {tuple(pair['unit_ids']) for pair in summaries['unigram_bigram']['top100'][:20]}
    report = {'scope': 'fixed-corpus representation sensitivity, not semantic effectiveness',
              'runs': 4, 'repeat_identity': True, 'top20_overlap': len(before & after),
              'removed_from_top20': sorted(before - after), 'added_to_top20': sorted(after - before),
              'conditions': {name: {key: value for key, value in result.items() if key not in ('controls', 'top100')}
                             for name, result in summaries.items()},
              'artifact_sha256': {path.name: sha(path) for path in output.iterdir() if path.is_file()}}
    (output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'runs': 4, 'top20_overlap': report['top20_overlap'],
                      'conditions': {name: {'nonzero': result['nonzero'], 'features': result['features'],
                                            'role_pair': result['diagnostics'][5], 'cfg_pair': result['diagnostics'][0]}
                                     for name, result in summaries.items()}}, indent=2))


if __name__ == '__main__':
    main()
