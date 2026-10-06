# -*- coding: utf-8 -*-
"""BỘ ĐỆM BÁO CÁO THEO THÁNG — tính một lần, dùng lại tới khi dữ liệu CỦA THÁNG ĐÓ đổi (chủ dự án chốt 24/09).

Vì sao cần: nghìn chuyến / ngày thì một tháng ~30.000 phiếu × ~5 dòng chi. Báo cáo tháng phải cộng lại chừng đó
mỗi lần mở; màn Tổng quan còn vẽ 6 tháng. Sáu tháng cũ gần như không ai sửa nữa mà vẫn bị tính lại mỗi lần bấm.

Không phải bộ đệm "hết hạn sau N phút" (loại đó hiện số CŨ trong N phút — với tiền là không được). Ở đây:

  · Mỗi lần ghi (ORM flush) có đụng phiếu hay thứ gắn với phiếu, số phiên bản của tháng CỦA PHIẾU đó — và của NGÀY
    của phiếu đó ('YYYY-MM-DD') — tăng 1, ngay trong giao dịch ghi (bảng phien_ban_thang). Giao dịch huỷ thì không tăng.
    Theo ngày vì tháng này bị ghi liên tục (nghìn chuyến / ngày): báo cáo tháng cộng từ các NGÀY đã tính sẵn, ghi vào
    phiếu hôm nay thì chỉ hôm nay phải tính lại — 29 ngày kia vẫn nguyên.
  · Báo cáo lưu kèm số phiên bản đọc được TRƯỚC khi tính. Lần sau số còn y nguyên → dữ liệu tháng đó chưa đổi →
    trả luôn. Số khác → tính lại. Số nằm trong DB nên chạy nhiều tiến trình máy chủ vẫn đúng.
  · Xoá / sửa hàng loạt (query().delete(), update()) trên các bảng đó → tăng khoá '*' → mọi tháng tính lại.
  · Bảng khác ảnh hưởng một vài báo cáo thì có KHOÁ RIÊNG (THEM): lần thu → 'thu', thẻ cao tốc → 'the', hoá đơn gộp
    → 'hd', nhà cung cấp → 'ncc'. Báo cáo nào đọc bảng đó thì khai thêm khoá đó (ví dụ cấn trừ).
  · Bản đã tính lưu cả trong bộ nhớ lẫn trong DB (bảng bao_cao_dem) — khởi động lại máy chủ vẫn dùng lại được.
  · Lưới an toàn: bản trong bộ nhớ quá 30 phút, bản trong DB quá 1 ngày thì tính lại (phòng ai sửa thẳng DB bằng tay).

Chỉ những bảng dưới đây ảnh hưởng báo cáo được đệm (tổng quan · 6 tháng · xu hướng · tiền chuyến tài xế). Báo cáo
nào đọc bảng khác (ví dụ cấn trừ đọc thẻ cao tốc, hoá đơn gộp) thì KHÔNG đi qua bộ đệm này.
"""
import datetime as dt
import json
import random
import threading
import time

from sqlalchemy import event, inspect as sa_inspect, text
from sqlalchemy.orm import Session

THEO_PHIEU = {"Trip", "TripExpense", "TripPayment", "TripSection", "TripEvent", "ChungTu", "Voucher", "TripGoods"}
TOAN_BO = {"Route", "RouteStop"}
THEM = {"TripPayment": "thu", "TollCard": "the", "TollCardMove": "the", "Invoice": "hd", "InvoicePayment": "hd",
        "Supplier": "ncc", "SupplierPayment": "ncc", "DriverSettlement": "tt", "Driver": "tx"}
SONG_DB = 7 * 86400         # giây — bản lưu trong DB (lưới an toàn cho sửa tay ngoài ứng dụng)
TOI_DA = 3000              # số bản lưu tối đa trong bộ nhớ một tiến trình (phần lớn là bản của từng ngày, nhỏ)
SONG_TOI_DA = 1800         # giây
_KHO, _KHOA = {}, threading.Lock()
_CO_BANG = []


def _thang(d):
    return d.strftime("%Y-%m") if d else None


def _ngay_thang(d):
    return (d.strftime("%Y-%m"), d.isoformat()) if d else ()


