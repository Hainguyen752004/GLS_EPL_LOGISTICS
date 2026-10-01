# -*- coding: utf-8 -*-
"""BÚT TOÁN CHỜ GỬI — khoản sổ kế toán phải ghi mà KHÔNG đi qua tiền (chủ dự án chốt 01/10/2026: "toàn diện nhất, đúng Excel,
đúng nghiệp vụ").

Khoản đi qua tiền thì thành phiếu chi / thu bên hệ kế toán anh Tune (services/chi_tune.py, chi_muc_tune.py…). Khoản không qua
tiền — ghi nhận chi phí thuê xe, ghi nợ nhà cung cấp, quyết toán… — hệ anh Tune CHƯA có đường nhận (source chưa có chứng từ
"bút toán tổng hợp", hợp đồng kế toán mục 12.12.4). Bên em không đoán cấu trúc sổ cái bên đó để ghi thẳng, nên giữ bút toán ở
đây, ĐỦ hai vế từng dòng bằng mã thật (services/tai_khoan.py), chờ có API thì gửi — không mất khoản nào trong lúc chờ.

GIAO ƯỚC (module khác gọi — giữ cố định):

    ghi(db, nguon, ma_nguon, ngay, dong, dien_giai) -> ButToanCho | None
        nguon      ≤ 16 ký tự: loại nguồn — thue_xe · no_ncc (khoá phiếu, ở đây) · nguồn khác do module gọi tự đặt
        ma_nguon   ≤ 80 ký tự: mã bản ghi nguồn (thue_xe / no_ncc: Trip.id)
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
            r.status, r.huy_luc, r.huy_by = "huy", dt.datetime.utcnow(), by_user
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


def huy(db, nguon, ma_nguon, by_user=None):
    """Nguồn bị huỷ: bản chưa gửi thành `huy`; bản đã gửi giữ nguyên số, đánh `can_dao` (chờ bút toán đảo)."""
    nguon, ma_nguon = _khoa(nguon, ma_nguon)
    r = _tim(db, nguon, ma_nguon)
    if r is None:
        return None
    if r.status == "cho_gui":
        r.status, r.huy_luc, r.huy_by = "huy", dt.datetime.utcnow(), by_user
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
        r.status, r.huy_luc, r.huy_by = "huy", dt.datetime.utcnow(), by_user
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
        x = {"no": no, "co": co, "tien": lak, "ccy": "LAK", "ref": d.id, "section": d.section,
             "doi_tuong": {"loai": "ncc", "ref_id": d.supplier_id} if d.supplier_id else None,
             "dien_giai": "%s %s · %s" % ({"fuel": "III", "travel": "IV", "repair": "V", "other": "VI"}.get(d.section, ""),
                                         d.item_name or d.item_key or "", p.doc_no)}
        if (d.currency or "LAK").upper() != "LAK":
            x.update({"tien_goc": lam_tron((d.qty or 0) * (d.unit_price or 0), d.currency), "ccy_goc": d.currency.upper(),
                      "ty_gia": ty_gia(p, d.currency)})
        if no == TK.CHU_XE and p.owner_id:
            x["doi_tuong_no"] = {"loai": "chu_xe", "ref_id": p.owner_id}
        dong.append(x)
    if dong:
        ra[NO_NCC] = (dong, "Ghi nhận chi phí ghi nợ nhà cung cấp phiếu %s" % p.doc_no)
    return ra


def ghi_khoa_phieu(db, p, by_user=None, cac_dong=None):
    """Khoá phiếu → ghi (hoặc cập nhật) hai bút toán chờ; nguồn nào không còn dòng thì huỷ bản chưa gửi. Trả {nguon: bản}."""
    ngay = dt.date.today()
    bo = dong_khoa_phieu(db, p, cac_dong)
    ra = {}
    for n in NGUON_KHOA_PHIEU:
        dong, dg = bo.get(n, ([], None))
        r = ghi(db, n, p.id, ngay, dong, dg, trip_id=p.id, by_user=by_user)
        if r is not None:
            ra[n] = r
    return ra


def huy_khoa_phieu(db, p, by_user=None):
    """Mở khoá phiếu → huỷ các bút toán CHƯA gửi của phiếu đó (bản đã gửi: đánh chờ đảo)."""
    return [r for r in (huy(db, n, p.id, by_user) for n in NGUON_KHOA_PHIEU) if r is not None]
