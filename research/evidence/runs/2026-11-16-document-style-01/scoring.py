"""Finite-domain Rust controls for code/document discovery, not refactor labels."""

import argparse
from collections import Counter
import hashlib
import itertools
import json
import math
from pathlib import Path
import re
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def counts(text):
    return Counter(re.findall(r'(?u)\b\w\w+\b', text.lower()))


def fit(texts):
    bags = [counts(text) for text in texts]
    vocabulary = sorted(set().union(*(bag.keys() for bag in bags)))
    return {word: math.log((1 + len(bags)) / (1 + sum(word in bag for bag in bags))) + 1
            for word in vocabulary}


def transform(text, weights):
    vector = {word: count * weights[word] for word, count in counts(text).items() if word in weights}
    norm = math.sqrt(sum(value * value for value in vector.values()))
    return {word: value / norm for word, value in vector.items()} if norm else {}


def cosine(left, right):
    return sum(value * right.get(word, 0) for word, value in left.items())


def document(fixture, arm):
    if arm == 'no_docs':
        return ''
    fields = dict(fixture['fields'])
    if arm == 'without_output':
        del fields['output']
    if arm == 'wrong_output':
        fields['output'] = fixture['wrong_output']
    return '\n'.join(fields.values())


def expected(name, value):
    return {'clamp': min(value, 63), 'remainder': value % 16,
            'quotient': value // 16, 'aligned': value // 16 * 16,
            'predicate': int(value >= 16)}[name]


def rank(identities, code, docs, method):
    pairs = []
    for left, right in itertools.combinations(identities, 2):
        code_score = cosine(code[left], code[right])
        doc_score = cosine(docs[left], docs[right])
        score = {'code': code_score, 'doc': doc_score,
                 'mean_fusion': (code_score + doc_score) / 2}[method]
        score = round(score, 12)
        if score > 0:
            pairs.append({'pair': [left, right], 'score': score})
    return sorted(pairs, key=lambda item: (-item['score'], item['pair']))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['prepare', 'execute'])
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    output = args.output
    if args.action == 'prepare':
        output.mkdir(parents=True, exist_ok=False)
        for source, name in [(ROOT / 'research/protocols/document-discovery-controls-v1.json', 'protocol.json'),
                             (ROOT / 'research/protocols/document-discovery-fixtures-v1.json', 'fixtures.json'),
                             (Path(__file__), 'runner.py')]:
            shutil.copyfile(source, output / name)
        dump(output / 'freeze.json', {name: digest(output / name)
                                      for name in ('protocol.json', 'fixtures.json', 'runner.py')})
        return
    if (output / 'results.json').exists():
        raise ValueError('Completed run cannot be overwritten')
    frozen = json.loads((output / 'freeze.json').read_text())
    assert digest(Path(__file__)) == frozen['runner.py']
    assert all(digest(output / name) == checksum for name, checksum in frozen.items())
    protocol = json.loads((output / 'protocol.json').read_text())
    fixtures = json.loads((output / 'fixtures.json').read_text())
    assert len({item['id'] for item in fixtures}) == len(fixtures)
    assert all(set(item['fields']) == set(protocol['fields']) for item in fixtures)
    rust = '\n'.join(f"fn {item['id']}(value: u16) -> u16 {{ {item['body']} }}" for item in fixtures)
    calls = '\n'.join(f'println!("{item["id"]},{{}},{{}}", value, {item["id"]}(value));' for item in fixtures)
    rust += '\nfn main() { for value in 0..=255u16 {\n' + calls + '\n} }\n'
    (output / 'fixture.rs').write_text(rust)
    binary = ROOT / '.build/document-discovery-controls' / output.name
    binary.parent.mkdir(parents=True, exist_ok=True)
    version = subprocess.check_output(['rustc', '--version'], text=True)
    command = ['rustc', '--edition=2021', '-Dwarnings', str(output / 'fixture.rs'), '-o', str(binary)]
    built = subprocess.run(command, capture_output=True, text=True, timeout=60)
    (output / 'build.log').write_text(built.stdout + built.stderr)
    dump(output / 'environment.json', {'rustc': version.strip(), 'command': command, 'exit_code': built.returncode})
    built.check_returncode()
    traces = [subprocess.check_output([str(binary)], text=True, timeout=10) for _ in range(2)]
    assert traces[0] == traces[1]
    vectors = {item['id']: [] for item in fixtures}
    by_id = {item['id']: item for item in fixtures}
    for line in traces[0].splitlines():
        identity, value, result = line.split(',')
        assert int(value) == len(vectors[identity])
        assert int(result) == expected(by_id[identity]['oracle'], int(value))
        vectors[identity].append(int(result))
    assert all(len(vector) == 256 for vector in vectors.values())
    for repeat, trace in enumerate(traces):
        (output / f'trace-{repeat}.csv').write_text(trace)
    identities = sorted(vectors)
    truth = [list(pair) for pair in itertools.combinations(identities, 2)
             if vectors[pair[0]] == vectors[pair[1]]]
    dump(output / 'finite-domain-labels.json', {'positive_pairs': truth, 'domain': protocol['domain']})
    code_weights = fit([item['body'] for item in fixtures])
    doc_weights = fit([document(item, 'complete') for item in fixtures])
    dump(output / 'weights.json', {'code': code_weights, 'doc': doc_weights})
    code = {item['id']: transform(item['body'], code_weights) for item in fixtures}
    inputs = {arm: {item['id']: document(item, arm) for item in fixtures} for arm in protocol['arms']}
    dump(output / 'document-inputs.json', inputs)
    results = []
    for repeat in range(protocol['repeats']):
        for arm in protocol['arms']:
            docs = {identity: transform(text, doc_weights) for identity, text in inputs[arm].items()}
            for method in protocol['methods']:
                ranking = rank(identities, code, docs, method)
                selected = ranking[:protocol['budget']]
                hits = sum(item['pair'] in truth for item in selected)
                results.append({'repeat': repeat, 'arm': arm, 'method': method,
                                'hits_at_3': hits, 'returned': len(selected),
                                'reference_recall_at_3': hits / len(truth) if truth else None,
                                'ranking': ranking})
    half = len(results) // 2
    assert [{key: value for key, value in row.items() if key != 'repeat'} for row in results[:half]] == [
        {key: value for key, value in row.items() if key != 'repeat'} for row in results[half:]]
    dump(output / 'results.json', results)
    dump(output / 'checks.json', {'formula_checks_per_repeat': len(fixtures) * 256,
                                  'positive_pairs': len(truth), 'repeats_equal': True,
                                  'independent_effectiveness': False})
    for row in results[:half]:
        print(row['arm'], row['method'], row['hits_at_3'], row['returned'])


if __name__ == '__main__':
    main()
