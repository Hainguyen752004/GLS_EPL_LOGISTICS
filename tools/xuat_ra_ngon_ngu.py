# -*- coding: utf-8 -*-
"""Tệp Excel rà tiếng Lào cho người bản ngữ (10/10 — anh Cello, bạn anh Khampla: "send me the localization review").

    python tools/xuat_ra_ngon_ngu.py [ra.xlsx]
    python tools/xuat_ra_ngon_ngu.py [ra.xlsx] --man theo-doi-tuyen --chu chu.json --anh anh.png      # riêng một màn

RIÊNG MỘT MÀN (10/10, anh Cello gửi ảnh màn Theo dõi tuyến): khoá mà mã của màn đó dùng (frontend/modules/<man>/, kể cả tab, hộp
chưa mở) + chữ menu / phần chung ĐANG HIỆN trên màn (--chu: các chuỗi gom từ trình duyệt ở tiếng Lào — khoá dùng chung mà câu Lào
khớp đúng một chuỗi trên màn). --anh: ảnh màn thật tiếng Lào, đặt ở trang Read me.

Ba cột chính theo anh Hải: Việt (trái) · Anh (giữa) · Lào (phải, điền sẵn câu đang dùng — anh Cello sửa thẳng, tô chữ ĐỎ). Thêm cột
Ghi chú (của người rà), Màn (nơi câu hiện), Lưu ý (câu mới / vừa sửa so với bản đã commit — nên xem kỹ); cột ẨN: ID (khoá để nhập lại)
và câu Lào GỐC (nguyên thẻ / chỗ chèn).
CHỮ DỄ ĐỌC (anh Hải 10/10: bản đầu còn "dấu của code"): bỏ thẻ HTML — tiêu đề phụ <span class="sub"> / <small> xuống dòng thứ hai,
<b> <i> <span> khác bỏ thẻ giữ chữ; chỗ máy chèn {n} {ten} (trang 1, 4) / {1} {2} (trang 2, 3) → ① ② … đánh số theo thứ tự xuất hiện
trong câu tiếng Việt, cùng số ở cả ba cột (de_doc). Nhập lại: ① → tên chỗ chèn theo cột gốc; câu có thẻ thì ráp thẻ lại tay.
Bốn trang: 1 chữ trên các màn (frontend/js/ngon_ngu.js, đang dùng — tools/xuat_ra_ngon_ngu.js gắn màn) · 2 câu báo của máy chủ
(backend/app/services/loi_dich.json) · 3 câu báo của hệ kế toán chuyển sang (loi_dich_ke_toan.json) · 4 chữ cũ có thể không còn dùng.
Nhận tệp về: so cột Lào với bản xuất (khoá ở cột ID, trang 2–3 khoá là câu tiếng Việt) rồi ghi lại vào ngon_ngu.js / loi_dich*.json."""
import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys
import tempfile

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

GOC = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
NGAY = dt.date.today()
_ts = argparse.ArgumentParser()
_ts.add_argument("ra", nargs="?")
_ts.add_argument("--man", help="id thư mục màn trong frontend/modules — chỉ xuất màn đó")
_ts.add_argument("--chu", help="JSON: các chuỗi đang hiện trên màn (tiếng Lào)")
_ts.add_argument("--anh", help="ảnh màn thật tiếng Lào, đặt ở trang Read me")
TS = _ts.parse_args()
RA = TS.ra or os.path.join(GOC, "DOCS", "gui_anh_Cello_%s" % NGAY.strftime("%d_%m"),
                           "EPL_Lao_language_review_%s%s.xlsx" % ("%s_" % TS.man if TS.man else "", NGAY.isoformat()))

# ---------------------------------------------------------------- dữ liệu
tam = tempfile.mkdtemp()
subprocess.run(["node", os.path.join(GOC, "tools", "xuat_ra_ngon_ngu.js"), os.path.join(tam, "ui.json")], check=True)
UI = json.load(open(os.path.join(tam, "ui.json"), encoding="utf-8"))


