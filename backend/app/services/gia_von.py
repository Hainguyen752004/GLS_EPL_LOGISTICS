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
from models import ExchangeRate, FuelPlace

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


# Tồn, giá bình quân dầu và phụ tùng dời sang trang kế toán (28/09): services/gia_von_dau.py bên EPL_KETOAN tính đúng
# thuật toán cũ; bên này hỏi qua services/kho_ke_toan.py. Không tính tồn từ sổ bên này nữa — sổ đó đứng yên từ ngày dời.
