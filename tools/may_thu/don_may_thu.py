# -*- coding: utf-8 -*-
"""Dọn sạch HAI DB BẢN SAO của máy thử (8011 → epl_lao_d7 · 8031 → epl_ketoan_d7) để gieo lại bộ chuyến đi trọn luồng.

    python tools/may_thu/don_may_thu.py          chỉ liệt kê: đếm sẽ xoá gì, KHÔNG ghi
    python tools/may_thu/don_may_thu.py that     xoá thật (mỗi DB một giao dịch) — sao lưu pg_dump trước

XOÁ  mọi dữ liệu nghiệp vụ: phiếu xe / DO và mọi thứ treo theo (dòng chi, mục, nhật ký, đính kèm, sự kiện, hàng, phiếu lĩnh,
     tạm ứng, tất toán, hoá đơn, thu, trả chủ xe, trả NCC, bán hàng, lệnh sửa, sổ dầu / phụ tùng / thẻ cao tốc, vị trí GPS,
     hàng chờ gửi sang anh Tune, bộ đệm báo cáo) — bên sổ kho tạm: chứng từ, bút toán, sổ kho, bán hàng, hoá đơn, trả…
     Rác danh mục của bộ kiểm: chủ xe "ທ້າວ ທົດສອບ (Chủ thử)" đã ngưng + xe THU-CX-01 của họ, thẻ THU-THE-01…, đối tác kho
     tạm tên "THỬ …".
GIỮ  danh mục: người dùng, khách, chủ xe thật, xe, rơ-moóc, tài xế, bằng lái, NCC, tuyến, giá cước, hợp đồng, điểm dầu,
     phụ tùng, tài khoản, tỷ giá, cấu hình, ánh xạ đối tượng bên anh Tune (doi_tuong_tune — đối tượng bên đó không xoá).
ĐẶT LẠI  xe / tài xế đang chạy → rảnh, xe đang sửa → rảnh, số dư thẻ = 0, tồn phụ tùng = 0 (tồn chỉ đi theo phiếu nhập).

Chỉ chạy trên DB tên có hậu tố bản sao (…_d<số>); gặp epl_lao / epl_ketoan thật thì dừng. Bên anh Tune dọn bằng script
GLS-QLSX-APIs/Backend.API/Database/Scripts/20261002_don_du_lieu_thu_epl.sql (chủ dự án tự chạy) — phải dọn bên đó TRƯỚC khi gieo
lại, không thì phiếu chi tạm ứng trùng số PTU sẽ bị dùng lại.
"""
import os
import re
import sys

import sqlalchemy as sa

MT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".may_thu"))
THAT = len(sys.argv) > 1 and sys.argv[1] == "that"

# bảng nghiệp vụ — xoá hết (TRUNCATE không CASCADE: bảng nào ngoài danh sách còn trỏ vào thì báo lỗi chứ không lan)
NGHIEP_VU_LAO = (
    "trips", "trip_goods", "goods_moves", "trip_expenses", "trip_sections", "trip_logs", "trip_events", "trip_attachments",
    "trip_payments", "vouchers", "driver_settlements", "chung_tu", "bao_cao_dem", "phien_ban_thang", "invoices",
    "invoice_payments", "owner_payments", "supplier_payments", "sales", "sale_lines", "repair_orders", "repair_lines",
    "fuel_moves", "part_moves", "toll_card_moves", "vehicle_positions", "gui_so_tune", "gui_so_nhien_lieu_tune", "chi_tune",
    "chi_muc_tune", "but_toan_cho", "phieu_tien_tune", "chi_chu_xe_tune", "can_tru_tune")
NGHIEP_VU_KT = (
    "entries", "entry_lines", "vouchers", "fuel_moves", "part_moves", "goods_moves", "repair_orders", "repair_lines", "sales",
    "sale_lines", "trip_invoices", "invoices", "invoice_payments", "trip_payments", "owner_payments", "owner_payment_trips",
    "driver_settlements", "supplier_payments")
CHU_THU = "ທ້າວ ທົດສອບ (Chủ thử)"

