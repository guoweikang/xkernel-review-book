import hashlib
import json
import urllib.request
from pathlib import Path

root = Path(__file__).resolve().parent
url = 'https://doc.rust-lang.org/reference/destructors.html'
assert not (root / 'destructors.html').exists()
with urllib.request.urlopen(url, timeout=40) as response:
    source = response.read(1_000_001)
assert len(source) <= 1_000_000
(root / 'destructors.html').write_bytes(source)
(root / 'source.json').write_text(json.dumps({'url': url, 'retrieved': '2026-11-18',
    'sha256': hashlib.sha256(source).hexdigest(), 'bytes': len(source),
    'anchors': ['destructors.scope.nesting-drop-order', 'destructors.scope.params', 'destructors.operation'],
    'limit': 'Live Reference, not a pinned toolchain document; no specific kernel behavior established.'}, indent=2) + '\n')
