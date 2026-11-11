import argparse
import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TOOLCHAIN = Path('/root/.rustup/toolchains/1.95.0-x86_64-unknown-linux-gnu')
RUSTC = TOOLCHAIN / 'bin/rustc'
OBJDUMP = TOOLCHAIN / 'lib/rustlib/x86_64-unknown-linux-gnu/bin/llvm-objdump'
INPUT = ROOT / 'research/evidence/runs/2026-11-05-alignment-core-01'
TARGETS = ['x86_64-unknown-linux-gnu', 'x86_64-unknown-none', 'x86_64-unknown-uefi',
           'riscv64gc-unknown-none-elf', 'aarch64-unknown-none-softfloat',
           'loongarch64-unknown-none-softfloat']
CASES = {
    'cpu_dynamic': ('cpu', 'usize', 'Option<usize>', 'alignment'),
    'cpu_type16': ('cpu', 'usize', 'Option<usize>', 'core::mem::align_of::<Aligned>()'),
    'host_4': ('host', 'usize', 'Option<usize>', '4'),
    'host_dynamic': ('host', 'usize', 'Option<usize>', 'alignment'),
    'boot_4096': ('boot', 'u64', "Result<u64, &'static str>", '4096'),
    'boot_dynamic': ('boot', 'u64', "Result<u64, &'static str>", 'alignment'),
}


def instructions(disassembly):
    if disassembly.count('<evaluate>:\n') != 1:
        raise ValueError('Missing or ambiguous wrapper disassembly')
    body = disassembly.split('<evaluate>:\n', 1)[1]
    return [' '.join(line.split()) for line in body.splitlines() if line.strip()]


def main():
    parser = argparse.ArgumentParser(description='Fixed-setting codegen screen, not a runtime benchmark')
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9_-]+', args.run_id):
        parser.error('Invalid run ID')
    evidence = ROOT / 'research/evidence/runs' / args.run_id
    work = ROOT / '.build/alignment-codegen' / args.run_id
    if evidence.exists() or work.exists():
        parser.error('Run already exists')
    evidence.mkdir(parents=True)
    work.mkdir(parents=True)
    report = {'passed': False, 'purpose': 'screen generated instructions; not assert all pairs identical',
              'settings': ['opt-level=3', 'panic=abort', 'debug-assertions=no', 'codegen-units=1'],
              'commands': [], 'pairs': [], 'runtime_benchmark': 'not_run', 'integration': 'not_run'}
    shutil.copy2(__file__, evidence / 'runner.py')

    def execute(command, output):
        report['commands'].append([str(part) for part in command])
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=90)
        (evidence / output).write_bytes(result.stdout)
        if result.returncode:
            raise ValueError(f'Command failed: {output}')
        return result.stdout.decode()

    try:
        source_report = json.loads((INPUT / 'report.json').read_text())
        if not source_report['passed']:
            raise ValueError('Input probe did not pass')
        report['input_report_sha256'] = hashlib.sha256((INPUT / 'report.json').read_bytes()).hexdigest()
        execute([RUSTC, '-Vv'], 'rustc.txt')
        execute([OBJDUMP, '--version'], 'objdump.txt')
        for case, (family, integer, result, argument) in CASES.items():
            for variant in ['original', 'candidate']:
                path = INPUT / f'{family}-{variant}.rs'
                if hashlib.sha256(path.read_bytes()).hexdigest() != source_report['artifacts_sha256'][path.name]:
                    raise ValueError('Input snippet hash mismatch')
                parameters = f'value: {integer}'
                if argument == 'alignment':
                    parameters += f', alignment: {integer}'
                aligned = '#[repr(align(16))]\nstruct Aligned;\n' if case == 'cpu_type16' else ''
                source = ('#![no_std]\n' + path.read_text() + '\n' + aligned
                          + f'#[unsafe(no_mangle)]\npub fn evaluate({parameters}) -> {result} {{\n'
                          + f'    align_up(value, {argument})\n}}\n')
                source_path = evidence / f'{case}-{variant}.rs'
                source_path.write_text(source)
                for target in TARGETS:
                    name = f'{target}-{case}-{variant}'
                    obj = work / (name + '.o')
                    execute([RUSTC, '--edition=2024', '--crate-type=lib', '--crate-name=probe',
                             '--target', target, '-Copt-level=3', '-Cpanic=abort', '-Cdebug-assertions=no',
                             '-Ccodegen-units=1', '--emit=obj', source_path, '-o', obj], name + '-compile.log')
                    execute([OBJDUMP, '--disassemble-symbols=evaluate', '--no-show-raw-insn',
                             '--no-leading-addr', '--no-leading-headers', obj], name + '.disasm')
            for target in TARGETS:
                original = (evidence / f'{target}-{case}-original.disasm').read_text()
                candidate = (evidence / f'{target}-{case}-candidate.disasm').read_text()
                original_body = instructions(original)
                candidate_body = instructions(candidate)
                report['pairs'].append({'target': target, 'case': case,
                                        'normalized_instructions_identical': original_body == candidate_body,
                                        'original_instruction_lines': len(original_body),
                                        'candidate_instruction_lines': len(candidate_body)})
        report['passed'] = True
    except Exception as error:
        report['error'] = str(error)
    finally:
        report['artifacts_sha256'] = {path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                                    for path in sorted(evidence.iterdir()) if path.is_file()}
        (evidence / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'passed': report['passed'], 'error': report.get('error'), 'pairs': report['pairs']}))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
