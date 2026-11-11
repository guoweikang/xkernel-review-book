"""Bounded non-unittest candidate build and compiler-input gate."""

import json
from pathlib import Path
import shlex
import shutil
import subprocess

from run_metadata_pair import ROOT, PREVIOUS, PATCH_RUN, digest, source_check


def main():
    paired = ROOT / 'research/evidence/runs/2026-11-05-metadata-pair-01'
    pair_report = json.loads((paired / 'report.json').read_text())
    if pair_report['status'] != 'paired_tests_passed':
        raise ValueError('Paired tests must pass first')
    scratch = ROOT / '.build/metadata-pair/2026-11-05-metadata-pair-01'
    source = scratch / 'candidate-source'
    target = scratch / 'production-target'
    output = ROOT / 'research/evidence/runs/2026-11-05-metadata-production-01'
    if target.exists() or output.exists():
        raise ValueError('This fixed run already exists')
    output.mkdir()
    proposal = json.loads((PATCH_RUN / 'report.json').read_text())
    archive = PREVIOUS / 'source.tar'
    if digest(archive) != pair_report['source_archive_sha256']:
        raise ValueError('Archive differs')
    before = source_check(source, archive, proposal)
    if digest(source / '.config') != digest(paired / 'candidate-.config'):
        raise ValueError('Config differs')
    command = ['timeout', '--kill-after=10', '600', 'make', 'build', 'UNITTEST=n',
               'TARGET_DIR=' + str(target), 'XKMAKE_ARGS=-v']
    with (output / 'build.log').open('wb') as log:
        result = subprocess.run(command, cwd=source, env=pair_report['environment'],
                                stdout=log, stderr=subprocess.STDOUT)
    log = (output / 'build.log').read_text(errors='replace')
    lines = [line for line in log.splitlines() if 'Running `' in line and '--crate-name kvfs ' in line]
    flags = []
    for line in lines:
        tokens = shlex.split(line.split('Running `', 1)[1].rstrip('`'))
        flags.extend(tokens[index + 1] for index, token in enumerate(tokens[:-1]) if token == '--cfg')
    depfiles = list((target / 'x86_64-unknown-none/release/deps').glob('kvfs-*.d'))
    depfile_gate = bool(depfiles) and all('ut-tests/' not in path.read_text() for path in depfiles)
    report = {'revision': pair_report['revision'], 'command': command, 'exit_code': result.returncode,
              'environment': pair_report['environment'], 'kvfs_compile_commands': len(lines),
              'kvfs_cfg_flags': flags, 'kvfs_depfiles': len(depfiles),
              'depfiles_exclude_ut_tests': depfile_gate, 'source_files_checked_before': before,
              'source_files_checked_after': source_check(source, archive, proposal),
              'runtime': 'not_run', 'net_benefit': 'unverified'}
    report['config_unchanged'] = digest(source / '.config') == digest(paired / 'candidate-.config')
    report['passed'] = result.returncode == 0 and bool(lines) and 'unittest' not in flags and depfile_gate and report['config_unchanged']
    for path in depfiles:
        shutil.copyfile(path, output / path.name)
    for relative in ['.config', '.cargo/.xconfig.toml', 'Cargo.lock', 'xtask/Cargo.lock']:
        path = source / relative
        if path.exists():
            shutil.copyfile(path, output / relative.replace('/', '__'))
    (output / 'kvfs-commands.log').write_text('\n'.join(lines) + '\n')
    shutil.copyfile(__file__, output / 'runner.py')
    report['artifact_sha256'] = {path.name: digest(path) for path in output.iterdir() if path.is_file()}
    (output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
