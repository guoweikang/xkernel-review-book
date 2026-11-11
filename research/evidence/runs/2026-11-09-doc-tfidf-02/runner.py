"""Run the frozen direct-documentation TF-IDF development baseline."""

import argparse
from collections import Counter
import hashlib
import itertools
import json
import math
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import time

import numpy as np
import sklearn
from sklearn.feature_extraction.text import TfidfVectorizer

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def make_vectorizer(protocol):
    options = dict(protocol['vectorizer'])
    options['ngram_range'] = tuple(options['ngram_range'])
    return TfidfVectorizer(**options)


def controls(protocol):
    texts = ['read buffer buffer', 'read buffer buffer', 'write disk', '', 'x', 'not read']
    vectorizer = make_vectorizer(protocol)
    actual = vectorizer.fit_transform(texts).toarray()
    vocabulary = vectorizer.get_feature_names_out().tolist()
    counts = [Counter(re.findall(protocol['vectorizer']['token_pattern'], text.lower())) for text in texts]
    expected = []
    for count in counts:
        weights = [count[word] * (math.log((1 + len(texts)) /
                   (1 + sum(word in item for item in counts))) + 1) for word in vocabulary]
        norm = math.sqrt(sum(weight * weight for weight in weights))
        expected.append([weight / norm if norm else 0 for weight in weights])
    np.testing.assert_allclose(actual, expected, rtol=1e-12, atol=1e-12)
    similarities = actual @ actual.T
    assert abs(similarities[0, 1] - 1) < 1e-12
    assert similarities[0, 2] == 0
    assert not actual[3].any() and not actual[4].any()
    assert 'not' in vocabulary
    assert rank_pairs(['b', 'a', 'c'], np.ones((3, 3))) == [
        (1.0, 'a', 'b'), (1.0, 'a', 'c'), (1.0, 'b', 'c')]
    return {'texts': texts, 'vocabulary': vocabulary, 'manual_formula_matches': True,
            'identical_disjoint_empty_single_character_negation_ties': 'passed'}


def rank_pairs(identities, similarities):
    pairs = []
    for left, right in itertools.combinations(range(len(identities)), 2):
        score = round(float(similarities[left, right]), 12)
        if score > 0:
            first, second = sorted([identities[left], identities[right]])
            pairs.append((score, first, second))
    return sorted(pairs, key=lambda pair: (-pair[0], pair[1], pair[2]))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    protocol_path = ROOT / 'research/protocols/doc-tfidf-discovery-v1.json'
    protocol = json.loads(protocol_path.read_text())
    if sklearn.__version__ != '1.7.2':
        raise ValueError('Unexpected sklearn version')
    control = controls(protocol)
    input_path = ROOT / 'research/evidence/runs/2026-11-09-source-doc-inventory-02/bindings.json'
    if sha(input_path) != protocol['input_sha256']:
        raise ValueError('Documentation input changed')
    bindings = sorted(json.loads(input_path.read_text()), key=lambda item: item['unit_id'])
    identities = [item['unit_id'] for item in bindings]
    if len(set(identities)) != len(identities):
        raise ValueError('Duplicate unit identity')
    started = time.perf_counter()
    vectorizer = make_vectorizer(protocol)
    matrix = vectorizer.fit_transform([item['doc_text'] for item in bindings])
    similarities = (matrix @ matrix.T).toarray()
    pairs = rank_pairs(identities, similarities)
    elapsed = time.perf_counter() - started
    by_id = {item['unit_id']: item for item in bindings}
    ledger_path = ROOT / 'research/protocols/discovery-ledger-v4.json'
    ledger = json.loads(ledger_path.read_text())
    scc_pairs = {tuple(sorted(member['id'] for member in pair['members'])) for pair in ledger['records']}
    nonzero_ids = {identity for identity, count in zip(identities, matrix.getnnz(axis=1)) if count}
    candidates = []
    for rank, (score, left, right) in enumerate(pairs[:100], 1):
        candidates.append({'rank': rank, 'unit_ids': [left, right], 'cosine_rounded': score,
                           'in_scc_outputs': (left, right) in scc_pairs,
                           'members': [by_id[left], by_id[right]],
                           'review_status': 'unknown', 'truth_label': None})
    state_counts = Counter('nonzero' if item['unit_id'] in nonzero_ids else
                           'tokenizer_zero' if item['doc_text'].strip() else 'missing_or_empty'
                           for item in bindings)
    artifacts = {'top100.json': candidates, 'review-queue.json': candidates[:20],
                 'controls.json': control,
                 'vocabulary.json': {'terms': vectorizer.get_feature_names_out().tolist(),
                                     'idf': vectorizer.idf_.tolist()}}
    for name, value in artifacts.items():
        (args.output / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    shutil.copyfile(__file__, args.output / 'runner.py')
    shutil.copyfile(protocol_path, args.output / 'protocol.json')
    freeze = subprocess.check_output([sys.executable, '-m', 'pip', 'freeze'], text=True)
    (args.output / 'requirements.txt').write_text(freeze)
    report = {'schema': 'doc-tfidf-run/1', 'input_sha256': sha(input_path),
              'protocol_sha256': sha(protocol_path), 'ledger_sha256': sha(ledger_path),
              'python': platform.python_version(), 'sklearn': sklearn.__version__,
              'documents': len(bindings), 'document_states': dict(state_counts),
              'vocabulary_size': matrix.shape[1], 'positive_pairs': len(pairs),
              'possible_pairs_all': math.comb(len(bindings), 2),
              'possible_pairs_nonzero': math.comb(len(nonzero_ids), 2),
              'top20_count': len(candidates[:20]),
              'top20_scc_overlap': sum(item['in_scc_outputs'] for item in candidates[:20]),
              'scc_pairs_with_two_nonzero_docs': sum(set(pair) <= nonzero_ids for pair in scc_pairs),
              'fit_score_rank_seconds': elapsed, 'semantic_evaluation': 'not_run',
              'artifact_sha256': {path.name: sha(path) for path in args.output.iterdir() if path.is_file()}}
    (args.output / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({key: value for key, value in report.items() if key != 'artifact_sha256'}))


if __name__ == '__main__':
    main()
