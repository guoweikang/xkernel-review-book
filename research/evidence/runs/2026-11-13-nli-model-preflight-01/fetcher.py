"""Pin NLI candidate metadata and historical HANS tree without loading weights."""

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import urllib.request

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    if not args.run_id or any(not (character.isalnum() or character in '-_') for character in args.run_id):
        raise ValueError('invalid run id')
    folder = ROOT / 'research/evidence/runs' / args.run_id
    originals = ROOT / 'research/evidence/originals' / args.run_id
    folder.mkdir()
    originals.mkdir()
    shutil.copy2(__file__, folder / 'fetcher.py')
    sources = []

    def save(name, url):
        with urllib.request.urlopen(url, timeout=60) as response:
            data = response.read()
        (originals / name).write_bytes(data)
        sources.append({'name': name, 'url': url, 'path': str((originals / name).relative_to(ROOT)),
                        'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()})
        (folder / 'sources.json').write_text(json.dumps(sources, indent=2) + '\n')
        return data

    historical = '7299f6f657089ce06a0f98e7e81f8d0f5b7741ce'
    tree = json.loads(save('hans-tree.json', f'https://api.github.com/repos/tommccoy1/hans/git/trees/{historical}?recursive=1'))
    save('hans-feather-README.txt', f'https://raw.githubusercontent.com/tommccoy1/hans/{historical}/berts_of_a_feather/README.md')
    model = 'cross-encoder/nli-deberta-v3-base'
    metadata = json.loads(save('model-api.json', f'https://huggingface.co/api/models/{model}?blobs=true'))
    revision = metadata['sha']
    card = save('model-README.txt', f'https://huggingface.co/{model}/resolve/{revision}/README.md')
    config = json.loads(save('config.json', f'https://huggingface.co/{model}/resolve/{revision}/config.json'))
    tokenizer = json.loads(save('tokenizer_config.json', f'https://huggingface.co/{model}/resolve/{revision}/tokenizer_config.json'))
    weights = [item for item in metadata.get('siblings', []) if item['rfilename'].endswith('.safetensors')]
    report = {'scope': 'metadata availability, not downloaded or verified model weights',
              'historical_revision': historical, 'historical_tree_truncated': tree.get('truncated'),
              'historical_weight_like_paths': [item['path'] for item in tree['tree'] if item['path'].endswith(('.pt', '.bin', '.npz', '.th', '.safetensors', '.tar.gz'))],
              'candidate': model, 'revision': revision, 'id2label': config.get('id2label'),
              'architectures': config.get('architectures'), 'tokenizer_class': tokenizer.get('tokenizer_class'),
              'license_metadata': metadata.get('cardData', {}).get('license'), 'safetensors_metadata': weights,
              'model_inferences': 0, 'card_bytes': len(card)}
    (folder / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
