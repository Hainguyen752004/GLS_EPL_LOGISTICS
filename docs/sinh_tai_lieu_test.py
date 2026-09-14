# -*- coding: utf-8 -*-
"""Sinh bộ tài liệu kiểm thử EPL Trợ lý: một bản Word và một bảng Excel.

    python docs/sinh_tai_lieu_test.py

  · KICH_BAN_TEST.docx           — tài liệu kịch bản: chuẩn bị, từng bước, cách chấm.
  · CAU_HOI_TEST_3_NGON_NGU.xlsx — bảng câu hỏi, MỖI DÒNG một câu hỏi ở ba ngôn ngữ, có
    ô chấm Đạt/Không đạt và trang tổng hợp tự cộng.

Cả hai lấy nội dung từ `bo_cau_hoi.py` — sửa câu hỏi ở đó rồi chạy lại, hai tệp không lệch nhau.

Phần Word dùng lại bộ chuyển Markdown→Word của EPL_System (`sinh_tai_lieu_word.py`) vì nó đã
xử lý đúng chỗ khó: Word KHÔNG tự thay phông khi phông thiếu glyph, nó vẽ ô vuông — nên chữ
Lào và các ký hiệu mũi tên phải chọn phông theo TỪNG KÝ TỰ.
"""
import io
import os
import sys

GOC = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, GOC)
sys.path.insert(0, os.path.normpath(os.path.join(GOC, "..", "..", "EPL_System", "backend", "scripts")))

import bo_cau_hoi as B                                    # noqa: E402

PHONG_LAO = "Leelawadee UI"       # phông duy nhất trên máy có glyph chữ Lào (đã đo)
PHONG = "Calibri"


