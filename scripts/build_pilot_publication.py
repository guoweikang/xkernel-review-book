"""Build the evidence-bound pilot manuscript and ten-slide editable presentation."""

import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.util import Inches, Pt as SlidePt

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'research/publications/2026-11-11-pilot-draft'
NAVY = '101D31'
WHITE = 'F4F7FB'
MUTED = 'A9BCD1'
TEAL = '40D9BF'
ORANGE = 'FFBE70'
PANEL = '1B2E47'
FONT = 'Noto Sans CJK SC'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def evidence():
    names = [
        'research/evidence/runs/2026-11-05-rust-baseline-corpus-01/report.json',
        'research/evidence/runs/2026-11-05-rust-scc-01/report.json',
        'research/evidence/runs/2026-11-09-source-doc-inventory-02/report.json',
        'research/evidence/runs/2026-11-09-doc-tfidf-01/report.json',
        'research/evidence/runs/2026-11-09-doc-tfidf-review-01/report.json',
        'research/protocols/discovery-ledger-v4.json',
        'research/notes/2026-11-05-metadata-paired-validation.md',
        'research/notes/2026-11-05-metadata-case-disposition.md',
        'research/evidence/runs/2026-11-11-bigclone-download-probe-01/report.json',
        'research/evidence/runs/2026-11-09-doc-tfidf-01/review-queue.json',
    ]
    reports = [json.loads((ROOT / name).read_text()) for name in names[:6]]
    assert reports[0]['files'] == 88 and reports[0]['units'] == 2180
    assert reports[1]['eligible_units'] == 812 and reports[1]['unique_pairs'] == 156
    assert reports[2]['with_literal_docs'] == 780
    assert reports[3]['top20_scc_overlap'] == 1
    assert reports[4]['both_below_65_tokens'] == 19
    old = {tuple(sorted(member['id'] for member in pair['members']))
           for pair in reports[5]['records'] if pair['review_status'] == 'reviewed'}
    new = {tuple(pair['unit_ids']) for pair in json.loads((ROOT / names[-1]).read_text())}
    assert len(old) == 18 and len(new) == 20 and len(old & new) == 0
    manifest = {'date': '2026-11-11', 'reviewed_pair_union': len(old | new),
                'independent_samples': False,
                'inputs': [{'path': name, 'sha256': sha(ROOT / name)} for name in names]}
    (OUT / 'evidence-manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')


def font(style, name, size):
    style.font.name = name
    style.font.size = Pt(size)
    style.element.get_or_add_rPr().rFonts.set(qn('w:eastAsia'), name)


def manuscript():
    document = Document()
    section = document.sections[0]
    section.page_width, section.page_height = Cm(21), Cm(29.7)
    section.top_margin = section.bottom_margin = Cm(2.1)
    section.left_margin = section.right_margin = Cm(2.2)
    font(document.styles['Normal'], 'Noto Serif CJK SC', 10.5)
    document.styles['Normal'].paragraph_format.space_after = Pt(5)
    document.styles['Normal'].paragraph_format.line_spacing = 1.15
    for name, size in [('Title', 20), ('Heading 1', 15), ('Heading 2', 12)]:
        font(document.styles[name], FONT, size)
    header = section.header.paragraphs[0]
    header.text = 'Rust系统代码重构机会研究  |  探索性实证初稿 v0.1'
    font(document.styles['Header'], FONT, 8)
    footer = section.footer.paragraphs[0]
    footer.alignment = 2
    footer.add_run('2026-11-11  •  ')
    field = OxmlElement('w:fldSimple')
    field.set(qn('w:instr'), 'PAGE')
    footer._p.append(field)
    lines = (OUT / 'paper.md').read_text().splitlines()
    index = 0
    while index < len(lines):
        line = lines[index].strip()
        if not line:
            index += 1
            continue
        if line.startswith('|'):
            rows = []
            while index < len(lines) and lines[index].strip().startswith('|'):
                row = [cell.strip() for cell in lines[index].strip().strip('|').split('|')]
                if not all(re.fullmatch(r'[-: ]+', cell) for cell in row):
                    rows.append(row)
                index += 1
            table = document.add_table(rows=0, cols=len(rows[0]))
            table.style = 'Light Shading Accent 1'
            for cells in rows:
                row = table.add_row()
                for cell, text in zip(row.cells, cells):
                    cell.text = text
                    for paragraph in cell.paragraphs:
                        paragraph.paragraph_format.space_after = Pt(3)
                        for run in paragraph.runs:
                            run.font.size = Pt(8)
                properties = row._tr.get_or_add_trPr()
                properties.append(OxmlElement('w:cantSplit'))
            continue
        if line.startswith('# '):
            document.add_paragraph(line[2:], 'Title')
        elif line.startswith('### '):
            document.add_heading(line[4:], 2)
        elif line.startswith('## '):
            document.add_heading(line[3:], 1)
        elif line.startswith('- '):
            document.add_paragraph(line[2:], 'List Bullet')
        else:
            document.add_paragraph(line)
        index += 1
    document.core_properties.title = '从相似候选到重构机会：Rust系统代码的证据约束实证试点'
    document.core_properties.author = '研究团队（署名待确认）'
    document.core_properties.subject = '探索性实证研究初稿；无独立准确率或性能增益结论'
    document.save(OUT / 'paper.docx')