@event.listens_for(Session, "after_flush")
def _sau_khi_ghi(session, _ctx):
    from models import Trip
    thang, tat = set(), False
    with session.no_autoflush:
        for o in list(session.new) + list(session.dirty) + list(session.deleted):
            ten = type(o).__name__
            if ten in THEM:
                thang.add(THEM[ten])
            if ten in TOAN_BO:
                tat = True
            elif ten == "Trip":
                thang.update(_ngay_thang(o.doc_date))
                for d in (sa_inspect(o).attrs.doc_date.history.deleted or ()):     # đổi ngày phiếu: cả ngày / tháng cũ
                    thang.update(_ngay_thang(d))
            elif ten in THEO_PHIEU:
                tid = getattr(o, "trip_id", None)
                if not tid:
                    continue
                p = session.get(Trip, tid)
                if p is None:
                    tat = True
                else:
                    thang.update(_ngay_thang(p.doc_date))
    thang.discard(None)
    if tat:
        thang.add("*")
    if thang:                                # chỉ GOM lại; tăng số một lần lúc commit (_truoc_commit)
        session.info.setdefault("_thang_doi", set()).update(thang)


@event.listens_for(Session, "do_orm_execute")
def _ghi_hang_loat(st):
    if not (st.is_update or st.is_delete):
        return
    m = st.bind_mapper
    if m is not None and (m.class_.__name__ in THEO_PHIEU or m.class_.__name__ in TOAN_BO):
        st.session.info.setdefault("_thang_doi", set()).add("*")
    if m is not None and m.class_.__name__ in THEM:
        st.session.info.setdefault("_thang_doi", set()).add(THEM[m.class_.__name__])


@event.listens_for(Session, "before_commit")
def _truoc_commit(session):
    """Tăng số phiên bản MỘT lần cho cả giao dịch, ngay trước commit, theo thứ tự khoá cố định — hai giao dịch
    cùng ghi không thể giữ khoá của nhau theo hai chiều ngược nhau (không khoá chéo), và giữ khoá chỉ trong tích tắc."""
    session.flush()                          # phần chưa flush của commit này cũng phải được gom
    thang = session.info.pop("_thang_doi", None)
    if thang:
        c = session.connection()
        if not _CO_BANG:                     # DB cũ chưa có bảng (công cụ chạy trước khi máy chủ mới khởi động)
            c.execute(text(_BANG_SQL))
            _CO_BANG.append(True)
        # MỘT câu cho mọi khoá (02/10: trước đây một câu mỗi khoá — tháng + ngày + … — mỗi câu một lượt tới DB ở xa). Dòng ghi
        # theo đúng thứ tự VALUES (đã xếp) nên thứ tự lấy khoá vẫn cố định như cũ; khoá trong tập không trùng nhau.
        ks = sorted(thang)
        c.execute(text("INSERT INTO phien_ban_thang (khoa, so) VALUES %s ON CONFLICT (khoa) DO UPDATE SET so = phien_ban_thang.so + 1"
                       % ", ".join("(:k%d, 1)" % i for i in range(len(ks)))), {"k%d" % i: k for i, k in enumerate(ks)})


@event.listens_for(Session, "after_rollback")
def _sau_huy(session):
    session.info.pop("_thang_doi", None)


def danh_dau_doi(session, cac_ngay):
    """Báo bộ đệm: dữ liệu báo cáo của các NGÀY này (ngày lập phiếu) đổi trong giao dịch đang mở — tăng phiên bản ngày + tháng
    lúc commit như mọi lần ghi phiếu; giao dịch huỷ thì thôi. Dùng cho bảng KHÔNG nằm trong THEO_PHIEU vì phần lớn lần ghi của nó
    không đổi báo cáo: 06/10 chi_luong_tune — luồng nền ghi checked_at mỗi lượt hỏi, chỉ khi một dòng chuyển "đã trả" mới gọi
    hàm này (đưa vào THEO_PHIEU thì cứ 5 phút cả trăm ngày bị tính lại)."""
    k = set()
    for d in cac_ngay:
        k.update(_ngay_thang(d))
    k.discard(None)
    if k:
        session.info.setdefault("_thang_doi", set()).update(k)


_BANG_SQL = "CREATE TABLE IF NOT EXISTS phien_ban_thang (khoa varchar(16) PRIMARY KEY, so integer NOT NULL DEFAULT 0)"
_DON = ("DELETE FROM bao_cao_dem WHERE luc < now() - INTERVAL '3 days' AND khoa NOT LIKE '%, \"\"]'")   # bản gắn "hôm nay" đã qua


def _dam_bao_bang(db):
    """Bảng chưa có (DB chưa chạy máy chủ bản mới) thì dựng — bằng KẾT NỐI RIÊNG, không đụng giao dịch của yêu cầu."""
    if _CO_BANG:
        return
    with db.get_bind().connect() as c:
        c.execute(text(_BANG_SQL)); c.commit()
    _CO_BANG.append(True)


