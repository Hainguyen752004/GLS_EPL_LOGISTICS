# -*- coding: utf-8 -*-
"""Thử Việc 10 (08/10) — NHÀ CUNG CẤP + CHỦ XE LIÊN KẾT là đối tượng danh mục nhà cung cấp chung (services/doi_tuong_gls.py,
routes/nha_cung_cap.py, routes/chu_xe.py, chi_tune.doi_tuong, dong_bo_nen bước ncc_gls).

    python kiem/thu_ncc_gls.py

MỌI THỨ trong một giao dịch ngoài trên bản sao _d7, cuối ROLLBACK (kể cả ALTER TABLE thêm cột nếu d7 chưa có): không ghi gì vào d7.
KHÔNG gọi mạng: chi_tune._goi thay bằng danh mục nhà cung cấp chung giả lập (list · detail · upsert suppliers); gọi đường nào khác là
bài hỏng. Tài xế (EPLTX-) không đổi: doi_tuong(tai_xe) vẫn đi đường cũ.
"""
import os
import sys

GOC = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
URL = open(os.path.join(GOC, ".may_thu", "url_epl_lao_d7.txt"), encoding="utf-8").read().strip()
if "_d7" not in URL.rsplit("/", 1)[-1]:
    sys.exit("Chuỗi nối không trỏ bản sao _d7 — bài chỉ chạy trên bản sao.")
os.environ["DATABASE_URL"] = URL
os.environ["EPL_DANG_NHAP_GLS"] = "0"
os.environ["EPL_NCC_GLS"] = "0"
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
from services import doi_tuong_gls as DT                # noqa: E402

KQ, GOI, LA = [], [], []
DS, CT, GHI = DT.duong("ncc", "list"), DT.duong("ncc", "detail"), DT.duong("ncc", "upsert")
GLS = {                                                 # danh mục nhà cung cấp chung giả lập: ObjId → Detail
    1615: {"ObjId": 1615, "ObjectNo": "EPLNCC-804c0e8ff1d8", "Name": "ຊີບປີງ ລາວ (ສາງພາສີ)", "Phone": None, "Address": None, "IsActive": True},
    1606: {"ObjId": 1606, "ObjectNo": "EPLCX-0a073ea75bb3", "Name": "ທ້າວ ຄຳຫລ້າ", "Phone": None, "Address": None, "IsActive": True},
    1800: {"ObjId": 1800, "ObjectNo": "NCC-LOP-01", "Name": "Lốp Đức Thành", "Phone": "0912 000 111", "Address": "Viêng Chăn", "IsActive": True},
    1801: {"ObjId": 1801, "ObjectNo": "CX-BOUN", "Name": "ທ້າວ ບຸນມີ", "Phone": "020 7777 1234", "Address": "Thà Bốc", "IsActive": True},
}


def dung(dk, ten, ct=""):
    KQ.append(bool(dk))
    print(("  ✓ " if dk else "  SAI ") + ten + ((" — " + str(ct)[:300]) if ct != "" else ""))


def gia_goi(method, duong, body=None):
    GOI.append(duong)
    if duong == DS:
        q = (body.get("ObjKey") or "").lower()
        ds = [x for x in GLS.values() if x.get("ObjId") and (not q or (x["ObjectNo"] or "").lower() == q or q in (x["Name"] or "").lower())]
        return {"Data": [dict(x) for x in ds], "Pagination": {"TotalRecords": len(ds), "TotalPages": 1 if ds else 0}}
    if duong == CT:
        return {"Detail": dict(GLS.get(body["ObjId"]) or {"ObjId": None})}
    if duong == GHI:
        oid = max(GLS) + 1
        GLS[oid] = {"ObjId": oid, "ObjectNo": body["ObjectNo"], "Name": body["ObjectName"], "Phone": body.get("HandPhone"),
                    "Address": body.get("Address"), "IsActive": True, "IsOrganization": body.get("IsOrganization"),
                    "Description": body.get("Description")}
        return oid
    LA.append((method, duong))
    raise HTTPException(500, {"ma": "DUONG_LA", "loi": duong})


