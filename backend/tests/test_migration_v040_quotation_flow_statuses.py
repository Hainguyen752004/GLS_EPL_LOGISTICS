# -*- coding: utf-8 -*-
"""Bốn trạng thái xương sống của luồng báo giá phải được PostgreSQL cho phép.

LỖI ĐÃ ĐO ĐƯỢC TRÊN POSTGRESQL THẬT, bằng giao dịch rồi hoàn tác nên không ghi
gì. Ràng buộc `ck_quotations_canonical_status` chỉ cho năm giá trị — `draft`,
`sent`, `approved`, `cancelled`, `unknown` — trong khi mã nguồn của luồng báo
giá mới ghi thêm bốn giá trị nữa:

    ✗ pending_approval   gửi khách khi biên dưới ngưỡng  -> BỊ CHẶN
    ✗ accepted           khách chấp nhận                 -> BỊ CHẶN
    ✗ rejected           khách từ chối                   -> BỊ CHẶN
    ✗ split              đã tách ra lệnh giao hàng       -> BỊ CHẶN

Và 8 trong 10 case demo (7 `split` + 1 `pending_approval`) **không tồn tại
được** trên PostgreSQL.

VÌ SAO NÓ VÔ HÌNH LÂU HƠN LẦN TRƯỚC. Ở mốc `032` (trạng thái `arrived` của lệnh
giao hàng) thì `models.py` CÓ khai `CheckConstraint`, nên SQLite dựng từ mô hình
có ngay ràng buộc mới và chỉ PostgreSQL bị trôi. Lần này `models.py` KHÔNG khai
`CheckConstraint` nào cho `quotations`, nên SQLite **không có ràng buộc gì cả**
và nhận mọi giá trị. Cả hai bên đều "chạy trơn": một bên không kiểm gì, bên kia
kiểm theo một danh sách đã cũ. Không một bài kiểm nào chạy trên SQLite có thể
phát hiện ra.

Bài kiểm này khóa ba chiều để chuyện đó không lặp lại:

  1. Tập trạng thái trong mốc `040` phải PHỦ HẾT những giá trị mà mã nguồn thật
     sự ghi. Đọc trực tiếp từ `bao_gia_service.py` và `workflow_service.py` —
     thêm một trạng thái mới trong mã mà quên mốc thì bài này đỏ ngay.
  2. Ràng buộc không được nới quá rộng: một giá trị bịa phải vẫn bị chặn.
  3. Mốc có trong chuỗi, và câu SQL nó sinh ra đúng tên ràng buộc.
"""

import os
import re

from migrations.runner import MIGRATIONS
from migrations import v040_quotation_flow_statuses as v040


GOC_APP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEP_GHI_TRANG_THAI = (
    os.path.join(GOC_APP, "app", "services", "bao_gia_service.py"),
    os.path.join(GOC_APP, "app", "services", "workflow_service.py"),
)

#: Chỉ bắt phép gán TRÊN ĐỐI TƯỢNG BÁO GIÁ (`q.canonical_status = "..."`).
#:
#: Bản đầu của phép quét này bắt mọi `canonical_status = "..."` trong hai tệp,
#: và nó lẫn ngay: hai tệp đó cũng TẠO lệnh giao hàng, nên `pending`,
#: `in_transit`, `delivered`, `confirmed` bị đếm vào như thể là trạng thái báo
#: giá. Bài kiểm đỏ vì một lý do sai, và cách "sửa" dễ nhất lúc đó là thêm
#: `pending` vào `v040.TRANG_THAI` — tức nới ràng buộc của báo giá cho một giá
#: trị mà báo giá không bao giờ dùng. Một bài kiểm dẫn người sửa tới chỗ sai
#: thì tệ hơn không có.
#:
#: Trong cả hai tệp, biến giữ bản ghi báo giá luôn tên là `q`. Phép quét hẹp
#: cho đúng bảy giá trị: accepted, approved, draft, pending_approval, rejected,
#: sent, split.
MAU_QUET = re.compile(r'\bq\.canonical_status\s*=\s*"([a-z_]+)"')


def _trang_thai_ma_nguon_ghi():
    """Quét các phép gán trạng thái báo giá trong hai tệp dịch vụ.

    Quét mã nguồn thay vì viết cứng một danh sách ở đây là có chủ ý: một danh
    sách viết cứng trong bài kiểm sẽ trôi khỏi mã nguồn đúng như ràng buộc đã
    trôi, và lúc đó bài kiểm này thành vô dụng.
    """
    thay = set()
    for duong in TEP_GHI_TRANG_THAI:
        with open(duong, encoding="utf-8-sig") as f:
            thay.update(MAU_QUET.findall(f.read()))
    return thay


