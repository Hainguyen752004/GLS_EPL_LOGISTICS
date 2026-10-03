# -*- coding: utf-8 -*-
"""TẤT TOÁN ĐỐI TÁC (chủ xe liên kết) — số liệu cho màn "Tất toán đối tác" (chủ dự án chốt 02/10/2026).

Trả đối tác = tiền thuê − phí quản lý − cắt quá tải − tạm ứng EPL đưa (tiền mặt) − nợ nhà cung cấp EPL trả thay − SO nhiên liệu
còn nợ (services/tra_chu_xe.phan_tra). Lập đề nghị thì máy cấn trừ SO nhiên liệu rồi phiếu chi phần còn lại
(services/chi_tune.de_nghi_tra_chu_xe). Ở đây chỉ ĐỌC: gom theo kỳ (tháng xe đi — cùng luật tất toán tài xế) mọi phiếu xe thuê
đã khoá, mỗi đối tác một dòng, và (khi chọn một đối tác) chi tiết từng chuyến tới từng khoản ứng / nợ / dầu.

Giao ước JSON (agent giao diện vẽ theo — thêm khoá được, không đổi tên / bỏ khoá): xem `bang`. Tiền là số; `_lak` = quy Kíp theo
tỷ giá khoá trên phiếu; tiền thuê theo `tien_te` (tiền thuê) của phiếu. Nạp theo lô (một câu mỗi bảng), không mỗi phiếu một câu.
"""
import datetime as dt
import json
from collections import defaultdict

from sqlalchemy import func

from models import (ButToanCho, CanTruTune, ChiChuXeTune, ChiMucTune, ChiTune, GuiSoNhienLieuTune, Owner, Route, Supplier, Trip,
                    TripExpense, Voucher)
from services import but_toan_cho as BTC
from services import so_nhien_lieu as NL
from services import tra_chu_xe as TC
from services.tinh_toan import lam_tron, tien_dong, tinh_phieu, ty_gia


def _khoang(ky):
    dau = dt.date.fromisoformat(ky + "-01")
    return dau, dt.date(dau.year + (dau.month == 12), dau.month % 12 + 1, 1) - dt.timedelta(days=1)


def _iso(d):
    return d.isoformat() if d else None


def _doi(v, r_tu, r_sang, ccy):
    """Đổi một số theo tỷ giá Kíp của phiếu (r_tu → r_sang)."""
    return lam_tron((v or 0) * r_tu / r_sang, ccy) if r_sang else 0


def _nap(db, ky, owner_id=None):
    """Phiếu xe thuê đã khoá trong kỳ + mọi thứ cần cho bảng, mỗi bảng một câu."""
    dau, cuoi = _khoang(ky)
    ngay = func.coalesce(Trip.out_date, Trip.doc_date)
    q = db.query(Trip).filter(Trip.company == "joint", Trip.locked.is_(True), Trip.owner_id.isnot(None), ngay >= dau, ngay <= cuoi)
    if owner_id:
        q = q.filter(Trip.owner_id == owner_id)
    ds = q.order_by(ngay, Trip.doc_no).all()
    ids = [p.id for p in ds] or [""]
    n = {"phieu": ds, "dong": defaultdict(list), "so": {}, "de_nghi": {}, "can_tru": defaultdict(list)}
    for d in db.query(TripExpense).filter(TripExpense.trip_id.in_(ids)).order_by(TripExpense.trip_id, TripExpense.section, TripExpense.line_no):
        n["dong"][d.trip_id].append(d)
    for b in db.query(GuiSoNhienLieuTune).filter(GuiSoNhienLieuTune.trip_id.in_(ids)):
        n["so"][b.trip_id] = b
    chu = sorted({p.owner_id for p in ds}) or [""]
    for r in db.query(ChiChuXeTune).filter(ChiChuXeTune.owner_id.in_(chu)).order_by(ChiChuXeTune.created_at):
        n["de_nghi"][r.id] = r
    for ct in db.query(CanTruTune).filter(CanTruTune.de_nghi_id.in_(list(n["de_nghi"]) or [""])).order_by(CanTruTune.created_at):
        n["can_tru"][ct.de_nghi_id].append(ct)
    n["chu"] = {o.id: o for o in db.query(Owner).filter(Owner.id.in_(chu))}
    return n


