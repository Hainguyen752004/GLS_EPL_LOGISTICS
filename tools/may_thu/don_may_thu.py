# -*- coding: utf-8 -*-
"""Dọn SẠCH dữ liệu nghiệp vụ của trang điều xe trên DB BẢN SAO máy thử (8011 → epl_lao_d7) để gieo lại bộ dữ liệu chuẩn.

    python tools/may_thu/don_may_thu.py                  chỉ liệt kê: đếm từng bảng sẽ xoá / đặt lại, KHÔNG ghi
    python tools/may_thu/don_may_thu.py that             sao lưu (pg_dump, hỏng thì xuất JSON) rồi xoá thật trong MỘT giao dịch
    python tools/may_thu/don_may_thu.py that --ca-8031   … cả DB kho tạm 8031 (epl_ketoan_d7) — kho tạm đã bỏ từ 05/10, mặc định
                                                         KHÔNG đụng tới

Bản 06/10 (chủ dự án: "clear toàn bộ data của module logistic … làm lại bộ data chuẩn"). Đổi so với bản 03/10:
  · thêm các bảng nghiệp vụ mới: dieu_chinh_hang (đơn điều chỉnh kho hàng quặng), chi_luong_tune (phiếu chi lương đọc lại theo
    dòng); tờ PNK_HH / PXK_HH / DC_HH nằm ở chung_tu, sổ kho hàng ở goods_moves, liên kết xuất kho QLSX / huỷ nằm trên dòng
    trip_expenses, điểm GPS gửi bù theo lô ở vehicle_positions (bảng chia phân vùng theo tháng — xoá bảng mẹ là xoá hết phân vùng);
  · trạng thái đồng bộ nền (cau_hinh khoá `dong_bo_nen`) xoá đi — lượt nền sau tự ghi lại; các khoá cấu hình khác giữ;
  · phien_ban_thang (số phiên bản bộ đệm báo cáo) KHÔNG xoá mà TĂNG — tiến trình 8011 đang chạy còn giữ báo cáo trong bộ nhớ kèm
    số phiên bản cũ; đưa số về 0 thì có lúc đếm lên đúng số cũ và trả báo cáo cũ. bao_cao_dem (bản lưu trong DB) xoá;
  · bảng nào có trong DB mà không nằm ở NGHIEP_VU_LAO lẫn DANH_MUC_LAO thì DỪNG, không xoá gì — thêm bảng mới phải phân loại ở đây;
  · tự sao lưu trước khi xoá (.may_thu/sao_luu/<db>_truoc_don_<yyyymmdd_hhmm>.dump · .json);
  · kho tạm 8031 chỉ dọn khi truyền --ca-8031.

XOÁ  mọi dữ liệu nghiệp vụ (NGHIEP_VU_LAO): DO và mọi thứ treo theo (dòng chi, mục, nhật ký, đính kèm, sự kiện, hàng, sổ kho hàng
     quặng + đơn điều chỉnh + tờ, phiếu lĩnh, tạm ứng, tất toán, hoá đơn / thu cũ, trả chủ xe, trả NCC, bán hàng / lệnh sửa cũ, sổ
     dầu / phụ tùng / thẻ cao tốc, vị trí GPS, lượt gửi SO / SO nhiên liệu / phiếu chi / bút toán / cấn trừ / phiếu lương sang anh
     Tune, bộ đệm báo cáo). Rác danh mục của bộ kiểm: chủ xe "ທ້າວ ທົດສອບ (Chủ thử)" đã ngưng + xe THU-CX-01, thẻ THU-THE-01…,
     tuyến thử "THU…" đã ngưng mà không bảng giá nào dùng (theo don_du_lieu_loi.py G12). Tên danh mục mang dấu thử khác (test, thử,
     ທົດສອບ, UAT, THU-, dummy, asdf) chỉ LIỆT KÊ — danh mục không tự xoá.
GIỮ  danh mục (DANH_MUC_LAO): người dùng, khách, chủ xe thật, xe, rơ-moóc (+ gắn xe), tài xế, bằng lái, ảnh, NCC, tuyến (+ điểm
     dừng), giá cước, hợp đồng (+ tệp), điểm dầu, phụ tùng, thẻ cao tốc, tỷ giá (+ lịch sử), cấu hình, ánh xạ đối tượng bên anh
     Tune (doi_tuong_tune — đối tượng EPLKH- / EPLCX- / EPLTX- / EPLNCC- bên đó không xoá; nếu script bên đó có xoá PUBOBJECT thì
     phải xoá cả bảng này, không thì phiếu chi trỏ ObjectId không còn).
ĐẶT LẠI  xe đang chạy / đang sửa → rảnh, rơ-moóc đang chạy → rảnh, tài xế đang chạy → rảnh, số dư thẻ = 0, tồn phụ tùng kho tạm
     cũ = 0 (cột parts.qty còn nhưng kho thật ở anh Tune từ 05/10).

SỐ CHỨNG TỪ đánh lại từ đầu: số DO gợi ý (G4- / T4-nnnn-mm/EPL) lấy số lớn nhất đang có trong trips, số tờ (PDT, PNK_HH, PXK_HH,
DC_HH… LOAI/yymm/nnnn) lấy số lớn nhất trong chung_tu, PTU / PLNL theo số DO — xoá xong thì đánh lại từ 0001. Bên anh Tune dọn
bằng GLS-QLSX-APIs/…/Database/Scripts/20261006_don_sach_logistics_epl.sql (chủ dự án chạy) — phải dọn bên đó cùng đợt, không thì
phiếu chi tạm ứng chống trùng theo đối tượng + số PTU sẽ gặp lại phiếu cũ cùng số. SO, bút toán, cấn trừ khoá theo mã DO (uuid)
nên không trùng.

Chỉ chạy trên DB tên có hậu tố bản sao (…_d<số>); gặp epl_lao / epl_ketoan thật thì dừng. Không dừng / khởi động máy 8011: giao
dịch đặt lock_timeout, nếu 8011 đang giữ khoá bảng thì báo lỗi, rollback, chạy lại.
"""
import datetime as dt
import glob
import json
import os
import re
import shutil
import subprocess
import sys

