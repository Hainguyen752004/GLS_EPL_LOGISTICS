# -*- coding: utf-8 -*-
"""Chuyển ba bản hướng dẫn từ Markdown sang Word (.docx).

Không dùng thư viện chuyển đổi tổng quát: tài liệu này chỉ dùng một tập hẹp các
thành phần (tiêu đề, đoạn, bảng, danh sách, trích dẫn, khối mã), nên đọc thẳng
và dựng đúng kiểu Word cho từng thứ thì kiểm soát được bố cục in ra.

Chữ Lào cần phông riêng: Word mặc định dựng chữ Lào bằng phông thay thế, dấu
thanh rơi lệch khỏi phụ âm. Đặt phông cho cả ba vùng (ascii, hAnsi, cs) và
thêm w:lang cho vùng chữ phức hợp.
"""
import re
import sys
import io

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Pt, RGBColor, Cm

XANH = RGBColor(0x1F, 0x4E, 0x79)
XAM = RGBColor(0x59, 0x59, 0x59)
VIEN = RGBColor(0xD0, 0xD0, 0xD0)


PHONG_LAO = 'Leelawadee UI'      # phông duy nhất trên máy này có glyph chữ Lào
PHONG_KY_HIEU = 'Segoe UI Symbol'  # mũi tên, khung kẻ, ⚡ ⚠ ✍ 📍 ☁ ↻ ⌂


def co_lao(s):
    """Consolas không có glyph chữ Lào: dùng nó là ra ô vuông. Đo trước khi chọn phông."""
    return any(0x0E80 <= ord(c) <= 0x0EFF for c in s)


def phong_cho(ch, phong):
    """Phông nào vẽ được ký tự này.

    Word KHÔNG tự thay phông khi phông đã chỉ định thiếu glyph trong tệp .docx —
    nó vẽ ô vuông. Đã đo trên máy: Calibri thiếu chữ Lào và thiếu ⚡ ⚠ ✍ 📍 ☁ ↻ ⌂;
    Leelawadee UI có chữ Lào nhưng thiếu mũi tên và khung kẻ. Nên chọn theo từng
    ký tự chứ không theo từng đoạn.
    """
    m = ord(ch)
    if 0x0E80 <= m <= 0x0EFF:
        return PHONG_LAO
    if m >= 0x2190:              # mũi tên trở lên: hình học, khung kẻ, biểu tượng, emoji
        return PHONG_KY_HIEU
    return phong


def ghi_run(p, chu, phong, co, dam=None, mau=None, nghieng=False):
    """Ghi chuỗi thành nhiều run, cắt tại chỗ đổi phông."""
    i = 0
    while i < len(chu):
        f = phong_cho(chu[i], phong)
        j = i + 1
        while j < len(chu) and phong_cho(chu[j], phong) == f:
            j += 1
        r = p.add_run(chu[i:j])
        dat_phong(r, f, co, dam, mau)
        if nghieng:
            r.font.italic = True
        i = j


def dat_phong(run, ten, co=None, dam=None, mau=None, mono=False):
    run.font.name = ten
    r = run._element.rPr.rFonts
    for v in ('w:ascii', 'w:hAnsi', 'w:cs', 'w:eastAsia'):
        r.set(qn(v), ten)
    if co is not None:
        run.font.size = Pt(co)
        # Cỡ chữ cho vùng chữ phức hợp (chữ Lào nằm ở vùng này) phải đặt riêng,
        # nếu không Word dựng chữ Lào theo cỡ mặc định chứ không theo cỡ đã đặt.
        szcs = run._element.rPr.makeelement(qn('w:szCs'), {qn('w:val'): str(int(co * 2))})
        run._element.rPr.append(szcs)
    if dam is not None:
        run.font.bold = dam
    if mau is not None:
        run.font.color.rgb = mau


def viet(p, chu, phong, co, mau=None, dam_mac_dinh=False):
    """Ghi một đoạn, hiểu **đậm**, *nghiêng* và `mã` ở mức trong dòng."""
    # Mã đứng trước để dấu sao nằm trong `…` không bị hiểu là nhấn mạnh; cụm đậm
    # dùng .+? để ôm được cả nghiêng lồng bên trong (**… *cái này* …**) — nếu đòi
    # "không có dấu sao ở giữa" thì cụm đó vỡ, để lọt dấu sao thừa ra mặt giấy.
    for phan in re.split(r'(`[^`]+`|\*\*.+?\*\*|\*[^*`]+?\*)', chu):
        if not phan:
            continue
        if phan.startswith('**') and phan.endswith('**'):
            ghi_run(p, phan[2:-2].replace('*', ''), phong, co, True, mau)
        elif phan.startswith('`') and phan.endswith('`'):
            noi = phan[1:-1]
            ghi_run(p, noi, phong if co_lao(noi) else 'Consolas', co - 0.5,
                    dam_mac_dinh, RGBColor(0xB0, 0x30, 0x30))
        elif phan.startswith('*') and phan.endswith('*'):
            ghi_run(p, phan[1:-1], phong, co, dam_mac_dinh, mau, nghieng=True)
        else:
            ghi_run(p, phan, phong, co, dam_mac_dinh, mau)


