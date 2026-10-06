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
     06/10 — kho QLSX (KHO_NGUON mặc định): quầy ở hệ kế toán, hàng mua ở quầy là SO BÁN HÀNG còn nợ của đối tác bên đó (`so_quay`);
     cùng `tinh_tru`, nhưng "giữ chỗ" là CẤN TRỪ SO đó (collection-offset, như SO nhiên liệu) lúc lập đề nghị; bỏ đề nghị thì gỡ cấn
     trừ. Không ghi bút toán Nợ 4022 / Có 707 ở đây: bên kế toán ghi bút toán cấn trừ cùng lần (Nợ phải trả đối tác / Có 1211).
  4. **TẤT TOÁN ĐỐI TÁC** (chủ dự án chốt 02/10) — `phan_tra`: trả đối tác = tiền thuê − phí quản lý − cắt quá tải − tạm ứng EPL
     đưa (tiền mặt) − nợ nhà cung cấp EPL trả thay − SO NHIÊN LIỆU còn nợ. Dầu / phụ tùng kho xuất bán cho đối tác không trừ thẳng
     nữa mà thành SO nhiên liệu bên kế toán (services/so_nhien_lieu.py); lập đề nghị trả thì máy CẤN TRỪ phần SO còn nợ (phiếu cấn
     trừ bên kế toán, bảng can_tru_tune), rồi phiếu chi phần còn lại. Đối tác tự mua tự trả hết → trả đủ tiền thuê. Khi SO nhiên
     liệu chưa thu đồng nào, số còn trả đúng bằng `tra_chu_xe` cũ của tinh_phieu (EPL ứng gồm cả dầu theo giá bán).
