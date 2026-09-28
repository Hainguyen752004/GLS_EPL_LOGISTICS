# -*- coding: utf-8 -*-
"""Bán hàng — EPL bán phụ tùng và xăng dầu cho bên ngoài (không phải chi cho chuyến).

Một phiếu bán = xuất kho + hoá đơn + (sau đó) thu tiền. Đúng câu anh dặn: có trong kho thì xuất kho.
Mỗi bước để lại một tờ trong Sổ chứng từ để bên kế toán kéo về:
    lập phiếu  → PXK_BAN (xuất kho bán, giá vốn / 371) + HD_BAN (1211 / 70)
    thu tiền   → PT_BAN  (tiền mặt / 1211)
Tồn phụ tùng trừ ngay lúc lập; dầu ghi một dòng xuất trong sổ kho nhiên liệu.
Chưa thu mà bỏ phiếu thì trả hàng về kho và rút tờ chứng từ chưa đối chiếu.
"""
import datetime as dt

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import Customer, ExchangeRate, FuelPlace, Owner, Part, Sale, SaleLine
from services import kho_ke_toan as KK
from services import chung_tu as CT
from services import gia_von as GV
from services.bao_mat import can_vai, nguoi_hien_tai

router = APIRouter()
LAP = ("acct", "rev", "fuel")                 # ai lập phiếu bán
THU = ("rev", "cash", "treasury")             # ai ghi thu tiền
TIEN_TE = ("LAK", "USD", "THB", "VND")


def _so(v, ten, bat_buoc=False):
    if v in (None, ""):
        if bat_buoc:
            raise HTTPException(422, {"ma": "THIEU_SO", "loi": "Thiếu %s." % ten})
        return None
    try:
        return float(str(v).replace(",", ""))
    except ValueError:
        raise HTTPException(422, {"ma": "SO_SAI", "loi": "%s phải là số." % ten})


def _ngay(v):
    if not v:
        return dt.date.today()
    try:
        return dt.date.fromisoformat(str(v)[:10])
    except ValueError:
        raise HTTPException(422, {"ma": "NGAY_SAI", "loi": "Ngày phải dạng YYYY-MM-DD."})


def _so_phieu_moi(db, ngay):
    """BH-YYMM-0001 — lấy SỐ LỚN NHẤT đang có rồi cộng một.

    Không đếm số dòng: bỏ một phiếu chưa thu là số tụt lại, phiếu sau ra trùng số phiếu cũ và
    máy chủ báo lỗi. (Cùng một lỗi với số chứng từ, đã sửa trong services/chung_tu.py.)
    """
    tien_to = "BH-%s-" % ngay.strftime("%y%m")
    cuoi = (db.query(Sale.doc_no).filter(Sale.doc_no.like(tien_to + "%"))
            .order_by(Sale.doc_no.desc()).first())        # 4 chữ số có đệm 0 nên xếp chữ = xếp số
    n = 0
    if cuoi:
        try:
            n = int(str(cuoi[0]).rsplit("-", 1)[-1])
        except ValueError:
            n = 0
    return "%s%04d" % (tien_to, n + 1)


def _ty_gia(db, ma):
    if ma == "LAK":
        return 1.0
    r = db.get(ExchangeRate, ma)
    return r.rate_to_lak if r else {"USD": 22000, "THB": 700, "VND": 1.2}[ma]