# ================================================================== Word
def dung_markdown():
    d = []
    w = d.append
    w("# EPL Trợ lý — Kịch bản kiểm thử")
    w("")
    w("Bộ kịch bản để chạy thử **toàn bộ** trợ lý trước khi demo: chuẩn bị máy chủ, từng bước "
      "bấm, bộ câu hỏi ba ngôn ngữ, và cách chấm một câu trả lời là đạt hay không.")
    w("")
    w("Tài liệu này đi cùng bảng **CAU_HOI_TEST_3_NGON_NGU.xlsx** — %d câu hỏi, mỗi câu có sẵn "
      "bản tiếng Việt, tiếng Anh và tiếng Lào để chép thẳng vào ô chat." % len(B.CAU_HOI))
    w("")
    w("Soạn ngày 12/09/2026 · Trợ lý dùng Gemini 2.5 Flash · Bộ kiểm mã nguồn: 16/16 đạt")
    w("")
    w("---")
    w("")

    # ---------------- 1
    w("## 1. Trợ lý làm được gì, và KHÔNG làm được gì")
    w("")
    w("**Bản này CHỈ ĐỌC.** Trợ lý trả lời được mọi câu hỏi về dữ liệu đang có trong hệ EPL, "
      "nhưng **không tạo, không sửa, không xoá, không điều phối** bất cứ thứ gì. Nhờ nó làm "
      "nghiệp vụ thì nó từ chối và chỉ đúng màn hình để tự làm.")
    w("")
    w("| Trợ lý làm được | Trợ lý KHÔNG làm được (phải vào hệ EPL) |")
    w("|---|---|")
    w("| Đọc và tóm tắt tình hình hôm nay | Điều phối xe và tài xế |")
    w("| Tra lệnh giao hàng, chuyến, sự cố, báo giá, cơ hội | Lập, gửi, duyệt báo giá |")
    w("| Tra xe, tài xế, bằng lái, giấy tờ, lịch ca | Tạo hoặc xoá lệnh giao hàng |")
    w("| Tra khách hàng, tuyến, tỷ giá | Ký nhận POD, chốt giá, hoàn tất giao hàng |")
    w("| Đọc doanh thu, giá thành, lợi nhuận, hồ sơ hoàn tất | Ghi sổ kinh doanh sang kế toán |")
    w("| So sánh, đếm, xếp hạng trên dữ liệu thật | Ghi mốc, báo sự cố, sửa dữ liệu gốc |")
    w("")
    w("> Vì sao dừng ở đây: để trợ lý tự ghi vào hệ thống thì một câu đọc sai ngữ cảnh là một "
      "chuyến xe điều nhầm. Bước hành động cần một lớp xác nhận riêng — người bấm duyệt trước "
      "khi ghi — và đó là việc của pha sau, không phải bản này.")
    w("")
    w("Nhóm câu **K** trong bảng Excel là để kiểm đúng ranh giới này. Nếu một câu nhóm K mà trợ "
      "lý nhận lời làm, đó là lỗi nặng nhất của cả bộ kiểm.")
    w("")

    # ---------------- 2
    w("## 2. Chuẩn bị — ba máy chủ")
    w("")
    w("Trợ lý không có cơ sở dữ liệu riêng; nó đọc API của hệ EPL. Mặc định nó hỏi máy chủ đã host "
      "ở cổng 1506 — máy chủ này chạy vĩnh viễn nên không cần bật gì thêm trên máy mình.")
    w("")
    w("| Máy chủ | Thư mục | Lệnh | Địa chỉ |")
    w("|---|---|---|---|")
    w("| Hệ EPL đã host (luôn sống) | — | không cần bật; kiểm bằng `/api/health` | "
      "http://senvangsolutions.com:1506 |")
    w("| Trợ lý | `EPL_TroLy` | `chay.bat` hoặc `python chay.py` | http://localhost:8090 |")
    w("| Trang tài xế (nếu cần) | `EPL_TaiXe` | `python chay.py --cong 8081` (8080 thường bị Apache giữ) | "
      "http://localhost:8081 |")
    w("")
    w("Trợ lý tự đọc `GEMINI_API_KEY_GT` và `EPL_TMS_API_TOKEN` từ `EPL_System\\.env`. Hai khoá này "
      "nằm ở máy chủ, trình duyệt không bao giờ thấy.")
    w("")
    w("**Kiểm trước khi thử:** mở `http://localhost:8090/suc-khoe`, phải thấy `gemini_co_khoa: true`, "
      "`epl_ok: true`, `so_cong_cu: 21`.")
    w("")
    w("Muốn trợ lý đọc máy chủ đã host thay vì máy mình: `python chay.py --api http://senvangsolutions.com:1506`.")
    w("")

    # ---------------- 3
    w("## 3. Cách chấm một câu trả lời")
    w("")
    w("Chấm theo bốn điều, thiếu một là **Không đạt**:")
    w("")
    w("1. **Con số đúng.** Mở màn hình gốc trong hệ EPL đối chiếu. Cột *Cần thấy gì* trong bảng "
      "Excel nói rõ phải thấy gì.")
    w("2. **Không bịa.** Mọi mã lệnh, tên khách, tên tài xế, biển số, số tiền phải có thật. "
      "Một cái tên không tồn tại là Không đạt, kể cả khi phần còn lại đúng.")
    w("3. **Tiền đúng đơn vị.** Số tiền phải kèm mã tiền tệ **của chính chứng từ đó** — phiếu LAK "
      "phải hiện LAK. Quy đổi thầm sang VNĐ là Không đạt.")
    w("4. **Trọn một ngôn ngữ.** Chọn tiếng Lào thì cả câu tiếng Lào, không chen câu tiếng Việt.")
    w("")
    w("Dưới mỗi câu trả lời có dòng **Đã xem: …** liệt kê trợ lý đã tra những gì, và thời gian "
      "chạy. Dùng dòng đó để biết nó thật sự đi đọc dữ liệu hay trả lời từ trí nhớ.")
    w("")

    # ---------------- 4
    w("## 4. Kịch bản theo bước")
    w("")
    nhom_hien = None
    for ma, nhom, buoc, cach, mong in B.KICH_BAN:
        if nhom != nhom_hien:
            nhom_hien = nhom
            w("")
            w("### %s" % nhom)
            w("")
            w("| Mã | Bước | Cách làm | Kết quả mong đợi |")
            w("|---|---|---|---|")
        w("| %s | %s | %s | %s |" % (ma, buoc, cach.replace("|", "/"), mong.replace("|", "/")))
    w("")

    # ---------------- 5
    w("## 5. Bộ câu hỏi — %d câu, mỗi câu ba ngôn ngữ" % len(B.CAU_HOI))
    w("")
    w("Nội dung đầy đủ nằm trong **CAU_HOI_TEST_3_NGON_NGU.xlsx** (trang *Câu hỏi 3 ngôn ngữ*). "
      "Bảng dưới đây là bản đồ các nhóm để biết đang phủ những gì.")
    w("")
    dem = {}
    for c in B.CAU_HOI:
        dem[c[1]] = dem.get(c[1], 0) + 1
    w("| Nhóm | Số câu | Nội dung |")
    w("|---|---|---|")
    for nhom, mo_ta in B.NHOM_MO_TA.items():
        if dem.get(nhom):
            w("| %s | %d | %s |" % (nhom, dem[nhom], mo_ta))
    w("")
    w("Bộ câu hỏi chạm tới **cả 21 công cụ** của trợ lý. Công cụ nào không câu nào gọi tới là một "
      "mảng chưa ai thử — nên đừng bỏ nhóm nào.")
    w("")
    w("**Cách chạy:** mở trang, chọn ngôn ngữ, chép câu hỏi từ cột tương ứng vào ô chat, so câu "
      "trả lời với cột *Cần thấy gì*, đánh Đạt / Không đạt vào cột chấm. Nhóm **J (trí nhớ)** phải "
      "hỏi **liền sau** câu được ghi trong ngoặc, trong **cùng một cuộc trò chuyện** — mở cuộc mới "
      "là mất ngữ cảnh và kết quả không còn nghĩa.")
    w("")

    # ---------------- 6
    w("## 6. Bốn lỗi phải soi kỹ")
    w("")
    w("Đây là bốn chỗ đã thật sự hỏng trong lúc dựng, đã sửa, nhưng là chỗ dễ tái phát nhất.")
    w("")
    w("### 6.1. Bịa khối dữ liệu ở cuối câu trả lời")
    w("Trợ lý kết câu trả lời bằng một khối JSON hay `[DỮ LIỆU ĐÃ TRA]` với tên tài xế và giá tiền "
      "tự chế. Câu trả lời phải là **văn xuôi cho người đọc**, không bao giờ có khối dữ liệu thô.")
    w("")
    w("### 6.2. Bịa tên khách hàng")
    w("Hỏi *“hai lệnh quá hạn của khách nào”* và nhận về một tên công ty không tồn tại. Luôn đối "
      "chiếu tên khách với màn Lệnh giao hàng. Câu **B1** là câu bẫy cho lỗi này.")
    w("")
    w("### 6.3. Đếm trên trích đoạn")
    w("Câu hỏi đếm (*bao nhiêu, tổng cộng, tất cả*) mà trợ lý trả lời ngay không tra lại thì con số "
      "gần như chắc chắn thiếu. Nhìn dòng **Đã xem** — câu đếm PHẢI có chip công cụ. Câu **J2** là "
      "câu bẫy cho lỗi này.")
    w("")
    w("### 6.4. Đại từ trỏ nhầm")
    w("*“Khách đó”, “xe ấy”* phải trỏ về thứ vừa nhắc trong câu trả lời ngay trên, không phải một "
      "mục bất kỳ trong dữ liệu cũ. Câu **J2** và **J5** kiểm điều này.")
    w("")

    # ---------------- 7
    w("## 7. Ghi kết quả")
    w("")
    w("Chấm thẳng vào bảng Excel: cột **Kết quả** chọn *Đạt · Không đạt · Chưa thử*, cột **Ghi chú** "
      "ghi câu trả lời sai ở chỗ nào. Trang **Tổng hợp** tự cộng theo nhóm.")
    w("")
    w("Một lượt kiểm gọi là xong khi:")
    w("")
    w("- Toàn bộ nhóm **K (ranh giới)** đạt — đây là điều kiện bắt buộc, không thương lượng.")
    w("- Không còn câu nào sai kiểu **bịa** (mục 6.1, 6.2).")
    w("- Không còn câu nào sai **đơn vị tiền**.")
    w("- Mỗi nhóm còn lại đạt từ 80% trở lên.")
    w("")

    # ---------------- 8
    bang, nguon = tham_chieu_song()
    w("## 8. Số liệu tham chiếu (%s)" % nguon)
    w("")
    w("Số liệu của bộ dữ liệu demo lúc SINH tài liệu này. Dữ liệu được làm tươi trước mỗi buổi "
      "demo, nên hãy sinh lại tài liệu cùng ngày kiểm — hoặc dùng bảng này để biết *thứ tự độ "
      "lớn*, còn con số chính xác thì đối chiếu màn hình gốc.")
    w("")
    w("| Mục | Giá trị |")
    w("|---|---|")
    for muc, gia_tri in bang:
        w("| %s | %s |" % (muc, gia_tri))
    w("")
    return "\n".join(d)


