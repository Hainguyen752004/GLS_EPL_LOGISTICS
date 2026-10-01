# -*- coding: utf-8 -*-
"""TRẢ CHỦ XE LIÊN KẾT — phần tính và bản chép "đã trả" trên phiếu.

Chủ dự án chốt 01/10: bỏ phần tiền của trang kế toán tạm (đợt trả, tờ PC_CX — số thử, bỏ), cắt sổ hôm nay; tiền trả chủ xe
chi THẬT ở hệ kế toán anh Tune — services/chi_tune.py lập phiếu chi "Chi khác" (Nợ 4022 / Có tiền) đứng tên chủ xe, thủ quỹ
bên đó chi và ghi sổ, rồi gọi `danh_dau_tra` với mã đợt "TUNE:<số phiếu bên đó>". Ở đây còn:

  1. **Số "trả chủ xe" của từng phiếu** — tiền thuê × tấn − phí − quá tải − EPL đã ứng (services/tinh_toan → tinh_phieu).
     Đề nghị trả lấy đúng số này, không gõ tay, không tính lại cách khác.
  2. **Bản chép "đã trả"** trên phiếu: owner_payment_id ("TUNE:…"), owner_paid, owner_paid_usd / _lak / _by / _at.
     Kiểm lại ngay lúc ghi (dòng khoá) để không trả hai lần.
  3. **Trừ hàng chủ xe mua ở quầy** (chủ dự án 23/09: "deal 1tr6, mua xăng 3 trăm → trả 1tr3") — phiếu bán nằm ở KHO TẠM
     (EPL_KETOAN, ba đường máy /api/lien-thong/ban-hang/…). Đề nghị trả lấy SỐ TRẢ THỰC = Σ phiếu − Σ hàng mua: `tinh_tru`.
     Lúc lập đề nghị giữ chỗ các phiếu bán ("TUNE-CHO:<số đề nghị>"), thủ quỹ đã chi thì chốt ("TUNE:<số phiếu chi>") và ghi
     bút toán chờ Nợ 4022 / Có 707, đề nghị bị bỏ thì trả phiếu bán về chờ trừ.
"""
import datetime as dt
from urllib.parse import quote

from fastapi import HTTPException

from models import Owner, Trip, TripExpense
from services.tinh_toan import lam_tron, tinh_phieu

TIEN_TO_TUNE = "TUNE:"          # chỉ đề nghị trả qua hệ kế toán anh Tune mới đánh "đã trả" (cắt sổ 01/10)
GIU_CHO = "TUNE-CHO:"           # phiếu bán đang nằm trong một đề nghị trả chưa chi (kho tạm không cho thu, không cho bỏ)
NGUON_BAN = "ban_chu_xe"        # bút toán chờ Nợ 4022 / Có 707 của hàng bán cho chủ xe — một phiếu bán một bút toán


def dong_phieu(db, p, dong=None):
    """Một phiếu cho màn trả chủ xe: số trả và các phần trừ, cùng trạng thái (khoá, đã trả)."""
    k = tinh_phieu(p, db.query(TripExpense).filter(TripExpense.trip_id == p.id).order_by(TripExpense.section, TripExpense.line_no).all()
                   if dong is None else dong)
    return {"id": p.id, "doc_no": p.doc_no, "doc_date": p.doc_date.isoformat() if p.doc_date else None,
            "truck_no": p.truck_no, "customer_name": p.customer_name, "company": p.company, "owner_id": p.owner_id,
            "owner_name": p.owner_name, "locked": bool(p.locked),
            "owner_paid": bool(p.owner_paid or p.owner_payment_id), "owner_payment_id": p.owner_payment_id,
            "tan_tinh": k["tan_tinh"], "hire_ccy": k.get("hire_ccy"), "tien_thue": k.get("tien_thue"), "phi": k.get("phi"),
            "tru_vuot": k.get("tru_vuot"), "ung_truoc": k.get("ung_truoc"), "tra_chu_xe": k.get("tra_chu_xe"),
            "tra_chu_xe_lak": k.get("tra_chu_xe_lak")}


def cho_tra(db, owner_id):
    """Phiếu đã KHOÁ của chủ xe chưa trả — cũ trước (chi_tune lọc thêm phiếu đang nằm đề nghị trả)."""
    from routes.chu_xe import _phieu_cho_tra
    o = db.get(Owner, owner_id)
    if not o:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có chủ xe này bên trang điều xe."})
    return [dong_phieu(db, p) for p in _phieu_cho_tra(db, o)]


def so_lieu(db, trip_ids):
    return {p.id: dong_phieu(db, p) for p in db.query(Trip).filter(Trip.id.in_([i for i in trip_ids if i] or [""])).all()}


def _chan(p, ma, chu):
    raise HTTPException(409, {"ma": ma, "loi": chu, "trip_id": p.id, "doc_no": p.doc_no})


