"""Build development document interventions; never assign correctness labels."""

import argparse
import copy
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def render(fields):
    return '\n\n'.join(f'## {name}\n{field["text"]}' for name, field in fields.items()) + '\n'


def validate(packet, required):
    if packet['provider'] != 'researcher' or packet['review_status'] != 'provider_validation_unavailable':
        raise ValueError('unsupported provider status')
    if packet['evaluation_eligible'] or packet['split'] != 'development':
        raise ValueError('not independent evaluation input')
    arms = packet['arms']
    base = arms['D2_candidate']['fields']
    if set(base) != set(required) or any(not field['text'].strip() for field in base.values()):
        raise ValueError('missing field or empty heading')
    if arms['D0']['text'] != '' or arms['D1']['text'] != packet['native_text']:
        raise ValueError('native/no-document corruption')
    for arm, target in [('D3', packet['corruption_field']), ('paraphrase', packet['paraphrase_field'])]:
        changed = [name for name in base if base[name] != arms[arm]['fields'][name]]
        if changed != [target]:
            raise ValueError('intervention changes unexpected fields')
    for name in required:
        ablated = arms['without_' + name]['fields']
        if ablated != {key: value for key, value in base.items() if key != name}:
            raise ValueError('ablation is not single-field removal')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--repo', default='/root/codes/x-kernel')
    args = parser.parse_args()
    assert args.run_id and all(character.isalnum() or character in '-_' for character in args.run_id)
    output = ROOT / 'research/evidence/runs' / args.run_id
    output.mkdir()
    plan_path = ROOT / 'research/protocols/governed-doc-packets-v1.json'
    plan = json.loads(plan_path.read_text())
    contract_path = ROOT / plan['parent']
    contract = json.loads(contract_path.read_text())
    shutil.copy2(plan_path, output / 'protocol.json')
    shutil.copy2(__file__, output / 'builder.py')
    manifest = {'inputs': {str(path.relative_to(ROOT)): sha(path.read_bytes()) for path in [plan_path, contract_path, Path(__file__)]}}
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    packets = []
    for spec in plan['packets']:
        folder = output / spec['id']
        folder.mkdir()
        if 'seed' in spec:
            card_path = ROOT / 'research/evidence/runs/2026-11-12-rust-seeds-01' / spec['seed'] / 'card.json'
            card = json.loads(card_path.read_text())
            member = card['members'][spec['member_index']]
            source = (card_path.parent / member['source_file']).read_bytes()
            assert sha(source) == member['source_sha256']
            native = member['doc_text']
            revision = card['revision']
            entity = {'path': member['path'], 'name': member['name'], 'lines': [member['start_line'], member['end_line']]}
            shutil.copy2(card_path, folder / 'source-card.json')
            native_kind = 'direct_literal_rustdoc'
        else:
            revision = spec['revision']
            source = subprocess.check_output(['git', '-C', args.repo, 'show', revision + ':' + spec['native_path']])
            native = source.decode()
            entity = {'path': spec['native_path'], 'name': spec['entity']}
            native_kind = spec['native_kind']
        (folder / 'source.txt').write_bytes(source)
        fields = {name: {'status': 'unknown' if text is None else 'content',
                         'text': text if text is not None else 'Unknown: resolved build configuration not collected.',
                         'assertion_kind': spec['assertion_kind']} for name, text in spec['fields'].items()}
        arms = {'D0': {'text': ''}, 'D1': {'text': native}, 'D2_candidate': {'fields': fields}}
        for arm, target, replacement in [('D3', spec['corruption_field'], spec['corruption']),
                                         ('paraphrase', spec['paraphrase_field'], spec['paraphrase'])]:
            altered = copy.deepcopy(fields)
            altered[target]['text'] = replacement
            arms[arm] = {'fields': altered}
        for name in fields:
            arms['without_' + name] = {'fields': {key: value for key, value in fields.items() if key != name}}
        packet = {'id': spec['id'], 'task': spec['task'], 'level': spec['level'], 'source_revision': revision,
                  'entity_identity': entity, 'native_kind': native_kind, 'source_sha256': sha(source),
                  'provider': plan['provider'], 'review_status': plan['review_status'],
                  'author_exposure': plan['author_exposure'], 'evaluation_eligible': False,
                  'split': 'development', 'native_text': native, 'arms': arms,
                  'corruption_field': spec['corruption_field'], 'paraphrase_field': spec['paraphrase_field']}
        validate(packet, contract['levels'][spec['level']])
        for name, arm in arms.items():
            text = render(arm['fields']) if 'fields' in arm else arm['text']
            (folder / (name + '.txt')).write_text(text)
        (folder / 'packet.json').write_text(json.dumps(packet, indent=2) + '\n')
        packets.append(packet)
    rejected = []
    controls = {
        'provider_promotion': lambda packet: packet.update(provider='maintainer'),
        'test_promotion': lambda packet: packet.update(split='test'),
        'evaluation_promotion': lambda packet: packet.update(evaluation_eligible=True),
        'native_rewrite': lambda packet: packet['arms']['D1'].update(text='replacement'),
        'extra_corruption': lambda packet: packet['arms']['D3']['fields']['purpose'].update(text='unrelated'),
        'empty_heading': lambda packet: packet['arms']['D2_candidate']['fields']['purpose'].update(text=''),
    }
    for name, mutate in controls.items():
        packet = copy.deepcopy(packets[0])
        mutate(packet)
        try:
            validate(packet, contract['levels']['item'])
        except ValueError:
            rejected.append(name)
        else:
            raise AssertionError(name)
    report = {'packets': len(packets), 'variants': sum(len(packet['arms']) for packet in packets),
              'provider_validated': 0, 'evaluation_eligible': 0, 'detector_runs': 0,
              'rejected_controls': rejected,
              'unknown_fields': {packet['id']: [name for name, field in packet['arms']['D2_candidate']['fields'].items() if field['status'] == 'unknown'] for packet in packets},
              'scope': 'Input construction only; field presence and isolated edits do not prove truth or paraphrase equivalence',
              'artifact_sha256': {str(path.relative_to(output)): sha(path.read_bytes()) for path in sorted(output.rglob('*')) if path.is_file()}}
    (output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({key: value for key, value in report.items() if key != 'artifact_sha256'}, indent=2))


if __name__ == '__main__':
    main()