import sqlalchemy as sa

try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass

MT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".may_thu"))
SAO_LUU = os.path.join(MT, "sao_luu")
THAT = any(a in ("that", "--that") for a in sys.argv[1:])
CA_8031 = "--ca-8031" in sys.argv[1:]

# bảng nghiệp vụ — xoá hết (TRUNCATE không CASCADE: bảng nào ngoài danh sách còn trỏ vào thì báo lỗi chứ không lan)
NGHIEP_VU_LAO = (
    "trips", "trip_goods", "goods_moves", "dieu_chinh_hang", "trip_expenses", "trip_sections", "trip_logs", "trip_events",
    "trip_attachments", "trip_payments", "vouchers", "driver_settlements", "chung_tu", "bao_cao_dem", "invoices",
    "invoice_payments", "owner_payments", "supplier_payments", "sales", "sale_lines", "repair_orders", "repair_lines",
    "fuel_moves", "part_moves", "toll_card_moves", "vehicle_positions", "gui_so_tune", "gui_so_nhien_lieu_tune", "chi_tune",
    "chi_muc_tune", "but_toan_cho", "phieu_tien_tune", "chi_chu_xe_tune", "can_tru_tune", "chi_luong_tune")
# danh mục / cấu hình — giữ (phien_ban_thang: tăng số, không xoá — xem docstring)
DANH_MUC_LAO = (
    "users", "customers", "owners", "vehicles", "vehicle_photos", "trailers", "trailer_assignments", "drivers", "driver_licenses",
    "driver_photos", "suppliers", "exchange_rates", "exchange_rate_logs", "routes", "route_stops", "fuel_places", "parts",
    "toll_cards", "contracts", "contract_files", "customer_rates", "cau_hinh", "doi_tuong_tune", "phien_ban_thang")
PHAN_VUNG = {"vehicle_positions": re.compile(r"^vehicle_positions_(\d{4}_\d{2}|khac)$")}   # phân vùng theo tháng của bảng GPS
NGHIEP_VU_KT = (
    "entries", "entry_lines", "vouchers", "fuel_moves", "part_moves", "goods_moves", "repair_orders", "repair_lines", "sales",
    "sale_lines", "trip_invoices", "invoices", "invoice_payments", "trip_payments", "owner_payments", "owner_payment_trips",
    "driver_settlements", "supplier_payments")
CHU_THU = "ທ້າວ ທົດສອບ (Chủ thử)"
DAU_THU = r"(test|thử|ທົດສອບ|\muat\M|THU-|dummy|asdf)"      # cùng dấu với don_du_lieu_loi.py (Postgres ~*)

