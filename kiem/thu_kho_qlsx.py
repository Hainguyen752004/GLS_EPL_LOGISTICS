# -*- coding: utf-8 -*-
"""KHO EPL Ở HỆ ANH TUNE (QLSX) — bỏ kho tạm 8031 (chủ dự án duyệt 05/10). Bản sao _d7, mỗi ca một giao dịch ngoài (SET LOCAL
lock_timeout 10s) + phiên savepoint, cuối ROLLBACK. API kho anh Tune GIẢ LẬP (services/kho_qlsx._goi) — không gọi mạng; kho tạm
(goi_ke_toan.goi) bị cấm gọi khi KHO_NGUON=qlsx.

    python kiem/thu_kho_qlsx.py

  1 Đọc: tồn / giá vốn phụ tùng (KHO-PT, EPLPT-<id>) và dầu (EPLNL-diesel theo fuel_places.code) từ stock-balance; màn Xem kho.
  2 Xuất phụ tùng mục V: xe nhà INTERNAL / xe thuê PARTNER_SALE + EPLCX-<chủ xe>; SourceRef EPLLAO:trip_expense:<dòng>; đơn giá dòng =
    giá vốn bình quân bên đó; stock_move_id qlsx:<số phiếu>. Vượt tồn → 409, không ghi dòng. Mất phản hồi / bên này lưu hỏng sau khi
    xuất → gửi huỷ đúng SourceRef, tồn trả lại. Xoá dòng: huỷ theo khoá; dòng kho tạm cũ → 409 rõ.
  3 Hàng khách gửi: sổ goods_moves bên này (nhập lô khi xe gom về, phiếu giao lấy lô kiểm tồn, lô đã có người lấy không xoá được).
  4 Cái bị tắt: cấp dầu cũ qua kho tạm (409 → màn Quản lý kho Web anh Tune), QR không trỏ kho tạm, bán hàng quầy, lệnh sửa ngoài chuyến.
  5 KHO_NGUON=kho_tam: đường cũ (quay lui).
"""
import datetime as dt
import os
import sys
import types

GOC = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
URL = open(os.path.join(GOC, ".may_thu", "url_epl_lao_d7.txt"), encoding="utf-8").read().strip()
if "_d7" not in URL.rsplit("/", 1)[-1]:
    sys.exit("Chuỗi nối không trỏ bản sao _d7 — bài chỉ chạy trên bản sao.")
os.environ["DATABASE_URL"] = URL
os.environ["KHO_NGUON"] = "qlsx"
os.environ.pop("QLSX_WEB_URL", None)
sys.path.insert(0, os.path.join(GOC, "backend", "app"))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass

from fastapi import HTTPException                       # noqa: E402
from sqlalchemy import create_engine, text              # noqa: E402
from sqlalchemy.orm import Session                      # noqa: E402

import models as M                                      # noqa: E402
from routes import danh_muc as RDM                      # noqa: E402
from routes import kho_xem as RKX                       # noqa: E402
from routes import phieu as RP                          # noqa: E402
from routes import phieu_linh as RPL                    # noqa: E402
from services import but_toan_cho as BTC                # noqa: E402
from services import goi_ke_toan as KT                  # noqa: E402
from services import kho_hang as KH                     # noqa: E402
from services import kho_hang_dia as KHD                # noqa: E402
from services import kho_ke_toan as KK                  # noqa: E402
from services import kho_qlsx as KQ                     # noqa: E402
from services import tra_chu_xe as TC                   # noqa: E402

KQUA = []


def dung(dk, ten, ct=""):
    KQUA.append(bool(dk))
    print(("  ✓ " if dk else "  SAI ") + ten + ((" — " + str(ct)[:300]) if ct != "" else ""))


# ================================================================ API kho anh Tune giả
class GIA:
    ton = {}          # (kho, mã) → [số lượng, giá bình quân]
    phieu = {}        # SourceRef → kết quả
    huy = []          # SourceRef đã huỷ
    nhan = []         # (method, đường, thân, khoá)
    mat_phan_hoi = False
    n = 0


