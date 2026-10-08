# -*- coding: utf-8 -*-
"""Thử 08/10 (góp ý anh Khampla, chủ dự án duyệt):
  · KHOẢN MỤC CHI PHÍ cấu hình được (services/khoan_muc, routes/khoan_muc): thêm khoản mục IV–VI tên ba thứ tiếng, cách trả mặc định
    theo khoản, đổi mặc định thì dòng cũ giữ cách trả đang có, ngưng / không ngưng được, quyền.
  · ĐIỂM ĐỔ mở lại ở trang điều xe (services/diem_do_web, routes/phieu_linh): trạm ngoài thêm / sửa / ngưng; kho dầu EPL chọn từ danh
    mục kho trên Web, tên / trạng thái chép từ Web; không xoá.

    python kiem/thu_khoan_muc_diem_do.py

Chạy trong một giao dịch trên bản sao _d7, cuối ROLLBACK — không ghi gì. Danh mục kho Web được GIẢ (không gọi mạng) trừ câu cuối: đọc
thật danh mục kho một lần (chỉ đọc) để chắc đọc đúng khuôn trả về."""
import os
import sys
from types import SimpleNamespace

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
from dotenv import load_dotenv                          # noqa: E402
load_dotenv(os.path.join(GOC, ".env"))

from fastapi.testclient import TestClient               # noqa: E402
from sqlalchemy import create_engine, text              # noqa: E402
from sqlalchemy.orm import Session                      # noqa: E402

import models as M                                      # noqa: E402
from database import get_db                             # noqa: E402
from main import app                                    # noqa: E402
from services import ban_giao as BG                     # noqa: E402
from services import diem_do_web as DDW                 # noqa: E402
from services import khoan_muc as KMC                   # noqa: E402
from services import tinh_toan as TT                    # noqa: E402

