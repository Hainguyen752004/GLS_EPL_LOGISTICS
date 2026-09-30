# -*- coding: utf-8 -*-
"""Sổ chứng từ — mỗi bước nghiệp vụ sinh ra một BẢN GHI chứng từ, để bên kế toán (module của anh
Khang) kéo về tạo phiếu thu, phiếu chi, phiếu nhập kho, phiếu xuất kho.

Đây KHÔNG phải sổ kế toán. Bên mình không ghi bút toán, không cộng sổ, không tính công nợ — đó là
việc của module anh Khang. Bên mình chỉ ghi lại: chứng từ gì, sinh lúc nào, từ phiếu nào, của đối
tượng nào, bao nhiêu tiền, và HAI VẾ ĐỊNH KHOẢN GỢI Ý theo đúng quy trình họ viết (625/371, 614/402,
1211/70…). Vế nào quy trình của họ không ghi mã (tiền mặt, ngân hàng) thì để trống mã và ghi tên,
KHÔNG bịa mã.

Mỗi chứng từ có `da_day` = đã được bên kế toán nhận chưa. Bên kia kéo `GET /api/chung-tu?chua_day=1`,
xử lý xong gọi `POST /api/chung-tu/{id}/da-day`. Một chứng từ chỉ sinh MỘT lần cho một nguồn
(nguon_bang + nguon_id), gọi lại không sinh trùng.
"""
import datetime as dt
import json

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from models import ChungTu

# ------------------------------------------------------------------ danh mục loại chứng từ
# ma → (tên Việt, tên Lào, có định khoản không)
LOAI = {
    "DO":     ("Phiếu xuất xe · đề nghị xuất xe", "ໃບເບີກລົດ · ໃບສະເໜີເບີກລົດ", False),   # DO mang cả hai tên (30/09)
    "PLNL":   ("Phiếu đề nghị xuất kho nhiên liệu", "ໃບສະເໜີເບີກນໍ້າມັນອອກສາງ", False),
    "PTU":    ("Phiếu đề nghị tạm ứng", "ໃບສະເໜີເບີກເງິນລ່ວງໜ້າ", False),
    # Đề nghị THU (sếp 30/09): DO xong (xe về, có POD, khoá phiếu) → gửi bên công nợ (anh Tune) lập SO, hoá đơn, thu tiền.
    # Không định khoản: bên mình không ghi công nợ.
    "PDT":    ("Phiếu đề nghị thu", "ໃບສະເໜີຮັບເງິນ", False),
    "PXK_NL": ("Phiếu xuất kho nhiên liệu", "ໃບເບີກນໍ້າມັນອອກສາງ", True),
    "PXK_PT": ("Phiếu xuất kho phụ tùng", "ໃບເບີກອະໄຫຼ່ອອກສາງ", True),
    "PNK_NL": ("Phiếu nhập kho nhiên liệu", "ໃບຮັບນໍ້າມັນເຂົ້າສາງ", True),
    "PNK_PT": ("Phiếu nhập kho phụ tùng", "ໃບຮັບອະໄຫຼ່ເຂົ້າສາງ", True),
    # Chuyển dầu giữa hai kho của EPL (anh Khampla A3): tài sản vẫn nằm trong 1371 nên KHÔNG có định khoản —
    # tờ này để bên kế toán biết dầu đã đổi chỗ, không sinh bút toán.
    "CK_NL":  ("Phiếu chuyển kho nhiên liệu", "ໃບໂອນນໍ້າມັນລະຫວ່າງສາງ", False),
    # Hàng (quặng) nằm bãi giữa hai chặng: DO gom về thì nhập kho, DO giao lấy đi thì xuất kho.
    "PNK_HH": ("Phiếu nhập kho hàng", "ໃບຮັບສິນຄ້າເຂົ້າສາງ", True),
    "PXK_HH": ("Phiếu xuất kho hàng", "ໃບເບີກສິນຄ້າອອກສາງ", True),
    "DC_HH":  ("Phiếu điều chỉnh kho hàng", "ໃບປັບປຸງສາງສິນຄ້າ", True),
    "PC_TU":  ("Phiếu chi theo đề nghị tạm ứng", "ໃບຈ່າຍເງິນຕາມໃບສະເໜີເບີກເງິນລ່ວງໜ້າ", True),   # chi thật đi ra từ phiếu đề nghị (29/09)
    "PC_SC":  ("Phiếu chi sửa chữa · chi khác", "ໃບຈ່າຍສ້ອມແປງ · ອື່ນໆ", True),
    "PC_NCC": ("Phiếu chi trả nhà cung cấp", "ໃບຈ່າຍຜູ້ສະໜອງ", True),
    "PC_CX":  ("Phiếu chi trả chủ xe liên kết", "ໃບຈ່າຍເຈົ້າຂອງລົດຮ່ວມ", True),
    "HD":     ("Hoá đơn vận chuyển", "ໃບເກັບເງິນຂົນສົ່ງ", True),
    "PT":     ("Phiếu thu tiền khách", "ໃບຮັບເງິນລູກຄ້າ", True),
    "TT_CHI": ("Tất toán tài xế · chi bù", "ສະສາງໂຊເຟີ · ຈ່າຍເພີ່ມ", True),
    "TT_THU": ("Tất toán tài xế · thu hoàn", "ສະສາງໂຊເຟີ · ຮັບຄືນ", True),
    # bán phụ tùng · xăng dầu cho bên ngoài (không phải chi cho chuyến)
    "PXK_BAN": ("Phiếu xuất kho bán hàng", "ໃບເບີກສິນຄ້າຂາຍ", True),
    "HD_BAN":  ("Hoá đơn bán hàng", "ໃບເກັບເງິນຂາຍສິນຄ້າ", True),
    "PT_BAN":  ("Phiếu thu bán hàng", "ໃບຮັບເງິນຂາຍສິນຄ້າ", True),
}

