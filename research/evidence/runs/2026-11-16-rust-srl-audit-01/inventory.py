"""Inventory predicate containment in raw spans, not logical scope or entailment."""

import argparse
import hashlib
import json
from pathlib import Path

from check_hanlp_srl_smoke import check_batches


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folder', type=Path)
    args = parser.parse_args()
    folder = args.folder
    inputs = json.loads((folder / 'inputs.json').read_text())
    path = folder / 'raw-1.json'
    batches = json.loads(path.read_text())
    checked = check_batches(batches, [row['id'] for row in inputs])
    observations = []
    for batch in batches:
        for identity, frames in zip(batch['ids'], batch['output']['srl'], strict=True):
            predicates = [next(role for role in frame if role[1] == 'PRED') for frame in frames]
            edges = []
            for outer_index, outer in enumerate(frames):
                for role in outer:
                    if role[1] == 'PRED':
                        continue
                    for inner_index, predicate in enumerate(predicates):
                        if inner_index != outer_index and role[2] <= predicate[2] and predicate[3] <= role[3]:
                            edges.append({'outer_frame': outer_index, 'outer_predicate': predicates[outer_index][0],
                                          'role': role[1], 'role_span': role[2:], 'inner_frame': inner_index,
                                          'inner_predicate': predicate[0], 'inner_predicate_span': predicate[2:]})
            observations.append({'id': identity, 'predicate_order': [role[0] for role in predicates], 'containment': edges})
    print(json.dumps({'scope': 'post-output structural inventory, no logical mapping or accuracy',
                      'input_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                      'sentences': len(checked), 'frames': sum(row['frames'] for row in checked),
                      'spans': sum(row['spans'] for row in checked), 'tokens': sum(row['tokens'] for row in checked),
                      'empty_sentences': sum(row['frames'] == 0 for row in checked),
                      'containment_edges': sum(len(row['containment']) for row in observations),
                      'observations': observations}, indent=2))


if __name__ == '__main__':
    main()
