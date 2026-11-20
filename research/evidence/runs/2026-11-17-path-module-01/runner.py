import argparse
import difflib
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / 'research/evidence/runs/2026-11-05-rust-baseline-corpus-01'
PREVIOUS = ROOT / 'research/evidence/runs/2026-11-17-path-scanner-03'

HELPER = '''    fn final_component_bounds(&self) -> Option<(usize, usize)> {
        let mut end = self.inner.len();
        loop {
            while end > 0 && self.inner.as_bytes()[end - 1] == b'/' {
                end -= 1;
            }
            if end == 0 {
                return None;
            }
            let start = self.inner[..end].rfind('/').map(|index| index + 1).unwrap_or(0);
            if &self.inner[start..end] == "." && start > 0 {
                end = start - 1;
                continue;
            }
            return Some((start, end));
        }
    }

'''
METHODS = {
    'file_name': '''fn file_name(&self) -> Option<&'a str> {
        let (start, end) = self.final_component_bounds()?;
        match &self.inner[start..end] {
            "." | ".." => None,
            name => Some(name),
        }
    }''',
    'parent': '''fn parent(&self) -> Option<Pathname<'a>> {
        let (start, _) = self.final_component_bounds()?;
        let parent_end = if start == 0 { 0 } else if start == 1 { 1 } else { start - 1 };
        Some(Pathname::new(&self.inner[..parent_end]))
    }''',
}