RAC_LAO = (  # (nhãn, câu đếm, câu xoá) — theo đúng thứ tự xoá, chạy SAU khi đã xoá bảng nghiệp vụ
    ("ánh xạ chủ xe thử", "select count(*) from doi_tuong_tune where loai='chu_xe' and ref_id in (select id from owners where name=:c and not active)",
     "delete from doi_tuong_tune where loai='chu_xe' and ref_id in (select id from owners where name=:c and not active)"),
    ("thẻ cao tốc thử", "select count(*) from toll_cards where card_no like 'THU-THE-01%'", "delete from toll_cards where card_no like 'THU-THE-01%'"),
    ("xe thử THU-CX-01", "select count(*) from vehicles where truck_no='THU-CX-01' and not active",
     "delete from vehicles where truck_no='THU-CX-01' and not active"),
    ("chủ xe thử", "select count(*) from owners o where name=:c and not active and not exists (select 1 from vehicles v where v.owner_id=o.id)"
     " and not exists (select 1 from contracts k where k.owner_id=o.id)",
     "delete from owners o where name=:c and not active and not exists (select 1 from vehicles v where v.owner_id=o.id)"
     " and not exists (select 1 from contracts k where k.owner_id=o.id)"),
    ("tuyến thử «THU…» đã ngưng, không ai dùng (G12)",
     "select count(*) from routes r where r.name ~ '^THU' and not r.active and not exists (select 1 from customer_rates k where k.route_id=r.id)",
     "delete from routes r where r.name ~ '^THU' and not r.active and not exists (select 1 from customer_rates k where k.route_id=r.id)"),
)
DAT_LAI_LAO = (
    ("xe đang chạy / đang sửa → rảnh", "select count(*) from vehicles where status in ('on_trip','maintenance')",
     "update vehicles set status='available' where status in ('on_trip','maintenance')"),
    ("rơ-moóc đang chạy → rảnh", "select count(*) from trailers where status='on_trip'", "update trailers set status='available' where status='on_trip'"),
    ("tài xế đang chạy → rảnh", "select count(*) from drivers where status='on_trip'", "update drivers set status='available' where status='on_trip'"),
    ("số dư thẻ cao tốc → 0", "select count(*) from toll_cards where balance<>0", "update toll_cards set balance=0 where balance<>0"),
    ("tồn phụ tùng kho tạm cũ → 0", "select count(*) from parts where qty<>0", "update parts set qty=0, last_date=null, last_truck=null where qty<>0"),
    ("trạng thái đồng bộ nền (cau_hinh dong_bo_nen)", "select count(*) from cau_hinh where khoa='dong_bo_nen'",
     "delete from cau_hinh where khoa='dong_bo_nen'"),
    ("phiên bản bộ đệm báo cáo: tăng (không xoá)", "select count(*) from phien_ban_thang",
     "update phien_ban_thang set so = so + 1; insert into phien_ban_thang (khoa, so) values ('*', 1) "
     "on conflict (khoa) do update set so = phien_ban_thang.so + 1"),
)
RAC_KT = (
    ("đối tác kho thử «THỬ …»", "select count(*) from partners where name like 'THỬ %'", "delete from partners where name like 'THỬ %'"),
    ("đối tác chủ xe thử", "select count(*) from partners where kind='chu_xe' and name=:c", "delete from partners where kind='chu_xe' and name=:c"),
)
DAT_LAI_KT = (
    ("tồn phụ tùng → 0", "select count(*) from parts where qty<>0", "update parts set qty=0, last_date=null, last_truck=null where qty<>0"),
)
DO_TEN_THU = (("customers", "name", "khách"), ("owners", "name", "chủ xe"), ("drivers", "name", "tài xế"), ("vehicles", "truck_no", "xe"),
              ("suppliers", "name", "NCC"), ("routes", "name", "tuyến"), ("fuel_places", "name", "điểm dầu"), ("parts", "name", "phụ tùng"),
              ("trailers", "plate", "rơ-moóc"), ("toll_cards", "card_no", "thẻ"), ("users", "username", "người dùng"))


def mo(tep):
    url = open(os.path.join(MT, tep), encoding="utf-8").read().strip()
    ten = sa.engine.make_url(url).database or ""
    if not re.search(r"_d\d+$", ten) or ten in ("epl_lao", "epl_ketoan"):
        sys.exit("DỪNG: %s trỏ DB «%s» — chỉ dọn bản sao của máy thử (tên …_d<số>)." % (tep, ten))
    return url, ten, sa.create_engine(url)


def _pg_dump():
    p = shutil.which("pg_dump")
    if p:
        return p
    ds = sorted(glob.glob(r"C:\Program Files\PostgreSQL\*\bin\pg_dump.exe"), key=lambda x: int(re.findall(r"\\(\d+)\\bin", x)[0]))
    return ds[-1] if ds else None


