"""Compile fixed extracted constructors under explicit cfg assignments."""

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def digest(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', required=True)
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    assert args.run_id and all(character.isalnum() or character in '-_' for character in args.run_id)
    protocol_path = ROOT / 'research/protocols/cfg-membership-v1.json'
    protocol = json.loads(protocol_path.read_text())
    output = ROOT / 'research/evidence/runs' / args.run_id
    output.mkdir()
    sources = {}
    for path in [protocol['source'], 'task/kspin/Cargo.toml', 'api/kfeat/Cargo.toml',
                 'task/ktask/Kconfig.diagnostics', 'xtask/xconfig/src/build_config.rs',
                 'xtask/xconfig/src/cli/gen_cargo.rs']:
        data = subprocess.check_output(['git', '-C', args.repo, 'show', protocol['revision'] + ':' + path])
        target = output / 'sources' / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        sources[path] = digest(data)
    source = (output / 'sources' / protocol['source']).read_text()
    struct_start = source.index('pub struct SpinLock<')
    struct_end = source.index('\n}', struct_start) + 2
    impl_start = source.index('impl<G: BaseGuard, T> SpinLock<G, T> {')
    impl_end = source.index('\nimpl<G: BaseGuard, T: ?Sized>', impl_start)
    struct = source[struct_start:struct_end]
    implementation = source[impl_start:impl_end]
    disabled = '#[cfg(not(feature = "stats"))]'
    enabled = '#[cfg(feature = "stats")]'
    assert implementation.count(disabled) == 1 and implementation.count(enabled) == 2
    prefix = '''use std::{cell::UnsafeCell, marker::PhantomData};
#[cfg(feature = "smp")]
use std::sync::atomic::{AtomicBool, Ordering};
pub trait BaseGuard {}
struct ProbeGuard;
impl BaseGuard for ProbeGuard {}
mod klockstat {
    pub struct LockClassStats;
    pub static NOOP_CLASS: LockClassStats = LockClassStats;
}
'''
    suffix = '''
fn main() {
    let lock = SpinLock::<ProbeGuard, u32>::new(42);
    #[cfg(feature = "smp")]
    assert!(!lock.flag.load(Ordering::Relaxed));
    #[cfg(feature = "stats")]
    assert!(std::ptr::eq(lock.stats, &klockstat::NOOP_CLASS));
    assert_eq!(lock.into_inner(), 42);
    println!("constructor assertions passed");
}
'''
    variants = {
        'original': implementation,
        'both_enabled': implementation.replace(disabled, '#[cfg(all())]', 1).replace(enabled, '#[cfg(all())]', 1),
        'both_disabled': implementation.replace(disabled, '#[cfg(any())]', 1).replace(enabled, '#[cfg(any())]', 1),
    }
    compiler = ['rustup', 'run', protocol['toolchain'], 'rustc']
    manifest = {'scope': 'extracted constructor harness with explicit stubs',
                'sources': sources, 'protocol_sha256': digest(protocol_path.read_bytes()),
                'runner_sha256': digest(Path(__file__).read_bytes()),
                'compiler': subprocess.check_output(compiler + ['-vV'], text=True),
                'ranges': {'struct': [struct_start, struct_end], 'impl': [impl_start, impl_end]}}
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    shutil.copy2(protocol_path, output / 'protocol.json')
    shutil.copy2(__file__, output / 'runner.py')
    records = []
    for name, body in variants.items():
        (output / (name + '.rs')).write_text(prefix + struct + '\n' + body + suffix)
    with tempfile.TemporaryDirectory(prefix='cfg-membership-') as temporary:
        for repeat in range(1, protocol['repeats'] + 1):
            for name in protocol['variants']:
                for features in protocol['assignments']:
                    identity = f'{name}-{"_".join(features) or "none"}-{repeat}'
                    executable = Path(temporary) / identity
                    command = compiler + ['--edition=2024', str(output / (name + '.rs')), '-o', str(executable)]
                    for feature in features:
                        command += ['--cfg', f'feature="{feature}"']
                    result = subprocess.run(command, capture_output=True, text=True, timeout=30)
                    (output / (identity + '.stderr')).write_text(result.stderr)
                    record = {'id': identity, 'repeat': repeat, 'variant': name, 'features': features,
                              'command': command, 'compile_exit': result.returncode}
                    if name == 'original':
                        assert result.returncode == 0, identity
                        run = subprocess.run([str(executable)], capture_output=True, text=True, timeout=10)
                        record.update(execute_exit=run.returncode, stdout=run.stdout, stderr=run.stderr)
                        assert run.returncode == 0 and run.stdout == 'constructor assertions passed\n'
                    else:
                        expected = 'E0592' if name == 'both_enabled' else 'E0599'
                        assert result.returncode != 0 and expected in result.stderr, identity
                        record['expected_error'] = expected
                    records.append(record)
                    (output / 'executions.json').write_text(json.dumps(records, indent=2) + '\n')
    for first, second in zip(records[:12], records[12:]):
        for key in ['variant', 'features', 'compile_exit', 'execute_exit', 'stdout', 'expected_error']:
            assert first.get(key) == second.get(key)
    report = {'scope': manifest['scope'], 'compiles': len(records),
              'original_executions': 8, 'expected_compile_failures': 16,
              'repeat_outcomes_equal': True,
              'claim': 'exact source constructor gates select one new per abstract stats/smp assignment; not project config validation',
              'artifact_sha256': {str(path.relative_to(output)): digest(path.read_bytes()) for path in sorted(output.rglob('*')) if path.is_file()}}
    (output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({key: value for key, value in report.items() if key != 'artifact_sha256'}, indent=2))


if __name__ == '__main__':
    main()
