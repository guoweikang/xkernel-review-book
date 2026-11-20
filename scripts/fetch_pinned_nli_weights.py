"""Download only pinned safetensors/tokenizer assets; never load remote code."""

import hashlib
import json
from pathlib import Path
import urllib.request

ROOT = Path(__file__).resolve().parents[1]


def main():
    preflight = ROOT / 'research/evidence/runs/2026-11-13-nli-model-preflight-01/report.json'
    plan = json.loads(preflight.read_text())
    folder = ROOT / 'research/evidence/originals/2026-11-13-nli-weights-01'
    report_folder = ROOT / 'research/evidence/runs/2026-11-13-nli-weights-01'
    folder.mkdir()
    report_folder.mkdir()
    files = ['config.json', 'tokenizer_config.json', 'tokenizer.json', 'special_tokens_map.json',
             'added_tokens.json', 'spm.model', 'model.safetensors']
    records = []
    for filename in files:
        url = f'https://huggingface.co/{plan["candidate"]}/resolve/{plan["revision"]}/{filename}'
        path = folder / filename
        digest = hashlib.sha256()
        with urllib.request.urlopen(url, timeout=60) as response, path.open('xb') as stream:
            while chunk := response.read(1024 * 1024):
                stream.write(chunk)
                digest.update(chunk)
        if filename == 'model.safetensors':
            expected = plan['safetensors_metadata'][0]
            if path.stat().st_size != expected['size'] or digest.hexdigest() != expected['lfs']['sha256']:
                raise ValueError('weight does not match publisher metadata')
        records.append({'name': filename, 'url': url, 'sha256': digest.hexdigest(), 'bytes': path.stat().st_size})
        (report_folder / 'downloads.json').write_text(json.dumps(records, indent=2) + '\n')
    (report_folder / 'report.json').write_text(json.dumps({'model': plan['candidate'], 'revision': plan['revision'],
        'weight_sha_verified_against_publisher': True, 'files': len(records), 'model_loads': 0,
        'preflight_sha256': hashlib.sha256(preflight.read_bytes()).hexdigest()}, indent=2) + '\n')
    print('PASS: pinned assets downloaded; weight size and SHA256 verified; model not loaded')


if __name__ == '__main__':
    main()
