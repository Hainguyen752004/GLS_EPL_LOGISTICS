# -*- coding: utf-8 -*-
"""ĐỐI TƯỢNG DÙNG CHUNG với danh mục Đối tượng GLS (Việc 9 khách hàng, Việc 10 nhà cung cấp · chủ xe liên kết — 08/10/2026).

Khách, nhà cung cấp, chủ xe của vận tải là đối tượng trong danh mục Đối tượng GLS (PUBOBJECT — Web: /ObjManagement/…). Mỗi dòng
`customers` · `suppliers` · `owners` bên em là HỒ SƠ VẬN TẢI của một đối tượng (`obj_id` = OBJ_AUTOID): giữ phần chỉ vận tải có
(khách: cách xuất hoá đơn, bảng giá, hợp đồng · nhà cung cấp: khoản mục chi, mã kế toán, kỳ trả, khách cấn trừ · chủ xe: phí, ngưỡng
quá tải, cách trả, hợp đồng thuê xe); tên · điện thoại · địa chỉ · mã (OBJ_OBJECTNO) là BẢN CHÉP từ danh mục chung — sửa ở màn Đối
tượng, bên em chép về (lúc gắn, nút cập nhật, luồng nền dong_bo_nen). Chứng từ gửi kế toán dùng thẳng `obj_id` (chi_tune.doi_tuong).
Tài xế (EPLTX-) KHÔNG đi đường này — giữ như cũ (chi_tune.doi_tuong_tai_xe).

Đường danh mục chung (API anh Khang, cùng gốc / token với chi_tune — đã thử máy 5090, DB demo, 08/10):
    POST /api/v1/master-data/{customers|suppliers}/list    {PageIndex, ObjKey}   ObjKey khớp một phần TÊN hoặc đúng cả MÃ; 100 dòng / trang
    POST /api/v1/master-data/{customers|suppliers}/detail  {ObjId, OrgId, LangId} → Detail; không có → ObjId null
    POST /api/v1/master-data/{customers|suppliers}/upsert  (thân như chi_tune.doi_tuong) → OBJ_AUTOID
Nhà cung cấp và chủ xe cùng nằm trong nhóm suppliers bên đó (như chi_tune.LOAI_DOI_TUONG).

Cờ (.env): EPL_KHACH_GLS (khách) · EPL_NCC_GLS (nhà cung cấp + chủ xe) — 1 = thêm mới là chọn / tạo đối tượng trong danh mục
chung, thông tin chung của hồ sơ đã gắn chỉ sửa ở danh mục chung, luồng nền chép lại. EPL_GLS_KHACH_GIAY: nhớ kết quả tìm (giây).
Câu báo lỗi người dùng thấy KHÔNG nhắc "GLS" (với khách cả hệ thống là EPL).
"""
import datetime as dt
import os
import threading
import time

from fastapi import HTTPException
from sqlalchemy import func, or_

from models import Customer, DoiTuongTune, Owner, Supplier, Vehicle, ma_moi
from services import chi_tune as CHI

O_CHUNG = ("name", "phone", "address", "code")      # ô thông tin chung — chép từ danh mục chung

LOAI = {
    "khach": {"bang": Customer, "duong": "customers", "tien_to": "EPLKH-", "goi": "khách", "danh_muc": "danh mục khách hàng",
              "co": "EPL_KHACH_GLS", "mo_ta": "Khách hàng — module Vận tải EPL", "to_chuc": None,
              "ma_khong_co": "KHACH_GLS_KHONG_CO", "ma_trung": "MA_KHACH_TRUNG"},
    "ncc": {"bang": Supplier, "duong": "suppliers", "tien_to": "EPLNCC-", "goi": "nhà cung cấp", "danh_muc": "danh mục nhà cung cấp",
            "co": "EPL_NCC_GLS", "mo_ta": "Nhà cung cấp — module Vận tải EPL", "to_chuc": True,
            "ma_khong_co": "DOI_TUONG_KHONG_CO", "ma_trung": "MA_TRUNG"},
    "chu_xe": {"bang": Owner, "duong": "suppliers", "tien_to": "EPLCX-", "goi": "chủ xe", "danh_muc": "danh mục nhà cung cấp",
               "co": "EPL_NCC_GLS", "mo_ta": "Chủ xe liên kết — module Vận tải EPL", "to_chuc": False,
               "ma_khong_co": "DOI_TUONG_KHONG_CO", "ma_trung": "MA_TRUNG"},
}

