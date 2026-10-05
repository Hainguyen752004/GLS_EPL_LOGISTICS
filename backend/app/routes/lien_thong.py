# -*- coding: utf-8 -*-
"""LIÊN THÔNG hai trang — trang điều xe (đây) ↔ KHO TẠM (máy EPL_KETOAN; từ 01/10 bên đó bỏ phần tiền, chỉ còn làm kho).

    GET  /api/lien-thong/kiem          kho tạm gọi sang thử khoá: đúng khoá + đúng người thì trả người đó
    GET  /api/lien-thong/thu           Sếp bấm "Kiểm kết nối": gọi sang kho tạm và báo thật kết quả
    POST /api/lien-thong/tao-khoa      Sếp tạo (lại) khoá cho kho tạm gọi sang — chép khoá này vào Cài đặt bên đó
Còn lại là các đường KHO (danh mục điểm đổ, phụ tùng, cấp phát, tỷ giá, mã kế toán, xe, người mua). Phần tiền đã gỡ — cuối tệp.
"""
import secrets
import time

from fastapi import APIRouter, Body, Depends, HTTPException, Request, Response
from sqlalchemy import func
from sqlalchemy.orm import Session

from database import get_db
from models import FuelMove, FuelPlace, Part, SaleLine, Supplier, TripEvent, TripExpense, User, Voucher
from services import day_ke_toan as DK
from services import goi_ke_toan as KT
from services.bao_mat import can_vai, may_ke_toan_goi, nguoi_hien_tai, token_nhan_ke_toan

router = APIRouter()


@router.get("/api/lien-thong/kiem")
def kiem(u=Depends(may_ke_toan_goi)):
    return {"ok": True, "ben": "EPL_LAO_REAL", "nguoi": u.username, "vai": u.role}


@router.get("/api/lien-thong/thu")
def thu(db: Session = Depends(get_db), user=Depends(can_vai("admin"))):
    from services import kho_qlsx as KQ
    if KQ.bat():                         # 05/10: kho ở hệ anh Tune — thử bằng một lần đọc tồn
        t0 = time.time()
        try:
            n = len(KQ.ton(db, hang=(KQ.MA_DAU,)))
            return {"ok": True, "kho": "qlsx", "ms": int((time.time() - t0) * 1000), "so_dong_ton": n}
        except HTTPException as e:
            d = e.detail if isinstance(e.detail, dict) else {"loi": str(e.detail)}
            return {"ok": False, "kho": "qlsx", "ma": d.get("ma"), "loi": d.get("loi")}
    goc, token = KT.cau_hinh(db)
    t0 = time.time()
    ra = {"api": goc, "co_token_nhan": bool(token_nhan_ke_toan(db))}
    try:
        ra.update(ok=True, ms=int((time.time() - t0) * 1000), ben_kia=KT.goi(db, "GET", "/api/lien-thong/kiem", nguoi=user))
    except HTTPException as e:
        d = e.detail if isinstance(e.detail, dict) else {"loi": str(e.detail)}
        ra.update(ok=False, co_token=bool(token), ma=d.get("ma"), loi=d.get("loi"))
    return ra


@router.post("/api/lien-thong/tao-khoa")
def tao_khoa(db: Session = Depends(get_db), user=Depends(can_vai("admin"))):
    """Khoá mới thay khoá cũ ngay — trang kế toán phải dán khoá mới vào Cài đặt thì mới gọi sang được tiếp.
    Trả khoá đúng một lần trong câu trả lời này để Sếp chép; sau đó màn chỉ báo "đã có khoá"."""
    k = secrets.token_urlsafe(32)
    DK.dat_cau_hinh(db, "token_nhan_ke_toan", k, user)
    db.commit()
    return {"token_nhan_ke_toan": k}