def go_lien_ket(s):
    """[chữ](đường dẫn) → chữ. Tài liệu in ra không bấm được, giữ chữ là đủ."""
    return re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', s)


def chuyen(nguon, dich, phong, tieu_de_tai_lieu):
    dong = io.open(nguon, encoding='utf-8').read().split('\n')
    d = Document()

    st = d.styles['Normal']
    st.font.name = phong
    st.font.size = Pt(10.5)
    st.paragraph_format.space_after = Pt(6)
    st.paragraph_format.line_spacing = 1.15

    for s in d.sections:
        s.left_margin = s.right_margin = Cm(2.2)
        s.top_margin = s.bottom_margin = Cm(2.0)

    i = 0
    trong_muc_luc = False
    while i < len(dong):
        d0 = dong[i]
        s = d0.rstrip()
        t = s.strip()

        # --- Bảng: gom cả khối rồi dựng một lần ---
        if t.startswith('|') and i + 1 < len(dong) and re.match(r'^\s*\|[\s:|-]+\|\s*$', dong[i + 1]):
            hang = []
            while i < len(dong) and dong[i].strip().startswith('|'):
                r = dong[i].strip()
                if not re.match(r'^\|[\s:|-]+\|$', r):
                    hang.append([c.strip() for c in r.strip('|').split('|')])
                i += 1
            n = max(len(h) for h in hang)
            tb = d.add_table(rows=0, cols=n)
            tb.style = 'Table Grid'
            tb.alignment = WD_TABLE_ALIGNMENT.CENTER
            for k, h in enumerate(hang):
                o = tb.add_row().cells
                for j in range(n):
                    p = o[j].paragraphs[0]
                    p.paragraph_format.space_after = Pt(2)
                    viet(p, go_lien_ket(h[j] if j < len(h) else ''), phong, 9.5,
                         XANH if k == 0 else None, dam_mac_dinh=(k == 0))
                if k == 0:
                    for c in o:
                        bong = c._tc.get_or_add_tcPr().makeelement(
                            qn('w:shd'), {qn('w:fill'): 'EAF1F8', qn('w:val'): 'clear'})
                        c._tc.get_or_add_tcPr().append(bong)
            d.add_paragraph().paragraph_format.space_after = Pt(4)
            continue

        # --- Khối mã (sơ đồ luồng) ---
        if t.startswith('```'):
            i += 1
            noi = []
            while i < len(dong) and not dong[i].strip().startswith('```'):
                noi.append(dong[i])
                i += 1
            i += 1
            if co_lao('\n'.join(noi)):
                # Canh lề bằng khoảng trắng chỉ đúng với phông đều. Chữ Lào không có
                # phông đều ở đây, nên dựng lại thành các bước xếp dọc căn giữa —
                # đọc ra đúng thứ tự luồng mà không phụ thuộc bề rộng ký tự.
                for l in noi:
                    t2 = l.strip()
                    if not t2:
                        continue
                    q = d.add_paragraph()
                    q.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    q.paragraph_format.space_after = Pt(2)
                    mui_ten = set(t2) <= set('│▼─►| ')
                    ghi_run(q, t2, phong, 9 if mui_ten else 10.5,
                            False, XANH if mui_ten else None)
                d.add_paragraph().paragraph_format.space_after = Pt(4)
                continue
            p = d.add_paragraph()
            p.paragraph_format.left_indent = Cm(0.6)
            p.paragraph_format.space_before = Pt(6)
            p.paragraph_format.space_after = Pt(10)
            for k, l in enumerate(noi):
                r = p.add_run(l + ('\n' if k < len(noi) - 1 else ''))
                dat_phong(r, 'Consolas', 8.5)
            continue

        # --- Tiêu đề ---
        m = re.match(r'^(#{1,4})\s+(.*)$', t)
        if m:
            cap = len(m.group(1))
            chu = re.sub(r'\s*\{#.*\}$', '', m.group(2)).strip()
            trong_muc_luc = chu.lower() in ('contents', 'mục lục', 'ສາລະບານ')
            if cap == 1:
                p = d.add_paragraph()
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                p.paragraph_format.space_after = Pt(2)
                ghi_run(p, chu, phong, 21, True, XANH)
            else:
                p = d.add_paragraph()
                p.paragraph_format.space_before = Pt(14 if cap == 2 else 9)
                p.paragraph_format.space_after = Pt(4)
                ghi_run(p, chu, phong, {2: 15, 3: 12.5, 4: 11}[cap], True, XANH)
            i += 1
            continue

        # --- Đường kẻ ngang ---
        if re.match(r'^-{3,}$', t):
            p = d.add_paragraph()
            p.paragraph_format.space_before = Pt(2)
            p.paragraph_format.space_after = Pt(2)
            pr = p._p.get_or_add_pPr()
            b = pr.makeelement(qn('w:pBdr'), {})
            bot = b.makeelement(qn('w:bottom'), {
                qn('w:val'): 'single', qn('w:sz'): '6', qn('w:space'): '1', qn('w:color'): 'C9D6E4'})
            b.append(bot)
            pr.append(b)
            i += 1
            continue

        # --- Trích dẫn: gom nhiều dòng thành một khối có viền trái ---
        if t.startswith('>'):
            noi = []
            while i < len(dong) and dong[i].strip().startswith('>'):
                noi.append(dong[i].strip()[1:].strip())
                i += 1
            p = d.add_paragraph()
            p.paragraph_format.left_indent = Cm(0.5)
            p.paragraph_format.space_before = Pt(6)
            p.paragraph_format.space_after = Pt(8)
            pr = p._p.get_or_add_pPr()
            b = pr.makeelement(qn('w:pBdr'), {})
            b.append(b.makeelement(qn('w:left'), {
                qn('w:val'): 'single', qn('w:sz'): '18', qn('w:space'): '8', qn('w:color'): '1F4E79'}))
            pr.append(b)
            sh = pr.makeelement(qn('w:shd'), {qn('w:fill'): 'F4F8FC', qn('w:val'): 'clear'})
            pr.append(sh)
            viet(p, go_lien_ket(' '.join(x for x in noi if x)), phong, 10, XAM)
            continue

        # --- Danh sách ---
        m = re.match(r'^(\s*)([-*]|\d+\.)\s+(.*)$', d0)
        if m:
            muc = len(m.group(1)) // 2
            # Mục dài được ngắt dòng trong tệp Markdown cho dễ đọc. Những dòng tiếp
            # theo có thụt lề là PHẦN CÒN LẠI của mục này, không phải đoạn mới: tách
            # ra thì dòng tràn rơi ra ngoài dấu đầu dòng, đọc như một đoạn lạc.
            noi_tiep = [m.group(3)]
            i += 1
            while i < len(dong):
                x = dong[i]
                if (not x.strip() or not x[:1].isspace()
                        or re.match(r'^\s*([-*]|\d+\.)\s+', x)
                        or x.strip().startswith(('#', '>', '|', '```'))):
                    break
                noi_tiep.append(x.strip())
                i += 1
            m = (m.group(1), m.group(2), ' '.join(noi_tiep))
            p = d.add_paragraph()
            p.paragraph_format.left_indent = Cm(0.7 + 0.5 * muc)
            p.paragraph_format.first_line_indent = Cm(-0.35)
            p.paragraph_format.space_after = Pt(3)
            if trong_muc_luc:
                p.paragraph_format.space_after = Pt(1)
            dau = '• ' if not m[1][0].isdigit() else m[1] + ' '
            ghi_run(p, dau, phong, 10.5, False, XANH)
            viet(p, go_lien_ket(m[2]), phong, 10.5)
            continue

        # --- Đoạn văn: nối các dòng liền nhau (Markdown ngắt dòng cho dễ đọc) ---
        if t:
            noi = []
            while i < len(dong):
                x = dong[i].rstrip()
                if (not x.strip() or x.strip().startswith(('#', '>', '|', '```'))
                        or re.match(r'^\s*([-*]|\d+\.)\s+', x) or re.match(r'^-{3,}$', x.strip())):
                    break
                noi.append(x.strip())
                i += 1
            p = d.add_paragraph()
            p.paragraph_format.space_after = Pt(7)
            viet(p, go_lien_ket(' '.join(noi)), phong, 10.5)
            continue

        i += 1

    # Nhan đề tệp hiện trong thuộc tính tài liệu
    d.core_properties.title = tieu_de_tai_lieu
    d.core_properties.author = 'EPL Logistics'
    d.save(dich)
    print('  ->', dich)


if __name__ == '__main__':
    G = 'D:/Demo_Lao/EPL_System/docs/'
    viec = [
        (G + 'HUONG_DAN_SU_DUNG_VI.md', G + 'HUONG_DAN_SU_DUNG_VI.docx',
         'Calibri', 'EPL Logistics - Huong dan su dung'),
        (G + 'USER_GUIDE_EN.md', G + 'USER_GUIDE_EN.docx',
         'Calibri', 'EPL Logistics - User Guide'),
        (G + 'HUONG_DAN_SU_DUNG_LO.md', G + 'HUONG_DAN_SU_DUNG_LO.docx',
         'Leelawadee UI', 'EPL Logistics - Lao user guide'),
    ]
    for a, b, f, tt in viec:
        print(a)
        chuyen(a, b, f, tt)
