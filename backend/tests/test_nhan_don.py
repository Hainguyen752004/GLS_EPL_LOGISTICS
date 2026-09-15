# -*- coding: utf-8 -*-
"""Kiểm luồng Nhận đơn tự động: tệp khách gửi -> AI đọc -> duyệt -> đơn hàng thật.

    python backend\\tests\\test_nhan_don.py

Bài kiểm này GỌI THẬT Gemini, vì thứ đáng lo nhất của module không phải là mã
Python mà là chuyện máy đọc phiếu có ra đúng số lượng hay không. Đọc sai một cột
"2CT" thành 2 cái thay vì 2 thùng là kho lấy thiếu hàng, mà lỗi đó không bao giờ
lộ ra nếu ta chỉ kiểm bằng dữ liệu giả.

Không có khoá Gemini thì bài kiểm bỏ qua phần AI và chỉ kiểm phần chặn.
"""

import io
import os
import sys
import uuid

GOC = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(GOC, "backend", "app"))
os.chdir(GOC)

from fastapi.testclient import TestClient  # noqa: E402

import main  # noqa: E402
from services import doc_don_ai  # noqa: E402

client = TestClient(main.app)

# Số thùng và quy cách của phiếu mẫu — đây là thứ phải đọc ra đúng.
HANG = [
    ("8850002001234", "LA-100231", "LAY POTATO CHIP ORIGINAL 48G", 12, 24, 10000),
    ("8850002005678", "LA-100232", "TASTO BBQ FLAVOUR 62G", 12, 18, 12000),
    ("8851959132111", "LA-100233", "MAMA INSTANT NOODLE PORK 60G", 30, 40, 4500),
    ("8858891302222", "LA-100234", "BEER LAO LAGER CAN 330ML", 24, 60, 8500),
]
PO_TREN_PHIEU = "6003990311"

so_qua = [0]
so_hong = [0]


def kiem(dieu_kien, mo_ta):
    if dieu_kien:
        so_qua[0] += 1
        print("  [OK]   " + mo_ta)
    else:
        so_hong[0] += 1
        print("  [HONG] " + mo_ta)


def phieu_pdf():
    """Phiếu PO dạng PDF — đúng thứ khách gửi kèm email thật."""
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import mm
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    except ImportError:
        return None

    bo_nho = io.BytesIO()
    kieu = getSampleStyleSheet()
    doc = SimpleDocTemplate(bo_nho, pagesize=A4, topMargin=15 * mm, bottomMargin=15 * mm,
                            leftMargin=12 * mm, rightMargin=12 * mm)
    dau = [
        ["PO NUMBER:", PO_TREN_PHIEU, "ORDER DATE:", "2026-09-12"],
        ["VENDOR:", "SENVANG TRADING CO., LTD", "SHIPPING DATE:", "2026-09-18"],
        ["TAX NUMBER:", "0105556098765", "CURRENCY:", "LAK"],
        ["SHIP TO CODE:", "PTTLAO-DONEKOY", "", ""],
        ["SHIP TO:", "PTTLAO DONEKOY", "", ""],
        ["ADDRESS:", "Donekoy Village, Sisattanak, Vientiane", "", ""],
    ]
    b1 = Table(dau, colWidths=[30 * mm, 75 * mm, 30 * mm, 45 * mm])
    b1.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
    ]))

    hang = [["NO", "BARCODE", "ITEM ID", "ITEM DESCRIPTION", "PACK\nSIZE",
             "UNIT QUANTITY\n(UNIT/PACK/CASE)", "UNIT PRICE", "AMOUNT"]]
    tong = 0
    for i, (bc, ma, ten, quy, thung, gia) in enumerate(HANG, start=1):
        tien = quy * thung * gia
        tong += tien
        hang.append([str(i), bc, ma, ten, str(quy), "%dCT" % thung,
                     "{:,.2f}".format(gia), "{:,.2f}".format(tien)])
    hang.append(["", "", "", "TOTAL", "", "", "", "{:,.2f}".format(tong)])
    b2 = Table(hang, colWidths=[9 * mm, 28 * mm, 22 * mm, 58 * mm, 13 * mm,
                                26 * mm, 20 * mm, 24 * mm], repeatRows=1)
    b2.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 7.5),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.black),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ALIGN", (4, 1), (-1, -1), "RIGHT"),
    ]))
    doc.build([Paragraph("<b>PURCHASE ORDER</b>", kieu["Title"]), Spacer(1, 4 * mm),
               b1, Spacer(1, 5 * mm), b2])
    return bo_nho.getvalue()


