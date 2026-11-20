"""Frozen native-document LDA development adaptation with TF-IDF control."""

import argparse
import itertools
import json
from pathlib import Path
import shutil

import numpy as np
import sklearn
from sklearn.decomposition import LatentDirichletAllocation
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.preprocessing import normalize

from run_doc_tfidf import ROOT, make_vectorizer, rank_pairs, sha


def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    protocol_path = ROOT / 'research/protocols/doc-lda-v1.json'
    protocol = json.loads(protocol_path.read_text())
    baseline_path = ROOT / 'research/protocols/doc-tfidf-discovery-v1.json'
    baseline = json.loads(baseline_path.read_text())
    source = ROOT / protocol['input']
    assert sha(source) == protocol['input_sha256']
    assert sklearn.__version__ == '1.7.2'
    args.output.mkdir(parents=True, exist_ok=False)
    shutil.copyfile(__file__, args.output / 'runner.py')
    shutil.copyfile(protocol_path, args.output / 'protocol.json')
    dump(args.output / 'freeze.json', {
        'input_sha256': sha(source), 'protocol_sha256': sha(protocol_path),
        'runner_sha256': sha(Path(__file__)), 'baseline_sha256': sha(baseline_path),
        'shared_helpers_sha256': sha(ROOT / 'scripts/run_doc_tfidf.py'),
        'sklearn': sklearn.__version__, 'numpy': np.__version__})
    bindings = sorted(json.loads(source.read_text()), key=lambda item: item['unit_id'])
    identities = [item['unit_id'] for item in bindings]
    texts = [item['doc_text'] for item in bindings]
    tfidf = make_vectorizer(baseline)
    weighted = tfidf.fit_transform(texts)
    counter = CountVectorizer(lowercase=True, token_pattern=baseline['vectorizer']['token_pattern'])
    counts = counter.fit_transform(texts)
    assert list(counter.get_feature_names_out()) == list(tfidf.get_feature_names_out())
    eligible = counts.getnnz(axis=1) > 0
    assert np.array_equal(eligible, weighted.getnnz(axis=1) > 0)
    selected_ids = [identity for identity, keep in zip(identities, eligible) if keep]
    rankings = {'tfidf': rank_pairs(identities, (weighted @ weighted.T).toarray())[:protocol['budget']]}
    vocabulary = counter.get_feature_names_out().tolist()
    dump(args.output / 'vocabulary.json', vocabulary)
    for seed in protocol['seeds']:
        model = LatentDirichletAllocation(random_state=seed, **protocol['lda'])
        distributions = model.fit_transform(counts[eligible])
        np.testing.assert_allclose(distributions.sum(axis=1), 1, atol=1e-12)
        assert np.isfinite(distributions).all() and (distributions > 0).all()
        vectors = normalize(distributions)
        scores = vectors @ vectors.T
        np.testing.assert_allclose(np.diag(scores), 1, atol=1e-12)
        rankings[str(seed)] = rank_pairs(selected_ids, scores)[:protocol['budget']]
        np.savez_compressed(args.output / f'model-{seed}.npz', distributions=distributions, components=model.components_)
        dump(args.output / f'topics-{seed}.json', [[vocabulary[index] for index in np.argsort(-weights, kind='stable')[:15]] for weights in model.components_])
    by_id = {item['unit_id']: item for item in bindings}
    union = sorted({tuple(pair[1:]) for ranking in rankings.values() for pair in ranking})
    dump(args.output / 'review-queue.json', [{'unit_ids': pair, 'members': [by_id[identity] for identity in pair], 'status': 'not_reviewed'} for pair in union])
    dump(args.output / 'rankings.json', rankings)
    dump(args.output / 'eligible-ids.json', selected_ids)
    overlaps = {f'{left}:{right}': len({tuple(pair[1:]) for pair in rankings[left]} & {tuple(pair[1:]) for pair in rankings[right]}) for left, right in itertools.combinations(rankings, 2)}
    report = {'total': len(bindings), 'nonzero': int(eligible.sum()), 'excluded_zero': int((~eligible).sum()), 'union_pairs': len(union), 'top20_intersections': overlaps, 'semantic_evaluation': 'pending; no precision or recall', 'checks': 'vocabulary, eligibility, finite probabilities, probability sums, cosine diagonals passed'}
    dump(args.output / 'report.json', report)
    print(json.dumps(report))


if __name__ == '__main__':
    main()
