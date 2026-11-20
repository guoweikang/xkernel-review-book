import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tomllib
import zipfile


ROOT = Path(__file__).resolve().parents[1]


def digest(data):
    return hashlib.sha256(data).hexdigest()


def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', required=True)
    args = parser.parse_args()
    run = ROOT / 'research/evidence/runs' / args.run
    run.mkdir(exist_ok=False)
    original = ROOT / 'research/evidence/originals' / args.run
    original.mkdir(exist_ok=False)
    protocol_path = ROOT / 'research/protocols/rust-standard-source-inventory-v1.json'
    shutil.copyfile(protocol_path, run / 'protocol.json')
    shutil.copyfile(__file__, run / 'runner.py')
    version = subprocess.check_output(['rustc', '+1.95.0', '-Vv'], text=True)
    sysroot = Path(subprocess.check_output(['rustc', '+1.95.0', '--print', 'sysroot'], text=True).strip())
    source = sysroot / 'lib/rustlib/src/rust'
    installed_manifest = sysroot / 'lib/rustlib/manifest-rust-src'
    (run / 'rustc-version.txt').write_text(version)
    shutil.copyfile(installed_manifest, run / 'installed-manifest.txt')
    old_path = ROOT / 'research/evidence/runs/2026-11-05-rust-baseline-corpus-01/units.json'
    old = {row['source_sha256'] for row in json.loads(old_path.read_text())}
    dump(run / 'freeze.json', {'protocol': digest(protocol_path.read_bytes()), 'runner': digest(Path(__file__).read_bytes()), 'sysroot': str(sysroot), 'installed_manifest': digest(installed_manifest.read_bytes()), 'old_units': digest(old_path.read_bytes()), 'upstream_source_identity': 'not_verified'})
    records, licenses = [], {}
    archive_path = original / 'core-alloc.zip'
    manifest_lines = set(installed_manifest.read_text().splitlines())
    with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as archive:
        for package in ('core', 'alloc'):
            folder = source / 'library' / package
            metadata = folder / 'Cargo.toml'
            licenses[package] = tomllib.loads(metadata.read_text())['package']['license']
            for path in sorted(list((folder / 'src').rglob('*.rs')) + [metadata]):
                assert path.is_file() and not path.is_symlink(), path
                relative = str(path.relative_to(source))
                installed_relative = 'file:' + str(path.relative_to(sysroot))
                assert installed_relative in manifest_lines, installed_relative
                data = path.read_bytes()
                identity = digest(data)
                header = f'blob {len(data)}\0'.encode()
                records.append({'path': relative, 'package': package, 'bytes': len(data), 'sha256': identity, 'git_blob_sha1': hashlib.sha1(header + data).hexdigest(), 'exact_old_source_match': identity in old, 'prior_exposure': 'unknown', 'independent_test_eligible': False})
                archive.writestr(zipfile.ZipInfo(relative, (1980, 1, 1, 0, 0, 0)), data, compress_type=zipfile.ZIP_DEFLATED)
    with zipfile.ZipFile(archive_path) as archive:
        assert set(archive.namelist()) == {row['path'] for row in records}
        for row in records:
            assert digest(archive.read(row['path'])) == row['sha256']
    dump(run / 'inventory.json', records)
    report = {'files': len(records), 'rust_files': sum(row['path'].endswith('.rs') for row in records), 'packages': {package: sum(row['package'] == package for row in records) for package in licenses}, 'bytes': sum(row['bytes'] for row in records), 'license_declarations': licenses, 'exact_old_source_matches': sum(row['exact_old_source_match'] for row in records), 'eligible_test_files': 0, 'upstream_identity_verified': False, 'archive': str(archive_path.relative_to(ROOT / 'research/evidence')), 'archive_sha256': digest(archive_path.read_bytes()), 'archive_bytes': archive_path.stat().st_size, 'artifacts_sha256': {path.name: digest(path.read_bytes()) for path in run.iterdir() if path.is_file()}}
    dump(run / 'report.json', report)
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
