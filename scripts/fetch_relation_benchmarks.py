"""Archive primary relation benchmarks without executing third-party code."""

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import urllib.request

ROOT = Path(__file__).resolve().parents[1]


def fetch(url):
    request = urllib.request.Request(url, headers={'User-Agent': 'xkernel-review-research'})
    with urllib.request.urlopen(request, timeout=90) as response:
        return response.read()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    if not args.run_id or any(not (character.isalnum() or character in '-_') for character in args.run_id):
        raise ValueError('invalid run id')
    run = ROOT / 'research/evidence/runs' / args.run_id
    originals = ROOT / 'research/evidence/originals' / args.run_id
    run.mkdir()
    originals.mkdir()
    shutil.copy2(__file__, run / 'fetcher.py')
    records = []

    def save(name, url):
        data = fetch(url)
        if name.endswith('.pdf') and not data.startswith(b'%PDF'):
            raise ValueError('not a PDF')
        path = originals / name
        path.write_bytes(data)
        records.append({'name': name, 'url': url, 'local_path': str(path.relative_to(ROOT)),
                        'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()})
        (run / 'sources.json').write_text(json.dumps(records, indent=2) + '\n')
        return data

    for name, identity in [('paws', 'N19-1131'), ('hans', 'P19-1334'), ('semantoneg', '2022.blackboxnlp-1.20')]:
        save(name + '.pdf', f'https://aclanthology.org/{identity}.pdf')
    for name, repo, datafile in [('paws', 'google-research-datasets/paws', None),
                                 ('hans', 'tommccoy1/hans', 'heuristics_evaluation_set.txt')]:
        info = json.loads(save(name + '-commit.json', f'https://api.github.com/repos/{repo}/commits/HEAD'))
        revision = info['sha']
        save(name + '-README.txt', f'https://raw.githubusercontent.com/{repo}/{revision}/README.md')
        if datafile:
            save(name + '-data.tsv', f'https://raw.githubusercontent.com/{repo}/{revision}/{datafile}')
    print(json.dumps({'downloaded_files': len(records), 'originals_git_ignored': True, 'model_executions': 0}))


if __name__ == '__main__':
    main()
