# -*- coding: utf-8 -*-
"""QUYỀN TRÊN MỘT PHIẾU XUẤT XE cho màn Web (Việc 11 chuyển trang điều xe sang module Vận tải C#, 08/10/2026).

Màn cũ (frontend/modules/phieu-xuat-xe/phieu-xuat-xe.js) chép các luật của máy chủ vào JS để ẩn / khoá ô và nút: bảng QUYEN, suaDuoc,
suaTienDuoc, suaKeToanDuoc, suaPodDuoc, veVaiVaTrangThai (nút từng mục, việc mức phiếu), tabMacDinh. Chuẩn Web (tài liệu 02, 04
§14.1) không cho ghi cứng vai / quyền trong trình duyệt → các luật đó tính ở ĐÂY, từ bản phiếu đã xuất (routes/phieu.xuat_phieu) +
vai người gọi, và đi kèm phiếu dưới khoá "quyen". Máy chủ vẫn là nơi quyết: route chặn 403 / 409 như cũ; bảng này chỉ để Web hiện
đúng ô / nút. Mỗi luật ghi dòng gốc bên JS để soi khi một bên đổi.

Hình dạng:
    {"vai", "moi", "bi_khoa", "thay_tien_ban", "thay_tien_chi", "thay_gia_kho",
     "o": {tên ô: {"sua": bool, "an": bool}}            # ô mục I · II · POD · số phiếu · hợp đồng
     "muc": {mục: {"trang_thai", "nhan", "sua", "sua_tien", "tuy_chon", "viec": [send · verify · return · book · pay · unlock], "co_viec"}},
     "phieu": [khoa · mo-khoa · transit · doi-xe · arrived · xoa], "tab_mac_dinh": mục | "all",
     "hang": {"bang", "tu_lo", "sua", "gui", "nhac_can_mo", "nhac"},       # bảng Hàng trên phiếu (mục II)
     "cach_tra": {"travel": bool, "other": bool}}                          # đổi được cách trả dòng mục IV / VI
"""
from services import phan_quyen as PQ

MUC = ("info", "trans", "fuel", "travel", "repair", "other")
MUC_CHI = ("fuel", "travel", "repair", "other")
VAI_SAU_KHOA = ("acct", "expacct", "rev", "treasury", "cash", "fuel", "admin")   # = routes.phieu.VAI_SAU_KHOA
COT_INFO = ("kind", "company", "owner_name", "vehicle_id", "brand_model", "plate_head", "plate_trailer", "driver_id", "doc_date",
            "out_date", "back_date", "odo_out", "odo_back")
COT_TRANS = ("customer_id", "route_id", "goods_type", "ore_bill_no", "ore_bill_date", "origin", "destination", "weight_origin",
             "weight_dest", "price", "price_ccy", "price_mode", "hire_price", "hire_ccy", "fee_pct", "over_limit_t", "over_price")
COT_TIEN = ("price", "price_ccy", "price_mode", "hire_price", "hire_ccy", "fee_pct", "over_limit_t", "over_price")
COT_KE_TOAN = ("ore_bill_no", "ore_bill_date")            # kế toán nhập khi nhận giấy (anh Khampla C3.7)
COT_POD = ("pod_no", "pod_date", "pod_receiver")
CHO_XE_VE = {"info": ("back_date", "odo_back"), "trans": ("weight_dest",)}   # điền khi xe về / tới (chủ dự án 29/09)


def _la(vai, *ds):
    """= AUTH.la của màn cũ: Sếp (admin) luôn qua."""
    return vai == "admin" or vai in ds


