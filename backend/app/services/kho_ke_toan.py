# -*- coding: utf-8 -*-
"""KHO Ở TRANG KẾ TOÁN — trang điều xe hỏi tồn / giá và xuất kho qua đây (28/09).

Kho phụ tùng (đợt 3) và kho nhiên liệu (đợt 4) — danh mục, tồn, giá bình quân, sổ nhập xuất — dời sang trang kế toán.
Sổ dầu `fuel_moves` bên này đứng yên từ ngày dời (chỉ còn để khoá ngoại của phiếu cũ), không đọc nữa. Bảng `parts` bên này chỉ còn là
bản chép DANH MỤC (tên, đơn vị, tồn tối thiểu, đang dùng) để khoá ngoại của dòng chi mục V, dòng lệnh sửa, dòng bán
vẫn đúng. **Không đọc `Part.qty` / `Part.unit_price` bên này nữa** — số đó đứng yên từ ngày dời, đọc là đọc số cũ.

Xuất kho cho một dòng bên này (sự cố mục V, duyệt báo hỏng, lệnh sửa chữa, bán hàng) đi qua `GiaoDichKho`:

    with KK.GiaoDichKho(db, user) as gd:
        r = gd.xuat_phu_tung(khoa="trip_expense:" + dong.id, part_id=…, qty=…)   # trang kế toán trừ tồn, sinh PXK_PT
        dong.stock_move_id = r["move_id"]
        …
    # ra khỏi khối: bên này commit. Hỏng ở bất cứ đâu trong khối (kể cả lúc commit) → huỷ mọi lần xuất vừa làm
    # bên kế toán (trả tồn, rút tờ), rồi báo lỗi như thường. Hai bên không lệch.

`khoa` chống trùng: gọi lại cùng khoá thì trang kế toán trả lần xuất cũ, không trừ hai lần. Trang kế toán tắt → 503
"chưa nối được trang kế toán" và việc đó không làm được (chủ dự án chốt 28/09: chặn và báo rõ).

Từ 01/10 máy EPL_KETOAN chỉ còn là KHO TẠM (bỏ phần tiền). Mọi lời gọi ở đây đi qua `KT.goi`, đọc cấu hình KHO riêng
(`kho_api`, `kho_token`, `kho_web` — chưa đặt thì khoá cũ `ke_toan_*`), không còn dùng chung với đường đẩy chứng từ.

Kho HÀNG (đợt 5): sổ `goods_moves` cũng ở trang kế toán; dòng hàng trên phiếu (`trip_goods`) vẫn ở đây. Phiếu gom về
tới bãi → `gd.nhap_hang` (gọi lại không nhập trùng); lưu phiếu giao → `gd.xuat_hang` (thay phần xuất của phiếu, bên kia
kiểm tồn lô). Bên này lưu hỏng → gỡ phần vừa nhập / trả lại phần xuất cũ.
"""
import logging

from fastapi import HTTPException

from services import goi_ke_toan as KT
from services import kho_hang_dia as KHD
from services import kho_qlsx as KQ

_nk = logging.getLogger("epl_lao.kho_ke_toan")


# 05/10 — KHO_NGUON=qlsx (mặc định): các hàm dưới đây rẽ sang kho QLSX anh Tune (services/kho_qlsx.py) — tồn, giá vốn bình quân, xuất /
# huỷ xuất phụ tùng; kho hàng khách gửi về sổ goods_moves bên này (services/kho_hang_dia.py). KHO_NGUON=kho_tam: đường cũ.
DONG_KHO_TAM_CU = ("DONG_KHO_TAM_CU", "Dòng này xuất ở KHO TẠM cũ (trước khi kho chuyển sang hệ kế toán anh Tune 05/10) — không trả kho tự "
                   "động được nữa. Nhờ kế toán lập phiếu nhập điều chỉnh bên kho QLSX, rồi mới xoá phiếu.")


def _cu_kho_tam(mv):
    raise HTTPException(409, {"ma": DONG_KHO_TAM_CU[0], "loi": DONG_KHO_TAM_CU[1], "stock_move_id": mv})


