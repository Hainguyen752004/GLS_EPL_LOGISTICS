# -*- coding: utf-8 -*-
"""BÚT TOÁN CHỜ GỬI — khoản sổ kế toán phải ghi mà KHÔNG đi qua tiền (chủ dự án chốt 01/10/2026: "toàn diện nhất, đúng Excel,
đúng nghiệp vụ").

Khoản đi qua tiền thì thành phiếu chi / thu bên hệ kế toán anh Tune (services/chi_tune.py, chi_muc_tune.py…). Khoản không qua
tiền — ghi nhận chi phí thuê xe, ghi nợ nhà cung cấp, quyết toán… — hệ anh Tune CHƯA có đường nhận (source chưa có chứng từ
"bút toán tổng hợp", hợp đồng kế toán mục 12.12.4). Bên em không đoán cấu trúc sổ cái bên đó để ghi thẳng, nên giữ bút toán ở
đây, ĐỦ hai vế từng dòng bằng mã thật (services/tai_khoan.py), chờ có API thì gửi — không mất khoản nào trong lúc chờ.

GIAO ƯỚC (module khác gọi — giữ cố định):

    ghi(db, nguon, ma_nguon, ngay, dong, dien_giai) -> ButToanCho | None
        nguon      ≤ 16 ký tự: loại nguồn — thue_xe · no_ncc · xuat_noi_bo · xuat_ban (khoá phiếu, ở đây) · nguồn khác do
                   module gọi tự đặt (tat_toan, ban_chu_xe)
        ma_nguon   ≤ 80 ký tự: mã bản ghi nguồn (thue_xe / no_ncc: Trip.id · xuat_noi_bo / xuat_ban: "dau:<mã lần xuất kho>"
                   hoặc "pt:<mã lần xuất kho>" — TripExpense.stock_move_id, mã dòng sổ kho bên kho tạm)
        ngay       date (hoặc chuỗi YYYY-MM-DD) — ngày hạch toán
        dong       [{"no": "621", "co": "4022", "tien": 1250.5, "ccy": "USD",
                     "doi_tuong": {"loai": "chu_xe", "ref_id": "<Owner.id>"} | None, "dien_giai": "…"}, …]
                   khoá thêm trong dòng (tien_lak, ty_gia, ref…) được giữ nguyên. Dòng tiền 0 bỏ qua; dòng sai dạng → ValueError.
        dien_giai  diễn giải chung
      Tuỳ chọn (từ khoá): trip_id=…, by_user=… .
      Chống trùng theo (nguon, ma_nguon): đã có bản chưa gửi (cho_gui, huy) → cập nhật số và sống lại thành cho_gui; bản đã gửi
      (da_gui) → trả nguyên, không đổi. Không còn dòng nào → huỷ bản chưa gửi (nếu có), trả bản đó hoặc None.

    huy(db, nguon, ma_nguon, by_user=None) -> ButToanCho | None
        Nguồn bị huỷ (mở khoá phiếu…): bản cho_gui → huy. Bản da_gui → đánh can_dao (chờ bút toán đảo khi bên kia có API).

    rut(db, nguon, ma_nguon, by_user=None) -> bool
        Nguồn bị bỏ hẳn (bỏ chốt tất toán…): chưa gửi → huy, True · không có → False · đã gửi → HTTPException 409 BUT_TOAN_DA_GUI.

    danh_sach(db, nguon=None, status=None, trip_id=None, tu=None, den=None, gioi_han=200) -> [ButToanCho]
    xuat(r, doc_no=None) -> dict

XUẤT KHO CHO CHUYẾN (chủ dự án 01/10: "xuất dầu là xuất nội bộ và còn là xuất bán") — cũng ghi lúc khoá phiếu
(ghi_khoa_phieu), một LẦN XUẤT một bút toán, ngày = ngày xuất thật (dong_xuat_kho):
    xuat_noi_bo   xe nhà: dầu kho Nợ 625 / Có 1371 · phụ tùng kho Nợ 614 / Có 1371 — giá vốn bình quân kho
    xuat_ban      xe thuê, EPL ứng: Nợ 4022 / Có 707 theo GIÁ BÁN (đối tượng chủ xe) + Nợ 607 / Có 1371 theo giá vốn
    xe thuê chủ xe tự trả: không có. Khác `ban_chu_xe` (services/tra_chu_xe.py): đó là phiếu BÁN Ở QUẦY của kho tạm, trừ
    riêng vào tiền trả (tinh_tru); còn đây là dòng kho trên phiếu xuất xe, trừ qua `ung_truoc` của tinh_phieu.

Hàm ở đây KHÔNG commit — người gọi commit cùng giao dịch của nghiệp vụ (khoá phiếu ghi bút toán trong cùng lần khoá).

Trạng thái: cho_gui (chờ gửi) · da_gui (bên kế toán đã nhận, có số chứng từ) · huy.

GỬI sang hệ anh Tune (services/gui_but_toan_tune.py) khi cờ QLSX_GUI_BUT_TOAN bật (mặc định tắt — bên đó cần áp script DB):
ghi xong là tự gửi (hỏng thì giữ cho_gui, ghi lỗi); huỷ / rút bản đã gửi là gửi bút toán đảo — đảo xong thì huy, chưa đảo
được thì can_dao (Gửi hết thử lại). Bản đã đảo mà nguồn ghi lại thì SourceRef mới "…-<phien>". Cờ tắt: như trước, chỉ xem.
"""
import datetime as dt
import json
import math

from sqlalchemy.exc import IntegrityError

from models import TRANG_THAI_BUT_TOAN, ButToanCho
from services import tai_khoan as TK
from services.tinh_toan import TIEN_TE, lam_tron