def _de_nghi_cua_phieu(n):
    """{Trip.id: đề nghị còn hiệu lực gần nhất} — cùng luật chi_tune._dang_giu (đề nghị lỗi chỉ giữ phiếu khi đã có cấn trừ)."""
    ra = {}
    for r in n["de_nghi"].values():
        if r.status not in ("da_gui", "da_chi", "loi"):
            continue
        if r.status == "loi" and not any(ct.status != "huy" for ct in n["can_tru"].get(r.id, [])):
            continue
        for i in json.loads(r.trip_ids or "[]"):
            ra[i] = r
    return ra


def _tra_cua_de_nghi(r):
    """{Trip.id: (trả thực, trả thực Kíp)} theo số đã chốt lúc lập đề nghị."""
    try:
        t = json.loads(r.tru_hang) if r.tru_hang else {}
    except ValueError:
        t = {}
    return {d["trip_id"]: (d.get("tra_thuc"), d.get("tra_thuc_lak")) for d in t.get("dong") or []}


def xuat_de_nghi(r, cts):
    return {"so": r.ref_no, "id": r.id, "ngay": r.created_at.date().isoformat() if r.created_at else None, "tien": r.amount,
            "tien_lak": r.amount_lak, "tien_te": r.currency, "trang_thai": r.status, "phieu_chi": r.document_no,
            "cach_tra": r.phuong_thuc, "loi": r.error_message if r.status == "loi" else None,
            "trip_ids": json.loads(r.trip_ids or "[]"),
            "can_tru": [{"order_code": ct.order_code, "so_tkn": ct.so_tkn, "tien": ct.amount, "tien_te": ct.currency,
                         "trang_thai": ct.status, "trip_id": ct.trip_id} for ct in cts]}


def _mot_chuyen(p, dong, so, giu, tuyen):
    """Một chuyến: các phần tiền (tra_chu_xe.phan_tra) + trạng thái trả."""
    x = TC.phan_tra(p, dong, so)
    t = tinh_phieu(p, dong)
    r = giu.get(p.id)
    da_tra = bool(p.owner_payment_id or p.owner_paid)
    if da_tra:
        tt, con, con_lak = "da_tra", 0, 0
    elif r is not None:
        tt = "trong_de_nghi"
        con, con_lak = _tra_cua_de_nghi(r).get(p.id, (x["con_tra"], x["con_tra_lak"]))
    else:
        tt, con, con_lak = "chua_tra", x["con_tra"], x["con_tra_lak"]
    x.update({"t": t, "trang_thai_tra": tt, "con_tra_hien": con, "con_tra_hien_lak": con_lak,
              "de_nghi": r, "tuyen": (tuyen.name if tuyen else None) or "%s → %s" % (p.origin or "", p.destination or "")})
    return x


