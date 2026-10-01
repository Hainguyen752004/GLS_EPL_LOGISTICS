# -*- coding: utf-8 -*-
"""KHO — CHỈ XEM, theo MẶT HÀNG (sếp 30/09: kho dời về trang logistics, bên mình chỉ xem; thao tác kho do anh Toàn).

Mỗi mặt hàng một dòng: tồn, đang chờ xuất theo phiếu đề nghị, đã khai trên phiếu mà chưa có đề nghị, nhập / xuất trong
tháng, các lần xuất nhập gần nhất. Số tồn, giá, sổ nhập xuất hỏi bên kho (bây giờ là trang kế toán tạm, sau là API của
anh Toàn — đổi ở `services/kho_ke_toan.py`); phần "chờ xuất" là của bên này: phiếu đề nghị xuất kho nhiên liệu chưa cấp và
dòng kho trên phiếu xuất xe chưa rời kho.

    GET /api/kho-xem?thang=YYYY-MM

Bãi, thủ kho, thủ kho phụ tùng, tổ sửa chữa không thấy giá (giá bình quân, giá từng lần — `thay_gia_kho`, chốt 30/09).
Tài xế không vào màn này.
"""
import re
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import FuelPlace, Part, Trip, TripExpense, Voucher
from services import goi_ke_toan as KT
from services.bao_mat import nguoi_hien_tai
from services.gia_von import kho_goc
from services.phan_quyen import thay_gia_kho

router = APIRouter()

# Chữ trong tên khoá cho biết khoá mang TIỀN (giá bình quân, giá từng lần, giá trị tồn, đơn giá, quy Kíp…).
CHU_TIEN = {"gia", "tien", "price", "cost", "amount", "value", "von", "lak", "usd", "thb", "vnd", "cny"}