# Mã tài khoản anh Khampla trả lời 22/09/2026, theo sá-la-ban kế toán doanh nghiệp Lào:
#   kho 137 (mẹ) / 1371 (con) · nhà cung cấp 402 (mẹ) / 4021 (con, tách theo từng NCC)
#   tiền mặt Kíp 1011 · tiền mặt ngoại tệ 1012 · ngân hàng Kíp 1021 · ngân hàng ngoại tệ 1022
# Ghi sổ theo MÃ CON vì đó là cấp hạch toán; mã mẹ chỉ để cộng dồn. Anh Khang muốn khác thì đổi ở đây.
KHO = ("1371", "Kho hàng, vật tư (137 · 1371)")
# Mã hàng khách gửi: bên kế toán CHƯA cấp — vế mang tên nhưng mã None cho tới khi Sếp điền ở cấu hình.
HANG_GUI = (None, "Hàng khách gửi giữ hộ — ngoài bảng (mã do bên kế toán cấp)")
# Giá vốn hàng bán: chủ dự án chốt 607 ngày 23/09 (sá-la-ban Lào: 607 giá vốn hàng bán). Cấu hình `ma_gia_von`
# vẫn đổi được nếu anh Khang cấp mã khác.
GIA_VON = ("607", "Giá vốn hàng bán")
NCC = ("4021", "Phải trả nhà cung cấp (402 · 4021, tách theo nhà cung cấp)")
MA_TIEN = {
    ("cash", True): ("1011", "Tiền mặt bằng Kíp"),
    ("cash", False): ("1012", "Tiền mặt ngoại tệ"),
    ("bank", True): ("1021", "Tiền gửi ngân hàng bằng Kíp"),
    ("bank", False): ("1022", "Tiền gửi ngân hàng ngoại tệ"),
}


def ma_tien(phuong_thuc=None, tien_te=None):
    """Vế tiền chọn theo CÁCH thu/chi (mặt · ngân hàng) và TIỀN TỆ (Kíp · khác).

    Quỹ tiền mặt Thà Bốc và Thủ quỹ Viêng Chăn đều là quỹ tiền mặt đúng tên vai của họ, nên không
    ghi cách chi thì hiểu là tiền mặt. `offset` (cấn trừ) và `other` không phải tiền vào tay nên xếp
    vào ngân hàng — bên kế toán đối chiếu lại nếu cần."""
    pt = "bank" if (phuong_thuc or "cash") in ("bank", "offset", "other") else "cash"
    return MA_TIEN[(pt, (tien_te or "LAK").upper() == "LAK")]