def bang(db, ky, owner_id=None, cap_nhat=False):
    """GET /api/tat-toan-doi-tac — bảng kỳ `ky` (YYYY-MM):

    {ky, tong: {so_doi_tac, tien_thue_lak, phi_lak, qua_tai_lak, tam_ung_lak, no_ncc_lak, nhien_lieu_lak, nhien_lieu_con_no_lak,
                con_tra_lak, da_tra_lak},
     doi_tac: [{owner_id, ten, ma_ke_toan, tien_te, so_phieu, tien_thue, phi, qua_tai, tam_ung, no_ncc, nhien_lieu,
                nhien_lieu_con_no, con_tra, con_tra_lak, trang_thai, de_nghi: [{so, ngay, tien, tien_te, trang_thai, phieu_chi,
                can_tru: [{order_code, so_tkn, tien, trang_thai}]}], …thêm: da_tra, da_tra_lak, so_phieu_chua_tra}],
     chi_tiet: [...từng chuyến — chỉ khi có owner_id (_chi_tiet)]}

    trang_thai đối tác: loi (có đề nghị lỗi) › cho_so_nhien_lieu (chuyến chưa trả có xuất bán mà chưa có SO nhiên liệu) › chua_lap
    (còn chuyến chưa trả, chưa nằm đề nghị) › cho_thu_quy (đề nghị chờ thủ quỹ chi) › da_tra. `cap_nhat`: đọc lại còn nợ SO
    nhiên liệu từ hệ kế toán trước (một lời gọi mỗi đối tác)."""
    n = _nap(db, ky, owner_id)
    if cap_nhat and n["so"]:
        NL.doc_thu(db, [b for b in n["so"].values() if b.status == "synced"])
        db.commit()
    giu = _de_nghi_cua_phieu(n)
    tuyen = {r.id: r for r in db.query(Route).filter(Route.id.in_({p.route_id for p in n["phieu"] if p.route_id} or {""}))}
    theo_chu = defaultdict(list)
    for p in n["phieu"]:
        theo_chu[p.owner_id].append((p, _mot_chuyen(p, n["dong"][p.id], n["so"].get(p.id), giu, tuyen.get(p.route_id))))
    tong = defaultdict(float)
    doi_tac = []
    for oid, ds in theo_chu.items():
        o = n["chu"].get(oid)
        ccy = ds[0][1]["hire_ccy"]
        r0 = ty_gia(ds[0][0], ccy)
        dt_ = defaultdict(float)
        for p, x in ds:
            r = x["ty_gia_thue"]
            for k, gt in (("tien_thue", x["tien_thue"]), ("phi", x["phi"]), ("qua_tai", x["tru_vuot"]), ("tam_ung", x["tam_ung"]),
                          ("no_ncc", x["no_ncc"]), ("nhien_lieu", x["nhien_lieu"])):
                dt_[k] += gt if x["hire_ccy"] == ccy else _doi(gt, r, r0, ccy)
            for k in ("tam_ung", "no_ncc", "nhien_lieu"):
                tong[k + "_lak"] += x[k + "_lak"]
            for k, gt in (("tien_thue", x["tien_thue"]), ("phi", x["phi"]), ("qua_tai", x["tru_vuot"])):
                tong[k + "_lak"] += round((gt or 0) * r)
            con_no = round(x["nhien_lieu_con_no_lak"] or 0)
            dt_["nhien_lieu_con_no"] += _doi(con_no, 1, r0, ccy)
            tong["nhien_lieu_con_no_lak"] += con_no
            dt_["con_tra"] += x["con_tra_hien"] if x["hire_ccy"] == ccy else _doi(x["con_tra_hien"], r, r0, ccy)
            dt_["con_tra_lak"] += x["con_tra_hien_lak"] or 0
            if x["trang_thai_tra"] == "da_tra":
                da = p.owner_paid_usd if p.owner_paid_usd is not None else x["con_tra"]
                dt_["da_tra"] += da if x["hire_ccy"] == ccy else _doi(da, r, r0, ccy)
                dt_["da_tra_lak"] += p.owner_paid_lak if p.owner_paid_lak is not None else x["con_tra_lak"]
        tong["con_tra_lak"] += dt_["con_tra_lak"]
        tong["da_tra_lak"] += dt_["da_tra_lak"]
        chua = [x for _, x in ds if x["trang_thai_tra"] == "chua_tra"]
        dn = {x["de_nghi"].id: x["de_nghi"] for _, x in ds if x["de_nghi"] is not None}.values()
        ids = {p.id for p, _ in ds}
        chua_xong = {p.id for p, x in ds if x["trang_thai_tra"] != "da_tra"}
        tat_ca_dn = [r for r in n["de_nghi"].values() if r.owner_id == oid and ids & set(json.loads(r.trip_ids or "[]"))]
        if any(r.status == "loi" and chua_xong & set(json.loads(r.trip_ids or "[]")) for r in tat_ca_dn):
            tt = "loi"                              # đề nghị hỏng còn dính chuyến chưa trả — gửi lại hoặc bỏ
        elif any(x["cho_so"] for x in chua):
            tt = "cho_so_nhien_lieu"
        elif chua:
            tt = "chua_lap"
        elif any(r.status == "da_gui" for r in dn):
            tt = "cho_thu_quy"
        else:
            tt = "da_tra"
        doi_tac.append({
            "owner_id": oid, "ten": (o.name if o else None) or ds[0][0].owner_name, "ma_ke_toan": NL.ma_doi_tac(ds[0][0]),
            "tien_te": ccy, "so_phieu": len(ds), "so_phieu_chua_tra": len(chua),
            **{k: lam_tron(dt_[k], ccy) for k in ("tien_thue", "phi", "qua_tai", "tam_ung", "no_ncc", "nhien_lieu", "nhien_lieu_con_no",
                                                 "con_tra", "da_tra")},
            "con_tra_lak": round(dt_["con_tra_lak"]), "da_tra_lak": round(dt_["da_tra_lak"]), "trang_thai": tt,
            "de_nghi": [xuat_de_nghi(r, n["can_tru"].get(r.id, [])) for r in sorted(tat_ca_dn, key=lambda r: r.created_at or dt.datetime.min,
                                                                                   reverse=True)]})
    doi_tac.sort(key=lambda d: (d["ten"] or ""))
    ra = {"ky": ky, "tong": dict({"so_doi_tac": len(doi_tac)}, **{k: round(tong[k]) for k in (
        "tien_thue_lak", "phi_lak", "qua_tai_lak", "tam_ung_lak", "no_ncc_lak", "nhien_lieu_lak", "nhien_lieu_con_no_lak",
        "con_tra_lak", "da_tra_lak")}), "doi_tac": doi_tac}
    if owner_id:
        ra["chi_tiet"] = _chi_tiet(db, n, theo_chu.get(owner_id, []))
    return ra