def xuat(db, s):
    dong = db.query(SaleLine).filter(SaleLine.sale_id == s.id).order_by(SaleLine.line_no).all()
    return {"id": s.id, "doc_no": s.doc_no, "sale_date": s.sale_date.isoformat() if s.sale_date else None,
            "customer_id": s.customer_id, "customer_name": s.customer_name, "currency": s.currency,
            "owner_id": s.owner_id, "owner_payment_id": s.owner_payment_id,
            "rate_to_lak": s.rate_to_lak, "status": s.status, "total": s.total, "total_lak": s.total_lak,
            "cost_lak": s.cost_lak, "note": s.note, "by_user": s.by_user,
            "created_at": s.created_at.isoformat() if s.created_at else None,
            "paid_at": s.paid_at.isoformat() if s.paid_at else None, "paid_by": s.paid_by,
            "lines": [{"id": d.id, "line_no": d.line_no, "item_type": d.item_type, "part_id": d.part_id, "place_id": d.place_id,
                       "name": d.name, "unit": d.unit, "qty": d.qty, "unit_price": d.unit_price, "amount": d.amount,
                       "cost_lak": d.cost_lak, "stock_move_id": d.stock_move_id} for d in dong]}


@router.get("/api/ban-hang")
def ds_ban_hang(thang: str = "", db: Session = Depends(get_db), user=Depends(can_vai(*(LAP + THU)))):
    q = db.query(Sale)
    if thang:
        try:
            y, m = (int(x) for x in thang.split("-")[:2])
        except ValueError:
            raise HTTPException(422, {"ma": "THANG_SAI", "loi": "Tháng phải dạng YYYY-MM."})
        dau = dt.date(y, m, 1)
        cuoi = dt.date(y + (m == 12), (m % 12) + 1, 1)
        q = q.filter(Sale.sale_date >= dau, Sale.sale_date < cuoi)
    ds = [xuat(db, s) for s in q.order_by(Sale.sale_date.desc(), Sale.doc_no.desc()).all()]
    return {"ds": ds, "tong_lak": round(sum(s["total_lak"] or 0 for s in ds)),
            "chua_thu_lak": round(sum(s["total_lak"] or 0 for s in ds if s["status"] == "issued" and not s["owner_id"])),
            "cho_tru_chu_xe_lak": round(sum(s["total_lak"] or 0 for s in ds if s["status"] == "issued" and s["owner_id"]))}


@router.get("/api/ban-hang/{sid}")
def mot_phieu_ban(sid: str, db: Session = Depends(get_db), user=Depends(can_vai(*(LAP + THU)))):
    s = db.get(Sale, sid)
    if not s:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có phiếu bán này."})
    return xuat(db, s)