def text(slide, content, left, top, width, height, size=22, color=WHITE, bold=False):
    box = slide.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(height))
    frame = box.text_frame
    frame.word_wrap = True
    frame.margin_left = frame.margin_right = Inches(0.02)
    frame.margin_top = frame.margin_bottom = Inches(0.02)
    for index, line in enumerate(content.split('\n')):
        paragraph = frame.paragraphs[0] if index == 0 else frame.add_paragraph()
        paragraph.text = line
        paragraph.font.name = FONT
        paragraph.font.size = SlidePt(size)
        paragraph.font.bold = bold
        paragraph.font.color.rgb = RGBColor.from_string(color)
        paragraph.space_after = SlidePt(9)
    return box


def rectangle(slide, left, top, width, height, color=PANEL):
    shape = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(left), Inches(top), Inches(width), Inches(height))
    shape.fill.solid()
    shape.fill.fore_color.rgb = RGBColor.from_string(color)
    shape.line.fill.background()
    return shape


def base(deck, title, subtitle, source):
    slide = deck.slides.add_slide(deck.slide_layouts[6])
    slide.background.fill.solid()
    slide.background.fill.fore_color.rgb = RGBColor.from_string(NAVY)
    rectangle(slide, 0.55, 0.42, 0.08, 0.45, TEAL)
    text(slide, title, 0.8, 0.35, 11.8, 0.65, 28, bold=True)
    text(slide, subtitle, 0.8, 1.1, 11.8, 0.6, 15, MUTED)
    rectangle(slide, 0.8, 6.88, 11.7, 0.015, PANEL)
    text(slide, source, 0.8, 7.0, 10.9, 0.28, 9, MUTED)
    text(slide, f'{len(deck.slides):02d} / 10', 11.6, 6.99, 1, 0.3, 10, TEAL)
    return slide


def card(slide, left, top, width, title, body, color=TEAL):
    rectangle(slide, left, top, width, 2.05)
    text(slide, title, left + .2, top + .18, width - .4, .5, 23, color, True)
    text(slide, body, left + .2, top + .85, width - .4, 1.12, 17)


