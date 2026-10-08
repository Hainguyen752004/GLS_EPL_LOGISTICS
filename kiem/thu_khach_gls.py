# -*- coding: utf-8 -*-
"""Thử Việc 9 (08/10) — KHÁCH HÀNG LÀ ĐỐI TƯỢNG GLS (services/khach_gls.py, routes/danh_muc.py, chi_tune.doi_tuong, dong_bo_nen).

    python kiem/thu_khach_gls.py

MỌI THỨ trong một giao dịch ngoài trên bản sao _d7, cuối ROLLBACK (kể cả ALTER TABLE thêm cột obj_id nếu d7 chưa có): không
ghi gì vào d7. KHÔNG gọi mạng: chi_tune._goi thay bằng danh mục Đối tượng GLS giả lập (list · detail · upsert khách); gọi đường
nào khác là bài hỏng.
"""
import os
import sys

GOC = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
URL = open(os.path.join(GOC, ".may_thu", "url_epl_lao_d7.txt"), encoding="utf-8").read().strip()
if "_d7" not in URL.rsplit("/", 1)[-1]:
    sys.exit("Chuỗi nối không trỏ bản sao _d7 — bài chỉ chạy trên bản sao.")
os.environ["DATABASE_URL"] = URL
os.environ["EPL_DANG_NHAP_GLS"] = "0"
os.environ["EPL_KHACH_GLS"] = "0"
sys.path.insert(0, os.path.join(GOC, "backend", "app"))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass

from fastapi import HTTPException                       # noqa: E402
from fastapi.testclient import TestClient               # noqa: E402
from sqlalchemy import create_engine, text              # noqa: E402
from sqlalchemy.orm import Session                      # noqa: E402

import models as M                                      # noqa: E402
from database import get_db                             # noqa: E402
from main import app                                    # noqa: E402
from services import chi_tune as CHI                    # noqa: E402
from services import dong_bo_nen as DBN                 # noqa: E402
from services import khach_gls as KG                    # noqa: E402

KQ, GOI, LA = [], [], []
GLS = {                                                 # danh mục Đối tượng GLS giả lập: ObjId → Detail
    1600: {"ObjId": 1600, "ObjectNo": "DEMO-CUS-LOTTE", "Name": "Lotte Mart Việt Nam", "Phone": "0903888999",
           "Address": "Quận 7, TP.HCM", "TaxID": None, "IsOrganization": True, "IsActive": True},
    1608: {"ObjId": 1608, "ObjectNo": "EPLKH-0834a9e9606b", "Name": "ຄຳຕຸ້ຍ", "Phone": None, "Address": None,
           "TaxID": None, "IsOrganization": False, "IsActive": True},
    1609: {"ObjId": 1609, "ObjectNo": "EPLKH-d9ecab4e135b", "Name": "ນາງ ວັນນາ", "Phone": None, "Address": None,
           "TaxID": None, "IsOrganization": False, "IsActive": True},
    1700: {"ObjId": 1700, "ObjectNo": "KH-TRUNG", "Name": "Khách trùng mã", "Phone": None, "Address": None,
           "TaxID": None, "IsOrganization": False, "IsActive": True},
}
LOI = {"mang": False}


def dung(dk, ten, ct=""):
    KQ.append(bool(dk))
    print(("  ✓ " if dk else "  SAI ") + ten + ((" — " + str(ct)[:300]) if ct != "" else ""))