_NHO = {}
_KHOA = threading.Lock()


def duong(loai, viec):
    """viec: list · detail · upsert."""
    return "/api/v1/master-data/%s/%s" % (LOAI[loai]["duong"], viec)


def bat(loai):
    return (os.getenv(LOAI[loai]["co"]) or "0").strip() == "1"


def _giay():
    v = (os.getenv("EPL_GLS_KHACH_GIAY") or "").strip()
    return int(v) if v.isdigit() else 300


def _loi(ma, loi, http=422):
    raise HTTPException(http, {"ma": ma, "loi": loi})


def quen():
    """Bỏ kết quả tìm đã nhớ — sau khi tạo đối tượng mới."""
    with _KHOA:
        _NHO.clear()


def _dong(x):
    """Một dòng list / Detail của danh mục chung → dạng gọn (tên khoá như cột bên em). `is_org` None khi không trả."""
    return {"obj_id": int(x["ObjId"]), "code": (x.get("ObjectNo") or "").strip() or None, "name": (x.get("Name") or "").strip(),
            "phone": (x.get("Phone") or "").strip() or None, "address": (x.get("Address") or "").strip() or None,
            "tax_id": (x.get("TaxID") or "").strip() or None, "active": x.get("IsActive") is not False,
            "is_org": x.get("IsOrganization")}


def tim(loai, q="", trang=1, nho=True):
    """Tìm trong danh mục chung của loại. → {"items": [dòng gọn], "page", "pages", "total"}."""
    q = (q or "").strip()[:100]
    trang = max(1, int(trang or 1))
    khoa, bay_gio = (LOAI[loai]["duong"], q.lower(), trang), time.time()
    if nho:
        with _KHOA:
            v = _NHO.get(khoa)
            if v and bay_gio - v[0] < _giay():
                return v[1]
    r = CHI._goi("POST", duong(loai, "list"), {"PageIndex": trang, "ObjKey": q}) or {}
    pg = r.get("Pagination") or {}
    kq = {"items": [_dong(x) for x in (r.get("Data") or []) if x.get("ObjId")], "page": trang,
          "pages": int(pg.get("TotalPages") or 0), "total": int(pg.get("TotalRecords") or 0)}
    with _KHOA:
        _NHO[khoa] = (bay_gio, kq)
    return kq


def mot(loai, obj_id):
    """Thông tin chung của một đối tượng (luôn đọc mới). Không có → None."""
    r = CHI._goi("POST", duong(loai, "detail"), {"ObjId": int(obj_id), "OrgId": CHI._cfg("QLSX_ORG_ID", 1368), "LangId": 1}) or {}
    d = r.get("Detail") or {}
    return _dong(d) if d.get("ObjId") else None


def _chep(loai, k, g):
    """Chép thông tin chung vào hồ sơ vận tải. → (có ô đổi, tên cũ) — tên cũ để _theo_ten_chu_xe sửa tên chủ xe trên danh mục xe."""
    # danh mục chung để trống điện thoại / địa chỉ thì GIỮ số đang có (08/10: gắn chủ xe làm mất "020 5555 7777" vì bên đó trống)
    moi = {"name": g["name"] or k.name or g["code"], "phone": g["phone"] or getattr(k, "phone", None),
           "address": g["address"] or getattr(k, "address", None), "code": g["code"] or k.code}
    doi = any(getattr(k, o) != v for o, v in moi.items())
    ten_cu = k.name
    for o, v in moi.items():
        setattr(k, o, v)
    k.gls_synced_at = dt.datetime.utcnow()
    return doi, ten_cu


