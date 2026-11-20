import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main():
    parent = ROOT / 'research/evidence/runs/2026-11-17-standard-mechanisms-01'
    run = ROOT / 'research/evidence/runs/2026-11-17-standard-mechanism-cards-01'
    run.mkdir(exist_ok=False)
    units = json.loads((parent / 'units.json').read_text())
    files = json.loads((parent / 'files.json').read_text())
    selections = [
        ('deque_conditional_pop', [('library/alloc/src/collections/vec_deque/mod.rs', name) for name in ('pop_front_if', 'pop_back_if', 'pop_front', 'pop_back')], 'admit_for_claim_preparation', 'Shared conditional-control skeleton with endpoint policy and existing delegation; mutation/false outcome is observable. No claim a helper is worthwhile.'),
        ('skip_take_iterator_state', [('library/core/src/iter/adapters/' + adapter + '.rs', name) for adapter in ('skip', 'take') for name in ('next', 'nth')], 'defer_until_state_contract', 'Different skip/take state transitions; superficially similar counters do not establish interchangeable behavior. Iterator trait context is in a rejected file.'),
        ('slice_split', [('library/core/src/slice/mod.rs', name) for name in ('split_at', 'split_at_mut', 'split_at_checked', 'split_at_mut_checked')], 'defer_ast_unavailable', 'Whole source rejected by current frontend; never silently restrict the population to successful files.'),
    ]
    cards = []
    for family, targets, status, reason in selections:
        members = []
        for path, name in targets:
            source = next(file for file in files if file['path'] == path)
            matches = [unit for unit in units if unit['path'] == path and unit['name'] == name]
            if source['status'] == 'parsed_by_syn':
                assert len(matches) == 1
            else:
                assert not matches
            members.append({'path': path, 'name': name, 'parser_status': source['status'], 'source_sha256': source['source_sha256'], 'unit': matches[0] if matches else None})
        cards.append({'family': family, 'status': status, 'reason': reason, 'members': members, 'selection_basis': 'purposeful source reading after coverage audit; not random or independent validation sampling', 'code_relation_label': 'unknown', 'merge_worthiness': 'unmeasured', 'independent_test_eligible': False})
    claims = [
        {'id': 'DQ1', 'claim': 'On an empty deque the predicate is not called and result is None', 'basis': ['original method documentation', 'original method source', '12-condition runtime witness'], 'scope': 'source/doc claim plus observed i32 fixture'},
        {'id': 'DQ2', 'claim': 'A predicate may mutate the inspected element even when it returns false; observed mutation remains', 'basis': ['mutable predicate parameter and call before branch', 'four nonempty false runtime witnesses'], 'scope': 'existential witness, not all predicate effects or panic semantics'},
        {'id': 'DQ3', 'claim': 'Returning None implies the deque elements are unchanged', 'basis': ['deliberately constructed corrupted claim'], 'status': 'refuted_by_DQ2', 'scope': 'not a claim attributed to standard-library docs'},
        {'id': 'DQ4', 'claim': 'Front and back target different endpoints; accepted mutated element is returned', 'basis': ['original endpoint-specific calls', 'nonempty true runtime witnesses'], 'scope': 'observed lengths1and3; no general equivalence or extraction label'},
    ]
    artifacts = {'cards.json': cards, 'claim-ledger.json': claims, 'inputs.json': {'parent': str(parent.relative_to(ROOT)), 'units_sha256': hashlib.sha256((parent / 'units.json').read_bytes()).hexdigest(), 'files_sha256': hashlib.sha256((parent / 'files.json').read_bytes()).hexdigest(), 'witness_report_sha256': hashlib.sha256((ROOT / 'research/evidence/runs/2026-11-17-deque-document-witness-01/report.json').read_bytes()).hexdigest()}}
    for name, value in artifacts.items():
        (run / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    (run / 'runner.py').write_bytes(Path(__file__).read_bytes())
    hashes = {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in run.iterdir()}
    (run / 'manifest.json').write_text(json.dumps(hashes, indent=2) + '\n')
    print('PASS:3 purposive family cards;8 parsed units,4 unavailable targets;4 bounded claims, no independent labels')


if __name__ == '__main__':
    main()
