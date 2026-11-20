"""Run frozen AST interventions through unchanged Aroma reference indexing."""

import argparse
from collections import Counter
import copy
import hashlib
import json
from pathlib import Path
import pickle
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / 'research/protocols/aroma-representation-controls-v1.json'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + '\n')


def leaves(value):
    if isinstance(value, list):
        for child in value:
            yield from leaves(child)
    elif isinstance(value, dict):
        yield value


def at_path(value, indices):
    for index in indices:
        value = value[index]
    return value


def make_condition(original, identity):
    record = copy.deepcopy(original)
    if identity.endswith('_rename'):
        names = (['buffer_local', 'cursor_local', 'source_local'] if identity == 'lowercase_rename'
                 else ['BufferLocal', 'CursorLocal', 'SourceLocal'])
        mapping = dict(zip(['strBuf', 'itr', 'list'], names))
        for leaf in leaves(record['ast']):
            if leaf.get('var'):
                leaf['token'] = mapping[leaf['token']]
    elif identity == 'receiver_reassignment':
        first = at_path(record['ast'], [3, 1, 2, 3, 1])
        second = at_path(record['ast'], [4, 3, 2, 1, 1])
        assert first['token'] == 'list' and second['token'] == 'itr'
        assert first['var'] and second['var']
        first['token'], second['token'] = second['token'], first['token']
    elif identity == 'method_spelling':
        targets = [leaf for leaf in leaves(record['ast']) if leaf['token'] == 'hasNext']
        assert len(targets) == 1 and not targets[0].get('var')
        targets[0]['token'] = 'hasRemaining'
    elif identity == 'whitespace':
        for leaf in leaves(record['ast']):
            leaf['leading'] = leaf['trailing'] = ''
    else:
        assert identity == 'original'
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists():
        raise FileExistsError(output)
    protocol = json.loads(PROTOCOL.read_text())
    source, fixture = [ROOT / protocol[key] for key in ('source', 'fixture')]
    assert sha(source) == protocol['source_sha256']
    assert sha(fixture) == protocol['fixture_sha256']
    original = json.loads(fixture.read_text())
    identities = [entry['id'] for entry in protocol['conditions']]
    records = [make_condition(original, identity) for identity in identities]
    output.mkdir(parents=True)
    (output / '.gitignore').write_text('/cache/\n')
    (output / 'runner.py').write_bytes(Path(__file__).read_bytes())
    (output / 'protocol.json').write_bytes(PROTOCOL.read_bytes())
    corpus = output / 'controls.jsonl'
    corpus.write_text(''.join(json.dumps(record, sort_keys=True) + '\n' for record in records))
    dump(output / 'conditions.json', identities)
    dump(output / 'freeze.json', {'source': sha(source), 'fixture': sha(fixture),
                                'protocol': sha(PROTOCOL), 'runner': sha(Path(__file__)),
                                'controls': sha(corpus)})
    command = [sys.executable, '-B', str(source), '-c', str(corpus), '-d', str(output / 'cache')]
    dump(output / 'command.json', {'argv': command, 'timeout_seconds': 60})
    with (output / 'stdout.log').open('w') as stdout, (output / 'stderr.log').open('w') as stderr:
        try:
            completed = subprocess.run(command, stdout=stdout, stderr=stderr, timeout=60, check=False)
            status = {'exit_code': completed.returncode, 'timeout': False}
        except subprocess.TimeoutExpired:
            status = {'exit_code': None, 'timeout': True}
    dump(output / 'status.json', status)
    if status['exit_code'] != 0:
        raise RuntimeError(status)
    with (output / 'cache/vocab.pkl').open('rb') as stream:
        vocabulary, words = pickle.load(stream)
    produced = [json.loads(line) for line in (output / 'cache/features.json').read_text().splitlines()]
    assert len(produced) == len(records) == 6
    decoded = {}
    for identity, record, actual in zip(identities, records, produced):
        assert actual['ast'] == record['ast']
        decoded[identity] = [words[index - 11] if index > 10 else '#UNK' for index in actual['features']]
    dump(output / 'features.json', decoded)
    baseline = decoded['original']
    base_tokens = Counter(leaf['token'] for leaf in leaves(original['ast']))
    base_nonvar = [leaf['token'] for leaf in leaves(original['ast']) if leaf.get('leaf') and not leaf.get('var')]
    report = {}
    for identity, record in zip(identities, records):
        values = decoded[identity]
        common = set(values) & set(baseline)
        union = set(values) | set(baseline)
        report[identity] = {
            'occurrences': len(values), 'unique': len(set(values)),
            'ordered_equal': values == baseline, 'multiset_equal': Counter(values) == Counter(baseline),
            'binary_jaccard': len(common) / len(union),
            'raw_token_bag_equal': Counter(leaf['token'] for leaf in leaves(record['ast'])) == base_tokens,
            'nonvar_leaf_sequence_equal': [leaf['token'] for leaf in leaves(record['ast'])
                                         if leaf.get('leaf') and not leaf.get('var')] == base_nonvar,
            'missing_features': dict(Counter(baseline) - Counter(values)),
            'extra_features': dict(Counter(values) - Counter(baseline)),
        }
    dump(output / 'report.json', report)
    dump(output / 'cache-hashes.json', {path.name: sha(path) for path in (output / 'cache').iterdir()})
    assert sha(source) == protocol['source_sha256'] and sha(PROTOCOL) == sha(output / 'protocol.json')
    print(json.dumps({identity: {key: value for key, value in row.items()
                                if key not in ('missing_features', 'extra_features')}
                      for identity, row in report.items()}, indent=2))


if __name__ == '__main__':
    main()
