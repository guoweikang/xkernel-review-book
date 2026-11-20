"""Frozen structural ablations; not a general semantic or implementation verifier."""

import argparse
import hashlib
import json
from pathlib import Path
import shutil

from check_hanlp_srl_smoke import check_batches

ARMS = ('flat', 'containment_only', 'modifier_only', 'both', 'any_multiframe', 'all_abstain')
BLOCK_MODIFIERS = {'ARGM-ADV', 'ARGM-MOD', 'ARGM-CND'}


def decide(frames, query_forms, arm):
    if arm not in ARMS:
        raise ValueError('unknown arm')
    query = {value.casefold() for value in query_forms}
    targets = [(index, frame, role) for index, frame in enumerate(frames) for role in frame if role[1] == 'PRED' and role[0].casefold() in query]
    if len(targets) != 1:
        return {'prediction': None, 'reason': 'no_target' if not targets else 'ambiguous_target'}
    index, frame, predicate = targets[0]
    contained = any(role[1] != 'PRED' and role[2] <= predicate[2] and predicate[3] <= role[3]
                    for other_index, other in enumerate(frames) if other_index != index for role in other)
    modified = any(role[1] in BLOCK_MODIFIERS for role in frame)
    blocked = arm == 'all_abstain' or (arm == 'any_multiframe' and len(frames) > 1)
    blocked |= arm in {'containment_only', 'both'} and contained
    blocked |= arm in {'modifier_only', 'both'} and modified
    return {'prediction': None if blocked else 'negative' if any(role[1] == 'ARGM-NEG' for role in frame) else 'positive',
            'reason': 'gated' if blocked else 'flat_frame', 'contained': contained, 'modified': modified, 'target_frame': index}


def score(rows):
    total = len(rows)
    answered = sum(row['prediction'] is not None for row in rows)
    correct = sum(row['prediction'] is not None and row['prediction'] == row['gold'] for row in rows)
    return {'total': total, 'answered': answered, 'correct': correct, 'wrong': answered-correct,
            'coverage': answered/total if total else None,
            'selective_accuracy': correct/answered if answered else None,
            'unconditional_accuracy': correct/total if total else None,
            'promotion': sum(row['gold'] == 'unknown' and row['prediction'] == 'positive' for row in rows),
            'unknown_total': sum(row['gold'] == 'unknown' for row in rows),
            'lost_positives': sum(row['gold'] == 'positive' and row['prediction'] is None for row in rows),
            'positive_total': sum(row['gold'] == 'positive' for row in rows),
            'no_target': sum(row['reason'] == 'no_target' for row in rows),
            'ambiguous_target': sum(row['reason'] == 'ambiguous_target' for row in rows)}


def controls():
    action = [['worker', 'ARG0', 0, 1], ['opens', 'PRED', 2, 3], ['port', 'ARG1', 3, 4]]
    parent = [['requires', 'PRED', 1, 2], ['worker opens port', 'ARG1', 0, 4]]
    assert decide([action], ['opens'], 'both')['prediction'] == 'positive'
    assert decide([parent, action], ['opens'], 'flat')['prediction'] == 'positive'
    assert decide([action, parent], ['opens'], 'containment_only')['prediction'] is None
    nonparent = [['reports', 'PRED', 6, 7], ['message', 'ARG1', 7, 8]]
    assert decide([action, nonparent], ['opens'], 'containment_only')['prediction'] == 'positive'
    assert decide([action, nonparent], ['opens'], 'any_multiframe')['prediction'] is None
    modified = action + [['carefully', 'ARGM-ADV', 4, 5]]
    assert decide([modified], ['opens'], 'modifier_only')['prediction'] is None
    negative = action + [['not', 'ARGM-NEG', 1, 2]]
    assert decide([negative], ['opens'], 'flat')['prediction'] == 'negative'
    assert decide([], ['opens'], 'flat')['reason'] == 'no_target'
    assert decide([action, action], ['opens'], 'both')['reason'] == 'ambiguous_target'
    assert score([{'prediction': None, 'gold': 'unknown', 'reason': 'gated'}])['selective_accuracy'] is None
    assert score([{'prediction': 'negative', 'gold': 'unknown', 'reason': 'flat_frame'}])['wrong'] == 1
    return 11


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('smoke', type=Path)
    parser.add_argument('cases', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    args.output.mkdir()
    protocol = Path(__file__).resolve().parents[1] / 'research/protocols/srl-scope-ablation-v1.json'
    for source, name in ((protocol, 'protocol.json'), (Path(__file__), 'evaluator.py'), (args.cases, 'cases.json')):
        shutil.copy2(source, args.output / name)
    cases = json.loads(args.cases.read_text())
    identities = [row['id'] for row in cases]
    if len(set(identities)) != len(cases) or any(row['gold'] not in {'positive', 'negative', 'unknown'} for row in cases):
        raise ValueError('invalid cases')
    inputs = json.loads((args.smoke / 'inputs.json').read_text())
    if inputs != [{'id': row['id'], 'text': row['text']} for row in cases]:
        raise ValueError('different inference input')
    report = json.loads((args.smoke / 'report.json').read_text())
    if not report['success']:
        raise ValueError('incomplete inference')
    for repeat in (1, 2):
        raw_path = args.smoke / f'raw-{repeat}.json'
        digest = hashlib.sha256(raw_path.read_bytes()).hexdigest()
        if digest != report['artifact_sha256'][raw_path.name]:
            raise ValueError('changed raw output')
        batches = json.loads(raw_path.read_text())
        check_batches(batches, identities)
        frames = {identity: value for batch in batches for identity, value in zip(batch['ids'], batch['output']['srl'], strict=True)}
        rows = {arm: [dict(id=case['id'], family=case['family'], gold=case['gold'], **decide(frames[case['id']], case['query_forms'], arm)) for case in cases] for arm in ARMS}
        comparisons = {}
        for arm in ARMS[1:]:
            withheld = []
            for base, variant in zip(rows['flat'], rows[arm], strict=True):
                if variant['prediction'] is not None and variant['prediction'] != base['prediction']:
                    raise ValueError('gate introduced new answer')
                if base['prediction'] is not None and variant['prediction'] is None:
                    withheld.append(base)
            comparisons[arm] = {'withheld': len(withheld), 'withheld_correct': sum(row['prediction'] == row['gold'] for row in withheld), 'withheld_wrong': sum(row['prediction'] != row['gold'] for row in withheld)}
        result = {'raw_sha256': digest, 'rows': rows, 'metrics': {arm: score(values) for arm, values in rows.items()},
                  'families': {arm: {family: score([row for row in values if row['family'] == family]) for family in sorted({row['family'] for row in cases})} for arm, values in rows.items()},
                  'comparisons_to_flat': comparisons, 'synthetic_checks': controls()}
        (args.output / f'result-{repeat}.json').write_text(json.dumps(result, indent=2)+'\n')
    identical = (args.output / 'result-1.json').read_bytes() == (args.output / 'result-2.json').read_bytes()
    summary = {'repeat_identical': identical, 'metrics': result['metrics'], 'comparisons': result['comparisons_to_flat'],
               'artifact_sha256': {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(args.output.iterdir()) if path.is_file()}}
    (args.output / 'report.json').write_text(json.dumps(summary, indent=2)+'\n')
    print(json.dumps(summary['metrics'], indent=2))


if __name__ == '__main__':
    main()
