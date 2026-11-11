"""Build an evidence-linked research-in-progress presentation from slide records."""

import hashlib
import json
from pathlib import Path

from pptx import Presentation
from pptx.util import Inches

from build_pilot_publication import base, rectangle, text, TEAL, ORANGE, MUTED


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'research/publications/2026-11-11-research-briefing'


def main():
    specification = json.loads((OUT / 'slides.json').read_text())
    deck = Presentation()
    deck.slide_width, deck.slide_height = Inches(13.333), Inches(7.5)
    digest_inputs = {OUT / 'slides.json', Path(__file__).resolve(),
                     ROOT / 'scripts/build_pilot_publication.py'}
    reading = ['# 研究中汇报：逐页内容与证据', '']
    for index, record in enumerate(specification['slides'], 1):
        sources = [specification['sources'][key] for key in record['sources']]
        footer = '；'.join(f'{key} {specification["sources"][key]["short"]}'
                          for key in record['sources'])
        slide = base(deck, record['title'], record['subtitle'], footer)
        slide.shapes[-1].text_frame.paragraphs[0].runs[0].text = (
            f'{index:02d} / {len(specification["slides"])}')
        count = len(record['cards'])
        width = (11.7 - .3 * (count - 1)) / count
        for card_index, card in enumerate(record['cards']):
            left = .8 + card_index * (width + .3)
            rectangle(slide, left, 1.95, width, 3.7)
            text(slide, card['heading'], left + .18, 2.15, width - .36, .7,
                 23 if count < 3 else 20, TEAL, True)
            text(slide, card['body'], left + .18, 3.0, width - .36, 2.48,
                 20 if count < 3 else 17)
        text(slide, record['takeaway'], .9, 5.95, 11.5, .78, 21, ORANGE)
        notes = [record.get('notes', ''), '', '证据与原始出处：']
        reading += [f'## {index:02d} {record["title"]}', '', record['subtitle'], '']
        for card in record['cards']:
            reading += [f'### {card["heading"]}', '', card['body'], '']
        reading += [record['takeaway'], '', record.get('notes', ''), '']
        for source in sources:
            notes.append(source['title'])
            if source.get('url'):
                notes.append(source['url'])
                reading += [f'- [{source["title"]}]({source["url"]})']
            for relative in source.get('paths', []):
                path = ROOT / relative
                assert path.is_file(), relative
                digest_inputs.add(path)
                notes.append(relative)
                reading += [f'- 本地证据：`{relative}`']
        reading.append('')
        slide.notes_slide.notes_text_frame.text = '\n'.join(notes)
    deck.core_properties.title = specification['title']
    deck.core_properties.author = '研究团队（署名待确认）'
    deck.core_properties.subject = '研究动机、相关工作、复现边界与后续实验；非结题报告'
    deck.save(OUT / 'research-briefing.pptx')
    (OUT / 'SLIDE-NOTES.md').write_text('\n'.join(reading) + '\n')
    manifest = {
        'date': '2026-11-11', 'slides': len(deck.slides),
        'inputs': [{'path': str(path.relative_to(ROOT)),
                    'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
                   for path in sorted(digest_inputs)],
        'new_detection_or_kernel_experiments': False,
    }
    (OUT / 'evidence-manifest.json').write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    print(f'Built {len(deck.slides)} slides in {OUT}')


if __name__ == '__main__':
    main()
