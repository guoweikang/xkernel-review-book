"""Freeze native, source-assisted and deliberately altered Rust documentation."""

import hashlib
import json
from pathlib import Path
import shutil


def main():
    root = Path(__file__).resolve().parents[1]
    output = root / 'research/evidence/runs/2026-11-16-rust-srl-inputs-01'
    output.mkdir()
    claims_path = root / 'research/protocols/governed-doc-claims-v2.json'
    claims = json.loads(claims_path.read_text())
    by_id = {claim['id']: claim for claim in claims['claims']}
    role = root / 'research/evidence/runs/2026-11-12-role-preservation-01/source.rs'
    command = root / 'research/evidence/runs/2026-11-12-governed-doc-packets-01/complete-command/source.txt'
    sources = {'role': role, 'command': command}
    native = {'role': 'Returns this mode with new permission bits and the same file type.',
              'command': 'A simple command file that consumes each write as one complete request.'}
    definitions = [('role', 'role-change', 'permission-role'),
                   ('command', 'command-boundary', 'complete-command')]
    cases = []
    for name, claim_id, packet in definitions:
        assert native[name] in sources[name].read_text()
        texts = {'native': native[name], 'source_assisted': by_id[claim_id]['text'],
                 'altered': claims['interventions'][packet]['text']}
        for variant, text in texts.items():
            cases.append({'id': f'{name}-{variant}', 'text': text, 'case': name,
                          'variant': variant, 'provider_confirmed': False})
    protocol = {'input': str((output / 'cases.json').relative_to(root)),
                'question': 'Does unchanged SRL expose changed/preserved roles and whole-command callback conditions in real-source-backed development documentation?',
                'design': 'Two cases times three textual variants, two offline passes; all six retained. Native comments are exact substrings; source-assisted and altered texts reuse frozen v2 claims, not rewrites selected for parser success.',
                'references': {'role': 'Replacement permission and retained file-type roles; altered text reverses these. Neither direct interchangeability nor local sharing is established by SRL.',
                               'command': 'Nonempty and <=4096; one handler only after whole collection succeeds; error/zero progress before handler. Altered text permits per-fragment callbacks.'},
                'evaluation': 'Raw frames and role spans, predicate presence, two-pass integrity; qualitative clause audit with exact span evidence. No automatic semantic accuracy or binary clone label. No post-result rewriting.',
                'missing_input': 'No-document condition is unavailable evidence, not a fabricated sentence or a parser correctness point.',
                'limits': 'Already-seen development cases; researcher-authored completion, not provider approved. Completion adds source facts and changes phrasing, so cannot isolate formatting benefit. SRL alone sees text, not source behavior.',
                'stop': 'One six-input batch. Preserve failures and identify missing representation before another method; no new lexical exceptions.'}
    for name, value in [('cases.json', cases), ('inference-protocol.json', protocol)]:
        (output / name).write_text(json.dumps(value, indent=2) + '\n')
    for name, source in sources.items():
        shutil.copy2(source, output / f'{name}-source.txt')
    shutil.copy2(claims_path, output / 'claims-protocol.json')
    shutil.copy2(__file__, output / 'freezer.py')
    manifest = {'artifact_sha256': {path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                                  for path in sorted(output.iterdir())},
                'source_paths': {name: str(path.relative_to(root)) for name, path in sources.items()}}
    (output / 'report.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(output)


if __name__ == '__main__':
    main()
