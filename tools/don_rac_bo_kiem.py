# -*- coding: utf-8 -*-
"""Dọn RÁC BỘ KIỂM khỏi DB epl_lao (dùng chung với máy chủ của chủ dự án) — giữ nguyên dữ liệu mẫu.

    python tools/don_rac_bo_kiem.py          chạy thử: in ra sẽ xoá gì, KHÔNG ghi
    python tools/don_rac_bo_kiem.py that     xoá thật — NHỚ sao lưu pg_dump hai DB trước

GIỮ: 9 phiếu gieo ban đầu (lập 22/09) và phiếu bộ mẫu tháng 9 (ghi chú "MAU-…", tools/gieo_demo_2609.py), cùng mọi
thứ gắn với chúng; phiếu bán / lệnh sửa / dòng kho của bộ mẫu. XOÁ: mọi thứ bộ kiểm để lại (phiếu thử, phiếu lĩnh bộ kiểm
cấp lên phiếu mẫu, dòng kho mồ côi, phiếu bán thử, chủ xe · xe · thẻ thử, lịch sử tỷ giá thử, chứng từ mồ côi). Tồn phụ
tùng đảo ngược đúng dòng bị xoá. Xong thì dọn luôn bên sổ EPL_KETOAN: tờ nào bên nguồn không còn thì xoá cùng bút toán.
"""
import json
import os
import sys
from collections import Counter

GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(GOC, "backend", "app"))
from database import SessionLocal  # noqa: E402
import models as M  # noqa: E402

THAT = len(sys.argv) > 1 and sys.argv[1] == "that"
db = SessionLocal()
dem = Counter()

import subprocess  # noqa: E402
SO = os.path.join(os.path.dirname(GOC), "EPL_KETOAN", "backend", "app")
# tiến trình con KHÔNG mang DATABASE_URL của epl_lao (database.py bên này đã nạp vào môi trường) — sổ tự đọc .env
# của nó; mang sang thì sổ từ chối chạy (chốt an toàn "không dùng chung DB") — đúng như vậy.
MOI_TRUONG = {k: v for k, v in os.environ.items() if k != "DATABASE_URL"}


def goi_so(ma, *tham, dau_vao=""):
    return subprocess.run([sys.executable, "-X", "utf8", "-c", ma, SO, *tham], input=dau_vao, capture_output=True, text=True,
                          encoding="utf-8", env=MOI_TRUONG, cwd=os.path.dirname(os.path.dirname(SO)))


# Sổ dầu ở trang kế toán từ 28/09: đọc (không ghi) các dòng xuất theo phiếu lĩnh — bước 1b cần biết dòng chi nào bên này
# đang trỏ vào dòng xuất nào bên đó.
DOC_DAU = """
import json, sys
sys.path.insert(0, sys.argv[1])
from database import SessionLocal
import models as M
db = SessionLocal()
print(json.dumps({"dau": [{"id": m.id, "voucher_id": m.voucher_id} for m in db.query(M.FuelMove).filter(M.FuelMove.voucher_id.isnot(None)).all()],
                  "xe_sua": sorted({o.vehicle_id for o in db.query(M.RepairOrder).filter(M.RepairOrder.status != "paid").all()
                                    if o.vehicle_id and not (o.note or "").startswith("thử")})}))
"""
DAU_KT, XE_SUA_KT = [], set()
if os.path.isdir(SO):
    _r = goi_so(DOC_DAU)
    if _r.returncode:
        sys.exit("Không đọc được sổ dầu bên trang kế toán:\n" + _r.stderr.strip()[-600:])
    _g = json.loads(_r.stdout.strip().splitlines()[-1])
    DAU_KT, XE_SUA_KT = _g["dau"], set(_g["xe_sua"])


def xoa(obj, loai):
    dem[loai] += 1
    if THAT:
        db.delete(obj)