def _env(ma, kq=None, loi=None, cau=None):
    if loi:
        return ma, {"Success": False, "Code": ma, "Message": cau, "ErrorDetail": {"ErrorCode": loi}}
    return ma, {"Success": True, "Code": ma, "Message": "OK", "Result": kq}


def gia_goi(method, duong, body=None, key=None):
    GIA.nhan.append((method, duong, body, key))
    if duong.startswith(KQ.DUONG + "/stock-balance"):
        from urllib.parse import parse_qs, unquote, urlsplit
        q = parse_qs(urlsplit(duong).query)
        kho = set(unquote(q["warehouseCodes"][0]).split(",")) if "warehouseCodes" in q else None
        hang = set(unquote(q["itemCodes"][0]).split(",")) if "itemCodes" in q else None
        rows = [{"warehouseCode": k, "itemCode": h, "qty": v[0], "avgUnitCost": v[1], "amount": round(v[0] * v[1])}
                for (k, h), v in GIA.ton.items() if (kho is None or k in kho) and (hang is None or h in hang)]
        return _env(200, {"rows": rows})
    if duong == KQ.DUONG + "/stock-issues" and method == "POST":
        if key in GIA.phieu and key not in GIA.huy:
            return _env(200, dict(GIA.phieu[key], replayed=True))
        for d in body["Lines"]:
            v = GIA.ton.get((d["WarehouseCode"], d["ItemCode"]), [0, 0])
            if v[0] + 1e-9 < d["Qty"]:
                return _env(409, loi="LOGISTICS_STOCK_INSUFFICIENT", cau="%s tại %s còn %s, cần %s." % (d["ItemCode"], d["WarehouseCode"], v[0], d["Qty"]))
        GIA.n += 1
        lines = []
        for d in body["Lines"]:
            v = GIA.ton[(d["WarehouseCode"], d["ItemCode"])]
            v[0] -= d["Qty"]
            lines.append({"itemCode": d["ItemCode"], "warehouseCode": d["WarehouseCode"], "qty": d["Qty"], "unitCost": v[1],
                          "amount": round(d["Qty"] * v[1], 2)})
        kq = {"documentId": 9000 + GIA.n, "documentNo": "PXK-GIA-%d" % GIA.n, "sourceRef": key, "purpose": body["Purpose"],
              "objectCode": body.get("ObjectCode"), "lines": lines, "replayed": False}
        GIA.phieu[key] = kq
        if key in GIA.huy:
            GIA.huy.remove(key)
        if GIA.mat_phan_hoi:                                     # bên kia đã ghi nhưng phản hồi mất
            GIA.mat_phan_hoi = False
            raise HTTPException(503, {"ma": "KHO_QLSX_KHONG_GOI_DUOC", "loi": "giả: mất phản hồi", "chua_ro": True})
        return _env(201, kq)
    if duong == KQ.DUONG + "/stock-issues/cancel":
        sr = body["SourceRef"]
        if sr not in GIA.phieu:
            return 404, {"Success": False, "Code": 404, "Message": "không thấy", "ErrorDetail": {"ErrorCode": "LOGISTICS_STOCK_NOT_FOUND"}}
        if sr not in GIA.huy:
            for x in GIA.phieu[sr]["lines"]:
                GIA.ton[(x["warehouseCode"], x["itemCode"])][0] += x["qty"]
            GIA.huy.append(sr)
        return _env(200, dict(GIA.phieu[sr], state="CANCELLED"))
    return 404, {"Success": False, "Code": 404, "Message": "giả: không có đường %s" % duong}


def cam_kho_tam(*a, **k):
    raise AssertionError("KHO_NGUON=qlsx mà vẫn gọi kho tạm: %s" % (a[1:3],))


KQ._goi = gia_goi
KT.goi = cam_kho_tam


def nguoi(vai):
    return types.SimpleNamespace(role=vai, full_name="Thử " + vai, username="thu_" + vai, id="thu", driver_id=None, place_id=None)


ADMIN, TOTSUA, YARD, FUEL, ACCT = nguoi("admin"), nguoi("repair"), nguoi("yard"), nguoi("fuel"), nguoi("acct")