def _chu(khoa):
    """Tách tên khoá thành chữ: `gia_bq` → {gia, bq}; `unitPrice` → {unit, price}."""
    return set(re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", str(khoa)).lower().replace("-", "_").split("_"))


def go_gia(o):
    """Gỡ MỌI khoá tiền ở MỌI tầng (dict / list lồng nhau) cho vai không thấy giá vốn kho — trả chính đối tượng đó.

    Gỡ theo chữ trong tên khoá chứ không theo danh sách trường cố định: 30/09 kho tạm thêm khối `so_thang` (sổ tháng,
    mỗi dòng có `gia`) mà màn này chỉ gỡ giá ở `gan_day` → Bãi, thủ kho, tổ sửa chữa thấy giá vốn. Bên kho thêm khối mới
    nào nữa thì giá trong đó cũng bị gỡ ở đây."""
    if isinstance(o, dict):
        for k in [k for k in o if _chu(k) & CHU_TIEN]:
            del o[k]
        for v in o.values():
            go_gia(v)
    elif isinstance(o, list):
        for v in o:
            go_gia(v)
    return o


def _tuyen(p):
    return " → ".join(x for x in (p.origin, p.destination) if x) or None


def _cho_xuat_dau(db):
    """{place_id: {"de_nghi": [...phiếu đề nghị chờ cấp], "chua_de_nghi": [...dòng kho chưa có phiếu đề nghị]}}."""
    goc = kho_goc(db)
    ra = defaultdict(lambda: {"de_nghi": [], "chua_de_nghi": []})
    co_phieu = set()
    vs = db.query(Voucher, Trip).join(Trip, Trip.id == Voucher.trip_id).filter(Voucher.kind == "fuel", Voucher.status != "huy").all()
    for v, p in vs:
        co_phieu.add((v.trip_id, v.place_id or goc))
        if v.status == "cho":
            ra[v.place_id or goc]["de_nghi"].append({
                "voucher_no": v.doc_no, "trip_id": p.id, "doc_no": p.doc_no, "kind": p.kind, "company": p.company,
                "truck_no": v.truck_no or p.truck_no, "driver_name": v.driver_name or p.driver_name, "qty_l": v.qty_l or 0,
                "route": _tuyen(p), "ngay": v.doc_date.isoformat() if v.doc_date else None})
    dong = (db.query(TripExpense, Trip).join(Trip, Trip.id == TripExpense.trip_id)
            .filter(TripExpense.section == "fuel", TripExpense.source == "kho", TripExpense.paid_by_epl.is_(True),
                    TripExpense.stock_move_id.is_(None)).all())
    gop = {}
    for d, p in dong:
        ma = d.place_id or goc
        if (p.id, ma) in co_phieu:
            continue
        x = gop.setdefault((p.id, ma), {"trip_id": p.id, "doc_no": p.doc_no, "kind": p.kind, "company": p.company,
                                        "truck_no": p.truck_no, "driver_name": p.driver_name, "qty_l": 0.0, "route": _tuyen(p),
                                        "ngay": p.doc_date.isoformat() if p.doc_date else None})
        x["qty_l"] += d.qty or 0
    for (_, ma), x in gop.items():
        ra[ma]["chua_de_nghi"].append(x)
    for o in ra.values():
        for k in o:
            o[k].sort(key=lambda x: (x["ngay"] or "", x["doc_no"] or ""))
    return ra


def _cho_xuat_phu_tung(db):
    """{part_id: [...dòng phụ tùng lấy kho trên phiếu (mục V) chưa rời kho]}."""
    ra = defaultdict(list)
    q = (db.query(TripExpense, Trip).join(Trip, Trip.id == TripExpense.trip_id)
         .filter(TripExpense.section == "repair", TripExpense.source == "kho", TripExpense.part_id.isnot(None),
                 TripExpense.stock_move_id.is_(None)))
    for d, p in q.all():
        ra[d.part_id].append({"trip_id": p.id, "doc_no": p.doc_no, "truck_no": p.truck_no, "qty": d.qty or 0,
                              "ngay": p.doc_date.isoformat() if p.doc_date else None})
    return ra


@router.get("/api/kho-xem")
def kho_xem(thang: str = "", db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    if user.role == "driver":
        raise HTTPException(403, {"ma": "KHONG_CO_QUYEN", "loi": "Tài xế không xem kho."})
    kho = KT.goi(db, "GET", "/api/lien-thong/kho/mat-hang" + ("?thang=" + thang if thang else ""), nguoi=user) or {}
    gia = thay_gia_kho(user.role)          # thủ kho, thủ kho phụ tùng, tổ sửa chữa, Bãi: không giá vốn (30/09)

    cho = _cho_xuat_dau(db)
    ten_diem = {k.id: k for k in db.query(FuelPlace).all()}
    dau = []
    for k in kho.get("nhien_lieu", []):
        c = cho.pop(k["place_id"], {"de_nghi": [], "chua_de_nghi": []})
        k["de_nghi"], k["chua_de_nghi"] = c["de_nghi"], c["chua_de_nghi"]
        k["cho_xuat"] = round(sum(x["qty_l"] for x in c["de_nghi"]), 2)
        k["chua_de_nghi_l"] = round(sum(x["qty_l"] for x in c["chua_de_nghi"]), 2)
        k["con_dung"] = round((k.get("ton_lit") or 0) - k["cho_xuat"] - k["chua_de_nghi_l"], 2)
        dau.append(k)
    for ma, c in cho.items():          # kho bên này có phiếu chờ mà bên kho không trả về (kho đã tắt?) — vẫn hiện, không giấu
        diem = ten_diem.get(ma)
        dau.append({"place_id": ma, "code": diem.code if diem else None, "name": diem.name if diem else ma,
                    "country": diem.country if diem else None, "active": False, "ton_lit": None, "gia_bq": None,
                    "nhap_thang": 0, "xuat_thang": 0, "gan_day": [], "de_nghi": c["de_nghi"], "chua_de_nghi": c["chua_de_nghi"],
                    "cho_xuat": round(sum(x["qty_l"] for x in c["de_nghi"]), 2),
                    "chua_de_nghi_l": round(sum(x["qty_l"] for x in c["chua_de_nghi"]), 2), "con_dung": None})

    cho_pt = _cho_xuat_phu_tung(db)
    ten_pt = {p.id: p for p in db.query(Part).all()}
    pt = []
    for p in kho.get("phu_tung", []):
        p["tren_phieu"] = cho_pt.pop(p["id"], [])
        p["cho_xuat"] = round(sum(x["qty"] for x in p["tren_phieu"]), 3)
        p["con_dung"] = round((p.get("ton") or 0) - p["cho_xuat"], 3)
        p["duoi_muc"] = (p.get("min_qty") or 0) > 0 and (p.get("ton") or 0) <= (p.get("min_qty") or 0)
        pt.append(p)
    for pid, ds in cho_pt.items():
        x = ten_pt.get(pid)
        pt.append({"id": pid, "name": x.name if x else pid, "unit": x.unit if x else None, "active": False, "ton": None,
                   "min_qty": x.min_qty if x else 0, "gia_bq": None, "nhap_thang": 0, "xuat_thang": 0, "gan_day": [],
                   "tren_phieu": ds, "cho_xuat": round(sum(d["qty"] for d in ds), 3), "con_dung": None, "duoi_muc": False})

    if user.role == "depot":
        # thủ kho một kho (như Cấp phát): tab Nhiên liệu chỉ kho mình phụ trách; chưa gắn kho thì không thấy kho nào
        dau = [k for k in dau if user.place_id and k["place_id"] == user.place_id]
    ra = {"thang": kho.get("thang"), "nguon": "ke_toan_tam", "nhien_lieu": dau, "phu_tung": pt, "hang": kho.get("hang", [])}
    if not gia:
        go_gia(ra)
    ra["thay_gia"] = gia
    return ra
