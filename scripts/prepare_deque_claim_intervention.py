import argparse
import hashlib
import json
from pathlib import Path
import shutil
import zipfile


ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def verify(run):
    report = json.loads((run / 'report.json').read_text())
    for name, expected in report['artifacts_sha256'].items():
        assert sha(run / name) == expected, name
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', required=True)
    args = parser.parse_args()
    run = ROOT / 'research/evidence/runs' / args.run
    run.mkdir(exist_ok=False)
    runs = ROOT / 'research/evidence/runs'
    source_run = runs / '2026-11-17-standard-mechanisms-01'
    witness_run = runs / '2026-11-17-deque-document-witness-01'
    verify(source_run)
    verify(witness_run)
    protocol = ROOT / 'research/protocols/deque-single-claim-intervention-v1.json'
    shutil.copyfile(protocol, run / 'protocol.json')
    shutil.copyfile(__file__, run / 'runner.py')
    archive_path = Path(json.loads((source_run / 'freeze.json').read_text())['archive'])
    assert sha(archive_path) == json.loads((source_run / 'freeze.json').read_text())['archive_sha256']
    dump(run / 'freeze.json', {'source_report': sha(source_run / 'report.json'), 'witness_report': sha(witness_run / 'report.json'), 'archive_sha256': sha(archive_path), 'protocol': sha(protocol), 'runner': sha(Path(__file__))})
    path = 'library/alloc/src/collections/vec_deque/mod.rs'
    file = next(row for row in json.loads((source_run / 'files.json').read_text()) if row['path'] == path)
    parsed = json.loads((source_run / file['parsed']).read_text())
    units = json.loads((source_run / 'units.json').read_text())
    observations = [json.loads(line) for line in (witness_run / 'debug-1.jsonl').read_text().splitlines()]
    with zipfile.ZipFile(archive_path) as archive:
        source = archive.read(path)
    assert hashlib.sha256(source).hexdigest() == file['source_sha256']
    inputs = run / 'inputs'
    inputs.mkdir()
    evidence = []
    for direction, endpoint in (('front', 'first'), ('back', 'last')):
        unit = next(row for row in units if row['path'] == path and row['name'] == f'pop_{direction}_if')
        syntax = parsed['units'][unit['syntax_index']]
        begin, end = unit['range']
        assert hashlib.sha256(source[begin:end]).hexdigest() == unit['sha256']
        common = [f'Examines the {endpoint} element of the deque.', 'On an empty deque, returns None without calling the predicate.', 'Otherwise the predicate receives a mutable reference to the inspected element.', 'If the predicate returns true, removes and returns the inspected element.', 'If the predicate returns false, returns None without removing an element.']
        sentences = ['On normal false return, changes the predicate made to the inspected element are retained.', 'On normal false return, the inspected element is guaranteed to be unchanged.']
        for index, sentence in enumerate(sentences):
            (inputs / f'{direction}-v{index}.txt').write_text('\n'.join(common + [sentence]) + '\n')
        left = (inputs / f'{direction}-v0.txt').read_text().splitlines()
        right = (inputs / f'{direction}-v1.txt').read_text().splitlines()
        assert len(left) == len(right) == 6 and [index for index in range(6) if left[index] != right[index]] == [5]
        counterexamples = [row for row in observations if row['direction'] == direction and row['returned'] is None and row['remaining'] != row['initial']]
        assert len(counterexamples) == 2
        doc_spans = [attribute['range'] for attribute in syntax['attributes'] if attribute['path'] == 'doc']
        evidence.append({'method': unit['name'], 'code': unit, 'original_documentation': {'source_path': path, 'source_sha256': unit['source_sha256'], 'doc_attribute_ranges': doc_spans, 'claim': 'Empty deque skips predicate; false returns None', 'not_claimed': 'Original docs do not assert rollback on false'}, 'source_observation': {'range': unit['range'], 'claim': 'Mutable endpoint borrowed, predicate called before conditional pop; no rollback branch'}, 'runtime_witness': {'path': str((witness_run / 'debug-1.jsonl').relative_to(ROOT)), 'sha256': sha(witness_run / 'debug-1.jsonl'), 'counterexamples': counterexamples, 'scope': 'i32 fixture, lengths1and3, normal false return'}, 'researcher_authored': {'v0': 'source-supported scoped claim; finite witnesses corroborate, not a universal execution proof', 'v1': 'deliberately false guarantee, contradicted by saved witnesses'}, 'code_relation_label': 'unknown_in_both_arms', 'unknown': ['panic', 'destructors', 'external predicate effects', 'performance', 'generic sharing feasibility', 'merge value']})
    dump(run / 'analyst-evidence.json', evidence)
    dump(run / 'input-index.json', [{'document': f'inputs/{direction}-v{index}.txt', 'unit_id': next(item['code']['id'] for item in evidence if item['method'] == f'pop_{direction}_if')} for direction in ('front', 'back') for index in (0, 1)])
    report = {'status': 'prepared_and_closed_as_regression', 'method_contexts': 2, 'documents': 4, 'changed_sentences_per_pair': 1, 'counterexamples_reused': 4, 'new_rust_executions': 0, 'discovery_or_confirmation_model_runs': 0, 'quality_score': None, 'artifacts_sha256': {str(path.relative_to(run)): sha(path) for path in sorted(run.rglob('*')) if path.is_file()}}
    dump(run / 'report.json', report)
    print(json.dumps({key: value for key, value in report.items() if key != 'artifacts_sha256'}, indent=2))


if __name__ == '__main__':
    main()