def tu_dien_js(van):
    """Đọc nội dung ngon_ngu.js (chuỗi) → dict khoá → {vi, lo, en}."""
    f = os.path.join(tam, "nn.js")
    open(f, "w", encoding="utf-8").write(van)
    ra = subprocess.run(["node", "-e", "global.window={};require(process.argv[1]);process.stdout.write(JSON.stringify(window.EPL_TU_DIEN))", f],
                        check=True, capture_output=True)
    return json.loads(ra.stdout.decode("utf-8"))


try:
    CU = tu_dien_js(subprocess.run(["git", "show", "HEAD:frontend/js/ngon_ngu.js"], cwd=GOC, check=True, capture_output=True)
                    .stdout.decode("utf-8"))
except subprocess.CalledProcessError:
    CU = {}


def luu_y(keys, vi, en, lo):
    """'New' — khoá chưa có ở bản đã commit; 'Changed' — có nhưng câu khác."""
    if all(k not in CU for k in keys):
        return "New"
    if any(k in CU and (CU[k].get("vi"), CU[k].get("en"), CU[k].get("lo")) != (vi, en, lo) for k in keys):
        return "Changed"
    return ""


def tin(tep):
    return json.load(open(os.path.join(GOC, "backend", "app", "services", tep), encoding="utf-8"))


def tin_cu(tep):
    """Bản đã commit của tệp câu báo — để đánh dấu câu mới / vừa sửa."""
    try:
        return json.loads(subprocess.run(["git", "show", "HEAD:backend/app/services/" + tep], cwd=GOC, check=True,
                                         capture_output=True).stdout.decode("utf-8"))
    except (subprocess.CalledProcessError, ValueError):
        return {}


def luu_y_cau(cu, k, v):
    if k not in cu:
        return "New"
    return "Changed" if (cu[k].get("en"), cu[k].get("lo")) != (v.get("en"), v.get("lo")) else ""


CU_LOI, CU_LOI_KT = tin_cu("loi_dich.json"), tin_cu("loi_dich_ke_toan.json")

VONG = "①②③④⑤⑥⑦⑧⑨⑩⑪⑫"
CHEN_UI, CHEN_SO = re.compile(r"\{([A-Za-z_][A-Za-z0-9_]*)\}"), re.compile(r"\{(\d+)\}")


def de_doc(vi, en, lo, chen):
    """(vi, en, lo) dạng người đọc: bỏ thẻ, chỗ chèn → ①②… (cùng số cho cùng tên ở cả ba câu, đánh theo câu tiếng Việt)."""
    so = {}

    def mot(t):
        t = re.sub(r'<span class="sub">|<small>|<br\s*/?>', "\n", t or "")
        t = re.sub(r"</?(?:b|i|span|small|strong|em)\b[^>]*>", "", t)

        def thay(m):
            if m.group(1) not in so:
                so[m.group(1)] = VONG[len(so)] if len(so) < len(VONG) else "[" + m.group(1) + "]"
            return so[m.group(1)]
        return chen.sub(thay, t).strip("\n")
    return mot(vi), mot(en), mot(lo)


def vun(k):
    """Mảnh câu vụn bộ trích lấy ra từ chuỗi ghép bên kế toán (bắt đầu bằng ")", "}", ":", "." …, hoặc còn "{(") — không bao giờ hiện
    thành một câu, người rà không sửa được: không đưa vào tệp. Cũng bỏ câu báo nội bộ cho người viết mã còn ký hiệu lập trình
    ({loai, ref_id}, {e.Message}…) — người dùng không thấy."""
    return bool(re.match(r"[)}:.;,—]", k.strip())) or "{(" in k or bool(re.search(r"\{[^{}0-9][^{}]*\}", k))


def dong_ui(r, man, note):
    vi, en, lo = de_doc(r["vi"], r["en"], r["lo"], CHEN_UI)
    return dict(vi=vi, en=en, lo=lo, man=man, note=note, id=", ".join(r["keys"]), goc=r["lo"])


def dong_cau(k, v, man, note, id_=""):
    vi, en, lo = de_doc(k, v.get("en", ""), v.get("lo", ""), CHEN_SO)
    return dict(vi=vi, en=en, lo=lo, man=man, note=note, id=id_ or k, goc=v.get("lo", ""))