# ================================================================ bản chép danh mục kho (28/09)
# Điểm đổ nhiên liệu: bản GỐC ở trang kế toán. Ở đây là bản chép chỉ đọc, cùng mã — phiếu, phiếu lĩnh, tài khoản
# thủ kho vẫn trỏ vào bảng fuel_places như cũ. Chỉ trang kế toán ghi vào đây, qua các đường máy dưới đây.
COT_DIEM = ("code", "name", "country", "owner_type", "supplier_id", "address", "note", "active")


@router.get("/api/lien-thong/diem-do/thong-tin")
def diem_do_thong_tin(db: Session = Depends(get_db), u=Depends(may_ke_toan_goi)):
    """Hai thứ màn Điểm đổ bên kế toán cần mà còn ở đây: danh sách nhà cung cấp (để gắn trạm bán dầu) và số phiếu
    lĩnh đang chờ cấp ở từng điểm."""
    ncc = [{"id": s.id, "name": s.name} for s in db.query(Supplier).order_by(Supplier.name).all()]
    cho = dict(db.query(Voucher.place_id, func.count(Voucher.id))
               .filter(Voucher.status == "cho", Voucher.place_id.isnot(None)).group_by(Voucher.place_id).all())
    return {"nha_cung_cap": ncc, "cho_cap": cho}


@router.put("/api/lien-thong/ban-sao/diem-do/{pid}")
def ghi_ban_sao_diem(pid: str, d: dict = Body(...), db: Session = Depends(get_db), u=Depends(may_ke_toan_goi)):
    if not str(d.get("name") or "").strip():
        raise HTTPException(422, {"ma": "THIEU_TEN", "loi": "Điểm đổ phải có tên."})
    if d.get("owner_type") not in ("epl", "ngoai"):
        raise HTTPException(422, {"ma": "LOAI_SAI", "loi": "Loại điểm đổ không hợp lệ."})
    if d.get("supplier_id") and not db.get(Supplier, d["supplier_id"]):
        raise HTTPException(422, {"ma": "KHONG_THAY_NCC", "loi": "Không có nhà cung cấp này ở trang điều xe."})
    x = db.get(FuelPlace, pid)
    if not x:
        x = FuelPlace(id=pid); db.add(x)
    for c in COT_DIEM:
        if c in d:
            setattr(x, c, d[c] if d[c] != "" else None)
    x.active = bool(x.active)
    db.commit()
    return {"ok": True, "id": pid}


@router.delete("/api/lien-thong/ban-sao/diem-do/{pid}")
def xoa_ban_sao_diem(pid: str, db: Session = Depends(get_db), u=Depends(may_ke_toan_goi)):
    x = db.get(FuelPlace, pid)
    if not x:
        return {"ok": True, "id": pid}          # bên này chưa có thì coi như đã xoá
    dung = [ten for ten, bang, cot in (("phiếu xuất xe", TripExpense, TripExpense.place_id),
                                       ("khai đổ dầu", TripEvent, TripEvent.place_id),
                                       ("phiếu đề nghị xuất kho nhiên liệu", Voucher, Voucher.place_id),
                                       ("sổ kho dầu", FuelMove, FuelMove.place_id),
                                       ("phiếu bán hàng", SaleLine, SaleLine.place_id),
                                       ("tài khoản thủ kho", User, User.place_id))
            if db.query(bang).filter(cot == pid).first()]
    if dung:
        raise HTTPException(409, {"ma": "DANG_DUNG",
                                  "loi": "Điểm đổ đã có trên %s — chỉ được ngưng dùng, không xoá." % ", ".join(dung)})
    db.delete(x); db.commit()
    return {"ok": True, "id": pid}


