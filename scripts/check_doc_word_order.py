"""Audit a frozen word-order batch without tuning its representation."""

import argparse
from collections import Counter
import json
from pathlib import Path

import numpy as np

from run_doc_tfidf import ROOT, make_vectorizer, rank_pairs, sha


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    assert args.run_id and all(character.isalnum() or character in '-_' for character in args.run_id)
    source = ROOT / 'research/evidence/runs' / args.run_id
    report = json.loads((source / 'report.json').read_text())
    manifest = json.loads((source / 'manifest.json').read_text())
    for name, digest in report['artifact_sha256'].items():
        assert sha(source / name) == digest, name
    for name, digest in manifest['sha256'].items():
        assert sha(ROOT / name) == digest, name
    protocol = json.loads((source / 'protocol.json').read_text())
    baseline = json.loads((ROOT / protocol['base_protocol']).read_text())
    docs = sorted(json.loads((ROOT / 'research/evidence/runs/2026-11-09-source-doc-inventory-02/bindings.json').read_text()), key=lambda row: row['unit_id'])
    identities = [row['unit_id'] for row in docs]
    texts = [row['doc_text'] for row in docs]
    audit = {'scope': 'post-run mechanical audit; no new relevance labels',
             'source_report_sha256': sha(source / 'report.json'),
             'checker_sha256': sha(Path(__file__)), 'conditions': {}}
    unigram_idf = None
    for name, ngrams in protocol['conditions'].items():
        first = source / f'{name}-1.json'
        assert first.read_bytes() == (source / f'{name}-2.json').read_bytes()
        recorded = json.loads(first.read_text())
        options = json.loads(json.dumps(baseline))
        options['vectorizer']['ngram_range'] = ngrams
        vectorizer = make_vectorizer(options)
        matrix = vectorizer.fit_transform(texts)
        scores = (matrix @ matrix.T).toarray()
        pairs = rank_pairs(identities, scores)
        positions = {(left, right): (rank, score) for rank, (score, left, right) in enumerate(pairs, 1)}
        ties = Counter(score for score, left, right in pairs)
        vocabulary = vectorizer.get_feature_names_out().tolist()
        current_idf = {term: float(vectorizer.idf_[index]) for index, term in enumerate(vocabulary) if ' ' not in term}
        if unigram_idf is None:
            unigram_idf = current_idf
        else:
            assert unigram_idf == current_idf
        tokenizer = vectorizer.build_tokenizer()
        preprocessor = vectorizer.build_preprocessor()
        analyzer = vectorizer.build_analyzer()
        assert analyzer('change permission; preserve type') == analyzer('change permission preserve type')
        assert not analyzer('a ! b')
        diagnostics = []
        for item in recorded['diagnostics']:
            left, right = item['unit_ids']
            rank, score = positions[(left, right)]
            assert (rank, score) == (item['rank'], item['score'])
            details = dict(item, cosine_raw=float(scores[identities.index(left), identities.index(right)]), tie_group_size=ties[score])
            if item['prior_rank'] in (1, 6):
                endpoints = []
                for identity in (left, right):
                    index = identities.index(identity)
                    row = matrix.getrow(index)
                    endpoints.append({'unit_id': identity, 'text': texts[index],
                                      'tokens': tokenizer(preprocessor(texts[index])),
                                      'counts': dict(Counter(analyzer(texts[index]))),
                                      'normalized_weights': {vocabulary[column]: float(weight) for column, weight in zip(row.indices, row.data)}})
                details['endpoints'] = endpoints
            diagnostics.append(details)
        top = [{'rank': rank, 'unit_ids': [left, right], 'cosine_rounded': score}
               for rank, (score, left, right) in enumerate(pairs[:100], 1)]
        assert top == recorded['top100']
        assert len(pairs) == recorded['positive_pairs']
        assert matrix.shape[1] == recorded['features']
        audit['conditions'][name] = {'diagnostics': diagnostics,
            'top20_endpoint_count': len({identity for item in top[:20] for identity in item['unit_ids']}),
            'punctuation_collision': True, 'single_character_zero': True}
    audit['unigram_idf_unchanged'] = True
    print(json.dumps(audit, indent=2))


if __name__ == '__main__':
    main()