TRANG = [
    ("1 Screens", "Texts on the screens (menus, buttons, labels, hints)",
     [dong_ui(r, r["man"] + (" · also: " + ", ".join(r["cung"]) if r["cung"] else ""), luu_y(r["keys"], r["vi"], r["en"], r["lo"]))
      for r in UI if r["dung"]]),
    ("2 Messages", "Error and warning messages from the EPL server",
     [dong_cau(k, v, "Error / warning message", luu_y_cau(CU_LOI, k, v)) for k, v in tin("loi_dich.json").items() if not vun(k)]),
    ("3 Accounting msgs", "Messages passed on from the accounting system",
     [dong_cau(k, v, "Message from the accounting system", luu_y_cau(CU_LOI_KT, k, v)) for k, v in tin("loi_dich_ke_toan.json").items()
      if not vun(k)]),
    ("4 Older texts", "Older texts — probably no longer shown (lowest priority)",
     [dong_ui(r, "Probably not shown any more", luu_y(r["keys"], r["vi"], r["en"], r["lo"])) for r in UI if not r["dung"]]),
    # 10/10: chữ máy tự sinh lưu trong dữ liệu (mô tả chứng từ, ghi chú sự kiện) — services/mo_ta_dich.json, dịch lúc hiện
    ("5 Generated texts", "Notes and descriptions the app writes by itself (trip events, documents)",
     [dong_cau(k, v, "Written by the app", luu_y_cau(tin_cu("mo_ta_dich.json"), k, v)) for k, v in tin("mo_ta_dich.json").items()]),
]

if TS.man:
    _chu = json.load(open(TS.chu, encoding="utf-8")) if TS.chu else []
    if isinstance(_chu, dict):                 # {"nut": chữ từng nút văn bản, "khoi": chữ cả phần tử nhỏ} — chỉ phần nhìn thấy
        _chu = _chu.get("nut", []) + _chu.get("khoi", [])
    hien = {re.sub(r"\s+", " ", t).strip() for t in _chu}
    # chữ ghép từ nhiều khoá («Tên mục — trạng thái», «MÃ · tên chứng từ», «Nhãn: giá trị») → thêm từng mảnh
    hien |= {m.strip() for t in list(hien) for m in re.split(r"\s+[—·/→]\s+|:\s+|\s*✓$", t) if m.strip()}

    def tren_man(lo):
        """Câu Lào (bỏ thẻ) có đoạn nào khớp trọn một chuỗi đang hiện trên màn không (chỗ chèn {x} khớp mọi chữ)."""
        for doan in re.split(r"<[^>]+>", lo or ""):
            doan = re.sub(r"\s+", " ", doan).strip()
            # đoạn phải có chữ thật — đoạn chỉ gồm chỗ chèn ("{ten}", "{n} · {d}") khớp mọi chuỗi
            if len(re.sub(r"\{[A-Za-z0-9_]+\}|[\s·:;,.()/–—-]", "", doan)) < 2:
                continue
            mau = re.compile("^" + re.sub(r"\\\{[A-Za-z0-9_]+\\\}", ".+?", re.escape(doan)) + "$")
            if any(mau.match(t) for t in hien):
                return True
        return False
    rieng = [r for r in UI if TS.man in r["nhom"]]
    # khoá của màn / tệp khác mà câu Lào đang hiện trên màn này (menu, phần chung, tab Giấy tờ dùng chung với màn Chứng từ…)
    chung = [r for r in UI if TS.man not in r["nhom"] and r["dung"] and tren_man(r["lo"])]
    TEN_MAN = next((r["man"] for r in UI if r["nhom"] == [TS.man]), TS.man)
    # câu máy tự sinh hiện trên màn này: ghi chú sự kiện (tài xế báo về, báo cân mỏ, đổi xe) — mo_ta_dich.json
    sinh = [(k, v) for k, v in tin("mo_ta_dich.json").items() if re.search(r"tài xế báo về|đổi xe|can_mo", v.get("o", ""))]
    TRANG = [(TEN_MAN, "texts of this screen (all its tabs and windows) and the menu around it",
              [dong_ui(r, "This screen", luu_y(r["keys"], r["vi"], r["en"], r["lo"])) for r in rieng]
              + [dong_cau(k, v, "Event note written by the app", luu_y_cau(tin_cu("mo_ta_dich.json"), k, v)) for k, v in sinh]
              + [dong_ui(r, "Menu / common parts", luu_y(r["keys"], r["vi"], r["en"], r["lo"])) for r in chung])]