DAI_NGUON, DAI_MA_NGUON = 16, 80
# vai xem được bút toán chờ (GET /api/but-toan-cho, khối but_toan_cho trên phiếu): KT Thu/Chi VC (người khoá phiếu), KT Chi
# phí VC (người ghi sổ mục chi), Sếp. Bút toán mang tiền thuê xe liên kết — tiền bán, vai khác không thấy.
VAI_XEM = ("acct", "expacct", "admin")
# hai nguồn bút toán lúc KHOÁ PHIẾU (chủ dự án 01/10) — mở khoá thì huỷ cả hai
THUE_XE = "thue_xe"        # xe thuê: Nợ 621 chi phí vận chuyển / Có 4022 phải trả chủ xe, bằng tiền thuê
NO_NCC = "no_ncc"          # dòng chi ghi nợ nhà cung cấp: Nợ 625 · 614 (xe thuê 4022) / Có 4021
NGUON_KHOA_PHIEU = (THUE_XE, NO_NCC)
# XUẤT KHO cho chuyến (chủ dự án 01/10: "xuất dầu là xuất nội bộ và còn là xuất bán") — cũng ghi lúc khoá phiếu, nhưng MỘT
# LẦN XUẤT KHO một bút toán (ma_nguon "dau:<mã lần xuất>" · "pt:<mã lần xuất>" của kho tạm), để ngày chứng từ là ngày xuất thật
XUAT_NOI_BO = "xuat_noi_bo"  # xe nhà: dầu kho Nợ 625 / Có 1371 · phụ tùng kho Nợ 614 / Có 1371, theo giá vốn bình quân kho
XUAT_BAN = "xuat_ban"        # xe thuê, EPL ứng: Nợ 4022 / Có 707 theo GIÁ BÁN + Nợ 607 / Có 1371 theo giá vốn bình quân kho
NGUON_XUAT_KHO = (XUAT_NOI_BO, XUAT_BAN)


def _khoa(nguon, ma_nguon):
    n, m = str(nguon or "").strip(), str(ma_nguon or "").strip()
    if not n or len(n) > DAI_NGUON:
        raise ValueError("nguon phải có 1–%d ký tự, nhận %r" % (DAI_NGUON, nguon))
    if not m or len(m) > DAI_MA_NGUON:
        raise ValueError("ma_nguon phải có 1–%d ký tự, nhận %r" % (DAI_MA_NGUON, ma_nguon))
    return n, m


def _ngay(v):
    if isinstance(v, dt.datetime):
        return v.date()
    if isinstance(v, dt.date):
        return v
    try:
        return dt.date.fromisoformat(str(v or "")[:10])
    except ValueError:
        raise ValueError("ngay phải là date hoặc YYYY-MM-DD, nhận %r" % (v,))


def _chuan_dong(dong):
    """Kiểm từng dòng, làm tròn tiền theo tiền tệ (LAK, VND tròn đồng; tiền khác hai số lẻ), bỏ dòng tiền 0."""
    if dong is None:
        return []
    if not isinstance(dong, (list, tuple)):
        raise ValueError("dong phải là danh sách dòng")
    ra = []
    for i, d in enumerate(dong, 1):
        if not isinstance(d, dict):
            raise ValueError("dòng %d không phải dict" % i)
        no, co = str(d.get("no") or "").strip(), str(d.get("co") or "").strip()
        if not no or not co:
            raise ValueError("dòng %d thiếu vế Nợ hoặc Có (%r / %r)" % (i, d.get("no"), d.get("co")))
        if no == co:
            raise ValueError("dòng %d: Nợ và Có cùng một tài khoản %s" % (i, no))
        ccy = str(d.get("ccy") or "").strip().upper()
        if ccy not in TIEN_TE:
            raise ValueError("dòng %d: tiền %r không thuộc %s" % (i, d.get("ccy"), ", ".join(TIEN_TE)))
        try:
            tien = float(d.get("tien"))
        except (TypeError, ValueError):
            raise ValueError("dòng %d: tiền không phải số (%r)" % (i, d.get("tien")))
        if not math.isfinite(tien) or tien < 0:
            raise ValueError("dòng %d: tiền phải là số không âm (%r)" % (i, d.get("tien")))
        tien = lam_tron(tien, ccy)
        if tien == 0:
            continue
        dtg = d.get("doi_tuong")
        if dtg is not None:
            if not isinstance(dtg, dict) or not dtg.get("loai") or not dtg.get("ref_id"):
                raise ValueError("dòng %d: doi_tuong phải là {loai, ref_id} hoặc None" % i)
            dtg = {"loai": str(dtg["loai"]), "ref_id": str(dtg["ref_id"])}
        x = dict(d)
        x.update({"no": no, "co": co, "tien": tien, "ccy": ccy, "doi_tuong": dtg,
                  "dien_giai": (str(d.get("dien_giai") or "").strip() or None)})
        # mã chưa ghi sổ được bên kế toán (tài khoản nhóm / không có trong danh mục) — ghi rõ để người xem biết trước
        canh = ["%s: %s" % (m, TK.trang_thai(m)) for m in (no, co) if TK.trang_thai(m) not in ("that", "ma_con_khach")]
        if canh:
            x["canh_bao_tk"] = canh
        else:
            x.pop("canh_bao_tk", None)
        ra.append(x)
    return ra


def _tim(db, nguon, ma_nguon):
    return db.query(ButToanCho).filter(ButToanCho.nguon == nguon, ButToanCho.ma_nguon == ma_nguon).first()


def _dat(r, ngay, ds, dien_giai, trip_id, by_user):
    tien = {x["ccy"] for x in ds}
    r.ngay, r.dien_giai = ngay, (str(dien_giai or "").strip() or None)
    r.dong = json.dumps(ds, ensure_ascii=False, default=str)
    r.so_dong = len(ds)
    r.tien_te = tien.pop() if len(tien) == 1 else None
    r.tong = lam_tron(sum(x["tien"] for x in ds), r.tien_te) if r.tien_te else None
    if trip_id is not None:
        r.trip_id = trip_id
    if r.status == "huy" and r.ma_ben_ke_toan:
        # bản này từng sang bên kế toán rồi được ĐẢO: ghi lại là chứng từ mới — SourceRef mới, không đụng chứng từ đã đảo
        r.phien = (r.phien or 1) + 1
        r.ma_ben_ke_toan = r.so_ben_ke_toan = r.tune_status = r.gui_luc = None
    r.error_code = r.loi_gui = None
    base = "EPLLAO-%s-%s" % (r.nguon, r.ma_nguon)
    r.source_ref = (base if (r.phien or 1) <= 1 else "%s-%d" % (base, r.phien))[:100]
    r.status, r.huy_luc, r.huy_by, r.can_dao = "cho_gui", None, None, False
    if by_user and not r.created_by:
        r.created_by = by_user


