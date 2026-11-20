"""Freeze and audit common discovery inputs; no effectiveness labels or rankings."""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import shutil

ROOT = Path(__file__).resolve().parents[1]
INPUTS = {
    'units': 'research/evidence/runs/2026-11-05-rust-baseline-corpus-01/units.json',
    'tokens': 'research/evidence/runs/2026-11-05-rust-token-bags-01/report.json',
    'docs': 'research/evidence/runs/2026-11-09-source-doc-inventory-02/bindings.json',
    'doc_protocol': 'research/protocols/doc-tfidf-discovery-v1.json',
    'ledger': 'research/protocols/discovery-ledger-v4.json',
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def unique(records, key):
    result = {record[key]: record for record in records}
    if len(result) != len(records):
        raise ValueError('Duplicate identity')
    return result


def align(units, tokens, docs, pattern):
    units_by_id = unique(units, 'id')
    tokens_by_id = unique(tokens, 'unit_id')
    docs_by_id = unique(docs, 'unit_id')
    if units_by_id.keys() != tokens_by_id.keys() or units_by_id.keys() != docs_by_id.keys():
        raise ValueError('Identity sets differ')
    rows = []
    for identity, unit in sorted(units_by_id.items()):
        token = tokens_by_id[identity]
        doc = docs_by_id[identity]
        if unit['path'] != token['path'] or unit['path'] != doc['path']:
            raise ValueError('Path identity mismatch')
        if unit['package'] != doc['package'] or unit['range'] != token['range']:
            raise ValueError('Package/range identity mismatch')
        if token['status'] != 'tokenized':
            raise ValueError('Untokenized unit')
        eligible = 65 <= token['tokens'] <= 500000
        if eligible != token['size_eligible']:
            raise ValueError('Eligibility mismatch')
        doc_state = ('nonzero' if re.search(pattern, doc['doc_text'].lower()) else
                     'tokenizer_zero' if doc['doc_text'].strip() else 'missing_or_empty')
        rows.append({'unit_id': identity, 'path': unit['path'], 'package': unit['package'],
                     'start_line': unit['start_line'], 'tokens': token['tokens'],
                     'code_eligible': eligible, 'doc_state': doc_state,
                     'test_path_hint': unit['test_path_hint'], 'cfg': unit['cfg']})
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['prepare', 'execute'])
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    destination = args.output
    if args.action == 'prepare':
        destination.mkdir(parents=True, exist_ok=False)
        shutil.copyfile(__file__, destination / 'runner.py')
        protocol = {
            'question': 'Which frozen units and pairs are comparable without excluding missing docs?',
            'inputs': {key: {'path': path, 'sha256': sha(ROOT / path)} for key, path in INPUTS.items()},
            'runner_sha256': sha(Path(__file__)),
            'population': 'All matching IDs; primary comparison retains code-eligible units including zero docs.',
            'secondary': 'Both-code-eligible and nonzero-doc endpoints, explicitly conditional coverage.',
            'budget': 'Future top20 unique unordered pairs per method; ties frozen before ranking; no ranking here.',
            'label_policy': 'Existing review is development exposure, not independent truth; no effectiveness metrics.',
            'stop': 'Identity checks, partition counts, historical candidate coverage, two identical summaries.',
        }
        (destination / 'protocol.json').write_text(json.dumps(protocol, indent=2) + '\n')
        print('Prepared', destination)
        return
    protocol = json.loads((destination / 'protocol.json').read_text())
    if (destination / 'report.json').exists():
        raise ValueError('Refuse to overwrite completed run')
    if sha(Path(__file__)) != protocol['runner_sha256']:
        raise ValueError('Runner changed after freeze')
    data = {}
    for key, item in protocol['inputs'].items():
        path = ROOT / item['path']
        if sha(path) != item['sha256']:
            raise ValueError('Frozen input changed: ' + key)
        data[key] = json.loads(path.read_text())
    rows = align(data['units'], data['tokens']['records'], data['docs'],
                 data['doc_protocol']['vectorizer']['token_pattern'])
    repeated = align(data['units'], data['tokens']['records'], data['docs'],
                     data['doc_protocol']['vectorizer']['token_pattern'])
    assert rows == repeated
    by_id = {row['unit_id']: row for row in rows}
    eligible = [row for row in rows if row['code_eligible']]
    joint = [row for row in eligible if row['doc_state'] == 'nonzero']
    pair_states = Counter()
    for pair in data['ledger']['records']:
        members = [by_id[member['id']] for member in pair['members']]
        assert len(members) == 2 and all(member['code_eligible'] for member in members)
        pair_states[str(sum(member['doc_state'] == 'nonzero' for member in members))] += 1
    report = {
        'units': len(rows), 'code_eligible': len(eligible), 'joint_nonzero_units': len(joint),
        'primary_pair_universe': len(eligible) * (len(eligible) - 1) // 2,
        'conditional_nonzero_pair_universe': len(joint) * (len(joint) - 1) // 2,
        'strata': dict(sorted(Counter(f"{row['code_eligible']}:{row['doc_state']}" for row in rows).items())),
        'historical_scc_pairs_by_documented_endpoints': dict(sorted(pair_states.items())),
        'packages': dict(sorted(Counter(row['package'] for row in rows).items())),
        'cfg_states': dict(Counter(row['cfg'] for row in rows)),
        'repeat_equal': True, 'accuracy_measured': False,
        'limits': ['ID/path/range matching is not semantic doc correctness or evaluated cfg membership.',
                   'No new independent labels, ranking, fusion or document intervention executed.',
                   'Existing corpus is development-exposed; conditional subset must not replace primary denominator.'],
    }
    for name, content in [('units.json', rows), ('report.json', report)]:
        (destination / name).write_text(json.dumps(content, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
