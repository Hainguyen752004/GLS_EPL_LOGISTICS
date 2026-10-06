# -*- coding: utf-8 -*-
"""Phụ trợ bài kiểm trên bản sao d7 — BỘ DỮ LIỆU CŨ 06/10 (trước lần dọn 06/10 12:32), dựng TRONG giao dịch đang mở.

Nhiều bài 05/10–06/10 (thu_ban_giao_dau, thu_ban_giao_trang_thai_chi, thu_dong_bo_nen, thu_kho_hang, thu_kho_qlsx…) viết theo đúng
các DO của d7 lúc đó (G4-0001 … G4-0008, T4-0001: trạng thái, tiền, phiếu chi, SO, bút toán). Ngày 06/10 hai bên được dọn rồi gieo
bộ mới (tools/may_thu/gieo_bo_sach.py) — cùng số DO mà nội dung khác, nên các bài đó hỏng vì DỮ LIỆU chứ không vì mã.

    dat_bo_cu(conn)   trong giao dịch ngoài của bài (ROLLBACK cuối bài trả lại tất cả):
                      1. xoá mọi dòng NGHIỆP VỤ đang có trên d7 (DO, dòng chi, phiếu, chứng từ, bút toán chờ, bản ghi đồng bộ, GPS,
                         tệp đính kèm… — danh sách như tools/may_thu/don_may_thu.py), theo thứ tự khoá ngoại;
                      2. đặt lại cột trạng thái danh mục theo bản cũ (xe / tài xế / rơ-moóc đang chạy hay rảnh, số dư thẻ, tồn
                         phụ tùng kho tạm cũ);
                      3. chèn lại dữ liệu nghiệp vụ cũ từ kiem/bo_cu_d7_0610.json (tách từ
                         .may_thu/sao_luu/epl_lao_d7_truoc_don_20261006_1232.dump — chỉ bảng nghiệp vụ, không chép người dùng / hồ sơ).
                      Bài thấy đúng thế giới d7 lúc viết bài, không phụ thuộc d7 đang có gì. Danh mục (người dùng, xe, tài xế, khách,
                      điểm đổ, phụ tùng, tuyến…) dùng bản đang có trên d7 — các lần dọn giữ danh mục, id không đổi.

Khoá: chỉ khoá DÒNG (DELETE / UPDATE / INSERT), không TRUNCATE — máy 8011 chạy song song vẫn đọc được; lần ghi của nó vào đúng dòng bài
đang giữ thì chờ tới khi bài ROLLBACK. Bài nên đặt SET LOCAL lock_timeout như các bài khác.
"""
import json
import os

GOC = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
TEP = os.path.join(GOC, "kiem", "bo_cu_d7_0610.json")
# bảng nghiệp vụ trang điều xe — cùng danh sách tools/may_thu/don_may_thu.py (NGHIEP_VU_LAO)
NGHIEP_VU = (
    "trips", "trip_goods", "goods_moves", "dieu_chinh_hang", "trip_expenses", "trip_sections", "trip_logs", "trip_events",
    "trip_attachments", "trip_payments", "vouchers", "driver_settlements", "chung_tu", "bao_cao_dem", "invoices",
    "invoice_payments", "owner_payments", "supplier_payments", "sales", "sale_lines", "repair_orders", "repair_lines",
    "fuel_moves", "part_moves", "toll_card_moves", "vehicle_positions", "gui_so_tune", "gui_so_nhien_lieu_tune", "chi_tune",
    "chi_muc_tune", "but_toan_cho", "phieu_tien_tune", "chi_chu_xe_tune", "can_tru_tune", "chi_luong_tune")
TRANG_THAI = {"vehicles": "status", "drivers": "status", "trailers": "status", "toll_cards": "balance", "parts": "qty"}


def _thu_tu_xoa(conn, bang):
    """Bảng con trước bảng cha (khoá ngoại trong cùng nhóm) — để DELETE không vướng khoá ngoại."""
    from sqlalchemy import text
    cap = conn.execute(text(
        "select c.relname, p.relname from pg_constraint k join pg_class c on c.oid = k.conrelid "
        "join pg_class p on p.oid = k.confrelid where k.contype = 'f'")).all()
    con = {b: {cha for ten, cha in cap if ten == b and cha in bang and cha != b} for b in bang}
    ra, con_lai = [], list(bang)
    while con_lai:
        # bảng không còn bảng nào (trong nhóm) trỏ vào nó → xoá được
        la = [b for b in con_lai if not any(b in con[k] for k in con_lai if k != b)]
        if not la:                                      # vòng khoá ngoại (không có trên d7) — xoá theo thứ tự còn lại
            la = con_lai[:1]
        for b in la:
            ra.append(b)
            con_lai.remove(b)
    return ra


def dat_bo_cu(conn):
    """Thay dữ liệu nghiệp vụ d7 bằng bộ cũ 06/10 TRONG giao dịch đang mở của `conn`. → {bảng: số dòng đã chèn}."""
    from sqlalchemy import text

    import models as M
    from _mau_kbaz import _gia_tri
    du = json.load(open(TEP, encoding="utf-8"))
    co = [b for b in NGHIEP_VU if conn.execute(text("select to_regclass(:b)"), {"b": "public." + b}).scalar()]
    for b in _thu_tu_xoa(conn, co):
        conn.execute(text("delete from %s" % b))
    for b, cot in TRANG_THAI.items():
        for ma, v in (du["trang_thai"].get(b) or {}).items():
            conn.execute(text("update %s set %s = :v where id = :ma and %s is distinct from :v" % (b, cot, cot)),
                         {"v": _gia_tri(M.Base.metadata.tables[b].c[cot], v), "ma": ma})
    da = {}
    for b in du["thu_tu"]:
        bang = M.Base.metadata.tables[b]
        dong = [{c: _gia_tri(bang.c[c], v) for c, v in r.items() if c in bang.c} for r in du["nghiep_vu"][b]]
        if dong:
            conn.execute(bang.insert(), dong)
        da[b] = len(dong)
    return da
