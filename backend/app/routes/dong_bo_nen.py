# -*- coding: utf-8 -*-
"""TÌNH TRẠNG TỰ ĐỒNG BỘ NỀN với hệ kế toán anh Tune (06/10) — services/dong_bo_nen.py.

    GET /api/dong-bo-nen     (Sếp) bật / tắt, chu kỳ, giới hạn mỗi lượt, lượt gần nhất (lúc chạy, số bản ghi đã hỏi / đã cập nhật
                             theo loại, lỗi lượt đó, lỗi gần nhất) — đọc từ bảng cau_hinh nên đúng cho mọi worker.

Chỉ xem: không có nút chạy tay (bấm Cập nhật trên từng màn vẫn hỏi lại ngay như cũ). Không có màn giao diện riêng.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from services import dong_bo_nen as DBN
from services.bao_mat import can_vai

router = APIRouter()


@router.get("/api/dong-bo-nen")
def tinh_trang(db: Session = Depends(get_db), user=Depends(can_vai("admin"))):
    return DBN.tinh_trang(db)
