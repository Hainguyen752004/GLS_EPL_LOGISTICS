# -*- coding: utf-8 -*-
"""HỒ SƠ DO HAI BÊN — màn "Đề nghị theo DO" (modules/chung-tu), chủ dự án 02/10/2026. CHỈ ĐỌC.

Một DO đi qua hai hệ: bên ĐIỀU XE (trang này) đề nghị chi / xuất kho / thu và ghi các khoản không qua tiền; bên KẾ TOÁN (QLSX
anh Tune) lập chứng từ thật — phiếu chi, SO, bút toán tổng hợp. Màn này đặt hai bên cạnh nhau theo bảy nhóm:

    tam_ung   Tạm ứng                tờ PTU                         ↔ phiếu chi "Chi trước" (CTR)
    chi_muc   Chi mục V / VI          mục V · VI (quỹ trả ngay)      ↔ phiếu chi "Chi khác" (CKH)
    xuat_kho  Xuất kho                tờ PLNL · phụ tùng lấy kho     ↔ bút toán xuất nội bộ / xuất bán (GL…)
    but_toan  Thuê xe · nợ NCC        khoá phiếu                     ↔ bút toán 621/4022 · …/4021 (GL…)
    thu       Đề nghị thu             tờ PDT                         ↔ SO dịch vụ vận chuyển (TK-…) + đã thu + bút toán doanh thu
                                                                         1211/708 (GL…, ghi lúc Tạo SO — 06/10)
    so_nl     SO nhiên liệu (xe thuê) dòng kho xuất bán             ↔ SO nhiên liệu + cấn trừ TKN + bút toán doanh thu 1211/707 (06/10)
    tra_dt    Trả đối tác (xe thuê)   đề nghị TCX                    ↔ phiếu chi "Chi khác"

Mỗi nhóm: {ap_dung, muc, em: [tờ bên điều xe], kt: [chứng từ bên kế toán], ghi_chu}. `muc` là một chữ cho cả nhóm:
    khong    không phát sinh                 chua     bên điều xe chưa làm xong phần mình (chưa ghi sổ, chưa khoá, kho chưa cấp…)
    cho_gui  đã ghi, chờ gửi sang kế toán     cho_kt   kế toán đã có chứng từ, chờ chi / thu / ghi sổ chính thức
    xong     xong cả hai bên                  loi      chưa sang được kế toán / chờ bút toán đảo

    GET /api/ho-so-do?thang=YYYY-MM&q=     mỗi DO một dòng + bảy nhóm (không gói dòng — nhẹ, nạp theo lô)
    GET /api/ho-so-do/{trip_id}            một DO: bảy nhóm + từng dòng tiền và chứng từ của nó (ban_giao.dong_goi → settlement)

Quyền như màn Đề nghị theo DO (routes/de_nghi.py): tài xế và ba vai một việc (thủ kho, kho phụ tùng, tổ sửa) không vào. Vai
không thấy tiền CHI (Bãi) không nhận số tiền chi; không thấy tiền BÁN thì không nhận cước, tiền thuê, tiền trả đối tác; số tiền
bút toán chỉ cho vai xem màn Bút toán chờ gửi (but_toan_cho.VAI_XEM). Không ghi gì, không hỏi sang hệ kế toán — trạng thái là
bản chép lần đọc lại gần nhất của từng đường.
"""
import datetime as dt
import json
import logging
from collections import defaultdict

import models as M

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session

from database import get_db
from models import (ButToanCho, ChiChuXeTune, ChiMucTune, ChiTune, ChungTu, FuelPlace, GuiSoTune, Trip, TripExpense,
                    TripSection, Voucher)
from services.bao_mat import nguoi_hien_tai
from services.phan_quyen import thay_tien_ban, thay_tien_chi
from services.tinh_toan import cach_tra, la_tien_mat_tai_xe, la_xuat_ban, tien_dong, tinh_phieu

