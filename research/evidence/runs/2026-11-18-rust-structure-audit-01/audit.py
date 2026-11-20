import copy
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
INPUT = ROOT / 'research/evidence/runs/2026-11-18-rust-structure-prototype-01'
CHECKER = ROOT / 'scripts/check_rust_structure_output.py'
spec = importlib.util.spec_from_file_location('independent_checker', CHECKER)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    destination = HERE / 'results.json'
    if destination.exists():
        raise SystemExit('Refusing to overwrite an existing audit')
    sources = sorted((INPUT / 'attempt-0').glob('control-*.rs'))
    sources += sorted((INPUT / 'corpus').glob('*.rs'))
    assert len(sources) == 20
    records = []
    for source in sources:
        output = source.with_suffix('.stdout')
        try:
            result = module.check(source.read_bytes(), json.loads(output.read_text()))
            records.append({'source': str(source.relative_to(ROOT)),
                            'source_sha256': digest(source), 'output_sha256': digest(output),
                            'check_passed': True, 'result': result})
        except Exception as error:
            records.append({'source': str(source.relative_to(ROOT)),
                            'check_passed': False, 'error': repr(error)})
    original = json.loads(sources[0].with_suffix('.stdout').read_text())
    mutations = {}
    changed = copy.deepcopy(original)
    changed['nodes'][0]['source_text'] += 'corruption'
    mutations['wrong_source_slice'] = changed
    changed = copy.deepcopy(original)
    parent = next(node for node in changed['nodes'] if node['ordered_children'])
    parent['ordered_children'].append(parent['ordered_children'][0])
    mutations['duplicate_child'] = changed
    changed = copy.deepcopy(original)
    occurrence = next(entry for entry in changed['occurrences'] if entry['binder_candidate'] is not None)
    occurrence['binder_candidate'] = 999999
    mutations['missing_binder'] = changed
    changed = copy.deepcopy(original)
    changed['coverage']['complete_supported'] = not changed['coverage']['complete_supported']
    mutations['false_body_coverage'] = changed
    changed = copy.deepcopy(original)
    occurrence = next(entry for entry in changed['occurrences'] if entry['binder_candidate'] is not None)
    occurrence['candidate_status'] = 'unknown_scope'
    mutations['unknown_scope_claims_candidate'] = changed
    negatives = []
    for name, payload in mutations.items():
        (HERE / f'{name}.json').write_text(json.dumps(payload, indent=2) + '\n')
        try:
            module.check(sources[0].read_bytes(), payload)
            negatives.append({'name': name, 'rejected': False})
        except (AssertionError, KeyError) as error:
            negatives.append({'name': name, 'rejected': True, 'error': repr(error)})
    report = {'checker_sha256': digest(CHECKER), 'audit_sha256': digest(Path(__file__)),
              'outputs': records, 'negative_controls': negatives,
              'semantic_binding_proven': False,
              'limitations': 'Integrity audit, not full Rust binding or retrieval quality oracle.'}
    destination.write_text(json.dumps(report, indent=2) + '\n')
    (HERE / 'checker.py.snapshot').write_bytes(CHECKER.read_bytes())
    assert all(record['check_passed'] for record in records)
    assert all(record['rejected'] for record in negatives)
    print(f'{len(records)} original outputs checked; {len(negatives)} corruptions rejected')


if __name__ == '__main__':
    main()