def ds_phu_tung(db, nguoi=None):
    """Mọi phụ tùng (kể cả ngưng dùng) kèm tồn và giá bình quân hiện tại — hỏi thẳng kho, không đệm.
    Kho QLSX: danh mục là bản chép parts bên này, tồn + giá vốn bình quân theo mã EPLPT-<id> ở kho phụ tùng (KHO-PT)."""
    if KQ.bat():
        from models import Part
        ton = {r.get("itemCode"): r for r in KQ.ton(db, kho=(KQ.kho_pt(),))}
        ra = []
        for p in db.query(Part).order_by(Part.name).all():
            r = ton.get(KQ.ma_pt(p.id)) or {}
            qty = float(r.get("qty") or 0)
            ra.append({"id": p.id, "name": p.name, "unit": p.unit, "qty": qty, "min_qty": p.min_qty,
                       "unit_price": float(r.get("avgUnitCost") or 0), "active": p.active, "item_code": KQ.ma_pt(p.id),
                       "warehouse_code": KQ.kho_pt(), "status": ("het" if qty <= 0 else "thap" if p.min_qty and qty <= p.min_qty else "du")})
        return ra
    return KT.goi(db, "GET", "/api/lien-thong/phu-tung", nguoi=nguoi) or []


def gia_phu_tung(db, part_id):
    """Giá bình quân hiện tại của một phụ tùng (LAK). Một yêu cầu hỏi trang kế toán một lần."""
    bang = db.info.get("_pt_ke_toan")
    if bang is None:
        bang = db.info["_pt_ke_toan"] = {p["id"]: p for p in ds_phu_tung(db)}
    p = bang.get(part_id)
    return (p.get("unit_price") or 0) if p else 0


def huy_xuat(db, nguoi, move_id=None, khoa=None):
    """Trả lại một lần xuất phụ tùng. Kho QLSX: huỷ phiếu xuất theo SourceRef dựng từ khoa ("trip_expense:<mã dòng>")."""
    if KQ.bat():
        if move_id and not KQ.la_mv(move_id):
            _cu_kho_tam(move_id)
        if not khoa:
            raise HTTPException(409, {"ma": "THIEU_KHOA_KHO", "loi": "Không biết phiếu xuất kho nào để huỷ (thiếu khoá dòng)."})
        return KQ.huy(db, KQ.sr(khoa), "Trang điều xe huỷ dòng / xoá phiếu %s" % (getattr(nguoi, "full_name", None) or ""))
    return KT.goi(db, "POST", "/api/lien-thong/phu-tung/huy-xuat", {"move_id": move_id, "khoa": khoa}, nguoi=nguoi)


# ---------------------------------------------------------------- kho nhiên liệu (đợt 4, 28/09)
def kho_dau(db):
    """{place_id: {ton_lit, gia_bq}} của mọi kho dầu EPL — hỏi trang kế toán một lần mỗi yêu cầu."""
    bang = db.info.get("_dau_ke_toan")
    if bang is None and KQ.bat():
        from models import FuelPlace
        ma = {k.code: k.id for k in db.query(FuelPlace).filter(FuelPlace.owner_type == "epl") if k.code}
        bang = {}
        for r in KQ.ton(db, kho=tuple(ma), hang=(KQ.MA_DAU,)):
            if r.get("itemCode") == KQ.MA_DAU and r.get("warehouseCode") in ma:
                bang[ma[r["warehouseCode"]]] = {"ton_lit": float(r.get("qty") or 0), "gia_bq": float(r.get("avgUnitCost") or 0),
                                                "code": r["warehouseCode"]}
        db.info["_dau_ke_toan"] = bang
    if bang is None:
        bang = db.info["_dau_ke_toan"] = KT.goi(db, "GET", "/api/lien-thong/nhien-lieu/kho") or {}
    return bang


def gia_dau(db, place_id):
    """Giá bình quân hiện tại (LAK/lít) của một kho dầu; trống = kho Thà Bốc."""
    from services.gia_von import kho_goc
    return ((kho_dau(db).get(place_id or kho_goc(db)) or {}).get("gia_bq")) or 0


def huy_xuat_dau(db, nguoi, move_id=None, khoa=None):
    if KQ.bat():
        if KQ.la_mv(move_id):           # cấp ở kho QLSX theo phiếu đề nghị: thủ kho huỷ phiếu xuất bên đó (routes/phieu chặn trước)
            raise HTTPException(409, {"ma": "DA_CAP_KHO_QLSX", "loi": "Dầu đã cấp ở kho QLSX (phiếu kho %s) — huỷ phiếu xuất kho bên đó "
                                                                       "trước." % move_id[len(KQ.TIEN_TO_MV):]})
        _cu_kho_tam(move_id)
    return KT.goi(db, "POST", "/api/lien-thong/nhien-lieu/huy-xuat", {"move_id": move_id, "khoa": khoa}, nguoi=nguoi)