def _nho_doi_tuong(db, loai, k):
    """Bảng nhớ đối tượng bên kế toán (doi_tuong_tune) theo đúng obj_id — đường cũ đọc bảng đó vẫn khớp."""
    r = db.get(DoiTuongTune, (loai, k.id))
    if r is None:
        db.add(DoiTuongTune(loai=loai, ref_id=k.id, obj_id=int(k.obj_id), object_no=k.code or (LOAI[loai]["tien_to"] + k.id)))
    elif r.obj_id != k.obj_id or r.object_no != k.code:
        r.obj_id, r.object_no = int(k.obj_id), k.code or r.object_no


def _theo_ten_chu_xe(db, loai, k, ten_cu):
    if loai == "chu_xe" and ten_cu is not None and ten_cu != k.name:
        for v in db.query(Vehicle).filter(Vehicle.owner_id == k.id).all():
            v.owner_name = k.name


def lien_ket(db, loai, obj_id):
    """Hồ sơ vận tải của đối tượng `obj_id`: đã có thì chép lại thông tin chung; hồ sơ cũ bên em từng gửi chứng từ với đối tượng
    này, hoặc cùng mã (chưa gắn) thì nhận làm hồ sơ của nó; không thì tạo hồ sơ mới. → (bản ghi, mới_tạo) — chưa commit."""
    c = LOAI[loai]
    bang = c["bang"]
    g = mot(loai, obj_id)
    if g is None:
        _loi(c["ma_khong_co"], "Không tìm thấy %s này trong %s." % (c["goi"], c["danh_muc"]), 404)
    k = db.query(bang).filter(bang.obj_id == g["obj_id"]).first()
    moi = False
    if k is None:
        r = db.query(DoiTuongTune).filter(DoiTuongTune.loai == loai, DoiTuongTune.obj_id == g["obj_id"]).first()
        x = db.get(bang, r.ref_id) if r is not None else None
        k = x if x is not None and not x.obj_id else None
    if k is None and g["code"]:
        cung_ma = db.query(bang).filter(func.lower(bang.code) == g["code"].lower()).all()
        if [x for x in cung_ma if x.obj_id and x.obj_id != g["obj_id"]]:
            _loi(c["ma_trung"], "Mã %s %s đã dùng cho %s khác." % (c["goi"], g["code"], c["goi"]), 409)
        k = next((x for x in cung_ma if not x.obj_id), None)
    if k is None:
        moi = True
        k = bang(id=ma_moi(), active=True)
        if loai == "khach":
            k.invoice_mode = "phieu"
            k.cust_type = None if g["is_org"] is None else ("company" if g["is_org"] else "person")
        elif loai == "ncc":
            k.payment_term = "t_monthly"
        db.add(k)
    k.obj_id = g["obj_id"]
    _, ten_cu = _chep(loai, k, g)
    db.flush()
    if not moi:
        _theo_ten_chu_xe(db, loai, k, ten_cu)
    _nho_doi_tuong(db, loai, k)
    return k, moi


def tao(loai, data, ma=None):
    """Chưa có trong danh mục chung: tạo đối tượng (master-data/…/upsert). → OBJ_AUTOID. Mã đã có thì chặn — chọn đối tượng đó."""
    c = LOAI[loai]
    ten = str(data.get("name") or "").strip()
    if not ten:
        _loi("THIEU_TEN", "%s phải có tên." % c["goi"].capitalize())
    so = ma or (c["tien_to"] + ma_moi())
    co = next((x for x in tim(loai, so, nho=False)["items"] if (x["code"] or "").lower() == so.lower()), None)
    if co:
        _loi("MA_DA_CO_BEN_GLS", "Mã %s đã có trong %s (%s) — chọn %s đó thay vì tạo mới." % (so, c["danh_muc"], co["name"], c["goi"]), 409)
    than = {"ObjectNo": so, "ObjectName": ten[:100], "CountryAutoId": CHI._cfg("QLSX_COUNTRY_ID", 11),
            "ObjectOfOrganization": CHI._cfg("QLSX_ORG_ID", 1368), "HandPhone": (data.get("phone") or "").strip() or None,
            "Address": (data.get("address") or "").strip() or None, "Description": c["mo_ta"]}
    to_chuc = c["to_chuc"]
    if loai == "khach" and data.get("cust_type") in ("person", "company"):
        to_chuc = data["cust_type"] == "company"
    if to_chuc is not None:
        than["IsOrganization"] = to_chuc
    oid = CHI._goi("POST", duong(loai, "upsert"), than)
    quen()
    if not oid:
        _loi("KHONG_TAO_DUOC_DOI_TUONG", "Không thêm được %s %s vào %s." % (c["goi"], ten, c["danh_muc"]), 502)
    return int(oid)