def ghi(db, nguon, ma_nguon, ngay, dong, dien_giai, *, trip_id=None, by_user=None):
    """Ghi (hoặc cập nhật bản chưa gửi của) MỘT bút toán cho một nguồn. Xem giao ước ở đầu tệp."""
    nguon, ma_nguon = _khoa(nguon, ma_nguon)
    ngay = _ngay(ngay)
    ds = _chuan_dong(dong)
    r = _tim(db, nguon, ma_nguon)
    if r is not None and r.status == "da_gui" and r.can_dao:
        _dao(db, r)                                 # nguồn bị huỷ rồi ghi lại: đảo bản cũ được thì ghi bản mới (SourceRef mới)
    if r is not None and r.status == "da_gui":
        return r                                    # bên kế toán đã nhận: không sửa lặng lẽ — đổi số thì phải bút toán đảo
    if not ds:
        if r is not None and r.status == "cho_gui":
            _bo_ban_chua_gui(db, r, by_user)
        return r
    if r is None:
        # hai lần khoá cùng lúc (bấm đúp, hai máy) có thể cùng tạo: ghi trong SAVEPOINT, đụng khoá duy nhất thì lấy bản đã có
        r = ButToanCho(nguon=nguon, ma_nguon=ma_nguon)
        try:
            with db.begin_nested():
                _dat(r, ngay, ds, dien_giai, trip_id, by_user)
                db.add(r)
                db.flush()
            return _tu_gui(db, r)
        except IntegrityError:
            r = _tim(db, nguon, ma_nguon)
            if r is None or r.status == "da_gui":
                return r
    _dat(r, ngay, ds, dien_giai, trip_id, by_user)
    db.flush()
    return _tu_gui(db, r)


def _tu_gui(db, r):
    from services import gui_but_toan_tune as GBT
    return GBT.tu_gui(db, r)


def _dao(db, r):
    """Cờ gửi bật: gửi bút toán đảo cho bản đã gửi; được → huy, không được → can_dao (Gửi hết thử lại). Cờ tắt: can_dao.
    Trả True khi đã đảo xong."""
    from fastapi import HTTPException
    from services import gui_but_toan_tune as GBT
    if not GBT.bat():
        r.can_dao = True
        return False
    try:
        GBT.dao(db, r, commit=False)
        return True
    except HTTPException:
        return False                                # dao() đã đánh can_dao, ghi lỗi


def _bo_ban_chua_gui(db, r, by_user):
    """Bỏ một bản `cho_gui`. Lần gửi trước CHƯA RÕ (mất mạng / 5xx — bên kế toán có thể đã lưu) mà cờ gửi bật: hỏi lại bên đó
    trước; bên đó có chứng từ thì bản này thành đã gửi và đi đường đảo như bản đã gửi — không để sót chứng từ bên kia."""
    from fastapi import HTTPException
    from services import gui_but_toan_tune as GBT
    if GBT.bat() and r.error_code in GBT.CHUA_RO:
        try:
            if GBT.hoi(db, r, cho=GBT.CHO_GIAY_TU_GUI) is not None:
                if _dao(db, r):
                    r.huy_by = by_user
                return
        except HTTPException:
            pass                                    # không hỏi được: vẫn bỏ ở đây; mã lỗi cũ giữ trên bản ghi để đối soát
    r.status, r.huy_luc, r.huy_by = "huy", dt.datetime.utcnow(), by_user


def huy(db, nguon, ma_nguon, by_user=None):
    """Nguồn bị huỷ: bản chưa gửi thành `huy`; bản đã gửi giữ nguyên số, đánh `can_dao` (chờ bút toán đảo)."""
    nguon, ma_nguon = _khoa(nguon, ma_nguon)
    r = _tim(db, nguon, ma_nguon)
    if r is None:
        return None
    if r.status == "cho_gui":
        _bo_ban_chua_gui(db, r, by_user)
    elif r.status == "da_gui":
        if _dao(db, r):
            r.huy_by = by_user
    db.flush()
    return r


def rut(db, nguon, ma_nguon, by_user=None):
    """Rút bút toán của một nguồn bị bỏ (bỏ chốt tất toán…): chưa gửi → `huy` (giữ dấu vết), trả True; không có → False;
    bên kế toán đã nhận → 409 BUT_TOAN_DA_GUI — phải bút toán đảo bên đó, không rút lặng lẽ ở đây."""
    from fastapi import HTTPException
    nguon, ma_nguon = _khoa(nguon, ma_nguon)
    r = _tim(db, nguon, ma_nguon)
    if r is None:
        return False
    if r.status == "da_gui":
        from services import gui_but_toan_tune as GBT
        if not GBT.bat():
            raise HTTPException(409, {"ma": "BUT_TOAN_DA_GUI", "loi": "Bút toán %s đã gửi sang hệ kế toán (%s) — không rút được ở đây, "
                                                                     "đối soát và ghi bút toán đảo bên đó trước." % (
                                                                         r.source_ref or ma_nguon, r.so_ben_ke_toan or r.ma_ben_ke_toan or "—")})
        if _dao(db, r):                             # đảo xong bên kế toán
            r.huy_by = by_user
        db.flush()                                  # chưa đảo được: can_dao — nguồn vẫn bỏ được, Gửi hết đảo sau
        return True
    if r.status != "huy":
        _bo_ban_chua_gui(db, r, by_user)
        db.flush()
    return True


def danh_sach(db, nguon=None, status=None, trip_id=None, tu=None, den=None, gioi_han=200):
    """Bút toán chờ, mới trước. `nguon` / `status` nhận một giá trị hoặc nhiều giá trị cách dấu phẩy."""
    q = db.query(ButToanCho)
    if nguon:
        q = q.filter(ButToanCho.nguon.in_([x.strip() for x in str(nguon).split(",") if x.strip()]))
    if status:
        tt = [x.strip() for x in str(status).split(",") if x.strip()]
        sai = [x for x in tt if x not in TRANG_THAI_BUT_TOAN]
        if sai:
            raise ValueError("status phải thuộc %s, nhận %s" % (", ".join(TRANG_THAI_BUT_TOAN), ", ".join(sai)))
        q = q.filter(ButToanCho.status.in_(tt))
    if trip_id:
        q = q.filter(ButToanCho.trip_id == trip_id)
    if tu:
        q = q.filter(ButToanCho.ngay >= _ngay(tu))
    if den:
        q = q.filter(ButToanCho.ngay <= _ngay(den))
    gioi_han = max(1, min(int(gioi_han or 200), 1000))
    return q.order_by(ButToanCho.ngay.desc(), ButToanCho.created_at.desc()).limit(gioi_han).all()


def _gio(t):
    return t.isoformat(timespec="minutes") + "+00:00" if t else None


