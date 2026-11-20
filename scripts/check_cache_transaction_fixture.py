"""Verify the complete two-cell kernel fixture evidence, not just process exits."""

import hashlib
import json
from pathlib import Path
import re
import sys
import tarfile


ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / 'research/evidence/runs/2026-11-18-cache-transaction-fixture-01'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    freeze = json.loads((RUN / 'freeze.json').read_text())
    for relative, expected in freeze['research_inputs'].items():
        assert digest(ROOT / relative) == expected, relative
    fixture = (RUN / 'fixture.rs').read_text()
    names = re.findall(r'^fn (test_cache_fixture_\w+)\(', fixture, re.M)
    assert len(names) == len(set(names)) == 6
    designated = 'test_cache_fixture_live_par_winner'
    evidence = {}
    populations = []
    for cell in ('original', 'mutant'):
        folder = RUN / cell
        report = json.loads((folder / 'report.json').read_text())
        assert digest(folder / 'run.log') == report['run_log_sha256']
        assert not report['timeout'] and report['configuration_unchanged']
        assert report['source_hashes_after'] == freeze['cell_source_hashes'][cell]
        assert report['exit_code'] == (0 if cell == 'original' else 2)
        log = (folder / 'run.log').read_text()
        matches = re.findall(r'RESULT\s+(\S+)\s+\.\.\. (ok|FAILED)', log)
        results = dict(matches)
        assert len(matches) == len(results) == 303
        populations.append(set(results))
        failed = [name for name, outcome in matches if outcome == 'FAILED']
        expected_failed = [] if cell == 'original' else ['kvfs::node::dentry::tests_dentry::' + designated]
        assert failed == expected_failed, failed
        selected = {name: results['kvfs::node::dentry::tests_dentry::' + name] for name in names}
        diagnostics = [line for line in log.splitlines() if 'assert! failed at ' in line]
        if cell == 'original':
            assert not diagnostics
            assert '303 passed, 0 failed, 0 ignored, 303 total' in log
            assert 'UNITTEST_STATUS: ALL_TESTS_PASSED' in log
        else:
            assert len(diagnostics) == 1 and diagnostics[0].endswith(': par_winner_identity')
            line = int(re.search(r':(\d+): par_winner_identity$', diagnostics[0]).group(1))
            combined = (RUN / 'baseline-test.rs').read_text() + '\n' + fixture
            assert combined.splitlines()[line - 1].strip() == 'assert!(par_winner_identity);'
            assert '302 passed, 1 failed, 0 ignored, 303 total' in log
            assert 'UNITTEST_STATUS: TESTS_FAILED' in log
        evidence[cell] = {'total': len(results), 'failed': failed, 'fixture_results': selected, 'assert_diagnostics': diagnostics}
    assert populations[0] == populations[1]
    baseline = (RUN / 'baseline-dentry.rs').read_text()
    mutant = (RUN / 'mutant-dentry.rs').read_text()
    addition = '            .filter(|entry| !entry.is_parallel_lookup())\n'
    assert mutant.count(addition) == baseline.count(addition) + 1
    assert mutant.replace(addition, '', 1) == baseline
    restoration = None
    if '--check-restored-source' in sys.argv:
        source = Path(freeze['source'])
        assert digest(source / '.config') == freeze['configuration_sha256']
        checked = 0
        with tarfile.open(source / 'source.tar') as archive:
            for member in archive:
                if member.isfile():
                    assert not Path(member.name).is_absolute() and '..' not in Path(member.name).parts
                    assert digest(source / member.name) == hashlib.sha256(archive.extractfile(member).read()).hexdigest(), member.name
                    checked += 1
        restoration = {'archive_source_files_equal': checked, 'configuration_restored': True}
    print(json.dumps({'cells': evidence, 'same_303_test_population': True, 'single_designated_mutation_detected': True, 'restoration': restoration, 'refactor_equivalence_proven': False}, indent=2))


if __name__ == '__main__':
    main()
