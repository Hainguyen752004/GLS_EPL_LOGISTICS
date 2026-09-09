# -*- coding: utf-8 -*-
"""Phieu THU va phieu CHI, gan vao LENH GIAO HANG.

Chu du an mo ta viec nay: *"cac chuc nang tao phieu thu phieu chi, vi du chi cho
cai DO 1 thi can nhung gi la phieu chi xang dau cac thu"*.

BA TANG cua he thong, theo dung dinh nghia cua anh, quyet dinh moi lua chon o
day:

    Bao gia (QT) = thoa thuan voi khach: tuyen nao, loai xe gi, gia bao nhieu.
    DO           = mot lenh giao hang cu the. DO la thu khach yeu cau.
    Trip         = mot chuyen xe that. Trip la thu cong ty to chuc de thuc hien DO.

Cong no khach di theo DO, nen PHIEU DI THEO DO. Nhung chi phi thi phat sinh o
tang CHUYEN — mot chuyen cho hai DO thi xang dau va BOT la cua ca chuyen. Nen
ham `goi_y_phieu_chi` phan bo chi phi chuyen ve tung DO, va no NOI RO da phan bo
theo cai gi chu khong am tham chia.
"""
import datetime as dt
import uuid
from decimal import Decimal

from models import (DeliveryOrder, DOVoucher, DOVoucherLine, FreightActualCost,
                    FreightChargeItem, TransportTrip, TransportTripLeg,
                    TripDeliveryOrder)
from services.errors import DomainError, conflict

#: Dung DUNG danh sach cua `FreightChargeItem`. Mot danh sach rieng o day se troi
#: khoi no, va luc do he cong no doi chieu hai ben khong khop.
KHOAN_MUC = ("fuel", "toll", "driver", "yard", "waiting", "loading", "unloading",
             "carrier_base", "surcharge", "discount", "other")

#: Ten tieng Viet de hien tren phieu. Chi la NHAN, khong phai nguon su that —
#: nguon su that la ma o tren.
TEN_KHOAN_MUC = {
    "fuel": "Chi phí xăng dầu",
    "toll": "Phí cầu đường / BOT",
    "driver": "Phụ cấp chuyến tài xế",
    "yard": "Phí bãi & lưu kho",
    "waiting": "Phí chờ",
    "loading": "Phí bốc hàng",
    "unloading": "Phí dỡ hàng",
    "carrier_base": "Cước nhà xe thuê ngoài",
    "surcharge": "Phụ phí",
    "discount": "Giảm trừ",
    "other": "Khoản khác",
}

LOAI_PHIEU = ("thu", "chi")
CACH_TRA = ("cash", "bank_transfer", "credit", "other")

#: Khoa cua CONG THUC GIA THANH -> ma khoan muc.
#:
#: Cong thuc dung bo khoa rieng cua no (`js/formula-model.js`): fuel, driver,
#: toll, `wh` cho phi bai & luu kho, `rate` cho cuoc thu khach. Ba khoa dau
#: trung ten voi `charge_type`, nhung `wh` thi khong — no la `yard`.
KHOA_CONG_THUC = {
    "fuel": "fuel",
    "driver": "driver",
    "toll": "toll",
    "wh": "yard",
    "yard": "yard",
    "rate": "carrier_base",     # cuoc — chi xuat hien o phieu THU
}

#: Nhan tieng Viet -> ma khoan muc, dung khi ben goi chi gui TEN chu khong gui khoa.
#:
#: Doi chieu theo tu khoa chu khong theo chuoi day du: nhan that co the la
#: "Chi phi xang dau /km" hay "Chi phí xăng dầu" tuy man hinh.
TU_KHOA_NHAN = (
    ("xăng", "fuel"), ("dầu", "fuel"), ("nhiên liệu", "fuel"),
    ("cầu đường", "toll"), ("bot", "toll"), ("phí đường", "toll"),
    ("tài xế", "driver"), ("phụ cấp", "driver"), ("lương", "driver"),
    ("bãi", "yard"), ("lưu kho", "yard"), ("kho", "yard"),
    ("bốc", "loading"), ("xếp hàng", "loading"),
    ("dỡ", "unloading"), ("hạ hàng", "unloading"),
    ("chờ", "waiting"), ("lưu ca", "waiting"),
    ("thuê ngoài", "carrier_base"), ("nhà xe", "carrier_base"),
    ("phụ phí", "surcharge"),
    ("giảm", "discount"), ("chiết khấu", "discount"),
)