def gia_goi(method, duong, body=None):
    GOI.append(duong)
    if LOI["mang"]:
        raise HTTPException(502, {"ma": "KHONG_GOI_DUOC", "loi": "giả lập mất mạng"})
    if duong == KG.DUONG_DS:
        q = (body.get("ObjKey") or "").lower()
        ds = [x for x in GLS.values() if x.get("ObjId") and (not q or (x["ObjectNo"] or "").lower() == q or q in (x["Name"] or "").lower())]
        return {"Data": [{k: x[k] for k in ("ObjId", "ObjectNo", "Name", "Phone", "Address", "TaxID", "IsActive")} for x in ds],
                "Pagination": {"PageNumber": 1, "PageSize": 100, "TotalRecords": len(ds), "TotalPages": 1 if ds else 0}}
    if duong == KG.DUONG_CT:
        return {"Detail": dict(GLS.get(body["ObjId"]) or {"ObjId": None})}
    if duong == "/api/v1/sales/debt/customer-detail":                       # công nợ một khách (tab Công nợ)
        return {"Summary": {"TotalDebt": 300, "CurrentDebt": 250, "OverdueDebt": 100, "TotalCollected": 50},
                "Aging": [], "Collections": [], "Orders": [],
                "Debts": [{"OrderCode": "SO-QUA", "RCTD_EXPIRE": "2026-01-01T00:00:00", "RCTD_DEBTMONEY": 100, "RETK_PAYMENTAMOUNT": 100, "CurrencyCode": "USD"},
                          {"OrderCode": "SO-CHUA", "RCTD_EXPIRE": "2099-01-01T00:00:00", "RCTD_DEBTMONEY": 150, "RETK_PAYMENTAMOUNT": 200, "CurrencyCode": "USD"},
                          {"OrderCode": "SO-XONG", "RCTD_EXPIRE": "2026-01-01T00:00:00", "RCTD_DEBTMONEY": 0, "RETK_PAYMENTAMOUNT": 50, "CurrencyCode": "USD"}]}
    if duong == KG.DUONG_GHI:
        oid = max(GLS) + 1
        GLS[oid] = {"ObjId": oid, "ObjectNo": body["ObjectNo"], "Name": body["ObjectName"], "Phone": body.get("HandPhone"),
                    "Address": body.get("Address"), "TaxID": None, "IsOrganization": body.get("IsOrganization"), "IsActive": True}
        return oid
    LA.append((method, duong))
    raise HTTPException(500, {"ma": "DUONG_LA", "loi": duong})