# ---------------------------------------------------------------- 1. phiếu thử (lập 23/09 — mẫu gieo lúc 22/09)
MAU = {p.id for p in db.query(M.Trip).all()
       if (p.created_at and p.created_at.strftime("%Y-%m-%d") == "2026-09-22") or (p.note or "").startswith("MAU-")}
thu = [p for p in db.query(M.Trip).all() if p.id not in MAU]
print("Phiếu mẫu giữ: %d · phiếu thử xoá: %s" % (len(MAU), ", ".join(p.doc_no for p in thu)))
id_thu = {p.id for p in thu}
dong_thu = {e.id for e in db.query(M.TripExpense).filter(M.TripExpense.trip_id.in_(id_thu)).all()} if id_thu else set()

# sổ dầu trỏ khoá ngoại vào phiếu lĩnh → xoá dòng dầu của phiếu thử TRƯỚC
pl_thu = {v.id for v in db.query(M.Voucher).filter(M.Voucher.trip_id.in_(id_thu)).all()} if id_thu else set()
for m in db.query(M.FuelMove).all():
    if (m.voucher_id in pl_thu) or (m.expense_id and m.expense_id in dong_thu):
        xoa(m, "dòng dầu")
if THAT:
    db.flush()

# thẻ cao tốc: dòng trừ thẻ của phiếu thử → trả lại số dư
for m in db.query(M.TollCardMove).filter(M.TollCardMove.trip_id.in_(id_thu)).all() if id_thu else []:
    the = db.get(M.TollCard, m.card_id)
    if THAT and the and m.kind == "chi":
        the.balance = (the.balance or 0) + (m.amount or 0)
    xoa(m, "dòng thẻ của phiếu thử")
for bang, ten in ((M.Voucher, "phiếu lĩnh"), (M.TripPayment, "lần thu"), (M.VehiclePosition, "vị trí"), (M.TripAttachment, "tệp"),
                  (M.GoodsMove, "sổ kho hàng"), (M.TripGoods, "dòng hàng"), (M.TripEvent, "sự kiện"), (M.TripLog, "nhật ký"),
                  (M.TripSection, "mục"), (M.TripExpense, "dòng chi")):
    for x in db.query(bang).filter(bang.trip_id.in_(id_thu)).all() if id_thu else []:
        xoa(x, ten)
for p in thu:
    xoa(p, "phiếu")
if THAT:
    db.flush()

# ---- 1b. bộ kiểm đã đụng vào PHIẾU MẪU: bộ mẫu chỉ gieo phiếu tạm ứng; mọi phiếu LĨNH DẦU trên phiếu mẫu là của bộ
#          kiểm (dầu bị xuất hai lần: dòng xuất tháng 8 của bộ mẫu + dòng cấp theo phiếu lĩnh). Gỡ ra, dòng dầu về
#          "chưa xuất" với giá 30.000 LAK như bộ mẫu. Và 3 dòng "tài xế đổ dọc đường" bộ kiểm thêm vào G4-0101.
pl_xoa = set()
for v in db.query(M.Voucher).filter(M.Voucher.kind == "fuel", M.Voucher.trip_id.in_(MAU)).all():
    pl_xoa.add(v.id)
    for m in db.query(M.FuelMove).filter(M.FuelMove.voucher_id == v.id).all():
        for e in db.query(M.TripExpense).filter(M.TripExpense.stock_move_id == m.id).all():
            dem["dòng dầu phiếu mẫu về chưa xuất"] += 1
            if THAT:
                e.stock_move_id = None
                if e.currency == "LAK": e.unit_price = 30000
        xoa(m, "dòng dầu của phiếu lĩnh thử trên phiếu mẫu")
    # từ 28/09 dòng xuất nằm ở sổ dầu trang kế toán (bước 10 xoá nó); dòng chi bên này trỏ vào nó thì về "chưa xuất"
    for km in (x for x in DAU_KT if x["voucher_id"] == v.id):
        for e in db.query(M.TripExpense).filter(M.TripExpense.stock_move_id == km["id"]).all():
            dem["dòng dầu phiếu mẫu về chưa xuất"] += 1
            if THAT:
                e.stock_move_id = None
                if e.currency == "LAK": e.unit_price = 30000
    xoa(v, "phiếu lĩnh thử trên phiếu mẫu")