router = APIRouter()
GIOI_HAN = 400
KHONG_XEM = ("driver", "depot", "parts", "repair")           # đúng KHONG_XEM_THEO_DO + tài xế (routes/de_nghi.py)
LOAI_PDT = "PDT"                                             # de_nghi_thu.LOAI
VAI_XEM_BT = ("acct", "expacct", "admin")                    # but_toan_cho.VAI_XEM — vai xem số tiền bút toán
NGUON_XK = ("xuat_noi_bo", "xuat_ban")
NGUON_GL = ("thue_xe", "no_ncc", "cung_luong")       # 06/10: cung_luong Nợ 625 / Có 4201 lúc khoá (xe nhà)
# 06/10: bút toán doanh thu ghi lúc «Tạo SO bên kế toán» (services/but_toan_cho.ghi_doanh_thu) — hiện cạnh SO của nó
NGUON_DT_CUOC, NGUON_DT_BAN = "doanh_thu", "doanh_thu_ban"
THU_TU_MUC = {"loi": 0, "chua": 1, "cho_gui": 2, "cho_kt": 3, "xong": 4}
MUC_V = {"repair": "V", "other": "VI"}
HANG = {"da_chi": 3, "da_gui": 2, "loi": 1}


def _chan(user):
    if user.role in KHONG_XEM:
        raise HTTPException(403, {"ma": "KHONG_CO_QUYEN", "loi": "Vai %s không có màn Đề nghị theo DO." % user.role})


def _thang(thang):
    try:
        dau = dt.date.fromisoformat((thang or dt.date.today().strftime("%Y-%m"))[:7] + "-01")
    except ValueError:
        raise HTTPException(422, {"ma": "THANG_SAI", "loi": "Tháng phải có dạng YYYY-MM."})
    cuoi = (dau.replace(day=28) + dt.timedelta(days=4)).replace(day=1) - dt.timedelta(days=1)
    return dau, cuoi


def _ngay(v):
    return v.isoformat() if v else None


# ================================================================ nạp theo lô
def _nap(db, ds):
    """Mọi bản ghi của các phiếu `ds`, mỗi bảng MỘT câu hỏi (không hỏi từng phiếu)."""
    ma = [p.id for p in ds]
    N = {"vs": defaultdict(list), "ct": {}, "dong": defaultdict(list), "muc": defaultdict(dict), "cmt": defaultdict(list),
         "btc": defaultdict(list), "pdt": {}, "so": {}, "cx": defaultdict(list), "kho": {}, "ncc": set()}
    if not ma:
        return N
    vs = db.query(Voucher).filter(Voucher.trip_id.in_(ma), Voucher.status != "huy").order_by(Voucher.doc_no).all()
    for v in vs:
        N["vs"][v.trip_id].append(v)
    ung = [v.id for v in vs if v.kind == "advance"]
    if ung:
        N["ct"] = {c.voucher_id: c for c in db.query(ChiTune).filter(ChiTune.voucher_id.in_(ung))}
    for d in db.query(TripExpense).filter(TripExpense.trip_id.in_(ma)).order_by(TripExpense.section, TripExpense.line_no):
        N["dong"][d.trip_id].append(d)
    for s in db.query(TripSection).filter(TripSection.trip_id.in_(ma)):
        N["muc"][s.trip_id][s.section] = s.status
    for r in (db.query(ChiMucTune).filter(ChiMucTune.trip_id.in_(ma), ChiMucTune.status != "huy")
              .order_by(ChiMucTune.section, ChiMucTune.lan)):
        N["cmt"][r.trip_id].append(r)
    for r in db.query(ButToanCho).filter(ButToanCho.trip_id.in_(ma), ButToanCho.status != "huy").order_by(ButToanCho.ngay):
        N["btc"][r.trip_id].append(r)
    for c in db.query(ChungTu).filter(ChungTu.trip_id.in_(ma), ChungTu.loai == LOAI_PDT):
        N["pdt"].setdefault(c.trip_id, c)
    for b in db.query(GuiSoTune).filter(GuiSoTune.trip_id.in_(ma)):
        N["so"][b.trip_id] = b
    chu = {p.owner_id for p in ds if p.company == "joint" and p.owner_id}
    if chu:
        trong = set(ma)
        for r in db.query(ChiChuXeTune).filter(ChiChuXeTune.owner_id.in_(list(chu)), ChiChuXeTune.status != "huy"):
            try:
                ids = json.loads(r.trip_ids or "[]")
            except ValueError:
                ids = []
            for tid in ids:
                if tid in trong:
                    N["cx"][tid].append(r)
    # SO nhiên liệu xe thuê (agent 1, 02/10: models.GuiSoNhienLieuTune · CanTruTune). Máy chưa dựng bảng (chưa khởi động lại với
    # model mới) thì nhóm so_nl giữ "sắp có" — điểm lưu (savepoint) để câu hỏi hỏng không làm hỏng cả giao dịch đọc.
    SoNL, CanTru = getattr(M, "GuiSoNhienLieuTune", None), getattr(M, "CanTruTune", None)
    N["so_nl"], N["can_tru"], N["co_so_nl"] = {}, defaultdict(list), False
    if SoNL is not None:
        try:
            with db.begin_nested():
                for b in db.query(SoNL).filter(SoNL.trip_id.in_(ma)):
                    N["so_nl"][b.trip_id] = b
                if CanTru is not None:
                    for c in db.query(CanTru).filter(CanTru.trip_id.in_(ma), CanTru.status != "huy"):
                        N["can_tru"][c.trip_id].append(c)
            N["co_so_nl"] = True
        except Exception:  # noqa: BLE001 — bảng chưa có
            N["so_nl"], N["can_tru"] = {}, defaultdict(list)
    N["kho"] = {k.id: k.name for k in db.query(FuelPlace)}
    if any(d.section == "repair" for x in N["dong"].values() for d in x):
        from routes.nha_cung_cap import khoan_muc_ncc
        N["ncc"] = khoan_muc_ncc(db)
    return N


