import argparse
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', required=True)
    args = parser.parse_args()
    run = ROOT / 'research/evidence/runs' / args.run
    frozen = json.loads((run / 'frozen-inputs.json').read_text())
    for relative, expected in frozen['files'].items():
        assert hashlib.sha256((run / relative).read_bytes()).hexdigest() == expected, relative
    protocol = json.loads((run / 'protocol.json').read_text())
    expected_new = set(re.findall(r'#\[def_test\]\s*fn (\w+)\(', (run / 'fixture.rs').read_text()))
    assert len(expected_new) == 6
    expected_failed = {'removal_event_unlink_cached_fallback', 'removal_event_rmdir_cached_fallback'}
    baseline_log = (ROOT / 'research/evidence/runs/2026-11-17-kvfs-original-01/run.log').read_text()
    baseline_names = {name for name, _status in re.findall(r'RESULT\s+(\S+)\s+\.\.\.\s+(\S+)', baseline_log)}
    assert len(baseline_names) == 297
    summary = []
    sets = {}
    for condition in protocol['conditions']:
        cell = run / condition
        report = json.loads((cell / 'report.json').read_text())
        assert not report['timeout'] and not report['unexpected_source_changes']
        assert report['configuration_unchanged']
        for relative, expected in report['files'].items():
            assert hashlib.sha256((cell / relative).read_bytes()).hexdigest() == expected, (condition, relative)
        log = (cell / 'run.log').read_text()
        results = re.findall(r'RESULT\s+(\S+)\s+\.\.\.\s+(\S+)', log)
        assert [list(result) for result in results] == report['results']
        names = {name for name, _status in results}
        assert len(names) == len(results)
        sets[condition] = names
        observed = condition.endswith('-observed')
        assert len(results) == (303 if observed else 297)
        new = {name.rsplit('::', 1)[-1] for name in names if '::removal_event_' in name}
        assert new == (expected_new if observed else set())
        assert {name for name in names if '::removal_event_' not in name} == baseline_names
        failed = {name.rsplit('::', 1)[-1] for name, status in results if status != 'ok'}
        if condition == 'mutant-observed':
            assert failed == expected_failed
            assert report['exit_code'] != 0
            assert '301 passed, 2 failed, 0 ignored, 303 total' in log
        else:
            assert not failed and report['exit_code'] == 0
            assert 'ALL_TESTS_PASSED' in log
            count = len(results)
            assert f'{count} passed, 0 failed, 0 ignored, {count} total' in log
        summary.append({'condition': condition, 'tests': len(results), 'passed': len(results) - len(failed), 'failed': sorted(failed)})
    assert sets['original-observed'] == sets['candidate-observed'] == sets['mutant-observed']
    assert sets['mutant-old'] < sets['original-observed']
    report = {'conditions': summary, 'frozen_inputs_verified': len(frozen['files']), 'consistent_test_identities': True, 'limits': 'One development candidate, one mutant, one execution per cell; no general detection rate or performance inference.'}
    (run / 'checked-results.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
