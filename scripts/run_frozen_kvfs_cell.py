"""Execute one pre-frozen kvfs research cell without changing its sources."""

import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    run = (ROOT / 'research/evidence/runs' / sys.argv[1]).resolve()
    assert run.parent == (ROOT / 'research/evidence/runs').resolve()
    cell = sys.argv[2]
    freeze = json.loads((run / 'execution-freeze.json').read_text())
    assert cell in freeze['cells']
    source = Path(freeze['source'])
    for relative, expected in freeze['research_inputs'].items():
        assert digest(ROOT / relative) == expected, relative
    expected_sources = freeze['cells'][cell]['source_hashes']
    for relative, expected in expected_sources.items():
        assert digest(source / relative) == expected, relative
    assert digest(source / '.config') == freeze['configuration_sha256']
    output = run / cell
    output.mkdir(exist_ok=False)
    disk = source / freeze['cells'][cell]['disk_name']
    assert disk.parent == source and not disk.exists()
    with (output / 'setup.log').open('wb') as log:
        subprocess.run(['truncate', '-s', '128M', str(disk)], stdout=log, stderr=subprocess.STDOUT, check=True)
        subprocess.run(['mkfs.ext4', '-F', '-O', '^metadata_csum,^64bit', str(disk)], stdout=log, stderr=subprocess.STDOUT, check=True)
    command = freeze['command_prefix'] + [f'DISK_IMG={disk}']
    environment = dict(os.environ)
    environment.update(freeze['environment'])
    (output / 'command.json').write_text(json.dumps({'command': command, 'environment_overrides': freeze['environment'], 'source': str(source), 'timeout_seconds': freeze['timeout_seconds']}, indent=2) + '\n')
    timed_out = False
    with (output / 'run.log').open('wb') as log:
        process = subprocess.Popen(command, cwd=source, env=environment, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        try:
            code = process.wait(timeout=freeze['timeout_seconds'])
        except subprocess.TimeoutExpired:
            timed_out = True
            os.killpg(process.pid, signal.SIGKILL)
            code = process.wait()
    lines = (output / 'run.log').read_text(errors='replace').splitlines()
    markers = ('RESULT ', 'Test results', 'UNITTEST_STATUS:', 'assert! failed', 'assert_eq! failed', 'panicked')
    (output / 'test-results.txt').write_text('\n'.join(line for line in lines if any(marker in line for marker in markers)) + '\n')
    report = {
        'cell': cell, 'exit_code': code, 'timeout': timed_out,
        'configuration_unchanged': digest(source / '.config') == freeze['configuration_sha256'],
        'source_hashes_after': {relative: digest(source / relative) for relative in expected_sources},
        'run_log_sha256': digest(output / 'run.log'),
        'interpretation': 'Execution evidence only; full log and exact required tests still need independent checking',
    }
    (output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