def sao_luu(url, ten, e, bang):
    """pg_dump -Fc cả DB vào .may_thu/sao_luu; không có / hỏng thì xuất JSON mọi bảng `bang`. Trả đường dẫn, hỏng cả hai thì dừng."""
    os.makedirs(SAO_LUU, exist_ok=True)
    goc = os.path.join(SAO_LUU, "%s_truoc_don_%s" % (ten, dt.datetime.now().strftime("%Y%m%d_%H%M")))
    pd = _pg_dump()
    if pd:
        u = sa.engine.make_url(url)
        env = dict(os.environ, PGPASSWORD=u.password or "")
        r = subprocess.run([pd, "-Fc", "-h", u.host, "-p", str(u.port or 5432), "-U", u.username, "-d", u.database, "-f", goc + ".dump"],
                           env=env, capture_output=True, text=True)
        if r.returncode == 0 and os.path.getsize(goc + ".dump") > 0:
            return goc + ".dump"
        print("   pg_dump hỏng (%s) — xuất JSON thay" % (r.stderr or "").strip()[-300:])
    with e.connect() as c:
        du = {b: [dict(x._mapping) for x in c.execute(sa.text('select * from "%s"' % b))] for b in bang}
    with open(goc + ".json", "w", encoding="utf-8") as f:
        json.dump(du, f, ensure_ascii=False, default=str)
    return goc + ".json"


def don(tep, nghiep_vu, rac, dat_lai, danh_muc=None, do_thu=False):
    url, ten, e = mo(tep)
    print("== %s (%s)" % (ten, "XOÁ THẬT" if THAT else "chỉ liệt kê"))
    with e.connect() as c:
        co = [r[0] for r in c.execute(sa.text("select tablename from pg_tables where schemaname='public' order by 1"))]
    bang = [b for b in nghiep_vu if b in co]
    thieu = [b for b in nghiep_vu if b not in co]
    if danh_muc is not None:
        la = [b for b in co if b not in nghiep_vu and b not in danh_muc
              and not any(m in co and p.match(b) for m, p in PHAN_VUNG.items())]
        if la:
            sys.exit("DỪNG: bảng chưa phân loại (thêm vào NGHIEP_VU_LAO hoặc DANH_MUC_LAO rồi chạy lại): " + ", ".join(la))
    if THAT:
        print("   sao lưu → %s" % sao_luu(url, ten, e, co))
    with e.begin() as c:
        c.execute(sa.text("set local lock_timeout = '20s'"))
        tong = 0
        print("   %-28s %8s" % ("bảng nghiệp vụ", "dòng"))
        for b in bang:
            n = c.execute(sa.text('select count(*) from "%s"' % b)).scalar()
            tong += n
            print("   %-28s %8d" % (b, n))
        print("   → %d dòng nghiệp vụ trong %d bảng%s" % (tong, len(bang), (" · chưa có bảng: " + ", ".join(thieu)) if thieu else ""))
        if THAT and bang:
            c.execute(sa.text("truncate %s restart identity" % ", ".join('"%s"' % b for b in bang)))
        for nhan, dem, lenh in rac + dat_lai:
            n = c.execute(sa.text(dem), {"c": CHU_THU}).scalar()
            print("   %-46s %6d" % (nhan, n))
            if THAT and n:
                for cau in lenh.split("; "):
                    c.execute(sa.text(cau), {"c": CHU_THU})
        if do_thu:   # G12: tên danh mục mang dấu thử — chỉ liệt kê
            for b, cot, nhan in DO_TEN_THU:
                if b in co:
                    for r in c.execute(sa.text('select "%s", active from "%s" where "%s" ~* :d' % (cot, b, cot)), {"d": DAU_THU}):
                        print("   [chỉ liệt kê] %s «%s»%s mang dấu thử — danh mục không tự xoá" % (nhan, r[0], "" if r[1] else " (đã ngưng)"))
        if THAT:
            con = {b: c.execute(sa.text('select count(*) from "%s"' % b)).scalar() for b in bang}
            sot = {b: n for b, n in con.items() if n}
            if sot:
                raise SystemExit("Hậu kiểm hỏng, rollback: %s" % sot)
            print("   hậu kiểm: mọi bảng nghiệp vụ về 0 — COMMIT")


don("url_epl_lao_d7.txt", NGHIEP_VU_LAO, RAC_LAO, DAT_LAI_LAO, danh_muc=DANH_MUC_LAO, do_thu=True)
if CA_8031:
    don("url_epl_ketoan_d7.txt", NGHIEP_VU_KT, RAC_KT, DAT_LAI_KT)
if not THAT:
    print("\nChưa ghi gì. Chạy lại với tham số `that` để sao lưu rồi xoá (thêm --ca-8031 nếu muốn dọn cả kho tạm 8031 đã bỏ).")