def khoan_muc_tu(khoa=None, ten=None, mac_dinh="other"):
    """Suy ra ma KHOAN MUC tu khoa cong thuc hoac tu ten hien thi.

    VI SAO CAN HAM NAY. Duong lap bang chi phi thuc te truoc day VIET CUNG
    `charge_type="other"` cho MOI dong. Ten that van con o `description`
    ("Chi phi xang dau /km"), nhung ma phan loai — thu duy nhat may doc duoc —
    bi bo di. Nen he cong no khong tach duoc xang dau voi cau duong: do duoc
    tren du lieu demo that, ca bon dong deu ra "Khoan khac".

    Thu tu tin cay: KHOA cong thuc truoc (tuong minh), roi den TEN (phai doan),
    cuoi cung la `other`. Doan theo ten la duong doi lui cho nhung ben goi chua
    gui khoa — khong phai duong chinh, va no khong bao gio ghi de mot khoa da co.

    Khoan muc do NGUOI DUNG TU THEM tren man cong thuc thi khong co khoa nao
    quen biet; luc do ho phai tu chon khoan muc, va o chinh la viec cua giao
    dien. Ham nay khong doan bua cho chung.
    """
    ma = str(khoa or "").strip().lower()
    if ma in KHOAN_MUC:
        return ma
    if ma in KHOA_CONG_THUC:
        return KHOA_CONG_THUC[ma]
    chu = str(ten or "").strip().lower()
    if chu:
        for tu, km in TU_KHOA_NHAN:
            if tu in chu:
                return km
    return mac_dinh if mac_dinh in KHOAN_MUC else "other"

#: Khoan muc phat sinh o tang CHUYEN, phai phan bo ve tung DO.
#:
#: Xang dau va cau duong ti le voi DUONG CHAY, phu cap tai xe la cua ca chuyen.
#: Nhung khoan con lai (boc, do, cho, bai) gan voi TUNG LO HANG nen khong phan
#: bo — chung thuoc dung mot DO.
KHOAN_MUC_CHUNG_CHUYEN = ("fuel", "toll", "driver")


def _tien(x):
    try:
        return Decimal(str(x or 0))
    except Exception:
        return Decimal("0")


def _dep_tien(x):
    return "{:,.0f}".format(float(x or 0)).replace(",", ".")


def _ma_moi(tien_to):
    return "%s-%s" % (tien_to, uuid.uuid4().hex[:10].upper())


def _so_phieu_moi(db, kind, ngay):
    """So phieu de doc va de tra cuu: PC-2026-09-0007 / PT-2026-09-0003.

    Dem theo THANG chu khong theo tat ca: mot so chay tang mai mai thi den cuoi
    nam thanh nam chu so va khong ai doc duoc. Ke toan Viet Nam cung danh so lai
    theo ky.
    """
    tien_to = "PC" if kind == "chi" else "PT"
    dau = "%s-%04d-%02d-" % (tien_to, ngay.year, ngay.month)
    da_co = (db.query(DOVoucher.voucher_no)
             .filter(DOVoucher.voucher_no.like(dau + "%")).all())
    lon_nhat = 0
    for (so,) in da_co:
        duoi = str(so or "").rsplit("-", 1)[-1]
        if duoi.isdigit():
            lon_nhat = max(lon_nhat, int(duoi))
    return "%s%04d" % (dau, lon_nhat + 1)


# ===========================================================================
# TAO / DOC / GHI SO
# ===========================================================================