class Phien:
    eng = None

    def __enter__(self):
        if Phien.eng is None:
            Phien.eng = create_engine(URL, connect_args={"options": "-c timezone=UTC"})
        self.conn = Phien.eng.connect()
        self.ngoai = self.conn.begin()
        self.conn.execute(text("SET LOCAL lock_timeout = '10s'"))
        import _bo_cu_0610 as BO_CU                     # 06/10: d7 dọn + gieo lại → dựng bộ dữ liệu bài viết theo TRONG giao dịch
        BO_CU.dat_bo_cu(self.conn)
        self.db = Session(bind=self.conn, join_transaction_mode="create_savepoint", autoflush=False)
        return self.db

    def __exit__(self, *a):
        self.db.close()
        self.ngoai.rollback()
        self.conn.close()
        return False


def lam_lai(db):
    GIA.ton.clear(); GIA.phieu.clear(); GIA.huy.clear(); GIA.nhan.clear(); GIA.mat_phan_hoi = False
    for k in db.query(M.FuelPlace).filter(M.FuelPlace.owner_type == "epl"):
        GIA.ton[(k.code, KQ.MA_DAU)] = [1430.0 if k.code == "KHO-TB" else 700.0 if k.code == "KHO-XE-VN" else 0.0,
                                        26500.0 if k.code == "KHO-TB" else 27000.0]
    for p in db.query(M.Part):
        GIA.ton[("KHO-PT", KQ.ma_pt(p.id))] = [5.0, 3200000.0 if "12R22.5" in p.name else 500000.0]


def phieu(db, so):
    return db.query(M.Trip).filter(M.Trip.doc_no == so).one()


def lop(db):
    return next(p for p in db.query(M.Part) if "12R22.5" in p.name)


def ca_1():
    print("1. Đọc tồn / giá vốn từ kho QLSX")
    with Phien() as db:
        lam_lai(db)
        ds = KK.ds_phu_tung(db)
        l = next(x for x in ds if "12R22.5" in x["name"])
        dung(l["qty"] == 5 and l["unit_price"] == 3200000 and l["item_code"] == KQ.ma_pt(l["id"]) and l["warehouse_code"] == "KHO-PT",
             "phụ tùng: danh mục bên này + tồn / giá bình quân EPLPT-<id> ở KHO-PT", {k: l[k] for k in ("qty", "unit_price", "item_code")})
        dung(KK.gia_phu_tung(db, l["id"]) == 3200000, "giá phụ tùng lấy kho = giá vốn bình quân bên QLSX")
        tb = db.query(M.FuelPlace).filter(M.FuelPlace.code == "KHO-TB").one()
        dung(KK.gia_dau(db, tb.id) == 26500 and KK.kho_dau(db)[tb.id]["ton_lit"] == 1430, "dầu: tồn + giá bình quân theo mã kho fuel_places.code",
             KK.kho_dau(db)[tb.id])
        x = RKX.kho_xem("", db=db, user=ACCT)
        k = next(k for k in x["nhien_lieu"] if k.get("code") == "KHO-TB")
        dung(k["ton_lit"] == 1430 and any(p.get("ton") == 5 for p in x["phu_tung"]), "màn Xem kho đọc tồn kho QLSX (dầu + phụ tùng)",
             (k["ton_lit"], k.get("con_dung")))
        y = RKX.kho_xem("", db=db, user=YARD)
        dung(all("gia_bq" not in k for k in y["nhien_lieu"]), "Bãi xem kho: không thấy giá vốn")


def _repair(db, p, qty=1, user=TOTSUA):
    return RP.ghi_su_kien(p.id, {"kind": "repair", "incident_type": "tire", "note": "thử kho QLSX",
                                 "repair": {"source": "kho", "part_id": lop(db).id, "qty": qty}}, db=db, user=user)


def _dong_moi(db, p, truoc):
    return [e for e in db.query(M.TripExpense).filter(M.TripExpense.trip_id == p.id, M.TripExpense.section == "repair") if e.id not in truoc]