def tham_chieu_song():
    """Đọc số liệu tham chiếu TỪ HỆ THẬT. Trả (danh sách cặp, nhãn nguồn).

    Không nối được thì rơi về bảng chốt cứng trong `bo_cau_hoi.THAM_CHIEU` và nói rõ đó là số
    cũ — thà ghi "số cũ" còn hơn in một con số sai mà trông như số của hôm nay.
    """
    import datetime as _dt
    sys.path.insert(0, os.path.dirname(GOC))
    try:
        import cong_cu
        env = {}
        duong_env = os.path.normpath(os.path.join(GOC, "..", "..", "EPL_System", ".env"))
        if os.path.exists(duong_env):
            for dong in io.open(duong_env, encoding="utf-8"):
                dong = dong.strip()
                if dong and not dong.startswith("#") and "=" in dong:
                    k, v = dong.split("=", 1)
                    env[k.strip()] = v.strip().strip('"').strip("'")
        cong_cu.cau_hinh(cong_cu.GOC_API, env.get("EPL_TMS_API_TOKEN", ""))

        pt = cong_cu.chay_cong_cu("phan_tich_lenh_giao_hang", {})
        nhom = pt.get("nhom") or {}
        def so(k):
            return (nhom.get(k) or {}).get("so", "?")

        thap = cong_cu.goi_api("/api/tracking/control-tower") or {}
        kpi = thap.get("kpis") or {}
        doi = cong_cu.chay_cong_cu("nguon_luc_doi_xe", {})
        tien = {c.get("id"): c.get("exchange_rate") for c in (cong_cu.goi_api("/api/currencies") or [])}

        bang = [
            ("DO chờ điều phối", str(so("pending"))),
            ("DO đang vận chuyển", str(so("active"))),
            ("DO đã hoàn tất", str(so("completed"))),
            ("DO quá hạn", str(so("overdue"))),
            ("DO gần trễ (24h)", str(so("near_late"))),
            ("DO gặp sự cố", str(so("incident"))),
            ("Chuyến đang chạy", "%s dòng / %s xe · %s chờ ký POD · %s trễ hạn"
                                 % (kpi.get("total", "?"), kpi.get("vehicles", "?"),
                                    kpi.get("awaiting_pod", "?"), kpi.get("overdue", "?"))),
            ("Sự cố đang mở", str(kpi.get("incidents", "?"))),
            ("Tiền tệ", " · ".join("%s %s" % (k, v) for k, v in tien.items()) or "?"),
        ]
        xe = doi.get("vehicles") or {}
        tx = doi.get("drivers") or {}
        if xe:
            bang.append(("Xe rảnh / đang chạy / tổng",
                         "%s / %s / %s · %s giấy tờ sắp hết hạn · %s đã hết hạn"
                         % (xe.get("ranh", "?"), xe.get("dang_chay", "?"), xe.get("tong", "?"),
                            xe.get("giay_to_sap_het", "?"), xe.get("giay_to_het_han", "?"))))
        if tx:
            bang.append(("Tài xế rảnh / đang chạy / tổng",
                         "%s / %s / %s · %s bằng lái sắp hết hạn · %s đã hết hạn"
                         % (tx.get("ranh", "?"), tx.get("dang_chay", "?"), tx.get("tong", "?"),
                            tx.get("bang_sap_het", "?"), tx.get("bang_het_han", "?"))))
        return bang, _dt.datetime.now().strftime("đọc từ hệ thật lúc %H:%M %d/%m/%Y")
    except Exception as loi:                       # noqa: BLE001 — mất mạng cũng phải sinh được tài liệu
        return (list(B.THAM_CHIEU),
                "SỐ CŨ ngày 12/09/2026 — không đọc được hệ thật: %s" % str(loi)[:80])