def tao_phieu(db, data, actor="system"):
    """Tao mot phieu thu hoac phieu chi cho mot lenh giao hang.

    HINH DANG PHIEU: chu du an chot "ca hai, nguoi dung chon". Mot dong la phieu
    theo tung khoan muc ("phieu chi xang dau"); nhieu dong la phieu gop khi tra
    cung mot lan cho cung mot nguoi. Ham nay khong ap dat hinh nao — nguoi goi
    truyen bao nhieu dong thi ra phieu bao nhieu dong.
    """
    ma_do = str(data.get("do_id") or "").strip()
    do = db.query(DeliveryOrder).filter(DeliveryOrder.id == ma_do).first()
    if not do:
        raise DomainError("DELIVERY_ORDER_NOT_FOUND",
                          "Không tìm thấy lệnh giao hàng %s. Phiếu thu/chi phải "
                          "gắn vào một lệnh giao hàng." % (ma_do or "(trống)"), 404)

    kind = str(data.get("kind") or "").strip().lower()
    if kind not in LOAI_PHIEU:
        raise DomainError("INVALID_VOUCHER_KIND",
                          "Loại phiếu phải là 'thu' hoặc 'chi', nhận được %r."
                          % data.get("kind"), 422)

    cach_tra = str(data.get("payment_method") or "cash").strip().lower()
    if cach_tra not in CACH_TRA:
        raise DomainError("INVALID_PAYMENT_METHOD",
                          "Hình thức thanh toán phải là một trong: %s."
                          % ", ".join(CACH_TRA), 422)

    cac_dong = [d for d in (data.get("lines") or []) if isinstance(d, dict)]
    if not cac_dong:
        raise DomainError("VOUCHER_LINES_REQUIRED",
                          "Phiếu phải có ít nhất một dòng khoản mục. Một phiếu "
                          "không có dòng nào thì không nói được là thu/chi cho "
                          "việc gì.", 422)

    ngay = _doc_ngay(data.get("voucher_date")) or dt.date.today()
    phieu = DOVoucher(
        id=data.get("id") or _ma_moi("PHIEU"),
        voucher_no=(data.get("voucher_no") or "").strip() or _so_phieu_moi(db, kind, ngay),
        kind=kind,
        do_id=do.id,
        trip_id=(data.get("trip_id") or None) or _chuyen_cua_do(db, do.id),
        voucher_date=ngay,
        payment_method=cach_tra,
        counterparty=(data.get("counterparty") or "").strip() or None,
        status="draft",
        currency_code=(data.get("currency_code") or "VND").strip().upper(),
        note=(data.get("note") or "").strip() or None,
        created_by=actor, updated_by=actor,
    )

    tong = Decimal("0")
    for i, d in enumerate(cac_dong, start=1):
        km = str(d.get("charge_type") or "").strip().lower()
        if km not in KHOAN_MUC:
            raise DomainError("INVALID_CHARGE_TYPE",
                              "Dòng %d: khoản mục %r không có trong danh sách. "
                              "Danh sách hợp lệ: %s." % (i, d.get("charge_type"),
                                                         ", ".join(KHOAN_MUC)), 422)
        so_tien = _tien(d.get("amount"))
        if so_tien < 0:
            raise DomainError("INVALID_AMOUNT",
                              "Dòng %d: số tiền không được âm. Muốn ghi giảm trừ "
                              "thì dùng khoản mục 'discount'." % i, 422)
        phieu.lines.append(DOVoucherLine(
            id=_ma_moi("PHDONG"), charge_type=km,
            description=(d.get("description") or "").strip()
                        or TEN_KHOAN_MUC.get(km, km),
            amount=so_tien,
            note=(d.get("note") or "").strip() or None,
        ))
        tong += so_tien

    if tong <= 0:
        raise DomainError("VOUCHER_TOTAL_REQUIRED",
                          "Tổng tiền của phiếu phải lớn hơn 0. Mọi dòng đang là "
                          "0 đồng nên phiếu này không ghi nhận việc gì.", 422)
    phieu.total_amount = tong

    db.add(phieu)
    db.flush()
    return phieu


def danh_sach_phieu(db, do_id=None, kind=None, trip_id=None):
    q = db.query(DOVoucher)
    if do_id:
        q = q.filter(DOVoucher.do_id == do_id)
    if trip_id:
        q = q.filter(DOVoucher.trip_id == trip_id)
    if kind:
        q = q.filter(DOVoucher.kind == kind)
    return q.order_by(DOVoucher.voucher_date.desc(), DOVoucher.voucher_no.desc()).all()


