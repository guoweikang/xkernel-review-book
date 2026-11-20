"""Freeze source-backed documentation interventions for four existing candidate pairs."""

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


def main():
    output = ROOT / 'research/evidence/runs/2026-11-16-candidate-srl-inputs-01'
    output.mkdir(exist_ok=False)
    queue_path = ROOT / 'research/evidence/runs/2026-11-16-doc-lda-01/review-queue.json'
    queue = json.loads(queue_path.read_text())
    corpus = ROOT / 'research/evidence/runs/2026-11-05-rust-baseline-corpus-01'
    units = {unit['id']: unit for unit in json.loads((corpus / 'units.json').read_text())}
    definitions = [
        (0, 0, 'write', 'The write method accepts a shared byte slice and returns an InvalidInput error.', 'shared', 'mutable', 'slice mutability; default stub, not successful data transfer'),
        (0, 1, 'read', 'The read method accepts a mutable byte slice and returns an InvalidInput error.', 'mutable', 'shared', 'slice mutability; default stub, not successful data transfer'),
        (8, 0, 'try_call_once', 'The try_call_once method returns an existing value if initialization has completed. Otherwise it calls try_call_once_slow with the supplied closure.', 'try_call_once_slow', 'call_once', 'direct slow-path target; no resolved compiler call graph'),
        (8, 1, 'call_once', 'The call_once method calls try_call_once with a closure that wraps the initializer result in Ok. It returns the initialized value.', 'calls try_call_once', 'calls try_call_once_slow', 'direct delegation target; no claim of whole-function equivalence'),
        (25, 0, 'symlink', 'The symlink method locks the dentry location and obtains directory operations. It then calls the symlink operation with a target string while retaining the location guard.', 'a target string', 'a mode value', 'operation argument; source scope holds guard, runtime not tested'),
        (25, 1, 'mkdir', 'The mkdir method locks the dentry location and obtains directory operations. It then calls the mkdir operation with a mode value while retaining the location guard.', 'a mode value', 'a target string', 'operation argument; common steps do not prove safe extraction'),
        (9, 0, 'lookup_inode', 'The lookup_inode method retrieves an existing inode by calling node::lookup_inode with the superblock and inode number.', 'retrieves', 'creates', 'lookup versus creation; existing native contract plus forwarding source'),
        (9, 1, 'new_with_inode_attribute_operations', 'The constructor creates an inode with attribute operations. It selects operation tables according to the node type and calls from_parts_with_attribute_operations.', 'creates', 'retrieves', 'creation versus lookup; source construction path'),
    ]
    cases, references = [], []
    with zipfile.ZipFile(corpus / 'units.zip') as archive:
        for pair_index, member_index, name, complete, original, replacement, question in definitions:
            binding = queue[pair_index]['members'][member_index]
            unit = units[binding['unit_id']]
            assert unit['name'] == name
            fragment = archive.read(unit['entry'])
            assert hashlib.sha256(fragment).hexdigest() == unit['sha256']
            assert complete.count(original) == 1
            key = f'pair{pair_index}-{name}'
            (output / f'{key}.rs').write_bytes(fragment)
            for variant, text in [('native', binding['doc_text']), ('complete', complete), ('altered', complete.replace(original, replacement))]:
                cases.append({'id': f'{key}-{variant}', 'text': text, 'variant': variant, 'unit_id': unit['id']})
            references.append({'id': key, 'queue_index': pair_index, 'unit': unit,
                               'question': question, 'replaced': original, 'replacement': replacement,
                               'source_fragment': f'{key}.rs', 'provider_confirmed': False,
                               'assessment': 'analyst-authored source-assisted development input; not independent gold'})
    protocol = {
        'input': str((output / 'cases.json').relative_to(ROOT)),
        'question': 'Does unchanged SRL retain argument distinctions, call targets and common steps in four real candidate pairs?',
        'design': 'Eight functions, three arms, two offline passes. Preserve all 24 inputs, no retraining, reranking or post-output edits.',
        'selection': 'Previously seen development queue indices 0,8,25,9; purposive failure analysis, not random or held-out evaluation.',
        'read_write_amendment': 'These are trait defaults returning errors. Test mutability and error contract, not imaginary successful transfer direction.',
        'reference_policy': 'Only id/text reach model. References are source-assisted analyst descriptions, not independent provider norms or automated labels.',
        'evaluation': 'Raw predicate/argument spans and explicit textual changes; qualitative audit of every input. No field accuracy without frozen mapping, no refactoring score.',
        'execution': 'Reuse unchanged run_hanlp_srl_smoke.py, pinned local assets and unused-NER compatibility guard; CPU4, seed0, batch4, offline, weights_only=True, timeout600s.',
        'stop': 'One fixed batch; preserve errors and absent frames. No input rewriting for parser success. No production edits or optimization patch.',
    }
    dump(output / 'cases.json', cases)
    dump(output / 'references.json', references)
    dump(output / 'inference-protocol.json', protocol)
    shutil.copy2(__file__, output / 'freezer.py')
    dump(output / 'report.json', {'queue_sha256': sha(queue_path), 'units_sha256': sha(corpus / 'units.json'),
        'artifact_sha256': {path.name: sha(path) for path in output.iterdir() if path.is_file()}})
    print(output)


if __name__ == '__main__':
    main()