def _khoan(db, d, ten="khoan"):
    """Tên khoản một dòng: {<ten>: tên Việt, <ten>_lo: tên Lào, item_key} — màn dịch theo khoá chuẩn khi có (03/10)."""
    from services.ban_giao import _ten
    vi, lo = _ten(db, d)
    return {ten: vi, ten + "_lo": lo, "item_key": d.item_key}


def _chi_tiet(db, n, ds):
    """Chi tiết từng chuyến của MỘT đối tác (giao ước `chi_tiet[]`):
    {trip_id, doc_no, ngay, tuyen, xe, tai_xe, tan_tinh, gia_thue, tien_te, tien_thue, phi_pct, phi, qua_tai_t, qua_tai,
     tam_ung: {so_ptu, phieu_chi, tien, tien_lak, dong: [{khoan, sl, don_gia, tien_te, tien_lak}]},
     no_ncc: [{khoan, nha_cung_cap, tien_lak, but_toan}],
     nhien_lieu: {order_code, trang_thai: chua_tao | da_tao | da_thu | can_tru | null, tien_lak, da_thu_lak, con_no_lak,
                  dong: [{mat_hang, lit, gia_ban, tien_lak, gia_von_lak}]},
     con_tra, con_tra_lak, trang_thai_tra: chua_tra | trong_de_nghi | da_tra, so_de_nghi}
    Thêm: muc từng dòng, no_ncc[].phieu_chi (garage quỹ trả ngay mục V), tra_truoc_can_tru, can_tru, can_tru_lak, da_tra; 03/10 —
    tam_ung.dong[] / no_ncc[] thêm khoan_lo + item_key, nhien_lieu.dong[] thêm mat_hang_lo + item_key (_khoan)."""
    ids = [p.id for p, _ in ds] or [""]
    ptu, chi = {}, {}
    for v in db.query(Voucher).filter(Voucher.trip_id.in_(ids), Voucher.kind == "advance", Voucher.status != "huy"):
        ptu[v.trip_id] = v
    for r in db.query(ChiTune).filter(ChiTune.trip_id.in_(ids)):
        chi[r.voucher_id] = r
    gl = {}
    for r in db.query(ButToanCho).filter(ButToanCho.trip_id.in_(ids), ButToanCho.nguon == BTC.NO_NCC, ButToanCho.status != "huy"):
        for x in json.loads(r.dong or "[]"):
            if isinstance(x, dict) and x.get("ref"):
                gl[x["ref"]] = r
    quy = {}
    for r in db.query(ChiMucTune).filter(ChiMucTune.trip_id.in_(ids), ChiMucTune.status != "huy"):
        for i in json.loads(r.expense_ids or "[]"):
            quy[i] = r
    ncc = {s.id: s.name for s in db.query(Supplier).filter(Supplier.id.in_({d.supplier_id for p, _ in ds for d in n["dong"][p.id]
                                                                              if d.supplier_id} or {""}))}
    can_tru = {}
    for cts in n["can_tru"].values():
        for ct in cts:
            if ct.status != "huy":
                can_tru[ct.trip_id] = ct
    MUC = {"fuel": "III", "travel": "IV", "repair": "V", "other": "VI"}
    ra = []
    for p, x in ds:
        t, h = x["t"], x["hire_ccy"]
        dong = n["dong"][p.id]
        v = ptu.get(p.id)
        rc = chi.get(v.id) if v is not None else None
        tm_ids = {d.id for d in x["dong_tam_ung"]}
        ban_ids = {d.id for d in x["dong_ban"]}
        no = []
        for d in dong:
            if d.paid_by_epl is False or d.id in tm_ids or d.id in ban_ids or (d.qty or 0) <= 0:
                continue
            lak = round(tien_dong(p, d))
            if lak <= 0:
                continue
            b, q = gl.get(d.id), quy.get(d.id)
            no.append({**_khoan(db, d), "muc": MUC.get(d.section), "nha_cung_cap": ncc.get(d.supplier_id), "tien_lak": lak,
                       "but_toan": b.so_ben_ke_toan if b is not None else None,
                       "phieu_chi": q.document_no if q is not None else None})
        so = n["so"].get(p.id)
        ct = can_tru.get(p.id)
        if not x["dong_ban"] and so is None:
            nl_tt = None
        elif so is None or so.status != "synced":
            nl_tt = "chua_tao"
        elif ct is not None and ct.status == "da_gui":
            nl_tt = "can_tru"
        elif (NL.con_no_lak(so) or 0) <= NL.LECH:
            nl_tt = "da_thu"
        else:
            nl_tt = "da_tao"
        r_de_nghi = x["de_nghi"]
        ra.append({
            "trip_id": p.id, "doc_no": p.doc_no, "ngay": _iso(p.out_date or p.doc_date), "tuyen": x["tuyen"], "xe": p.truck_no,
            "tai_xe": p.driver_name, "tan_tinh": t.get("tan_tinh"), "gia_thue": t.get("gia_thue"), "tien_te": h,
            "tien_thue": x["tien_thue"], "phi_pct": p.fee_pct if p.fee_pct is not None else 2, "phi": x["phi"],
            "qua_tai_t": t.get("vuot_tan"), "qua_tai": x["tru_vuot"],
            "tam_ung": {"so_ptu": v.doc_no if v is not None else None, "phieu_chi": rc.document_no if rc is not None else None,
                        "trang_thai": rc.status if rc is not None else (v.status if v is not None else None),
                        "tien": x["tam_ung"], "tien_lak": x["tam_ung_lak"],
                        "dong": [{**_khoan(db, d), "muc": MUC.get(d.section), "sl": d.qty, "don_gia": d.unit_price,
                                  "tien_te": d.currency or "LAK", "tien_lak": round(tien_dong(p, d))} for d in x["dong_tam_ung"]]},
            "no_ncc": no,
            "nhien_lieu": {"order_code": so.order_code if so is not None and so.status == "synced" else None, "trang_thai": nl_tt,
                           "tien_lak": x["nhien_lieu_lak"], "da_thu_lak": (so.thu_da_thu or 0) if so is not None and so.status == "synced" else 0,
                           "con_no_lak": x["nhien_lieu_con_no_lak"], "so_tkn": ct.so_tkn if ct is not None else None,
                           "dong": [{**_khoan(db, d, "mat_hang"), "muc": MUC.get(d.section), "lit": d.qty,
                                     "gia_ban": d.sale_price if d.sale_price is not None else None,
                                     "tien_lak": round(tien_dong(p, d)),
                                     "gia_von_lak": round((d.qty or 0) * (d.unit_price or 0) * ty_gia(p, d.currency))}
                                    for d in x["dong_ban"]]},
            "tra_truoc_can_tru": x["tra_truoc_can_tru"], "can_tru": x["can_tru"], "can_tru_lak": x["can_tru_lak"],
            "con_tra": x["con_tra_hien"], "con_tra_lak": x["con_tra_hien_lak"], "trang_thai_tra": x["trang_thai_tra"],
            "so_de_nghi": r_de_nghi.ref_no if r_de_nghi is not None else None,
            "da_tra": p.owner_paid_usd if x["trang_thai_tra"] == "da_tra" else None,
            "da_tra_lak": p.owner_paid_lak if x["trang_thai_tra"] == "da_tra" else None})
    return ra
