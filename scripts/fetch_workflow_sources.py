"""Archive bounded first-party workflow documents, never install or execute them."""

import hashlib
import json
from pathlib import Path
import urllib.request


def fetch(url):
    request = urllib.request.Request(url, headers={'User-Agent': 'research-workflow-audit'})
    with urllib.request.urlopen(request, timeout=30) as response:
        body = response.read(1024 * 1024 + 1)
        if len(body) > 1024 * 1024:
            raise ValueError('Document exceeds 1 MiB bound')
        return body


def main():
    root = Path(__file__).resolve().parents[1]
    output = root / 'research/evidence/runs/2026-11-12-research-workflows-01'
    output.mkdir(parents=True, exist_ok=False)
    records = []
    for repository, branch, filename in [('karpathy/autoresearch', 'master', 'program.md'),
                                          ('SakanaAI/AI-Scientist-v2', 'main', 'README.md')]:
        metadata_url = f'https://api.github.com/repos/{repository}/commits/{branch}'
        metadata = fetch(metadata_url)
        revision = json.loads(metadata)['sha']
        url = f'https://raw.githubusercontent.com/{repository}/{revision}/{filename}'
        content = fetch(url)
        basename = repository.replace('/', '--')
        (output / (basename + '-commit.json')).write_bytes(metadata)
        (output / (basename + '-' + filename)).write_bytes(content)
        records.append({'repository': repository, 'revision': revision, 'metadata_url': metadata_url,
                        'url': url, 'path': basename + '-' + filename, 'bytes': len(content),
                        'sha256': hashlib.sha256(content).hexdigest()})
    (output / 'manifest.json').write_text(json.dumps(records, indent=2) + '\n')
    print(json.dumps(records, indent=2))


if __name__ == '__main__':
    main()
