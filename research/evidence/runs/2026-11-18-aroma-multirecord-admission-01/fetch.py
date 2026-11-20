import hashlib
import json
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
COMMIT = 'e8d8beeb99255d8929874c156fd65aac74d21508'
RAW = f'https://raw.githubusercontent.com/facebookresearch/aroma/{COMMIT}/'
SOURCES = {
    'tree.json': f'https://api.github.com/repos/facebookresearch/aroma/git/trees/{COMMIT}?recursive=1',
    'github_repositories.csv': RAW + 'datasets/github_repositories.csv',
    'stack_overflow_code_snippets.csv': RAW + 'datasets/stack_overflow_code_snippets.csv',
    'biggroum_code_snippets.csv': RAW + 'datasets/biggroum_code_snippets.csv',
    'pom.xml': RAW + 'reference/pom.xml',
}


def main():
    assert not (HERE / 'downloads.json').exists()
    manifest = []
    remaining = 5_000_000
    for filename, url in SOURCES.items():
        try:
            request = urllib.request.Request(url, headers={'User-Agent': 'research-artifact-audit'})
            with urllib.request.urlopen(request, timeout=40) as response:
                data = response.read(remaining + 1)
            assert len(data) <= remaining, 'Download budget exceeded'
            remaining -= len(data)
            (HERE / filename).write_bytes(data)
            manifest.append({'file': filename, 'url': url, 'bytes': len(data),
                             'sha256': hashlib.sha256(data).hexdigest(), 'status': 'downloaded'})
        except Exception as error:
            manifest.append({'file': filename, 'url': url, 'status': 'failed', 'error': repr(error)})
    (HERE / 'downloads.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps(manifest, indent=2))


if __name__ == '__main__':
    main()