def dinh_khoan(loai, company="EPL", section=None, tien_te=None, phuong_thuc=None):
    """Hai vế gợi ý theo đúng bảng định khoản trong quy trình của họ. Trả (no, no_ten, co, co_ten)."""
    chi_phi = ("4022", "Chi hộ xe liên kết") if company == "joint" else (
        ("614", "Chi phí sửa chữa") if section == "repair" else ("625", "Chi phí vận chuyển"))
    TIEN = ma_tien(phuong_thuc, tien_te)
    b = {
        "PXK_NL": (chi_phi, KHO),
        "PXK_PT": (chi_phi, KHO),
        "PNK_NL": (KHO, NCC),
        "PNK_PT": (KHO, NCC),
        # QUẶNG CỦA KHÁCH nằm bãi mình giữ hộ (chốt 22/09): KHÔNG phải tài sản của EPL nên không ghi
        # vào kho 1371 — ghi thế là tồn kho EPL phình lên bằng hàng của người khác. Nó là khoản
        # NGOÀI BẢNG (ghi đơn, một vế): nhập thì Nợ, xuất thì Có, cùng một mã do bên kế toán cấp
        # (đặt ở màn Chứng từ → Cấu hình, khoá `ma_hang_khach_gui`); chưa có mã thì để trống, tấn
        # vẫn đi đủ trong payload để bên kia đối chiếu.
        "PNK_HH": (HANG_GUI, (None, None)),
        "PXK_HH": ((None, None), HANG_GUI),
        # Điều chỉnh: tăng ghi như nhập, giảm ghi như xuất — chiều nào thì payload nói rõ.
        "DC_HH":  (HANG_GUI, HANG_GUI),
        "PC_TU":  (chi_phi, TIEN),
        "PC_SC":  (chi_phi, TIEN),
        "PC_NCC": (NCC, TIEN),
        "PC_CX":  (("4022", "Phải trả chủ xe liên kết"), TIEN),
        "HD":     (("1211", "Phải thu khách hàng"), ("70", "Doanh thu bán hàng và dịch vụ")),
        "PT":     (TIEN, ("1211", "Phải thu khách hàng")),
        "TT_CHI": (chi_phi, TIEN),
        "TT_THU": (TIEN, chi_phi),
        "PXK_BAN": (GIA_VON, KHO),
        "HD_BAN":  (("1211", "Phải thu khách hàng"), ("70", "Doanh thu bán hàng và dịch vụ")),
        "PT_BAN":  (TIEN, ("1211", "Phải thu khách hàng")),
    }.get(loai)
    if not b:
        return (None, None, None, None)
    (no, no_ten), (co, co_ten) = b
    return (no, no_ten, co, co_ten)


def _dien_ma_cau_hinh(db, loai, no, co):
    """Điền hai mã bên kế toán cấp SAU (Sếp gõ ở màn Chứng từ → Cấu hình) vào đúng vế còn trống.
    Không có cấu hình thì vế đó vẫn None kèm tên — bên kia đọc tên mà biết."""
    from services.day_ke_toan import cau_hinh
    if loai in ("PNK_HH", "PXK_HH", "DC_HH"):
        ma = cau_hinh(db, "ma_hang_khach_gui")
        if ma:
            if loai != "PXK_HH" and no is None: no = ma
            if loai != "PNK_HH" and co is None: co = ma
    elif loai == "PXK_BAN":
        ma = cau_hinh(db, "ma_gia_von")
        if ma:
            no = ma
    return no, co


def _so_moi(db, loai, ngay):
    """Số chứng từ: LOAI/YYMM/0001, đánh theo loại và theo tháng.

    Lấy SỐ LỚN NHẤT đang có rồi cộng một, chứ không đếm số dòng: đếm dòng thì sau khi rút một tờ
    chưa đối chiếu (xoá phiếu, bỏ chốt) số sẽ tụt lại và đụng số cũ.
    """
    tien_to = "%s/%s/" % (loai, ngay.strftime("%y%m"))
    cuoi = (db.query(ChungTu.so).filter(ChungTu.loai == loai, ChungTu.so.like(tien_to + "%"))
            .order_by(ChungTu.so.desc()).first())          # 4 chữ số có đệm 0 nên xếp chữ = xếp số
    n = 0
    if cuoi:
        try:
            n = int(str(cuoi[0]).rsplit("/", 1)[-1])
        except ValueError:
            n = 0
    return "%s%04d" % (tien_to, n + 1)


def tim(db, loai, nguon_bang, nguon_id):
    """Tờ chứng từ đã ghi cho một nguồn, hoặc None."""
    return (db.query(ChungTu).filter(ChungTu.loai == loai, ChungTu.nguon_bang == nguon_bang,
                                     ChungTu.nguon_id == str(nguon_id)).first())