def main():
    eng = create_engine(URL, connect_args={"options": "-c timezone=UTC"})
    conn = eng.connect()
    ngoai = conn.begin()
    conn.execute(text("SET LOCAL lock_timeout = '10s'"))
    for bang, cot in (("suppliers", "code VARCHAR"), ("suppliers", "phone VARCHAR"), ("suppliers", "address VARCHAR"),
                      ("suppliers", "obj_id INTEGER"), ("suppliers", "gls_synced_at TIMESTAMP WITHOUT TIME ZONE"),
                      ("owners", "code VARCHAR"), ("owners", "obj_id INTEGER"), ("owners", "gls_synced_at TIMESTAMP WITHOUT TIME ZONE"),
                      ("customers", "obj_id INTEGER"), ("customers", "gls_synced_at TIMESTAMP WITHOUT TIME ZONE")):
        conn.execute(text("ALTER TABLE %s ADD COLUMN IF NOT EXISTS %s" % (bang, cot)))      # d7 chưa khởi động bản mới
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
    DT.quen()
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
        for u in ("ketoancp", "ketoan", "thabok", "admin"):
            TK[u] = c.post("/api/dang-nhap", json={"username": u, "password": "1234"}).json()["token"]
        ncc_cu = db.get(M.Supplier, "804c0e8ff1d8")
        chu_cu = db.get(M.Owner, "0a073ea75bb3")
        dung(ncc_cu is not None and chu_cu is not None, "d7 có NCC chip Lào và chủ xe ທ້າວ ຄຳຫລ້າ")
        for x in (ncc_cu, chu_cu):
            x.obj_id = None
        chu_cu.phone = dt_phone = "020 5555 7777"
        db.flush()

        print("== 0. quyền màn Nhà cung cấp trên Web")
        q = {u: goi(u, "GET", "/api/suppliers/quyen")[1] for u in ("ketoancp", "ketoan", "thabok")}
        dung(q["ketoancp"]["edit"] and q["ketoancp"]["view_debt"] and q["ketoancp"]["request_pay"] and q["ketoancp"]["view_acct"],
             "KT Chi phí: sửa, xem công nợ, lập đề nghị trả, thấy mã kế toán", q["ketoancp"])
        dung(not q["ketoan"]["edit"] and q["ketoan"]["view_debt"] and not q["ketoan"]["request_pay"], "KT Thu/Chi: chỉ xem công nợ", q["ketoan"])
        dung(not any(q["thabok"][k] for k in ("edit", "view_debt", "request_pay", "view_acct")), "Bãi: không sửa, không thấy tiền / mã kế toán", q["thabok"])
        dung("x_tire" in q["ketoancp"]["lookups"]["item_keys"] and q["ketoancp"]["lookups"]["pay_methods"] == ["cash", "bank"],
             "danh sách chọn lấy từ máy chủ", q["ketoancp"]["lookups"])

        print("== 1. tìm trong danh mục nhà cung cấp chung")
        s, r = goi("ketoancp", "GET", "/api/suppliers/gls?q=lốp")
        dung(s == 200 and [x["obj_id"] for x in r["items"]] == [1800] and r["items"][0]["supplier_id"] is None
             and "owner_id" in r["items"][0], "KT Chi phí tìm 'lốp' → 1800, chưa có hồ sơ, kèm supplier_id / owner_id", r)
        s, r = goi("thabok", "GET", "/api/suppliers/gls?q=lốp")
        dung(s == 403, "Bãi tìm nhà cung cấp → 403", s)
        s, r = goi("ketoan", "GET", "/api/owners/gls?q=CX-BOUN")
        dung(s == 200 and [x["obj_id"] for x in r["items"]] == [1801], "KT Thu/Chi tìm chủ xe đúng mã → 1801", r)

        print("== 2. gắn hồ sơ vận tải")
        s, r = goi("ketoancp", "POST", "/api/suppliers/gls/1800", {"item_key": "x_tire", "acct_code": "625/4021", "payment_term": "t_monthly"})
        dung(s == 200 and r["obj_id"] == 1800 and r["name"] == "Lốp Đức Thành" and r["code"] == "NCC-LOP-01" and r["phone"] == "0912 000 111"
             and r["item_key"] == "x_tire" and r["acct_code"] == "625/4021", "NCC mới từ danh mục chung + phần riêng vận tải", r)
        lop = r["id"]
        dt_ = db.get(M.DoiTuongTune, ("ncc", lop))
        dung(dt_ is not None and dt_.obj_id == 1800, "bảng nhớ đối tượng kế toán (ncc) khớp", dt_ and dt_.obj_id)
        s, r = goi("ketoancp", "POST", "/api/suppliers/gls/1615", {})
        dung(s == 200 and r["id"] == "804c0e8ff1d8" and r["obj_id"] == 1615, "NCC cũ đã gửi chứng từ (bảng nhớ) → nhận làm hồ sơ, giữ id", r)
        s, r = goi("ketoan", "POST", "/api/owners/gls/1606", {"fee_pct": 3})
        dung(s == 200 and r["id"] == "0a073ea75bb3" and r["obj_id"] == 1606 and r["fee_pct"] == 3, "chủ xe cũ → nhận làm hồ sơ, phí 3 %", r)
        dung(r["phone"] == dt_phone, "danh mục chung để trống điện thoại → giữ số đang có (không xoá)", (dt_phone, r["phone"]))
        s, r = goi("ketoan", "POST", "/api/owners/gls/1801", {})
        dung(s == 200 and r["name"] == "ທ້າວ ບຸນມີ" and r["code"] == "CX-BOUN" and r["fee_pct"] == 2 and r["pay_mode"] == "phieu",
             "chủ xe mới từ danh mục chung, phí / cách trả mặc định", r)
        boun = r["id"]
        s, r = goi("ketoancp", "POST", "/api/owners/gls/1801", {})
        dung(s == 403, "KT Chi phí gắn chủ xe → 403 (chủ xe do KT Thu/Chi VC giữ)", s)
        s, r = goi("ketoancp", "POST", "/api/suppliers/gls/999999", {})
        dung(s == 404 and ma(r) == "DOI_TUONG_KHONG_CO" and "GLS" not in (r["detail"]["loi"] or ""),
             "không có trong danh mục → 404, câu báo không nhắc GLS", r)

        print("== 3. luật mới (EPL_NCC_GLS=1)")
        os.environ["EPL_NCC_GLS"] = "1"
        s, r = goi("ketoancp", "POST", "/api/suppliers", {"name": "Cầu đường 13 Nam", "item_key": "x_toll"})
        moi = max(GLS)
        dung(s == 200 and r["obj_id"] == moi and r["code"].startswith("EPLNCC-") and GLS[moi]["IsOrganization"] is True
             and "GLS" not in GLS[moi]["Description"] and r["item_key"] == "x_toll", "thêm NCC → tạo trong danh mục chung (EPLNCC-…, tổ chức)", r)
        s, r = goi("ketoan", "POST", "/api/owners", {"name": "ທ້າວ ສົມສັກ", "phone": "020 1111 2222", "fee_pct": 2.5})
        moi = max(GLS)
        dung(s == 200 and r["obj_id"] == moi and r["code"].startswith("EPLCX-") and GLS[moi]["IsOrganization"] is False
             and r["fee_pct"] == 2.5, "thêm chủ xe → tạo trong danh mục chung (EPLCX-…, cá nhân), phí 2,5 %", r)
        s, r = goi("ketoancp", "POST", "/api/suppliers", {"name": "Trùng", "code": "NCC-LOP-01"})
        dung(s == 409 and ma(r) == "MA_DA_CO_BEN_GLS", "mã đã có trong danh mục → 409", r)
        s, r = goi("ketoancp", "PUT", "/api/suppliers/" + lop, {"name": "Đổi tên ở đây"})
        dung(s == 409 and ma(r) == "SUA_O_GLS" and "GLS" not in r["detail"]["loi"], "NCC đã gắn đổi tên → 409, sửa ở danh mục chung", r)
        s, r = goi("ketoancp", "PUT", "/api/suppliers/" + lop, {"name": "Lốp Đức Thành", "payment_term": "t_prepaid", "note": "n"})
        dung(s == 200 and r["payment_term"] == "t_prepaid" and r["name"] == "Lốp Đức Thành", "gửi lại đúng tên + đổi kỳ trả → 200", r)
        s, r = goi("ketoan", "PUT", "/api/owners/" + boun, {"phone": "999"})
        dung(s == 409 and ma(r) == "SUA_O_GLS", "chủ xe đã gắn đổi điện thoại → 409", r)
        s, r = goi("ketoan", "PUT", "/api/owners/" + boun, {"over_limit_t": 42})
        dung(s == 200 and r["over_limit_t"] == 42, "chủ xe: đổi ngưỡng quá tải (phần riêng) → 200", r)

        print("== 4. chứng từ kế toán dùng thẳng obj_id; tài xế giữ đường cũ")
        n = len(GOI)
        dung(CHI.doi_tuong(db, "ncc", lop, "x") == 1800 and CHI.doi_tuong(db, "chu_xe", boun, "x") == 1801 and len(GOI) == n,
             "doi_tuong(ncc / chu_xe) có obj_id → trả thẳng, không gọi danh mục chung")
        ncc_moi = db.query(M.Supplier).filter(M.Supplier.obj_id.is_(None), M.Supplier.id != lop).first()
        r_ = M.DoiTuongTune(loai="ncc", ref_id=ncc_moi.id, obj_id=1700, object_no="EPLNCC-" + ncc_moi.id)
        db.merge(r_); db.flush()
        dung(CHI.doi_tuong(db, "ncc", ncc_moi.id, ncc_moi.name) == 1700 and ncc_moi.obj_id == 1700,
             "NCC chưa gắn mà có bảng nhớ → ghi luôn obj_id lên hồ sơ", ncc_moi.obj_id)
        tx = db.query(M.Driver).first()
        if tx is not None and db.get(M.DoiTuongTune, ("tai_xe", tx.id)) is not None:
            dung(CHI.doi_tuong(db, "tai_xe", tx.id, tx.name) == db.get(M.DoiTuongTune, ("tai_xe", tx.id)).obj_id, "tài xế: bảng nhớ cũ (EPLTX-)")

        print("== 5. chép lại thông tin chung + tên chủ xe trên danh mục xe")
        db.flush()
        xe = db.query(M.Vehicle).filter(M.Vehicle.owner_id == "0a073ea75bb3").first()
        GLS[1606]["Name"] = "ທ້າວ ຄຳຫລ້າ (đổi tên)"
        GLS[1800] = {"ObjId": None}                                           # NCC bị xoá khỏi danh mục chung
        s, r = goi("ketoan", "POST", "/api/owners/dong-bo-gls")
        dung(s == 200 and r["cap_nhat"] >= 1, "chủ xe: chép lại → có đổi", r)
        db.expire_all()
        dung(db.get(M.Owner, "0a073ea75bb3").name == "ທ້າວ ຄຳຫລ້າ (đổi tên)"
             and (xe is None or db.get(M.Vehicle, xe.id).owner_name == "ທ້າວ ຄຳຫລ້າ (đổi tên)"), "tên chủ xe mới chép cả sang danh mục xe",
             xe and db.get(M.Vehicle, xe.id).owner_name)
        s, r = goi("ketoancp", "POST", "/api/suppliers/dong-bo-gls")
        dung(s == 200 and 1800 in [m["obj_id"] for m in r["mat"]], "NCC không còn trong danh mục → ghi vào mat", r)
        names = [t for t, _ in DBN._viec()]
        dung("ncc_gls" in names, "luồng nền có bước ncc_gls khi EPL_NCC_GLS=1", names)
        db.query(M.Supplier).filter(M.Supplier.obj_id.isnot(None)).update({M.Supplier.gls_synced_at: None})
        db.flush()
        ket = {"da_hoi": {}, "cap_nhat": {}, "loi": None, "loi_ban_ghi": []}
        DBN._ncc_gls(db, 50, ket, "ncc_gls")
        dung(ket["da_hoi"].get("ncc_gls", 0) >= 1, "bước nền ncc_gls hỏi các hồ sơ chép quá 60 phút", ket)
        os.environ["EPL_NCC_GLS"] = "0"
        dung("ncc_gls" not in [t for t, _ in DBN._viec()], "EPL_NCC_GLS=0 → không có bước ncc_gls")

        print("== 6. luật cũ (cờ tắt)")
        s, r = goi("ketoancp", "POST", "/api/suppliers", {"name": "NCC riêng bên em"})
        dung(s == 200 and r["obj_id"] is None, "cờ tắt, không obj_id → NCC riêng như cũ", r)
        s, r = goi("ketoancp", "PUT", "/api/suppliers/" + lop, {"name": "Đổi được khi cờ tắt"})
        dung(s == 200 and r["name"] == "Đổi được khi cờ tắt", "cờ tắt → sửa tên như cũ", r)
        # GET /api/suppliers đi qua bộ đệm báo cáo (kết nối riêng — bài này giữ một kết nối ROLLBACK) → kiểm thẳng hàm xuất của danh sách
        from routes import nha_cung_cap as NCC
        x = NCC._xuat(db, db.get(M.Supplier, lop), {"so_dong": 0, "phat_sinh": 0, "ghi_no": 0})
        dung(all(k in x for k in ("obj_id", "code", "phone", "address", "gls_synced_at")), "dòng danh sách NCC có obj_id · code · phone · address", x)
        dung(not LA, "không gọi đường danh mục chung nào ngoài list · detail · upsert nhà cung cấp", LA)
    finally:
        CHI._goi = goc_goi
        os.environ["EPL_NCC_GLS"] = "0"
        app.dependency_overrides.clear()
        db.close()
        ngoai.rollback()
        conn.close()
    print("\n%d/%d đúng" % (sum(KQ), len(KQ)))
    sys.exit(0 if all(KQ) else 1)


if __name__ == "__main__":
    main()
