"""Audit existing representation inputs without asserting semantic equivalence."""

import argparse
import copy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil

from check_crate_contract import validate

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    protocol_path = ROOT / 'research/protocols/equal-information-admission-v1.json'
    plan = json.loads(protocol_path.read_text())
    paths = {key: ROOT / value for key, value in plan['sources'].items()}
    for path in paths.values():
        report = json.loads((path.parent / 'report.json').read_text())
        assert sha(path) == report['artifact_sha256'][path.name]
    claims = {claim['id']: claim for claim in json.loads(paths['claims'].read_text())}
    contracts = {case['id']: case['contract'] for case in json.loads(paths['contracts'].read_text())}
    registry = json.loads(paths['registry'].read_text())
    args.output.mkdir(parents=True, exist_ok=False)
    shutil.copy2(protocol_path, args.output / 'protocol.json')
    shutil.copy2(__file__, args.output / 'runner.py')
    dump(args.output / 'freeze.json', {'sources': {key: sha(path) for key, path in paths.items()},
         'protocol': sha(protocol_path), 'runner': sha(Path(__file__)),
         'existing_validator': sha(ROOT / 'scripts/check_crate_contract.py')})
    records = []
    for specification in plan['records']:
        claim = claims[specification['claim']]
        text = claim['text']
        spans = []
        for clause in specification['clauses']:
            assert text.count(clause['text']) == 1
            start = text.index(clause['text'])
            spans.append({**clause, 'character_range': [start, start + len(clause['text'])]})
        contract = contracts[specification['contract']] if specification['contract'] else None
        schema_results = []
        if contract:
            for repeat in range(2):
                validate(contract, registry, ROOT)
                schema_results.append('accepted')
        records.append({**specification, 'claim_text': text, 'kind': claim['kind'],
            'revision': claim['revision'], 'contract': contract, 'clause_alignment': spans,
            'schema_checks': schema_results, 'semantic_equivalence': 'not_established',
            'mapping_origin': 'analyst', 'human_authoring_minutes': None})
    altered = copy.deepcopy(contracts['role'])
    altered['limitations'] = ['No guarantee of a valid NodeType']
    try:
        validate(altered, registry, ROOT)
    except ValueError as error:
        rejection = str(error)
    else:
        raise AssertionError('v0 unexpectedly accepts unmapped field')
    dump(args.output / 'alignment.json', records)
    dump(args.output / 'schema-control.json', {'contract': altered, 'rejected': True, 'reason': rejection})
    ended = datetime.now(timezone.utc)
    started = datetime.strptime(plan['started_utc'], '%Y-%m-%d %H:%M:%S UTC').replace(tzinfo=timezone.utc)
    dump(args.output / 'cost.json', {'agent_batch_started_utc': plan['started_utc'],
         'execution_completed_utc': ended.isoformat(), 'elapsed_seconds': (ended - started).total_seconds(),
         'meaning': 'agent wall interval through audit execution, includes reading and tool waiting; excludes later review/documentation; not human cost',
         'human_minutes': None, 'records_manually_aligned': 3, 'clauses_manually_aligned': 7,
         'counterparts_reused': 2, 'new_counterparts_created': 0})
    report = {'records': len(records), 'schema_acceptances': 4, 'schema_rejections': 1,
              'semantic_equivalence_established': 0, 'detector_runs': 0,
              'artifact_sha256': {path.name: sha(path) for path in args.output.iterdir() if path.is_file()}}
    dump(args.output / 'report.json', report)
    print(json.dumps({key: value for key, value in report.items() if key != 'artifact_sha256'}))


if __name__ == '__main__':
    main()
