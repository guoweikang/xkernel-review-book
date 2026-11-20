"""Controlled checks for asset coverage and literal retrieval boundaries."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from research_lookup import TEXT_LIMIT, inventory, retrieve


def main():
    with TemporaryDirectory() as temporary:
        root = Path(temporary)
        evidence = root / 'research/evidence'
        evidence.mkdir(parents=True)
        (root / 'research/note.md').write_text('角色反转\nSourcererCC failed\n')
        (root / 'research/catalog.json').write_text(json.dumps({'groups': [
            {'id': 'discovery', 'documents': ['note.md']}]}))
        (evidence / 'manifest.json').write_text(json.dumps({'records': [
            {'path': 'originals/missing.pdf', 'source_id': 'P01', 'status': 'downloaded'},
            {'source_id': 'failed-download', 'status': 'failed'}]}))
        (evidence / 'large.log').write_text('a' * (TEXT_LIMIT + 1))
        (evidence / 'bad.txt').write_bytes(b'\xff')
        (evidence / 'outside.txt').symlink_to('/etc/passwd')
        records = list(inventory(root))
        by_path = {record['path']: record for record in records}
        assert by_path['research/evidence/originals/missing.pdf']['status'] == 'missing'
        assert by_path['research/evidence/large.log']['status'] == 'metadata-only-size'
        assert by_path['research/evidence/bad.txt']['status'] == 'unreadable-text'
        assert by_path['research/evidence/outside.txt']['status'] == 'outside-root'
        hits = retrieve(records, ['角色反转'], topic='discovery')
        assert len(hits) == 1 and hits[0]['excerpts'][0]['line'] == 1
        assert retrieve(records, ['sourcerercc', 'failed'], require_all=True)
        assert not retrieve(records, ['SourcererCC', 'unknown'], require_all=True)
        assert retrieve(records, ['P01'], kind='source')[0]['status'] == 'missing'
        assert retrieve(records, ['failed-download'], kind='source')[0]['status'] == 'no-local-path'
        assert not retrieve(records, ['SourcererCC'], kind='run')
        (root / 'research/note.md').write_text('新的结果')
        assert not retrieve(list(inventory(root)), ['角色反转'])
        assert retrieve(list(inventory(root)), ['新的结果'])
        (root / 'research/note.md').unlink()
        assert not retrieve(list(inventory(root)), ['新的结果'])
    print('PASS: lookup coverage, Chinese/case/AND/filter/line checks, missing and excluded assets, fresh edits/deletion')


if __name__ == '__main__':
    main()