def danh_dau_tra(db, user, owner_payment_id, cac_dong):
    """Phiếu chi trả chủ xe bên hệ kế toán đã ghi sổ (chi_tune.dong_bo_chu_xe) → ghi bản chép "đã trả" cho các phiếu đó.
    Kiểm lại ngay lúc ghi (dòng khoá): phiếu phải là xe liên kết, đã khoá, chưa trả. Chỉ nhận mã đợt "TUNE:…"."""
    from routes.phieu import _ghi_log
    theo = {str(d.get("trip_id")): d for d in (cac_dong or []) if d.get("trip_id")}
    if not owner_payment_id or not theo:
        raise HTTPException(422, {"ma": "THIEU", "loi": "Thiếu đợt trả hoặc phiếu."})
    if not str(owner_payment_id).startswith(TIEN_TO_TUNE):
        raise HTTPException(409, {"ma": "TRA_QUA_KE_TOAN", "loi": "Trả chủ xe chỉ qua đề nghị trả sang hệ kế toán anh Tune (cắt sổ "
                                                                 "01/10) — không ghi \"đã trả\" từ nơi khác."})
    ds = db.query(Trip).filter(Trip.id.in_(list(theo))).with_for_update().all()
    if len(ds) != len(theo):
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Có phiếu không còn bên trang điều xe."})
    for p in ds:
        if p.company != "joint":
            _chan(p, "KHONG_PHAI_LIEN_KET", "Phiếu %s là xe nhà, không có chủ xe để trả." % p.doc_no)
        if not p.locked:
            _chan(p, "CHUA_KHOA", "Phiếu %s chưa khoá; kế toán khoá rồi quỹ mới trả." % p.doc_no)
        if p.owner_payment_id or p.owner_paid:
            _chan(p, "DA_TRA", "Phiếu %s đã trả chủ xe rồi." % p.doc_no)
    bay_gio = dt.datetime.utcnow()
    for p in ds:
        d = theo[p.id]
        p.owner_payment_id = str(owner_payment_id)
        p.owner_paid, p.owner_paid_usd, p.owner_paid_lak = True, d.get("tra_chu_xe"), d.get("tra_chu_xe_lak")
        p.owner_paid_by, p.owner_paid_at = getattr(user, "full_name", None), bay_gio
        _ghi_log(db, p, user, "a_pay_owner")
    db.commit()
    return {p.id: True for p in ds}

# ================================================================ trừ hàng chủ xe mua ở quầy (kho tạm giữ phiếu bán)
def _kho(db, method, duong, body=None, user=None):
    from services import goi_ke_toan as KT          # kho tạm tắt → 503 CHUA_NOI_KE_TOAN: chặn, không trả dư cho chủ xe
    return KT.goi(db, method, duong, body, nguoi=user)


def hang_cho_tru(db, owner_id, user):
    """Phiếu bán chủ xe mua ở quầy CHƯA trừ (chưa thu, chưa nằm đề nghị nào) — cũ trước. Kho tạm không nối được thì ném 503."""
    return _kho(db, "GET", "/api/lien-thong/ban-hang/cho-tru?owner_id=%s" % quote(owner_id), user=user) or []


def tinh_tru(chon, hang):
    """SỐ TRẢ THỰC của một đề nghị: các phiếu chọn (dòng của cho_tra / so_lieu, cùng tiền thuê) trừ hàng mua ở quầy.

    Luật cũ của đợt trả (giữ nguyên): xét hàng mua cũ trước, phiếu bán nào còn vừa số chưa trừ (tính bằng Kíp) thì trừ, không
    vừa thì để đợt sau — không trừ lố thành chủ xe nợ ngược. Phần trừ chia vào các phiếu dương, cũ trước, nên mỗi dòng phiếu
    chi bên kế toán là số THỰC TRẢ của phiếu đó (không dòng âm); phiếu bị trừ hết thì dòng bằng 0 (bỏ khỏi phiếu chi)."""
    ccy = (chon[0].get("hire_ccy") if chon else None) or "LAK"
    tong = lam_tron(sum(x.get("tra_chu_xe") or 0 for x in chon), ccy)
    tong_lak = round(sum(x.get("tra_chu_xe_lak") or 0 for x in chon))
    con, tru_lak, lay, de_lai = tong_lak, 0, [], []
    for b in sorted(hang or [], key=lambda b: (b.get("sale_date") or "", b.get("doc_no") or "")):
        lak = round(b.get("total_lak") or 0)
        if 0 < lak <= con:
            con -= lak; tru_lak += lak; lay.append(b)
        elif lak > 0:
            de_lai.append(b)
    dong, con_lak = [], tru_lak
    for x in chon:
        t, tl = x.get("tra_chu_xe") or 0, round(x.get("tra_chu_xe_lak") or 0)
        bt_lak = min(tl, con_lak) if (t > 0 and tl > 0) else 0
        con_lak -= bt_lak
        bt = t if bt_lak == tl and bt_lak else lam_tron(bt_lak * t / tl, ccy) if bt_lak else 0
        dong.append({"trip_id": x["id"], "doc_no": x.get("doc_no"), "tra_chu_xe": t, "tra_chu_xe_lak": tl, "tru": bt, "tru_lak": bt_lak,
                     "tra_thuc": lam_tron(t - bt, ccy), "tra_thuc_lak": tl - bt_lak})
    tru = lam_tron(sum(d["tru"] for d in dong), ccy)
    return {"ccy": ccy, "tong": tong, "tong_lak": tong_lak, "tru": tru, "tru_lak": tru_lak,
            "tra_thuc": lam_tron(tong - tru, ccy), "tra_thuc_lak": tong_lak - tru_lak,
            "hang": [{k: b.get(k) for k in ("id", "doc_no", "sale_date", "currency", "total", "total_lak")} for b in lay],
            "hang_de_lai": [{k: b.get(k) for k in ("id", "doc_no", "sale_date", "currency", "total", "total_lak")} for b in de_lai],
            "dong": dong}