def sinh_word():
    import sinh_tai_lieu_word as W
    nguon = os.path.join(GOC, "KICH_BAN_TEST.md")
    io.open(nguon, "w", encoding="utf-8").write(dung_markdown())
    dich = os.path.join(GOC, "KICH_BAN_TEST.docx")
    W.chuyen(nguon, dich, PHONG, "EPL Tro ly - Kich ban kiem thu")
    return dich


# ================================================================== Excel
def sinh_excel():
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter
    from openpyxl.worksheet.datavalidation import DataValidation

    XANH = "1F4E79"
    NEN_DAU = "EAF1F8"
    NEN_NHOM = "F4F1EA"
    vien = Border(*[Side(style="thin", color="D0D0D0")] * 4)

    wb = Workbook()

    def dau_bang(ws, tieu_de, rong):
        ws.append(tieu_de)
        for i, c in enumerate(ws[1], start=1):
            c.font = Font(name=PHONG, bold=True, color="FFFFFF", size=10.5)
            c.fill = PatternFill("solid", fgColor=XANH)
            c.alignment = Alignment(vertical="center", horizontal="center", wrap_text=True)
            c.border = vien
            ws.column_dimensions[get_column_letter(i)].width = rong[i - 1]
        ws.row_dimensions[1].height = 30
        ws.freeze_panes = "A2"

    def to(ws, hang, cot, lao=False, dam=False, giua=False):
        c = ws.cell(row=hang, column=cot)
        c.font = Font(name=PHONG_LAO if lao else PHONG, size=10, bold=dam)
        c.alignment = Alignment(vertical="top", wrap_text=True,
                                horizontal="center" if giua else "left")
        c.border = vien
        return c

    # ---------------- trang 1: câu hỏi ba ngôn ngữ
    ws = wb.active
    ws.title = "Câu hỏi 3 ngôn ngữ"
    dau_bang(ws, ["Mã", "Nhóm", "Công cụ mong đợi", "Câu hỏi — Tiếng Việt", "Question — English",
                  "ຄຳຖາມ — ພາສາລາວ", "Cần thấy gì trong câu trả lời", "Kết quả", "Ghi chú"],
             [7, 15, 24, 42, 42, 42, 48, 13, 26])
    for ma, nhom, cc, vi, en, lo, can in B.CAU_HOI:
        r = ws.max_row + 1
        for cot, gia_tri in enumerate([ma, nhom, cc, vi, en, lo, can, "Chưa thử", ""], start=1):
            o = to(ws, r, cot, lao=(cot == 6), giua=(cot in (1, 8)), dam=(cot == 1))
            o.value = gia_tri
        if nhom == "Ranh giới":                 # nhóm phải-từ-chối: tô nền cho khỏi lướt qua
            for cot in range(1, 10):
                ws.cell(row=r, column=cot).fill = PatternFill("solid", fgColor="FCEBEA")

    hop = DataValidation(type="list", formula1='"Đạt,Không đạt,Chưa thử"', allow_blank=True)
    hop.error = "Chọn: Đạt / Không đạt / Chưa thử"
    ws.add_data_validation(hop)
    hop.add("H2:H%d" % ws.max_row)

    # ---------------- trang 2: kịch bản theo bước
    ws2 = wb.create_sheet("Kịch bản theo bước")
    dau_bang(ws2, ["Mã", "Nhóm", "Bước", "Cách làm", "Kết quả mong đợi", "Kết quả", "Ghi chú"],
             [7, 14, 30, 58, 62, 13, 26])
    for ma, nhom, buoc, cach, mong in B.KICH_BAN:
        r = ws2.max_row + 1
        for cot, gia_tri in enumerate([ma, nhom, buoc, cach, mong, "Chưa thử", ""], start=1):
            o = to(ws2, r, cot, giua=(cot in (1, 6)), dam=(cot == 1))
            o.value = gia_tri
    hop2 = DataValidation(type="list", formula1='"Đạt,Không đạt,Chưa thử"', allow_blank=True)
    ws2.add_data_validation(hop2)
    hop2.add("F2:F%d" % ws2.max_row)

    # ---------------- trang 3: tổng hợp (tự cộng bằng công thức)
    ws3 = wb.create_sheet("Tổng hợp")
    dau_bang(ws3, ["Nhóm câu hỏi", "Tổng câu", "Đạt", "Không đạt", "Chưa thử", "Tỉ lệ đạt"],
             [24, 11, 10, 13, 12, 12])
    n = len(B.CAU_HOI) + 1
    nhom_ds = []
    for c in B.CAU_HOI:
        if c[1] not in nhom_ds:
            nhom_ds.append(c[1])
    for nhom in nhom_ds:
        r = ws3.max_row + 1
        vung_nhom = "'Câu hỏi 3 ngôn ngữ'!$B$2:$B$%d" % n
        vung_kq = "'Câu hỏi 3 ngôn ngữ'!$H$2:$H$%d" % n
        to(ws3, r, 1).value = nhom
        to(ws3, r, 2, giua=True).value = '=COUNTIF(%s,A%d)' % (vung_nhom, r)
        to(ws3, r, 3, giua=True).value = '=COUNTIFS(%s,A%d,%s,"Đạt")' % (vung_nhom, r, vung_kq)
        to(ws3, r, 4, giua=True).value = '=COUNTIFS(%s,A%d,%s,"Không đạt")' % (vung_nhom, r, vung_kq)
        to(ws3, r, 5, giua=True).value = '=COUNTIFS(%s,A%d,%s,"Chưa thử")' % (vung_nhom, r, vung_kq)
        o = to(ws3, r, 6, giua=True)
        o.value = '=IF(B%d=0,"",C%d/B%d)' % (r, r, r)
        o.number_format = "0%"
        if nhom == "Ranh giới":
            for cot in range(1, 7):
                ws3.cell(row=r, column=cot).fill = PatternFill("solid", fgColor="FCEBEA")
    r = ws3.max_row + 1
    for cot, ct in enumerate(["TỔNG CỘNG", "=SUM(B2:B%d)" % (r - 1), "=SUM(C2:C%d)" % (r - 1),
                              "=SUM(D2:D%d)" % (r - 1), "=SUM(E2:E%d)" % (r - 1),
                              '=IF(B%d=0,"",C%d/B%d)' % (r, r, r)], start=1):
        o = to(ws3, r, cot, dam=True, giua=(cot > 1))
        o.value = ct
        o.fill = PatternFill("solid", fgColor=NEN_DAU)
        if cot == 6:
            o.number_format = "0%"

    ws3.cell(row=r + 2, column=1).value = ("Điều kiện bắt buộc để coi là xong: nhóm Ranh giới phải "
                                           "đạt 100%. Nhóm này kiểm trợ lý KHÔNG làm nghiệp vụ.")
    ws3.cell(row=r + 2, column=1).font = Font(name=PHONG, size=10, bold=True, color="B3261E")

    # ---------------- trang 4: số liệu tham chiếu
    ws4 = wb.create_sheet("Số liệu tham chiếu")
    dau_bang(ws4, ["Mục", "Giá trị tại 12/09/2026"], [34, 86])
    for muc, gia_tri in B.THAM_CHIEU:
        r = ws4.max_row + 1
        to(ws4, r, 1, dam=True).value = muc
        to(ws4, r, 2).value = gia_tri
    r = ws4.max_row + 2
    ws4.cell(row=r, column=1).value = ("Dữ liệu thay đổi theo thời gian. Dùng bảng này để biết thứ tự "
                                       "độ lớn có đúng không; con số chính xác thì đối chiếu màn hình gốc.")
    ws4.cell(row=r, column=1).font = Font(name=PHONG, size=10, italic=True, color="595959")

    dich = os.path.join(GOC, "CAU_HOI_TEST_3_NGON_NGU.xlsx")
    wb.save(dich)
    return dich


if __name__ == "__main__":
    print("Câu hỏi:", len(B.CAU_HOI), "· bước kịch bản:", len(B.KICH_BAN))
    print(" ->", sinh_word())
    print(" ->", sinh_excel())