def ca_2():
    print("2. Xuất phụ tùng mục V qua kho QLSX")
    with Phien() as db:
        lam_lai(db)
        e = phieu(db, "G4-0004-10/EPL")
        truoc = {x.id for x in db.query(M.TripExpense.id).filter(M.TripExpense.trip_id == e.id)}
        _repair(db, e)
        moi = _dong_moi(db, e, truoc)
        g = [x for x in GIA.nhan if x[1] == KQ.DUONG + "/stock-issues"][-1]
        d = moi[0] if moi else None
        dung(d is not None and g[3] == "EPLLAO:trip_expense:" + d.id and g[2]["Purpose"] == "INTERNAL" and "ObjectCode" not in g[2]
             and g[2]["Lines"][0]["ItemCode"] == KQ.ma_pt(lop(db).id) and g[2]["Lines"][0]["WarehouseCode"] == "KHO-PT",
             "xe nhà: INTERNAL, SourceRef EPLLAO:trip_expense:<dòng>, EPLPT-<id> @ KHO-PT", g[3])
        dung(d.stock_move_id == "qlsx:PXK-GIA-1" and d.unit_price == 3200000 and GIA.ton[("KHO-PT", KQ.ma_pt(lop(db).id))][0] == 4,
             "dòng mang qlsx:<số phiếu>, đơn giá = giá vốn bên đó, tồn trừ 1", (d.stock_move_id, d.unit_price))
        ds = {k: v for k, v in BTC.dong_xuat_kho(db, e).items()}
        dong = [x for (_, ln, _) in ds.values() for x in ln]
        dung(any(x["no"] == "614" and x["co"] == "1371" for x in dong), "bút toán xuất nội bộ phụ tùng vẫn 614/1371",
             [(x["no"], x["co"], x["tien"]) for x in dong])
        # xoá dòng (xoá phiếu / trả kho): huỷ theo khoá dòng
        KK.huy_xuat(db, ADMIN, move_id=d.stock_move_id, khoa="trip_expense:" + d.id)
        dung(GIA.huy == ["EPLLAO:trip_expense:" + d.id] and GIA.ton[("KHO-PT", KQ.ma_pt(lop(db).id))][0] == 5,
             "huỷ dòng → stock-issues/cancel đúng SourceRef, tồn trả lại")
        try:
            KK.huy_xuat(db, ADMIN, move_id="mv-kho-tam-cu", khoa="trip_expense:x")
            dung(False, "dòng kho tạm cũ phải bị chặn")
        except HTTPException as x:
            dung(x.status_code == 409 and x.detail["ma"] == "DONG_KHO_TAM_CU", "dòng xuất ở kho tạm cũ → 409 DONG_KHO_TAM_CU, nói cách xử lý")
    with Phien() as db:                                   # xe thuê: PARTNER_SALE + đối tác
        lam_lai(db)
        c = phieu(db, "G4-0002-10/EPL")
        c.locked = False
        db.commit()
        truoc = {x.id for x in db.query(M.TripExpense.id).filter(M.TripExpense.trip_id == c.id)}
        _repair(db, c)
        g = [x for x in GIA.nhan if x[1] == KQ.DUONG + "/stock-issues"][-1]
        dung(g[2]["Purpose"] == "PARTNER_SALE" and g[2]["ObjectCode"] == "EPLCX-" + c.owner_id and _dong_moi(db, c, truoc),
             "xe thuê: PARTNER_SALE kèm đối tác EPLCX-<chủ xe>", (g[2]["Purpose"], g[2].get("ObjectCode")))
    with Phien() as db:                                   # vượt tồn
        lam_lai(db)
        e = phieu(db, "G4-0004-10/EPL")
        truoc = {x.id for x in db.query(M.TripExpense.id).filter(M.TripExpense.trip_id == e.id)}
        try:
            _repair(db, e, qty=99)
            dung(False, "vượt tồn phải bị chặn")
        except HTTPException as x:
            db.rollback()
            dung(x.status_code == 409 and x.detail["ma"] == "VUOT_TON" and not _dong_moi(db, e, truoc)
                 and GIA.ton[("KHO-PT", KQ.ma_pt(lop(db).id))][0] == 5, "vượt tồn → 409 VUOT_TON, không ghi dòng, tồn nguyên", x.detail["loi"])
    with Phien() as db:                                   # phản hồi mất sau khi bên kia đã ghi
        lam_lai(db)
        e = phieu(db, "G4-0004-10/EPL")
        truoc = {x.id for x in db.query(M.TripExpense.id).filter(M.TripExpense.trip_id == e.id)}
        GIA.mat_phan_hoi = True
        try:
            _repair(db, e)
            dung(False, "mất phản hồi phải báo lỗi")
        except HTTPException as x:
            db.rollback()
            dung(x.status_code == 503 and len(GIA.huy) == 1 and GIA.ton[("KHO-PT", KQ.ma_pt(lop(db).id))][0] == 5 and not _dong_moi(db, e, truoc),
                 "mất phản hồi (chưa rõ) → báo 503 rõ, gửi huỷ đúng SourceRef, tồn trả lại, không ghi nửa vời", x.detail.get("loi"))
    with Phien() as db:                                   # bên này lưu hỏng sau khi kho đã xuất
        lam_lai(db)
        e = phieu(db, "G4-0004-10/EPL")
        cu = BTC.chan_sua_sau_khoa

        def hong(*a, **k):
            raise HTTPException(409, {"ma": "GIA_HONG", "loi": "giả: lưu hỏng sau khi xuất"})
        BTC.chan_sua_sau_khoa = hong
        try:
            _repair(db, e)
            dung(False, "lưu hỏng phải báo lỗi")
        except HTTPException as x:
            db.rollback()
            dung(x.detail["ma"] == "GIA_HONG" and len(GIA.huy) == 1 and GIA.ton[("KHO-PT", KQ.ma_pt(lop(db).id))][0] == 5,
                 "bên này lưu hỏng sau khi kho đã xuất → huỷ phiếu xuất bên QLSX, tồn trả lại")
        finally:
            BTC.chan_sua_sau_khoa = cu