def mot_phieu(db, ma):
    phieu = db.query(DOVoucher).filter(DOVoucher.id == ma).first()
    if not phieu:
        raise DomainError("VOUCHER_NOT_FOUND", "Không tìm thấy phiếu %s." % ma, 404)
    return phieu


def ghi_so(db, ma, actor="system"):
    """Ghi so mot phieu: `draft` -> `posted`.

    Phieu da ghi so thi KHONG sua duoc nua — do la diem khong quay lai duoc, vi
    tu day so tien di vao cong no. Muon sua thi huy phieu roi lap phieu moi, de
    con dau vet cua ca hai.
    """
    phieu = mot_phieu(db, ma)
    if phieu.status == "posted":
        raise conflict("VOUCHER_ALREADY_POSTED",
                       "Phiếu %s đã ghi sổ. Muốn sửa thì huỷ phiếu rồi lập phiếu "
                       "mới — sửa một phiếu đã ghi sổ là xoá dấu vết của con số "
                       "đã vào công nợ." % phieu.voucher_no)
    if phieu.status == "cancelled":
        raise conflict("VOUCHER_CANCELLED",
                       "Phiếu %s đã huỷ, không ghi sổ được." % phieu.voucher_no)
    phieu.status = "posted"
    phieu.updated_by = actor
    phieu.updated_at = dt.datetime.utcnow()
    phieu.version = (phieu.version or 1) + 1
    db.flush()
    return phieu


def huy_phieu(db, ma, ly_do, actor="system"):
    phieu = mot_phieu(db, ma)
    if phieu.status == "cancelled":
        return phieu
    ly_do = (ly_do or "").strip()
    if not ly_do:
        raise DomainError("CANCEL_REASON_REQUIRED",
                          "Huỷ phiếu phải ghi lý do. Một phiếu bị huỷ mà không "
                          "ai biết vì sao thì lần đối soát sau không giải thích "
                          "được khoản tiền đó.", 422)
    phieu.status = "cancelled"
    phieu.note = ((phieu.note or "") + "\n[HUỶ] " + ly_do).strip()
    phieu.updated_by = actor
    phieu.updated_at = dt.datetime.utcnow()
    phieu.version = (phieu.version or 1) + 1
    db.flush()
    return phieu


# ===========================================================================
# GOI Y PHIEU CHI TU CHI PHI THUC TE
# ===========================================================================

def _chuyen_cua_do(db, do_id):
    hang = (db.query(TripDeliveryOrder.trip_id)
            .filter(TripDeliveryOrder.do_id == do_id).first())
    return hang[0] if hang else None


def _km_theo_do(db, trip_id):
    """So km cua tung DO trong mot chuyen, doc tu cac CHANG.

    `TransportTripLeg` co ca `do_id` lan `distance_km`, nen day la con so THAT
    chu khong phai mot uoc luong.
    """
    ra = {}
    for do_id, km in (db.query(TransportTripLeg.do_id, TransportTripLeg.distance_km)
                      .filter(TransportTripLeg.trip_id == trip_id).all()):
        if not do_id:
            continue
        ra[do_id] = ra.get(do_id, Decimal("0")) + _tien(km)
    return ra


