"""Run unchanged SCC over prepared Rust bags and verify every eligible pair."""

import argparse
import csv
from fractions import Fraction
import itertools
import json
from pathlib import Path
import re
import shutil
import subprocess

from prepare_rust_token_bags import decode_bag
from run_scc_smoke import ROOT, REVISION, digest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9_-]+', args.run_id):
        parser.error('Invalid run ID')
    evidence = ROOT / 'research/evidence/runs' / args.run_id
    run = ROOT / '.build/scc-runs' / args.run_id
    if evidence.exists() or run.exists():
        parser.error('Run already exists')
    evidence.mkdir(parents=True)
    work = run / 'work'
    work.mkdir(parents=True)
    tools = ROOT / '.tools/scc-smoke'
    source = tools / f'SourcererCC-{REVISION}'
    token_input = ROOT / 'research/evidence/runs/2026-11-05-rust-token-bags-01'
    corpus = ROOT / 'research/evidence/runs/2026-11-05-rust-baseline-corpus-01'
    report = {'passed': False, 'source_revision': REVISION, 'threshold_argument': 8,
              'minimum_tokens': 65, 'maximum_tokens': 500000,
              'semantic_labels': 'unverified', 'paper_result_reproduction': 'not_run'}
    shutil.copy2(__file__, evidence / 'runner.py')
    shutil.copy2(ROOT / 'scripts/prepare_rust_token_bags.py', evidence / 'bag_decoder.py')
    shutil.copy2(ROOT / 'scripts/scc_namespace.sh', evidence / 'namespace.sh')
    try:
        tree = json.loads((tools / 'source-tree.json').read_text())
        if tree['sha'] != REVISION or tree.get('truncated'):
            raise ValueError('Incomplete or mismatched source tree')
        import hashlib
        verified = {}
        for entry in tree['tree']:
            path = source / entry['path']
            if entry['type'] != 'blob' or not path.is_file():
                continue
            content = path.read_bytes()
            actual = hashlib.sha1(b'blob ' + str(len(content)).encode() + b'\0' + content).hexdigest()
            if actual != entry['sha']:
                raise ValueError('Upstream source mismatch')
            verified[entry['path']] = actual
        if {str(path.relative_to(source)) for path in source.rglob('*') if path.is_file()} != set(verified):
            raise ValueError('Unverified upstream files')
        (evidence / 'source-integrity.json').write_text(json.dumps(verified, indent=2) + '\n')
        for directory in [token_input, corpus]:
            upstream = json.loads((directory / 'report.json').read_text())
            if not upstream['passed']:
                raise ValueError('Input gate failed')
            for name, checksum in upstream['artifacts_sha256'].items():
                if digest(directory / name) != checksum:
                    raise ValueError('Input artifact mismatch')
        token_report = json.loads((token_input / 'report.json').read_text())
        if token_report['corpus_report_sha256'] != digest(corpus / 'report.json'):
            raise ValueError('Corpus and token report identity mismatch')
        report['inputs'] = {str(path.relative_to(ROOT)): digest(path) for path in
                            [token_input / 'report.json', token_input / 'blocks.file', corpus / 'report.json', corpus / 'units.json']}
        report['tool_archives'] = {name: digest(tools / name) for name in ['source.tar.gz', 'jdk.tar.gz', 'ant.tar.gz']}
        units = {unit['id']: unit for unit in json.loads((corpus / 'units.json').read_text())}
        mapping = {record['file_id']: units[record['unit_id']] for record in token_report['records']}
        bags = {}
        for line in (token_input / 'blocks.file').read_text().splitlines():
            number = int(line.split(',', 2)[1])
            if number in bags or number not in mapping:
                raise ValueError('Ambiguous or unknown file ID')
            bags[number] = decode_bag(line)
        if set(bags) != set(mapping):
            raise ValueError('Missing tokenized units')
        totals = {number: sum(bag.values()) for number, bag in bags.items()}
        eligible = sorted(number for number, total in totals.items() if 65 <= total <= 500000)
        expected = set()
        for first, second in itertools.combinations(eligible, 2):
            denominator = max(totals[first], totals[second])
            if min(totals[first], totals[second]) * 10 < 8 * denominator:
                continue
            shared = sum((bags[first] & bags[second]).values())
            if shared * 10 >= 8 * denominator:
                expected.add((first, second))
        report['total_units'] = len(bags)
        report['eligible_units'] = len(eligible)
        report['oracle_comparisons'] = len(eligible) * (len(eligible) - 1) // 2
        detector = work / 'clone-detector'
        shutil.copytree(source / 'clone-detector', detector)
        (work / 'bin').mkdir()
        (work / 'bin/python').symlink_to('/usr/bin/python3')
        dataset = detector / 'input/dataset'
        dataset.mkdir(parents=True, exist_ok=True)
        shutil.copy2(token_input / 'blocks.file', dataset / 'blocks.file')
        properties = detector / 'sourcerer-cc.properties'
        properties.write_text(re.sub(r'(?m)^([A-Z]+_THREADS)=\d+$', r'\1=1', properties.read_text()))
        if 'MIN_TOKENS=65\n' not in properties.read_text() or 'MAX_TOKENS=500000\n' not in properties.read_text():
            raise ValueError('Detector size settings changed')
        shutil.copy2(properties, evidence / 'sourcerer-cc.properties')
        pipeline = '''#!/bin/bash
set -euo pipefail
java -version
ant -version
test ! -e /root
test ! -e /proc/1/root
cd /work/clone-detector
ant clean cdi
bash execute.sh 1
run_phase() {
    echo 1 > search_metadata.txt
    rm -f nodes_completed.txt
    java -Dproperties.rootDir=/work/clone-detector/ \\
        -Dproperties.location=/work/clone-detector/NODE_1/sourcerer-cc.properties \\
        -Dlog4j.configurationFile=/work/clone-detector/NODE_1/log4j2.xml \\
        -jar dist/indexbased.SearchManager.jar "$1" 8
}
run_phase init
run_phase index
bash move-index.sh
bash execute.sh 1
run_phase search
'''
        (work / 'pipeline.sh').write_text(pipeline)
        shutil.copy2(work / 'pipeline.sh', evidence / 'pipeline.sh')
        command = ['timeout', '240', 'unshare', '--user', '--map-root-user', '--mount', '--pid', '--net',
                   '--ipc', '--uts', '--fork', 'bash', str(ROOT / 'scripts/scc_namespace.sh'),
                   str(run / 'root'), str(work), str(tools), '/usr/bin/bash', '/work/pipeline.sh']
        report['command'] = command
        with (evidence / 'execution.log').open('w') as log:
            result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, timeout=260)
        report['exit_code'] = result.returncode
        for path in detector.glob('NODE_1/output*/*'):
            if path.is_file():
                shutil.copy2(path, evidence / path.name)
        if result.returncode:
            raise ValueError('Native pipeline failed')
        pair_files = list(evidence.glob('*clones_index_WITH_FILTER.txt'))
        if len(pair_files) != 1:
            raise ValueError('Expected one raw pair output')
        pairs = []
        for row in csv.reader(pair_files[0].read_text().splitlines()):
            if len(row) != 4 or row[0] != '1' or row[2] != '1':
                raise ValueError('Unexpected project or pair format')
            first, second = sorted([int(row[1]), int(row[3])])
            if first == second or first not in bags or second not in bags:
                raise ValueError('Invalid pair identity')
            pairs.append((first, second))
        actual = set(pairs)
        report.update({'raw_pairs': len(pairs), 'unique_pairs': len(actual),
                       'repeated_rows': len(pairs) - len(actual), 'oracle_pairs': len(expected),
                       'missing_from_detector': sorted(expected - actual),
                       'unexpected_from_detector': sorted(actual - expected)})
        candidates = []
        for first, second in sorted(actual):
            left, right = mapping[first], mapping[second]
            shared = sum((bags[first] & bags[second]).values())
            same_file = left['path'] == right['path']
            candidates.append({'file_ids': [first, second], 'members': [left, right],
                               'shared_tokens': shared, 'denominator': max(totals[first], totals[second]),
                               'ancestor_related': left['id'] in right['ancestor_ids'] or right['id'] in left['ancestor_ids'],
                               'source_ranges_overlap': same_file and max(left['range'][0], right['range'][0]) < min(left['range'][1], right['range'][1]),
                               'both_test_path_hint': left['test_path_hint'] and right['test_path_hint'],
                               'interpretation': 'text_similarity_only_unreviewed'})
        candidates.sort(key=lambda item: (-Fraction(item['shared_tokens'], item['denominator']), item['file_ids']))
        (evidence / 'candidates.json').write_text(json.dumps(candidates, ensure_ascii=False, indent=2) + '\n')
        report['ancestor_related_pairs'] = sum(item['ancestor_related'] for item in candidates)
        report['overlapping_range_pairs'] = sum(item['source_ranges_overlap'] for item in candidates)
        report['both_test_path_hint_pairs'] = sum(item['both_test_path_hint'] for item in candidates)
        report['algorithm_java_unchanged'] = all(digest(path) == digest(detector / path.relative_to(source / 'clone-detector'))
                                                for path in (source / 'clone-detector/src').rglob('*.java'))
        report['passed'] = actual == expected and report['algorithm_java_unchanged']
    except Exception as error:
        report['error'] = str(error)
    finally:
        report['artifacts_sha256'] = {path.name: digest(path) for path in sorted(evidence.iterdir()) if path.is_file()}
        (evidence / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({key: value for key, value in report.items() if key != 'artifacts_sha256'}, indent=2))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