for e in db.query(M.TripExpense).filter(M.TripExpense.trip_id.in_(MAU), M.TripExpense.note.like("Tài xế đổ dọc đường%")).all():
    for ev in db.query(M.TripEvent).filter(M.TripEvent.expense_id == e.id).all():
        xoa(ev, "sự kiện khai đổ dầu thử")
    dong_thu.add(e.id)
    xoa(e, "dòng khai đổ dầu thử trên phiếu mẫu")
for ev in db.query(M.TripEvent).filter(M.TripEvent.trip_id.in_(MAU), M.TripEvent.kind == "refuel").all():
    xoa(ev, "sự kiện khai đổ dầu thử")
if THAT:
    db.flush()

# ---------------------------------------------------------------- 2. bán hàng thử (giữ BH-2608-0001 của bộ mẫu)
BAN_MAU = ("Chủ xe đổ thêm dầu ở bãi", "Khách mua ở quầy bãi Thà Bốc")   # phiếu bán của tools/gieo_demo_2609.py
ban_thu = [s for s in db.query(M.Sale).all() if s.doc_no != "BH-2608-0001" and (s.note or "") not in BAN_MAU]
so_ban_con = {s.doc_no for s in db.query(M.Sale).all()} - {s.doc_no for s in ban_thu}
so_ban_thu = {s.doc_no for s in ban_thu}
id_ban_thu = {s.id for s in ban_thu}
con_dong_ban = {d.id for d in db.query(M.SaleLine).all() if d.sale_id not in id_ban_thu}
for s in ban_thu:
    for d in db.query(M.SaleLine).filter(M.SaleLine.sale_id == s.id).all():
        xoa(d, "dòng bán")
    xoa(s, "phiếu bán")

# ---------------------------------------------------------------- 3. lệnh sửa thử (giữ LSC-2609-01)
lenh_thu = [o for o in db.query(M.RepairOrder).all() if (o.note or "").startswith("thử")]
so_lenh_thu = {o.doc_no for o in lenh_thu}
id_lenh_thu = {o.id for o in lenh_thu}
con_dong_sua = {d.id for d in db.query(M.RepairLine).all() if d.order_id not in id_lenh_thu}
for o in lenh_thu:
    for d in db.query(M.RepairLine).filter(M.RepairLine.order_id == o.id).all():
        xoa(d, "dòng lệnh sửa")
    xoa(o, "lệnh sửa")
if THAT:
    db.flush()

# ---------------------------------------------------------------- 4. sổ phụ tùng — ở trang kế toán từ 28/09
# Tồn, giá, sổ nhập xuất phụ tùng nằm ở epl_ketoan. Ở đây chỉ gom dấu hiệu nhận ra lần xuất của bộ kiểm (dòng chi mục V
# đã bị xoá, lệnh sửa thử, phiếu bán thử, ghi chú "trả kho" thử); bước 10 dọn bên đó và ĐẢO TỒN đúng những lần xuất ấy.
con_dong = {e.id for e in db.query(M.TripExpense).all()} - (dong_thu if not THAT else set())
TRA_THU = ("hoàn trả sau", "thử trả kho", "trả lại sau")