def test_moc_040_phu_het_trang_thai_ma_nguon_that_su_ghi():
    ma_nguon = _trang_thai_ma_nguon_ghi()
    assert ma_nguon, "khong quet ra trang thai nao — phep quet da hong"
    thieu = sorted(ma_nguon - set(v040.TRANG_THAI))
    assert not thieu, (
        "moc 040 chua cho phep %s. Ma nguon ghi cac gia tri nay, nen moi lan ghi "
        "chung se VO tren PostgreSQL. Them chung vao `v040.TRANG_THAI` va viet "
        "mot moc moi de noi rang buoc." % ", ".join(thieu)
    )


def test_bon_trang_thai_tung_bi_chan_deu_co_trong_moc():
    """Bon gia tri da do duoc la bi chan tren PostgreSQL that."""
    for tt in ("pending_approval", "accepted", "rejected", "split"):
        assert tt in v040.TRANG_THAI, tt


def test_khong_noi_rang_buoc_qua_rong():
    """Rang buoc phai VAN chan gia tri la.

    Noi qua rong thi ta doi mot loi hien ra thanh mot loi im lang: mot trang
    thai viet sai chinh ta se duoc ghi vao va khong ai biet.
    """
    cau = " ".join(v040.statements("postgresql", "upgrade"))
    assert "canonical_status IN (" in cau
    for bia in ("trang_thai_bia", "", "any"):
        assert "'%s'" % bia not in cau


def test_cau_sql_dung_ten_rang_buoc_va_them_cot_items_notes():
    cau = v040.statements("postgresql", "upgrade")
    gop = " ".join(cau)
    assert "ck_quotations_canonical_status" in gop
    assert "DROP CONSTRAINT IF EXISTS" in gop, "phai bo rang buoc cu truoc khi dat cai moi"
    assert "items ADD COLUMN IF NOT EXISTS notes" in gop, (
        "cot `items.notes` co trong models.py ma khong co tren PostgreSQL — "
        "mot cho troi nua tim ra trong cung lan doi chieu"
    )


def test_phep_lui_doi_du_lieu_truoc_khi_that_lai_rang_buoc():
    """Thu tu nay bat buoc: that lai rang buoc truoc thi lenh ADD CONSTRAINT vo
    vi cac dong dang o trang thai moi khong dat duoc rang buoc cu."""
    cau = v040.statements("postgresql", "rollback")
    vi_tri_update = next(i for i, c in enumerate(cau) if c.startswith("UPDATE quotations"))
    vi_tri_add = next(i for i, c in enumerate(cau) if "ADD CONSTRAINT" in c)
    assert vi_tri_update < vi_tri_add
    # Va phai doi DUNG bon gia tri chi co o ban moi, khong doi bua cac dong khac.
    cau_update = cau[vi_tri_update]
    for tt in ("pending_approval", "accepted", "rejected", "split", "expired"):
        assert "'%s'" % tt in cau_update, tt
    for tt in ("draft", "sent", "approved", "cancelled"):
        assert "'%s'" % tt not in cau_update.split("WHERE")[1], (
            "%s la trang thai HOP LE ca truoc va sau — khong duoc doi no" % tt
        )


def test_moc_nay_da_duoc_dang_ky_trong_chuoi():
    # So bang CHUOI `VERSION`, khong bang dinh danh module: `MIGRATIONS` co the
    # duoc nap lai va dinh danh doi, con chuoi thi khong.
    assert v040.VERSION in [m.VERSION for m in MIGRATIONS]


def test_sqlite_khong_bi_that_chat_hon_postgresql():
    """SQLite KHONG duoc dat mot rang buoc rieng cho `quotations`.

    `models.py` khong khai `CheckConstraint` cho bang do, nen dat mot rang buoc
    chi co o SQLite se lam SQLite nghiem ngat hon PostgreSQL — dung nguoc lai
    voi van de moc nay di chua. Nguon su that chi co mot cho.
    """
    cau = v040.statements("sqlite", "upgrade")
    assert cau == [], "moc nay khong duoc sinh SQL cho SQLite qua `statements`"
