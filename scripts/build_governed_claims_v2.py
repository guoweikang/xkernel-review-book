"""Separate source observations, norms and document reports in a versioned slice."""

import argparse
import copy
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
KINDS = {'source_observation', 'normative_responsibility', 'document_report', 'planned_capability', 'unknown'}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def validate(claim):
    if claim['kind'] not in KINDS:
        raise ValueError('invalid evidence kind')
    if claim['provider_validated'] or claim['independent_label'] is not None:
        raise ValueError('unsupported validation promotion')
    if claim['kind'] == 'unknown':
        if claim['evidence']:
            raise ValueError('unknown must not contain fabricated evidence')
        return
    evidence = claim['evidence']
    source = (ROOT / evidence['path']).read_bytes()
    if sha(source) != evidence['source_sha256'] or evidence['revision'] != claim['revision']:
        raise ValueError('wrong source identity')
    if claim['kind'] == 'source_observation' and evidence['medium'] not in ('rust_source', 'cargo_manifest'):
        raise ValueError('design declaration is not implementation evidence')
    lines = source.decode().splitlines(keepends=True)
    start, end = evidence['lines']
    if not 1 <= start <= end <= len(lines):
        raise ValueError('invalid range')
    excerpt = ''.join(lines[start - 1:end])
    if excerpt != evidence['excerpt']:
        raise ValueError('changed excerpt')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    assert args.run_id and all(character.isalnum() or character in '-_' for character in args.run_id)
    output = ROOT / 'research/evidence/runs' / args.run_id
    output.mkdir()
    path = ROOT / 'research/protocols/governed-doc-claims-v2.json'
    plan = json.loads(path.read_text())
    shutil.copy2(path, output / 'protocol.json')
    shutil.copy2(__file__, output / 'builder.py')
    claims = []
    parent_hashes = {}
    for spec in plan['claims']:
        folder = ROOT / plan['parent_run'] / spec['packet']
        parent_path = folder / 'packet.json'
        parent = json.loads(parent_path.read_text())
        parent_hashes[str(parent_path.relative_to(ROOT))] = sha(parent_path.read_bytes())
        claim = {**spec, 'revision': parent['source_revision'], 'evidence': None,
                 'provider_validated': False, 'independent_label': None}
        if spec['kind'] != 'unknown':
            if spec['source'] == 'packet':
                source_path = folder / 'source.txt'
                medium = 'design_document' if spec['packet'] == 'firmware-ownership' else 'rust_source'
                assert sha(source_path.read_bytes()) == parent['source_sha256']
            else:
                suffix = 'src/fwnode_backend/dtb.rs' if spec['source'] == 'backend' else 'Cargo.toml'
                source_path = ROOT / plan['audit_run'] / 'same-revision/drivers/firmware/rs-fdtree' / suffix
                medium = 'rust_source' if spec['source'] == 'backend' else 'cargo_manifest'
            source = source_path.read_bytes()
            start, end = spec['lines']
            claim['evidence'] = {'path': str(source_path.relative_to(ROOT)), 'revision': parent['source_revision'],
                'source_sha256': sha(source), 'medium': medium, 'lines': spec['lines'],
                'excerpt': ''.join(source.decode().splitlines(keepends=True)[start - 1:end])}
        validate(claim)
        claims.append(claim)
    interventions = []
    for packet, intervention in plan['interventions'].items():
        selected = [claim for claim in claims if claim['packet'] == packet]
        base = [claim['text'] for claim in selected]
        index = next(index for index, claim in enumerate(selected) if claim['id'] == intervention['claim'])
        changed = list(base)
        changed[index] = intervention['text']
        assert sum(left != right for left, right in zip(base, changed)) == 1
        folder = output / 'detector-input' / packet
        folder.mkdir(parents=True)
        (folder / 'revised.txt').write_text('\n\n'.join(base) + '\n')
        (folder / 'corrupted.txt').write_text('\n\n'.join(changed) + '\n')
        interventions.append({'packet': packet, 'claim': intervention['claim'], 'changed_statements': 1,
                              'base_characters': len('\n\n'.join(base)), 'corrupted_characters': len('\n\n'.join(changed))})
    rejected = []
    for name, identity, change in [
        ('document_as_implementation', 'firmware-reported-gap', {'kind': 'source_observation'}),
        ('provider_promotion', 'role-change', {'provider_validated': True}),
        ('independent_label_promotion', 'role-change', {'independent_label': 'positive'}),
    ]:
        altered = copy.deepcopy(next(claim for claim in claims if claim['id'] == identity))
        altered.update(change)
        try:
            validate(altered)
        except ValueError:
            rejected.append(name)
        else:
            raise AssertionError(name)
    (output / 'claims.json').write_text(json.dumps(claims, indent=2) + '\n')
    (output / 'manifest.json').write_text(json.dumps({'parent_packets': parent_hashes, 'scope': plan['scope']}, indent=2) + '\n')
    report = {'claims': len(claims), 'unknown': sum(claim['kind'] == 'unknown' for claim in claims),
              'interventions': interventions, 'rejected_controls': rejected, 'detector_runs': 0,
              'provider_validated': 0, 'scope': plan['status'],
              'artifact_sha256': {str(file.relative_to(output)): sha(file.read_bytes()) for file in sorted(output.rglob('*')) if file.is_file()}}
    (output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({key: value for key, value in report.items() if key != 'artifact_sha256'}, indent=2))


if __name__ == '__main__':
    main()