# ---------------------------------------------------------------- 5. sổ dầu: dòng của phiếu / phiếu bán không còn
# Bảng fuel_moves bên này ĐỨNG YÊN từ 28/09 (sổ gốc đã dời sang trang kế toán, bước 10 dọn bên đó) — không còn dòng mới,
# nhưng vẫn giữ bước này cho dòng cũ. Các tập "còn" dưới đây gửi luôn sang bước 10.
so_phieu_con = {p.doc_no for p in db.query(M.Trip).all() if p.id not in id_thu}
phieu_linh_con = {v.id for v in db.query(M.Voucher).all() if v.trip_id not in id_thu and v.id not in pl_xoa}
for m in db.query(M.FuelMove).all():
    la_thu = ((m.expense_id and m.expense_id not in con_dong)
              or (m.voucher_id and m.voucher_id not in phieu_linh_con)
              or (m.doc_no in so_ban_thu)
              or (m.kind == "out" and not m.expense_id and not m.voucher_id and not m.transfer_no and m.doc_no
                  and m.doc_no not in so_phieu_con and m.doc_no not in so_ban_con and m.doc_no != "PN-0815"))
    if la_thu:
        xoa(m, "dòng dầu")

# ---------------------------------------------------------------- 6. chủ xe · xe · thẻ · đợt trả thử
cx_thu = [o for o in db.query(M.Owner).all() if "(Chủ thử)" in (o.name or "")]
id_cx = {o.id for o in cx_thu}
for x in db.query(M.OwnerPayment).filter(M.OwnerPayment.owner_id.in_(id_cx)).all() if id_cx else []:
    for p in db.query(M.Trip).filter(M.Trip.owner_payment_id == x.id).all():
        if THAT: p.owner_payment_id = None
    xoa(x, "đợt trả chủ xe")
xe_thu = [v for v in db.query(M.Vehicle).all() if (v.truck_no or "").startswith("THU-")]
for v in xe_thu:
    for a in db.query(M.TrailerAssignment).filter(M.TrailerAssignment.vehicle_id == v.id).all():
        xoa(a, "gắn rơ-moóc")
    xoa(v, "xe thử")
if THAT:
    db.flush()
for o in cx_thu:
    xoa(o, "chủ xe thử")
for t in db.query(M.TollCard).filter(M.TollCard.card_no.like("THU-%")).all():
    for m in db.query(M.TollCardMove).filter(M.TollCardMove.card_id == t.id).all():
        xoa(m, "dòng thẻ thử")
    xoa(t, "thẻ thử")

# ---------------------------------------------------------------- 7. lịch sử tỷ giá của bộ kiểm · dòng giá khách trùng
for l in db.query(M.ExchangeRateLog).all():
    if l.ghi_chu and ("bộ kiểm" in l.ghi_chu or "trả lại 22.000" in l.ghi_chu):
        xoa(l, "lịch sử tỷ giá thử")
thay = set()
for r in db.query(M.CustomerRate).order_by(M.CustomerRate.id).all():
    k = (r.customer_id, r.route_id, r.goods_type, r.price, r.hire_price, r.valid_from, r.price_ccy, r.price_mode, r.note)
    if k in thay:
        xoa(r, "dòng giá khách trùng")
    thay.add(k)
if THAT:
    db.flush()

# ---------------------------------------------------------------- 8. chứng từ mồ côi (nguồn đã không còn)
BANG = {"part_moves": M.PartMove, "vouchers": M.Voucher, "sales": M.Sale, "trips": M.Trip, "fuel_moves": M.FuelMove,
        "owner_payments": M.OwnerPayment, "repair_orders": M.RepairOrder, "trip_payments": M.TripPayment,
        "invoice_payments": M.InvoicePayment, "invoices": M.Invoice}
con_trip = {p.id for p in db.query(M.Trip).all()} - (id_thu if not THAT else set())


def con_nguon(c):
    if c.trip_id and c.trip_id not in con_trip:
        return False
    if c.nguon_bang == "trip_sections":
        return c.nguon_id.split(":")[0] in con_trip
    if c.nguon_bang == "fuel_transfers":
        return db.query(M.FuelMove).filter(M.FuelMove.transfer_no == c.nguon_id).count() > 0
    b = BANG.get(c.nguon_bang)
    if b is None:
        return True
    x = db.get(b, c.nguon_id)
    if x is None:
        return False
    if not THAT:          # chạy thử: nguồn còn trong DB nhưng sắp bị xoá ở trên
        if b is M.Sale and x.doc_no in so_ban_thu: return False
        if b is M.RepairOrder and x.doc_no in so_lenh_thu: return False
        if b is M.OwnerPayment and x.owner_id in id_cx: return False
        if b is M.Trip and x.id in id_thu: return False
    return True


