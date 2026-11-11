"""Isolated Lucene component control, not an InMap or paper reproduction."""

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import urllib.request


ROOT = Path(__file__).resolve().parents[1]
VERSION = '8.6.2'
ARTIFACTS = ('core', 'analyzers-common', 'queryparser', 'queries', 'sandbox')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    if not args.run_id or any(character not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_'
                              for character in args.run_id):
        parser.error('run-id must be a simple name')
    evidence = ROOT / 'research/evidence/runs' / args.run_id
    build = ROOT / '.build/lucene-probes' / args.run_id
    if evidence.exists() or build.exists():
        parser.error('refusing to overwrite a run')
    evidence.mkdir(parents=True)
    work = build / 'work'
    jars = work / 'jars'
    jars.mkdir(parents=True)
    provenance = []
    for artifact in ARTIFACTS:
        name = f'lucene-{artifact}-{VERSION}.jar'
        url = f'https://repo.maven.apache.org/maven2/org/apache/lucene/lucene-{artifact}/{VERSION}/{name}'
        content = urllib.request.urlopen(url, timeout=60).read()
        checksum = urllib.request.urlopen(url + '.sha1', timeout=60).read().decode().strip()
        if hashlib.sha1(content).hexdigest() != checksum.split()[0]:
            raise ValueError(f'checksum mismatch: {name}')
        (jars / name).write_bytes(content)
        provenance.append({'file': name, 'url': url, 'bytes': len(content),
                           'sha1_url': url + '.sha1', 'sha1': checksum,
                           'sha256': hashlib.sha256(content).hexdigest()})
        (evidence / 'dependencies.json').write_text(json.dumps(provenance, indent=2) + '\n')
    source = ROOT / 'research/tools/LuceneScoringProbe.java'
    shutil.copy2(source, work / source.name)
    shutil.copy2(source, evidence / source.name)
    shutil.copy2(__file__, evidence / 'runner.py')
    namespace = ROOT / 'scripts/scc_namespace.sh'
    shutil.copy2(namespace, evidence / 'namespace.sh')
    command = ['unshare', '--user', '--map-root-user', '--mount', '--pid', '--fork', '--net',
               '--ipc', '--uts', 'bash', str(namespace), str(build / 'root'), str(work), str(ROOT / '.tools/scc-smoke'),
               '/bin/bash', '-c',
               'cd /work && java -version && javac -version && '
               'javac -cp "jars/*" LuceneScoringProbe.java && '
               'java -cp ".:jars/*" LuceneScoringProbe']
    result = subprocess.run(command, capture_output=True, text=True, timeout=180)
    (evidence / 'stdout.txt').write_text(result.stdout)
    (evidence / 'stderr.txt').write_text(result.stderr)
    (evidence / 'execution.json').write_text(json.dumps({'command': command,
        'returncode': result.returncode, 'scope': 'synthetic Lucene component only'}, indent=2) + '\n')
    result.check_returncode()
    rows = [line.split('\t') for line in result.stdout.splitlines()]
    hits = {(row[1], row[2], row[3]): (float(row[4]), float(row[5]))
            for row in rows if row[0] == 'HIT'}
    identical = []
    for mode in ('default', 'classic-control'):
        for query in ('cpu', 'cpu*', 'cpu~', 'cpu*~', '( cpu*~ )^30.0 ( node*~ )^2.0'):
            first = hits[(mode, query, 'driver.Node')]
            second = hits[(mode, query, 'cpu.Node')]
            assert first[0] == second[0]
            assert abs(second[1] / first[1] - 900.0) < 0.001
            identical.append({'mode': mode, 'query': query, 'raw_equal': True,
                              'adjusted_ratio': second[1] / first[1]})
    report = {'scope': 'Lucene runtime control, not InMap execution',
              'queries': [row[1:] for row in rows if row[0] == 'QUERY'],
              'similarities': [row for row in rows if row[0] in ('WRITER', 'SEARCHER')],
              'identical_content_controls': identical,
              'artifact_sha256': {path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                                  for path in evidence.iterdir() if path.is_file()}}
    (evidence / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
