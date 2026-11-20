import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', required=True)
    parser.add_argument('--removal-run', required=True)
    args = parser.parse_args()
    queue_run = ROOT / 'research/evidence/runs/2026-11-16-common-budget-01'
    path_run = ROOT / 'research/evidence/runs/2026-11-17-path-module-01'
    removal_run = ROOT / 'research/evidence/runs' / args.removal_run
    inputs = [queue_run / 'review-queue.json', path_run / 'report.json', removal_run / 'checked-results.json']
    queue = json.loads(inputs[0].read_text())
    path_report = json.loads(inputs[1].read_text())
    removal_report = json.loads(inputs[2].read_text())
    assert len(queue) == 40
    assert path_report['stable'] and len(path_report['outcomes']) == 4
    assert all(entry['passed_tests'] == 7 and entry['cases'] == 37459 for entry in path_report['outcomes'])
    assert removal_report['consistent_test_identities']
    rankings = {}
    for method in ['code', 'documentation', 'fusion']:
        path = queue_run / (method + '-top100.json')
        inputs.append(path)
        rankings[method] = {tuple(sorted(row[1:])): {'rank': index + 1, 'score': row[0]} for index, row in enumerate(json.loads(path.read_text()))}
    rows = []
    for index, candidate in enumerate(queue):
        key = tuple(sorted(candidate['unit_ids']))
        ranks = {method: ranked.get(key) for method, ranked in rankings.items()}
        methods = [method for method, entry in ranks.items() if entry is not None and entry['rank'] <= 20]
        assert methods == candidate['methods']
        row = {'queue_index': index, 'unit_ids': candidate['unit_ids'], 'members': [{'name': member['name'], 'path': member['path'], 'start_line': member['start_line']} for member in candidate['members']], 'top20_methods': methods, 'ranks_within_archived_top100': ranks, 'status': 'not_implemented_in_this_followup', 'benefit': 'unknown', 'test_path_hint': any(member['test_path_hint'] for member in candidate['members'])}
        if index == 27:
            assert {member['name'] for member in candidate['members']} == {'parent', 'file_name'}
            row.update({'status': 'isolated_module_extraction_finite_domain_compatible', 'evidence': str(path_run.relative_to(ROOT)), 'public_api_changes': 0, 'formatted_line_delta': -13})
        if index == 7:
            assert {member['name'] for member in candidate['members']} == {'unlink_with_pathname_tracked', 'rmdir_tracked'}
            row.update({'status': 'isolated_kernel_extraction_passes_targeted_observations', 'evidence': str(removal_run.relative_to(ROOT)), 'control': 'old_tests_miss_no_fallback_mutant_new_tests_detect_two_cases'})
        if index in (7, 27):
            row['posthoc_budget_membership'] = {str(budget): [method for method, entry in ranks.items() if entry is not None and entry['rank'] <= budget] for budget in (10, 20, 50, 100)}
        rows.append(row)
    displaced = [row['queue_index'] for row in rows if 'code' in row['top20_methods'] and 'fusion' not in row['top20_methods']]
    run = ROOT / 'research/evidence/runs' / args.run
    run.mkdir(exist_ok=False)
    report = {'input_sha256': {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in inputs}, 'queue_size': len(rows), 'implemented_development_cases': [7, 27], 'code_top20_not_in_fusion_top20': displaced, 'remaining_implementation_outcomes': 'unknown, not negative', 'limits': ['Post-hoc source-reviewed case selection, not random or independent evaluation', 'No method success rate, precision, recall or net benefit estimated', 'Rank absent means not in archived top100, not universally undetectable', 'Fixed budget membership, not causal attribution to documentation alone'], 'rows': rows}
    (run / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    (run / 'runner.py').write_bytes(Path(__file__).read_bytes())
    print(json.dumps({key: value for key, value in report.items() if key != 'rows'}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
