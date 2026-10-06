# Bộ kiểm lỗi thời

Các bài dưới đây kiểm thứ hệ thống đã bỏ, hoặc trùng bài khác. Giữ lại để tra cứu, không chạy nữa.

- `thu_ban_hang.py`: kiểm bán phụ tùng, dầu, hoá đơn và thu tiền ở trang kế toán tạm 8031. Phần này đã bỏ; bán quầy nay ở Web anh Tune (06/10). Phần đính kèm phiếu quặng trùng `thu_hop_dong_pod.py` và `thu_nen_tep.py`.
- `thu_chot_22_09.py`: các ý chính đã chuyển hoặc đã có ở bài khác.
  - Đổi chéo xe nhà ↔ xe liên kết: `thu_vai_va_doi_xe.py`.
  - Ảnh tài xế và quyền đặt mã cấu hình: `thu_no_ky_thuat.py`.
  - Bảng cấn trừ (và chặn ghi cấn trừ): `thu_no_tram_dau.py`.
  - Công nợ khách: `thu_khach_hang_moi.py`.
  - Phần mã giá vốn PXK_BAN đi theo bán hàng ở trang kế toán tạm, nên đã bỏ cùng phần bán hàng đó.
- `thu_hai_do.py`: kiểm hai DO gom → giao nối nhau qua sổ kho hàng ở trang kế toán 8031, chỗ đã bỏ. Kho hàng ở bãi nay thuộc trang điều xe và đã có `thu_kho_hang.py` (73 ý) kiểm.
- `thu_sua_chua.py`: kiểm lệnh sửa chữa ngoài chuyến ở trang kế toán 8031, đã bỏ. Nay sửa chữa ngoài chuyến lập phiếu 48 trên Web anh Tune; trang điều xe chặn đường cũ (`thu_kho_qlsx.py`, ca 4).