def phien_ban(db, cac_thang):
    _dam_bao_bang(db)
    ks = sorted(set(cac_thang) | {"*"})
    r = dict(db.execute(text("SELECT khoa, so FROM phien_ban_thang WHERE khoa = ANY(:ks)"), {"ks": ks}).all())
    return tuple(r.get(k, 0) for k in ks)


_BANG_DEM = ("CREATE TABLE IF NOT EXISTS bao_cao_dem (khoa varchar PRIMARY KEY, pb varchar NOT NULL, "
             "du_lieu text NOT NULL, luc timestamp NOT NULL DEFAULT now())")
_GHI_DEM = ("INSERT INTO bao_cao_dem (khoa, pb, du_lieu, luc) VALUES (:k, :pb, :d, now()) "
            "ON CONFLICT (khoa) DO UPDATE SET pb = EXCLUDED.pb, du_lieu = EXCLUDED.du_lieu, luc = EXCLUDED.luc")


def lay(db, khoa, cac_thang, tinh, theo_ngay=True, them=()):
    """Kết quả `tinh()` cho `khoa`, dùng lại nếu dữ liệu các khoá `cac_thang` (tháng 'YYYY-MM' hoặc ngày 'YYYY-MM-DD')
    và các khoá riêng `them` chưa đổi kể từ lần tính trước. `theo_ngay=True`: kết quả có dùng "hôm nay" (đi lâu, số
    ngày đi) → sang ngày là tính lại.

    Giá trị trả về là bản lưu (hoặc bản đọc lại từ JSON) — bên gọi không được sửa tại chỗ (cần bỏ khoá thì chép ra)."""
    return lay_nhieu(db, [(khoa, list(cac_thang) + list(them), tinh)], theo_ngay=theo_ngay)[0]


def lay_ngay(db, loai, cac_ngay, tinh_lo):
    """{ngày ISO: phần của ngày đó} — mỗi ngày đệm riêng, khoá phiên bản là CHÍNH NGÀY ĐÓ. Ngày nào thiếu thì
    `tinh_lo(danh sách ngày thiếu)` tính MỘT LƯỢT cho cả nhóm (trả {ngày ISO: phần}) — không tính từng ngày một."""
    viec = [((loai, d.isoformat()), [d.isoformat()], None) for d in cac_ngay]
    ra = lay_nhieu(db, viec, tinh_lo=lambda thieu: (lambda kq: [kq[cac_ngay[i].isoformat()] for i in thieu])(
        tinh_lo([cac_ngay[i] for i in thieu])))
    return {d.isoformat(): v for d, v in zip(cac_ngay, ra)}