def dong_bo(db, loai, n=None, cu_hon_phut=None):
    """Chép lại thông tin chung các hồ sơ đã gắn — lâu chưa chép nhất trước, tối đa `n` (None = tất cả); `cu_hon_phut` = chỉ hồ sơ
    chép cách đây hơn ngần ấy phút (luồng nền). Lỗi máy chủ / mạng thì ném lên (người gọi dừng); đối tượng không còn thì ghi vào
    `mat`. → {"da_hoi", "cap_nhat", "mat"}."""
    bang = LOAI[loai]["bang"]
    q = db.query(bang).filter(bang.obj_id.isnot(None))
    if cu_hon_phut:
        moc = dt.datetime.utcnow() - dt.timedelta(minutes=cu_hon_phut)
        q = q.filter(or_(bang.gls_synced_at.is_(None), bang.gls_synced_at < moc))
    q = q.order_by(bang.gls_synced_at.asc().nullsfirst(), bang.name)
    ds = q.limit(n).all() if n else q.all()
    kq = {"da_hoi": 0, "cap_nhat": 0, "mat": []}
    for k in ds:
        g = mot(loai, k.obj_id)
        kq["da_hoi"] += 1
        if g is None:
            k.gls_synced_at = dt.datetime.utcnow()
            kq["mat"].append({"id": k.id, "name": k.name, "obj_id": k.obj_id})
            continue
        doi, ten_cu = _chep(loai, k, g)
        if doi:
            kq["cap_nhat"] += 1
        _theo_ten_chu_xe(db, loai, k, ten_cu)
        _nho_doi_tuong(db, loai, k)
    db.flush()
    return kq


def chan_sua_chung(loai, k, data):
    """Sửa hồ sơ đã gắn khi cờ của loại bật: ô thông tin chung (tên, điện thoại, địa chỉ, mã) đổi giá trị → 409 `SUA_O_GLS`; form
    gửi lại đúng giá trị đang có thì cho qua. → data đã bỏ các ô thông tin chung (hồ sơ chưa gắn / cờ tắt: data nguyên vẹn)."""
    if not (bat(loai) and k.obj_id):
        return data
    c = LOAI[loai]
    doi = [o for o in O_CHUNG if o in data and (str(data[o] or "").strip() or None) != (getattr(k, o) or None)]
    if doi:
        raise HTTPException(409, {"ma": "SUA_O_GLS", "loi": "Tên, điện thoại, địa chỉ, mã %s dùng chung với %s — sửa ở màn thông tin "
                                                             "%s." % (c["goi"], c["danh_muc"], c["goi"]), "o": doi})
    return {x: v for x, v in data.items() if x not in O_CHUNG}


def tim_kem_ho_so(db, loai, kq):
    """Kết quả tìm danh mục chung + id hồ sơ bên em đã gắn từng dòng (`customer_id` · `supplier_id` · `owner_id`). Nhà cung cấp và
    chủ xe cùng nằm trong danh mục nhà cung cấp chung nên dòng nào cũng kèm cả hai id đó."""
    ids = [x["obj_id"] for x in kq["items"]]
    if not ids:
        return kq
    kem = {"khach": ("customer_id",), "ncc": ("supplier_id", "owner_id"), "chu_xe": ("supplier_id", "owner_id")}[loai]
    bang = {"customer_id": Customer, "supplier_id": Supplier, "owner_id": Owner}
    gan = {k: dict(db.query(bang[k].obj_id, bang[k].id).filter(bang[k].obj_id.in_(ids)).all()) for k in kem}
    return {**kq, "items": [{**x, **{k: gan[k].get(x["obj_id"]) for k in kem}} for x in kq["items"]]}