# ================================================================ bảy nhóm
def _nhom(p, N, chi, ban, xem_bt):
    """Bảy nhóm "bên điều xe ↔ bên kế toán" của một phiếu."""
    lk = p.company == "joint"
    dong = N["dong"][p.id]
    vs = N["vs"][p.id]
    st = N["muc"][p.id]
    btc = N["btc"][p.id]
    tien = (lambda v: v) if chi else (lambda v: None)

    def gl(r):
        x = {"loai": "gl", "nguon": r.nguon, "so": r.so_ben_ke_toan or r.ma_ben_ke_toan, "ref": r.source_ref,
             "tt": "can_dao" if r.can_dao else r.status, "loi": bool(r.status == "cho_gui" and (r.error_code or r.loi_gui)),
             "chinh_thuc": r.tune_status == 12, "ngay": _ngay(r.ngay)}
        if xem_bt:
            x.update({"id": r.id, "tien": r.tong, "ccy": r.tien_te})
        return x

    def muc_gl(ds_gl):
        if not ds_gl:
            return None
        if any(x["tt"] == "can_dao" or x["loi"] for x in ds_gl):
            return "loi"
        if any(x["tt"] == "cho_gui" for x in ds_gl):
            return "cho_gui"
        return "xong" if all(x["chinh_thuc"] for x in ds_gl) else "cho_kt"

    def gop(muc, ds_gl):
        """06/10: mức của nhóm SO gộp thêm bút toán doanh thu của SO đó — lấy mức KÉM hơn (lỗi › chưa › chờ gửi › chờ kế toán ›
        xong). DO tạo SO trước 06/10 không có bút toán doanh thu → giữ mức theo SO như cũ."""
        m = muc_gl(ds_gl)
        if m is None or muc not in THU_TU_MUC:
            return muc
        return m if THU_TU_MUC[m] < THU_TU_MUC[muc] else muc

    ra = {}

    # ---- 1. tạm ứng: tờ PTU ↔ phiếu chi "Chi trước"
    tu = next((v for v in vs if v.kind == "advance"), None)
    rec = N["ct"].get(tu.id) if tu is not None else None
    co_tm = any(la_tien_mat_tai_xe(d, p.company) for d in dong)
    g = {"ap_dung": bool(tu or co_tm), "em": [], "kt": [], "ghi_chu": None}
    if tu is not None:
        g["em"].append({"loai": "ptu", "so": tu.doc_no, "tt": tu.status, "tien_lak": tien(tu.amount_lak)})
    if rec is not None:
        g["kt"].append({"loai": "ctr", "so": rec.document_no, "tt": "phieu_mat" if rec.error_code == "PHIEU_CHI_MAT" else rec.status,
                        "tien_lak": tien(rec.amount_lak), "loi": rec.error_message if rec.status == "loi" else None})
    if not g["ap_dung"]:
        g["muc"] = "khong"
    elif tu is None:
        g["muc"], g["ghi_chu"] = "chua", "chua_lap_ptu"
    elif rec is None:
        g["muc"], g["ghi_chu"] = ("xong", "chi_tai_quy") if tu.status == "da_cap" else ("chua", "cho_ghi_so_iv")
    else:
        g["muc"] = {"da_chi": "xong", "da_gui": "cho_kt"}.get(rec.status, "loi")
    g["hinh_thuc"] = "cong_no_chu_xe" if lk else "noi_bo"
    ra["tam_ung"] = g

    # ---- 2. chi mục V / VI quỹ trả ngay ↔ phiếu chi "Chi khác"
    cmt = N["cmt"][p.id]
    g = {"em": [], "kt": [], "ghi_chu": None}
    for s, la in MUC_V.items():
        recs = [r for r in cmt if r.section == s]
        quy = [d for d in dong if d.section == s and s == "repair" and d.paid_by_epl and d.source != "kho"
               and not la_tien_mat_tai_xe(d, p.company) and not d.ghi_no and not d.toll_card_id
               and not (d.supplier_id is None and d.item_key in N["ncc"])]
        if not recs and not quy:
            continue
        g["em"].append({"loai": "muc", "muc": la, "tt": st.get(s, "wait"), "so": recs[-1].ref_no if recs else None,
                        "so_dong": len(quy), "tien_lak": tien(round(sum(tien_dong(p, d) for d in quy)))})
        for r in recs:
            g["kt"].append({"loai": "ckh", "muc": la, "so": r.document_no, "ref": r.ref_no, "tt": r.status,
                            "tien_lak": tien(r.amount_lak), "loi": r.error_message if r.status == "loi" else None})
    g["ap_dung"] = bool(g["em"])
    if not g["ap_dung"]:
        g["muc"] = "khong"
    elif not g["kt"]:
        g["muc"], g["ghi_chu"] = "chua", "cho_ghi_so_v"
    elif any(x["tt"] == "loi" for x in g["kt"]):
        g["muc"] = "loi"
    else:
        g["muc"] = "xong" if all(x["tt"] == "da_chi" for x in g["kt"]) else "cho_kt"
    ra["chi_muc"] = g

    # ---- 3. xuất kho: PLNL · phụ tùng kho ↔ bút toán xuất nội bộ / xuất bán
    nl = [v for v in vs if v.kind == "fuel"]
    pt = [d for d in dong if d.section == "repair" and d.source == "kho"]
    dau_kho = [d for d in dong if d.section == "fuel" and d.source == "kho"]
    xk = [gl(r) for r in btc if r.nguon in NGUON_XK]
    g = {"ap_dung": bool(nl or pt or dau_kho or xk), "ghi_chu": None, "hinh_thuc": "xuat_ban" if lk else "noi_bo",
         "em": [{"loai": "plnl", "so": v.doc_no, "tt": v.status, "lit": v.granted_qty if v.granted_qty is not None else v.qty_l,
                 "kho": N["kho"].get(v.place_id)} for v in nl], "kt": xk}
    if pt:
        g["em"].append({"loai": "pt_kho", "n": len(pt), "da_xuat": sum(1 for d in pt if d.stock_move_id)})
    if not g["ap_dung"]:
        g["muc"] = "khong"
    elif any(v.status == "cho" for v in nl) or any(not d.stock_move_id for d in pt):
        g["muc"], g["ghi_chu"] = "chua", "cho_kho_cap"
    elif not p.locked:
        g["muc"], g["ghi_chu"] = "chua", "cho_khoa"
    else:
        g["muc"] = muc_gl(xk) or "chua"
        if not xk:
            g["ghi_chu"] = "khoa_truoc_luat"
    ra["xuat_kho"] = g

    # ---- 4. thuê xe · nợ nhà cung cấp ↔ bút toán GL (ghi lúc khoá phiếu)
    bt = [gl(r) for r in btc if r.nguon in NGUON_GL]
    co_ncc = any(d.ghi_no or (d.section in ("travel", "other") and cach_tra(d, p.company) == "ncc") for d in dong
                 if not (lk and d.paid_by_epl is False))
    co_luong = not lk and any(d.section in ("travel", "other") and d.paid_by_epl is not False and cach_tra(d, p.company) == "luong"
                              and (d.qty or 0) * (d.unit_price or 0) > 0 for d in dong)
    g = {"ap_dung": bool(lk or co_ncc or co_luong or bt), "em": [{"loai": "khoa", "tt": "da_khoa" if p.locked else "chua_khoa",
                                                                  "thue": lk, "ncc": co_ncc, "luong": co_luong}], "kt": bt, "ghi_chu": None}
    if not g["ap_dung"]:
        g["muc"], g["em"] = "khong", []
    elif not p.locked:
        g["muc"], g["ghi_chu"] = "chua", "cho_khoa"
    else:
        g["muc"] = muc_gl(bt) or "chua"
        if not bt:
            g["ghi_chu"] = "khoa_truoc_luat"
    ra["but_toan"] = g

    # ---- 5. đề nghị thu ↔ SO dịch vụ vận chuyển
    c, b = N["pdt"].get(p.id), N["so"].get(p.id)
    tt_thu = ("cho_khoa" if not p.locked else
              ("da_thu" if b.thu_trang_thai == "da_thu" else "thu_mot_phan" if b.thu_trang_thai == "thu_mot_phan" else "da_tao_so")
              if b is not None and b.status == "synced" else ("chua_lap" if c is None else "cho_gui"))
    g = {"ap_dung": True, "em": [{"loai": "pdt", "so": c.so if c is not None else None, "tt": tt_thu}], "kt": [], "ghi_chu": None}
    if ban:
        t = tinh_phieu(p, dong)
        g["em"][0].update({"tien": t["doanh_thu"], "ccy": t["ccy"]})
    if b is not None:
        x = {"loai": "so", "so": b.order_code, "tt": (b.thu_trang_thai or "chua_thu") if b.status == "synced" else b.status,
             "loi": b.error_message if b.status != "synced" else None}
        if ban and b.status == "synced":
            x.update({"tong": b.thu_tong if b.thu_tong is not None else b.total_amount, "da_thu": b.thu_da_thu,
                      "con_no": b.thu_con_no, "ccy": b.currency})
        g["kt"].append(x)
    dt_cuoc = [gl(r) for r in btc if r.nguon == NGUON_DT_CUOC]       # 06/10: Nợ 1211 / Có 708 theo SO cước
    g["kt"].extend(dt_cuoc)
    if not p.locked:
        g["muc"], g["ghi_chu"] = "chua", "cho_khoa"
    elif b is None or b.status not in ("synced", "failed", "conflict"):
        g["muc"], g["ghi_chu"] = "chua", "cho_tao_so"
    elif b.status != "synced":
        g["muc"] = "loi"
    else:
        g["muc"] = gop("xong" if b.thu_trang_thai == "da_thu" else "cho_kt", dt_cuoc)
    ra["thu"] = g

    # ---- 6. SO nhiên liệu (xe thuê): dòng kho xuất bán ↔ SO bên kế toán ghi công nợ đối tác (+ cấn trừ TKN lúc trả đối tác)
    xb = [d for d in dong if lk and la_xuat_ban(p, d) and d.paid_by_epl is not False]
    b, cts = N["so_nl"].get(p.id), N["can_tru"][p.id]
    if not N["co_so_nl"]:
        ra["so_nl"] = {"ap_dung": bool(xb), "muc": "chua" if xb else "khong", "em": [], "kt": [], "ghi_chu": "sap_co", "sap_co": True}
    else:
        g = {"ap_dung": bool(xb or b), "em": [], "kt": [], "ghi_chu": None}
        if xb:
            g["em"].append({"loai": "nl_em", "so_dong": len(xb), "tien_lak": round(sum(tien_dong(p, d) for d in xb)) if ban else None})
        if b is not None:
            ok = b.status == "synced"
            da_tru = any(c.status == "da_gui" for c in cts)
            tt = ("loi" if not ok else "da_thu" if b.thu_trang_thai == "da_thu" else
                  "can_tru" if da_tru and (b.thu_con_no is not None and b.thu_con_no <= 0.5) else "da_tao")
            g["kt"].append({"loai": "nl_so", "so": b.order_code, "tt": tt, "loi": b.error_message if not ok else None,
                            "con_no_lak": b.thu_con_no if ban and ok and (b.currency or "LAK") == "LAK" else None})
            for c in cts:
                g["kt"].append({"loai": "tkn", "so": c.so_tkn, "ref": c.ref_no, "tt": c.status,
                                "tien_lak": c.amount if ban else None, "loi": c.error_message if c.status == "loi" else None})
        dt_ban = [gl(r) for r in btc if r.nguon == NGUON_DT_BAN]        # 06/10: Nợ 1211 / Có 707 theo SO nhiên liệu
        g["kt"].extend(dt_ban)
        if not g["ap_dung"]:
            g["muc"] = "khong"
        elif not p.locked:
            g["muc"], g["ghi_chu"] = "chua", "cho_khoa"
        elif b is None:
            g["muc"], g["ghi_chu"] = "chua", "nl_cho_tao"
        elif g["kt"][0]["tt"] == "loi" or any(x["tt"] == "loi" for x in g["kt"][1:] if x["loai"] == "tkn"):
            g["muc"] = "loi"
        else:
            g["muc"] = gop("xong" if g["kt"][0]["tt"] in ("da_thu", "can_tru") else "cho_kt", dt_ban)
        ra["so_nl"] = g

    # ---- 7. trả đối tác (xe thuê): đề nghị TCX ↔ phiếu chi "Chi khác"
    g = {"ap_dung": lk, "em": [], "kt": [], "ghi_chu": None}
    if lk:
        tot = None
        for r in N["cx"][p.id]:
            if tot is None or HANG.get(r.status, 0) > HANG.get(tot.status, 0):
                tot = r
        if tot is not None:
            g["em"].append({"loai": "tcx", "so": tot.ref_no, "tt": tot.status, "tien": tot.amount if ban else None,
                            "ccy": tot.currency, "so_phieu": len(json.loads(tot.trip_ids or "[]"))})
            g["kt"].append({"loai": "ckh", "so": tot.document_no, "tt": tot.status,
                            "loi": tot.error_message if tot.status == "loi" else None})
        elif (p.owner_payment_id or "").startswith("TUNE:"):
            g["kt"].append({"loai": "ckh", "so": p.owner_payment_id[5:], "tt": "da_chi"})
        if not p.locked:
            g["muc"], g["ghi_chu"] = "chua", "cho_khoa"
        elif not g["kt"]:
            g["muc"], g["ghi_chu"] = ("xong", "tra_trang_tam") if p.owner_paid else ("chua", "cho_de_nghi_tra")
        else:
            g["muc"] = {"da_chi": "xong", "da_gui": "cho_kt"}.get(g["kt"][0]["tt"], "loi")
    else:
        g["muc"] = "khong"
    ra["tra_dt"] = g
    return ra


