"""Compare selected pinned original files without running InMap."""

import argparse
import difflib
import hashlib
import json
from pathlib import Path
import shutil
import urllib.error
import urllib.parse
import urllib.request


ROOT = Path(__file__).resolve().parents[1]
REVISIONS = {'pre-paper-candidate': 'cae17d87f8c17d8108d21abd41e0520b6ca65d7c',
             'current-audited': '6921e580c9dc009731010fe671942f19938fe236'}
FILES = ('.classpath', 'src/recommender/ir/IRAnalysis.java',
         'src/recommender/Evaluator.java', 'test-systems/Jabref/config-jabref.json')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    shutil.copy2(__file__, args.output / 'collector.py')
    provenance = []
    records = {}
    for label, revision in REVISIONS.items():
        for path in FILES:
            url = ('https://git.cs.kau.se/api/v4/projects/683/repository/files/'
                   + urllib.parse.quote(path, safe='') + '/raw?ref=' + revision)
            name = label + '__' + path.replace('/', '__')
            record = {'revision': revision, 'source_path': path, 'file': name, 'url': url}
            try:
                content = urllib.request.urlopen(url, timeout=60).read()
            except urllib.error.HTTPError as error:
                if error.code != 404:
                    raise
                record['status'] = 'http_404'
            else:
                (args.output / name).write_bytes(content)
                record.update(status='downloaded', bytes=len(content),
                              sha256=hashlib.sha256(content).hexdigest())
                records[(label, path)] = content
            provenance.append(record)
            (args.output / 'provenance.json').write_text(json.dumps(provenance, indent=2) + '\n')
    comparisons = []
    patches = []
    for path in FILES:
        before = records.get(('pre-paper-candidate', path))
        after = records.get(('current-audited', path))
        comparisons.append({'path': path, 'both_downloaded': before is not None and after is not None,
                            'byte_identical': before == after if before is not None and after is not None else None})
        if before is not None and after is not None:
            patches.extend(difflib.unified_diff(before.decode().splitlines(keepends=True),
                after.decode().splitlines(keepends=True), fromfile='pre-paper/' + path,
                tofile='current/' + path))
    (args.output / 'selected.diff').write_text(''.join(patches))
    report = {'revisions': REVISIONS, 'comparisons': comparisons,
              'scope': 'four selected files only; paper experiment revision not established'}
    (args.output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
