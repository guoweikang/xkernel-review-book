"""Run one frozen real-kernel fixture cell in an existing isolated source tree."""

import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / 'research/evidence/runs/2026-11-18-cache-transaction-fixture-01'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    cell = sys.argv[1]
    assert cell in ('original', 'mutant')
    freeze = json.loads((RUN / 'freeze.json').read_text())
    source = Path(freeze['source'])
    for relative, expected in freeze['research_inputs'].items():
        assert digest(ROOT / relative) == expected, relative
    for relative, expected in freeze['cell_source_hashes'][cell].items():
        assert digest(source / relative) == expected, relative
    assert digest(source / '.config') == freeze['configuration_sha256']
    output = RUN / cell
    output.mkdir(exist_ok=False)
    disk = source / f'research-cache-transaction-{cell}.ext4'
    assert not disk.exists()
    with (output / 'setup.log').open('wb') as log:
        subprocess.run(['truncate', '-s', '128M', str(disk)], stdout=log, stderr=subprocess.STDOUT, check=True)
        subprocess.run(['mkfs.ext4', '-F', '-O', '^metadata_csum,^64bit', str(disk)], stdout=log, stderr=subprocess.STDOUT, check=True)
    command = ['make', 'unittest', 'UNITTEST_CRATE=kvfs', 'ACCEL=n', 'NET=n', 'BLK=y', 'VSOCK=n', 'SMP=2', 'MEM=1g', f'DISK_IMG={disk}']
    environment = dict(os.environ)
    environment.update(freeze['environment'])
    (output / 'command.json').write_text(json.dumps({'command': command, 'environment_overrides': freeze['environment'], 'source': str(source), 'timeout_seconds': 300}, indent=2) + '\n')
    timed_out = False
    with (output / 'run.log').open('wb') as log:
        process = subprocess.Popen(command, cwd=source, env=environment, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        try:
            code = process.wait(timeout=300)
        except subprocess.TimeoutExpired:
            timed_out = True
            os.killpg(process.pid, signal.SIGKILL)
            code = process.wait()
    lines = (output / 'run.log').read_text(errors='replace').splitlines()
    results = [line for line in lines if any(marker in line for marker in ('RESULT ', 'Test results', 'ALL_TESTS_PASSED', 'FAILED_TESTS', 'panicked', 'test_research_cache_'))]
    (output / 'test-results.txt').write_text('\n'.join(results) + '\n')
    report = {
        'cell': cell, 'exit_code': code, 'timeout': timed_out,
        'configuration_unchanged': digest(source / '.config') == freeze['configuration_sha256'],
        'source_hashes_after': {relative: digest(source / relative) for relative in freeze['cell_source_hashes'][cell]},
        'run_log_sha256': digest(output / 'run.log'),
        'interpretation': 'Raw execution only; parent must inspect exact assertion, coverage and failure reason',
    }
    (output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
