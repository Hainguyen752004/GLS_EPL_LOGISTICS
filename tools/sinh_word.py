# -*- coding: utf-8 -*-
"""Sinh tệp .docx từ một tệp Markdown (mặc định là bản đồ chức năng).

Tài liệu giao cho người dùng phải là Word, Markdown chỉ là bản nguồn. Chạy lại mỗi khi sửa .md:

    python tools/sinh_word.py                     # DOCS/md/BAN_DO_CHUC_NANG.md
    python tools/sinh_word.py DOCS/md/<tệp>.md    # tệp bất kỳ

Nguồn Markdown nằm ở DOCS/md, bản Word sinh ra nằm ở DOCS/word (cùng tên tệp). Tệp .md ngoài
thư mục DOCS/md thì .docx vẫn đặt cạnh nó như cũ.
"""
import io
import os
import re

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt, RGBColor

GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAC_DINH = os.path.join(GOC, 'DOCS', 'md', 'BAN_DO_CHUC_NANG.md')
THU_MUC_MD = os.path.join(GOC, 'DOCS', 'md')
THU_MUC_WORD = os.path.join(GOC, 'DOCS', 'word')

XANH = RGBColor(0x14, 0x5C, 0x4A)


def dam_va_ma(p, chu):
    """Viết một đoạn có **đậm**, *nghiêng* và `mã` thành các run đúng kiểu."""
    for phan in re.split(r'(\*\*[^*]+\*\*|\*[^*\s][^*]*\*|`[^`]+`)', chu):
        if not phan:
            continue
        if phan.startswith('**') and phan.endswith('**'):
            p.add_run(phan[2:-2]).bold = True
        elif len(phan) > 2 and phan.startswith('*') and phan.endswith('*'):
            p.add_run(phan[1:-1]).italic = True
        elif phan.startswith('`') and phan.endswith('`'):
            r = p.add_run(phan[1:-1])
            r.font.name = 'Consolas'
            r.font.size = Pt(9.5)
        else:
            p.add_run(phan)


def main():
    import sys
    nguon = sys.argv[1] if len(sys.argv) > 1 else MAC_DINH
    if not os.path.isabs(nguon):
        nguon = os.path.join(GOC, nguon)
    ten = os.path.splitext(os.path.basename(nguon))[0] + '.docx'
    if os.path.dirname(os.path.abspath(nguon)) == THU_MUC_MD:
        os.makedirs(THU_MUC_WORD, exist_ok=True)
        dich = os.path.join(THU_MUC_WORD, ten)
    else:
        dich = os.path.splitext(nguon)[0] + '.docx'
    dong = io.open(nguon, encoding='utf-8').read().split(chr(10))
    d = Document()
    d.styles['Normal'].font.name = 'Segoe UI'
    d.styles['Normal'].font.size = Pt(10.5)
    # 07/10: chữ Lào là "complex script" — đặt font cs (Leelawadee UI có sẵn trên Windows) cho mọi kiểu chữ, không thì Word
    # tự chọn font thiếu dấu. Bản tiếng Lào (tên tệp có _LO) lấy luôn Leelawadee UI làm font chính.
    from docx.oxml.ns import qn
    la_lao = '_LO' in os.path.basename(nguon).upper()
    for st in d.styles:
        try:
            rpr = st.element.get_or_add_rPr()
        except AttributeError:
            continue
        f = rpr.find(qn('w:rFonts'))
        if f is None:
            f = rpr.makeelement(qn('w:rFonts'), {})
            rpr.append(f)
        f.set(qn('w:cs'), 'Leelawadee UI')
        if la_lao:
            for k in ('w:ascii', 'w:hAnsi'):
                f.set(qn(k), 'Leelawadee UI')

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

        # khối lệnh ``` … ``` (có thể thụt vào dưới một ý đánh số): mỗi dòng một đoạn chữ Consolas, giữ nguyên
        if l.strip().startswith('```'):
            i += 1
            while i < len(dong) and not dong[i].strip().startswith('```'):
                p = d.add_paragraph()
                p.paragraph_format.left_indent = Pt(18)
                p.paragraph_format.space_after = Pt(0)
                r = p.add_run(dong[i].strip())
                r.font.name = 'Consolas'
                r.font.size = Pt(9)
                i += 1
            i += 1
            d.add_paragraph()
            continue
        # khối trích dẫn "> …" (hộp ghi chú đầu tài liệu): bỏ dấu ">", dựng như dòng thường rồi thụt lề — trước đây hiện
        # nguyên dấu ">" trong Word
        trich = l.lstrip().startswith('>')
        if trich:
            l = re.sub(r'^\s*>\s?', '', l)
        if not l.strip():
            i += 1
            continue
        # 07/10: ảnh màn hình "![chú thích](đường/dẫn.png)" (đường dẫn tương đối theo tệp .md) → ảnh rộng 16 cm + chú thích nghiêng
        anh = re.match(r'^\s*!\[([^\]]*)\]\(([^)]+)\)\s*$', l)
        if anh:
            duong = anh.group(2)
            if not os.path.isabs(duong):
                duong = os.path.join(os.path.dirname(os.path.abspath(nguon)), duong)
            if os.path.isfile(duong):
                from docx.shared import Cm
                d.add_picture(duong, width=Cm(16))
                d.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
                if anh.group(1).strip():
                    p = d.add_paragraph()
                    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    r = p.add_run(anh.group(1).strip())
                    r.italic = True
                    r.font.size = Pt(9)
            else:
                print('THIẾU ẢNH: %s' % duong)
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
            p = d.add_heading(l[4:], level=2)
        elif l.startswith('#### '):
            p = d.add_heading(l[5:], level=3)                                       # 3.2.1, 12.7.x…
        elif l.startswith('- ') or l.startswith('* '):
            p = d.add_paragraph(style='List Bullet')
            dam_va_ma(p, l[2:])
        elif re.match(r'^\d+\. ', l):
            p = d.add_paragraph(style='List Number')
            dam_va_ma(p, re.sub(r'^\d+\. ', '', l))
        elif re.match(r'^\s+[-*] ', l):
            p = d.add_paragraph(style='List Bullet 2')                              # ý con thụt (2 hay 3 dấu cách)
            dam_va_ma(p, l.strip()[2:])
        elif re.match(r'^\s+\d+\. ', l):
            p = d.add_paragraph(style='List Number 2')
            dam_va_ma(p, re.sub(r'^\s*\d+\. ', '', l))
        else:
            p = d.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            dam_va_ma(p, l.strip())
        if trich:
            p.paragraph_format.left_indent = Pt(18)
        i += 1

    d.save(dich)
    print('Đã sinh %s' % dich)


if __name__ == '__main__':
    main()