# ---------------------------------------------------------------- kiểu
XANH, VANG = "1F5C4A", "FFF4C2"
F = "Arial"
F_LAO = "Leelawadee UI"                # có chữ Lào sẵn trên Windows 10 / 11; máy khác tự thay phông Lào
vien = Border(*(Side(style="thin", color="D5DAD7"),) * 4)
COT = [("No.", 6), ("Vietnamese (Tiếng Việt)", 46), ("English", 46), ("Lao — current text (correct in RED)", 54),
       ("Comment (Cello)", 30), ("Screen", 22), ("Note", 10), ("ID", 22), ("Lao original", 30)]
AN = (8, 9)                                # cột ẩn: khoá + câu Lào gốc (để nhập lại)


def ghi(o, v):
    o.value = v
    if isinstance(v, str) and v[:1] in ("=", "+", "-", "@"):
        o.data_type = "s"                  # câu bắt đầu bằng "=" … không phải công thức


wb = Workbook()
hd = wb.active
hd.title = "Read me"
dong = [
    ("EPL Transport — Lao language review", Font(name=F, size=16, bold=True, color=XANH)),
    ("Prepared %s for Mr. Cello. Thank you for helping us correct the Lao!" % NGAY.strftime("%d %B %Y"), Font(name=F, size=11, color="555555")),
    ("", None),
    ("How to review", Font(name=F, size=12, bold=True, color=XANH)),
    ("1.  Each row is one text shown in the EPL app: Vietnamese is the original, English is our translation, Lao is what the app shows now.", None),
    ("2.  If the Lao text is wrong or does not sound natural, type the correct Lao in the Lao column and make it RED (Home → Font Color → Red).", None),
    ("3.  If the Lao text is already good, leave it as it is (black). Please do not change the Vietnamese or English columns.", None),
    ("4.  Signs ①, ②, ③ mark a value the app fills in — a number, a name, a date, an amount… Keep them in your Lao text; you may move", None),
    ("     them to wherever they fit best in Lao. Example: «Found ① trucks» is shown as «Found 12 trucks».", None),
    ("5.  When a cell has two lines, the second line is a small subtitle under the first one on the screen — please keep two lines.", None),
    ("6.  Questions or remarks: write them in the Comment column. The Screen column shows where the text appears.", None),
    ("7.  Rows marked «New» or «Changed» in the Note column were added or edited in the last days — please check those carefully.", None),
    ("", None),
    ("What to do first", Font(name=F, size=12, bold=True, color=XANH)),
]
for ten, mo_ta, ds in TRANG:
    dong.append(("•  Sheet «%s» — %s: %d rows%s" % (ten, mo_ta, len(ds), "" if not ds or not any(r["note"] for r in ds)
                                                     else " (%d marked New / Changed)" % sum(1 for r in ds if r["note"])), None))
dong += [(("This file has only the «%s» screen from your screenshot, plus the menu and common parts shown around it. The real Lao "
           "screen is at the bottom of this page." % TRANG[0][0]) if TS.man else "Sheets 1, 2 and 5 matter most. Sheets 3 and 4 only if you have time.",
          Font(name=F, size=10, italic=True, color="555555")),
         ("", None), ("Example (not a real correction)", Font(name=F, size=12, bold=True, color=XANH))]
for i, (v, f) in enumerate(dong, start=1):
    o = hd.cell(row=i, column=1, value=v)
    o.font = f or Font(name=F, size=10.5)
    o.alignment = Alignment(wrap_text=False, vertical="center")
