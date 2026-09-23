# -*- coding: utf-8 -*-
"""Giá vốn BÌNH QUÂN của kho — anh Khampla chọn ở C5.3 (23/09/2026): "ລາຄາສະເລ່ຍ".

Trước đây dầu xuất kho mang giá do Bãi gõ trên phiếu, còn bán dầu thì lấy giá lần nhập gần nhất.
Hai cách đó cho ra hai giá vốn khác nhau cho cùng một lít dầu trong cùng một kho.

Nay:
  · DẦU: bình quân gia quyền theo TỪNG KHO, tính theo thứ tự thời gian của sổ kho. Mỗi lần nhập cộng
    (lít × giá nhập quy LAK) vào giá trị tồn; mỗi lần xuất (cho xe, bán, chuyển đi) lấy ra theo giá
    bình quân lúc xuất. Giá nhập bằng VND/THB/USD quy LAK theo tỷ giá LÚC NHẬP (ghi vào `unit_cost_lak`),
    để đổi tỷ giá hôm nay không làm đổi giá vốn của dầu đã nằm trong kho.
  · PHỤ TÙNG: `parts.unit_price` chính là giá bình quân — mỗi lần nhập có giá thì tính lại.

Dòng sổ kho cũ chưa ghi kho nào (trước khi có danh mục điểm đổ) thuộc kho Thà Bốc: hồi đó chỉ có một kho.
"""
from models import ExchangeRate, FuelMove, FuelPlace

MA_KHO_GOC = "KHO-TB"


def ty_gia_lak(db, ma):
    ma = (ma or "LAK").upper()
    if ma == "LAK":
        return 1.0
    r = db.get(ExchangeRate, ma)
    return r.rate_to_lak if r else {"USD": 22000, "THB": 700, "VND": 1.2, "CNY": 3000}.get(ma, 1.0)


def kho_goc(db):
    """Id kho Thà Bốc — chủ của các dòng sổ kho cũ không ghi kho."""
    x = db.query(FuelPlace).filter(FuelPlace.code == MA_KHO_GOC).first()
    if x is None:
        x = db.query(FuelPlace).filter(FuelPlace.owner_type == "epl").order_by(FuelPlace.code).first()
    return x.id if x else None


def _gia_nhap_lak(db, m):
    if m.unit_cost_lak is not None:
        return m.unit_cost_lak
    return (m.unit_price or 0) * ty_gia_lak(db, m.currency)


def ton_dau(db, place_id):
    """(số lít tồn, giá bình quân LAK/lít) của một kho dầu, tính cộng dồn theo thời gian."""
    goc = kho_goc(db)
    q = db.query(FuelMove)
    if place_id == goc:
        q = q.filter((FuelMove.place_id == place_id) | (FuelMove.place_id.is_(None)))
    else:
        q = q.filter(FuelMove.place_id == place_id)
    lit, gia_tri, gia = 0.0, 0.0, 0.0
    # dòng cũ chưa có giờ tạo (trước 23/09) đứng TRƯỚC dòng mới cùng ngày — PostgreSQL mặc định để NULL cuối,
    # làm bình quân tính lệch thứ tự và nhảy số giữa hai lần đọc.
    for m in q.order_by(FuelMove.move_date, FuelMove.created_at.asc().nullsfirst(), FuelMove.id).all():
        n = m.qty_l or 0
        if m.kind == "in":
            g = _gia_nhap_lak(db, m)
            lit += n; gia_tri += n * g
            gia = gia_tri / lit if lit > 0 else g
        else:
            # Xuất lấy ra theo GIÁ BÌNH QUÂN HIỆN HÀNH — không theo giá ghi trên dòng xuất. Dòng xuất cũ (trước 23/09)
            # mang giá Bãi gõ; lấy giá đó ra thì giá trị kho ≠ số lít × bình quân và lần nhập sau tính lệch
            # (bấm thử 23/09: kho Thà Bốc ra 33.377 thay vì 33.263 LAK/L). Bình quân chỉ đổi khi NHẬP.
            lit -= n; gia_tri -= n * gia
            if lit <= 0.0001:
                gia_tri = 0.0          # hết dầu thì hết giá trị; giá bình quân giữ số cuối cho lần xuất âm
    return round(lit, 3), round(gia, 2)


def gia_bq_dau(db, place_id):
    return ton_dau(db, place_id or kho_goc(db))[1]


def nhap_phu_tung(part, qty, gia):
    """Nhập phụ tùng có giá → tính lại giá bình quân. Không có giá thì giữ giá cũ."""
    if gia is None or gia <= 0:
        return
    ton = max(part.qty or 0, 0)
    part.unit_price = round((ton * (part.unit_price or 0) + qty * gia) / (ton + qty), 2) if ton + qty > 0 else gia
