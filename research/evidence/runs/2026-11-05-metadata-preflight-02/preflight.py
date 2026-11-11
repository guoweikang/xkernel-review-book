"""Offline dependency preflight of a fixed kernel snapshot, without kernel execution."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tarfile


ROOT = Path(__file__).resolve().parents[1]
REVISION = '7e3ac94431a0dbb376d2fc8d85098deeff1bba09'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, required=True)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--resolve-config', action='store_true')
    args = parser.parse_args()
    if not args.run_id or any(char not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for char in args.run_id):
        parser.error('run-id must use lowercase letters, digits and hyphens')
    output = ROOT / 'research/evidence/runs' / args.run_id
    scratch = ROOT / '.build/metadata-preflight' / args.run_id
    if output.exists() or scratch.exists():
        raise ValueError('Use a fresh run-id')
    output.mkdir(parents=True)
    scratch.mkdir(parents=True)
    archive = scratch / 'source.tar'
    with archive.open('wb') as stream:
        subprocess.run(['git', '-C', str(args.repo), 'archive', REVISION], stdout=stream, check=True)
    source = scratch / 'source'
    source.mkdir()
    with tarfile.open(archive) as bundle:
        bundle.extractall(source, filter='data')
    environment = {key: value for key, value in os.environ.items()
                   if not key.startswith(('CARGO_', 'RUST', 'GIT_'))}
    toolchain = Path('/root/.rustup/toolchains/1.95.0-x86_64-unknown-linux-gnu/bin')
    environment.update(PATH=str(toolchain) + os.pathsep + environment['PATH'],
                       CARGO_NET_OFFLINE='true', CARGO_TARGET_DIR=str(scratch / 'target'),
                       GIT_CEILING_DIRECTORIES=str(scratch), RUSTUP_TOOLCHAIN='1.95.0')
    report = {'revision': REVISION, 'source_archive_sha256': hashlib.sha256(archive.read_bytes()).hexdigest(),
              'kernel_execution': 'not_run', 'candidate_execution': 'not_run', 'steps': [],
              'environment_overrides': {key: environment[key] for key in
                                        ['CARGO_NET_OFFLINE', 'CARGO_TARGET_DIR', 'GIT_CEILING_DIRECTORIES', 'RUSTUP_TOOLCHAIN']}}
    for relative in ['Cargo.lock', 'xtask/Cargo.lock', 'rust-toolchain.toml', '.cargo/config.toml']:
        report.setdefault('input_sha256', {})[relative] = hashlib.sha256((source / relative).read_bytes()).hexdigest()
    commands = [('compiler', ['rustc', '-vV']),
                ('qemu', ['qemu-system-x86_64', '--version']),
                ('xtask-dependencies', ['cargo', 'metadata', '--offline', '--locked', '--format-version', '1',
                                        '--manifest-path', 'xtask/Cargo.toml']),
                ('kernel-dependencies', ['cargo', 'metadata', '--offline', '--locked', '--format-version', '1'])]
    if args.resolve_config:
        seed = source / 'platforms/kplat-x86_64/qemu_defconfig'
        (source / '.config').write_bytes(seed.read_bytes())
        report['input_sha256']['platform_seed'] = hashlib.sha256(seed.read_bytes()).hexdigest()
        commands.append(('resolve-config', ['cargo', 'run', '--offline', '--locked', '--jobs', '2',
                                            '--manifest-path', 'xtask/Cargo.toml', '-p', 'xconfig',
                                            '--bin', 'xconf', '--', 'defconfig', '.config',
                                            '--kconfig', 'Kconfig', '--srctree', '.']))
    for name, command in commands:
        with (output / (name + '.log')).open('wb') as log:
            try:
                result = subprocess.run(command, cwd=source, env=environment, stdout=log,
                                        stderr=subprocess.STDOUT, timeout=120)
                code = result.returncode
            except subprocess.TimeoutExpired:
                code = 124
            except FileNotFoundError as error:
                log.write(str(error).encode())
                code = 127
        report['steps'].append({'name': name, 'command': command, 'exit_code': code})
        if code:
            report['status'] = 'prerequisite_gap'
            break
    else:
        report['status'] = ('config_resolved_runtime_pending' if args.resolve_config else
                            'offline_dependency_resolution_passed_config_and_runtime_pending')
    if args.resolve_config:
        (output / 'config-after-attempt').write_bytes((source / '.config').read_bytes())
    (output / 'preflight.py').write_bytes(Path(__file__).read_bytes())
    report['artifact_sha256'] = {path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                                 for path in sorted(output.iterdir()) if path.is_file()}
    (output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    return 0 if report['status'].startswith('offline_dependency') else 1


if __name__ == '__main__':
    raise SystemExit(main())