def ca_3():
    print("3. Hàng khách gửi ở bãi — sổ goods_moves bên này")
    with Phien() as db:
        lam_lai(db)
        f, b = phieu(db, "G4-0005-10/EPL"), phieu(db, "T4-0001-10/EPL")
        db.query(M.GoodsMove).delete()
        db.commit()
        dung(not KH.da_nhap_kho(db, f), "chưa chép sổ: phiếu gom F chưa có trong kho bãi bên này")
        with KK.GiaoDichKho(db, ACCT) as gd:
            KH.nhap_kho(db, f, ACCT, gd)
        dung(KH.da_nhap_kho(db, f) and KH.ton_lo(db, f.id) == 39.7, "xe gom về: nhập lô theo cân bãi 39,7 t", KH.ton_lo(db, f.id))
        lo = KK.lo_hang(db)
        dung(any(x["lo_trip_id"] == f.id and x["con_t"] == 39.7 and x["customer_name"] for x in lo), "ô chọn lô của phiếu giao", lo[:1])
        with KK.GiaoDichKho(db, ACCT) as gd:
            gd.xuat_hang(b, [{"goods_name": "quặng", "qty_t": 20, "lo_trip_id": f.id}], ngay=dt.date.today())
        dung(KH.ton_lo(db, f.id) == 19.7 and KHD.cua_phieu(db, f.id)["lay_boi"] == [b.doc_no], "phiếu giao lấy 20 t → lô còn 19,7")
        try:
            with KK.GiaoDichKho(db, ACCT) as gd:
                gd.xuat_hang(b, [{"goods_name": "quặng", "qty_t": 45, "lo_trip_id": f.id}], ngay=dt.date.today())
            dung(False, "lấy quá tồn lô phải bị chặn")
        except HTTPException as x:
            dung(x.detail["ma"] == "VUOT_TON" and KH.ton_lo(db, f.id) == 19.7, "lấy quá tồn lô → 409 VUOT_TON, sổ nguyên", x.detail["loi"])
        try:
            KK.huy_hang(db, ADMIN, f.id)
            dung(False, "lô đã có người lấy không xoá được")
        except HTTPException as x:
            dung(x.detail["ma"] == "LO_DA_XUAT", "xoá phiếu gom khi lô đã có phiếu giao lấy → 409 LO_DA_XUAT")


