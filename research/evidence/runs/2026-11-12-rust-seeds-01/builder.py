"""Package existing Rust seed evidence with byte-checked source and explicit unknown labels."""

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import zipfile

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / 'research/evidence/runs'


def digest(content):
    return hashlib.sha256(content).hexdigest()


def load(path):
    return json.loads(path.read_text())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    assert args.run_id and all(character.isalnum() or character in '-_' for character in args.run_id)
    output = RUNS / args.run_id
    output.mkdir()
    protocol_path = ROOT / 'research/protocols/rust-development-seeds-v1.json'
    protocol = load(protocol_path)
    corpus = RUNS / '2026-11-05-rust-baseline-corpus-01'
    report = load(corpus / 'report.json')
    assert report['revision'] == protocol['revision']
    for name in ('units.json', 'units.zip', 'sources.zip'):
        assert digest((corpus / name).read_bytes()) == report['artifacts_sha256'][name]
    units = {unit['id']: unit for unit in load(corpus / 'units.json')}
    ledger_path = ROOT / 'research/protocols/discovery-ledger-v4.json'
    ledger = load(ledger_path)
    queue_path = RUNS / '2026-11-09-doc-tfidf-01/review-queue.json'
    queue_report = load(queue_path.parent / 'report.json')
    assert digest(queue_path.read_bytes()) == queue_report['artifact_sha256']['review-queue.json']
    queue = {pair['rank']: pair for pair in load(queue_path)}
    bindings_path = RUNS / '2026-11-09-source-doc-inventory-02/bindings.json'
    doc_protocol = load(ROOT / 'research/protocols/doc-tfidf-discovery-v1.json')
    assert digest(bindings_path.read_bytes()) == doc_protocol['input_sha256']
    docs = {item['unit_id']: item for item in load(bindings_path)}
    alignment = RUNS / '2026-11-12-evaluation-alignment-replay-01'
    alignment_report = load(alignment / 'report.json')
    assert alignment_report['passed'] and alignment_report['revision'] == protocol['revision']
    for name, checksum in alignment_report['artifacts_sha256'].items():
        assert digest((alignment / name).read_bytes()) == checksum
    inputs = [protocol_path, ledger_path, queue_path, bindings_path, corpus / 'report.json', alignment / 'report.json', Path(__file__)]
    manifest = {'scope': protocol['selection'], 'input_sha256': {str(path.relative_to(ROOT)): digest(path.read_bytes()) for path in inputs}}
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    shutil.copy2(protocol_path, output / 'selection.json')
    shutil.copy2(__file__, output / 'builder.py')
    cards = []
    with zipfile.ZipFile(corpus / 'sources.zip') as sources, zipfile.ZipFile(corpus / 'units.zip') as snippets:
        for seed in protocol['seeds']:
            directory = output / seed['id']
            directory.mkdir()
            members = []
            selector = seed['selector']
            identities = []
            if 'scc_pair' in selector:
                matching = [record for record in ledger['records'] if sorted(record['file_ids']) == sorted(selector['scc_pair'])]
                assert len(matching) == 1 and matching[0]['family'] == seed['family']
                identities = [member['id'] for member in matching[0]['members']]
            elif 'doc_rank' in selector:
                identities = queue[selector['doc_rank']]['unit_ids']
            for identity in identities:
                unit = units[identity]
                source = sources.read(unit['path'])
                snippet = snippets.read(unit['entry'])
                assert digest(source) == unit['source_sha256'] and digest(snippet) == unit['sha256']
                start, end = unit['range']
                assert source[start:end] == snippet
                stem = str(len(members) + 1)
                (directory / (stem + '-source.rs')).write_bytes(source)
                (directory / (stem + '-unit.rs')).write_bytes(snippet)
                member = {key: unit[key] for key in ('id', 'path', 'name', 'start_line', 'end_line', 'range', 'sha256', 'source_sha256', 'attributes', 'ancestor_attributes', 'file_attributes', 'cfg')}
                member.update(source_file=stem + '-source.rs', unit_file=stem + '-unit.rs',
                              doc_text=docs[identity]['doc_text'], doc_scope='direct literal docs, truth not verified')
                members.append(member)
            if selector.get('alignment'):
                for name, source_record in alignment_report['sources'].items():
                    source = (alignment / (name + '-source.rs')).read_bytes()
                    snippet = (alignment / (name + '-original.rs')).read_bytes().rstrip(b'\n')
                    assert digest(source) == source_record['sha256'] and source.count(snippet) == 1
                    start = source.index(snippet)
                    assert source[:start].count(b'\n') + 1 == source_record['start_line']
                    (directory / (name + '-source.rs')).write_bytes(source)
                    (directory / (name + '-unit.rs')).write_bytes(snippet)
                    members.append({'id': 'alignment-' + name, 'path': source_record['path'], 'name': 'align_up',
                                    'range': [start, start + len(snippet)], 'start_line': source_record['start_line'],
                                    'end_line': source[:start + len(snippet)].count(b'\n') + 1,
                                    'sha256': digest(snippet), 'source_sha256': digest(source),
                                    'source_file': name + '-source.rs', 'unit_file': name + '-unit.rs',
                                    'cfg': 'not_evaluated', 'doc_scope': 'not_extracted', 'doc_text': None})
            assert len(members) >= 2
            for evidence in seed['evidence']:
                assert (ROOT / evidence).is_file()
            card = {**seed, 'revision': protocol['revision'], 'split': 'development',
                    'origin_group': 'xkernel-' + protocol['revision'],
                    'relation_label': 'unknown', 'reuse_preconditions': seed['configuration_scope'],
                    'optimization_benefit': 'unverified', 'independent_adjudication': 'not_available',
                    'members': members, 'evidence_sha256': {name: digest((ROOT / name).read_bytes()) for name in seed['evidence']}}
            (directory / 'card.json').write_text(json.dumps(card, ensure_ascii=False, indent=2) + '\n')
            cards.append({'id': seed['id'], 'family': seed['family'], 'members': len(members), 'card': seed['id'] + '/card.json'})
    report = {'seed_cards': cards, 'count': len(cards), 'source_members': sum(card['members'] for card in cards),
              'scope': 'retrospective development packaging, no new detector run or labels',
              'artifact_sha256': {str(path.relative_to(output)): digest(path.read_bytes()) for path in output.rglob('*') if path.is_file()}}
    (output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'cards': len(cards), 'source_members': report['source_members'], 'output': str(output)}))


if __name__ == '__main__':
    main()
