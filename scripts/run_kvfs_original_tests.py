import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / 'research/evidence/runs/2026-11-17-kvfs-original-01'
PARENT = ROOT / 'research/evidence/runs/2026-11-16-pagecache-original-01'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    RUN.mkdir(exist_ok=False)
    shutil.copyfile(__file__, RUN / 'runner.py')
    previous = json.loads((PARENT / 'report.json').read_text())
    source = Path(previous['isolated_source'])
    assert digest(source / 'source.tar') == previous['source_archive_sha256']
    assert digest(source / '.config') == digest(PARENT / 'output.config')

    def source_check():
        changed = []
        count = 0
        with tarfile.open(source / 'source.tar') as archive:
            for member in archive:
                if member.isfile():
                    count += 1
                    expected = hashlib.sha256(archive.extractfile(member).read()).hexdigest()
                    if not (source / member.name).is_file() or digest(source / member.name) != expected:
                        changed.append(member.name)
        return {'checked': count, 'changed': changed}

    before = source_check()
    (RUN / 'source-before.json').write_text(json.dumps(before, indent=2) + '\n')
    assert not before['changed']
    evidence_files = ['fs/kvfs/src/mount.rs', 'fs/kvfs/src/node/dentry.rs', 'fs/kvfs/src/types.rs', 'fs/kvfs/src/namei.rs', 'fs/kvfs/ut-tests/node_dentry.rs', 'posix/fs/src/namei.rs']
    for relative in evidence_files:
        target = RUN / 'sources' / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source / relative, target)
    disk = source / 'research-kvfs-root.ext4'
    assert not disk.exists()
    command = ['make', 'unittest', 'UNITTEST_CRATE=kvfs', 'ACCEL=n', 'NET=n', 'BLK=y', 'VSOCK=n', 'SMP=2', 'MEM=1g', f'DISK_IMG={disk}']
    protocol = {'revision': previous['revision'], 'question': 'Which existing kvfs tests execute in the original kernel harness before any removal-event refactoring?', 'command': command, 'timeout_seconds': 300, 'attempts': 1, 'source': str(source), 'configuration_sha256': digest(source / '.config'), 'source_archive_sha256': digest(source / 'source.tar'), 'compiler': '1.95.0', 'test_status': 'baseline only, no candidate or new assertions', 'measurement': 'Retain all log output, per-test RESULT lines, summary, exit, source hashes; do not equate passing with event snapshot contract coverage.', 'files': {str(path.relative_to(RUN)): digest(path) for path in sorted(RUN.rglob('*')) if path.is_file()}}
    (RUN / 'protocol.json').write_text(json.dumps(protocol, indent=2) + '\n')
    with (RUN / 'setup.log').open('wb') as log:
        subprocess.run(['truncate', '-s', '128M', str(disk)], stdout=log, stderr=subprocess.STDOUT, check=True)
        subprocess.run(['mkfs.ext4', '-F', '-O', '^metadata_csum,^64bit', str(disk)], stdout=log, stderr=subprocess.STDOUT, check=True)
    disk_before = digest(disk)
    environment = dict(os.environ)
    environment.update({'RUSTUP_TOOLCHAIN': '1.95.0', 'CARGO_NET_OFFLINE': 'true', 'CARGO_BUILD_JOBS': '4', 'RUSTFLAGS': '', 'CARGO_ENCODED_RUSTFLAGS': '', 'GIT_CEILING_DIRECTORIES': '/tmp'})
    timed_out = False
    with (RUN / 'run.log').open('wb') as log:
        process = subprocess.Popen(command, cwd=source, env=environment, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        try:
            code = process.wait(timeout=300)
        except subprocess.TimeoutExpired:
            timed_out = True
            os.killpg(process.pid, signal.SIGKILL)
            code = process.wait()
    lines = (RUN / 'run.log').read_text(errors='replace').splitlines()
    results = [line for line in lines if 'RESULT ' in line or 'Test results' in line or 'ALL_TESTS_PASSED' in line or 'FAILED_TESTS' in line or 'COVERAGE_PERSISTED' in line]
    (RUN / 'test-results.txt').write_text('\n'.join(results) + '\n')
    report = {'exit_code': code, 'timeout': timed_out, 'source_after': source_check(), 'configuration_unchanged': digest(source / '.config') == protocol['configuration_sha256'], 'disk_before': disk_before, 'disk_after': digest(disk), 'results': results, 'files': {str(path.relative_to(RUN)): digest(path) for path in sorted(RUN.rglob('*')) if path.is_file()}}
    (RUN / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({key: value for key, value in report.items() if key not in ('results', 'files')}, indent=2))


if __name__ == '__main__':
    main()
