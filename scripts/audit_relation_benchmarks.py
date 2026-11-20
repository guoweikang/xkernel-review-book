"""Inventory downloaded HANS labels; no model predictions or accuracy."""

from collections import Counter
import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / 'research/evidence/runs/2026-11-13-relation-benchmarks-01'


def main():
    sources = json.loads((RUN / 'sources.json').read_text())
    for source in sources:
        if hashlib.sha256((ROOT / source['local_path']).read_bytes()).hexdigest() != source['sha256']:
            raise ValueError('source hash differs')
    source = next(row for row in sources if row['name'] == 'hans-data.tsv')
    with (ROOT / source['local_path']).open() as stream:
        rows = list(csv.DictReader(stream, delimiter='\t'))
    if len({row['pairID'] for row in rows}) != len(rows):
        raise ValueError('duplicate pair id')
    result = {'scope': 'download and label inventory, not model reproduction', 'rows': len(rows),
              'labels': dict(Counter(row['gold_label'] for row in rows)),
              'heuristics': dict(Counter(row['heuristic'] for row in rows)),
              'subcases': dict(Counter(row['subcase'] for row in rows)),
              'model_executions': 0, 'data_sha256': source['sha256']}
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
