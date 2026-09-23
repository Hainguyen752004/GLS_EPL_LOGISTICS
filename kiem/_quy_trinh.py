# -*- coding: utf-8 -*-
"""Lập / sửa phiếu xuất xe ĐÚNG QUY TRÌNH từ 23/09 (anh Khampla A2 · C4.1 · C5.1) — dùng chung cho các bộ kiểm.

Bãi (thabok) không thấy tiền và không nhập tiền. Nên một phiếu "có giá" trong bộ kiểm đi ba bước như người thật:
  1. Bãi lập / sửa phiếu: số lượng, nơi đổ, ai trả — không có giá cước, giá thuê, phí, đơn giá dòng chi.
  2. KT Thu/Chi Viêng Chăn (ketoan) nhập giá cước, giá thuê xe liên kết, phí, ngưỡng tấn.
  3. Người KIỂM từng mục nhập đơn giá dòng chi: KT kho xăng dầu (khonl) mục III, KT Chi phí (ketoancp) IV–VI.
Dòng dầu/phụ tùng lấy từ KHO thì giá là bình quân của kho — máy chủ tự đặt, không ai gõ.

`goi(duong, du_lieu, vai=..., method=...)` là hàm gọi API của từng bộ kiểm; phải đăng nhập sẵn các vai
thabok, ketoan, ketoancp, khonl, admin.
"""
COT_TIEN = ("price", "price_ccy", "price_mode", "hire_price", "hire_ccy", "fee_pct", "over_limit_t", "over_price")
NGUOI_NHAP_GIA = {"fuel": "khonl", "travel": "ketoancp", "repair": "ketoancp", "other": "ketoancp"}
VAI_KHONG_TIEN = ("thabok",)


def _tach(body):
    tien = {k: body[k] for k in COT_TIEN if k in body}
    con = {k: v for k, v in body.items() if k not in COT_TIEN}
    return con, tien


def dat_gia(goi, pid, tien=None, dong_gui=None):
    """Bước 2 + 3: kế toán nhập tiền cho phiếu Bãi vừa lập/sửa. Trả (status, phiếu theo mắt admin)."""
    if tien:
        s, g = goi("/api/trips/%s" % pid, tien, vai="ketoan", method="PUT")
        if s != 200:
            return s, g
    if dong_gui:
        s, full = goi("/api/trips/%s" % pid, vai="admin")
        if s != 200:
            return s, full
        for m, vai in NGUOI_NHAP_GIA.items():
            gui = [d for d in dong_gui if d.get("section") == m]
            that = [e for e in full["expenses"] if e["section"] == m]
            dong = []
            for d, e in zip(gui, that):
                if d.get("unit_price") in (None, "") or e.get("source") == "kho":
                    continue
                dong.append({"id": e["id"], "section": m, "unit_price": d["unit_price"],
                             "currency": d.get("currency") or e.get("currency") or "LAK"})
            if dong:
                s, g = goi("/api/trips/%s" % pid, {"expenses": dong}, vai=vai, method="PUT")
                if s != 200:
                    return s, g
    return goi("/api/trips/%s" % pid, vai="admin")


def lap_phieu(goi, body, vai="thabok"):
    """POST /api/trips theo quy trình. Vai khác Bãi (admin…) thì gửi thẳng như cũ."""
    if vai not in VAI_KHONG_TIEN:
        return goi("/api/trips", body, vai=vai)
    con, tien = _tach(body)
    s, p = goi("/api/trips", con, vai=vai)
    if s != 200:
        return s, p
    return dat_gia(goi, p["id"], tien, body.get("expenses"))


def sua_phieu(goi, pid, body, vai="thabok"):
    """PUT /api/trips/{id} theo quy trình (Bãi sửa số lượng, kế toán nhập lại giá)."""
    if vai not in VAI_KHONG_TIEN:
        return goi("/api/trips/%s" % pid, body, vai=vai, method="PUT")
    con, tien = _tach(body)
    s, p = goi("/api/trips/%s" % pid, con, vai=vai, method="PUT")
    if s != 200:
        return s, p
    return dat_gia(goi, pid, tien, body.get("expenses"))