def _co_ban(p):
    return {"trip_id": p.id, "doc_no": p.doc_no, "doc_date": _ngay(p.doc_date), "out_date": _ngay(p.out_date),
            "back_date": _ngay(p.back_date), "kind": p.kind, "company": p.company,
            "owner_id": p.owner_id if p.company == "joint" else None, "owner_name": p.owner_name if p.company == "joint" else None,
            "truck_no": p.truck_no, "driver_name": p.driver_name, "customer_name": p.customer_name,
            "origin": p.origin, "destination": p.destination, "transport_status": p.transport_status,
            "locked": bool(p.locked), "locked_at": p.locked_at.isoformat(timespec="minutes") if p.locked_at else None}


def _vai(user):
    return thay_tien_chi(user.role), thay_tien_ban(user.role), user.role in VAI_XEM_BT


# ================================================================ danh sách
@router.get("/api/ho-so-do")
def ds_ho_so(thang: str = "", q: str = "", db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    _chan(user)
    chi, ban, xem_bt = _vai(user)
    dau, cuoi = _thang(thang)
    qs = db.query(Trip).filter(Trip.doc_date >= dau, Trip.doc_date <= cuoi)
    if q and q.strip():
        k = "%" + q.strip() + "%"
        qs = qs.filter(or_(Trip.doc_no.ilike(k), Trip.truck_no.ilike(k), Trip.driver_name.ilike(k), Trip.customer_name.ilike(k),
                           Trip.owner_name.ilike(k)))
    ds = qs.order_by(Trip.doc_date.desc(), Trip.doc_no.desc()).limit(GIOI_HAN).all()
    N = _nap(db, ds)
    return {"thang": dau.strftime("%Y-%m"), "thay_tien_chi": chi, "thay_tien_ban": ban, "xem_but_toan": xem_bt,
            "ds": [{**_co_ban(p), "nhom": _nhom(p, N, chi, ban, xem_bt)} for p in ds],
            "gioi_han": GIOI_HAN if len(ds) >= GIOI_HAN else None}


# ================================================================ một DO
COT_DONG = ("line_no", "kind", "section", "section_name", "item_key", "name", "name_lo", "qty", "source", "paid_by",
            "sale_to_owner", "ghi_no", "line_key", "settlement")
COT_TIEN = ("unit_price", "calculation", "actual_amount", "currency", "amount_lak", "acc_code")


def _dong_goi(db, p, chi, ban):
    """Từng dòng tiền của DO và chứng từ của nó (ban_giao.dong_goi, settlement) — bỏ số tiền theo vai."""
    from services import ban_giao as BG
    goi = BG.dong_goi(db, p)
    ra = []
    for x in goi.get("details") or []:
        thu = x.get("kind") == "thu"
        if thu and not ban:
            continue                                         # dòng cước là tiền bán
        d = {k: x.get(k) for k in COT_DONG}
        if (ban if thu else chi):
            d.update({k: x.get(k) for k in COT_TIEN})
            if thu and x.get("debt"):
                d["debt"] = x["debt"]
        ra.append(d)
    h = goi.get("header") or {}
    thue = None
    if ban and isinstance(h.get("hire"), dict):
        hh = h["hire"]
        thue = {k: hh.get(k) for k in ("currency", "unit_price", "amount", "amount_lak", "fee_pct", "fee", "over_t",
                                       "over_deduction", "advanced_by_epl", "pay_owner", "pay_owner_lak", "acc_code",
                                       "settlement", "journal")}
    # SO nhiên liệu của DO xe thuê (header.fuel_so, agent 1 02/10) — tiền bán cho đối tác: vai thấy tiền bán mới nhận
    fuel_so = h.get("fuel_so") if ban and isinstance(h.get("fuel_so"), dict) else None
    return ra, thue, fuel_so


@router.get("/api/ho-so-do/{trip_id}")
def mot_ho_so(trip_id: str, db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    _chan(user)
    chi, ban, xem_bt = _vai(user)
    p = db.get(Trip, trip_id)
    if p is None:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có phiếu này."})
    N = _nap(db, [p])
    # gói DO (ban_giao.dong_goi) hỏng thì vẫn trả bảy nhóm — tab "Từng dòng tiền" báo không đọc được, ghi log để xem
    loi_dong = None
    try:
        with db.begin_nested():
            dong, thue, fuel_so = _dong_goi(db, p, chi, ban)
    except Exception:  # noqa: BLE001
        logging.getLogger("epl_lao.ho_so_do").exception("Không dựng được gói DO %s", p.id)
        dong, thue, fuel_so, loi_dong = [], None, None, "Không đọc được từng dòng tiền của DO này (xem log máy chủ)."
    x = {**_co_ban(p), "contract_no": p.contract_no, "hire_contract_no": p.hire_contract_no if p.company == "joint" else None,
         "pod_no": p.pod_no, "weight_origin": p.weight_origin, "weight_dest": p.weight_dest}
    return {"do": x, "thay_tien_chi": chi, "thay_tien_ban": ban, "xem_but_toan": xem_bt,
            "nhom": _nhom(p, N, chi, ban, xem_bt), "dong": dong, "thue": thue, "fuel_so": fuel_so, "loi_dong": loi_dong}
