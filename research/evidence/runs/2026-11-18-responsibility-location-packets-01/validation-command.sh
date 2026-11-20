python3 '/root/codes/x-kernel-worktrees/ai-review-book/research/evidence/runs/2026-11-18-responsibility-location-packets-01/rebuild.py' --check
python3 - <<'PY'
import pathlib,json,subprocess,hashlib
base=pathlib.Path('/root/codes/x-kernel-worktrees/ai-review-book/research/evidence/runs/2026-11-18-responsibility-location-packets-01')
inputs=json.loads((base/'inputs.json').read_text())
for source in inputs['sources']:
    data=(base/source['archive']).read_bytes()
    original=subprocess.check_output(['git','-C','/root/codes/x-kernel','show',inputs['revision']+':'+source['path']])
    assert data==original
    print('PASS fixed Git source',source['path'],hashlib.sha256(data).hexdigest())
assert (base/'protocol.snapshot.json').read_bytes()==pathlib.Path('research/protocols/responsibility-location-pilot-v1.json').read_bytes()
print('PASS protocol snapshot')
PY
python3 scripts/check_research_catalog.py
python3 scripts/build.py
