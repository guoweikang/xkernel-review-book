"""Separate relation labels and freeze external-source inventory, without execution."""

import argparse
import hashlib
import itertools
import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def relations(trace):
    observations = {}
    for line in trace.splitlines():
        identity, value, result = line.split(',')
        domain = observations.setdefault(identity, {})
        if int(value) in domain:
            raise ValueError('Duplicate observation')
        domain[int(value)] = int(result)
    if not observations or any(set(values) != set(range(256)) for values in observations.values()):
        raise ValueError('Incomplete domain')
    rows = []
    for left, right in itertools.combinations(sorted(observations), 2):
        differences = [value for value in range(256) if observations[left][value] != observations[right][value]]
        witness = None
        if differences:
            value = differences[0]
            witness = {'input': value, 'outputs': [observations[left][value], observations[right][value]]}
        rows.append({'pair': [left, right], 'scope': 'u16 input 0..255, scalar output only',
                     'finite_output_equivalence': {'label': 'negative' if differences else 'positive',
                                                   'witness': witness, 'basis': 'replayed_execution'},
                     'local_mechanism_sharing': {'label': 'unknown', 'missing': 'boundary/adapters/preservation evidence'},
                     'responsibility_placement': {'label': 'not_assessed', 'missing': 'owner/normative source'},
                     'optimization_benefit': 'unmeasured'})
    return rows


def git(repo, *arguments):
    return subprocess.check_output(['git', '-C', str(repo), *arguments], timeout=60)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    output = args.output
    output.mkdir(parents=True, exist_ok=False)
    sources = {'protocol.json': ROOT / 'research/protocols/relation-validation-v1.json',
               'trace.csv': ROOT / 'research/evidence/runs/2026-11-16-document-controls-01/trace-0.csv',
               'xkernel-units.json': ROOT / 'research/evidence/runs/2026-11-05-rust-baseline-corpus-01/units.json',
               'runner.py': Path(__file__)}
    for name, path in sources.items():
        shutil.copyfile(path, output / name)
    dump(output / 'freeze.json', {name: sha((output / name).read_bytes()) for name in sources})
    protocol = json.loads((output / 'protocol.json').read_text())
    rows = relations((output / 'trace.csv').read_text())
    dump(output / 'relation-cards.json', rows)
    source_hashes = {item['source_sha256'] for item in json.loads((output / 'xkernel-units.json').read_text())}
    reports = []
    for entry in protocol['repositories']:
        repo, revision = Path(entry['path']), entry['revision']
        assert git(repo, 'rev-parse', revision + '^{commit}').decode().strip() == revision
        tree = git(repo, 'ls-tree', '-rz', '--full-tree', revision)
        files = []
        license_paths = []
        for record in tree.split(b'\0'):
            if not record:
                continue
            header, path_bytes = record.split(b'\t', 1)
            mode, kind, blob = header.decode().split()
            path = path_bytes.decode()
            if Path(path).name.lower().startswith(('license', 'copying')):
                license_paths.append(path)
            if not path.endswith('.rs') or kind != 'blob' or mode not in ('100644', '100755'):
                continue
            content = git(repo, 'cat-file', 'blob', blob)
            checksum = sha(content)
            order = sha(('relation-validation-v1:' + revision + ':' + path).encode())
            files.append({'path': path, 'blob': blob, 'sha256': checksum, 'bytes': len(content),
                          'order': order, 'exact_xkernel_source_match': checksum in source_hashes})
        files.sort(key=lambda item: item['order'])
        reports.append({'repository': str(repo), 'revision': revision,
                        'rust_files': len(files), 'files': files, 'selected_paths': [item['path'] for item in files[:4]],
                        'exact_matches': sum(item['exact_xkernel_source_match'] for item in files),
                        'license_paths_not_reviewed': license_paths,
                        'scope': 'Committed tree only, working tree ignored; Rust blobs hashed, not semantically adjudicated.',
                        'lineage': 'pending', 'prior_exposure': 'unknown', 'split': 'unassigned',
                        'independent_test_eligible': False})
    dump(output / 'source-inventory.json', reports)
    summary = {'finite_positive': sum(row['finite_output_equivalence']['label'] == 'positive' for row in rows),
               'finite_negative': sum(row['finite_output_equivalence']['label'] == 'negative' for row in rows),
               'mechanism_unknown': len(rows), 'responsibility_not_assessed': len(rows),
               'source_files': sum(report['rust_files'] for report in reports),
               'selected_files': sum(len(report['selected_paths']) for report in reports),
               'independent_test_cases': 0, 'new_rust_executions': 0}
    dump(output / 'summary.json', summary)
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