def ca_4():
    print("4. Những đường bị tắt khi bỏ kho tạm")
    with Phien() as db:
        lam_lai(db)
        e = phieu(db, "G4-0004-10/EPL")
        tb = db.query(M.FuelPlace).filter(M.FuelPlace.code == "KHO-TB").one()
        db.add(M.TripExpense(trip_id=e.id, section="fuel", line_no=9, item_key="diesel", qty=10, unit_price=26500, currency="LAK",
                             place_id=tb.id, paid_by_epl=True, source="kho"))
        v = M.Voucher(trip_id=e.id, kind="fuel", doc_no="PLNL-THU-KQ-1", doc_date=dt.date.today(), place_id=tb.id, qty_l=10, status="cho",
                      token="thu-kq-1", issued_by="thử")
        db.add(v)
        db.commit()
        try:
            RPL.cap_phat(v.id, {"qty": 10}, db=db, user=FUEL)
            dung(False, "cấp dầu kiểu cũ phải bị chặn")
        except HTTPException as x:
            db.rollback()
            dung(x.status_code == 409 and x.detail["ma"] == "DA_DOI_SANG_QLSX", "cấp dầu qua kho tạm → 409: cấp ở màn Quản lý kho Web anh Tune",
                 x.detail["loi"])
        dung(RPL.xuat_phieu_linh(db, db.get(M.Voucher, v.id), "http://x", "fuel")["tra_cuu"] is None and KK.web_ke_toan(db) == "",
             "phiếu đề nghị: không còn đường tra cứu / QR trỏ màn Cấp phát kho tạm")
        dung(TC.hang_cho_tru(db, e.owner_id or "x", ADMIN) == [], "bán hàng quầy: không còn phiếu bán chờ trừ (không gọi kho tạm)")
        try:
            TC.giu_hang_quay(db, "TCX-THU", "x", ["s1"], ADMIN)
            dung(False, "giữ phiếu bán phải bị chặn")
        except HTTPException as x:
            dung(x.detail["ma"] == "QUAY_DA_TAT", "giữ / trừ phiếu bán quầy → 409 QUAY_DA_TAT")
        xe = db.get(M.Vehicle, e.vehicle_id)
        r = RDM.xuat_xe(db, xe, chi_tiet=True, vai="admin") if "chi_tiet" in RDM.xuat_xe.__code__.co_varnames else None
        dung(r is None or "Web anh Tune" in (r.get("sua_chua_lenh_loi") or ""), "hồ sơ xe: lệnh sửa chữa ngoài chuyến ghi rõ đã chuyển sang Web anh Tune",
             (r or {}).get("sua_chua_lenh_loi"))


def ca_5():
    print("5. KHO_NGUON=kho_tam — đường cũ (quay lui)")
    os.environ["KHO_NGUON"] = "kho_tam"
    goi = []
    KT.goi = lambda db, m, d, body=None, nguoi=None: goi.append((m, d)) or [{"id": "x", "unit_price": 7, "active": True}]
    try:
        with Phien() as db:
            dung(KK.ds_phu_tung(db)[0]["unit_price"] == 7 and goi == [("GET", "/api/lien-thong/phu-tung")] and not KQ.bat(),
                 "kho_tam: hỏi kho tạm như trước, không gọi kho QLSX", goi)
    finally:
        os.environ["KHO_NGUON"] = "qlsx"
        KT.goi = cam_kho_tam


def main():
    for ca in (ca_1, ca_2, ca_3, ca_4, ca_5):
        try:
            ca()
        except Exception as e:                       # noqa: BLE001
            import traceback
            traceback.print_exc()
            dung(False, "%s vỡ: %s" % (ca.__name__, str(e).replace(URL, "<url>")[:300]))
    print("đã ROLLBACK mọi ca — bản sao d7 không đổi")
    print("TỔNG: %d/%d đạt" % (sum(KQUA), len(KQUA)))
    sys.exit(0 if all(KQUA) else 1)


if __name__ == "__main__":
    main()
