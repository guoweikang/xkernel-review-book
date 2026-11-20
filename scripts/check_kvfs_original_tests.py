import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / 'research/evidence/runs/2026-11-17-kvfs-original-01'
report = json.loads((RUN / 'report.json').read_text())
assert report['exit_code'] == 0 and not report['timeout']
assert report['source_after'] == {'checked': 3634, 'changed': []}
assert report['configuration_unchanged']
for relative, expected in report['files'].items():
    assert hashlib.sha256((RUN / relative).read_bytes()).hexdigest() == expected, relative
log = (RUN / 'run.log').read_text()
results = re.findall(r'RESULT\s+(\S+)\s+\.\.\.\s+(\S+)', log)
assert len(results) == 297 and len({name for name, _status in results}) == 297
assert all(status == 'ok' for _name, status in results)
assert '297 passed, 0 failed, 0 ignored, 297 total' in log
assert 'ALL_TESTS_PASSED' in log and 'COVERAGE_PERSISTED' in log
required = ['test_rmdir_uses_directory_removal_callback', 'test_unlink_validator_observes_callback_victim', 'test_readonly_mount_blocks_unlink', 'test_sticky_directory_rejects_unrelated_user_delete']
for suffix in required:
    assert any(name.endswith('::' + suffix) for name, _status in results), suffix
checked = {'unique_passes': 297, 'required_tests': required, 'artifacts_verified': len(report['files']), 'limits': 'Baseline assertions only; no tracked snapshot or fallback correctness inferred.'}
(RUN / 'checked-results.json').write_text(json.dumps(checked, indent=2) + '\n')
print(json.dumps(checked))