@router.post("/api/ban-hang")
def lap_phieu_ban(d: dict = Body(...), db: Session = Depends(get_db), user=Depends(can_vai(*LAP))):
    ngay = _ngay(d.get("sale_date"))
    tien_te = str(d.get("currency") or "LAK").upper()
    if tien_te not in TIEN_TE:
        raise HTTPException(422, {"ma": "TIEN_TE_SAI", "loi": "Tiền tệ phải là %s." % ", ".join(TIEN_TE)})
    kh = db.get(Customer, d.get("customer_id") or "") if d.get("customer_id") else None
    chu = db.get(Owner, d.get("owner_id") or "") if d.get("owner_id") else None
    if d.get("owner_id") and not chu:
        raise HTTPException(422, {"ma": "CHU_XE_SAI", "loi": "Không có chủ xe này."})
    if chu:
        kh = None                                  # người mua là chủ xe: trừ vào tiền trả, không thành nợ khách
    ten_kh = (chu.name if chu else kh.name if kh else str(d.get("customer_name") or "").strip())
    if not ten_kh:
        raise HTTPException(422, {"ma": "THIEU_KHACH", "loi": "Phải chọn khách hoặc ghi tên người mua."})
    dong_vao = [x for x in (d.get("lines") or []) if x]
    if not dong_vao:
        raise HTTPException(422, {"ma": "KHONG_CO_DONG", "loi": "Phiếu bán phải có ít nhất một dòng."})

    ty_gia = _ty_gia(db, tien_te)
    # phụ tùng xuất ở trang kế toán (28/09): cả lần lập phiếu đi trong GiaoDichKho — dòng nào hỏng thì mọi lần xuất
    # của các dòng trước bên kia được huỷ, hai bên không lệch
    with KK.GiaoDichKho(db, user) as gd:
        s = Sale(doc_no=_so_phieu_moi(db, ngay), sale_date=ngay, customer_id=kh.id if kh else None, customer_name=ten_kh,
                 owner_id=chu.id if chu else None,
                 currency=tien_te, rate_to_lak=ty_gia, status="issued", note=(d.get("note") or None), by_user=user.full_name)
        db.add(s); db.flush()

        tong = 0.0; von = 0.0; chi_tiet = []
        for i, x in enumerate(dong_vao, 1):
            loai = x.get("item_type")
            qty = _so(x.get("qty"), "số lượng", bat_buoc=True)
            gia = _so(x.get("unit_price"), "đơn giá", bat_buoc=True)
            if qty <= 0 or gia < 0:
                raise HTTPException(422, {"ma": "SO_SAI", "loi": "Dòng %d: số lượng phải > 0, đơn giá không âm." % i})
            dong = SaleLine(sale_id=s.id, line_no=i, item_type=loai, qty=qty, unit_price=gia, amount=round(qty * gia, 2))
            if loai == "part":
                pt = db.get(Part, x.get("part_id") or "")            # bản chép danh mục — tồn, giá ở trang kế toán
                if not pt:
                    raise HTTPException(422, {"ma": "THIEU_PHU_TUNG", "loi": "Dòng %d: phải chọn phụ tùng." % i})
                db.add(dong); db.flush()
                # trang kế toán kiểm tồn (không đủ → 409), trừ tồn, ghi sổ kho theo GIÁ BÌNH QUÂN; không sinh PXK_PT —
                # phiếu bán có tờ xuất kho bán (PXK_BAN) riêng, giá vốn lấy đúng giá bình quân bên đó trả về
                r = gd.xuat_phu_tung(khoa="sale_line:" + dong.id, part_id=pt.id, qty=qty, ngay=ngay, ghi_chung_tu=False,
                                     note="Bán · %s · %s" % (s.doc_no, ten_kh))
                dong.part_id, dong.name, dong.unit, dong.stock_move_id = pt.id, pt.name, pt.unit, r["move_id"]
                dong.cost_lak = round(qty * (r["unit_price"] or 0))
            elif loai == "fuel":
                diem = db.get(FuelPlace, x.get("place_id") or "") if x.get("place_id") else None
                if diem and diem.owner_type != "epl":
                    raise HTTPException(422, {"ma": "KHONG_PHAI_KHO", "loi": "Dòng %d: chỉ bán dầu từ kho của EPL." % i})
                kho = diem.id if diem else GV.kho_goc(db)
                db.add(dong); db.flush()
                # kho nhiên liệu ở trang kế toán (28/09): kiểm tồn (không đủ → 409), xuất theo GIÁ VỐN bình quân của kho —
                # không ghi giá bán; không sinh PXK_NL (phiếu bán có tờ xuất kho bán riêng)
                r = gd.xuat_dau(khoa="sale_line:" + dong.id, place_id=kho, qty_l=qty, ngay=ngay, doc_no=s.doc_no, kiem_ton=True,
                                ghi_chung_tu=False, note="Bán dầu · %s" % ten_kh)
                dong.place_id, dong.name, dong.unit, dong.stock_move_id = kho, "ນໍ້າມັນກາຊວນ (dầu diesel)", "u_l", r["move_id"]
                dong.cost_lak = round(qty * (r["unit_price"] or 0))
            else:
                raise HTTPException(422, {"ma": "LOAI_SAI", "loi": "Dòng %d: loại hàng phải là part hoặc fuel." % i})
            db.add(dong)
            tong += dong.amount; von += dong.cost_lak or 0
            chi_tiet.append({"line_no": i, "item_type": loai, "name": dong.name, "qty": qty, "unit_price": gia, "amount": dong.amount,
                             "part_id": dong.part_id, "place_id": dong.place_id, "cost_lak": dong.cost_lak})
        s.total, s.total_lak, s.cost_lak = round(tong, 2), round(tong * ty_gia), round(von)
        db.flush()
        dt_loai = "chu_xe" if chu else "khach"
        CT.ghi(db, "PXK_BAN", nguon_bang="sales", nguon_id=s.id, ngay=ngay, doi_tuong_loai=dt_loai, doi_tuong_ten=ten_kh,
               tien=s.cost_lak, tien_te="LAK", by_user=user.full_name, mo_ta="Xuất kho bán hàng %s (giá vốn)" % s.doc_no,
               payload={"doc_no": s.doc_no, "lines": chi_tiet})
        CT.ghi(db, "HD_BAN", nguon_bang="sales", nguon_id=s.id, ngay=ngay, doi_tuong_loai=dt_loai, doi_tuong_ten=ten_kh,
               tien=s.total, tien_te=tien_te, tien_lak=s.total_lak, by_user=user.full_name,
               mo_ta="Hoá đơn bán hàng %s · %s%s" % (s.doc_no, ten_kh, " (trừ vào tiền trả chủ xe)" if chu else ""),
               payload={"doc_no": s.doc_no, "rate_to_lak": ty_gia, "lines": chi_tiet, "owner_id": chu.id if chu else None})
    return xuat(db, s)


