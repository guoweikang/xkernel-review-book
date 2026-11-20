"""Check existing isolated kernel inputs before constructing cache transaction tests."""

import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tarfile


ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / 'research/evidence/runs'
RUN = RUNS / '2026-11-18-cache-transaction-preflight-01'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    RUN.mkdir(exist_ok=False)
    previous_path = RUNS / '2026-11-16-pagecache-original-01/report.json'
    previous = json.loads(previous_path.read_text())
    source = Path(previous['isolated_source'])
    archive_path = source / 'source.tar'
    protocol = {
        'question': 'Are the existing isolated fixed-revision kernel inputs intact for a new real-Dentry test fixture?',
        'revision': '7e3ac94431a0dbb376d2fc8d85098deeff1bba09',
        'candidate': 'call-subset-continuation-02/case-002, first retained hypothesis in frozen slot order',
        'source': str(source),
        'parent_report_sha256': digest(previous_path),
        'expected_archive_sha256': previous['source_archive_sha256'],
        'operations': 'Read-only archive/source/configuration comparison and executable discovery; no build, test or mutation',
        'stop': 'Any missing or changed input remains a recorded readiness gap; no repair or fallback to host model in this batch',
        'limits': 'Readiness does not establish runnable tests, kernel behavior, or refactoring equivalence',
    }
    (RUN / 'protocol.json').write_text(json.dumps(protocol, indent=2) + '\n')
    shutil.copyfile(__file__, RUN / 'runner.py')
    lookup = subprocess.run(
        ['python3', 'scripts/research_lookup.py', 'insert_cache', 'cache_lookup_candidate', 'kvfs-original', '--limit', '6'],
        cwd=ROOT, capture_output=True, text=True, check=False,
    )
    (RUN / 'lookup.json').write_text(lookup.stdout)
    (RUN / 'lookup.stderr').write_text(lookup.stderr)
    report = {'archive_exists': archive_path.is_file(), 'lookup_exit': lookup.returncode}
    report['archive_matches'] = archive_path.is_file() and digest(archive_path) == protocol['expected_archive_sha256']
    checked = 0
    changed = []
    if report['archive_matches']:
        with tarfile.open(archive_path) as archive:
            for member in archive:
                if not member.isfile():
                    continue
                checked += 1
                relative = Path(member.name)
                if relative.is_absolute() or '..' in relative.parts:
                    changed.append({'path': member.name, 'reason': 'unsafe archive path'})
                    continue
                target = source / relative
                expected = hashlib.sha256(archive.extractfile(member).read()).hexdigest()
                if not target.is_file() or target.is_symlink() or digest(target) != expected:
                    changed.append({'path': member.name, 'reason': 'missing, symlink or changed'})
    report.update({'source_files_checked': checked, 'source_differences': changed})
    expected_config = RUNS / '2026-11-16-pagecache-original-01/output.config'
    report['configuration_matches'] = (source / '.config').is_file() and digest(source / '.config') == digest(expected_config)
    report['executables'] = {name: shutil.which(name) for name in ['qemu-system-x86_64', 'make', 'rustup', 'mkfs.ext4']}
    report['inputs_ready'] = bool(report['archive_matches'] and checked and not changed and report['configuration_matches'] and all(report['executables'].values()))
    report['kernel_tests_executed'] = 0
    (RUN / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