# ---------------------------------------------------------------- kho hàng (đợt 5, 28/09)
def lo_hang(db, tru_phieu=None):
    """Lô còn hàng ở bãi — ô chọn lô trên phiếu giao."""
    if KQ.bat():
        return KHD.danh_sach_lo(db, con_hang=True, tru_phieu_id=tru_phieu)
    return KT.goi(db, "GET", "/api/lien-thong/kho-hang/lo" + ("?tru_phieu=" + tru_phieu if tru_phieu else "")) or []


def hang_cua_phieu(db, trip_id):
    """{da_nhap, ton_lo, lay_boi, xuat} của một phiếu trong sổ kho hàng bên trang kế toán — một yêu cầu hỏi một lần."""
    if KQ.bat():
        return KHD.cua_phieu(db, trip_id)
    bang = db.info.setdefault("_hh_ke_toan", {})
    if trip_id not in bang:
        bang[trip_id] = KT.goi(db, "GET", "/api/lien-thong/kho-hang/phieu/" + trip_id) or {}
    return bang[trip_id]


def huy_hang(db, nguoi, trip_id):
    """Xoá phiếu → xoá dòng sổ kho hàng của phiếu bên trang kế toán, rút tờ. Lô đã có phiếu giao khác lấy → 409."""
    db.info.pop("_hh_ke_toan", None)
    if KQ.bat():
        return KHD.huy(db, trip_id)
    return KT.goi(db, "POST", "/api/lien-thong/kho-hang/huy", {"trip_id": trip_id}, nguoi=nguoi)


def _ma_hang_gui(db):
    from services import day_ke_toan as DK
    return DK.cau_hinh(db, "ma_hang_khach_gui") or None


# Bán hàng cho chủ xe mua ở quầy (đợt 6): từ đợt 7b đợt trả chủ xe ở chính trang kế toán, nên việc trừ phiếu bán
# làm luôn bên đó — bên này không còn hỏi / báo trừ nữa.


def web_ke_toan(db):
    """Địa chỉ kho tạm (máy EPL_KETOAN) để MỞ bằng trình duyệt / in vào mã QR phiếu lĩnh (màn Cấp phát ở đó).
    Cấu hình kho riêng từ 01/10: `kho_web`; không đặt thì dùng địa chỉ API kho `kho_api` (cùng máy chủ phục vụ cả giao
    diện). Khoá mới chưa đặt thì đọc khoá cũ `ke_toan_web` / `ke_toan_api` — services/goi_ke_toan.py:doc_kho."""
    if KQ.bat():                         # kho tạm đã tắt: thủ kho cấp ở màn Quản lý kho bên Web anh Tune (QLSX_WEB_URL, có thể trống)
        import os
        return (os.getenv("QLSX_WEB_URL") or "").rstrip("/")
    return (KT.doc_kho(db, "web") or KT.doc_kho(db, "api") or "").rstrip("/")


def doi_tac_xuat_ban(company, owner_id):
    """Đối tác của lần xuất kho cho XE THUÊ (company = joint) — xuất bán cho chủ xe (chủ dự án 29/09 dầu, 30/09 phụ tùng).
    Kho tạm (EPL_KETOAN services/kho_toan.ghi_xuat_dau / ghi_xuat_pt) đọc `owner_id` rồi tự dựng mã EPLCX-<owner_id> để đặt đối
    tác lên phiếu xuất bán bên kho anh Toàn; gửi kèm `ma_doi_tac` (cùng mã PUBOBJECT mà phiếu chi trả chủ xe / SO nhiên liệu
    bên hệ anh Tune dùng — chi_tune.LOAI_DOI_TUONG) để bên kia khỏi phải đoán. Xe nhà (EPL) không gửi gì: xuất nội bộ, không
    có đối tác. Xe thuê mà phiếu chưa có chủ xe thì cũng không gửi — kho tạm ghi rõ "chưa gửi owner_id" trên phiếu đẩy."""
    if company != "joint" or not owner_id:
        return {}
    from services.chi_tune import LOAI_DOI_TUONG
    return {"owner_id": owner_id, "ma_doi_tac": LOAI_DOI_TUONG["chu_xe"][1] + str(owner_id)}