RAC_LAO = (  # (nhãn, câu đếm, câu xoá) — theo đúng thứ tự xoá
    ("ánh xạ chủ xe thử", "select count(*) from doi_tuong_tune where loai='chu_xe' and ref_id in (select id from owners where name=:c and not active)",
     "delete from doi_tuong_tune where loai='chu_xe' and ref_id in (select id from owners where name=:c and not active)"),
    ("thẻ cao tốc thử", "select count(*) from toll_cards where card_no like 'THU-THE-01%'", "delete from toll_cards where card_no like 'THU-THE-01%'"),
    ("xe thử THU-CX-01", "select count(*) from vehicles where truck_no='THU-CX-01' and not active",
     "delete from vehicles where truck_no='THU-CX-01' and not active"),
    ("chủ xe thử", "select count(*) from owners o where name=:c and not active and not exists (select 1 from vehicles v where v.owner_id=o.id)"
     " and not exists (select 1 from contracts k where k.owner_id=o.id)",
     "delete from owners o where name=:c and not active and not exists (select 1 from vehicles v where v.owner_id=o.id)"
     " and not exists (select 1 from contracts k where k.owner_id=o.id)"),
)
DAT_LAI_LAO = (
    ("xe đang chạy / đang sửa → rảnh", "select count(*) from vehicles where status in ('on_trip','maintenance')",
     "update vehicles set status='available' where status in ('on_trip','maintenance')"),
    ("tài xế đang chạy → rảnh", "select count(*) from drivers where status='on_trip'", "update drivers set status='available' where status='on_trip'"),
    ("số dư thẻ cao tốc → 0", "select count(*) from toll_cards where balance<>0", "update toll_cards set balance=0 where balance<>0"),
    ("tồn phụ tùng (bản cũ) → 0", "select count(*) from parts where qty<>0", "update parts set qty=0, last_date=null, last_truck=null where qty<>0"),
)
RAC_KT = (
    ("đối tác kho thử «THỬ …»", "select count(*) from partners where name like 'THỬ %'", "delete from partners where name like 'THỬ %'"),
    ("đối tác chủ xe thử", "select count(*) from partners where kind='chu_xe' and name=:c", "delete from partners where kind='chu_xe' and name=:c"),
)
DAT_LAI_KT = (
    ("tồn phụ tùng → 0", "select count(*) from parts where qty<>0", "update parts set qty=0, last_date=null, last_truck=null where qty<>0"),
)


def mo(tep):
    url = open(os.path.join(MT, tep), encoding="utf-8").read().strip()
    ten = sa.engine.make_url(url).database or ""
    if not re.search(r"_d\d+$", ten) or ten in ("epl_lao", "epl_ketoan"):
        sys.exit("DỪNG: %s trỏ DB «%s» — chỉ dọn bản sao của máy thử (tên …_d<số>)." % (tep, ten))
    return ten, sa.create_engine(url)


def don(tep, nghiep_vu, rac, dat_lai):
    ten, e = mo(tep)
    print("== %s (%s)" % (ten, "XOÁ THẬT" if THAT else "chỉ liệt kê"))
    with e.begin() as c:
        co = {r[0] for r in c.execute(sa.text("select tablename from pg_tables where schemaname='public'"))}
        bang = [b for b in nghiep_vu if b in co]
        thieu = [b for b in nghiep_vu if b not in co]
        tong = 0
        for b in bang:
            n = c.execute(sa.text('select count(*) from "%s"' % b)).scalar()
            tong += n
            if n:
                print("   xoá %-24s %6d dòng" % (b, n))
        print("   → %d dòng nghiệp vụ trong %d bảng%s" % (tong, len(bang), (" · chưa có bảng: " + ", ".join(thieu)) if thieu else ""))
        if THAT and bang:
            c.execute(sa.text("truncate %s restart identity" % ", ".join('"%s"' % b for b in bang)))
        for nhan, dem, lenh in rac + dat_lai:
            n = c.execute(sa.text(dem), {"c": CHU_THU}).scalar()
            print("   %-34s %6d" % (nhan, n))
            if THAT and n:
                c.execute(sa.text(lenh), {"c": CHU_THU})
        if THAT:
            con = {b: c.execute(sa.text('select count(*) from "%s"' % b)).scalar() for b in bang}
            sot = {b: n for b, n in con.items() if n}
            if sot:
                raise SystemExit("Hậu kiểm hỏng, rollback: %s" % sot)
            print("   hậu kiểm: mọi bảng nghiệp vụ về 0 — COMMIT")


don("url_epl_lao_d7.txt", NGHIEP_VU_LAO, RAC_LAO, DAT_LAI_LAO)
don("url_epl_ketoan_d7.txt", NGHIEP_VU_KT, RAC_KT, DAT_LAI_KT)
if not THAT:
    print("\nChưa ghi gì. Chạy lại với tham số `that` để xoá (sao lưu trước: .may_thu/sao_luu).")
