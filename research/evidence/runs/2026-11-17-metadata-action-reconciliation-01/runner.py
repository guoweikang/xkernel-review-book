import hashlib
import json
from pathlib import Path
import subprocess
import sys

from check_metadata_pair import check

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_artifacts(directory, key):
    report = json.loads((directory / 'report.json').read_text())
    for name, expected in report[key].items():
        assert sha(directory / name) == expected, name
    return report


def main():
    run = ROOT / 'research/evidence/runs/2026-11-17-metadata-action-reconciliation-01'
    run.mkdir(exist_ok=False)
    queue_path = ROOT / 'research/evidence/runs/2026-11-16-common-budget-01/review-queue.json'
    queue = json.loads(queue_path.read_text())
    candidates_path = ROOT / 'research/evidence/runs/2026-11-05-rust-scc-01/candidates.json'
    source_report = json.loads((candidates_path.parent / 'report.json').read_text())
    assert sha(candidates_path) == source_report['artifacts_sha256']['candidates.json']
    historical = next(pair for pair in json.loads(candidates_path.read_text()) if pair['file_ids'] == [1571, 1732])
    assert set(queue[11]['unit_ids']) == {member['id'] for member in historical['members']}
    for member in historical['members']:
        current = next(item for item in queue[11]['members'] if item['id'] == member['id'])
        for key in ('id', 'sha256', 'source_sha256', 'path', 'start_line', 'end_line'):
            assert current[key] == member[key], key
    paired = ROOT / 'research/evidence/runs/2026-11-05-metadata-pair-01'
    paired_checks = check(paired)
    assert paired_checks['passed'] and paired_checks['tests_each'] == 94
    self_check = subprocess.run([sys.executable, str(ROOT / 'scripts/check_metadata_pair.py'), str(paired), '--self-check'], capture_output=True)
    (run / 'historical-checker.log').write_bytes(self_check.stdout + self_check.stderr)
    self_check.check_returncode()
    patch = ROOT / 'research/evidence/runs/2026-11-05-metadata-fixture-patch-02'
    patch_report = verify_artifacts(patch, 'artifacts_sha256')
    pair_report = json.loads((paired / 'report.json').read_text())
    assert (paired / 'candidate.patch').read_bytes() == (patch / 'candidate.patch').read_bytes()
    production = ROOT / 'research/evidence/runs/2026-11-05-metadata-production-01'
    production_report = verify_artifacts(production, 'artifact_sha256')
    assert production_report['passed'] and production_report['exit_code'] == 0
    assert production_report['depfiles_exclude_ut_tests']
    assert 'unittest' not in production_report['kvfs_cfg_flags']
    assert all('ut-tests/' not in path.read_text() for path in production.glob('*.d'))
    bindings_path = ROOT / 'research/evidence/runs/2026-11-09-source-doc-inventory-02/bindings.json'
    bindings = {row['unit_id']: row['doc_text'] for row in json.loads(bindings_path.read_text())}
    doc_lengths = {identity: len(bindings[identity]) for identity in queue[11]['unit_ids']}
    report = {'queue_index': 11, 'historical_file_ids': [1571, 1732], 'identity_and_source_hashes_match': True, 'unit_ids': queue[11]['unit_ids'], 'top20_methods': queue[11]['methods'], 'native_document_character_lengths': doc_lengths, 'historical_paired_check': paired_checks, 'historical_production_report_verified': True, 'revision': pair_report['revision'], 'patch_revision': patch_report['revision'], 'production_revision': production_report['revision'], 'current_kernel_execution': False, 'disposition': 'historical_feasible_extraction_net_benefit_unverified_not_recommended_standalone_PR', 'input_sha256': {str(path.relative_to(ROOT)): sha(path) for path in [queue_path, candidates_path, bindings_path, paired / 'report.json', patch / 'report.json', production / 'report.json', ROOT / 'scripts/check_metadata_pair.py', ROOT / 'scripts/check_metadata_test_log.py']}, 'limits': ['Historical 94-test filtered run, not current 297-test rerun', 'Identity/evidence reconciliation, not a new discovery or new refactoring experiment', 'A feasible displaced candidate does not establish a method-level utility score']}
    assert len({report['revision'], report['patch_revision'], report['production_revision']}) == 1
    (run / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    (run / 'runner.py').write_bytes(Path(__file__).read_bytes())
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
