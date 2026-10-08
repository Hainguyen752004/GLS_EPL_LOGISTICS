# -*- coding: utf-8 -*-
"""Thử Việc 11a (08/10) — QUYỀN TRÊN PHIẾU cho màn Web (services/quyen_phieu.py, khoá "quyen" của GET /api/trips/{id}),
tờ phiếu trắng (GET /api/trips-moi), tính thử (POST /api/trips/tinh-thu: dòng hàng → cân đầu, giá hợp đồng gợi ý), bảng hàng
(quyen.hang), chủ xe của phiếu xe thuê khi màn gửi kèm số xe (_ap_truong).

    python kiem/thu_quyen_phieu.py

Chạy trong một giao dịch trên bản sao _d7, cuối ROLLBACK — không ghi gì. Không gọi mạng. Hai phiếu mẫu của d7:
  G4-0007-10/EPL  gom · xe nhà · đang chạy · chưa khoá · mục I–IV "đã nhập", V–VI chờ
  G4-0010-10/EPL  gom · xe nhà · đã tới · ĐÃ KHOÁ · I–II đã kiểm, III–IV đã ghi sổ, V đã chi, VI chờ
Kỳ vọng chép theo luật màn cũ (phieu-xuat-xe.js: suaDuoc, suaTienDuoc, suaKeToanDuoc, veVaiVaTrangThai, tabMacDinh).
"""
import os
import sys

GOC = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
URL = open(os.path.join(GOC, ".may_thu", "url_epl_lao_d7.txt"), encoding="utf-8").read().strip()
if "_d7" not in URL.rsplit("/", 1)[-1]:
    sys.exit("Chuỗi nối không trỏ bản sao _d7 — bài chỉ chạy trên bản sao.")
os.environ["DATABASE_URL"] = URL
os.environ["EPL_DANG_NHAP_GLS"] = "0"
sys.path.insert(0, os.path.join(GOC, "backend", "app"))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass

from fastapi.testclient import TestClient               # noqa: E402
from sqlalchemy import create_engine, text              # noqa: E402
from sqlalchemy.orm import Session                      # noqa: E402

import models as M                                      # noqa: E402
from database import get_db                             # noqa: E402
from main import app                                    # noqa: E402

KQ = []
DANG_CHAY, DA_KHOA = "ab65dc282091", "934aef04961a"


def dung(dk, ten, ct=""):
    KQ.append(bool(dk))
    print(("  ✓ " if dk else "  SAI ") + ten + ((" — " + str(ct)[:300]) if ct != "" else ""))