def ghi(db, loai, *, nguon_bang, nguon_id, trip=None, ngay=None, doi_tuong_loai=None, doi_tuong_ten=None,
        tien=None, tien_te="LAK", tien_lak=None, section=None, mo_ta=None, by_user=None, payload=None,
        company=None, phuong_thuc=None):
    """Ghi MỘT chứng từ. Gọi lại với cùng (nguon_bang, nguon_id, loai) thì trả bản đã có, không sinh trùng."""
    if loai not in LOAI:
        raise ValueError("Không có loại chứng từ %s" % loai)
    cu = db.query(ChungTu).filter(ChungTu.loai == loai, ChungTu.nguon_bang == nguon_bang,
                                  ChungTu.nguon_id == str(nguon_id)).first()
    if cu:
        return cu
    ngay = ngay or dt.date.today()
    cty = company or (trip.company if trip is not None else "EPL")
    no, no_ten, co, co_ten = (dinh_khoan(loai, cty, section, tien_te, phuong_thuc) if LOAI[loai][2]
                              else (None, None, None, None))
    no, co = _dien_ma_cau_hinh(db, loai, no, co)
    if loai == "HD_BAN" and doi_tuong_loai == "chu_xe":
        # chủ xe mua ở quầy, trừ vào tiền trả: không phải khách nợ 1211 mà là GIẢM khoản phải trả chủ xe
        no, no_ten = "4022", "Phải trả chủ xe liên kết (trừ vào tiền trả)"
    thuoc_tinh = dict(loai=loai, ngay=ngay,
                      trip_id=trip.id if trip is not None else None,
                      trip_doc_no=trip.doc_no if trip is not None else None,
                      doi_tuong_loai=doi_tuong_loai, doi_tuong_ten=doi_tuong_ten,
                      tien=tien, tien_te=(tien_te or "LAK").upper(),
                      tien_lak=tien_lak if tien_lak is not None else (tien if (tien_te or "LAK").upper() == "LAK" else None),
                      no=no, no_ten=no_ten, co=co, co_ten=co_ten, mo_ta=mo_ta,
                      nguon_bang=nguon_bang, nguon_id=str(nguon_id), by_user=by_user,
                      payload=json.dumps(payload or {}, ensure_ascii=False, default=str))
    # Hai người cùng lúc (thủ kho hai kho, hàng đợi ngoại tuyến gửi lại) có thể cùng tính ra một số.
    # Ghi trong SAVEPOINT: đụng số thì lùi về chỗ đó, lấy số kế tiếp rồi ghi lại, không hỏng cả phiên.
    # Mỗi vòng dựng một đối tượng MỚI: sau khi savepoint lùi lại, đối tượng cũ đã bị gỡ khỏi phiên,
    # đụng vào nó (expunge, add lại) là InvalidRequestError — lỗi đó đã từng làm lần thử lại chết.
    for _lan in range(6):
        c = ChungTu(so=_so_moi(db, loai, ngay), **thuoc_tinh)
        try:
            with db.begin_nested():
                db.add(c)
                db.flush()
            return c
        except IntegrityError:
            continue
    raise HTTPException(409, {"ma": "TRUNG_SO_CHUNG_TU",
                              "loi": "Không cấp được số chứng từ %s, thử lại giúp em." % loai})


def rut(db, *, nguon_bang=None, nguon_id=None, trip_id=None):
    """Nguồn bị xoá (bỏ chốt tất toán, xoá phiếu thử, xoá dòng kho) → rút các tờ CHƯA đối chiếu của nó.
    Tờ đã đối chiếu thì giữ: bên kế toán đã nhận, rút đi là hai bên lệch nhau mà không ai biết."""
    q = db.query(ChungTu).filter(ChungTu.da_day.is_(False))
    if trip_id is not None:
        q = q.filter(ChungTu.trip_id == trip_id)
    else:
        q = q.filter(ChungTu.nguon_bang == nguon_bang, ChungTu.nguon_id == str(nguon_id))
    return q.delete(synchronize_session=False)


def xuat(c):
    try:
        pl = json.loads(c.payload) if c.payload else {}
    except ValueError:
        pl = {}
    ten = LOAI.get(c.loai, (c.loai, c.loai, False))
    return {"id": c.id, "loai": c.loai, "loai_ten": ten[0], "loai_ten_lo": ten[1], "so": c.so,
            "ngay": c.ngay.isoformat() if c.ngay else None,
            "trip_id": c.trip_id, "trip_doc_no": c.trip_doc_no,
            "doi_tuong_loai": c.doi_tuong_loai, "doi_tuong_ten": c.doi_tuong_ten,
            "tien": c.tien, "tien_te": c.tien_te, "tien_lak": c.tien_lak,
            "no": c.no, "no_ten": c.no_ten, "co": c.co, "co_ten": c.co_ten,
            "mo_ta": c.mo_ta, "nguon_bang": c.nguon_bang, "nguon_id": c.nguon_id,
            "by_user": c.by_user, "ts": c.ts.isoformat() if c.ts else None,
            "da_day": bool(c.da_day), "day_luc": c.day_luc.isoformat() if c.day_luc else None,
            "ma_ben_ke_toan": c.ma_ben_ke_toan, "loi_day": c.loi_day, "lan_thu": c.lan_thu or 0,
            "payload": pl}