def main():
    eng = create_engine(URL, connect_args={"options": "-c timezone=UTC"})
    conn = eng.connect()
    ngoai = conn.begin()
    conn.execute(text("SET LOCAL lock_timeout = '10s'"))
    conn.execute(text("ALTER TABLE customers ADD COLUMN IF NOT EXISTS obj_id INTEGER"))           # d7 chưa khởi động bản mới
    conn.execute(text("ALTER TABLE customers ADD COLUMN IF NOT EXISTS gls_synced_at TIMESTAMP WITHOUT TIME ZONE"))
    db = Session(bind=conn, join_transaction_mode="create_savepoint", autoflush=False)

    def _db():
        try:
            yield db
        finally:
            db.rollback()
    app.dependency_overrides[get_db] = _db
    c = TestClient(app, raise_server_exceptions=False)
    goc_goi = CHI._goi
    CHI._goi = gia_goi
    KG.quen()
    TK = {}

    def goi(u, method, duong, body=None):
        r = c.request(method, duong, json=body, headers={"Authorization": "Bearer " + TK[u]})
        try:
            return r.status_code, r.json()
        except ValueError:
            return r.status_code, None

    def ma(g):
        return ((g or {}).get("detail") or {}).get("ma")
    try:
        for u in ("admin", "ketoan", "thabok", "tx01"):
            r = c.post("/api/dang-nhap", json={"username": u, "password": "1234"})
            TK[u] = r.json()["token"]
        kham = db.get(M.Customer, "0834a9e9606b")
        dung(kham is not None and kham.code == "EPLKH-0834a9e9606b", "d7 có khách ຄຳຕຸ້ຍ mã EPLKH-0834a9e9606b")
        so_kh = db.query(M.Customer).count()

        print("== 0. quyền màn Khách hàng trên Web")
        s, r = goi("ketoan", "GET", "/api/customers/quyen")
        dung(s == 200 and {k: v for k, v in r.items() if k in ("edit", "assign_code", "view_debt", "view_rates", "edit_rates", "gls")}
             == {"edit": True, "assign_code": True, "view_debt": True, "view_rates": True, "edit_rates": True, "gls": False},
             "KT Thu/Chi VC: sửa, gán mã, xem công nợ, xem / sửa bảng giá", r)
        dung(r["lookups"] == {"invoice_modes": ["phieu", "thang"], "cust_types": ["person", "company"],
                              "currencies": ["LAK", "USD", "THB", "VND", "CNY"], "price_modes": ["ton", "chuyen"],
                              "goods_types": ["iron_ore", "other_goods"]}, "danh sách chọn của màn lấy từ hằng số máy chủ", r["lookups"])
        s, r = goi("thabok", "GET", "/api/customers/quyen")
        dung(s == 200 and r["edit"] is True and not (r["assign_code"] or r["view_debt"] or r["view_rates"] or r["edit_rates"]),
             "Bãi: sửa danh mục, không gán mã, không thấy tiền", r)
        s, r = goi("tx01", "GET", "/api/customers/quyen")
        dung(s == 200 and not any(v for k, v in r.items() if k not in ("gls", "lookups", "view_contracts")), "tài xế: không làm gì ở màn này", r)
        quyen_kt = goi("ketoan", "GET", "/api/customers/quyen")[1]

        print("== 1. tìm khách bên Đối tượng GLS")
        s, r = goi("ketoan", "GET", "/api/customers/gls?q=lotte")
        dung(s == 200 and [x["obj_id"] for x in r["items"]] == [1600] and r["items"][0]["customer_id"] is None,
             "KT tìm 'lotte' → ObjId 1600, chưa có hồ sơ", r)
        s, r = goi("tx01", "GET", "/api/customers/gls?q=lotte")
        dung(s == 403, "tài xế tìm khách GLS → 403", s)
        n = len(GOI)
        goi("ketoan", "GET", "/api/customers/gls?q=lotte")
        dung(len(GOI) == n, "tìm lại cùng chữ → dùng kết quả đã nhớ, không gọi GLS")

        print("== 2. lập hồ sơ vận tải cho đối tượng GLS")
        s, r = goi("ketoan", "POST", "/api/customers/gls/1600", {"invoice_mode": "thang"})
        dung(s == 200 and r["obj_id"] == 1600 and r["name"] == "Lotte Mart Việt Nam" and r["code"] == "DEMO-CUS-LOTTE"
             and r["phone"] == "0903888999" and r["cust_type"] == "company" and r["invoice_mode"] == "thang",
             "POST /gls/1600 → chép tên · điện thoại · mã, loại công ty, cách hoá đơn tháng", r)
        lotte = r["id"]
        dt_ = db.get(M.DoiTuongTune, ("khach", lotte))
        dung(dt_ is not None and dt_.obj_id == 1600 and dt_.object_no == "DEMO-CUS-LOTTE", "bảng nhớ đối tượng kế toán khớp obj_id")
        s, r = goi("ketoan", "POST", "/api/customers/gls/1600", {})
        dung(s == 200 and r["id"] == lotte and db.query(M.Customer).count() == so_kh + 1, "lập lại → cùng hồ sơ, không tạo trùng")
        s, r = goi("ketoan", "GET", "/api/customers/gls?q=DEMO-CUS-LOTTE")
        dung(s == 200 and r["items"][0]["customer_id"] == lotte, "tìm đúng mã → dòng kèm customer_id đã có", r)
        s, r = goi("ketoan", "POST", "/api/customers/gls/1608", {})
        dung(s == 200 and r["id"] == "0834a9e9606b" and r["obj_id"] == 1608, "khách cũ cùng mã (ຄຳຕຸ້ຍ) → nhận làm hồ sơ, giữ id cũ", r)
        s, r = goi("ketoan", "POST", "/api/customers/gls/999999", {})
        dung(s == 404 and ma(r) == "KHACH_GLS_KHONG_CO", "đối tượng không có bên GLS → 404", r)
        db.add(M.Customer(id="thu-trung-ma", name="Thử trùng mã", code="KH-TRUNG", obj_id=1, invoice_mode="phieu", active=True))
        db.flush()
        s, r = goi("ketoan", "POST", "/api/customers/gls/1700", {})
        dung(s == 409 and ma(r) == "MA_KHACH_TRUNG", "mã đã gắn đối tượng GLS khác → 409", r)
        db.query(M.Customer).filter(M.Customer.id == "thu-trung-ma").delete(); db.flush()   # yêu cầu 409 đã rollback dòng này
        s, r = goi("tx01", "POST", "/api/customers/gls/1600", {})
        dung(s == 403, "tài xế lập hồ sơ → 403", s)
        tuyen = db.query(M.Route).filter(M.Route.active.is_(True)).first()
        import datetime as _dt
        hom_nay = _dt.date.today()
        for tu, gia in ((hom_nay - _dt.timedelta(days=60), 10), (hom_nay - _dt.timedelta(days=5), 12), (hom_nay + _dt.timedelta(days=30), 15)):
            s, r = goi("ketoan", "POST", "/api/customers/%s/bang-gia" % lotte, {"route_id": tuyen.id, "price": gia, "valid_from": tu.isoformat()})
        s, r = goi("ketoan", "GET", "/api/customers/%s/bang-gia" % lotte)
        dang = [x["price"] for x in r if x["current"]]
        dung(s == 200 and dang == [12], "bảng giá: chỉ dòng giá mới nhất đã tới ngày áp dụng mang current", [(x["price"], x["valid_from"], x["current"]) for x in r])

        print("== 3. luật cũ (EPL_KHACH_GLS=0)")
        n = len(GOI)
        s, r = goi("ketoan", "POST", "/api/customers", {"name": "Khách riêng bên em"})
        dung(s == 200 and r["obj_id"] is None and len(GOI) == n, "thêm khách không obj_id → khách riêng, không gọi GLS", r)
        s, r = goi("ketoan", "PUT", "/api/customers/" + lotte, {"code": "DEMO-CUS-LOTTE-2"})
        dung(s == 200 and r["obj_id"] is None and r["code"] == "DEMO-CUS-LOTTE-2", "đổi mã khách → bỏ obj_id (tìm lại theo mã mới)", r)
        s, r = goi("ketoan", "POST", "/api/customers/gls/1600", {})          # gắn lại cho các bước sau
        dung(s == 200 and r["id"] == lotte and r["code"] == "DEMO-CUS-LOTTE", "gắn lại 1600 → cùng hồ sơ, mã chép lại từ GLS", r)

        print("== 4. luật mới (EPL_KHACH_GLS=1)")
        os.environ["EPL_KHACH_GLS"] = "1"
        s, r = goi("ketoan", "POST", "/api/customers", {"name": "Khách tạo bên GLS", "phone": "020 555", "cust_type": "company",
                                                         "invoice_mode": "thang"})
        moi = max(GLS)
        dung(s == 200 and r["obj_id"] == moi and r["code"].startswith("EPLKH-") and GLS[moi]["Name"] == "Khách tạo bên GLS"
             and GLS[moi]["IsOrganization"] is True and r["invoice_mode"] == "thang",
             "thêm khách không obj_id → tạo đối tượng GLS (EPLKH-…) rồi lập hồ sơ", r)
        s, r = goi("ketoan", "POST", "/api/customers", {"name": "Trùng", "code": "DEMO-CUS-LOTTE"})
        dung(s == 409 and ma(r) == "MA_DA_CO_BEN_GLS", "mã đã có bên GLS → 409, bảo chọn khách đó", r)
        s, r = goi("thabok", "POST", "/api/customers", {"name": "Bãi gõ mã", "code": "KH-BAI-01"})
        dung(s == 403 and ma(r) == "MA_KHACH_KE_TOAN", "vai Bãi gõ mã khách → 403 (chỉ KT Thu/Chi VC, Sếp)", r)
        s, r = goi("ketoan", "POST", "/api/customers", {"obj_id": 1608, "note": "ghi chú vận tải"})
        dung(s == 200 and r["id"] == "0834a9e9606b" and r["note"] == "ghi chú vận tải", "POST có obj_id → liên kết, ghi phần riêng", r)
        s, r = goi("ketoan", "PUT", "/api/customers/" + lotte, {"name": "Đổi tên ở đây"})
        dung(s == 409 and ma(r) == "SUA_O_GLS", "đổi tên khách đã liên kết → 409 sửa ở màn Đối tượng GLS", r)
        s, r = goi("ketoan", "PUT", "/api/customers/" + lotte, {"name": "Lotte Mart Việt Nam", "phone": "0903888999",
                                                                 "address": "Quận 7, TP.HCM", "code": "DEMO-CUS-LOTTE",
                                                                 "invoice_mode": "phieu", "note": "n1"})
        dung(s == 200 and r["invoice_mode"] == "phieu" and r["note"] == "n1" and r["obj_id"] == 1600,
             "form gửi lại đúng thông tin chung + đổi phần riêng → 200", r)

        print("== 5. SO / đề nghị thu dùng thẳng obj_id")
        n = len(GOI)
        oid = CHI.doi_tuong(db, "khach", lotte, "Lotte", ma="DEMO-CUS-LOTTE")
        dung(oid == 1600 and len(GOI) == n, "doi_tuong(khach) có obj_id → 1600, không gọi GLS")
        kh = db.get(M.Customer, "d9ecab4e135b")
        kh.obj_id = None; db.flush()                                         # d7 có thể đã chạy doi_chieu --ghi — đưa về chưa gắn
        dung(kh is not None and kh.obj_id is None and db.get(M.DoiTuongTune, ("khach", kh.id)) is not None,
             "ນາງ ວັນນາ chưa liên kết, đã có bảng nhớ đối tượng kế toán")
        oid = CHI.doi_tuong(db, "khach", kh.id, kh.name, ma=kh.code); db.flush()   # đường thật commit sau đó
        dung(oid == db.get(M.DoiTuongTune, ("khach", kh.id)).obj_id and kh.obj_id == oid, "đường cũ → ghi luôn obj_id lên khách", oid)

        print("== 6. chép lại thông tin chung từ GLS")
        GLS[1600]["Name"] = "Lotte Mart (đổi tên ở GLS)"
        GLS[1608] = {"ObjId": None}                                          # đối tượng bị xoá bên GLS
        s, r = goi("ketoan", "POST", "/api/customers/dong-bo-gls")
        dung(s == 200 and r["cap_nhat"] >= 1 and [m["obj_id"] for m in r["mat"]] == [1608], "đồng bộ → 1600 đổi tên, 1608 mất", r)
        db.expire_all()
        dung(db.get(M.Customer, lotte).name == "Lotte Mart (đổi tên ở GLS)", "tên khách = tên bên GLS")
        names = [t for t, _ in DBN._viec()]
        dung("khach_gls" in names, "luồng nền có bước khach_gls khi EPL_KHACH_GLS=1", names)
        ket = {"da_hoi": {}, "cap_nhat": {}, "loi": None, "loi_ban_ghi": []}
        DBN._khach_gls(db, 50, ket, "khach_gls")
        dung(ket["da_hoi"].get("khach_gls", 0) == 0, "vừa chép xong → bước nền không hỏi lại (chép quá 60 phút mới hỏi)", ket)
        db.query(M.Customer).filter(M.Customer.obj_id.isnot(None)).update({M.Customer.gls_synced_at: None})
        LOI["mang"] = True
        try:
            DBN._khach_gls(db, 50, ket, "khach_gls")
            dung(False, "GLS mất mạng → dừng lượt")
        except DBN._DungLuot as e:
            dung("KHONG_GOI_DUOC" in str(e), "GLS mất mạng → dừng lượt (lượt sau thử lại)", e)
        LOI["mang"] = False
        os.environ["EPL_KHACH_GLS"] = "0"
        dung("khach_gls" not in [t for t, _ in DBN._viec()], "EPL_KHACH_GLS=0 → không có bước khach_gls")
        print("== 7. tab Chuyến & phiếu, tab Công nợ, quyền hợp đồng (màn Web)")
        kham_id = "0834a9e9606b"
        s, r = goi("ketoan", "GET", "/api/customers/%s/chuyen?thang=2020-01&tu_tim=true" % kham_id)
        dung(s == 200 and r["thang_hoi"] == "2020-01" and r["thang"] != "2020-01" and len(r["items"]) > 0,
             "tháng không có phiếu + tu_tim → sang tháng gần nhất có phiếu", (s, r.get("thang"), len(r.get("items") or [])))
        dung(r["xem_tien"] is True and r["tong"]["so_phieu"] == len(r["items"])
             and abs(r["tong"]["tan"] - sum(float(x["tan"] or 0) for x in r["items"])) < 0.01
             and all("so_trang_thai" in x for x in r["items"]) and isinstance(r["tong"]["doanh_thu"], dict),
             "KT: có tiền, cộng tháng (tấn, doanh thu theo tiền) tính ở máy chủ", r["tong"])
        s2, r2 = goi("ketoan", "GET", "/api/customers/%s/chuyen?thang=2020-01" % kham_id)
        dung(s2 == 200 and r2["items"] == [] and r2["thang"] == "2020-01", "không tu_tim → đúng tháng hỏi, rỗng", r2.get("thang"))
        s3, r3 = goi("thabok", "GET", "/api/customers/%s/chuyen?thang=%s" % (kham_id, r["thang"]))
        dung(s3 == 200 and r3["xem_tien"] is False and r3["tong"]["doanh_thu"] is None
             and not any(k in x for x in r3["items"] for k in ("don_gia", "doanh_thu", "so_order")),
             "Bãi: không có đơn giá / thành tiền / SO", r3["tong"])
        s, r = goi("ketoan", "GET", "/api/customers/%s/chuyen?thang=2026-13" % kham_id)
        dung(s == 422, "tháng sai → 422", s)
        s, r = goi("ketoan", "GET", "/api/customers/%s/cong-no-ke-toan" % lotte)
        tt = {x["so"]: (x["tinh_trang"], x["qua_han_ngay"]) for x in (r.get("no") or [])}
        dung(s == 200 and tt.get("SO-QUA", ("",))[0] == "qua_han" and (tt["SO-QUA"][1] or 0) > 0
             and tt.get("SO-CHUA") == ("chua_den_han", None) and tt.get("SO-XONG") == ("da_thu_du", None),
             "công nợ: tình trạng từng SO tính ở máy chủ (quá hạn n ngày · chưa đến hạn · đã thu đủ)", tt)
        s, r = goi("ketoan", "GET", "/api/customers/quyen")
        dung(r["view_contracts"] and r["edit_contracts"] and r["view_contract_files"], "KT: xem / sửa hợp đồng, mở bản scan", r)
        s, r = goi("thabok", "GET", "/api/customers/quyen")
        dung(r["view_contracts"] and not r["edit_contracts"] and not r["view_contract_files"], "Bãi: xem hợp đồng, không sửa, không mở bản scan", r)
        s, r = goi("tx01", "GET", "/api/customers/quyen")
        dung(not r["view_contracts"], "tài xế: không xem hợp đồng", r.get("view_contracts"))
        dung(not LA, "không gọi đường GLS nào ngoài list · detail · upsert khách · công nợ", LA)
    finally:
        CHI._goi = goc_goi
        app.dependency_overrides.clear()
        db.close()
        ngoai.rollback()
        conn.close()
    print("\n%d/%d đúng" % (sum(KQ), len(KQ)))
    sys.exit(0 if all(KQ) else 1)


if __name__ == "__main__":
    main()