@router.post("/api/ban-hang/{sid}/thu")
def thu_tien_ban(sid: str, d: dict = Body(default={}), db: Session = Depends(get_db), user=Depends(can_vai(*THU))):
    s = db.get(Sale, sid)
    if not s:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có phiếu bán này."})
    if s.status == "paid":
        raise HTTPException(409, {"ma": "DA_THU", "loi": "Phiếu %s đã thu tiền rồi." % s.doc_no})
    if s.owner_id:
        raise HTTPException(409, {"ma": "TRU_CHU_XE", "loi": "Phiếu %s trừ vào tiền trả chủ xe, không thu tiền mặt." % s.doc_no})
    s.status, s.paid_at, s.paid_by = "paid", dt.datetime.utcnow(), user.full_name
    CT.ghi(db, "PT_BAN", nguon_bang="sales", nguon_id=s.id, ngay=_ngay(d.get("pay_date")), doi_tuong_loai="khach", phuong_thuc="cash",
           doi_tuong_ten=s.customer_name, tien=s.total, tien_te=s.currency, tien_lak=s.total_lak, by_user=user.full_name,
           mo_ta="Thu tiền bán hàng %s · %s" % (s.doc_no, s.customer_name), payload={"doc_no": s.doc_no})
    db.commit()
    return xuat(db, s)


@router.delete("/api/ban-hang/{sid}")
def bo_phieu_ban(sid: str, db: Session = Depends(get_db), user=Depends(can_vai(*LAP))):
    """Bỏ phiếu chưa thu: hàng về kho, tờ chứng từ chưa đối chiếu rút theo."""
    s = db.get(Sale, sid)
    if not s:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có phiếu bán này."})
    if s.status == "paid":
        raise HTTPException(409, {"ma": "DA_THU", "loi": "Đã thu tiền thì không bỏ phiếu được."})
    if s.owner_payment_id:
        raise HTTPException(409, {"ma": "DA_TRU", "loi": "Phiếu đã trừ vào một đợt trả chủ xe, không bỏ được."})
    for dong in db.query(SaleLine).filter(SaleLine.sale_id == s.id).all():
        if dong.item_type == "part" and dong.stock_move_id:
            # phụ tùng về kho bên trang kế toán (trả tồn, xoá dòng sổ); trang kế toán tắt thì chưa bỏ phiếu được
            KK.huy_xuat(db, user, move_id=dong.stock_move_id)
        elif dong.item_type == "fuel" and dong.stock_move_id:
            KK.huy_xuat_dau(db, user, move_id=dong.stock_move_id)      # dầu về kho bên trang kế toán
        db.delete(dong)
    CT.rut(db, nguon_bang="sales", nguon_id=s.id)
    db.delete(s); db.commit()
    return {"ok": True}
