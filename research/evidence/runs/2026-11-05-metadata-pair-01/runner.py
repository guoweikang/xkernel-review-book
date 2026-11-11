"""Run original and candidate with identical preboot disk bytes and exact test gates."""

import argparse
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tarfile

from check_metadata_test_log import evaluate, expected_tests


ROOT = Path(__file__).resolve().parents[1]
PREVIOUS = ROOT / '.build/metadata-preflight/2026-11-05-metadata-preflight-03'
PATCH_RUN = ROOT / 'research/evidence/runs/2026-11-05-metadata-fixture-patch-02'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_check(source, archive, proposal=None):
    checked = 0
    with tarfile.open(archive) as bundle:
        for member in bundle:
            if member.isfile():
                expected = bundle.extractfile(member).read()
                if proposal and member.name in proposal['changed_paths']:
                    expected = (PATCH_RUN / 'proposed' / member.name).read_bytes()
                if (source / member.name).read_bytes() != expected:
                    raise ValueError('Source differs: ' + member.name)
                checked += 1
    if proposal:
        for relative in proposal['changed_paths']:
            if digest(source / relative) != proposal['artifacts_sha256']['proposed/' + relative]:
                raise ValueError('Proposal differs: ' + relative)
    return checked


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    if not args.run_id or any(char not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for char in args.run_id):
        parser.error('Invalid run-id')
    output = ROOT / 'research/evidence/runs' / args.run_id
    scratch = ROOT / '.build/metadata-pair' / args.run_id
    if output.exists() or scratch.exists():
        raise ValueError('Use a fresh run-id')
    output.mkdir(parents=True)
    scratch.mkdir(parents=True)
    preflight = json.loads((ROOT / 'research/evidence/runs/2026-11-05-metadata-preflight-03/report.json').read_text())
    proposal = json.loads((PATCH_RUN / 'report.json').read_text())
    archive = PREVIOUS / 'source.tar'
    patch = PATCH_RUN / 'candidate.patch'
    if digest(archive) != preflight['source_archive_sha256'] or digest(patch) != proposal['artifacts_sha256']['candidate.patch']:
        raise ValueError('Archive or patch identity changed')
    config = ROOT / 'research/evidence/runs/2026-11-05-metadata-preflight-03/config-after-attempt'
    if digest(config) != preflight['artifact_sha256']['config-after-attempt']:
        raise ValueError('Config identity changed')
    environment = {'HOME': '/root', 'PATH': '/root/.rustup/toolchains/1.95.0-x86_64-unknown-linux-gnu/bin:/root/.cargo/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin',
                   'LANG': 'C.UTF-8', 'CARGO_NET_OFFLINE': 'true', 'CARGO_BUILD_JOBS': '2',
                   'RUSTUP_TOOLCHAIN': '1.95.0', 'XKERNEL_ENABLE_COVERAGE': '0',
                   'GIT_CEILING_DIRECTORIES': str(ROOT / '.build')}
    report = {'revision': preflight['revision'], 'environment': environment, 'steps': [], 'runs': {},
              'status': 'incomplete', 'production_build': 'not_run', 'net_benefit': 'unverified',
              'cache_policy': 'original reuses verified original outputs; candidate has fresh outputs; not a timing experiment',
              'source_archive_sha256': digest(archive), 'patch_sha256': digest(patch)}

    def execute(name, command, cwd):
        with (output / (name + '.log')).open('wb') as log:
            result = subprocess.run(command, cwd=cwd, env=environment, stdout=log, stderr=subprocess.STDOUT)
        report['steps'].append({'name': name, 'command': command, 'cwd': str(cwd), 'exit_code': result.returncode})
        return result.returncode

    try:
        template = scratch / 'preboot.img'
        with template.open('xb') as stream:
            stream.truncate(64 * 1024 * 1024)
        if execute('format', ['timeout', '60', 'mkfs.ext4', '-q', '-F', '-b', '4096', '-O', '^metadata_csum,^64bit', str(template)], scratch):
            raise ValueError('Image formatting failed')
        report['template_sha256'] = digest(template)
        with gzip.open(output / 'preboot.img.gz', 'wb') as stream:
            stream.write(template.read_bytes())
        template.chmod(0o444)
        for variant in ['original', 'candidate']:
            source = PREVIOUS / 'source' if variant == 'original' else scratch / 'candidate-source'
            target = PREVIOUS / 'kernel-target' if variant == 'original' else scratch / 'candidate-target'
            if variant == 'candidate':
                source.mkdir()
                with tarfile.open(archive) as bundle:
                    bundle.extractall(source, filter='data')
                for mode in [['--check'], []]:
                    if execute('patch-check' if mode else 'patch-apply', ['git', 'apply', *mode, str(patch)], source):
                        raise ValueError('Patch application failed')
                shutil.copyfile(config, source / '.config')
            selected = proposal if variant == 'candidate' else None
            checked = source_check(source, archive, selected)
            if digest(source / '.config') != digest(config):
                raise ValueError('Variant config differs')
            disk = scratch / (variant + '.img')
            shutil.copyfile(template, disk)
            initial = digest(disk)
            if initial != report['template_sha256']:
                raise ValueError('Initial disk differs')
            code = execute(variant, ['timeout', '--kill-after=10', '600', 'make', 'unittest',
                                    'UNITTEST_CRATE=kvfs::mount::tests,kvfs::node::dentry::tests_dentry',
                                    'ACCEL=n', 'NET=n', 'VSOCK=n', 'BLK=y', 'DISK_IMG=' + str(disk),
                                    'TARGET_DIR=' + str(target)], source)
            gate = evaluate((output / (variant + '.log')).read_text(errors='replace'), code, expected_tests())
            report['runs'][variant] = {'test_gate': gate, 'initial_disk_sha256': initial,
                                       'final_disk_sha256': digest(disk), 'source_files_checked_before': checked,
                                       'source_files_checked_after': source_check(source, archive, selected)}
            for relative in ['.config', '.cargo/.xconfig.toml', 'Cargo.lock', 'xtask/Cargo.lock']:
                path = source / relative
                if path.exists():
                    shutil.copyfile(path, output / (variant + '-' + relative.replace('/', '__')))
            if digest(source / '.config') != digest(config):
                raise ValueError('Runtime changed config')
            if not gate['passed']:
                report['status'] = variant + '_not_accepted'
                break
        else:
            report['status'] = 'paired_tests_passed'
        if digest(template) != report['template_sha256']:
            raise ValueError('Template changed')
    except Exception as error:
        report['status'] = 'execution_error'
        report['error'] = str(error)
    finally:
        shutil.copyfile(__file__, output / 'runner.py')
        shutil.copyfile(ROOT / 'scripts/check_metadata_test_log.py', output / 'log-checker.py')
        shutil.copyfile(patch, output / 'candidate.patch')
        report['artifact_sha256'] = {path.name: digest(path) for path in output.iterdir() if path.is_file()}
        (output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    return 0 if report['status'] == 'paired_tests_passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
