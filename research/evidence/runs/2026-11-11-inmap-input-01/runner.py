"""Compile original InMap and run its input pipeline in an isolated namespace."""

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import urllib.request


ROOT = Path(__file__).resolve().parents[1]
REVISION = 'cae17d87f8c17d8108d21abd41e0520b6ca65d7c'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    if not args.run_id or any(character not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_' for character in args.run_id):
        parser.error('simple run-id required')
    evidence = ROOT / 'research/evidence/runs' / args.run_id
    build = ROOT / '.build/inmap-runs' / args.run_id
    if evidence.exists() or build.exists():
        parser.error('will not overwrite prior run')
    evidence.mkdir(parents=True)
    work = build / 'work'
    work.mkdir(parents=True)
    source = ROOT / '.tools/inmap' / REVISION / 'source'
    downloads = json.loads((ROOT / 'research/evidence/runs/2026-11-11-inmap-fetch-01/downloads.json').read_text())
    for archive in downloads:
        for item in archive['files']:
            assert hashlib.sha256((source / item['path']).read_bytes()).hexdigest() == item['sha256']
    shutil.copytree(source / 'src', work / 'src')
    relative = 'test-systems/Jabref/sources/3.7/src/main/java'
    shutil.copytree(source / relative, work / relative)
    jars = work / 'jars'
    jars.mkdir()
    dependency_manifest = ROOT / 'research/evidence/runs/2026-11-11-lucene-scoring-03/dependencies.json'
    dependencies = json.loads(dependency_manifest.read_text())
    cached = ROOT / '.build/lucene-probes/2026-11-11-lucene-scoring-03/work/jars'
    for item in dependencies:
        content = (cached / item['file']).read_bytes()
        assert hashlib.sha256(content).hexdigest() == item['sha256']
        (jars / item['file']).write_bytes(content)
    for artifact in ('asm', 'asm-util'):
        name = artifact + '-6.2.1.jar'
        url = f'https://repo.maven.apache.org/maven2/org/ow2/asm/{artifact}/6.2.1/{name}'
        content = urllib.request.urlopen(url, timeout=60).read()
        checksum = urllib.request.urlopen(url + '.sha1', timeout=60).read().decode().strip()
        assert hashlib.sha1(content).hexdigest() == checksum
        (jars / name).write_bytes(content)
        dependencies.append({'file': name, 'url': url, 'sha1': checksum,
                             'sha256': hashlib.sha256(content).hexdigest()})
    (evidence / 'dependencies.json').write_text(json.dumps(dependencies, indent=2) + '\n')
    config = ROOT / 'research/evidence/runs/2026-11-11-inmap-config-audit-02/config-single.txt'
    shutil.copy2(config, work / 'config-single.txt')
    shutil.copy2(config, evidence / 'config-single.txt')
    harness = ROOT / 'research/tools/InMapInputProbe.java'
    shutil.copy2(harness, work / harness.name)
    shutil.copy2(harness, evidence / harness.name)
    shutil.copy2(__file__, evidence / 'runner.py')
    namespace = ROOT / 'scripts/scc_namespace.sh'
    shutil.copy2(namespace, evidence / 'namespace.sh')
    sources = sorted(str(path.relative_to(work)) for path in (work / 'src').rglob('*.java'))
    (work / 'sources.txt').write_text('\n'.join(sources + [harness.name]) + '\n')
    command = ['unshare', '--user', '--map-root-user', '--mount', '--pid', '--fork', '--net', '--ipc', '--uts',
               'bash', str(namespace), str(build / 'root'), str(work), str(ROOT / '.tools/scc-smoke'),
               '/bin/bash', '-c', 'cd /work && java -version && mkdir classes && '
               'javac -cp "jars/*" -d classes @sources.txt && java -cp "classes:jars/*" InMapInputProbe']
    result = subprocess.run(command, capture_output=True, text=True, timeout=180)
    (evidence / 'stdout.txt').write_text(result.stdout)
    (evidence / 'stderr.txt').write_text(result.stderr)
    for name in ('filtered-classes.txt', 'indexed-paths.txt'):
        if (work / name).exists():
            shutil.copy2(work / name, evidence / name)
    report = {'scope': 'original config/preprocessing/indexing only', 'revision': REVISION,
              'returncode': result.returncode, 'command': command,
              'original_sources_modified': False,
              'source_files_compiled': len(sources),
              'artifact_sha256': {path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                                  for path in evidence.iterdir() if path.is_file()}}
    (evidence / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(result.stdout[-3000:])
    print(result.stderr[-2000:])
    result.check_returncode()


if __name__ == '__main__':
    main()