def xuat(r, doc_no=None):
    if r is None:
        return None
    try:
        dong = json.loads(r.dong or "[]")
    except ValueError:
        dong = []
    for x in dong:
        x["no_ten"], x["co_ten"] = TK.ten(x.get("no")), TK.ten(x.get("co"))
        # tên Lào nguyên danh mục anh Khampla — màn tiếng Lào hiện tên này thay tên Việt
        x["no_ten_lo"], x["co_ten_lo"] = TK.ten(x.get("no"), "lo"), TK.ten(x.get("co"), "lo")
    return {"id": r.id, "nguon": r.nguon, "ma_nguon": r.ma_nguon, "ngay": r.ngay.isoformat() if r.ngay else None,
            "dien_giai": r.dien_giai, "dong": dong, "so_dong": r.so_dong, "tien_te": r.tien_te, "tong": r.tong,
            "trip_id": r.trip_id, "trip_doc_no": doc_no, "status": r.status, "can_dao": bool(r.can_dao),
            "source_ref": r.source_ref, "ma_ben_ke_toan": r.ma_ben_ke_toan, "so_ben_ke_toan": r.so_ben_ke_toan,
            "gui_luc": _gio(r.gui_luc), "loi_gui": r.loi_gui, "error_code": r.error_code, "attempts": r.attempts or 0,
            "tune_status": r.tune_status, "phien": r.phien or 1, "huy_luc": _gio(r.huy_luc), "huy_by": r.huy_by,
            "created_by": r.created_by, "created_at": _gio(r.created_at), "updated_at": _gio(r.updated_at)}


# ================================================================ bút toán lúc KHOÁ PHIẾU (chủ dự án 01/10)
def dong_khoa_phieu(db, p, cac_dong=None):
    """{nguon: (dòng, diễn giải)} cho phiếu `p` lúc khoá — chưa ghi gì.

      · thue_xe — xe thuê: Nợ 621 / Có 4022 bằng TIỀN THUÊ (tinh_phieu `tien_thue`, đúng `hire.amount` của gói bàn giao DO),
        theo tiền thuê. Phí 2 % và trừ quá tải chưa có bút toán riêng (chờ anh Khampla chọn cách ghi).
      · no_ncc — mỗi dòng chi EPL chịu mà định khoản có vế Có 4021 (tai_khoan.tk_dong: dầu trạm ghi nợ, chipping, thẻ cao tốc,
        lốp nợ theo đợt, garage cho nợ…) — Nợ 625 · 614 (xe thuê 4022) / Có 4021, quy Kíp theo tỷ giá khoá trên phiếu. BỎ các
        dòng mục V quỹ TRẢ NGAY (chi_muc_tune.dong_quy_chi): những dòng đó vào chi phí qua phiếu chi "Chi khác" bên kế toán
        (Nợ 614 / Có tiền), ghi thêm Có 4021 là chi phí hai lần."""
    from models import TripExpense
    from services import chi_muc_tune as CMT
    from services.ban_giao import _ten as ten_dong
    from services.tinh_toan import tien_dong, tinh_phieu, ty_gia
    if cac_dong is None:
        cac_dong = (db.query(TripExpense).filter(TripExpense.trip_id == p.id)
                    .order_by(TripExpense.section, TripExpense.line_no).all())
    ra = {}
    t = tinh_phieu(p, cac_dong)
    if p.company == "joint" and (t.get("tien_thue") or 0) > 0:
        h = t["hire_ccy"]
        ra[THUE_XE] = ([{"no": TK.CP_THUE_XE, "co": TK.CHU_XE, "tien": t["tien_thue"], "ccy": h,
                         "tien_lak": t["tien_thue_lak"], "ty_gia": ty_gia(p, h),
                         "doi_tuong": {"loai": "chu_xe", "ref_id": p.owner_id} if p.owner_id else None,
                         "dien_giai": "Chi phí thuê xe liên kết %s · %s" % (p.doc_no, p.owner_name or "")}],
                       "Ghi nhận chi phí thuê xe liên kết phiếu %s (%s)" % (p.doc_no, p.owner_name or "—"))
    quy = {d.id for m in ("repair", "other") for d in CMT.dong_quy_chi(db, p, m, cac_dong)}
    dong = []
    for d in cac_dong:
        if d.id in quy or d.paid_by_epl is False:          # chủ xe tự chi: không phải tiền của EPL
            continue
        ma = TK.tk_dong(p.company, d)
        if not ma or "/" not in ma:
            continue
        no, co = ma.split("/", 1)
        if co != TK.NCC:
            continue
        lak = round(tien_dong(p, d))
        if lak <= 0:
            continue
        # tên khoản mục bằng chữ người đọc (dòng khoản mục chuẩn chỉ có item_key "x_tire" — trước đây diễn giải ghi nguyên
        # mã đó, cả lên màn lẫn sang hệ kế toán; rà 01/10)
        x = {"no": no, "co": co, "tien": lak, "ccy": "LAK", "ref": d.id, "section": d.section,
             "doi_tuong": {"loai": "ncc", "ref_id": d.supplier_id} if d.supplier_id else None,
             "dien_giai": "%s %s · %s" % ({"fuel": "III", "travel": "IV", "repair": "V", "other": "VI"}.get(d.section, ""),
                                         ten_dong(db, d)[0], p.doc_no)}
        if (d.currency or "LAK").upper() != "LAK":
            x.update({"tien_goc": lam_tron((d.qty or 0) * (d.unit_price or 0), d.currency), "ccy_goc": d.currency.upper(),
                      "ty_gia": ty_gia(p, d.currency)})
        if no == TK.CHU_XE and p.owner_id:
            x["doi_tuong_no"] = {"loai": "chu_xe", "ref_id": p.owner_id}
        dong.append(x)
    if dong:
        ra[NO_NCC] = (dong, "Ghi nhận chi phí ghi nợ nhà cung cấp phiếu %s" % p.doc_no)
    return ra


# ================================================================ XUẤT KHO cho chuyến (chủ dự án 01/10)
def _ngay_dia_phuong(t):
    """Giờ UTC lưu trong DB (bay_gio) → ngày theo giờ máy chủ — cùng cách lần xuất kho lấy ngày (dt.date.today() lúc cấp)."""
    return t.replace(tzinfo=dt.timezone.utc).astimezone().date() if t else None


def _so_doc(x):
    """Số gọn cho diễn giải: 100.0 → "100", 30000 → "30.000", 1.5 → "1,5" (cách viết của khách)."""
    x = float(x or 0)
    if abs(x - round(x)) < 1e-9:
        return "{:,}".format(int(round(x))).replace(",", ".")
    return ("%.2f" % x).rstrip("0").replace(".", ",")


