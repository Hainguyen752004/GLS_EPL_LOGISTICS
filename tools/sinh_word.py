# -*- coding: utf-8 -*-
"""Sinh DOCS/BAN_DO_CHUC_NANG.docx từ tệp Markdown cùng tên.

Tài liệu giao cho người dùng phải là Word, Markdown chỉ là bản nguồn. Chạy lại mỗi khi sửa .md:

    python tools/sinh_word.py
"""
import io
import os
import re

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt, RGBColor

GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NGUON = os.path.join(GOC, 'DOCS', 'BAN_DO_CHUC_NANG.md')
DICH = os.path.join(GOC, 'DOCS', 'BAN_DO_CHUC_NANG.docx')

XANH = RGBColor(0x14, 0x5C, 0x4A)


def dam_va_ma(p, chu):
    """Viết một đoạn có **đậm** và `mã` thành các run đúng kiểu."""
    for phan in re.split(r'(\*\*[^*]+\*\*|`[^`]+`)', chu):
        if not phan:
            continue
        if phan.startswith('**') and phan.endswith('**'):
            p.add_run(phan[2:-2]).bold = True
        elif phan.startswith('`') and phan.endswith('`'):
            r = p.add_run(phan[1:-1])
            r.font.name = 'Consolas'
            r.font.size = Pt(9.5)
        else:
            p.add_run(phan)


def main():
    dong = io.open(NGUON, encoding='utf-8').read().split('\n')
    d = Document()
    d.styles['Normal'].font.name = 'Segoe UI'
    d.styles['Normal'].font.size = Pt(10.5)

    i = 0
    while i < len(dong):
        l = dong[i].rstrip()
        # bảng Markdown
        if l.startswith('|') and i + 1 < len(dong) and set(dong[i + 1].replace('|', '').strip()) <= set('-: '):
            dau = [o.strip() for o in l.strip('|').split('|')]
            i += 2
            than = []
            while i < len(dong) and dong[i].startswith('|'):
                than.append([o.strip() for o in dong[i].strip('|').split('|')])
                i += 1
            t = d.add_table(rows=1, cols=len(dau))
            t.style = 'Light Grid Accent 1'
            for c, chu in zip(t.rows[0].cells, dau):
                c.text = ''
                dam_va_ma(c.paragraphs[0], chu)
                for r in c.paragraphs[0].runs:
                    r.bold = True
            for h in than:
                o = t.add_row().cells
                for c, chu in zip(o, h):
                    c.text = ''
                    dam_va_ma(c.paragraphs[0], chu)
            d.add_paragraph()
            continue

        if not l.strip():
            i += 1
            continue
        if l.startswith('# '):
            p = d.add_heading(l[2:], level=0)
            for r in p.runs:
                r.font.color.rgb = XANH
        elif l.startswith('## '):
            p = d.add_heading(l[3:], level=1)
            for r in p.runs:
                r.font.color.rgb = XANH
        elif l.startswith('### '):
            d.add_heading(l[4:], level=2)
        elif l.startswith('- ') or l.startswith('* '):
            dam_va_ma(d.add_paragraph(style='List Bullet'), l[2:])
        elif re.match(r'^\d+\. ', l):
            dam_va_ma(d.add_paragraph(style='List Number'), re.sub(r'^\d+\. ', '', l))
        else:
            p = d.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            dam_va_ma(p, l)
        i += 1

    d.save(DICH)
    print('Đã sinh %s' % DICH)


if __name__ == '__main__':
    main()