KQ = []
PHIEU = "ab65dc282091"          # G4-0007-10/EPL — mục IV có x_food (theo mặc định "chi ngay")
KHO_GIA = [
    {"wh_id": 23, "code": "KHO-TB", "name": "Kho dầu Thà Bốc · ສາງນໍ້າມັນ ທ່າບົກ", "address": "Thà Bốc", "active": True, "loai": "Kho công ty", "don_vi": "Demo EPL"},
    {"wh_id": 999, "code": "KHO-MOI-THU", "name": "Kho dầu mới (thử)", "address": None, "active": True, "loai": "Kho công ty", "don_vi": "Demo EPL"},
    {"wh_id": 22, "code": "KHO-PT", "name": "Kho phụ tùng Thà Bốc", "address": None, "active": True, "loai": "Kho công ty", "don_vi": "Demo EPL"},
]


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
    kho_that = DDW.kho_web
    DDW.kho_web = lambda: [dict(w) for w in KHO_GIA]

    def goi(u, method, duong, body=None):
        r = c.request(method, duong, json=body, headers={"Authorization": "Bearer " + TK[u]})
        try:
            return r.status_code, r.json()
        except ValueError:
            return r.status_code, None

    try:
        for u in ("thabok", "ketoancp", "khonl", "admin"):
            TK[u] = c.post("/api/dang-nhap", json={"username": u, "password": "1234"}).json()["token"]

        print("== 1. khoản mục chi phí — danh mục")
        s, km = goi("thabok", "GET", "/api/khoan-muc")
        dung(s == 200 and "x_water" in km["items"]["travel"] and km["items"]["fuel"] == ["diesel"] and km["pay_default"].get("x_water") == "luong",
             "GET /api/khoan-muc: bộ có sẵn như trước (gieo từ danh sách cũ), x_water mặc định cùng lương", km["items"]["travel"][:4])
        s, ds = goi("thabok", "GET", "/api/khoan-muc/danh-sach")
        dung(s == 200 and not ds["quyen"]["sua"] and any(x["key"] == "x_food" and x["so_dong"] > 0 for x in ds["items"]),
             "danh sách: Bãi xem được, không sửa; có số dòng đang dùng", ds["quyen"])
        s, ds = goi("ketoancp", "GET", "/api/khoan-muc/danh-sach")
        dung(s == 200 and ds["quyen"]["sua"], "KT Chi phí VC: sửa được", ds["quyen"])

        print("== 2. thêm khoản mới")
        s, r = goi("ketoancp", "POST", "/api/khoan-muc", {"section": "travel", "name_vi": "Tiền vé phà", "name_lo": "ຄ່າປີ້ແພ", "pay_default": "luong"})
        moi = r if s == 200 else {}
        dung(s == 200 and moi["key"].startswith("km_") and not moi["built_in"] and moi["pay_default"] == "luong",
             "KT Chi phí thêm «Tiền vé phà» (mục IV, trả cùng lương)", r)
        s, km = goi("thabok", "GET", "/api/khoan-muc")
        dung(moi.get("key") in km["items"]["travel"] and km["names"].get(moi.get("key"), {}).get("lo") == "ຄ່າປີ້ແພ"
             and km["pay_default"].get(moi.get("key")) == "luong", "khoản mới có ngay trên phiếu: ô chọn mục IV, tên ba thứ tiếng, mặc định cùng lương",
             km["names"].get(moi.get("key")))
        dung(TT.cach_tra(SimpleNamespace(item_key=moi.get("key"), pay_channel=None, section="travel"), "EPL") == "luong",
             "phép tính (tinh_toan.cach_tra) theo mặc định của khoản mới")
        dung(BG._ten(db, SimpleNamespace(part_id=None, item_name=None, item_key=moi.get("key"))) == ("Tiền vé phà", "ຄ່າປີ້ແພ"),
             "tên dòng phía máy chủ (phiếu chi, bút toán) lấy tên khoản mới")
        s, r = goi("thabok", "POST", "/api/khoan-muc", {"section": "travel", "name_vi": "Bãi thêm"})
        dung(s == 403, "Bãi thêm khoản → 403", s)
        s, r = goi("ketoancp", "POST", "/api/khoan-muc", {"section": "fuel", "name_vi": "Xăng"})
        dung(s == 422 and r["detail"]["ma"] == "MUC_SAI", "thêm khoản mục III (dầu) → 422 (mã hàng kho chỉ có dầu)", r)
        s, r = goi("ketoancp", "POST", "/api/khoan-muc", {"section": "travel", "name_vi": "tiền vé phà"})
        dung(s == 409 and r["detail"]["ma"] == "TRUNG_TEN", "trùng tên trong mục → 409", r)
        s, r = goi("ketoancp", "POST", "/api/khoan-muc", {"section": "travel"})
        dung(s == 422 and r["detail"]["ma"] == "THIEU_TEN", "thiếu tên → 422", r)

        print("== 3. đổi cách trả mặc định — dòng cũ giữ cách trả đang có")
        food = next(x for x in goi("ketoancp", "GET", "/api/khoan-muc/danh-sach")[1]["items"] if x["key"] == "x_food")
        truoc = {e.id: e.pay_channel for e in db.query(M.TripExpense).filter_by(item_key="x_food").all()}
        s, r = goi("ketoancp", "PUT", "/api/khoan-muc/" + food["id"], {"pay_default": "luong"})
        db.expire_all()
        sau = {e.id: e.pay_channel for e in db.query(M.TripExpense).filter_by(item_key="x_food").all()}
        dung(s == 200 and r["pay_default"] == "luong" and TT.CACH_TRA_MAC_DINH.get("x_food") == "luong",
             "x_food: mặc định chi ngay → cùng lương", r.get("pay_default"))
        dung(all((truoc[k] or "tien_mat") == (sau[k] or "") or (truoc[k] is None and sau[k] == "tien_mat") for k in truoc) and any(v == "tien_mat" for v in sau.values()),
             "dòng x_food cũ (đang theo mặc định) ghi rõ «chi ngay» — phiếu cũ không đổi nghĩa", (len(truoc), list(sau.values())[:4]))
        dung(TT.cach_tra(SimpleNamespace(item_key="x_food", pay_channel=None, section="travel"), "EPL") == "luong",
             "dòng mới x_food từ nay theo mặc định mới (cùng lương)")
        s, r = goi("ketoancp", "PUT", "/api/khoan-muc/" + food["id"], {"pay_default": "chuyen_khoan"})
        dung(s == 422, "cách trả lạ → 422", s)

        print("== 4. ngưng dùng")
        dsk = {x["key"]: x for x in goi("ketoancp", "GET", "/api/khoan-muc/danh-sach")[1]["items"]}
        s, r = goi("ketoancp", "PUT", "/api/khoan-muc/" + dsk["diesel"]["id"], {"active": False})
        dung(s == 409 and r["detail"]["ma"] == "KHONG_NGUNG_DUOC", "ngưng «dầu» → 409 (máy dùng)", r)
        s, r = goi("ketoancp", "PUT", "/api/khoan-muc/" + dsk["x_border"]["id"], {"active": False})
        s2, km = goi("thabok", "GET", "/api/khoan-muc")
        dung(s == 200 and "x_border" not in km["items"]["travel"] and "x_border" in km["all_items"]["travel"],
             "ngưng «x_border»: hết trên ô chọn, dòng cũ vẫn có tên (all_items)")
        s, r = goi("ketoancp", "PUT", "/api/khoan-muc/" + dsk["x_border"]["id"], {"name_vi": "Đổi tên khoản có sẵn"})
        dung(s == 200 and r["name_vi"] is None, "khoản có sẵn: tên không đổi (theo từ điển giao diện)", r.get("name_vi"))

        print("== 5. điểm đổ — quyền")
        for u, mong in (("thabok", False), ("khonl", True), ("ketoancp", True), ("admin", True)):
            s, r = goi(u, "GET", "/api/fuel-places/quyen")
            dung(s == 200 and r["sua"] is mong, "%s: sửa điểm đổ = %s" % (u, mong), r)

        print("== 6. trạm dầu ngoài")
        ncc = db.query(M.Supplier).first()
        s, r = goi("ketoancp", "POST", "/api/fuel-places", {"code": "VN-THU", "name": "Trạm dầu thử Cầu Treo", "country": "VN", "supplier_id": ncc.id})
        tram = r if s == 200 else {}
        dung(s == 200 and tram["owner_type"] == "ngoai" and tram["supplier_name"] == ncc.name and tram["active"],
             "KT Chi phí thêm trạm ngoài (Việt Nam, gắn nhà cung cấp)", r)
        s, ds = goi("thabok", "GET", "/api/fuel-places")
        dung(any(x["id"] == tram.get("id") for x in ds), "trạm mới có ngay ở ô Nơi đổ (Bãi)")
        s, r = goi("ketoancp", "POST", "/api/fuel-places", {"code": "VN-THU", "name": "Trùng mã"})
        dung(s == 409 and r["detail"]["ma"] == "TRUNG_MA", "trùng mã → 409", r)
        s, r = goi("thabok", "POST", "/api/fuel-places", {"code": "LA-THU", "name": "Bãi thêm"})
        dung(s == 403, "Bãi thêm điểm đổ → 403", s)
        s, r = goi("ketoancp", "POST", "/api/fuel-places", {"code": "KHO-X", "name": "Kho", "owner_type": "epl"})
        dung(s == 422 and r["detail"]["ma"] == "KHO_TAO_O_WEB", "thêm kho dầu EPL ở đây → 422 (tạo ở Web, chọn từ danh mục kho)", r)
        s, r = goi("ketoancp", "PUT", "/api/fuel-places/" + tram.get("id", "-"), {"active": False, "note": "đóng cửa"})
        s2, ds = goi("thabok", "GET", "/api/fuel-places")
        dung(s == 200 and not r["active"] and not any(x["id"] == tram.get("id") for x in ds), "ngưng trạm → hết trên ô Nơi đổ", r.get("active"))
        s, r = goi("admin", "DELETE", "/api/fuel-places/" + tram.get("id", "-"))
        dung(s == 409 and r["detail"]["ma"] == "KHONG_XOA_DIEM", "xoá điểm đổ → 409 (ngưng dùng thay xoá)", r)

        print("== 7. kho dầu EPL từ danh mục kho trên Web (danh mục giả)")
        s, kho = goi("khonl", "GET", "/api/fuel-places/kho-web")
        tb = next((x for x in kho if x["code"] == "KHO-TB"), {}) if s == 200 else {}
        dung(s == 200 and tb.get("place_id") and next(x for x in kho if x["code"] == "KHO-MOI-THU")["place_id"] is None,
             "danh mục kho: KHO-TB đã là điểm đổ, kho mới chưa", [(x["code"], x["place_id"]) for x in kho] if s == 200 else kho)
        x = db.query(M.FuelPlace).filter_by(code="KHO-TB").first()
        db.refresh(x)
        dung(x.name == KHO_GIA[0]["name"] and x.wh_id == 23 and x.wh_synced_at is not None, "mở danh mục kho → KHO-TB chép tên, mã kho Web", x.name)
        s, r = goi("khonl", "POST", "/api/fuel-places/kho-web/999", {"country": "LA"})
        dung(s == 200 and r["code"] == "KHO-MOI-THU" and r["owner_type"] == "epl" and r["wh_id"] == 999,
             "KT kho xăng dầu chọn «Kho dầu mới (thử)» → điểm đổ kho dầu EPL mang mã kho", r)
        s, ds = goi("thabok", "GET", "/api/fuel-places")
        dung(any(x["code"] == "KHO-MOI-THU" and x["owner_type"] == "epl" for x in ds), "kho mới có trên ô Nơi đổ (lấy kho → xuất kho theo mã KHO-MOI-THU)")
        s, r2 = goi("khonl", "PUT", "/api/fuel-places/" + r.get("id", "-"), {"name": "Đổi tên ở đây", "country": "VN", "note": "kho thử"})
        dung(s == 200 and r2["name"] == "Kho dầu mới (thử)" and r2["country"] == "VN" and r2["note"] == "kho thử",
             "kho dầu EPL: chỉ sửa nước + ghi chú ở đây; tên theo Web", (r2.get("name"), r2.get("country")))
        KHO_GIA[1]["active"] = False
        KHO_GIA[1]["name"] = "Kho dầu mới (thử) — đã đổi tên"
        s, kq = goi("khonl", "POST", "/api/fuel-places/dong-bo-kho")
        db.expire_all()
        x = db.query(M.FuelPlace).filter_by(code="KHO-MOI-THU").first()
        dung(s == 200 and kq["cap_nhat"] >= 1 and not x.active and x.name.endswith("đã đổi tên"),
             "Web ngưng + đổi tên kho → «Cập nhật từ danh mục kho» chép theo", (kq, x.name, x.active))
        s, r = goi("khonl", "POST", "/api/fuel-places/kho-web/12345")
        dung(s == 404 and r["detail"]["ma"] == "KHONG_THAY_KHO", "kho không có trên Web → 404", r)
        s, r = goi("thabok", "GET", "/api/fuel-places/kho-web")
        dung(s == 403, "Bãi xem danh mục kho Web → 403", s)

        print("== 8. đọc thật danh mục kho trên Web (chỉ đọc)")
        try:
            that = kho_that()
            dung(len(that) > 0 and any(w["code"] == "KHO-TB" for w in that) and all(w["wh_id"] for w in that),
                 "đọc được danh mục kho (khuôn trả về đúng)", "%s kho" % len(that))
        except Exception as e:                                  # noqa: BLE001
            dung(False, "đọc được danh mục kho trên Web", e)
    finally:
        DDW.kho_web = kho_that
        app.dependency_overrides.clear()
        db.close()
        ngoai.rollback()
        conn.close()
    print("\n%d/%d đúng" % (sum(KQ), len(KQ)))
    sys.exit(0 if all(KQ) else 1)


if __name__ == "__main__":
    main()
