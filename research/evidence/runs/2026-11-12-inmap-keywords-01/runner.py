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
    parser.add_argument('--retrieval-limit', type=int)
    parser.add_argument('--missing-method-loop', action='store_true')
    parser.add_argument('--unique-maximum-control', action='store_true')
    parser.add_argument('--keyword-control', action='store_true')
    args = parser.parse_args()
    if args.keyword_control and (args.missing_method_loop or args.unique_maximum_control or args.retrieval_limit is not None):
        parser.error('keyword controls cannot be combined with retrieval or loop variants')
    if args.missing_method_loop and args.retrieval_limit is not None:
        parser.error('loop control does not override original retrieval limit')
    if args.unique_maximum_control and not args.missing_method_loop:
        parser.error('selector control requires missing-method-loop')
    if args.retrieval_limit is not None and not 1 <= args.retrieval_limit <= 10000:
        parser.error('retrieval-limit out of bounded range')
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
    selector_change = None
    if args.unique_maximum_control:
        target = work / 'src/recommender/AutoMap.java'
        original = target.read_bytes()
        content = original.decode()
        start = content.index('\tprivate void pickHighestClassScore()')
        end = content.index('\tprivate void produceRecommendedMappings(', start)
        replacement = ROOT / 'research/tools/InMapUniqueMaximum.txt'
        variant = content[:start] + replacement.read_text() + content[end:]
        target.write_text(variant)
        shutil.copy2(replacement, evidence / replacement.name)
        selector_change = {'method': 'pickHighestClassScore',
                           'before_sha256': hashlib.sha256(original).hexdigest(),
                           'after_sha256': hashlib.sha256(target.read_bytes()).hexdigest(),
                           'removed_method': content[start:end]}
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
    harness_name = ('InMapKeywordProbe.java' if args.keyword_control else
                    'InMapLoopProbe.java' if args.missing_method_loop else 'InMapInputProbe.java')
    harness = ROOT / 'research/tools' / harness_name
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
               'javac -cp "jars/*" -d classes @sources.txt && java -cp "classes:jars/*" ' + harness.stem
               + ('' if args.retrieval_limit is None else ' ' + str(args.retrieval_limit))]
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=180)
    except subprocess.TimeoutExpired as error:
        result = subprocess.CompletedProcess(command, 124,
                    (error.stdout or b'').decode() if isinstance(error.stdout, bytes) else error.stdout or '',
                    (error.stderr or b'').decode() if isinstance(error.stderr, bytes) else error.stderr or '')
    (evidence / 'stdout.txt').write_text(result.stdout)
    (evidence / 'stderr.txt').write_text(result.stderr)
    for name in ('filtered-classes.txt', 'indexed-paths.txt', 'initial-ir-scores.tsv',
                 'oracle.tsv', 'pages.tsv', 'acceptedMappings.tsv', 'rejectedMappings.tsv'):
        if (work / name).exists():
            shutil.copy2(work / name, evidence / name)
    if (work / 'eval-results').exists():
        shutil.copytree(work / 'eval-results', evidence / 'eval-results')
    for terminal in work.glob('terminal-*.tsv'):
        shutil.copy2(terminal, evidence / terminal.name)
    for keyword in work.glob('keyword-*'):
        if keyword.is_file():
            shutil.copy2(keyword, evidence / keyword.name)
    scope = ('explicit missing-method-feedback control; not full paper reproduction' if args.missing_method_loop
             else 'original input pipeline and initial IR scoring; no iterative recommendations')
    if args.keyword_control:
        scope = 'controlled method-keyword extraction and sanitization; synthetic inputs, not a recovered graph'
    report = {'scope': scope, 'revision': REVISION,
              'returncode': result.returncode, 'command': command,
              'original_sources_modified': args.unique_maximum_control,
              'selector_variant': 'unique-maximum-only' if args.unique_maximum_control else 'original',
              'selector_change': selector_change,
              'retrieval_limit_override': args.retrieval_limit,
              'source_files_compiled': len(sources),
              'artifact_sha256': {path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                                  for path in evidence.iterdir() if path.is_file()}}
    (evidence / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(result.stdout[-3000:])
    print(result.stderr[-2000:])
    result.check_returncode()


if __name__ == '__main__':
    main()
