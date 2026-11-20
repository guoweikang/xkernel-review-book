"""Bounded symbolic checks and explicit simulated extraction errors."""

import argparse
import copy
import itertools
import json
import re
import shutil

from run_rust_contract_logic import ROOT, evaluate, sha


def validate_formula(formula, symbols):
    if isinstance(formula, str):
        if formula not in symbols:
            raise ValueError('unknown symbol')
        return
    if not isinstance(formula, list) or not formula or not isinstance(formula[0], str):
        raise ValueError('malformed formula')
    arity = {'not': 1, 'and': 2, 'implies': 2}
    if formula[0] not in arity or len(formula) != arity[formula[0]] + 1:
        raise ValueError('unsupported operator or arity')
    for child in formula[1:]:
        validate_formula(child, symbols)


def classify(symbols, premise, hypothesis):
    if premise is None or hypothesis is None:
        return {'label': 'abstain', 'reason': 'missing_representation'}
    if not 1 <= len(symbols) <= 8 or len(set(symbols)) != len(symbols):
        raise ValueError('unsupported variable count')
    validate_formula(premise, symbols)
    validate_formula(hypothesis, symbols)
    worlds = [dict(zip(symbols, values)) for values in itertools.product([False, True], repeat=len(symbols))]
    admissible = [world for world in worlds if evaluate(premise, world)]
    if not admissible:
        return {'label': 'abstain', 'reason': 'inconsistent_premise'}
    positive = [world for world in admissible if evaluate(hypothesis, world)]
    negative = [world for world in admissible if not evaluate(hypothesis, world)]
    return {'label': 'entailment' if not negative else 'contradiction' if not positive else 'neutral',
            'supporting_worlds': positive, 'counterexamples': negative}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    if not re.fullmatch('[A-Za-z0-9_-]+', args.run_id):
        raise ValueError('invalid run ID')
    output = ROOT / 'research/evidence/runs' / args.run_id
    output.mkdir()
    protocol = ROOT / 'research/protocols/contract-extraction-boundary-v1.json'
    plan = json.loads(protocol.read_text())
    parent = ROOT / plan['parent']
    for name, digest in json.loads((parent / 'report.json').read_text())['artifact_sha256'].items():
        if sha(parent / name) != digest:
            raise ValueError('parent changed')
    original = json.loads((parent / 'protocol.json').read_text())
    references = {row['id']: row['label'] for row in json.loads((parent / 'reference.json').read_text())}
    records = []
    for intervention in plan['interventions']:
        family = next(row for row in original['families'] if row['id'] == intervention['family'])
        for hypothesis in family['hypotheses']:
            identity = family['id'] + '/' + hypothesis['id']
            baseline = classify(sorted(family['variables']), family['formula'], hypothesis['formula'])
            if baseline['label'] != references[identity]:
                raise ValueError('baseline differs')
            altered = classify(sorted(family['variables']), intervention['replacement'], hypothesis['formula'])
            missing = classify(sorted(family['variables']), None, hypothesis['formula'])
            records.append({'id': identity, 'injection': intervention['id'], 'original': baseline,
                            'injected': altered, 'missing': missing, 'changed_label': baseline['label'] != altered['label']})
    rejected = []
    for name, formula in [('unknown_symbol', 'Z'), ('arity', ['not','A','A']), ('operator',['or','A','A']), ('empty', [])]:
        try:
            classify(['A'], formula, 'A')
        except ValueError:
            rejected.append(name)
        else:
            raise AssertionError(name)
    inconsistent = classify(['A'], ['and','A',['not','A']], 'A')
    if inconsistent != {'label':'abstain', 'reason':'inconsistent_premise'}:
        raise AssertionError('vacuous inference')
    shutil.copy2(protocol, output / 'protocol.json')
    shutil.copy2(__file__, output / 'runner.py')
    shutil.copy2(ROOT / 'scripts/run_rust_contract_logic.py', output / 'logic-source.py')
    (output / 'cases.json').write_text(json.dumps(records, indent=2) + '\n')
    (output / 'manifest.json').write_text(json.dumps({str(path.relative_to(ROOT)):sha(path) for path in (protocol, parent / 'report.json')}, indent=2) + '\n')
    report = {'scope':plan['scope'], 'baseline_consistent':len(records),
              'changed_labels':sum(row['changed_label'] for row in records),
              'changes_by_injection': {item['id']:sum(row['changed_label'] for row in records if row['injection']==item['id']) for item in plan['interventions']},
              'missing_abstentions':sum(row['missing']['label']=='abstain' for row in records),
              'rejected_controls':rejected, 'inconsistent_control':inconsistent,
              'automatic_extractions':0, 'model_inferences':0,
              'artifact_sha256':{path.name:sha(path) for path in sorted(output.iterdir()) if path.is_file()}}
    (output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({key:value for key,value in report.items() if key!='artifact_sha256'},indent=2))


if __name__ == '__main__':
    main()
