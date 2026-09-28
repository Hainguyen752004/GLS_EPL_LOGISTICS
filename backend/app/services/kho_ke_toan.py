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
"""
import logging

from services import goi_ke_toan as KT

_nk = logging.getLogger("epl_lao.kho_ke_toan")


def ds_phu_tung(db, nguoi=None):
    """Mọi phụ tùng (kể cả ngưng dùng) kèm tồn và giá bình quân hiện tại — hỏi thẳng trang kế toán, không đệm."""
    return KT.goi(db, "GET", "/api/lien-thong/phu-tung", nguoi=nguoi) or []


def gia_phu_tung(db, part_id):
    """Giá bình quân hiện tại của một phụ tùng (LAK). Một yêu cầu hỏi trang kế toán một lần."""
    bang = db.info.get("_pt_ke_toan")
    if bang is None:
        bang = db.info["_pt_ke_toan"] = {p["id"]: p for p in ds_phu_tung(db)}
    p = bang.get(part_id)
    return (p.get("unit_price") or 0) if p else 0


def huy_xuat(db, nguoi, move_id=None, khoa=None):
    return KT.goi(db, "POST", "/api/lien-thong/phu-tung/huy-xuat", {"move_id": move_id, "khoa": khoa}, nguoi=nguoi)


# ---------------------------------------------------------------- kho nhiên liệu (đợt 4, 28/09)
def kho_dau(db):
    """{place_id: {ton_lit, gia_bq}} của mọi kho dầu EPL — hỏi trang kế toán một lần mỗi yêu cầu."""
    bang = db.info.get("_dau_ke_toan")
    if bang is None:
        bang = db.info["_dau_ke_toan"] = KT.goi(db, "GET", "/api/lien-thong/nhien-lieu/kho") or {}
    return bang


def gia_dau(db, place_id):
    """Giá bình quân hiện tại (LAK/lít) của một kho dầu; trống = kho Thà Bốc."""
    from services.gia_von import kho_goc
    return ((kho_dau(db).get(place_id or kho_goc(db)) or {}).get("gia_bq")) or 0


def huy_xuat_dau(db, nguoi, move_id=None, khoa=None):
    return KT.goi(db, "POST", "/api/lien-thong/nhien-lieu/huy-xuat", {"move_id": move_id, "khoa": khoa}, nguoi=nguoi)


def web_ke_toan(db):
    """Địa chỉ trang kế toán để MỞ bằng trình duyệt / in vào mã QR phiếu lĩnh (màn Cấp phát ở đó).
    Cấu hình `ke_toan_web`; không đặt thì dùng địa chỉ API kế toán (cùng máy chủ phục vụ cả giao diện)."""
    from services import day_ke_toan as DK
    return (DK.cau_hinh(db, "ke_toan_web") or DK.cau_hinh(db, "ke_toan_api") or "").rstrip("/")


class GiaoDichKho:
    """Một lần lưu bên này có đụng kho bên kế toán. Xem ghi chú đầu tệp."""

    def __init__(self, db, nguoi):
        self.db, self.nguoi, self.da_xuat = db, nguoi, []

    def xuat_phu_tung(self, *, khoa, part_id, qty, ngay=None, gia=None, tien_te="LAK", ty_gia=1.0, truck_no=None,
                      trip_doc_no=None, expense_id=None, company="EPL", section="repair", mo_ta=None, note=None,
                      ghi_chung_tu=True, repair_order=None):
        r = KT.goi(self.db, "POST", "/api/lien-thong/phu-tung/xuat", {
            "khoa": khoa, "part_id": part_id, "qty": qty, "ngay": ngay.isoformat() if ngay else None, "gia": gia,
            "tien_te": tien_te, "ty_gia": ty_gia, "truck_no": truck_no, "trip_doc_no": trip_doc_no,
            "expense_id": expense_id, "company": company, "section": section, "mo_ta": mo_ta, "note": note,
            "ghi_chung_tu": ghi_chung_tu, "repair_order": repair_order}, nguoi=self.nguoi)
        self.da_xuat.append(("pt", r["move_id"]))
        return r

    def xuat_dau(self, *, khoa, place_id, qty_l, ngay=None, doc_no=None, truck_no=None, expense_id=None, voucher_id=None,
                 voucher_doc_no=None, trip_no=None, company="EPL", gia_du_phong=None, kiem_ton=False, ghi_chung_tu=True,
                 mo_ta=None, note=None):
        """Xuất dầu ở kho bên trang kế toán — giá bình quân của đúng kho lúc xuất; trả {move_id, unit_price…}."""
        r = KT.goi(self.db, "POST", "/api/lien-thong/nhien-lieu/xuat", {
            "khoa": khoa, "place_id": place_id, "qty_l": qty_l, "ngay": ngay.isoformat() if ngay else None, "doc_no": doc_no,
            "truck_no": truck_no, "expense_id": expense_id, "voucher_id": voucher_id, "voucher_doc_no": voucher_doc_no,
            "trip_no": trip_no, "company": company, "gia_du_phong": gia_du_phong, "kiem_ton": kiem_ton,
            "ghi_chung_tu": ghi_chung_tu, "mo_ta": mo_ta, "note": note}, nguoi=self.nguoi)
        self.da_xuat.append(("dau", r["move_id"]))
        return r

    def huy_xuat(self, move_id):
        """Trả lại một lần xuất cũ (bỏ phiếu bán…) — làm ngay; bên này hỏng sau đó thì không xuất lại được, báo rõ."""
        return huy_xuat(self.db, self.nguoi, move_id=move_id)

    def _huy_het(self):
        for loai, mv in self.da_xuat:
            try:
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