r0 = len(dong) + 1
for j, (t, w) in enumerate([("Vietnamese (Tiếng Việt)", 30), ("English", 30), ("Lao — current text (correct in RED)", 44), ("Comment (Cello)", 34)], start=1):
    o = hd.cell(row=r0, column=j, value=t)
    o.font, o.fill, o.border = Font(name=F, bold=True, color="FFFFFF"), PatternFill("solid", fgColor=XANH), vien
    o.alignment = Alignment(wrap_text=True, vertical="center")
vd = [("Đóng", "Close", "ປິດ", ""), ("Lưu nháp", "Save draft", "ບັນທຶກສະບັບຮ່າງ", "Example only")]
for i, row in enumerate(vd, start=r0 + 1):
    for j, v in enumerate(row, start=1):
        o = hd.cell(row=i, column=j, value=v)
        o.border = vien
        o.alignment = Alignment(wrap_text=True, vertical="top")
        o.font = Font(name=F_LAO if j == 3 else F, size=10.5, color="FF0000" if (i == r0 + 2 and j == 3) else "000000")
hd.cell(row=r0 + 3, column=1, value="Row 1: the Lao is good, nothing to do.  Row 2: the Lao was changed and coloured red, with a short comment.").font = Font(name=F, size=10, italic=True, color="555555")
if TS.anh:
    from openpyxl.drawing.image import Image as XlImage
    r_anh = r0 + 5
    hd.cell(row=r_anh, column=1, value="The real screen in Lao (EPL test server, Chrome translation OFF)").font = Font(name=F, size=12, bold=True, color=XANH)
    hd.cell(row=r_anh + 1, column=1, value="If your browser shows other words (for example «football club»), Chrome is auto-translating the page: click the "
            "translate icon in the address bar → «Show original».").font = Font(name=F, size=10, italic=True, color="555555")
    anh = XlImage(TS.anh)
    anh.width, anh.height = int(anh.width * 0.62), int(anh.height * 0.62)
    hd.add_image(anh, "A%d" % (r_anh + 3))
hd.column_dimensions["A"].width = 30
hd.column_dimensions["B"].width = 30
hd.column_dimensions["C"].width = 44
hd.column_dimensions["D"].width = 34
hd.sheet_view.showGridLines = False

for ten, mo_ta, ds in TRANG:
    ws = wb.create_sheet(ten)
    for j, (t, w) in enumerate(COT, start=1):
        o = ws.cell(row=1, column=j, value=t)
        o.font = Font(name=F, bold=True, color="FFFFFF", size=10.5)
        o.fill = PatternFill("solid", fgColor=XANH)
        o.alignment = Alignment(wrap_text=True, vertical="center")
        o.border = vien
        ws.column_dimensions[get_column_letter(j)].width = w
    ws.row_dimensions[1].height = 32
    man_truoc = None
    for i, r in enumerate(ds, start=2):
        gt = [i - 1, r["vi"], r["en"], r["lo"], "", r["man"], r["note"], r["id"], r["goc"]]
        for j, v in enumerate(gt, start=1):
            o = ws.cell(row=i, column=j)
            ghi(o, v)
            o.border = vien
            o.alignment = Alignment(wrap_text=True, vertical="top")
            nho = j in (1, 6, 7, 8, 9)
            o.font = Font(name=F_LAO if j == 4 else F, size=9 if nho else (11 if j == 4 else 10.5), color="808080" if j in (1, 8) else "000000")
            if j == 7 and r["note"]:
                o.fill = PatternFill("solid", fgColor=VANG)
                o.font = Font(name=F, size=9, bold=True, color="7A5B00")
            elif j == 6 and r["man"] != man_truoc:
                o.font = Font(name=F, size=9, bold=True, color=XANH)
        man_truoc = r["man"]
    for j in AN:
        ws.column_dimensions[get_column_letter(j)].hidden = True
    ws.freeze_panes = "B2"
    ws.auto_filter.ref = "A1:%s%d" % (get_column_letter(len(COT)), max(len(ds) + 1, 2))
    ws.sheet_view.zoomScale = 100

os.makedirs(os.path.dirname(RA), exist_ok=True)
wb.save(RA)
print("đã ghi", RA)
for ten, _, ds in TRANG:
    print("  %-18s %5d dòng · %d mới / vừa sửa" % (ten, len(ds), sum(1 for r in ds if r["note"])))
