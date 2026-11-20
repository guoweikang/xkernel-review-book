import argparse
import hashlib
import itertools
import json
from pathlib import Path
import shutil
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / 'research/evidence/runs/2026-11-05-rust-baseline-corpus-01'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', required=True)
    args = parser.parse_args()
    RUN = ROOT / 'research/evidence/runs' / args.run
    RUN.mkdir(exist_ok=False)
    units = json.loads((CORPUS / 'units.json').read_text())
    selected = [unit for unit in units if unit['path'] == 'fs/kvfs/src/path.rs' and unit['name'] in ('parent', 'file_name')]
    assert len(selected) == 2
    methods = []
    with zipfile.ZipFile(CORPUS / 'units.zip') as archive:
        for unit in selected:
            data = archive.read(unit['entry'])
            assert digest(data) == unit['sha256']
            methods.append(data.decode())
    original = "pub struct Pathname<'a> { inner: &'a str }\nimpl<'a> Pathname<'a> {\npub fn new(input: &'a str) -> Self { Self { inner: input } }\npub fn as_str(&self) -> &'a str { self.inner }\n" + '\n'.join(methods) + '\n}\n'
    (RUN / 'original.rs').write_text(original)
    shutil.copyfile(ROOT / 'scripts/path_scanner_fixture.rs', RUN / 'fixture.rs')
    shutil.copyfile(Path(__file__), RUN / 'runner.py')
    alphabet = ['/', '.', 'a', '中', '🙂', '\0', '\\', 'e\u0301']
    generated = [''.join(parts) for size in range(6) for parts in itertools.product(alphabet, repeat=size)]
    extra = ['a/b/.', 'a/..', 'a//b///', '///a', '目录/文件/', 'a/././', 'a/../.', '/../', '//./a//', 'e\u0301/中/e\u0301/', 'a' * 8192, '/' * 8192, 'a/./' * 2048]
    inputs = list(dict.fromkeys(generated + extra))
    payload = ''.join(value.encode().hex() + '\n' for value in inputs).encode()
    (RUN / 'inputs.hex').write_bytes(payload)
    compiler = shutil.which('rustc')
    version = subprocess.check_output([compiler, '-vV'], text=True)
    manifest = {'source_commit': '7e3ac94431a0dbb376d2fc8d85098deeff1bba09', 'units': selected, 'compiler': version, 'alphabet': alphabet, 'max_fragments': 5, 'generated_sequences': len(generated), 'unique_inputs': len(inputs), 'additional_unique': len(inputs) - len(set(generated)), 'inputs_sha256': digest(payload), 'fixture_sha256': digest((RUN / 'fixture.rs').read_bytes()), 'original_sha256': digest(original.encode()), 'protocol': 'Original functions unchanged in minimal wrapper; compare None/content/borrowed byte offsets; debug/release twice; nonzero process status retains panic/failure; original is compatibility oracle, not specification.', 'controls': ['After trailing-dot skipping, reject both dot and dotdot before parent policy', 'Trim all trailing slashes from computed parent, including root'], 'limits': ['Finite UTF-8 domain', 'No kernel integration', 'No performance claim', 'Hand-designed prototype and two mutants, not automatic detection or mutation score generalization']}
    (RUN / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    build = ROOT / '.build' / args.run
    build.mkdir(parents=True, exist_ok=True)
    outcomes = []
    for profile, flags in [('debug', []), ('release', ['-O'])]:
        binary = build / profile
        command = [compiler, '--edition=2021', str(RUN / 'fixture.rs'), '-o', str(binary)] + flags
        (RUN / f'{profile}-command.json').write_text(json.dumps(command) + '\n')
        compiled = subprocess.run(command, capture_output=True)
        (RUN / f'{profile}-compile.log').write_bytes(compiled.stdout + compiled.stderr)
        compiled.check_returncode()
        (RUN / f'{profile}-binary.sha256').write_text(digest(binary.read_bytes()) + '\n')
        for repeat in range(2):
            result = subprocess.run([str(binary)], input=payload, capture_output=True)
            stem = f'{profile}-{repeat}'
            (RUN / f'{stem}.tsv').write_bytes(result.stdout)
            (RUN / f'{stem}.stderr').write_bytes(result.stderr)
            result.check_returncode()
            rows = [line.split('\t') for line in result.stdout.decode().splitlines()]
            assert len(rows) == len(inputs)
            mismatches = [sum(row[3 + variant] == '1' for row in rows) for variant in range(3)]
            witnesses = [next(({'input': inputs[index], 'row': row} for index, row in enumerate(rows) if row[3 + variant] == '1'), None) for variant in range(3)]
            outcomes.append({'run': stem, 'rows': len(rows), 'sha256': digest(result.stdout), 'mismatches': mismatches, 'first_witnesses': witnesses})
    report = {'outcomes': outcomes, 'stable': len({entry['sha256'] for entry in outcomes}) == 1}
    (RUN / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(report, ensure_ascii=False, indent=2))
    assert report['stable']
    assert all(entry['mismatches'][0] == 0 and all(count > 0 for count in entry['mismatches'][1:]) for entry in outcomes)


if __name__ == '__main__':
    main()
