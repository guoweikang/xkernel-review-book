import argparse
import difflib
import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUSTC = Path('/root/.rustup/toolchains/1.95.0-x86_64-unknown-linux-gnu/bin/rustc')
REVISION = '7e3ac94431a0dbb376d2fc8d85098deeff1bba09'
SOURCES = {
    'cpu': 'arch/kcpu_slot/src/dynamic.rs',
    'boot': 'boot/kernel-elf-loader/src/lib.rs',
    'host': 'xtask/xkmake/src/image_metadata.rs',
}
TARGETS = ['x86_64-unknown-none', 'x86_64-unknown-uefi',
           'riscv64gc-unknown-none-elf', 'aarch64-unknown-none-softfloat',
           'loongarch64-unknown-none-softfloat']


def main():
    parser = argparse.ArgumentParser(description='R008 extracted functions versus a core-based adaptation')
    parser.add_argument('--repo', type=Path, required=True)
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9_-]+', args.run_id):
        parser.error('Invalid run ID')
    run = ROOT / '.build/alignment' / args.run_id
    evidence = ROOT / 'research/evidence/runs' / args.run_id
    if run.exists() or evidence.exists():
        parser.error('Run already exists')
    work = run / 'work'
    work.mkdir(parents=True)
    evidence.mkdir(parents=True)
    report = {'passed': False, 'revision': REVISION, 'commands': [], 'sources': {},
              'kernel_integration': 'not_run', 'performance': 'not_measured',
              'scope': 'extracted arithmetic functions; visibility widened for harness access'}
    shutil.copy2(__file__, evidence / 'runner.py')
    shutil.copy2(ROOT / 'scripts/scc_namespace.sh', evidence / 'namespace.sh')
    template = ROOT / 'research/tools/alignment-core-tests.rs.in'
    shutil.copy2(template, evidence / template.name)

    def execute(command, log):
        report['commands'].append([str(part) for part in command])
        with (evidence / log).open('w') as output:
            return subprocess.run(command, stdout=output, stderr=subprocess.STDOUT, timeout=90).returncode

    def fixed_source(path):
        return subprocess.check_output(['git', '-C', str(args.repo), 'show', f'{REVISION}:{path}']).decode()

    try:
        (evidence / 'rustc.txt').write_bytes(subprocess.check_output([RUSTC, '-Vv']))
        toolchain = fixed_source('rust-toolchain.toml')
        (evidence / 'rust-toolchain.toml').write_text(toolchain)
        if 'channel = "1.95.0"' not in toolchain:
            raise ValueError('Unexpected project toolchain')
        core = RUSTC.parent.parent / 'lib/rustlib/src/rust/library/core/src/num/uint_macros.rs'
        shutil.copy2(core, evidence / 'uint_macros.rs')
        report['core_source_sha256'] = hashlib.sha256(core.read_bytes()).hexdigest()
        modules = []
        patches = []
        for name, path in SOURCES.items():
            source = fixed_source(path)
            anchor = 'fn align_up('
            if source.count(anchor) != 1:
                raise ValueError('Ambiguous function anchor')
            begin = source.index(anchor)
            opening = source.index('{', begin)
            depth = 1
            end = opening + 1
            while depth:
                depth += (source[end] == '{') - (source[end] == '}')
                end += 1
            original = source[begin:end]
            alignment = 'alignment' if name == 'host' else 'align'
            pattern = (r'value\s*\.checked_add\(' + alignment + r' - 1\)'
                       r'\s*\.map\(\|value\| value & !\(' + alignment + r' - 1\)\)')
            candidate, count = re.subn(pattern, f'value.checked_next_multiple_of({alignment})', original)
            if count != 1:
                raise ValueError('Arithmetic replacement did not match exactly once')
            (evidence / (name + '-source.rs')).write_text(source)
            (evidence / (name + '-original.rs')).write_text(original + '\n')
            (evidence / (name + '-candidate.rs')).write_text(candidate + '\n')
            report['sources'][name] = {'path': path, 'start_line': source[:begin].count('\n') + 1,
                                      'sha256': hashlib.sha256(source.encode()).hexdigest()}
            adapted = source[:begin] + candidate + source[end:]
            patches.extend(difflib.unified_diff(source.splitlines(True), adapted.splitlines(True),
                                               fromfile='a/' + path, tofile='b/' + path))
            for variant, content in [('original', original), ('candidate', candidate)]:
                modules.append(f'mod {name}_{variant} {{\npub(crate) {content}\n}}\n')
        (evidence / 'candidate.patch').write_text(''.join(patches))
        library = ''.join(modules)
        tests = library + template.read_text()
        (work / 'probe.rs').write_text(tests)
        (evidence / 'probe.rs').write_text(tests)
        for profile, flags in [('debug', []), ('release', ['-O'])]:
            if execute([RUSTC, '--edition=2024', '--test', work / 'probe.rs', '-o', work / profile, *flags], profile + '-compile.log'):
                raise ValueError(profile + ' compile failed')
            command = ['timeout', '60', 'unshare', '--user', '--map-root-user', '--mount', '--pid', '--net', '--ipc', '--uts', '--fork',
                       'bash', ROOT / 'scripts/scc_namespace.sh', run / (profile + '-root'), work,
                       ROOT / '.tools/scc-smoke', '/work/' + profile, '--test-threads=1', '--nocapture']
            if execute(command, profile + '-tests.log'):
                raise ValueError(profile + ' tests failed')
        (work / 'library.rs').write_text('#![no_std]\n' + library)
        for target in TARGETS:
            if execute([RUSTC, '--edition=2024', '--crate-type=lib', '--target', target,
                        work / 'library.rs', '--emit=metadata', '-o', work / (target + '.rmeta')], target + '.log'):
                raise ValueError(target + ' metadata compile failed')
        report['target_metadata_compile'] = TARGETS
        report['passed'] = True
    except Exception as error:
        report['error'] = str(error)
    finally:
        report['artifacts_sha256'] = {path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                                    for path in sorted(evidence.iterdir()) if path.is_file()}
        (evidence / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'passed': report['passed'], 'error': report.get('error'), 'evidence': str(evidence)}))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
