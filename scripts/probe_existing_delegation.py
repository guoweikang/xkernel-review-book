"""Bounded extracted-source control of existing narrow-to-wide conversion delegation."""

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
REVISION = '5464361169822b3dbd3956017083bf8bbf7a7c2e'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def block(source, marker):
    start = source.index(marker)
    opened = source.index('{', start)
    depth = 1
    cursor = opened + 1
    while depth:
        depth += (source[cursor] == '{') - (source[cursor] == '}')
        cursor += 1
    return source[start:cursor]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['prepare', 'execute'])
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    output = args.output
    local = ROOT / '.build/delegation-probe' / output.name
    if args.action == 'prepare':
        output.mkdir(parents=True, exist_ok=False)
        local.mkdir(parents=True, exist_ok=False)
        raw = subprocess.check_output(['git', '-C', '/root/codes/kvirtiodrivers', 'show',
                                       REVISION + ':src/transport/mod.rs'], timeout=30)
        source = raw.decode()
        enum = block(source, 'pub enum DeviceType {')
        implementations = [block(source, f'impl TryFrom<{kind}> for DeviceType {{') for kind in ('u32', 'u16', 'u8')]
        error = block(source, 'pub enum DeviceTypeError {').replace('    #[error("Invalid or unknown virtio device type {0}")]\n', '')
        extracted = '#[repr(u8)]\n#[derive(Debug, PartialEq)]\n' + enum
        extracted += '\n#[derive(Debug, PartialEq)]\n' + error + '\n' + '\n'.join(implementations)
        harness = '''
fn main() {
    for value in 0..=u16::MAX {
        assert_eq!(DeviceType::try_from(value), DeviceType::try_from(u32::from(value)));
    }
    for value in 0..=u8::MAX {
        assert_eq!(DeviceType::try_from(value), DeviceType::try_from(u32::from(value)));
    }
    println!("PASS: 65536 u16 and 256 u8 results equal u32 conversion, including errors");
}
'''
        (local / 'original.rs').write_bytes(raw)
        (local / 'probe.rs').write_text(extracted + harness)
        shutil.copyfile(__file__, output / 'runner.py')
        protocol = {'revision': REVISION, 'path': 'src/transport/mod.rs',
                    'original_sha256': sha(raw), 'probe_sha256': sha((local / 'probe.rs').read_bytes()),
                    'runner_sha256': sha(Path(__file__).read_bytes()), 'local_source': str(local),
                    'implementation_blocks_sha256': [sha(body.encode()) for body in implementations],
                    'adaptation': 'Original enum variants and all three impl blocks unchanged; error formatting derive/attribute omitted; minimal Debug/PartialEq derives and harness added.',
                    'arms': ['code', 'code_with_native_direct_docs', 'code_with_supplemented_behavior_docs'],
                    'native_direct_docs': 'No direct doc comments on the selected u8/u16 impl methods; broader module docs remain context, not erased.',
                    'supplemented_behavior_docs': 'Input: unsigned device number in the source integer type. Output: DeviceType for recognized values or an error retaining an unrecognized number. No allocation or device I/O.',
                    'document_basis': 'Researcher-derived from the same code; no independent normative information or pair/reuse label.',
                    'measurement': 'debug/release x two repeats, exhaustive narrow domains; static information comparison only, no retrieval or AI accuracy measurement.',
                    'stop': 'All four runs pass or retain failure; no code changes to pursue performance, no unrelated bug investigation.'}
        (output / 'protocol.json').write_text(json.dumps(protocol, indent=2) + '\n')
        return
    assert not (output / 'results.json').exists()
    protocol = json.loads((output / 'protocol.json').read_text())
    assert sha(Path(__file__).read_bytes()) == protocol['runner_sha256']
    assert sha((local / 'probe.rs').read_bytes()) == protocol['probe_sha256']
    assert sha((local / 'original.rs').read_bytes()) == protocol['original_sha256']
    results = []
    for mode, options in [('debug', []), ('release', ['-O'])]:
        command = ['rustc', '--edition=2021', *options, str(local / 'probe.rs'), '-o', str(local / mode)]
        compilation = subprocess.run(command, capture_output=True, text=True, timeout=60)
        (output / f'{mode}-build.log').write_text(compilation.stdout + compilation.stderr)
        compilation.check_returncode()
        for repeat in range(2):
            run = subprocess.run([str(local / mode)], capture_output=True, text=True, timeout=20)
            (output / f'{mode}-{repeat}.log').write_text(run.stdout + run.stderr)
            results.append({'mode': mode, 'repeat': repeat, 'exit_code': run.returncode, 'stdout': run.stdout,
                            'command': command, 'binary_sha256': sha((local / mode).read_bytes())})
    (output / 'results.json').write_text(json.dumps({'rustc': subprocess.check_output(['rustc', '--version'], text=True).strip(),
        'runs': results, 'independent_normative_doc_information': False, 'retrieval_effect_measured': False}, indent=2) + '\n')
    assert all(row['exit_code'] == 0 and 'PASS: 65536' in row['stdout'] for row in results)
    print('PASS: 4 extracted-source executions; shared u32 conversion preserved across narrow domains; no retrieval effect claim')


if __name__ == '__main__':
    main()