def main():
    eng = create_engine(URL, connect_args={"options": "-c timezone=UTC"})
    conn = eng.connect()
    ngoai = conn.begin()
    conn.execute(text("SET LOCAL lock_timeout = '10s'"))
    db = Session(bind=conn, join_transaction_mode="create_savepoint", autoflush=False)

    def _db():
        try:
            yield db
        finally:
            db.rollback()
    app.dependency_overrides[get_db] = _db
    c = TestClient(app, raise_server_exceptions=False)
    TK = {}

    def goi(u, method, duong, body=None):
        r = c.request(method, duong, json=body, headers={"Authorization": "Bearer " + TK[u]})
        try:
            return r.status_code, r.json()
        except ValueError:
            return r.status_code, None
    try:
        for u in ("thabok", "ketoan", "khonl", "ketoancp", "quyvc", "quytb", "admin"):
            TK[u] = c.post("/api/dang-nhap", json={"username": u, "password": "1234"}).json()["token"]
        p7, p10 = db.get(M.Trip, DANG_CHAY), db.get(M.Trip, DA_KHOA)
        dung(p7 is not None and p10 is not None and p10.locked and p7.transport_status == "dispatched", "d7 có hai phiếu mẫu")

        print("== 1. tờ phiếu trắng")
        s, r = goi("thabok", "GET", "/api/trips-moi?kind=gom")
        q = r["quyen"]
        dung(s == 200 and r["doc_no"].startswith("G4-") and r["mac_dinh"]["kind"] == "gom" and r["mac_dinh"]["rate_usd"] > 0,
             "Bãi: số gợi ý G4-…, mặc định có tỷ giá", r["doc_no"])
        dung(q["moi"] and q["o"]["vehicle_id"]["sua"] and q["o"]["price"]["an"] and not q["o"]["ore_bill_no"]["sua"]
             and q["muc"]["info"]["sua"] and not q["muc"]["repair"]["sua"] and q["tab_mac_dinh"] == "info" and not q["o"]["pod_no"]["sua"],
             "Bãi phiếu mới: sửa mục I, giấu ô giá, không sửa số phiếu quặng / mục V / POD", q["o"]["price"])
        s, r = goi("ketoan", "GET", "/api/trips-moi")
        dung(s == 200 and not r["quyen"]["o"]["price"]["an"] and r["quyen"]["o"]["ore_bill_no"]["sua"] and not r["quyen"]["muc"]["info"]["sua"],
             "KT Thu/Chi phiếu mới: thấy giá, nhập số phiếu quặng, không sửa mục I", r["quyen"]["muc"]["info"])

        print("== 2. phiếu đang chạy (G4-0007) — nút từng mục theo vai")
        q = goi("thabok", "GET", "/api/trips/" + DANG_CHAY)[1]["quyen"]
        dung(q["muc"]["info"]["sua"] and q["muc"]["info"]["viec"] == [] and q["o"]["vehicle_id"]["sua"] and not q["o"]["back_date"]["sua"]
             and q["o"]["weight_origin"]["sua"] and not q["o"]["weight_dest"]["sua"],
             "Bãi: mục I đã nhập còn sửa, chưa có nút; ngày về / cân cuối khoá tới khi xe về", q["muc"]["info"])
        dung(set(q["phieu"]) == {"transit", "doi-xe", "arrived", "xoa"}, "Bãi: việc mức phiếu đang chạy · đổi xe · xe đã tới · xoá", q["phieu"])
        dung(q["muc"]["repair"]["tuy_chon"] and q["muc"]["repair"]["nhan"] == "stt_na", "mục V chưa có dòng → không phát sinh", q["muc"]["repair"])
        q = goi("ketoan", "GET", "/api/trips/" + DANG_CHAY)[1]["quyen"]
        dung(q["muc"]["info"]["viec"] == ["verify", "return"] and q["muc"]["trans"]["viec"] == ["verify", "return"] and q["muc"]["fuel"]["viec"] == []
             and q["o"]["price"]["sua"] and not q["o"]["vehicle_id"]["sua"] and q["o"]["ore_bill_no"]["sua"] and q["phieu"] == [],
             "KT Thu/Chi: kiểm / trả lại I–II, sửa giá + số phiếu quặng, không sửa xe, chưa khoá được (xe chưa tới)", q["muc"]["trans"])
        q = goi("khonl", "GET", "/api/trips/" + DANG_CHAY)[1]["quyen"]
        dung(q["muc"]["fuel"]["viec"] == ["verify", "return"] and q["muc"]["info"]["viec"] == [] and q["tab_mac_dinh"] == "fuel",
             "KT kho xăng dầu: kiểm mục III, mở sẵn tab III", q["muc"]["fuel"])
        q = goi("ketoancp", "GET", "/api/trips/" + DANG_CHAY)[1]["quyen"]
        dung(q["muc"]["travel"]["viec"] == ["verify", "return"] and q["tab_mac_dinh"] == "travel", "KT Chi phí: kiểm mục IV", q["muc"]["travel"])

        print("== 3. phiếu đã khoá (G4-0010)")
        q = goi("thabok", "GET", "/api/trips/" + DA_KHOA)[1]["quyen"]
        dung(q["bi_khoa"] and not any(v["sua"] for v in q["o"].values()) and q["phieu"] == [] and not q["muc"]["info"]["sua"],
             "Bãi: phiếu đã khoá → mọi ô khoá, không việc mức phiếu", q["phieu"])
        r = goi("ketoan", "GET", "/api/trips/" + DA_KHOA)[1]
        q = r["quyen"]
        dung(q["muc"]["info"]["viec"] == [] and ("mo-khoa" in q["phieu"]) == (not r.get("da_tao_so")),
             "KT Thu/Chi: không trả lại mục đã kiểm khi phiếu khoá; mở khoá được khi chưa tạo SO", (q["phieu"], r.get("da_tao_so")))
        q = goi("quyvc", "GET", "/api/trips/" + DA_KHOA)[1]["quyen"]
        dung(q["muc"]["fuel"]["viec"] == ["pay"], "Thủ quỹ VC: chi mục III đã ghi sổ", q["muc"]["fuel"])
        q = goi("quytb", "GET", "/api/trips/" + DA_KHOA)[1]["quyen"]
        dung(q["muc"]["travel"]["viec"] == [], "Quỹ tiền mặt: mục IV chi ở Kế toán → không nút Chi", q["muc"]["travel"])
        q = goi("admin", "GET", "/api/trips/" + DA_KHOA)[1]["quyen"]
        dung("unlock" in q["muc"]["fuel"]["viec"] and "return" in q["muc"]["info"]["viec"] and q["tab_mac_dinh"] == "all",
             "Sếp: mở khoá mục, trả lại được cả khi phiếu khoá, mở Toàn phiếu", (q["muc"]["fuel"]["viec"], q["muc"]["info"]["viec"]))

        print("== 4. tính thử (không ghi)")
        p7 = db.get(M.Trip, DANG_CHAY)
        cu = (p7.weight_origin, p7.price)
        s, r = goi("ketoan", "POST", "/api/trips/tinh-thu", {"id": DANG_CHAY, "weight_origin": 50, "price": 10, "price_mode": "ton"})
        dung(s == 200 and r["tinh"]["doanh_thu"] == 500 and r["tinh"]["tan_tinh"] == 50, "KT: 50 t × 10 → doanh thu 500 (theo số đang gõ)", r["tinh"].get("doanh_thu"))
        db.expire_all()
        p7 = db.get(M.Trip, DANG_CHAY)
        dung((p7.weight_origin, p7.price) == cu, "tính thử không ghi gì vào phiếu", (p7.weight_origin, p7.price))
        s, r = goi("ketoan", "POST", "/api/trips/tinh-thu", {"id": DANG_CHAY, "weight_origin": 50, "price_mode": "chuyen", "price": 900})
        dung(s == 200 and r["tinh"]["doanh_thu"] == 900, "trọn chuyến: doanh thu = giá, không nhân tấn", r["tinh"].get("doanh_thu"))
        s, r = goi("thabok", "POST", "/api/trips/tinh-thu", {"id": DANG_CHAY, "weight_origin": 50, "price": 99999})
        dung(s == 200 and "doanh_thu" not in r["tinh"] and "don_gia" not in r["tinh"] and "chi" not in r["tinh"],
             "Bãi: kết quả không có tiền bán / tiền chi (giá gửi lên bị bỏ)", sorted(r["tinh"]))
        s, r = goi("ketoan", "POST", "/api/trips/tinh-thu", {"weight_origin": 40, "weight_dest": 39, "price": 12.5, "odo_out": 1000, "odo_back": 1450})
        dung(s == 200 and r["tinh"]["doanh_thu"] == 487.5 and r["odo_km"] == 450 and r["hao_t"] == 1 and r["tinh"]["hao_hut_pct"] == 2.5,
             "phiếu mới: cân cuối 39 × 12,5 = 487,5 · km 450 · hao 1 t (2,5 %)", r)
        s, r = goi("ketoan", "POST", "/api/trips/tinh-thu", {"weight_origin": "abc"})
        dung(s == 422, "số sai → 422", s)
        s, r = goi("ketoan", "POST", "/api/trips/tinh-thu", {"weight_origin": 40, "price": 10, "expenses": [
            {"section": "travel", "qty": 2, "unit_price": 50000, "currency": "LAK"}, {"section": "fuel", "qty": 100, "unit_price": 1, "currency": "USD"}]})
        dung(s == 200 and r["tinh"]["chi"]["travel"] == 100000 and r["tinh"]["chi"]["fuel"] == 100 * r["tinh"]["chi"]["fuel"] / 100,
             "dòng chi đang sửa đi vào tổng chi (mục IV 100.000 LAK)", r["tinh"]["chi"])
        s, r = goi("thabok", "POST", "/api/trips/tinh-thu", {"kind": "giao", "goods": [
            {"loai": "hang", "qty_t": 20}, {"loai": "hang", "qty_t": "15.5"}, {"loai": "hao_hut", "qty_t": 1}]})
        dung(s == 200 and r["weight_origin"] == 35.5 and r["tinh"]["tan_tinh"] == 35.5, "dòng hàng đang sửa: cân đầu = tổng tấn (bỏ dòng hao hụt)", r["weight_origin"])
        kh_rt = {"customer_id": "0834a9e9606b", "route_id": "b9213bcb64b9", "goods_type": "iron_ore", "weight_origin": 40}
        s, r = goi("ketoan", "POST", "/api/trips/tinh-thu", kh_rt)
        g = r.get("gia_hop_dong") or {}
        dung(s == 200 and g.get("price") == 12.5 and g.get("price_ccy") == "USD" and g.get("hire_price") == 12 and r["tinh"]["doanh_thu"] == 500,
             "có khách + tuyến, chưa có giá → giá hợp đồng 12,5 USD gợi ý và đi vào phép tính", g)
        s, r = goi("ketoan", "POST", "/api/trips/tinh-thu", dict(kh_rt, price=11))
        dung(s == 200 and r["gia_hop_dong"] is None and r["tinh"]["doanh_thu"] == 440, "đã gõ giá → không gợi ý, giữ giá đang gõ", r["gia_hop_dong"])
        s, r = goi("thabok", "POST", "/api/trips/tinh-thu", kh_rt)
        dung(s == 200 and r["gia_hop_dong"] is None, "Bãi: không gợi ý giá (không thấy tiền bán)", r["gia_hop_dong"])

        print("== 5. bảng hàng trên phiếu")
        q = goi("thabok", "GET", "/api/trips/" + DANG_CHAY)[1]["quyen"]["hang"]
        dung(not q["bang"] and not q["tu_lo"] and q["sua"] and not q["gui"] and q["nhac_can_mo"] and q["nhac"] == "goods_hint_gom",
             "DO gom một mặt hàng đang chạy: không bảng, không gửi dòng hàng, nhắc cân mỏ", q)
        q = goi("admin", "GET", "/api/trips/" + DA_KHOA)[1]["quyen"]["hang"]
        dung(not q["sua"] and q["nhac"] == "goods_locked_gom" and not q["nhac_can_mo"], "DO gom đã về bãi: hàng đã vào kho — khoá, câu nhắc riêng", q)
        q = goi("thabok", "GET", "/api/trips-moi?kind=giao")[1]["quyen"]["hang"]
        dung(q["bang"] and q["tu_lo"] and q["sua"] and q["gui"] and q["nhac"] == "goods_hint_giao", "DO giao mới: có bảng + cột lấy từ lô", q)

        print("== 6. xe thuê: chủ xe theo xe kể cả khi màn gửi kèm số xe")
        from types import SimpleNamespace
        from routes import phieu as RP
        xe = db.query(M.Vehicle).filter(M.Vehicle.owner_type == "joint", M.Vehicle.owner_id.isnot(None)).first()
        p = M.Trip(doc_no="THU-Q-CHU-XE", kind="giao")
        RP._ap_truong(db, p, {"vehicle_id": xe.id, "truck_no": xe.truck_no, "plate_trailer": "SUA-TAY", "company": "joint",
                              "owner_name": xe.owner_name}, SimpleNamespace(role="yard", full_name="thu"))
        dung(p.owner_id == xe.owner_id and p.company == "joint" and p.plate_trailer == "SUA-TAY",
             "gửi truck_no: vẫn gắn owner_id của xe, giữ biển rơ-moóc sửa tay", (p.owner_id, xe.owner_id, p.plate_trailer))
        p = M.Trip(doc_no="THU-Q-CHU-XE2", kind="giao")
        RP._ap_truong(db, p, {"vehicle_id": xe.id}, SimpleNamespace(role="yard", full_name="thu"))
        dung(p.owner_id == xe.owner_id and p.company == "joint" and p.truck_no == xe.truck_no, "chỉ gửi mã xe: chép số xe, biển, chủ xe như cũ",
             (p.owner_id, p.truck_no))
    finally:
        app.dependency_overrides.clear()
        db.close()
        ngoai.rollback()
        conn.close()
    print("\n%d/%d đúng" % (sum(KQ), len(KQ)))
    sys.exit(0 if all(KQ) else 1)


if __name__ == "__main__":
    main()