def goi_y_phieu_chi(db, do_id):
    """Tra loi cau "chi cho DO nay thi can nhung phieu gi".

    Doc bang chi phi THUC TE cua chuyen dang cho DO nay, roi:

      · Khoan muc PHAT SINH O TANG CHUYEN (`fuel`, `toll`, `driver`) thi PHAN BO
        ve tung DO theo SO KM cua tung DO trong chuyen. Xang dau va cau duong ti
        le voi duong chay chu khong ti le voi hang nang; chia deu thi mot DO di
        5 km phai ganh nhu DO di 100 km, chia theo tan thi mot lo nhe ma di xa
        lai duoc ganh nhe.
      · Khoan muc con lai (boc, do, cho, bai) gan voi TUNG LO HANG nen khong
        phan bo — chung thuoc dung mot DO.

    Moi dong tra ve NOI RO da phan bo theo cai gi va ti le bao nhieu. Mot con so
    duoc chia ma khong noi cach chia thi nguoi doi soat khong kiem lai duoc, va
    khong kiem lai duoc thi ho khong dam dung.

    KHONG tu tao phieu. Ham nay chi GOI Y; nguoi dung xem, sua, roi bam tao.
    """
    do = db.query(DeliveryOrder).filter(DeliveryOrder.id == do_id).first()
    if not do:
        raise DomainError("DELIVERY_ORDER_NOT_FOUND",
                          "Không tìm thấy lệnh giao hàng %s." % do_id, 404)

    trip_id = _chuyen_cua_do(db, do_id)
    if not trip_id:
        return {"do_id": do_id, "trip_id": None, "cac_dong": [],
                "viec_con_thieu": ["Lệnh giao hàng này chưa thuộc chuyến nào, nên "
                                   "chưa có chi phí thực tế để gợi ý."]}

    cost = (db.query(FreightActualCost)
            .filter(FreightActualCost.trip_id == trip_id,
                    FreightActualCost.is_active == True)  # noqa: E712
            .order_by(FreightActualCost.created_at.desc()).first())
    if not cost:
        return {"do_id": do_id, "trip_id": trip_id, "cac_dong": [],
                "viec_con_thieu": ["Chuyến %s chưa có bảng chi phí thực tế. Lập "
                                   "bảng chi phí trước rồi mới gợi ý được phiếu "
                                   "chi." % trip_id]}

    km = _km_theo_do(db, trip_id)
    tong_km = sum(km.values()) or Decimal("0")
    km_do = km.get(do_id, Decimal("0"))
    # Khong co so km thi chia DEU va NOI RO la chia deu — im lang chia deu roi
    # de nguoi doi soat tu doan la cach chac chan gay tranh chap.
    if tong_km > 0:
        ti_le = km_do / tong_km
        cach_chia = "theo km (%s/%s km)" % (_dep_tien(km_do), _dep_tien(tong_km))
    else:
        so_do = max(len(set(x[0] for x in db.query(TripDeliveryOrder.do_id)
                            .filter(TripDeliveryOrder.trip_id == trip_id).all())), 1)
        ti_le = Decimal("1") / Decimal(so_do)
        cach_chia = "chia đều cho %d lệnh giao hàng (chặng chưa khai số km)" % so_do

    cac_dong, thieu = [], []
    for item in (db.query(FreightChargeItem)
                 .filter(FreightChargeItem.cost_id == cost.id).all()):
        goc = _tien(item.actual_amount) or _tien(item.original_amount)
        if goc <= 0:
            continue
        chung = item.charge_type in KHOAN_MUC_CHUNG_CHUYEN
        so_tien = (goc * ti_le) if chung else goc
        cac_dong.append({
            "charge_type": item.charge_type,
            "ten_khoan_muc": TEN_KHOAN_MUC.get(item.charge_type, item.charge_type),
            "description": item.description or TEN_KHOAN_MUC.get(item.charge_type),
            "so_tien_chuyen": float(goc),
            "amount": float(round(so_tien, 0)),
            "phan_bo": cach_chia if chung else "riêng của lệnh giao hàng này",
            "la_chi_phi_chung": chung,
        })
    if tong_km <= 0:
        thieu.append("Các chặng của chuyến %s chưa khai số km, nên chi phí chung "
                     "đang chia đều thay vì chia theo km. Khai số km ở màn Tuyến "
                     "đường để con số đúng hơn." % trip_id)

    return {
        "do_id": do_id, "trip_id": trip_id, "cost_id": cost.id,
        "cach_phan_bo": cach_chia,
        "tong_tien": float(sum(Decimal(str(d["amount"])) for d in cac_dong)),
        "cac_dong": cac_dong,
        "viec_con_thieu": thieu,
    }


def _doc_ngay(gia_tri):
    if not gia_tri:
        return None
    if isinstance(gia_tri, dt.date) and not isinstance(gia_tri, dt.datetime):
        return gia_tri
    if isinstance(gia_tri, dt.datetime):
        return gia_tri.date()
    chu = str(gia_tri).strip()[:10]
    try:
        return dt.date.fromisoformat(chu)
    except ValueError:
        raise DomainError("INVALID_VOUCHER_DATE",
                          "Ngày phiếu %r không đọc được. Dùng dạng YYYY-MM-DD."
                          % gia_tri, 422)
