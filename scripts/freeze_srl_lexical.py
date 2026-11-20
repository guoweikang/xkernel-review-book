"""Freeze a complete lexical factorial before running the unchanged SRL pipeline."""

import hashlib
import itertools
import json
from pathlib import Path
import shutil


def main():
    root = Path(__file__).resolve().parents[1]
    folder = root / 'research/evidence/runs/2026-11-16-srl-lexical-inputs-01'
    folder.mkdir()
    factors = [('allocator', 'recycler'), ('buffer', 'lease'),
               ('validator', 'verifier'), ('request', 'ticket')]
    cases = []
    for levels in itertools.product((0, 1), repeat=4):
        actor, resource, checker, token = [pair[level] for pair, level in zip(factors, levels, strict=True)]
        cases.append({'id': 'lex-' + ''.join(map(str, levels)), 'family': 'only_if',
                      'levels': list(levels),
                      'text': f'The {actor} releases the {resource} only if the {checker} accepts the {token}.',
                      'query_forms': ['release', 'releases', 'released'], 'gold': 'unknown',
                      'rationale': 'Necessary condition does not assert that release occurred.'})
    protocol = {'input': str((folder / 'cases.json').relative_to(root)),
                'question': 'Does lexical substitution change conditional attachment and frozen gate output?',
                'factors_in_order': factors, 'design': 'Full 2^4 factorial; all 16 retained; two identical inference passes.',
                'selection': 'Development diagnosis after observing both endpoints; not held-out or independent labels.',
                'metrics': 'Six unchanged scope arms; target frame modifier presence; 8 matched contrasts per noun factor. Descriptive only; all references unknown, so no useful-answer accuracy estimate.',
                'attachment_proxy': 'Target releases frame contains ARGM-ADV/MOD/CND; proxy only, inspect raw spans before semantic attribution.',
                'fixed': 'Same HanLP assets, environment, runner, compatibility check and evaluate_srl_scope.py. No rule tuning.',
                'stop': 'One full factorial then return to Rust source-backed cases. No lexical exceptions.'}
    for name, value in [('cases.json', cases), ('inference-protocol.json', protocol)]:
        (folder / name).write_text(json.dumps(value, indent=2) + '\n')
    for source in [root / 'scripts/evaluate_srl_scope.py', root / 'research/protocols/srl-scope-ablation-v1.json', Path(__file__)]:
        shutil.copy2(source, folder / source.name)
    manifest = {'artifact_sha256': {path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                                  for path in sorted(folder.iterdir())}}
    (folder / 'report.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(folder)


if __name__ == '__main__':
    main()
