import argparse
import difflib
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import tarfile
import time

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--run', required=True)
    args = parser.parse_args()
    source = args.source.resolve()
    assert source.name.startswith('xkernel-removal-event-')
    run = ROOT / 'research/evidence/runs' / args.run
    run.mkdir(exist_ok=False)
    protocol_path = ROOT / 'research/protocols/removal-event-factorial-v1.json'
    protocol = json.loads(protocol_path.read_text())
    parent = ROOT / 'research/evidence/runs/2026-11-16-pagecache-original-01'
    baseline = json.loads((parent / 'report.json').read_text())
    assert digest(source / 'source.tar') == baseline['source_archive_sha256']
    assert digest(source / '.config') == digest(parent / 'output.config')
    implementation_path = protocol['implementation']
    test_path = protocol['tests']
    with tarfile.open(source / 'source.tar') as archive:
        originals = {member.name: archive.extractfile(member).read() for member in archive if member.isfile()}
    allowed_changes = {implementation_path, test_path}

    def unexpected_changes(expected):
        return [name for name, content in originals.items() if not (source / name).is_file() or (source / name).read_bytes() != expected.get(name, content)]

    initial_changes = unexpected_changes({})
    assert set(initial_changes) <= allowed_changes, initial_changes
    original = originals[implementation_path].decode()
    old_tests = originals[test_path].decode()
    fixture = (ROOT / protocol['fixture']).read_text()
    observed_tests = old_tests + '\n' + fixture
    blocks = re.findall(r'removed = Some\((RemovedEntry \{.*?\n            \})\);', original, re.DOTALL)
    assert len(blocks) == 2 and blocks[0] == blocks[1]
    body = '\n'.join(line[8:] if line.startswith('        ') else line for line in blocks[0].splitlines())
    helper = '    fn snapshot_removed_entry(&self, name: &str, victim: &Dentry, victim_path: &Path) -> RemovedEntry {\n        ' + body + '\n    }\n\n'
    anchor = '    /// Unlinks like `Mount::unlink_with_pathname` and reports the victim.\n'
    assert original.count(anchor) == 1
    candidate = original.replace(anchor, helper + anchor).replace('removed = Some(' + blocks[0] + ');', 'removed = Some(self.snapshot_removed_entry(name, victim, &victim_path));')
    assert candidate.count('self.snapshot_removed_entry(name, victim, &victim_path)') == 2
    pattern = r'victim_nlink: Some\(\s*victim_path\s*\.getattr\(\)\s*\.map_or_else\(\|_\| victim_path.identity\(\).nlink, \|meta\| meta.nlink\),\s*\),'
    mutant, replacements = re.subn(pattern, 'victim_nlink: victim_path.getattr().ok().map(|meta| meta.nlink),', original)
    assert replacements == 2
    implementations = {'original': original, 'candidate': candidate, 'mutant': mutant}
    for label, content in implementations.items():
        (run / f'{label}.rs').write_text(content)
    (run / 'old-tests.rs').write_text(old_tests)
    (run / 'observed-tests.rs').write_text(observed_tests)
    (run / 'fixture.rs').write_text(fixture)
    (run / 'candidate.diff').write_text(''.join(difflib.unified_diff(original.splitlines(True), candidate.splitlines(True), fromfile='a/' + implementation_path, tofile='b/' + implementation_path)))
    shutil.copyfile(__file__, run / 'runner.py')
    shutil.copyfile(protocol_path, run / 'protocol.json')
    shutil.copyfile(source / '.config', run / 'input.config')
    frozen = {'source': str(source), 'archive_sha256': digest(source / 'source.tar'), 'initial_changes': initial_changes, 'initial_changed_hashes': {name: digest(source / name) for name in initial_changes}, 'files': {path.name: digest(path) for path in sorted(run.iterdir()) if path.is_file()}}
    (run / 'frozen-inputs.json').write_text(json.dumps(frozen, indent=2) + '\n')
    environment = dict(os.environ)
    environment.update({'RUSTUP_TOOLCHAIN': '1.95.0', 'CARGO_NET_OFFLINE': 'true', 'CARGO_BUILD_JOBS': '4', 'RUSTFLAGS': '', 'CARGO_ENCODED_RUSTFLAGS': '', 'GIT_CEILING_DIRECTORIES': '/tmp:/root/.tmp'})
    outcomes = []
    for condition in protocol['conditions']:
        cell = run / condition
        cell.mkdir()
        label, observation = condition.split('-')
        expected = {implementation_path: implementations[label].encode(), test_path: (observed_tests if observation == 'observed' else old_tests).encode()}
        for name, content in expected.items():
            (source / name).write_bytes(content)
        assert not unexpected_changes(expected)
        disk = source / ('research-' + args.run + '-' + condition + '.ext4')
        assert not disk.exists()
        with (cell / 'setup.log').open('wb') as log:
            subprocess.run(['truncate', '-s', '128M', str(disk)], stdout=log, stderr=subprocess.STDOUT, check=True)
            subprocess.run(['mkfs.ext4', '-F', '-O', '^metadata_csum,^64bit', str(disk)], stdout=log, stderr=subprocess.STDOUT, check=True)
        disk_before = digest(disk)
        command = ['make', 'unittest', 'UNITTEST_CRATE=kvfs', 'ACCEL=n', 'NET=n', 'BLK=y', 'VSOCK=n', 'SMP=2', 'MEM=1g', f'DISK_IMG={disk}']
        (cell / 'command.json').write_text(json.dumps(command) + '\n')
        started = time.monotonic()
        timed_out = False
        with (cell / 'run.log').open('wb') as log:
            process = subprocess.Popen(command, cwd=source, env=environment, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
            try:
                code = process.wait(timeout=protocol['limits']['seconds_per_condition'])
            except subprocess.TimeoutExpired:
                timed_out = True
                os.killpg(process.pid, signal.SIGKILL)
                code = process.wait()
        text = (cell / 'run.log').read_text(errors='replace')
        results = re.findall(r'RESULT\s+(\S+)\s+\.\.\.\s+(\S+)', text)
        report = {'condition': condition, 'exit_code': code, 'timeout': timed_out, 'seconds': round(time.monotonic() - started, 3), 'results': results, 'unexpected_source_changes': unexpected_changes(expected), 'configuration_unchanged': digest(source / '.config') == digest(run / 'input.config'), 'disk_before': disk_before, 'disk_after': digest(disk), 'files': {path.name: digest(path) for path in sorted(cell.iterdir()) if path.is_file()}}
        (cell / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
        outcomes.append(report)
        print(json.dumps({key: value for key, value in report.items() if key not in ('results', 'files')}) + f' tests={len(results)}', flush=True)
        (run / 'report.json').write_text(json.dumps({'outcomes': outcomes}, indent=2) + '\n')
        assert not report['unexpected_source_changes'] and report['configuration_unchanged']
        if condition == 'original-observed' and (code != 0 or not results or any(status != 'ok' for _name, status in results)):
            raise RuntimeError('Original observed condition failed; preserve and diagnose before interpreting other arms')
    print('Completed all frozen conditions', flush=True)


if __name__ == '__main__':
    main()