# Phụ tùng: bản GỐC (tồn, giá, sổ) ở trang kế toán. Ở đây là bản chép DANH MỤC — tên, đơn vị, tồn tối thiểu, đang dùng —
# để dòng chi mục V, dòng lệnh sửa, dòng bán vẫn trỏ đúng. Không nhận tồn, không nhận giá (số đó chỉ bên kia giữ).
@router.put("/api/lien-thong/ban-sao/phu-tung/{pid}")
def ghi_ban_sao_phu_tung(pid: str, d: dict = Body(...), db: Session = Depends(get_db), u=Depends(may_ke_toan_goi)):
    if not str(d.get("name") or "").strip():
        raise HTTPException(422, {"ma": "THIEU_TEN", "loi": "Phụ tùng phải có tên."})
    x = db.get(Part, pid)
    if not x:
        x = Part(id=pid, qty=0, unit_price=0); db.add(x)
    x.name = str(d["name"]).strip()
    x.unit = d.get("unit") or "u_pc"
    x.min_qty = d.get("min_qty") or 0
    x.active = bool(d.get("active", True))
    db.commit()
    return {"ok": True, "id": pid}



# ================================================================ màn Cấp phát ở trang kế toán (đợt 4, 28/09)
# Phiếu lĩnh / tạm ứng vẫn ở đây (giấy của chuyến). Màn Cấp phát bên kế toán gọi sang, dưới tên người đang bấm — quyền
# và mọi quy tắc là của chính routes/phieu_linh.py, không viết lại. Cấp dầu thì phieu_linh gọi ngược sang kho dầu bên đó.
@router.get("/api/lien-thong/cap-phat")
def lt_cap_phat(request: Request, response: Response, trang_thai: str = "cho", db: Session = Depends(get_db),
                u=Depends(may_ke_toan_goi)):
    from routes import phieu_linh as PL
    return PL.ds_cho_cap(request, response, trang_thai=trang_thai, loai="", co=500, db=db, user=u)


@router.get("/api/lien-thong/cap-phat/tra-cuu/{token}")
def lt_tra_cuu(token: str, request: Request, db: Session = Depends(get_db), u=Depends(may_ke_toan_goi)):
    from routes import phieu_linh as PL
    return PL.tra_cuu(token, request, db=db, user=u)


@router.post("/api/lien-thong/cap-phat/{vid}/cap")
def lt_cap(vid: str, d: dict = Body(default={}), db: Session = Depends(get_db), u=Depends(may_ke_toan_goi)):
    from routes import phieu_linh as PL
    return PL.cap_phat(vid, d, db=db, user=u)


@router.get("/api/lien-thong/ty-gia")
def lt_ty_gia(db: Session = Depends(get_db), u=Depends(may_ke_toan_goi)):
    """Tỷ giá quy Kíp hiện hành (màn Tỷ giá ở đây) — gợi ý khi nhập kho dầu bằng ngoại tệ ở trang kế toán."""
    from models import ExchangeRate
    return {r.code: r.rate_to_lak for r in db.query(ExchangeRate).all()}


