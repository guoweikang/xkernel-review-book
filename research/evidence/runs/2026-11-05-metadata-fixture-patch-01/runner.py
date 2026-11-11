"""Prepare a test-only research patch; verify edits, not kernel behavior."""

import argparse
import difflib
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess


ROOT = Path(__file__).resolve().parents[1]
REVISION = '7e3ac94431a0dbb376d2fc8d85098deeff1bba09'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, required=True)
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9_-]+', args.run_id):
        parser.error('Invalid run ID')
    evidence = ROOT / 'research/evidence/runs' / args.run_id
    work = ROOT / '.build/metadata-fixture' / args.run_id
    if evidence.exists() or work.exists():
        parser.error('Run exists')
    evidence.mkdir(parents=True)
    work.mkdir(parents=True)
    report = {'passed': False, 'revision': REVISION, 'kernel_modified': False,
              'rust_compilation': 'not_run', 'kernel_tests': 'not_run', 'net_benefit': 'unverified'}
    shutil.copy2(__file__, evidence / 'runner.py')
    try:
        candidate_path = ROOT / 'research/evidence/runs/2026-11-05-rust-scc-01/candidates.json'
        source_report = json.loads((candidate_path.parent / 'report.json').read_text())
        if hashlib.sha256(candidate_path.read_bytes()).hexdigest() != source_report['artifacts_sha256']['candidates.json']:
            raise ValueError('Candidate input changed')
        pairs = json.loads(candidate_path.read_text())
        pair = next(pair for pair in pairs if pair['file_ids'] == [1571, 1732])
        report['candidate_sha256'] = hashlib.sha256(candidate_path.read_bytes()).hexdigest()
        original = {}
        proposed = {}
        expressions = []
        for member in pair['members']:
            path = member['path']
            content = subprocess.check_output(['git', '-C', str(args.repo), 'show', f'{REVISION}:{path}'])
            if hashlib.sha256(content).hexdigest() != member['source_sha256']:
                raise ValueError('Source identity mismatch')
            begin, end = member['range']
            snippet = content[begin:end].decode()
            if hashlib.sha256(content[begin:end]).hexdigest() != member['sha256']:
                raise ValueError('Unit identity mismatch')
            match = re.search(r'Ok\((Metadata \{.*\})\)\s*\}', snippet, re.DOTALL)
            if not match or match.group(1).count('self.inode') != 1:
                raise ValueError('Unexpected metadata constructor')
            expression = match.group(1)
            expressions.append(expression)
            replacement = 'crate::test_support::directory_metadata(self.inode)'
            adapted = snippet[:match.start(1)] + replacement + snippet[match.end(1):]
            if adapted.replace(replacement, expression) != snippet:
                raise ValueError('Unexpected changes outside constructor expression')
            original[path] = content.decode()
            proposed[path] = content[:begin].decode() + adapted + content[end:].decode()
        if expressions[0] != expressions[1]:
            raise ValueError('Constructors are not identical')
        fields = re.findall(r'^\s+(\w+):', expressions[0], re.MULTILINE)
        if len(fields) != len(set(fields)) or len(fields) != 13:
            raise ValueError('Unexpected field inventory')
        expression = expressions[0].replace('self.inode', 'inode')
        lines = expression.splitlines()
        expression = lines[0] + '\n' + '\n'.join(line[4:] for line in lines[1:])
        support = ('use ktime_types::SystemTime;\n\n'
                   'use crate::{Metadata, NodePermission, NodeType};\n\n'
                   'pub(crate) fn directory_metadata(inode: u64) -> Metadata {\n'
                   '    ' + expression + '\n}\n')
        support_path = 'fs/kvfs/ut-tests/support.rs'
        if subprocess.run(['git', '-C', str(args.repo), 'cat-file', '-e', f'{REVISION}:{support_path}'],
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0:
            raise ValueError('Proposed support path already exists')
        proposed[support_path] = support
        library_path = 'fs/kvfs/src/lib.rs'
        original[library_path] = subprocess.check_output(['git', '-C', str(args.repo), 'show', f'{REVISION}:{library_path}']).decode()
        if 'mod test_support' in original[library_path]:
            raise ValueError('Support module already exists')
        proposed[library_path] = original[library_path] + '\nunittest::path_mod_test!(test_support, "../ut-tests/support.rs");\n'
        patch = []
        for path in sorted(proposed):
            before = original.get(path, '')
            patch.extend(difflib.unified_diff(before.splitlines(True), proposed[path].splitlines(True),
                                             fromfile='a/' + path if path in original else '/dev/null', tofile='b/' + path))
            if path in original:
                target = work / path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(before)
            target = evidence / 'proposed' / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(proposed[path])
        patch_path = evidence / 'candidate.patch'
        patch_path.write_text(''.join(patch))
        environment = {**os.environ, 'GIT_CEILING_DIRECTORIES': str(work.parent)}
        commands = [['git', 'apply', '--check', str(patch_path)], ['git', 'apply', str(patch_path)]]
        report['commands'] = commands
        with (evidence / 'patch-check.log').open('w') as log:
            for command in commands:
                subprocess.run(command, cwd=work, env=environment, stdout=log, stderr=subprocess.STDOUT, check=True)
        if any((work / path).read_text() != content for path, content in proposed.items()):
            raise ValueError('Applied patch differs from proposal')
        report.update({'passed': True, 'fields_preserved': fields, 'changed_paths': sorted(proposed),
                       'original_constructor_sites': 2, 'proposed_constructor_sites': 1,
                       'new_module_gate': 'existing path_mod_test macro cfg(unittest)',
                       'validation': 'exact constructor identity, local substitution reversibility, patch applies to isolated fixed-source copies'})
    except Exception as error:
        report['error'] = str(error)
    finally:
        report['artifacts_sha256'] = {str(path.relative_to(evidence)): hashlib.sha256(path.read_bytes()).hexdigest()
                                    for path in sorted(evidence.rglob('*')) if path.is_file()}
        (evidence / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
