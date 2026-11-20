"""Audit a 2x2 evidence budget on fixed pairs, not benchmark detector accuracy."""

import argparse
import hashlib
import itertools
import json
from pathlib import Path
import re
import shutil

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    if not args.run_id or any(not (char.isalnum() or char in '-_') for char in args.run_id):
        raise ValueError('invalid run ID')
    output = ROOT / 'research/evidence/runs' / args.run_id
    output.mkdir()
    seeds = ROOT / 'research/evidence/runs/2026-11-12-rust-seeds-01'
    cases = []
    definitions = {
        'DEV-DOC-PARAMETER-ROLE': {
            'contracts': [{'replace': 'permission_bits', 'preserve': 'file_type_bits'},
                          {'replace': 'file_type_bits', 'preserve': 'permission_bits'}],
            'common_domain': None,
            'gap': 'No frozen cross-type input correspondence between NodePermission and NodeType; separate setter tests are not pair equivalence evidence.'},
        'DEV-STREAM-COMMAND': {
            'contracts': [{'payload': 'fragment', 'callback_boundary': 'per_successful_fragment'},
                          {'payload': 'whole', 'callback_boundary': 'after_whole_collection'}],
            'common_domain': {'scenario': 'short_success', 'input_length': 4, 'payload': [0, 1, 2, 3], 'copy_plan': [2, 2]},
            'gap': 'Modeled dependencies, not kernel integration; local sharing and benefit remain unknown.'}}
    for identity, definition in definitions.items():
        folder = seeds / identity
        card = json.loads((folder / 'card.json').read_text())
        units = []
        for index, member in enumerate(card['members'], 1):
            path = folder / member['unit_file']
            assert sha(path) == member['sha256']
            assert sha(folder / member['source_file']) == member['source_sha256']
            units.append(path.read_text())
            shutil.copy2(path, output / f'{identity}-{index}.rs')
        shutil.copy2(folder / 'card.json', output / f'{identity}-card.json')
        tokens = [set(re.findall(r'[A-Za-z_][A-Za-z_0-9]*|\d+|[^\s]', unit)) for unit in units]
        cases.append({'id': identity, 'revision': card['revision'],
                      'members': [{'id': member['id'], 'name': member['name'], 'path': member['path']} for member in card['members']],
                      'token_set_jaccard': len(tokens[0] & tokens[1]) / len(tokens[0] | tokens[1]),
                      **definition})
    trace_folder = ROOT / 'research/evidence/runs/2026-11-12-stream-command-01'
    trace_report = json.loads((trace_folder / 'report.json').read_text())
    for name in ('probe.rs', 'debug-1-execute.stdout'):
        assert sha(trace_folder / name) == trace_report['artifact_sha256'][name]
        shutil.copy2(trace_folder / name, output / name)
    protocol = {'question': 'What evidence supports each scoped pair judgment when declarations and paired observations are independently omitted?',
                'arms': '2x2 contract available/absent x aligned trace available/absent; fixed two development pairs, no rank selection.',
                'code_signal': 'Regex token-set Jaccard, descriptive fixed-pair signal only; no threshold, semantic inference or claim of SourcererCC reproduction.',
                'contracts': 'Researcher-authored narrow field projections from known source, not provider approved or automatically extracted. Not full crate-contract/0 objects.',
                'judgments': 'Contract field mismatch -> declared_difference, not implementation refutation. Aligned event observations unequal -> bounded_observed_difference. No alignment -> unknown.',
                'role_boundary': 'Single-function wrong-contract failures and separate setters on unlike arguments cannot replace a frozen common input mapping.',
                'metrics': 'Per pair/arm evidence availability, difference keys, aligned witness and unknowns. No false-positive rate, accuracy, novel discovery or cost-normalized superiority.',
                'budget': 'Same two pairs; contract and trace arms deliberately receive additional information and manual preparation. Not equal total information or total labor.',
                'expected': 'Command trace establishes bounded difference with or without contracts; role trace unavailable in both requested trace arms. Both contracts show declared differences.',
                'stop': 'Eight conditions, two evaluator repeats; retain all unknowns. Next choose new sample eligibility before inspecting semantic outcomes.'}
    for name, value in [('cases.json', cases), ('protocol.json', protocol)]:
        (output / name).write_text(json.dumps(value, indent=2) + '\n')
    shutil.copy2(__file__, output / 'runner.py')
    (output / 'frozen.json').write_text(json.dumps({path.name: sha(path) for path in sorted(output.iterdir())}, indent=2) + '\n')
    raw = [json.loads(line) for line in (output / 'debug-1-execute.stdout').read_text().splitlines()]
    rows = []
    for repeat in (1, 2):
        rows = []
        for case in cases:
            for contracts_on, traces_on in itertools.product((False, True), repeat=2):
                left, right = case['contracts']
                differences = sorted(key for key in left if left[key] != right[key]) if contracts_on else []
                witness = None
                if traces_on and case['common_domain'] is not None:
                    paired = [row for row in raw if row['scenario'] == case['common_domain']['scenario']]
                    assert len(paired) == 2 and {row['adapter'] for row in paired} == {'scalar', 'command'}
                    observations = {row['adapter']: row['calls'] for row in paired}
                    assert observations['scalar'] != observations['command']
                    witness = {'domain': case['common_domain'], 'callback_events': observations,
                               'scope': 'archived exact bodies under modeled dependencies'}
                rows.append({'id': case['id'], 'contracts_requested': contracts_on, 'traces_requested': traces_on,
                             'code_signal': case['token_set_jaccard'], 'declaration_differences': differences,
                             'declaration_status': 'declared_difference' if differences else 'not_evaluated',
                             'behavior_status': 'bounded_observed_difference' if witness else 'unknown',
                             'trace_available': witness is not None, 'witness': witness,
                             'remaining_gap': case['gap'], 'local_sharing': 'unknown', 'optimization_benefit': 'unverified'})
        (output / f'result-{repeat}.json').write_text(json.dumps(rows, indent=2) + '\n')
    assert (output / 'result-1.json').read_bytes() == (output / 'result-2.json').read_bytes()
    report = {'pairs': 2, 'arms': 4, 'repeats': 2, 'new_rust_executions': 0,
              'bounded_difference_cells_per_repeat': sum(row['witness'] is not None for row in rows),
              'declared_difference_cells_per_repeat': sum(bool(row['declaration_differences']) for row in rows),
              'repeat_identical': True,
              'artifact_sha256': {path.name: sha(path) for path in sorted(output.iterdir())}}
    (output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({key: value for key, value in report.items() if key != 'artifact_sha256'}, indent=2))


if __name__ == '__main__':
    main()