def _lan_xuat(db, p, loai, ds):
    """(ngày xuất kho THẬT, số tờ) của một lần xuất. Dầu: phiếu đề nghị xuất kho nhiên liệu đã cấp của đúng kho (granted_at —
    lần cấp là lần xuất, phieu_linh.cap_phat). Phụ tùng: sự cố sinh dòng (duyệt báo hỏng → approved_at; tổ sửa tự khai → ts)
    — phụ tùng rời kho ngay lúc đó. Không tìm được (dòng cũ xuất lúc ghi sổ mục III trước 30/09) thì ngày xe đi."""
    from models import TripEvent, Voucher
    from services.gia_von import kho_goc
    ngay, nhan = None, None
    if loai == "dau":
        noi = ds[0].place_id or kho_goc(db)
        v = (db.query(Voucher).filter(Voucher.trip_id == p.id, Voucher.kind == "fuel", Voucher.status == "da_cap",
                                      Voucher.place_id == noi).order_by(Voucher.granted_at.desc()).first())
        if v is not None:
            ngay, nhan = _ngay_dia_phuong(v.granted_at), v.doc_no
    else:
        e = db.query(TripEvent).filter(TripEvent.trip_id == p.id, TripEvent.expense_id == ds[0].id).first()
        if e is not None:
            ngay = _ngay_dia_phuong(e.approved_at or e.ts)
    return ngay or p.out_date or p.doc_date or dt.date.today(), nhan


def dong_xuat_kho(db, p, cac_dong=None):
    """{(nguon, ma_nguon): (ngày xuất, dòng, diễn giải)} — bút toán XUẤT KHO cho chuyến của phiếu `p`, chưa ghi gì.

    Chỉ dòng ĐÃ RỜI KHO: dầu mục III / phụ tùng mục V `source = kho` có `stock_move_id` (dầu: thủ kho đã cấp theo phiếu đề
    nghị; phụ tùng: xuất ngay lúc khai sự cố). EPL ứng (`paid_by_epl` khác False), số lượng > 0. Gom theo LẦN XUẤT (một tờ cấp
    dầu có thể gồm nhiều dòng cùng kho) — một lần xuất một bút toán, ngày chứng từ = ngày xuất thật (`_lan_xuat`).

      · xe nhà → `xuat_noi_bo`: định khoản của dòng (tai_khoan.tk_dong — luật: dầu 625/1371, phụ tùng 614/1371) bằng GIÁ VỐN.
      · xe thuê → `xuat_ban`: hai dòng — doanh thu theo định khoản của dòng (luật: 4022/707) bằng GIÁ BÁN (`sale_price`, đúng
        số tinh_toan.tien_dong trừ vào tiền trả chủ xe; chưa gõ giá bán thì tiền trừ tạm theo giá vốn — bút toán theo đúng số
        đó, ghi rõ `gia_ban_tam`), đối tượng chủ xe; và giá vốn Nợ 607 / Có 1371 bằng GIÁ VỐN, không đối tượng.
    GIÁ VỐN = số lượng × `unit_price` của dòng: giá bình quân của đúng kho LÚC XUẤT do kho tạm trả về (dầu: cap_phat chép
    `unit_cost_lak` của dòng sổ lên dòng; phụ tùng: giá bình quân đọc ngay trước khi xuất, cùng giá kho tạm ghi trên dòng sổ).
    Dòng đã xuất không sửa được giá (phieu._ap_gia, _ap_dong_chi) nên số này đứng yên.
    Dòng mang mã người dùng tự chọn có vế Có 4021 thì đã nằm trong `no_ncc` — bỏ ở đây để không ghi hai lần."""
    from models import TripExpense
    from services.ban_giao import _ten as ten_dong
    from services.tinh_toan import la_xuat_ban, tien_dong, ty_gia
    if cac_dong is None:
        cac_dong = (db.query(TripExpense).filter(TripExpense.trip_id == p.id)
                    .order_by(TripExpense.section, TripExpense.line_no).all())
    thue = p.company == "joint"
    nguon = XUAT_BAN if thue else XUAT_NOI_BO
    nhom = {}
    for d in cac_dong:
        if d.section not in ("fuel", "repair") or d.source != "kho" or not d.stock_move_id:
            continue
        # "chủ xe tự trả": không phải tiền của EPL. Từ 02/10 dòng kho xe thuê không được ghi vậy (chan_xuat_ban chặn khoá) —
        # điều kiện này chỉ còn giữ phòng dữ liệu cũ
        if d.paid_by_epl is False or (d.qty or 0) <= 0:
            continue
        nhom.setdefault(("dau" if d.section == "fuel" else "pt", d.stock_move_id), []).append(d)
    ra = {}
    for (loai, mv), ds in nhom.items():
        ngay, so_to = _lan_xuat(db, p, loai, ds)
        hang = "dầu" if loai == "dau" else "phụ tùng"
        dong = []
        for d in ds:
            ma = TK.tk_dong(p.company, d)
            if not ma or "/" not in ma:
                continue
            no, co = ma.split("/", 1)
            if co == TK.NCC:
                continue
            ty = ty_gia(p, d.currency)
            gia_von = d.unit_price or 0
            von = round((d.qty or 0) * gia_von * ty)
            ten = "%s %s %s" % ({"fuel": "III", "repair": "V"}[d.section], ten_dong(db, d)[0], _so_doc(d.qty))
            chung = {"ccy": "LAK", "ref": d.id, "section": d.section, "sl": d.qty, "stock_move_id": mv,
                     "hinh_thuc": "xuat_ban" if thue else "noi_bo"}
            if (d.currency or "LAK").upper() != "LAK":
                chung["ty_gia"] = ty
            if thue and la_xuat_ban(p, d) and co != TK.KHO:
                ban_tam = d.sale_price is None
                gia_ban = d.unit_price if ban_tam else d.sale_price
                x = dict(chung, no=no, co=co, tien=round(tien_dong(p, d)), ve="doanh_thu", don_gia=gia_ban,
                         doi_tuong={"loai": "chu_xe", "ref_id": p.owner_id} if p.owner_id else None,
                         dien_giai="Xuất bán cho chủ xe — doanh thu %s × %s (%s) · %s" % (
                             ten, _so_doc(gia_ban), "chưa có giá bán, tạm theo giá vốn" if ban_tam else "giá bán", p.doc_no))
                if ban_tam:
                    x["gia_ban_tam"] = True
                dong.append(x)
                dong.append(dict(chung, no=TK.GIA_VON, co=TK.KHO, tien=von, ve="gia_von", don_gia=gia_von, doi_tuong=None,
                                 dien_giai="Xuất bán cho chủ xe — giá vốn %s × %s (bình quân kho) · %s" % (
                                     ten, _so_doc(gia_von), p.doc_no)))
            else:
                dong.append(dict(chung, no=no, co=co, tien=von, ve="gia_von", don_gia=gia_von, doi_tuong=None,
                                 dien_giai="%s — %s × %s (giá vốn bình quân kho) · %s" % (
                                     "Xuất kho" if thue else "Xuất nội bộ", ten, _so_doc(gia_von), p.doc_no)))
        if not dong:
            continue
        kem = (" · " + so_to) if so_to else (" · " + ten_dong(db, ds[0])[0] if loai == "pt" else "")
        dg = ("Xuất bán cho chủ xe %s — %s phiếu %s%s" % (p.owner_name or "—", hang, p.doc_no, kem) if thue
              else "Xuất kho nội bộ %s phiếu %s%s" % (hang, p.doc_no, kem))
        ra[(nguon, "%s:%s" % (loai, mv))] = (ngay, dong, dg)
    return ra