da_xoa_ref = []
for c in db.query(M.ChungTu).all():
    if not con_nguon(c):
        da_xoa_ref.append(c.so)
        xoa(c, "chứng từ mồ côi" + (" (đã đẩy sổ)" if c.da_day else ""))

# ---------------------------------------------------------------- 9. trạng thái xe / tài xế do phiếu thử để lại
if THAT:
    db.flush()
    con_chay = db.query(M.Trip).filter(M.Trip.transport_status != "arrived").all()
    xe_chay = {p.vehicle_id for p in con_chay}; tx_chay = {p.driver_id for p in con_chay}
    # tính lại từ dữ liệu còn lại — rà 23/09: lệnh sửa thử bị xoá mà xe ຮ່ວມ-07 vẫn kẹt "đang sửa". Lệnh sửa chữa ở trang
    # kế toán từ đợt 6: lấy xe có lệnh mở (không kể lệnh thử) bên đó, cộng lệnh cũ còn mở bên này.
    xe_sua = {o.vehicle_id for o in db.query(M.RepairOrder).filter(M.RepairOrder.status != "paid").all()} | XE_SUA_KT
    for v in db.query(M.Vehicle).filter(M.Vehicle.status.in_(("available", "on_trip", "maintenance", "idle"))).all():
        moi = "on_trip" if v.id in xe_chay else "maintenance" if v.id in xe_sua else "available"
        if moi != v.status: v.status = moi; dem["trạng thái xe tính lại"] += 1
    for d in db.query(M.Driver).filter(M.Driver.status.in_(("available", "on_trip", "idle"))).all():
        moi = "on_trip" if d.id in tx_chay else "available"
        if moi != d.status: d.status = moi; dem["trạng thái tài xế tính lại"] += 1

print("\n%s" % ("ĐÃ XOÁ:" if THAT else "SẼ XOÁ (chạy thử):"))
for k, n in sorted(dem.items(), key=lambda x: -x[1]):
    print("  %4d  %s" % (n, k))
print("  số chứng từ bị xoá: %d" % len(da_xoa_ref))
if THAT:
    db.commit(); print("ĐÃ GHI epl_lao.")