@router.get("/api/lien-thong/dia-chi")
def dia_chi(db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    """Địa chỉ KHO TẠM (máy EPL_KETOAN) để giao diện bên này mở sang (nút Cấp phát, Kho nhiên liệu…). `kho_web` là tên mới
    (01/10, cấu hình kho riêng); `ke_toan_web` cùng giá trị, giữ cho giao diện bản cũ — bỏ ở đợt dọn tên cấu hình."""
    from services import kho_ke_toan as KK
    web = KK.web_ke_toan(db)
    return {"kho_web": web, "ke_toan_web": web}


@router.get("/api/lien-thong/ma-ke-toan")
def lt_ma_ke_toan(db: Session = Depends(get_db), u=Depends(may_ke_toan_goi)):
    """Hai mã bên kế toán cấp sau, đang đặt ở màn Chứng từ → Cấu hình bên này — trang kế toán ghi lên tờ kho nó sinh
    (DC_HH điều chỉnh kho hàng…). Trống = chưa đặt; tờ vẫn mang tên vế, như trước."""
    return {"ma_hang_khach_gui": DK.cau_hinh(db, "ma_hang_khach_gui") or None, "ma_gia_von": DK.cau_hinh(db, "ma_gia_von") or None}


# ---------------------------------------------------------------- lệnh sửa chữa ở trang kế toán (đợt 6)
@router.get("/api/lien-thong/xe")
def lt_xe(db: Session = Depends(get_db), u=Depends(may_ke_toan_goi)):
    """Danh mục xe (ở đây) — ô chọn xe của lệnh sửa chữa bên trang kế toán."""
    from models import Vehicle
    return [{"id": x.id, "truck_no": x.truck_no, "plate_head": x.plate_head, "owner_type": x.owner_type,
             "odometer_km": x.odometer_km, "status": x.status, "active": bool(x.active)}
            for x in db.query(Vehicle).order_by(Vehicle.truck_no).all()]


@router.post("/api/lien-thong/xe/{vid}/sua-chua")
def lt_xe_sua_chua(vid: str, d: dict = Body(...), db: Session = Depends(get_db), u=Depends(may_ke_toan_goi)):
    """Lệnh sửa chữa bên trang kế toán báo xe VÀO xưởng (`vao`: true) hay sửa xong (false). Danh mục xe phải nói đúng —
    điều xe nhìn vào đó mà xếp chuyến. Sửa xong thì xe về rảnh, trừ khi đang chạy một chuyến hoặc đã ngưng dùng."""
    from models import Trip, Vehicle
    x = db.get(Vehicle, vid)
    if not x:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có xe này bên trang điều xe."})
    if d.get("vao"):
        if x.status not in ("inactive", "on_trip"):
            x.status = "maintenance"
    elif x.status == "maintenance":
        dang_chay = db.query(Trip.id).filter(Trip.vehicle_id == x.id, Trip.transport_status != "arrived").first()
        x.status = "on_trip" if dang_chay else "available"
    db.commit()
    return {"id": x.id, "status": x.status}


# ---------------------------------------------------------------- bán hàng ở trang kế toán (đợt 6)
# Đường kho (kho tạm), không có tiền — giữ tới khi nối hệ anh Toàn. Màn Bán hàng bên đó cần ô chọn người mua để lập phiếu xuất
# kho bán (PXK_BAN); phần tiền của bán hàng (HD_BAN, PT_BAN) sang hệ anh Tune là việc còn mở (chủ dự án 01/10).
@router.get("/api/lien-thong/nguoi-mua")
def lt_nguoi_mua(db: Session = Depends(get_db), u=Depends(may_ke_toan_goi)):
    """Danh mục khách hàng và chủ xe liên kết (ở đây) — ô chọn người mua của phiếu bán hàng bên trang kế toán."""
    from collections import defaultdict
    from models import Customer, Owner, Vehicle
    xe = defaultdict(list)
    for oid, so in db.query(Vehicle.owner_id, Vehicle.truck_no).filter(Vehicle.owner_id.isnot(None), Vehicle.active.is_(True)):
        xe[oid].append(so)
    return {"khach": [{"id": k.id, "name": k.name, "active": bool(k.active)} for k in db.query(Customer).order_by(Customer.name).all()],
            "chu_xe": [{"id": o.id, "name": o.name, "active": bool(o.active), "so_xe": xe.get(o.id, [])}
                       for o in db.query(Owner).order_by(Owner.name).all()]}


# ---------------------------------------------------------------- phần TIỀN của trang kế toán tạm: đã gỡ (01/10)
# Chủ dự án chốt 01/10: bỏ phần tiền trang kế toán tạm (số ở đó là số thử), cắt sổ hôm nay — mọi việc tiền chỉ ở hệ anh Tune.
# Gỡ các đường máy bên đó gọi sang: doanh-thu/* (hoá đơn, thu tiền) · chu-xe/* và xe-lien-ket (đợt trả chủ xe) ·
# tien-tai-xe, tat-toan/*, thang-moi-nhat (tiền tài xế, tất toán) · ncc/*, can-tru (nhà cung cấp, cấn trừ).
# Trang điều xe tự làm lại phần đó và nối hệ anh Tune: routes/tat_toan.py, routes/nha_cung_cap.py, routes/chu_xe.py
# (services/chi_tat_toan_tune.py, services/chi_tune.py). Các đường KHO ở trên giữ nguyên — trang kế toán tạm còn làm kho.
