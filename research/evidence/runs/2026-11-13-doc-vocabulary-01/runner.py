"""Isolate frozen word vocabulary loss and contrast exact character counts."""

import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import re
import shutil

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def word_counts(text):
    tokens = re.findall(r'(?u)\b\w\w+\b', text.lower())
    return Counter(' '.join(tokens[start:start + size]) for size in (1, 2)
                   for start in range(len(tokens) - size + 1))


def char_counts(text):
    text = ' '.join(text.lower().split())
    return Counter(text[start:start + size] for size in (3, 4, 5)
                   for start in range(len(text) - size + 1))


def cosine(left, right):
    return round(sum(value * right.get(term, 0) for term, value in left.items()), 12)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9_-]+', args.run_id):
        raise ValueError('invalid run id')
    folder = ROOT / 'research/evidence/runs' / args.run_id
    folder.mkdir()
    protocol_path = ROOT / 'research/protocols/doc-vocabulary-v1.json'
    plan = json.loads(protocol_path.read_text())
    parent = ROOT / plan['parent']
    parent_manifest = json.loads((parent / 'manifest.json').read_text())
    corpus_path = ROOT / plan['corpus']
    if sha(corpus_path) != parent_manifest['inputs'][plan['corpus']]:
        raise ValueError('corpus identity mismatch')
    for relative, expected in json.loads((parent / 'report.json').read_text())['artifact_sha256'].items():
        if sha(parent / relative) != expected:
            raise ValueError('parent artifact mismatch')
    corpus = json.loads(corpus_path.read_text())
    inputs = json.loads((parent / 'inputs.json').read_text())
    queries = json.loads((parent / 'protocol.json').read_text())['queries']
    frequencies = Counter()
    for row in corpus:
        frequencies.update(word_counts(row['doc_text']).keys())
    vocabulary = set(frequencies)
    all_texts = [row['text'] for rows in inputs.values() for row in rows]
    all_texts += [row['text'] for row in queries] + list(plan['controls'].values())
    extended = vocabulary | {term for text in all_texts for term in word_counts(text)}
    shutil.copy2(protocol_path, folder / 'protocol.json')
    shutil.copy2(__file__, folder / 'runner.py')
    (folder / 'inputs.json').write_text(json.dumps({'conditions': inputs, 'queries': queries, 'controls': plan['controls']}, indent=2) + '\n')
    results = {}
    for method in plan['methods']:
        def vector(text):
            counts = char_counts(text) if method == 'char_count' else word_counts(text)
            allowed = vocabulary if method == 'frozen_word' else extended
            values = {term: count if method == 'char_count' else
                      count * (math.log((1 + len(corpus)) / (1 + frequencies[term])) + 1)
                      for term, count in counts.items() if method == 'char_count' or term in allowed}
            norm = math.sqrt(sum(value * value for value in values.values()))
            return {term: value / norm for term, value in values.items()} if norm else {}

        for repeat in range(1, plan['repeats'] + 1):
            rankings = {}
            for condition, rows in inputs.items():
                rankings[condition] = []
                for query in queries:
                    query_vector = vector(query['text'])
                    ordered = sorted([{'id': row['id'], 'score': cosine(query_vector, vector(row['text']))}
                                      for row in rows], key=lambda row: (-row['score'], row['id']))
                    rankings[condition].append({'query': query['id'], 'all_scores': ordered,
                                                'top1': [row for row in ordered if row['score'] > 0][:1]})
                if method == 'frozen_word':
                    prior = json.loads((parent / f'unigram_bigram-{condition}-1.json').read_text())
                    if rankings[condition] != prior['rankings']:
                        raise ValueError('baseline regression')
            pairs = []
            for before, after in zip(inputs['docs_source-revised'], inputs['docs_source-intervention']):
                left, right = vector(before['text']), vector(after['text'])
                counter = char_counts if method == 'char_count' else word_counts
                old, new = counter(before['text']), counter(after['text'])
                changed = {term for term in old.keys() | new.keys() if old[term] != new[term]}
                kept = changed & (left.keys() | right.keys())
                pairs.append({'packet': before['id'], 'identical_vectors': left == right,
                              'cosine': cosine(left, right), 'changed_features': len(changed),
                              'retained_changed_features': len(kept)})
            controls = {name: cosine(vector(plan['controls']['base']), vector(text))
                        for name, text in plan['controls'].items()}
            if controls['identical'] != 1 or controls['empty'] != 0:
                raise ValueError('control failed')
            result = {'method': method, 'pairs': pairs, 'controls': controls, 'rankings': rankings}
            path = folder / f'{method}-{repeat}.json'
            path.write_text(json.dumps(result, indent=2) + '\n')
            if repeat > 1 and path.read_bytes() != (folder / f'{method}-1.json').read_bytes():
                raise ValueError('repeat mismatch')
            results[method] = {'pairs': pairs, 'controls': controls}
    sources = [protocol_path, corpus_path, parent / 'report.json', Path(__file__)]
    (folder / 'manifest.json').write_text(json.dumps({'input_sha256': {str(path.relative_to(ROOT)): sha(path) for path in sources},
                                                    'original_vocabulary': len(vocabulary), 'extended_vocabulary': len(extended)}, indent=2) + '\n')
    report = {'executions': 6, 'baseline_matches_prior': True, 'repeat_identical': True,
              'results': results, 'artifact_sha256': {str(path.relative_to(folder)): sha(path) for path in sorted(folder.iterdir()) if path.is_file()}}
    (folder / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({key: value for key, value in report.items() if key != 'artifact_sha256'}, indent=2))


if __name__ == '__main__':
    main()