def presentation():
    deck = Presentation()
    deck.slide_width, deck.slide_height = Inches(13.333), Inches(7.5)
    slide = base(deck, '从相似候选到重构机会', 'Rust系统代码的证据约束实证试点  /  2026.11.11', '研究初稿 v0.1 · 作者与单位待确认 · 非最终投稿结论')
    text(slide, '发现共同实现\n不等于值得合并', .9, 2.0, 8.5, 2.2, 40, bold=True)
    text(slide, '以xkernel为试验场，分开相似性、共享前提、行为验证与优化收益。', .9, 4.6, 11.4, .9, 23, MUTED)
    text(slide, '当前定位：可复现的探索性研究，而非已验证的新算法', .9, 6.0, 11.4, .5, 20, TEAL)

    slide = base(deck, '01  问题：相似与可重构之间缺少什么？', '最终目标：保持行为与性能，让代码更简洁、维护成本更低。', '正文 §1、§3 · 文献 [1] SourcererCC；[3] Librarian')
    card(slide, .8, 2.05, 3.7, '用途相似', '可能已有委托\n并非独立重复算法')
    card(slide, 4.8, 2.05, 3.7, '正文相似', '类型、锁与配置不同\n可能不能直接替换')
    card(slide, 8.8, 2.05, 3.7, '测试通过', '只覆盖已测行为\n不证明维护净收益')
    text(slide, '研究问题：候选差异从何而来？需要哪些约束？验证能支持多强的结论？', .9, 4.8, 11.5, 1.1, 23)

    slide = base(deck, '02  已有方法与本研究定位', '不是把不同任务的分数拼成排行榜。', '参考文献 [1] arXiv:1512.06448v1；[2] 2006.14505v1；[3] 2506.11058v3；[4] sklearn 1.7')
    rows = [('词法克隆', 'SourcererCC', '本轮已运行Rust输入适配'), ('注释辅助发现', 'LDA相关研究', '本轮采用TF-IDF简单基线，非LDA复现'), ('共享库重构', 'Librarian / MiniCode', '借鉴生成与评价分离，尚未复现')]
    for index, (kind, method, status) in enumerate(rows):
        top = 2.0 + index * 1.3
        rectangle(slide, .8, top, 11.7, 1.05)
        text(slide, kind, 1.0, top + .2, 2.4, .6, 21, TEAL)
        text(slide, method, 3.55, top + .2, 3.3, .6, 21)
        text(slide, status, 7.0, top + .15, 5.15, .8, 16, MUTED)
    text(slide, '贡献候选：约束缺口的实证分析与可复现工具链；尚无方法优越性证据。', .9, 6.1, 11.6, .5, 18, ORANGE)

    slide = base(deck, '03  方法：候选、证据、验证、收益分层', '已实现部分与拟议扩展明确分开。', '正文 §4 · E1–E7；工具／模型边界为研究设计，不是通用能力定理')
    for index, (title, body) in enumerate([('固定输入', '源码／配置／哈希'), ('工具发现', 'token／原生文档'), ('上下文核查', '类型／委托／契约'), ('验证与取舍', '行为／性能／维护')]):
        left = .8 + index * 3.0
        rectangle(slide, left, 2.25, 2.7, 1.75)
        text(slide, title, left + .15, 2.5, 2.4, .5, 22, TEAL, True)
        text(slide, body, left + .15, 3.25, 2.4, .6, 15)
    text(slide, '工具：提取、排序、执行检查、留存证据\n模型：辅助开放式解释与方案；当前审阅未经独立人工复核\n维护者：结合证据决定是否采纳，允许保留现状', .95, 4.6, 11.4, 1.85, 20)

    slide = base(deck, '04  试验范围与数据覆盖', '固定提交7e3ac944… · 四个包，不代表整个xkernel或所有Rust工程。', 'E1 源码语料；E3 文档绑定报告 · 路径提示不等于实际生产／测试配置')
    card(slide, .8, 1.95, 3.7, '88 文件', 'kvfs / kspin\nklazy / macros')
    card(slide, 4.8, 1.95, 3.7, '2,180 单元', '有函数体的归档单元\n未展开宏与cfg')
    card(slide, 8.8, 1.95, 3.7, '780 文档', '直接非空文档\n覆盖率 35.8%')
    rectangle(slide, 1.0, 4.65, 11.1, .45)
    rectangle(slide, 1.0, 4.65, 11.1 * 780 / 2180, .45, TEAL)
    text(slide, '780 有直接文档', 1, 5.3, 5, .5, 20, TEAL)
    text(slide, '1,400 缺失或为空', 7.1, 5.3, 5, .5, 20, MUTED)
    text(slide, '不能静默排除无文档函数，再宣称全仓有效。', 1, 6.15, 11.2, .45, 19, ORANGE)

    slide = base(deck, '05  关键结果：候选增量存在门槛混杂', '两个基线的可评价对象与选择规则不同，暂不能比较谁更优。', 'E2 SCC报告；E4 TF-IDF报告；E5 逐对token门槛核查')
    card(slide, .8, 2, 5.65, 'SourcererCC', '812个长度合格单元 → 156对\n最少65 token；重叠阈值0.8')
    card(slide, 6.85, 2, 5.65, '原生文档 TF-IDF', '780个非零向量 → 固定top20\n其中1对与SCC全体输出重叠')
    text(slide, '19 对“新增” ≠ 19 个语义漏检', .95, 4.65, 11.4, .8, 31, ORANGE, True)
    text(slide, '19对的两个函数都低于旧基线65-token门槛。\n下一轮先控制对象范围与审阅预算，再检验增益。', .95, 5.55, 11.4, 1.0, 21)

    slide = base(deck, '06  文档top20的源码核查', '单助手静态开发审阅；类别是主解释，不是独立真值或误报率。', 'E5 reviews.json · 各类别可能同时存在；无自动语义分类器')
    for index, (label, count, color) in enumerate([('配置互斥版本', 2, MUTED), ('角色或契约差异', 7, ORANGE), ('已有委托', 6, TEAL), ('小重叠，收益未知', 5, '84ABF3')]):
        top = 2.05 + index * .9
        text(slide, label, .9, top, 4.3, .5, 21)
        rectangle(slide, 5.5, top + .08, count * .75, .36, color)
        text(slide, str(count), 11.3, top - .03, 1, .55, 24, color, True)
    text(slide, '没有确认净收益机会 ≠ 全部候选都是误报', .95, 6.12, 11.5, .5, 20, ORANGE)

    slide = base(deck, '07  一个可解释的失败：相同词，不同角色', 'with_permission 与 with_node_type：文档cosine在本表示下为1。', 'E5 rank6 · 开发反例；不作为后续新方法的独立测试样本')
    card(slide, .8, 2.15, 5.65, '替换权限，保持类型', '权限掩码\n类型位保持不变', TEAL)
    card(slide, 6.85, 2.15, 5.65, '替换类型，保持权限', '类型位移\n权限位保持不变', ORANGE)
    text(slide, '词袋保留了词汇，却丢失“谁改变、谁保持”的关系。', .95, 4.75, 11.4, .9, 27, bold=True)
    text(slide, '研究线索：角色／契约表示能否减少混淆？需要对照与消融，不预设成功。', .95, 6.0, 11.4, .6, 18, MUTED)

    slide = base(deck, '08  重构案例：通过测试，仍暂缓采纳', '测试metadata构造抽取：行为证据与维护收益分开判断。', 'E7 成对验证及后续非unittest构建 · 一个案例，不是188个独立成功样本')
    card(slide, .8, 1.95, 3.7, '94 / 94', '原版与候选各94项通过\n同配置、同初始磁盘模板')
    card(slide, 4.8, 1.95, 3.7, '−5 行', '增加25、删除30\n涉及4文件并新增模块')
    card(slide, 8.8, 1.95, 3.7, '收益未知', '非测试构建通过\n没有性能改善测量', ORANGE)
    text(slide, '可提取  ≠  值得立即重构', .95, 4.7, 11.4, .8, 34, ORANGE, True)
    text(slide, '已覆盖行为未回归；不能证明全行为等价、所有配置安全或维护净收益为正。', .95, 5.8, 11.4, .8, 21)

    slide = base(deck, '09  结论与下一阶段', '现有材料足以形成探索性初稿，尚不足以支持完整方法优越性论文。', '正文 §8–§10 · E8 BigClone仅入口预检，未取得数据正文或运行基准')
    card(slide, .8, 1.95, 5.65, '已经具备', '可追溯工具与原始结果\n门槛混杂、约束案例、成对测试')
    card(slide, 6.85, 1.95, 5.65, '必须补齐', '同范围对照、独立标签、消融\n性能／维护收益、跨项目验证', ORANGE)
    text(slide, '公开基准 → Rust受控机制集 → 独立工程验证', .95, 4.8, 11.4, .75, 27, TEAL, True)
    text(slide, '论文与专利贡献由查新和实验决定；不把计划当结果，不把工具数量当创新。', .95, 5.9, 11.4, .8, 20)
    assert len(deck.slides) == 10
    for index, slide in enumerate(deck.slides):
        slide.notes_slide.notes_text_frame.text = (
            f'第{index + 1}页。完整方法、有效性威胁和参考文献见同目录paper.docx／paper.md。'
            'E编号对应论文附录A；本汇报为探索性实证试点，不报告独立准确率或性能提升。')
    deck.core_properties.title = '从相似候选到重构机会：Rust系统代码实证试点'
    deck.core_properties.author = '研究团队（署名待确认）'
    deck.save(OUT / 'slides.pptx')


def main():
    evidence()
    manuscript()
    presentation()
    (OUT / 'requirements.txt').write_text(subprocess.check_output(
        [sys.executable, '-m', 'pip', 'freeze'], text=True))
    print(f'Built {OUT / "paper.docx"} and ten-slide slides.pptx')


if __name__ == '__main__':
    main()