def _ban_xuat_kho(db, trip_id):
    return (db.query(ButToanCho).filter(ButToanCho.trip_id == trip_id, ButToanCho.nguon.in_(NGUON_XUAT_KHO))
            .order_by(ButToanCho.created_at).all())


def ghi_khoa_phieu(db, p, by_user=None, cac_dong=None):
    """Khoá phiếu → ghi (hoặc cập nhật) các bút toán chờ: `thue_xe`, `no_ncc` (một bản mỗi nguồn) và bút toán XUẤT KHO
    (`xuat_noi_bo` / `xuat_ban`, một bản mỗi lần xuất). Nguồn nào không còn dòng thì huỷ bản chưa gửi.
    Trả {nguon: bản} cho thue_xe / no_ncc, {nguon: [bản, …]} cho hai nguồn xuất kho.

    Vì sao bút toán xuất kho ghi LÚC KHOÁ chứ không lúc cấp dầu / xuất phụ tùng (dù hàng rời kho trước đó): GIÁ BÁN cho chủ
    xe chỉ có khi KT kho xăng dầu (mục III) / KT Chi phí (mục V) kiểm mục, sau lúc xuất; tiền trả chủ xe tính từ phiếu ĐÃ
    KHOÁ — ghi lúc khoá thì Nợ 4022 / Có 707 đúng bằng số trừ vào tiền trả; mở khoá huỷ / gỡ cùng thue_xe, no_ncc. Ngày
    chứng từ vẫn là ngày xuất thật (bút toán chưa gửi nên ghi muộn không lệch kỳ)."""
    ngay = dt.date.today()
    bo = dong_khoa_phieu(db, p, cac_dong)
    ra = {}
    for n in NGUON_KHOA_PHIEU:
        dong, dg = bo.get(n, ([], None))
        r = ghi(db, n, p.id, ngay, dong, dg, trip_id=p.id, by_user=by_user)
        if r is not None:
            ra[n] = r
    kho = dong_xuat_kho(db, p, cac_dong)
    for (n, m), (ngay_x, dong, dg) in kho.items():
        r = ghi(db, n, m, ngay_x, dong, dg, trip_id=p.id, by_user=by_user)
        if r is not None:
            ra.setdefault(n, []).append(r)
    # bản xuất kho cũ không còn ứng với lần xuất nào của phiếu theo loại xe hiện tại (đổi xe nhà ↔ xe thuê giữa hai lần
    # khoá…) → huỷ như mở khoá
    for r in _ban_xuat_kho(db, p.id):
        if (r.nguon, r.ma_nguon) not in kho and r.status != "huy":
            huy(db, r.nguon, r.ma_nguon, by_user)
    return ra


def huy_khoa_phieu(db, p, by_user=None):
    """Mở khoá / xoá phiếu → huỷ các bút toán CHƯA gửi của phiếu đó (bản đã gửi: gỡ bên kế toán, chưa gỡ được thì chờ đảo) —
    thue_xe, no_ncc và mọi bút toán xuất kho của phiếu."""
    ra = [r for r in (huy(db, n, p.id, by_user) for n in NGUON_KHOA_PHIEU) if r is not None]
    for r in _ban_xuat_kho(db, p.id):
        if r.status != "huy":                       # cho_gui → huy · da_gui → gỡ bên kế toán (chưa được thì chờ đảo)
            ra.append(huy(db, r.nguon, r.ma_nguon, by_user))
    return ra


# ================================================================ LUẬT DÒNG KHO XE THUÊ · KHOÁ PHIẾU (chủ dự án 02/10)
# 1. Dầu / phụ tùng LẤY TỪ KHO EPL cho xe thuê LUÔN là xuất bán cho chủ xe (chốt 30/09, nhắc lại 02/10): không có "chủ xe tự
#    trả". Chủ xe trả tiền ngay thì đi quầy bán hàng (phiếu bán ở kho tạm → ban_chu_xe).
# 2. Khoá phiếu bị chặn khi còn dòng xuất bán chưa có giá bán (THIEU_GIA_BAN), hoặc dòng cũ ghi "chủ xe tự trả"
#    (KHO_XE_THUE_XUAT_BAN — chặn chứ không tự đổi: đổi lặng lẽ là đổi số trừ tiền trả chủ xe mà không ai bấm).
# 3. Sau khoá, các dòng đã vào bút toán khoá phiếu (dòng kho, dòng ghi nợ nhà cung cấp) đứng yên: sửa → 409 DA_KHOA.
# Câu lỗi đủ ba tiếng: `loi` (Việt), `loi_lo`, `loi_en` — giao diện (js/chung.js API.goi) hiện theo tiếng đang xem.
_MUC = {"fuel": ("III", "dầu", "ນໍ້າມັນ", "fuel"), "repair": ("V", "phụ tùng", "ອາໄຫຼ່", "part")}
_NGUOI_GIA_BAN = {"fuel": ("KT kho xăng dầu", "ບັນຊີສາງນໍ້າມັນ", "the fuel store accountant"),
                  "repair": ("KT Chi phí", "ບັນຊີລາຍຈ່າຍ", "the cost accountant")}


