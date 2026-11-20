import hashlib
import json
import os
import shutil
from pathlib import Path

here = Path(__file__).resolve().parent
root = here.parents[3]
destination = root / '.build/delete-drop-witness-01'
assert not (here / 'binary-relocation.json').exists()
results = json.loads((here / 'results.json').read_text())
records = {}
for mode in ('debug', 'opt'):
    source = here / mode / 'witness'
    target = destination / mode / 'witness'
    assert not target.exists()
    expected = results['builds'][mode]['binary_sha256']
    assert hashlib.sha256(source.read_bytes()).hexdigest() == expected
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(source, target)
    assert hashlib.sha256(target.read_bytes()).hexdigest() == expected
    records[mode] = {'original_path': f'{mode}/witness',
                     'relative_destination': os.path.relpath(target, here),
                     'sha256': expected,
                     'reason': 'Post-audit relocation of build output to ignored .build; original execution records unchanged.'}
(here / 'binary-relocation.json').write_text(json.dumps(records, indent=2) + '\n')