"""
import datetime as dt
from urllib.parse import quote

from fastapi import HTTPException

from models import Owner, Trip, TripExpense
from services.tinh_toan import la_tien_mat_tai_xe, la_xuat_ban, lam_tron, tien_dong, tinh_phieu, ty_gia

TIEN_TO_TUNE = "TUNE:"          # chỉ đề nghị trả qua hệ kế toán anh Tune mới đánh "đã trả" (cắt sổ 01/10)
GIU_CHO = "TUNE-CHO:"           # phiếu bán đang nằm trong một đề nghị trả chưa chi (kho tạm không cho thu, không cho bỏ)
NGUON_BAN = "ban_chu_xe"        # bút toán chờ Nợ 4022 / Có 707 của hàng bán cho chủ xe — một phiếu bán một bút toán


def phan_tra(p, dong, so=None):
    """Các phần của tiền trả đối tác cho MỘT phiếu xe thuê (chủ dự án chốt 02/10). `so` = lần gửi SO nhiên liệu của DO
    (GuiSoNhienLieuTune | None) — còn nợ theo bản đọc lại. Tiền theo TIỀN THUÊ của phiếu, kèm số Kíp (tỷ giá khoá trên phiếu).

      tam_ung     dòng EPL ứng TIỀN MẶT (tinh_toan.la_tien_mat_tai_xe — tờ tạm ứng PTU)
      nhien_lieu  dầu / phụ tùng kho EPL XUẤT BÁN cho đối tác theo giá bán (tinh_toan.la_xuat_ban) — SO nhiên liệu
      no_ncc      mọi khoản EPL ứng còn lại (ghi nợ trạm / nhà cung cấp, chipping, thẻ cao tốc, garage quỹ trả ngay…) — EPL trả
                  thay. Ba phần cộng lại đúng bằng tổng chi EPL ứng của tinh_phieu (`ung_truoc`).
      tra_truoc_can_tru = tiền thuê − phí − quá tải − (tam_ung + no_ncc)
      can_tru     phần SO nhiên liệu còn nợ cấn vào tiền trả = min(còn nợ, tra_truoc_can_tru nếu dương) — Kíp (SO tính bằng Kíp)
      con_tra     = tra_truoc_can_tru − can_tru → số phiếu chi
    Phiếu có xuất bán mà SO nhiên liệu chưa tạo: `cho_so` True, cấn trừ giả định đủ phần nhiên liệu (con_tra = tra_chu_xe cũ) —
    chỉ để xem; lập đề nghị bị chặn cho tới khi tạo SO."""
    t = tinh_phieu(p, dong)
    h = t.get("hire_ccy") or "LAK"
    r_h = ty_gia(p, h)
    epl = [d for d in dong if d.paid_by_epl is not False and (d.qty or 0) > 0]
    ban = [d for d in epl if la_xuat_ban(p, d)]
    tm = [d for d in epl if not la_xuat_ban(p, d) and la_tien_mat_tai_xe(d, p.company)]
    nl_lak = round(sum(tien_dong(p, d) for d in ban))
    tu_lak = round(sum(tien_dong(p, d) for d in tm))
    ncc_lak = max(0, round(t.get("tong_chi_lak") or 0) - nl_lak - tu_lak)
    tien_thue, phi, vuot = t.get("tien_thue") or 0, t.get("phi") or 0, t.get("tru_vuot") or 0
    goc = lam_tron(tien_thue - phi - vuot - lam_tron((tu_lak + ncc_lak) / r_h, h), h)
    goc_lak = round(goc * r_h)
    co_so = so is not None and so.status == "synced"
    if co_so:
        con_no = so.thu_con_no if so.thu_con_no is not None else (so.total_amount or 0)
        con_no_lak = max(0, round(float(con_no)))
    else:
        con_no_lak = nl_lak                                   # chưa có SO: coi như chưa thu đồng nào
    can_lak = min(con_no_lak, max(0, goc_lak))
    can = goc if can_lak == goc_lak else lam_tron(can_lak / r_h, h)
    con = lam_tron(goc - can, h)
    return {"hire_ccy": h, "ty_gia_thue": r_h, "tien_thue": tien_thue, "phi": phi, "tru_vuot": vuot,
            "tam_ung_lak": tu_lak, "tam_ung": lam_tron(tu_lak / r_h, h), "no_ncc_lak": ncc_lak, "no_ncc": lam_tron(ncc_lak / r_h, h),
            "nhien_lieu_lak": nl_lak, "nhien_lieu": lam_tron(nl_lak / r_h, h), "dong_ban": ban, "dong_tam_ung": tm,
            "so_nhien_lieu": so.order_code if co_so else None, "so_nhien_lieu_status": so.status if so is not None else None,
            "cho_so": bool(ban) and not co_so, "nhien_lieu_con_no_lak": con_no_lak if (ban or co_so) else 0,
            "tra_truoc_can_tru": goc, "tra_truoc_can_tru_lak": goc_lak, "can_tru_lak": can_lak, "can_tru": can,
            "con_tra": con, "con_tra_lak": round(con * r_h)}


COT_TAT_TOAN = ("tam_ung", "tam_ung_lak", "no_ncc", "no_ncc_lak", "nhien_lieu", "nhien_lieu_lak", "so_nhien_lieu", "cho_so",
                "nhien_lieu_con_no_lak", "tra_truoc_can_tru", "tra_truoc_can_tru_lak", "can_tru", "can_tru_lak", "con_tra", "con_tra_lak")


def dong_phieu(db, p, dong=None, so=False):
    """Một phiếu cho màn trả chủ xe: số trả và các phần trừ, cùng trạng thái (khoá, đã trả). Từ 02/10 thêm các phần của tất toán
    đối tác (`phan_tra`, khoá COT_TAT_TOAN) — `tra_chu_xe` giữ nguyên số cũ (= cấn trừ đủ phần dầu).
    `so`: lần gửi SO nhiên liệu đã nạp sẵn (False = chưa nạp → hỏi DB)."""
    from services import so_nhien_lieu as NL
    dong = (db.query(TripExpense).filter(TripExpense.trip_id == p.id).order_by(TripExpense.section, TripExpense.line_no).all()
            if dong is None else dong)
    k = tinh_phieu(p, dong)
    ra = {"id": p.id, "doc_no": p.doc_no, "doc_date": p.doc_date.isoformat() if p.doc_date else None,
          "truck_no": p.truck_no, "customer_name": p.customer_name, "company": p.company, "owner_id": p.owner_id,
          "owner_name": p.owner_name, "locked": bool(p.locked),
          "owner_paid": bool(p.owner_paid or p.owner_payment_id), "owner_payment_id": p.owner_payment_id,
          "tan_tinh": k["tan_tinh"], "hire_ccy": k.get("hire_ccy"), "tien_thue": k.get("tien_thue"), "phi": k.get("phi"),
          "tru_vuot": k.get("tru_vuot"), "ung_truoc": k.get("ung_truoc"), "tra_chu_xe": k.get("tra_chu_xe"),
          "tra_chu_xe_lak": k.get("tra_chu_xe_lak")}
    if p.company == "joint":
        x = phan_tra(p, dong, NL.so_cua(db, p) if so is False else so)
        ra.update({c: x[c] for c in COT_TAT_TOAN})
    return ra


def sau_can_tru(chon):
    """Bản sao các dòng phiếu (dong_phieu) với tra_chu_xe / tra_chu_xe_lak = số CÒN TRẢ sau cấn trừ SO nhiên liệu — đầu vào của
    tinh_tru (trừ hàng quầy) và phiếu chi. Dòng không có phần tất toán đối tác giữ nguyên."""
    ra = []
    for x in chon:
        y = dict(x)
        if "con_tra" in x:
            y["tra_chu_xe"], y["tra_chu_xe_lak"] = x["con_tra"], x["con_tra_lak"]
        ra.append(y)
    return ra


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
    from services import kho_qlsx as KQ
    if KQ.bat():                                    # 05/10: bỏ kho tạm — bán hàng quầy chuyển sang Web anh Tune
        raise HTTPException(409, {"ma": "QUAY_DA_TAT", "loi": "Bán hàng quầy cho chủ xe đã chuyển sang hệ kế toán (Web anh Tune) — "
                                                              "trang điều xe không giữ / trừ phiếu bán nữa."})
    from services import goi_ke_toan as KT          # kho tạm tắt → 503 CHUA_NOI_KE_TOAN: chặn, không trả dư cho chủ xe
    return KT.goi(db, method, duong, body, nguoi=user)


def hang_cho_tru(db, owner_id, user):
    """Phiếu bán chủ xe mua ở quầy CHƯA trừ (chưa thu, chưa nằm đề nghị nào) — cũ trước. Kho tạm không nối được thì ném 503.
    Kho QLSX (06/10, chủ dự án chốt «làm đủ» — trước đây nhánh này trả rỗng nên tiền mua ở quầy không còn trừ vào tiền trả): SO BÁN
    HÀNG còn nợ của đối tác bên hệ kế toán (so_quay), bỏ SO đang chờ cấn trừ trong một đề nghị khác. Đọc không được thì ném."""
    from services import kho_qlsx as KQ
    if KQ.bat():
        if not owner_id or db.get(Owner, owner_id) is None:
            return []                               # không phải đối tác bên trang này (xe nhà…) → không có SO quầy để trừ, không gọi mạng
        return [x for x in so_quay(db, owner_id) if not x.get("dang_de_nghi")]
    return _kho(db, "GET", "/api/lien-thong/ban-hang/cho-tru?owner_id=%s" % quote(owner_id), user=user) or []


# ---------------------------------------------------------------- SO bán hàng mua ở quầy ở hệ kế toán (06/10)
# Kho / quầy dời sang hệ anh Tune (05/10): đối tác mua ở quầy là một SO BÁN HÀNG thường bên đó đứng tên đối tác (EPLCX-<chủ xe>),
# treo công nợ đối tác — khác SO cước (OrderSource LOGISTICS) và SO nhiên liệu (LOGISTICS_FUEL) của trang này. Lập đề nghị trả thì
# máy CẤN TRỪ các SO đó (collection-offset — thủ tục bên đó nhận mọi SO có phiếu bán + một dòng công nợ, không giới hạn loại SO) đúng
# cách SO nhiên liệu (chi_tune.de_nghi_tra_chu_xe → can_tru_tune, trip_id trống). Luật trừ giữ như phiếu bán kho tạm (tinh_tru): cũ
# trước, SO nào vừa số còn trả thì trừ CẢ phần còn nợ của SO, không vừa để đợt sau — không trừ lố thành đối tác nợ ngược.
LOAI_QUAY = "so_quay"
NGUON_SO_TRANG_NAY = ("LOGISTICS", "LOGISTICS_FUEL")   # TicketOrder.OrderSource của SO cước · SO nhiên liệu — không phải hàng quầy
TIEN_QUAY = ("LAK", "USD", "THB", "VND", "CNY")         # tiền trang này quy Kíp được (tinh_toan.TIEN_TE)


def so_quay(db, owner_id, kq=None):
    """SO bán hàng (mua ở quầy) CÒN NỢ của đối tác bên hệ kế toán, cũ trước. `kq` = công nợ đối tác đã đọc (chi_tune.cong_no_doi_tac);
    None → đọc (một lời gọi; lỗi → HTTPException, người gọi quyết). Mỗi SO, dạng tinh_tru dùng được (cùng khoá phiếu bán kho tạm):
      {id, doc_no, so: số SO, loai: "so_quay", sale_date, currency, total: CÒN NỢ (tiền SO — số sẽ cấn trừ), total_lak, ty_gia,
       tong_so, da_thu, phieu_ban, dang_de_nghi: số đề nghị đang chờ cấn trừ SO này | None}
    Bỏ: SO cước / SO nhiên liệu (OrderSource, và mã SO trang này đã gửi — phòng DB bên đó chưa áp script nên không có OrderSource), SO
    hết nợ, tiền lạ. Tỷ giá SO không phải Kíp = tỷ giá hiện hành (danh mục Tỷ giá — ngày cấn trừ), ≤ 5 số lẻ như thủ tục cấn trừ nhận."""
    from models import CanTruTune, ChiChuXeTune, GuiSoNhienLieuTune, GuiSoTune
    from services import chi_tune as CHI
    from services.gia_von import ty_gia_lak
    o = db.get(Owner, owner_id)
    if o is None:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có chủ xe này bên trang điều xe."})
    if kq is None:
        kq = CHI.cong_no_doi_tac(db, o)
    no = [x for x in (kq or {}).get("no") or [] if (x.get("so") or "").strip()]
    ngay_don = {(d.get("so") or ""): d.get("ngay") for d in (kq or {}).get("don") or []}
    ma = sorted({x["so"].strip() for x in no})
    cua_trang = set()
    if ma:
        cua_trang = ({c for (c,) in db.query(GuiSoTune.order_code).filter(GuiSoTune.order_code.in_(ma))}
                     | {c for (c,) in db.query(GuiSoNhienLieuTune.order_code).filter(GuiSoNhienLieuTune.order_code.in_(ma))})
    # SO đang nằm trong một đề nghị CHƯA cấn trừ xong (lần cấn trừ chưa gửi được) — bên kia chưa trừ nợ; đề nghị khác lấy lại là trừ hai lần
    dang = {}
    if ma:
        for ct, ref in (db.query(CanTruTune, ChiChuXeTune.ref_no).join(ChiChuXeTune, ChiChuXeTune.id == CanTruTune.de_nghi_id)
                        .filter(ChiChuXeTune.owner_id == owner_id, ChiChuXeTune.status != "huy", CanTruTune.status == "loi",
                                CanTruTune.order_code.in_(ma))):
            dang[ct.order_code] = ref
    ra = []
    for x in no:
        so = x["so"].strip()
        if (x.get("nguon") or "").upper() in NGUON_SO_TRANG_NAY or so in cua_trang:
            continue
        ccy = str(x.get("ccy") or "").strip().upper()
        try:
            con = float(x.get("con_no") or 0)
        except (TypeError, ValueError):
            continue
        if ccy not in TIEN_QUAY or con <= 0.005:
            continue
        con = lam_tron(con, ccy)
        if con <= 0:
            continue
        ty = 1.0 if ccy == "LAK" else round(float(ty_gia_lak(db, ccy)), 5)
        ngay = str(x.get("ngay") or ngay_don.get(so) or "")[:10] or None
        ra.append({"id": so, "doc_no": so, "so": so, "loai": LOAI_QUAY, "sale_date": ngay, "currency": ccy, "total": con,
                   "total_lak": round(con * ty), "ty_gia": ty, "tong_so": x.get("tien"), "da_thu": x.get("da_tra"),
                   "phieu_ban": x.get("phieu_ban"), "dang_de_nghi": dang.get(so)})
    return sorted(ra, key=lambda b: (b.get("sale_date") or "", b["so"]))


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
            "hang": [_gon(b) for b in lay], "hang_de_lai": [_gon(b) for b in de_lai], "dong": dong}


def _gon(b):
    """Một món hàng quầy trong kết quả tinh_tru (lưu vào đề nghị). 06/10: SO bán hàng ở hệ kế toán giữ thêm số SO, loại, tỷ giá —
    chi_tune lập lần cấn trừ theo đó; phiếu bán kho tạm (cũ) giữ đúng sáu khoá như trước."""
    x = {k: b.get(k) for k in ("id", "doc_no", "sale_date", "currency", "total", "total_lak")}
    if b.get("loai") == LOAI_QUAY:
        x.update({k: b.get(k) for k in ("so", "loai", "ty_gia")})
    return x


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