# ---------------------------------------------------------------- 10. sổ EPL_KETOAN
#   a) sổ phụ tùng (ở đó từ 28/09): xoá lần xuất / nhập của bộ kiểm, ĐẢO TỒN đúng dòng đó, rút tờ kho nó sinh ra;
#   a2) sổ dầu (ở đó từ 28/09): dòng xuất theo dòng chi / phiếu lĩnh / dòng bán không còn bên này, dòng nhập · chuyển kho
#      thử của bộ kiểm → xoá (tồn dầu tính cộng dồn từ sổ nên tự về đúng), rút tờ kho nó sinh ra;
#   a3) sổ kho hàng (ở đó từ 28/09, đợt 5): dòng của phiếu / lô (phiếu gom) không còn bên này → xoá, rút PNK_HH / PXK_HH /
#      DC_HH nó sinh ra;
#   b) tờ ĐẨY TỪ EPL_LAO mà nguồn bên này không còn → xoá cùng bút toán. Tờ kho SINH Ở SỔ (source EPL_KETOAN) thì không
#      bao giờ xoá theo cách này — nó không có bản bên này để so.
MA = """
import json, sys
sys.path.insert(0, sys.argv[1])
from database import SessionLocal
import models as M
THAT = sys.argv[2] == "that"
g = json.load(sys.stdin); con = set(g["con"]); con_dong = set(g["con_dong"]); lenh = set(g["lenh"]); ban = g["ban"]; tra = g["tra"]
con_pl = set(g["con_pl"]); con_ban = set(g["con_ban"]); con_sua = set(g["con_sua"]); phieu_con = set(g["phieu_con"]); ban_con = set(g["ban_con"])
con_trip = set(g["con_trip"])
db = SessionLocal(); n = b = 0
# a0) lệnh sửa chữa thử (ở đây từ đợt 6): ghi chú "thử…" — gỡ dòng, lệnh, tờ PC_SC; số lệnh cho bước sổ phụ tùng
lenh_kt = [o for o in db.query(M.RepairOrder).all() if (o.note or "").startswith("thử")]
lenh |= {o.doc_no for o in lenh_kt}
def xoa_to(v):
    global n, b
    if v.entry_id:
        e = db.get(M.Entry, v.entry_id); v.entry_id = None; db.flush()
        if e: db.query(M.EntryLine).filter(M.EntryLine.entry_id == e.id).delete(); db.delete(e); b += 1
    db.delete(v); n += 1
# a) sổ phụ tùng
dao = {}; so_mv = 0
for m in db.query(M.PartMove).all():
    thu = ((m.expense_id and m.expense_id not in con_dong)
           or (m.khoa and m.khoa.startswith("trip_expense:") and m.khoa.split(":", 1)[1] not in con_dong)
           or (m.trip_doc_no in lenh)
           or any(m.note and m.note.startswith("Bán · %s" % x) for x in ban)
           or (m.note and any(t in m.note for t in tra)))
    if not thu: continue
    so_mv += 1; dao[m.part_id] = dao.get(m.part_id, 0) + (m.qty if m.kind == "out" else -m.qty)
    for v in db.query(M.Voucher).filter(M.Voucher.nguon_bang == "part_moves", M.Voucher.nguon_id == m.id).all():
        xoa_to(v)
    db.delete(m)
for pid, k in dao.items():
    pt = db.get(M.Part, pid)
    if pt:
        print("  tồn %-26s %s → %s (sổ kế toán)" % (pt.name[:26], pt.qty, pt.qty + k))
        pt.qty = pt.qty + k
db.flush()
# a2) sổ dầu
def khoa_mat(k, tien_to, con_lai):
    return bool(k and k.startswith(tien_to) and k.split(":", 1)[1] not in con_lai)
xoa_dau = {}; ck_thu = set()
for m in db.query(M.FuelMove).all():
    thu = ((m.expense_id and m.expense_id not in con_dong)
           or (m.voucher_id and m.voucher_id not in con_pl)
           or khoa_mat(m.khoa, "trip_expense:", con_dong) or khoa_mat(m.khoa, "voucher:", con_pl)
           or khoa_mat(m.khoa, "sale_line:", con_ban) or khoa_mat(m.khoa, "repair_line:", con_sua)
           or (m.doc_no in ban)
           or (m.note and any(t in m.note for t in tra))
           or (m.kind == "out" and not m.expense_id and not m.voucher_id and not m.transfer_no and not m.khoa and m.doc_no
               and m.doc_no not in phieu_con and m.doc_no not in ban_con and m.doc_no != "PN-0815"))
    if thu:
        xoa_dau[m.id] = m
        if m.transfer_no: ck_thu.add(m.transfer_no)
for so_ck in ck_thu:                      # chuyển kho là HAI dòng cùng số: bỏ một thì bỏ cả hai
    for m in db.query(M.FuelMove).filter(M.FuelMove.transfer_no == so_ck).all():
        xoa_dau[m.id] = m
    for v in db.query(M.Voucher).filter(M.Voucher.nguon_bang == "fuel_transfers", M.Voucher.nguon_id == so_ck).all():
        xoa_to(v)
lit = {}
for m in xoa_dau.values():
    for v in db.query(M.Voucher).filter(M.Voucher.nguon_bang == "fuel_moves", M.Voucher.nguon_id == m.id).all():
        xoa_to(v)
    lit[m.kind] = lit.get(m.kind, 0) + (m.qty_l or 0)
    db.delete(m)
if xoa_dau:
    print("  sổ dầu (sổ kế toán): %d dòng · xuất %s L · nhập %s L · %d lần chuyển kho" % (len(xoa_dau), round(lit.get("out", 0), 1), round(lit.get("in", 0), 1), len(ck_thu)))
db.flush()
# a3) sổ kho hàng
xoa_hh = [m for m in db.query(M.GoodsMove).all()
          if (m.trip_id and m.trip_id not in con_trip) or (m.lo_trip_id and m.lo_trip_id not in con_trip)]
phieu_hh = set()
for m in xoa_hh:
    for v in db.query(M.Voucher).filter(M.Voucher.nguon_bang == "goods_moves", M.Voucher.nguon_id == m.id).all():
        xoa_to(v)
    phieu_hh.add(m.trip_id)
    db.delete(m)
for tid in phieu_hh - con_trip:
    for v in db.query(M.Voucher).filter(M.Voucher.nguon_bang == "trips", M.Voucher.nguon_id == tid).all():
        xoa_to(v)
if xoa_hh:
    print("  sổ kho hàng (sổ kế toán): %d dòng của %d phiếu thử" % (len(xoa_hh), len(phieu_hh)))
db.flush()
for o in lenh_kt:
    for v in db.query(M.Voucher).filter(M.Voucher.nguon_bang == "repair_orders", M.Voucher.nguon_id == o.id).all():
        xoa_to(v)
    db.query(M.RepairLine).filter(M.RepairLine.order_id == o.id).delete(synchronize_session=False)
    db.delete(o)
if lenh_kt:
    print("  lệnh sửa chữa thử (sổ kế toán): %s" % ", ".join(sorted(o.doc_no for o in lenh_kt)))
db.flush()
# b) tờ đẩy từ EPL_LAO mà nguồn không còn
for v in db.query(M.Voucher).filter(M.Voucher.source == "EPL_LAO").all():
    if v.ref not in con: xoa_to(v)
db.flush()
dung = {e.party_id for e in db.query(M.Entry).all() if e.party_id}
for p in db.query(M.Partner).all():
    if p.id not in dung: db.delete(p)
if THAT:
    db.commit(); print("ĐÃ GHI epl_ketoan: xoá %d lệnh sửa thử, %d dòng sổ phụ tùng, %d dòng sổ dầu, %d dòng sổ kho hàng, %d tờ, %d bút toán; còn %d tờ" % (len(lenh_kt), so_mv, len(xoa_dau), len(xoa_hh), n, b, db.query(M.Voucher).count()))
else:
    db.rollback(); print("SẼ XOÁ bên epl_ketoan: %d lệnh sửa thử, %d dòng sổ phụ tùng, %d dòng sổ dầu, %d dòng sổ kho hàng, %d tờ, %d bút toán (chạy thử — chưa ghi)" % (len(lenh_kt), so_mv, len(xoa_dau), len(xoa_hh), n, b))
"""


def chay_so(that):
    if not os.path.isdir(SO):
        return
    con = sorted(c.so for c in db.query(M.ChungTu).all() if c.so not in da_xoa_ref)
    goi = {"con": con, "con_dong": sorted(con_dong), "lenh": sorted(so_lenh_thu), "ban": sorted(so_ban_thu), "tra": list(TRA_THU),
           "con_pl": sorted(phieu_linh_con), "con_ban": sorted(con_dong_ban), "con_sua": sorted(con_dong_sua),
           "phieu_con": sorted(so_phieu_con), "ban_con": sorted(so_ban_con), "con_trip": sorted(con_trip)}
    r = goi_so(MA, "that" if that else "thu", dau_vao=json.dumps(goi))
    print(r.stdout.strip() or r.stderr.strip()[-600:])
    if r.returncode and r.stdout.strip():
        print(r.stderr.strip()[-600:])


chay_so(THAT)
if not THAT:
    db.rollback(); print("(chạy thử — chưa ghi gì; thêm tham số 'that' để xoá thật)")