def loi3(http, ma, vi, lo, en, **them):
    """HTTPException với câu lỗi đủ ba tiếng (Việt · Lào · Anh)."""
    from fastapi import HTTPException
    return HTTPException(http, dict({"ma": ma, "loi": vi, "loi_lo": lo, "loi_en": en}, **them))


def _vi_tri(d, cac_dong):
    """("mục III dòng 2", "ໜ້າ III ແຖວ 2", "section III line 2") — dòng thứ mấy TRONG MỤC, như màn phiếu đánh số."""
    cung = [x for x in cac_dong if x.section == d.section]
    i = next((k for k, x in enumerate(cung, 1) if x is d or (x.id and x.id == d.id)), None) or d.line_no or len(cung) + 1
    m = {"fuel": "III", "travel": "IV", "repair": "V", "other": "VI"}.get(d.section, d.section)
    return "mục %s dòng %d" % (m, i), "ໜ້າ %s ແຖວ %d" % (m, i), "section %s line %d" % (m, i)


def _noi(ds, k):
    return ", ".join(x[k] for x in ds)


def chan_kho_xe_thue_tu_tra(p, d, cac_dong=()):
    """Lập / sửa dòng: dòng kho (dầu mục III, phụ tùng mục V) của xe thuê mà ghi "chủ xe tự trả" → 422 KHO_XE_THUE_XUAT_BAN."""
    from services.tinh_toan import la_xuat_ban
    if not la_xuat_ban(p, d) or d.paid_by_epl is not False:
        return
    m, vi, lo, en = _MUC.get(d.section, ("", "hàng", "ສິນຄ້າ", "goods"))
    vt = _vi_tri(d, list(cac_dong) or [d])
    raise loi3(422, "KHO_XE_THUE_XUAT_BAN",
               "Xe thuê: %s lấy từ kho EPL (%s) luôn là xuất bán cho chủ xe — không chọn «Chủ xe tự trả» được. Chủ xe trả tiền ngay "
               "thì lập phiếu bán ở quầy (kho tạm)." % (vi, vt[0]),
               "ລົດເຊົ່າ: %s ທີ່ເບີກຈາກສາງ EPL (%s) ແມ່ນຂາຍໃຫ້ເຈົ້າຂອງລົດສະເໝີ — ເລືອກ «ເຈົ້າຂອງລົດຈ່າຍເອງ» ບໍ່ໄດ້. ຖ້າເຈົ້າຂອງລົດ"
               "ຈ່າຍເງິນທັນທີ ໃຫ້ອອກໃບຂາຍຢູ່ໜ້າຮ້ານ (ສາງຊົ່ວຄາວ)." % (lo, vt[1]),
               "Hired truck: %s taken from the EPL store (%s) is always sold to the truck owner — «Owner pays» is not allowed. If "
               "the owner pays on the spot, make a counter sale (temporary store)." % (en, vt[2]),
               trip_id=p.id, expense_id=d.id)


def chan_xuat_ban(p, cac_dong, muc=None, luc="khoa"):
    """Dòng xuất bán (xe thuê, dầu / phụ tùng lấy kho, số lượng > 0) của phiếu — hoặc của một mục `muc` — phải là EPL ứng và có
    giá bán. `luc`: "khoa" (khoá phiếu, 409) · "kiem" (kiểm mục, 409). Dòng cũ ghi "chủ xe tự trả" → KHO_XE_THUE_XUAT_BAN
    (chặn, kèm cách sửa); thiếu giá bán → THIEU_GIA_BAN (nói mục nào, ai gõ)."""
    from services.tinh_toan import la_xuat_ban
    ds = [d for d in cac_dong if la_xuat_ban(p, d) and (muc is None or d.section == muc) and (d.qty or 0) > 0]
    tu_tra = [_vi_tri(d, cac_dong) for d in ds if d.paid_by_epl is False]
    if tu_tra:
        raise loi3(409, "KHO_XE_THUE_XUAT_BAN",
                   "Phiếu %s: %s lấy từ kho EPL cho xe thuê đang ghi «Chủ xe tự trả» — hàng lấy kho EPL cho xe thuê luôn là xuất bán "
                   "cho chủ xe. Bấm «EPL ứng» cho dòng đó (người nhập mục, hoặc KT kho xăng dầu mục III / KT Chi phí mục V khi gõ giá "
                   "bán), gõ giá bán, rồi %s lại. Chủ xe đã trả tiền ngay thì bỏ dòng, lập phiếu bán ở quầy." % (
                       p.doc_no, _noi(tu_tra, 0), "khoá" if luc == "khoa" else "kiểm"),
                   "ໃບ %s: %s ທີ່ເບີກຈາກສາງ EPL ໃຫ້ລົດເຊົ່າ ຍັງເປັນ «ເຈົ້າຂອງລົດຈ່າຍເອງ» — ສິນຄ້າເບີກສາງ EPL ໃຫ້ລົດເຊົ່າ ແມ່ນຂາຍໃຫ້"
                   "ເຈົ້າຂອງລົດສະເໝີ. ກົດ «EPL ອອກກ່ອນ» ໃຫ້ແຖວນັ້ນ (ຜູ້ປ້ອນໜ້າ, ຫຼື ບັນຊີສາງນໍ້າມັນ ໜ້າ III / ບັນຊີລາຍຈ່າຍ ໜ້າ V ຕອນປ້ອນ"
                   "ລາຄາຂາຍ), ປ້ອນລາຄາຂາຍ, ແລ້ວ%sຄືນ. ຖ້າເຈົ້າຂອງລົດຈ່າຍເງິນທັນທີແລ້ວ ໃຫ້ລຶບແຖວ ແລະ ອອກໃບຂາຍຢູ່ໜ້າຮ້ານ." % (
                       p.doc_no, _noi(tu_tra, 1), "ລັອກ" if luc == "khoa" else "ກວດ"),
                   "Slip %s: %s taken from the EPL store for a hired truck is still marked «Owner pays» — goods from the EPL store "
                   "for a hired truck are always sold to the owner. Click «EPL advance» on that line (the person entering the "
                   "section, or the fuel store accountant for III / the cost accountant for V when entering the sale price), enter "
                   "the sale price, then %s again. If the owner already paid on the spot, delete the line and make a counter "
                   "sale." % (p.doc_no, _noi(tu_tra, 2), "lock" if luc == "khoa" else "verify"),
                   trip_id=p.id)
    thieu = {}
    for d in ds:
        if not (d.sale_price or 0) > 0:
            thieu.setdefault(d.section, []).append(_vi_tri(d, cac_dong))
    if not thieu:
        return
    phan = [(_noi(v, 0) + " (%s): %s gõ giá bán" % (_MUC[m][1], _NGUOI_GIA_BAN[m][0]),
             _noi(v, 1) + " (%s): %s ປ້ອນລາຄາຂາຍ" % (_MUC[m][2], _NGUOI_GIA_BAN[m][1]),
             _noi(v, 2) + " (%s): %s enters the sale price" % (_MUC[m][3], _NGUOI_GIA_BAN[m][2]))
            for m, v in sorted(thieu.items(), key=lambda kv: kv[0] != "fuel")]
    raise loi3(409, "THIEU_GIA_BAN",
               "Phiếu %s chưa %s được: xe thuê lấy hàng kho EPL là xuất bán cho chủ xe %s mà chưa có giá bán — %s. Gõ giá bán rồi %s "
               "lại." % (p.doc_no, "khoá" if luc == "khoa" else "kiểm", p.owner_name or "", "; ".join(x[0] for x in phan),
                         "khoá" if luc == "khoa" else "kiểm"),
               "ໃບ %s ຍັງ%sບໍ່ໄດ້: ລົດເຊົ່າເບີກສິນຄ້າຈາກສາງ EPL ແມ່ນຂາຍໃຫ້ເຈົ້າຂອງລົດ %s ແຕ່ຍັງບໍ່ມີລາຄາຂາຍ — %s. ປ້ອນລາຄາຂາຍແລ້ວ%s"
               "ຄືນ." % (p.doc_no, "ລັອກ" if luc == "khoa" else "ກວດ", p.owner_name or "", "; ".join(x[1] for x in phan),
                         "ລັອກ" if luc == "khoa" else "ກວດ"),
               "Slip %s cannot be %s yet: goods from the EPL store for a hired truck are sold to the owner %s but have no sale "
               "price — %s. Enter the sale price, then %s again." % (
                   p.doc_no, "locked" if luc == "khoa" else "verified", p.owner_name or "", "; ".join(x[2] for x in phan),
                   "lock" if luc == "khoa" else "verify"),
               trip_id=p.id, muc=sorted(thieu))