def phieu_csv():
    """Bản dự phòng khi máy chưa có reportlab — vẫn là một phiếu đọc được."""
    dong = ["PURCHASE ORDER", "PO NUMBER,%s" % PO_TREN_PHIEU, "ORDER DATE,2026-09-12",
            "SHIPPING DATE,2026-09-18", "SHIP TO CODE,PTTLAO-DONEKOY",
            "SHIP TO,PTTLAO DONEKOY", "VENDOR,SENVANG TRADING CO. LTD",
            "TAX NUMBER,0105556098765", "CURRENCY,LAK", "",
            "NO,BARCODE,ITEM ID,ITEM DESCRIPTION,PACK SIZE,UNIT QUANTITY (UNIT/PACK/CASE),UNIT PRICE"]
    for i, (bc, ma, ten, quy, thung, gia) in enumerate(HANG, start=1):
        dong.append("%d,%s,%s,%s,%d,%dCT,%d" % (i, bc, ma, ten, quy, thung, gia))
    return "\n".join(dong).encode("utf-8")


def chay():
    print("\n[N1] Chặn tệp không phải phiếu đặt hàng")
    r = client.post("/api/inbound/upload",
                    files={"file": ("chu_ky.bmp", b"BM" + b"\x00" * 64, "image/bmp")})
    kiem(r.status_code == 400 and (r.json().get("detail") or {}).get("code") == "IB_FILE_TYPE",
         "tệp lạ bị từ chối bằng IB_FILE_TYPE")

    print("\n[N2] Trạng thái kết nối trả lời được")
    r = client.get("/api/inbound/status")
    kiem(r.status_code == 200, "hỏi được trạng thái hộp thư và máy đọc")
    tt = r.json()["data"]
    print("      máy đọc: %s · hộp thư: %s%s" % (
        "đã nối" if tt["ai_ready"] else "chưa nối",
        "đã nối" if tt["gmail_ready"] else "chưa nối",
        "" if tt["gmail_ready"] else " (%s)" % tt.get("gmail_reason")))

    print("\n[N3] Hộp chờ duyệt liệt kê được")
    r = client.get("/api/inbound?status=all")
    kiem(r.status_code == 200 and "counts" in r.json()["data"], "danh sách hộp chờ có bộ đếm")

    if not doc_don_ai.san_sang():
        print("\n  (bỏ qua phần AI: chưa cấu hình GEMINI_API_KEY_GT trong .env)")
        return

    print("\n[N4] AI đọc phiếu PDF ra đúng số lượng")
    du_lieu = phieu_pdf()
    ten, mime = "PO_%s.pdf" % PO_TREN_PHIEU, "application/pdf"
    if du_lieu is None:
        du_lieu, ten, mime = phieu_csv(), "PO_%s.csv" % PO_TREN_PHIEU, "text/csv"
        print("      (không có reportlab — kiểm bằng bản CSV)")
    r = client.post("/api/inbound/upload", files={"file": (ten, du_lieu, mime)})
    kiem(r.status_code == 200, "nhận được phiếu tải lên (HTTP %s)" % r.status_code)
    if r.status_code != 200:
        return
    ib = r.json()["data"]
    kiem(ib["status"] == "parsed", "AI đọc xong ngay lúc tải lên (trạng thái %s)" % ib["status"])
    nhap = ib.get("draft") or {}
    kiem(nhap.get("po_number") == PO_TREN_PHIEU,
         "đọc đúng số PO (%s)" % nhap.get("po_number"))
    kiem(len(nhap.get("lines") or []) == len(HANG),
         "đọc đủ %d dòng hàng (được %d)" % (len(HANG), len(nhap.get("lines") or [])))

    # Đây là bài kiểm quan trọng nhất: "24CT" phải ra 24 THÙNG, không phải 24 cái.
    doc_duoc = {}
    for d in nhap.get("lines") or []:
        doc_duoc[d["description"].strip().upper()[:12]] = d
    for bc, ma, ten_hang, quy, thung, gia in HANG:
        d = doc_duoc.get(ten_hang.upper()[:12])
        kiem(d is not None and d["case_qty"] == thung,
             "%s: đọc %s thùng (phải %d)" % (ten_hang[:24], d and d["case_qty"], thung))

    print("\n[N5] Tệp gốc mở lại được để người duyệt đối chiếu")
    r = client.get("/api/inbound/%s/file" % ib["id"])
    kiem(r.status_code == 200 and len(r.content) == len(du_lieu),
         "tệp gốc trả về nguyên vẹn (%d byte)" % len(r.content))

    print("\n[N6] Sửa bản nháp trước khi duyệt")
    po_rieng = "KIEM-" + uuid.uuid4().hex[:8].upper()
    r = client.put("/api/inbound/%s/draft" % ib["id"], json={"po_number": po_rieng})
    kiem(r.status_code == 200 and (r.json()["data"]["draft"] or {}).get("po_number") == po_rieng,
         "bản nháp lưu lại số PO đã sửa")

    print("\n[N7] Không chọn khách hàng thì không duyệt được")
    r = client.post("/api/inbound/%s/approve" % ib["id"], json={"customer_id": None})
    kiem(r.status_code == 400 and r.json()["detail"]["code"] == "IB_NO_CUSTOMER",
         "duyệt mà chưa chọn khách bị chặn bằng IB_NO_CUSTOMER")

    print("\n[N8] Duyệt thành đơn hàng thật")
    kh = client.get("/api/customers?kind=customer").json()["data"]
    kiem(bool(kh), "danh mục có khách hàng để chọn")
    if not kh:
        return
    chon = nhap.get("ship_to_suggest_id") or kh[0]["id"]
    kiem(nhap.get("ship_to_suggest_id") is not None,
         "AI gợi ý được khách trong danh mục (%s)" % nhap.get("ship_to_suggest_name"))
    r = client.post("/api/inbound/%s/approve" % ib["id"], json={"customer_id": chon})
    kiem(r.status_code == 200, "duyệt xong (HTTP %s)" % r.status_code)
    if r.status_code != 200:
        print("      " + r.text[:300])
        return
    don = r.json()["data"]["order"]
    kiem(don["po_number"] == po_rieng, "đơn lấy đúng số PO của bản nháp đã sửa")
    kiem(len(don["lines"]) == len(HANG), "đơn có đủ %d dòng hàng" % len(HANG))
    tong_thung = sum(x[4] for x in HANG)
    kiem(don["total_case_qty"] == tong_thung,
         "tổng số thùng trên đơn = %d (được %s)" % (tong_thung, don["total_case_qty"]))

    print("\n[N9] Duyệt hai lần bị chặn")
    r = client.post("/api/inbound/%s/approve" % ib["id"], json={"customer_id": chon})
    kiem(r.status_code == 409 and r.json()["detail"]["code"] == "IB_ALREADY_APPROVED",
         "duyệt lại bị chặn bằng IB_ALREADY_APPROVED")
    r = client.post("/api/inbound/%s/parse" % ib["id"])
    kiem(r.status_code == 409, "đọc lại phiếu đã duyệt cũng bị chặn")

    print("\n[N10] Đơn mới đi thẳng vào màn đóng gói")
    d = client.get("/api/sales-orders/%s" % don["id"]).json()["data"]
    r = client.post("/api/sales-orders/%s/packing-lists" % don["id"], json={
        "items": [{"so_line_id": d["lines"][0]["id"], "case_qty": 2,
                   "piece_qty": 2 * d["lines"][0]["pack_size"]}],
        "box_count": 2,
    })
    kiem(r.status_code == 200, "đóng được Packing List từ đơn nhận tự động (HTTP %s)" % r.status_code)
    if r.status_code == 200:
        print("      Packing List: %s" % r.json()["data"]["id"])


if __name__ == "__main__":
    print("=" * 66)
    print("KIEM LUONG NHAN DON TU DONG")
    print("=" * 66)
    chay()
    print("\n" + "=" * 66)
    print("Qua: %d   Hong: %d" % (so_qua[0], so_hong[0]))
    print("=" * 66)
    sys.exit(1 if so_hong[0] else 0)