def quyen(p, vai, moi=False):
    """`p` = bản phiếu đã xuất (dict của xuat_phieu, day_du) — phiếu mới: {} hoặc vài ô mặc định; `vai` = vai người gọi."""
    p = p or {}
    q = PQ.QUYEN.get(vai, PQ.QUYEN["yard"])
    admin = vai == "admin"
    sec = p.get("sections") or {}
    st = lambda m: "wait" if moi else (sec.get(m) or "wait")                                       # noqa: E731
    dong = p.get("expenses") or []
    co_dong = lambda m: any(d.get("section") == m for d in dong)                                   # noqa: E731
    bi_khoa = (not moi) and bool(p.get("locked")) and vai not in VAI_SAU_KHOA                      # JS 341 biKhoa
    gom = (p.get("kind") or "giao") == "gom"
    da_nhap_kho = gom and not moi and p.get("transport_status") == "arrived"                       # JS 201 daNhapKho
    chua_ve = moi or p.get("transport_status") != "arrived"

    def sua(m):                                                                                   # JS 344 suaDuoc
        if moi:
            return admin or m in q["edit"]
        if bi_khoa:
            return False
        return admin or (m in q["edit"] and st(m) in ("wait", "entered"))

    def sua_tien(m):                                                                              # JS 350 suaTienDuoc
        if moi:
            return True
        if bi_khoa:
            return False
        return admin or (m in q["verify"] and st(m) in ("wait", "entered"))

    def sua_ke_toan(m):                                                                           # JS 349 suaKeToanDuoc
        if bi_khoa:
            return False
        return admin or (m in q["verify"] and st(m) in ("wait", "entered"))

    tien_ban = PQ.thay_tien_ban(vai)
    o = {}
    for m, cot in (("info", COT_INFO), ("trans", COT_TRANS)):                                     # JS 398 (ô mục I · II)
        khoa = not sua(m)
        for c in cot:
            if c in COT_KE_TOAN:
                duoc = sua_ke_toan(m)
            else:
                duoc = not ((khoa and not (c in COT_TIEN and sua_tien(m))) or (da_nhap_kho and c in ("weight_origin", "weight_dest")))
            if c in CHO_XE_VE.get(m, ()) and chua_ve:                                             # JS 403–408
                duoc = False
            o[c] = {"sua": bool(duoc), "an": c in COT_TIEN and not tien_ban}                      # Bãi không thấy tiền bán
    o["doc_no"] = {"sua": sua("info"), "an": False}                                               # JS 392
    pod = (not moi) and _la(vai, "yard", "acct", "rev") and not bi_khoa                           # JS 387 suaPodDuoc
    for c in COT_POD:
        o[c] = {"sua": pod, "an": False}
    hd = _la(vai, "acct", "rev") and not bi_khoa                                                  # routes.phieu._ap_hop_dong
    o["contract_id"] = {"sua": hd, "an": not tien_ban}
    o["hire_contract_id"] = {"sua": hd, "an": not tien_ban}

    # mục IV xe nhà không có tạm ứng tiền mặt (06/10) — chữ trạng thái sau ghi sổ (JS 524–528)
    iv_khong_tm = (not moi) and p.get("company") != "joint" and not any(d.get("tien_mat_tx") for d in dong) \
        and any(d.get("section") == "travel" and d.get("paid_by_epl") for d in dong)
    iv_cung_luong = any(d.get("section") == "travel" and d.get("paid_by_epl") and d.get("cach_tra") == "luong" for d in dong)

    def nhan(m, s):                                                                               # JS 527 khoaTT
        if m == "travel" and s in ("booked", "paid") and iv_khong_tm:
            return "stt_iv_luong" if iv_cung_luong else "stt_iv_khong_tm"
        if s == "wait":
            return "stt_wait2"
        if s == "verified" and m not in MUC_CHI:
            return "stt_verified_12"
        return "stt_" + s

    def co_viec(m, s):                                                                            # JS 485 coViec
        if moi:
            return m == "info"
        return (m in q["edit"] and s in ("wait", "entered")) or (m in q["verify"] and s == "entered") \
            or (m in q["book"] and s == "verified") or (m in q["pay"] and s == "booked" and not (m == "travel" and iv_khong_tm))

    muc = {}
    tra_duoc = not p.get("locked") or admin                                                       # JS 417
    for m in MUC:
        s = st(m)
        tuy_chon = m in ("repair", "other") and not moi and not co_dong(m)
        viec = []
        if not moi and not tuy_chon:                                                              # JS 413–426
            if s == "wait" and (admin or m in q["edit"]):
                viec.append("send")
            if s == "entered" and (admin or m in q["verify"]):
                viec.append("verify")
                if tra_duoc:
                    viec.append("return")
            if s == "verified" and m in MUC_CHI and (admin or m in q["book"]):
                viec.append("book")
            if s == "verified" and tra_duoc and (admin or m in q["verify"]):
                viec.append("return")
            cm = (p.get("chi_muc_ke_toan") or {}).get(m) or {}
            chi_kt = not admin and ((m == "travel" and (p.get("chi_tam_ung") or {}).get("o_ke_toan"))
                                    or (cm.get("o_ke_toan") and (cm.get("so_dong_con") or 0) > 0))
            if s == "booked" and not chi_kt and (admin or m in q["pay"]):
                viec.append("pay")
            if admin and s not in ("wait", "entered"):
                viec.append("unlock")
        muc[m] = {"trang_thai": s, "nhan": "stt_na" if tuy_chon else nhan(m, s), "sua": sua(m),
                  "sua_tien": sua_tien(m), "tuy_chon": tuy_chon, "viec": viec, "co_viec": co_viec(m, s)}

    phieu = []                                                                                    # JS 441–455
    if not moi:
        tts, khoa = p.get("transport_status"), bool(p.get("locked"))
        if _la(vai, "acct") and tts == "arrived" and not khoa:
            phieu.append("khoa")
        if _la(vai, "acct") and khoa and (not p.get("da_tao_so") or admin):
            phieu.append("mo-khoa")
        if _la(vai, "yard") and not khoa and tts == "dispatched":
            phieu.append("transit")
        if _la(vai, "yard") and not khoa and tts != "arrived":
            phieu.append("doi-xe")
            phieu.append("arrived")
        if _la(vai, "yard") and not khoa and all(st(m) in ("wait", "entered") for m in MUC):
            phieu.append("xoa")

    # bảng "Hàng trên phiếu" (JS 204–223 · 921): DO gom một mặt hàng không có bảng (máy ghi dòng từ Loại hàng + Cân tại mỏ); cột "Lấy
    # từ lô" chỉ DO giao; gom đã về bãi là hàng đã vào kho — bảng và hai ô cân đóng; câu nhắc dưới bảng theo đúng ca
    hang_that = [g for g in (p.get("goods") or []) if g.get("loai") != "hao_hut"]
    gom_mot_dong = gom and len(hang_that) <= 1
    hang = {"bang": not gom_mot_dong, "tu_lo": not gom, "sua": sua("trans") and not da_nhap_kho,
            "gui": sua("trans") and not gom_mot_dong, "nhac_can_mo": gom and not da_nhap_kho,
            "nhac": "goods_locked_gom" if da_nhap_kho else ("goods_hint_gom" if gom else "goods_hint_giao")}

    # tab mở sẵn theo vai (JS 493 tabMacDinh)
    if moi:
        tab = "info"
    else:
        cua = [m for m in MUC if m in q["edit"] or m in q["verify"] or m in q["book"] or m in q["pay"]]
        if not cua or admin:
            tab = "all"
        else:
            rong = lambda m: m in ("repair", "other") and not co_dong(m)                         # noqa: E731
            tab = next((m for m in cua if not rong(m) and co_viec(m, st(m))), cua[0])
    return {"vai": vai, "moi": moi, "bi_khoa": bi_khoa, "thay_tien_ban": tien_ban, "thay_tien_chi": PQ.thay_tien_chi(vai),
            "thay_gia_kho": PQ.thay_gia_kho(vai), "o": o, "muc": muc, "phieu": phieu, "tab_mac_dinh": tab, "hang": hang,
            # ô Cách trả dòng mục IV / VI (08/10): chỉ KT Chi phí VC lúc kiểm mục (cùng lúc nhập đơn giá) và Sếp — Bãi không chọn
            "cach_tra": {m: PQ.doi_cach_tra(vai) and sua_tien(m) for m in ("travel", "other")},
            # nút mở tờ đề nghị (11c): vai máy chủ cho lập tờ tạm ứng / xuất nhiên liệu · vai xem phiếu đề nghị thu (JS 1254–1257)
            "lap_de_nghi": _la(vai, "yard", "acct", "expacct", "fuel", "cash", "treasury"),
            "xem_de_nghi_thu": _la(vai, "acct", "expacct", "rev", "treasury", "cash", "fuel")}