def dau_khoa(db, p):
    """Dấu của những gì bút toán KHOÁ PHIẾU đã ghi theo (chỉ khi phiếu đang khoá; không khoá → None): mỗi dòng kho (nguồn,
    lần xuất, số lượng, giá vốn, giá bán, tiền tệ, ai trả), mỗi dòng ghi nợ nhà cung cấp (định khoản, tiền, nhà cung cấp) và
    từng dòng bút toán xuất kho. Không theo mã dòng: Sếp lưu lại một mục thì dòng chưa xuất kho được tạo lại mã mới mà số
    không đổi — không phải là sửa. → [(khoá so sánh, (tên vi, lo, en) | None)]"""
    if p is None or not p.locked:
        return None
    from models import TripExpense
    dong = (db.query(TripExpense).filter(TripExpense.trip_id == p.id)
            .order_by(TripExpense.section, TripExpense.line_no).all())
    ra = []
    for d in dong:
        if d.section in ("fuel", "repair") and d.source == "kho":
            ra.append((("kho", d.section, d.stock_move_id or "", d.part_id or "", d.place_id or "", float(d.qty or 0),
                        float(d.unit_price or 0), None if d.sale_price is None else float(d.sale_price),
                        (d.currency or "LAK").upper(), d.paid_by_epl is not False), _vi_tri(d, dong)))
    theo_id = {d.id: d for d in dong}
    for x in dong_khoa_phieu(db, p, dong).get(NO_NCC, ([], None))[0]:
        d = theo_id.get(x.get("ref"))
        ra.append((("ncc", x.get("section"), x["no"], x["co"], x["tien"], (x.get("doi_tuong") or {}).get("ref_id")),
                   _vi_tri(d, dong) if d is not None else None))
    for (n, m), (_, ds, _) in dong_xuat_kho(db, p, dong).items():
        for x in ds:
            ra.append(((n, m, x["no"], x["co"], x["tien"]), None))
    return ra


def chan_sua_sau_khoa(db, p, truoc):
    """Phiếu đang khoá: so dấu trước (dau_khoa lúc vào việc) với sau (đã áp thay đổi, chưa commit). Lệch → 409 DA_KHOA, nói dòng
    nào — người gọi không commit (route ném lỗi → phiên huỷ; trong GiaoDichKho thì lần xuất bên kho tạm được trả lại)."""
    if truoc is None:
        return
    from collections import Counter
    db.flush()
    sau = dau_khoa(db, p) or []
    a, b = Counter(k for k, _ in truoc), Counter(k for k, _ in sau)
    if a == b:
        return
    lech = set((a - b) | (b - a))
    ten = []
    for k, t in list(truoc) + list(sau):
        if k in lech and t and t not in ten:
            ten.append(t)
    ds = ten or [("các dòng xuất kho", "ແຖວເບີກສາງ", "the store-issue lines")]
    raise loi3(409, "DA_KHOA",
               "Phiếu %s đã khoá — %s đã vào bút toán khoá phiếu (xuất kho / ghi nợ nhà cung cấp): không sửa giá bán, đơn giá, số "
               "lượng, ai trả, không thêm / bỏ dòng, không cấp / xuất thêm được. KT Thu/Chi mở khoá phiếu rồi mới sửa." % (
                   p.doc_no, _noi(ds, 0)),
               "ໃບ %s ລັອກແລ້ວ — %s ລົງບັນຊີຕອນລັອກໃບແລ້ວ (ເບີກສາງ / ໜີ້ຜູ້ສະໜອງ): ແກ້ລາຄາຂາຍ, ລາຄາ, ຈຳນວນ, ຜູ້ຈ່າຍ, ເພີ່ມ / ລຶບແຖວ, "
               "ເບີກເພີ່ມ ບໍ່ໄດ້. ບັນຊີລາຍຈ່າຍ/ຮັບ ປົດລັອກໃບກ່ອນ ຈຶ່ງແກ້ໄດ້." % (p.doc_no, _noi(ds, 1)),
               "Slip %s is locked — %s went into the lock-time journal entries (store issue / supplier payable): the sale price, "
               "unit price, quantity and payer cannot change, lines cannot be added or removed, nothing more can be issued. The "
               "receipts & payments accountant must unlock the slip first." % (p.doc_no, _noi(ds, 2)),
               trip_id=p.id)