def lay_nhieu(db, viec, theo_ngay=False, tinh_lo=None):
    """Như `lay` cho NHIỀU bản cùng lúc (ví dụ 180 ngày của sáu tháng): MỘT câu đọc số phiên bản, MỘT câu đọc bản lưu
    trong DB, chỉ tính những bản còn thiếu, ghi lại trong MỘT kết nối. viec = [(khoa, [khoá phiên bản], tinh), …].
    `tinh_lo(danh sách chỉ số trong viec)` (nếu có) tính một lượt mọi bản còn thiếu, trả danh sách cùng thứ tự."""
    if not viec:
        return []
    _dam_bao_bang(db)
    tat_ca = sorted({k for _, ks, _ in viec for k in ks} | {"*"})
    so = dict(db.execute(text("SELECT khoa, so FROM phien_ban_thang WHERE khoa = ANY(:ks)"), {"ks": tat_ca}).all())
    hom_nay = dt.date.today().isoformat() if theo_ngay else ""
    muc = []
    for i, (khoa, ks, tinh) in enumerate(viec):              # đọc phiên bản TRƯỚC khi tính: ghi xen giữa thì lần sau thấy số mới
        pb = tuple(so.get(k, 0) for k in sorted(set(ks) | {"*"}))
        muc.append([json.dumps([khoa, hom_nay], default=str, ensure_ascii=False), pb, tinh, None, i])
    thieu = []
    with _KHOA:
        for m in muc:
            o = _KHO.get(m[0])
            if o and o[0] == m[1] and time.time() - o[1] < SONG_TOI_DA:
                m[3] = (o[2],)
            else:
                thieu.append(m)
    bind = db.get_bind()
    if thieu:
        try:
            with bind.connect() as c:       # kết nối riêng: không đụng giao dịch của yêu cầu
                luu = {k: (pb, d) for k, pb, d in c.execute(text(
                    "SELECT khoa, pb, du_lieu FROM bao_cao_dem WHERE khoa = ANY(:ks) AND luc > now() - make_interval(secs => :s)"),
                    {"ks": [m[0] for m in thieu], "s": SONG_DB})}
        except Exception:  # noqa: BLE001 — bảng chưa có: dựng rồi tính như thường
            luu = {}
            with bind.connect() as c:
                c.execute(text(_BANG_DEM)); c.commit()
        moi = []
        for m in thieu:
            x = luu.get(m[0])
            if x is not None and x[0] == json.dumps(m[1]):
                m[3] = (json.loads(x[1]),)
            else:
                moi.append(m)
        if moi and tinh_lo is not None:
            for m, v in zip(moi, tinh_lo([m[4] for m in moi])):
                m[3] = (json.loads(json.dumps(v, default=str)),)
        else:
            for m in moi:
                m[3] = (json.loads(json.dumps(m[2](), default=str)),)   # cùng một dạng dù lấy từ bộ nhớ hay từ DB
        if moi:
            try:
                with bind.connect() as c:
                    for m in moi:
                        c.execute(text(_GHI_DEM), {"k": m[0], "pb": json.dumps(m[1]), "d": json.dumps(m[3][0], ensure_ascii=False)})
                    if random.random() < 0.02:
                        c.execute(text(_DON))
                    c.commit()
            except Exception:  # noqa: BLE001 — không ghi được bản lưu thì thôi, kết quả vẫn đúng
                pass
        with _KHOA:
            for m in thieu:
                _KHO[m[0]] = (m[1], time.time(), m[3][0])
            if len(_KHO) > TOI_DA:
                for x in sorted(_KHO, key=lambda z: _KHO[z][1])[:len(_KHO) - TOI_DA]:
                    _KHO.pop(x, None)
    return [m[3][0] for m in muc]


def dem_phieu_theo(db, loai, cot):
    """{giá trị `cot` (cột của bảng trips, ví dụ driver_id): số phiếu} trên MỌI phiếu từ trước tới nay — cộng từ số đếm
    của TỪNG THÁNG (đệm theo tháng: tháng cũ không đổi thì không đếm lại, mỗi lần mở chỉ đếm lại tháng vừa có ghi).
    Đếm thẳng cả bảng thì thời gian tăng theo dữ liệu: 4 năm 0,8 s, 500 GB khoảng nửa phút."""
    from sqlalchemy import func
    from models import Trip
    lo, hi = db.query(func.min(Trip.doc_date), func.max(Trip.doc_date)).one()
    ra = {}
    if lo:
        thang = [dt.date(t // 12, t % 12 + 1, 1) for t in range(lo.year * 12 + lo.month - 1, hi.year * 12 + hi.month)]

        def tinh(idx):
            ds = [thang[i] for i in idx]
            cuoi = max(ds)
            sau = dt.date(cuoi.year + (cuoi.month == 12), cuoi.month % 12 + 1, 1)
            thg = func.date_trunc("month", Trip.doc_date)
            kq = {d: {} for d in ds}
            for t, k, n in (db.query(thg, cot, func.count(Trip.id))
                            .filter(Trip.doc_date >= min(ds), Trip.doc_date < sau, cot.isnot(None)).group_by(thg, cot)):
                if t.date() in kq:
                    kq[t.date()][k] = int(n)
            return [kq[d] for d in ds]
        for phan in lay_nhieu(db, [((loai, d.isoformat()), [d.strftime("%Y-%m")], None) for d in thang], tinh_lo=tinh):
            for k, n in phan.items():
                ra[k] = ra.get(k, 0) + n
    for k, n in db.query(cot, func.count(Trip.id)).filter(Trip.doc_date.is_(None), cot.isnot(None)).group_by(cot):
        ra[k] = ra.get(k, 0) + int(n)           # phiếu chưa có ngày: không thuộc tháng nào, đếm thẳng (thường không có)
    return ra


def xoa_het(db=None):
    """Bỏ mọi bản đã tính (trong bộ nhớ; có `db` thì cả trong DB) — dùng cho bộ kiểm."""
    with _KHOA:
        _KHO.clear()
    if db is not None:
        with db.get_bind().connect() as c:
            c.execute(text(_BANG_DEM)); c.execute(text("DELETE FROM bao_cao_dem")); c.commit()
