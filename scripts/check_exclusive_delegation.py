"""Verify source isolation and matched test populations for one delegation proposal."""

import hashlib
import json
from pathlib import Path
import re
import sys
import tarfile


ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / 'research/evidence/runs/2026-11-18-exclusive-delegation-01'
PRIOR = ROOT / 'research/evidence/runs/2026-11-18-cache-transaction-fixture-01'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    inputs = json.loads((RUN / 'input-freeze.json').read_text())
    freeze = json.loads((RUN / 'execution-freeze.json').read_text())
    for relative, expected in (inputs['input_hashes'] | freeze['research_inputs']).items():
        assert digest(ROOT / relative) == expected, relative
    source = (PRIOR / 'baseline-dentry.rs').read_text()
    lines = source.splitlines(keepends=True)
    expected_candidate = ''.join(lines[:1164]) + (RUN / 'proposal.rs').read_text() + ''.join(lines[1180:])
    assert (RUN / 'candidate-dentry.rs').read_text() == expected_candidate
    fixture = (RUN / 'fixture.rs').read_text()
    names = re.findall(r'^fn (test_exclusive_\w+)\(', fixture, re.M)
    assert 1 <= len(names) <= 6 and len(names) == len(set(names))
    summary = {}
    populations = []
    for cell in ('original', 'candidate'):
        folder = RUN / cell
        report = json.loads((folder / 'report.json').read_text())
        assert digest(folder / 'run.log') == report['run_log_sha256']
        assert report['exit_code'] == 0 and not report['timeout']
        assert report['configuration_unchanged']
        assert report['source_hashes_after'] == freeze['cells'][cell]['source_hashes']
        log = (folder / 'run.log').read_text()
        matches = re.findall(r'RESULT\s+(\S+)\s+\.\.\. (ok|FAILED)', log)
        results = dict(matches)
        assert len(matches) == len(results) == 297 + len(names)
        assert all(outcome == 'ok' for outcome in results.values())
        assert 'UNITTEST_STATUS: ALL_TESTS_PASSED' in log
        assert 'assert! failed' not in log and 'assert_eq! failed' not in log
        selected = {name: results['kvfs::node::dentry::tests_dentry::' + name] for name in names}
        populations.append(set(results))
        summary[cell] = {'total': len(results), 'fixture': selected}
    assert populations[0] == populations[1]
    baseline_log = (PRIOR / 'original/run.log').read_text()
    baseline_names = set(re.findall(r'RESULT\s+(\S+)\s+\.\.\. (?:ok|FAILED)', baseline_log))
    baseline_names = {name for name in baseline_names if '::test_cache_fixture_' not in name}
    assert len(baseline_names) == 297
    assert populations[0] - {'kvfs::node::dentry::tests_dentry::' + name for name in names} == baseline_names
    restoration = None
    if '--check-restored-source' in sys.argv:
        isolated = Path(freeze['source'])
        assert digest(isolated / '.config') == freeze['configuration_sha256']
        checked = 0
        with tarfile.open(isolated / 'source.tar') as archive:
            for member in archive:
                if member.isfile():
                    assert not Path(member.name).is_absolute() and '..' not in Path(member.name).parts
                    assert digest(isolated / member.name) == hashlib.sha256(archive.extractfile(member).read()).hexdigest(), member.name
                    checked += 1
        restoration = {'archive_files_equal': checked, 'configuration_equal': True}
    print(json.dumps({'cells': summary, 'same_test_population': True, 'original_297_tests_preserved': True, 'only_narrow_method_changed': True, 'restoration': restoration, 'full_equivalence_or_performance_proven': False}, indent=2))


if __name__ == '__main__':
    main()
