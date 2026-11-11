"""Bounded original-kernel attempt using the verified preflight snapshot."""

import hashlib
import json
import os
from pathlib import Path
import subprocess

from check_metadata_test_log import evaluate, expected_tests


ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    scratch = ROOT / '.build/metadata-preflight/2026-11-05-metadata-preflight-03'
    source = scratch / 'source'
    output = ROOT / 'research/evidence/runs/2026-11-05-metadata-original-01'
    output.mkdir()
    preflight = json.loads((ROOT / 'research/evidence/runs/2026-11-05-metadata-preflight-03/report.json').read_text())
    if digest(source / '.config') != preflight['artifact_sha256']['config-after-attempt']:
        raise ValueError('Config identity changed')
    for relative, expected in preflight['input_sha256'].items():
        if relative != 'platform_seed' and digest(source / relative) != expected:
            raise ValueError('Input identity changed: ' + relative)
    environment = {'HOME': '/root', 'PATH': '/root/.rustup/toolchains/1.95.0-x86_64-unknown-linux-gnu/bin:/root/.cargo/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin',
                   'LANG': 'C.UTF-8', 'CARGO_NET_OFFLINE': 'true', 'CARGO_BUILD_JOBS': '2',
                   'RUSTUP_TOOLCHAIN': '1.95.0', 'XKERNEL_ENABLE_COVERAGE': '0',
                   'GIT_CEILING_DIRECTORIES': str(scratch)}
    disk = scratch / 'metadata-original-disk.img'
    with disk.open('xb') as stream:
        stream.truncate(64 * 1024 * 1024)
    report = {'revision': preflight['revision'], 'environment': environment,
              'steps': [], 'candidate': 'not_run', 'coverage': 'disabled_explicitly',
              'disk_policy': 'new private 64MiB ext4, no user image, no host mount'}
    commands = [('format-disk', ['mkfs.ext4', '-q', '-F', '-b', '4096', '-O', '^metadata_csum,^64bit', str(disk)]),
                ('original', ['timeout', '--kill-after=10', '600', 'make', 'unittest',
                              'UNITTEST_CRATE=kvfs::mount::tests,kvfs::node::dentry::tests_dentry',
                              'ACCEL=n', 'NET=n', 'VSOCK=n', 'BLK=y', 'DISK_IMG=' + str(disk),
                              'TARGET_DIR=' + str(scratch / 'kernel-target'),
                              'XCONFIG_TARGET_DIR=' + str(scratch / 'target')])]
    for name, command in commands:
        with (output / (name + '.log')).open('wb') as log:
            result = subprocess.run(command, cwd=source, env=environment, stdout=log, stderr=subprocess.STDOUT)
        report['steps'].append({'name': name, 'command': command, 'exit_code': result.returncode})
        if name == 'format-disk' and result.returncode == 0:
            report['initial_disk_sha256'] = digest(disk)
        if result.returncode:
            break
    runtime = next((step for step in report['steps'] if step['name'] == 'original'), None)
    if runtime:
        report['test_gate'] = evaluate((output / 'original.log').read_text(errors='replace'),
                                       runtime['exit_code'], expected_tests())
    report['status'] = 'passed' if report.get('test_gate', {}).get('passed') else 'not_accepted'
    report['final_disk_sha256'] = digest(disk)
    for relative in ['.config', '.cargo/.xconfig.toml', 'Cargo.lock', 'xtask/Cargo.lock']:
        path = source / relative
        if path.exists():
            (output / relative.replace('/', '__')).write_bytes(path.read_bytes())
    (output / 'runner.py').write_bytes(Path(__file__).read_bytes())
    report['artifact_sha256'] = {path.name: digest(path) for path in output.iterdir() if path.is_file()}
    (output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    return 0 if report['status'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