class GiaoDichKho:
    """Một lần lưu bên này có đụng kho bên kế toán. Xem ghi chú đầu tệp."""

    def __init__(self, db, nguoi):
        self.db, self.nguoi, self.da_xuat = db, nguoi, []

    def xuat_phu_tung(self, *, khoa, part_id, qty, ngay=None, gia=None, tien_te="LAK", ty_gia=1.0, truck_no=None,
                      trip_doc_no=None, expense_id=None, company="EPL", section="repair", mo_ta=None, note=None,
                      ghi_chung_tu=True, repair_order=None, owner_id=None):
        """`owner_id`: chủ xe của phiếu — chỉ gửi khi xe thuê (doi_tac_xuat_ban).
        Kho QLSX: phiếu xuất 48 bên anh Tune — xe nhà INTERNAL, xe thuê PARTNER_SALE kèm đối tác EPLCX-<chủ xe>; SourceRef dựng từ
        khoa. Trả {move_id: "qlsx:<số phiếu kho>", unit_price: giá vốn bình quân bên đó, so_phieu, source_ref}."""
        if KQ.bat():
            return self._xuat_pt_qlsx(khoa=khoa, part_id=part_id, qty=qty, ngay=ngay, company=company, owner_id=owner_id,
                                      trip_doc_no=trip_doc_no, truck_no=truck_no, mo_ta=mo_ta, note=note)
        r = KT.goi(self.db, "POST", "/api/lien-thong/phu-tung/xuat", {
            "khoa": khoa, "part_id": part_id, "qty": qty, "ngay": ngay.isoformat() if ngay else None, "gia": gia,
            "tien_te": tien_te, "ty_gia": ty_gia, "truck_no": truck_no, "trip_doc_no": trip_doc_no,
            "expense_id": expense_id, "company": company, "section": section, "mo_ta": mo_ta, "note": note,
            "ghi_chung_tu": ghi_chung_tu, "repair_order": repair_order, **doi_tac_xuat_ban(company, owner_id)}, nguoi=self.nguoi)
        self.da_xuat.append(("pt", r["move_id"]))
        return r

    def _xuat_pt_qlsx(self, *, khoa, part_id, qty, ngay, company, owner_id, trip_doc_no, truck_no, mo_ta, note):
        nguon = KQ.sr(khoa)
        thue = company == "joint"
        dt_ = doi_tac_xuat_ban(company, owner_id)
        if thue and not dt_:
            raise HTTPException(422, {"ma": "THIEU_CHU_XE", "loi": "Xe thuê mà phiếu chưa có chủ xe — xuất bán phụ tùng phải có đối tác."})
        dong = [{"ItemCode": KQ.ma_pt(part_id), "WarehouseCode": KQ.kho_pt(), "Qty": qty,
                 "Note": (note or mo_ta or "")[:200] or None}]
        mo = mo_ta or "Xuất phụ tùng %s · %s" % (trip_doc_no or "", truck_no or "")
        try:
            kq = KQ.xuat(self.db, nguon, dong, muc_dich="PARTNER_SALE" if thue else "INTERNAL", ngay=ngay, mo_ta=mo,
                         ma_doi_tuong=dt_.get("ma_doi_tac"))
        except HTTPException as e:
            if isinstance(e.detail, dict) and e.detail.get("chua_ro"):
                self.da_xuat.append(("qlsx", nguon))     # chưa rõ bên kia ghi chưa: lưu hỏng thì gửi lệnh huỷ đúng khoá
            raise
        self.da_xuat.append(("qlsx", nguon))
        return {"move_id": KQ.TIEN_TO_MV + str(kq.get("documentNo") or kq.get("documentId")), "unit_price": KQ.don_gia(kq),
                "so_phieu": kq.get("documentNo"), "source_ref": nguon, "replayed": kq.get("replayed")}

    def xuat_dau(self, *, khoa, place_id, qty_l, ngay=None, doc_no=None, truck_no=None, expense_id=None, voucher_id=None,
                 voucher_doc_no=None, trip_no=None, company="EPL", gia_du_phong=None, kiem_ton=False, ghi_chung_tu=True,
                 mo_ta=None, note=None, owner_id=None):
        """Xuất dầu ở kho bên trang kế toán — giá bình quân của đúng kho lúc xuất; trả {move_id, unit_price…}.
        `owner_id`: chủ xe của phiếu — chỉ gửi khi xe thuê (doi_tac_xuat_ban)."""
        if KQ.bat():                     # kho QLSX: thủ kho cấp ở màn Quản lý kho bên Web anh Tune (services/ban_giao_dau.py)
            raise HTTPException(409, {"ma": "DA_DOI_SANG_QLSX", "loi": "Cấp dầu theo phiếu đề nghị làm ở màn Quản lý kho bên hệ kế toán "
                                                                        "(Web anh Tune) — kho tạm đã tắt."})
        r = KT.goi(self.db, "POST", "/api/lien-thong/nhien-lieu/xuat", {
            "khoa": khoa, "place_id": place_id, "qty_l": qty_l, "ngay": ngay.isoformat() if ngay else None, "doc_no": doc_no,
            "truck_no": truck_no, "expense_id": expense_id, "voucher_id": voucher_id, "voucher_doc_no": voucher_doc_no,
            "trip_no": trip_no, "company": company, "gia_du_phong": gia_du_phong, "kiem_ton": kiem_ton,
            "ghi_chung_tu": ghi_chung_tu, "mo_ta": mo_ta, "note": note, **doi_tac_xuat_ban(company, owner_id)}, nguoi=self.nguoi)
        self.da_xuat.append(("dau", r["move_id"]))
        return r

    def nhap_hang(self, trip, dong, *, ngay, tan, boc_len, hao_hut):
        """Phiếu gom về tới bãi → nhập kho hàng bên trang kế toán. Trả {da_co}: đã nhập từ trước thì không làm gì."""
        if KQ.bat():                     # hàng khách gửi: sổ goods_moves bên này, cùng giao dịch
            return KHD.nhap(self.db, trip, dong, ngay, getattr(self.nguoi, "full_name", None))
        r = KT.goi(self.db, "POST", "/api/lien-thong/kho-hang/nhap", {
            "trip_id": trip.id, "trip_doc_no": trip.doc_no, "ngay": ngay.isoformat() if ngay else None, "dong": dong,
            "customer_name": trip.customer_name, "origin": trip.origin, "truck_no": trip.truck_no, "company": trip.company,
            "tan": tan, "boc_len": boc_len, "hao_hut": hao_hut, "ma_hang_gui": _ma_hang_gui(self.db)}, nguoi=self.nguoi)
        if not r.get("da_co") and r.get("so_dong"):
            self.da_xuat.append(("hh_nhap", trip.id))
        self.db.info.pop("_hh_ke_toan", None)
        return r

    def xuat_hang(self, trip, dong, *, ngay):
        """Lưu phiếu giao → thay phần xuất kho hàng của phiếu bên trang kế toán (bên đó kiểm tồn lô)."""
        if KQ.bat():
            return KHD.xuat(self.db, trip, dong, ngay, getattr(self.nguoi, "full_name", None))
        r = KT.goi(self.db, "POST", "/api/lien-thong/kho-hang/xuat", {
            "trip_id": trip.id, "trip_doc_no": trip.doc_no, "ngay": ngay.isoformat() if ngay else None, "dong": dong,
            "company": trip.company, "ma_hang_gui": _ma_hang_gui(self.db)}, nguoi=self.nguoi)
        self.da_xuat.append(("hh_xuat", (trip.id, trip.doc_no, trip.company, ngay, r.get("cu") or [])))
        self.db.info.pop("_hh_ke_toan", None)
        return r

    def huy_xuat(self, move_id, khoa=None):
        """Trả lại một lần xuất cũ (bỏ phiếu bán…) — làm ngay; bên này hỏng sau đó thì không xuất lại được, báo rõ.
        Kho QLSX cần `khoa` ("trip_expense:<mã dòng>") để dựng SourceRef phiếu xuất cần huỷ."""
        return huy_xuat(self.db, self.nguoi, move_id=move_id, khoa=khoa)

    def _huy_het(self):
        for loai, mv in reversed(self.da_xuat):
            try:
                if loai == "qlsx":
                    KQ.huy(self.db, mv, "Trang điều xe lưu hỏng sau khi xuất — trả lại kho")
                elif loai == "hh_nhap":
                    KT.goi(self.db, "POST", "/api/lien-thong/kho-hang/huy-nhap", {"trip_id": mv}, nguoi=self.nguoi)
                elif loai == "hh_xuat":
                    tid, so, cty, ngay, cu = mv
                    KT.goi(self.db, "POST", "/api/lien-thong/kho-hang/xuat", {
                        "trip_id": tid, "trip_doc_no": so, "company": cty, "ngay": ngay.isoformat() if ngay else None,
                        "dong": cu, "khoi_phuc": True}, nguoi=self.nguoi)
                else:
                    (huy_xuat_dau if loai == "dau" else huy_xuat)(self.db, self.nguoi, move_id=mv)
            except Exception as e:  # noqa: BLE001 — không huỷ được thì ghi lại để đối chiếu, vẫn báo lỗi gốc
                _nk.error("KHÔNG huỷ được lần xuất %s bên trang kế toán sau khi bên này lưu hỏng: %s", mv, e)

    def __enter__(self):
        return self

    def __exit__(self, loai, loi, vet):
        if loai is None:
            try:
                self.db.commit()
                return False
            except Exception:
                self.db.rollback()
                self._huy_het()
                raise
        self.db.rollback()
        self._huy_het()
        return False