def tru_hang_quay(db, owner_id, chon, user):
    """tinh_tru với hàng mua ở quầy đang chờ trừ của chủ xe (hỏi kho tạm). Gọi lúc lập đề nghị và lúc xem trước."""
    return tinh_tru(chon, hang_cho_tru(db, owner_id, user) if chon else [])


def giu_hang_quay(db, ref_no, owner_id, sale_ids, user):
    """Lập đề nghị (TRƯỚC khi gọi hệ kế toán): giữ chỗ các phiếu bán "TUNE-CHO:<số đề nghị>" — kho tạm kiểm lại trong dòng khoá,
    phiếu đã bị trừ / đã thu / đã bỏ thì 409 / 404 và đề nghị không lập. Không có phiếu bán thì thôi."""
    if not sale_ids:
        return []
    return _kho(db, "POST", "/api/lien-thong/ban-hang/tru", {"sale_ids": list(sale_ids), "ma": GIU_CHO + ref_no, "owner_id": owner_id},
                user=user) or []


def tha_hang_quay(db, ref_no, user):
    """Đề nghị bị bỏ (huỷ, gửi lại mà phiếu không còn hợp lệ): phiếu bán đang giữ chỗ về chờ trừ. Gọi lại vô hại."""
    return _kho(db, "POST", "/api/lien-thong/ban-hang/bo-tru", {"ma": GIU_CHO + ref_no}, user=user) or {}


def chot_hang_quay(db, ref_no, so_phieu_chi, owner_id, sale_ids, user, by_user=None):
    """Thủ quỹ bên kế toán đã chi (phiếu chi đã ghi sổ): phiếu bán đổi "TUNE-CHO:<số đề nghị>" → "TUNE:<số phiếu chi>" và ghi
    bút toán chờ Nợ 4022 / Có 707 cho từng phiếu (KHÔNG commit — người gọi commit). Gọi lại vô hại (cùng mã, cùng nguồn).

    Vì sao ghi bút toán LÚC NÀY mà không lúc lập phiếu bán: phiếu bán lập ở kho tạm — trang điều xe chỉ biết nó khi trừ; lúc
    giữ chỗ việc trừ còn huỷ được; khi tiền trả chủ xe đã đi thì phần trừ là chắc. Ngày hạch toán là NGÀY BÁN, để doanh thu
    707 vào đúng kỳ bán (bút toán chưa gửi nên ghi muộn không lệch kỳ)."""
    from services import but_toan_cho as BTC
    from services import tai_khoan as TK
    if not sale_ids:
        return []
    ds = _kho(db, "POST", "/api/lien-thong/ban-hang/tru", {"sale_ids": list(sale_ids), "ma": TIEN_TO_TUNE + str(so_phieu_chi),
                                                           "ma_cu": GIU_CHO + ref_no, "owner_id": owner_id}, user=user) or []
    for b in ds:
        BTC.ghi(db, NGUON_BAN, b["id"], b.get("sale_date") or dt.date.today(),
                [{"no": TK.CHU_XE, "co": TK.DT_BAN_HANG, "tien": b.get("total") or 0, "ccy": b.get("currency") or "LAK",
                  "tien_lak": b.get("total_lak"), "doi_tuong": {"loai": "chu_xe", "ref_id": owner_id}, "ref": b.get("doc_no"),
                  "dien_giai": "Bán hàng cho chủ xe %s, trừ vào tiền trả (%s)" % (b.get("doc_no"), so_phieu_chi)}],
                "Hàng bán cho chủ xe %s trừ vào phiếu chi %s (đề nghị %s)" % (b.get("doc_no"), so_phieu_chi, ref_no), by_user=by_user)
    return ds