HARNESS = r'''extern crate alloc;
#[path = "original/src/path.rs"]
mod original;
#[path = "candidate/src/path.rs"]
mod candidate;
mod original_ut { include!("original/ut-adapted.rs"); }
mod candidate_ut { include!("candidate/ut-adapted.rs"); }

#[test]
fn differential_callers() {
    let mut count = 0;
    for (index, line) in include_str!("inputs.hex").lines().enumerate() {
        let bytes: Vec<u8> = (0..line.len()).step_by(2)
            .map(|offset| u8::from_str_radix(&line[offset..offset + 2], 16).unwrap()).collect();
        let input = String::from_utf8(bytes).unwrap();
        let before = original::Pathname::new(&input);
        let after = candidate::Pathname::new(&input);
        assert_eq!(before.file_name(), after.file_name(), "file input {index}");
        assert_eq!(before.parent().map(|value| value.as_str()), after.parent().map(|value| value.as_str()), "parent input {index}");
        let normalized_before = before.normalize().map(|value| value.as_str().to_owned());
        let normalized_after = after.normalize().map(|value| value.as_str().to_owned());
        assert_eq!(normalized_before, normalized_after, "normalize input {index}");
        let mut buffer_before = original::PathBuf::from(input.as_str());
        let mut buffer_after = candidate::PathBuf::from(input.as_str());
        let mut trace = Vec::new();
        let mut terminated = false;
        for _step in 0..=input.len() + 1 {
            let popped_before = buffer_before.pop();
            let popped_after = buffer_after.pop();
            assert_eq!(popped_before, popped_after, "pop bool input {index}");
            assert_eq!(buffer_before.as_str(), buffer_after.as_str(), "pop state input {index}");
            trace.push((popped_before, buffer_before.as_str().to_owned()));
            if !popped_before {
                terminated = true;
                break;
            }
        }
        assert!(terminated, "pop did not terminate for input {index}");
        println!("CASE {index}\t{normalized_before:?}\t{trace:?}");
        count += 1;
    }
    assert_eq!(count, 37459);
}
'''


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', required=True)
    args = parser.parse_args()
    run = ROOT / 'research/evidence/runs' / args.run
    run.mkdir(exist_ok=False)
    shutil.copyfile(__file__, run / 'runner.py')
    with zipfile.ZipFile(CORPUS / 'sources.zip') as archive:
        original = archive.read('fs/kvfs/src/path.rs')
        host = archive.read('fs/kvfs/tests/host/path.rs')
        unit_tests = archive.read('fs/kvfs/ut-tests/path.rs')
    candidate = original.decode()
    units = json.loads((CORPUS / 'units.json').read_text())
    with zipfile.ZipFile(CORPUS / 'units.zip') as archive:
        for unit in units:
            if unit['path'] == 'fs/kvfs/src/path.rs' and unit['name'] in METHODS:
                snippet = archive.read(unit['entry'])
                assert sha(snippet) == unit['sha256']
                assert sha(original) == unit['source_sha256']
                assert candidate.count(snippet.decode()) == 1
                candidate = candidate.replace(snippet.decode(), METHODS[unit['name']])
    anchor = '    /// Returns the final component of the pathname, if there is one.\n'
    assert candidate.count(anchor) == 1
    candidate = candidate.replace(anchor, HELPER + anchor)
    for label, content in [('original', original), ('candidate', candidate.encode())]:
        (run / label / 'src').mkdir(parents=True)
        (run / label / 'tests/host').mkdir(parents=True)
        (run / label / 'src/path.rs').write_bytes(content)
        (run / label / 'tests/host/path.rs').write_bytes(host)
        (run / label / 'ut-original.rs').write_bytes(unit_tests)
        adapted = unit_tests.decode().replace('use unittest::{assert, assert_eq, def_test};', '').replace('#[def_test]', '#[test]').replace('use super::*;', f'use crate::{label}::*;')
        (run / label / 'ut-adapted.rs').write_text(adapted)
    shutil.copyfile(PREVIOUS / 'inputs.hex', run / 'inputs.hex')
    (run / 'harness.rs').write_text(HARNESS)
    rustc = shutil.which('rustc')
    rustfmt = shutil.which('rustfmt')
    for label in ('original', 'candidate'):
        target = run / f'{label}-formatted.rs'
        shutil.copyfile(run / label / 'src/path.rs', target)
        result = subprocess.run([rustfmt, '--edition', '2021', '--config', 'skip_children=true', str(target)], capture_output=True)
        (run / f'{label}-format.log').write_bytes(result.stdout + result.stderr)
        result.check_returncode()
    formatted = {label: (run / f'{label}-formatted.rs').read_text() for label in ('original', 'candidate')}
    delta = ''.join(difflib.unified_diff(formatted['original'].splitlines(True), formatted['candidate'].splitlines(True), fromfile='a/fs/kvfs/src/path.rs', tofile='b/fs/kvfs/src/path.rs'))
    (run / 'candidate.diff').write_text(delta)
    manifest = {'question': 'Does local extraction preserve the complete path module callers on the frozen finite domain?', 'source_commit': '7e3ac94431a0dbb376d2fc8d85098deeff1bba09', 'compiler': subprocess.check_output([rustc, '-vV'], text=True), 'formatter': subprocess.check_output([rustfmt, '--version'], text=True), 'inputs': 37459, 'profiles': ['debug', 'release'], 'repeats': 2, 'checks': ['existing host test unchanged', 'two UT functions adapted to host test attributes', 'file_name and parent outputs', 'normalize Option and content', 'repeated pop bool and content through first false'], 'limits': ['No kernel cfg(unittest) execution', 'Host alloc and test harness', 'No timing or maintenance benefit measurement', 'No external semantic oracle'], 'files': {str(path.relative_to(run)): sha(path.read_bytes()) for path in sorted(run.rglob('*')) if path.is_file()}}
    (run / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    build = ROOT / '.build' / args.run
    build.mkdir(parents=True, exist_ok=True)
    outcomes = []
    for profile, flags in [('debug', []), ('release', ['-O'])]:
        binary = build / profile
        command = [rustc, '--edition=2021', '--test', str(run / 'harness.rs'), '-o', str(binary)] + flags
        (run / f'{profile}-command.json').write_text(json.dumps(command) + '\n')
        result = subprocess.run(command, capture_output=True)
        (run / f'{profile}-compile.log').write_bytes(result.stdout + result.stderr)
        result.check_returncode()
        (run / f'{profile}-binary.sha256').write_text(sha(binary.read_bytes()) + '\n')
        for repeat in range(2):
            result = subprocess.run([str(binary), '--nocapture', '--test-threads=1'], capture_output=True)
            stem = f'{profile}-{repeat}'
            (run / f'{stem}.stdout').write_bytes(result.stdout)
            (run / f'{stem}.stderr').write_bytes(result.stderr)
            result.check_returncode()
            lines = result.stdout.decode().splitlines()
            cases = '\n'.join(line[line.index('CASE '):] for line in lines if 'CASE ' in line)
            assert len(cases.splitlines()) == 37459
            assert '7 passed; 0 failed' in result.stdout.decode()
            outcomes.append({'run': stem, 'cases_sha256': sha(cases.encode()), 'cases': 37459, 'passed_tests': 7})
    costs = {label: {'lines': len(content.splitlines()), 'nonblank_lines': sum(bool(line.strip()) for line in content.splitlines())} for label, content in formatted.items()}
    report = {'outcomes': outcomes, 'stable': len({entry['cases_sha256'] for entry in outcomes}) == 1, 'whole_module_costs_same_formatter': costs, 'added_private_helpers': 1, 'helper_call_sites': 2, 'public_interface_changes': 0}
    (run / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    assert report['stable']
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
