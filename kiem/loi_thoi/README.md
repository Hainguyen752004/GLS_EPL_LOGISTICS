# Bộ kiểm lỗi thời

Bộ kiểm thứ đã bỏ / máy, DB không còn dùng — giữ để tra lịch sử, KHÔNG chạy. Mỗi dòng: tệp — lý do (ngày).

- `thu_day_ke_toan.py` — kiểm «không còn đẩy chứng từ sang trang kế toán tạm» và cấu hình / kết nối kho tạm 8031 (`EPL_KETOAN`); kho tạm và trang kế toán tạm đã bỏ 05/10 (`KHO_NGUON=qlsx`, kho ở Web anh Tune) (06/10).
- `thu_bao_cao_cu_moi.py` — so báo cáo với bản `b6dc7cb` (24/09, trước khi tiền dời sang hệ anh Tune 01/10) trên DB `epl_lao` — số đổi có chủ đích, so cũ ↔ mới không còn nghĩa; phần còn giá trị (gọi lại từ bộ đệm y hệt, dòng tổng Theo dõi theo ngày = cả tháng) chuyển vào `kiem/thu_dem_bao_cao.py` phần B, chạy trên d7 (06/10).
- `thu_danh_muc_cu_moi.py` — so danh mục / chờ trả chủ xe / tiền NCC / phiếu lĩnh QR với bản `b6dc7cb` trên `epl_lao` — phần tiền đã sang trang kế toán tạm (đã bỏ) rồi hệ anh Tune, QR phiếu lĩnh đổi; phần còn giá trị (tất toán `tinh_ky_lo` / bảng tháng = `tinh_ky`) chuyển vào `kiem/thu_dem_bao_cao.py` phần C (06/10).
- `thu_ban_hang.py` — bán phụ tùng / dầu, hoá đơn, thu tiền ở trang kế toán tạm 8031 (đã bỏ; bán quầy ở Web anh Tune 06/10); phần đính kèm phiếu quặng trùng `thu_hop_dong_pod.py`, `thu_nen_tep.py` (06/10).
- `thu_chot_22_09.py` — ý còn đúng đã có / đã chuyển: đổi chéo xe nhà ↔ xe liên kết → `thu_vai_va_doi_xe.py`; ảnh tài xế, quyền đặt mã cấu hình → `thu_no_ky_thuat.py`; bảng cấn trừ (và chặn ghi cấn trừ) → `thu_no_tram_dau.py`; công nợ khách → `thu_khach_hang_moi.py`; mã giá vốn PXK_BAN đi theo bán hàng trang kế toán tạm (đã bỏ) (06/10).
- `thu_hai_do.py` — hai DO gom → giao qua sổ kho hàng ở trang kế toán 8031 (đã bỏ); kho hàng ở bãi nay trên trang điều xe, kiểm ở `thu_kho_hang.py` (73 ý) (06/10).
- `thu_sua_chua.py` — lệnh sửa chữa ngoài chuyến ở trang kế toán 8031 (đã bỏ); nay phiếu 48 trên Web anh Tune, trang điều xe chặn đường cũ (`thu_kho_qlsx.py` ca 4) (06/10).
- `thu_tru_hang_quay.py` — trừ phiếu bán quầy của chủ xe ở kho tạm 8031 (giữ chỗ `TUNE-CHO:`, cần máy 8013 + 8031) vào đề nghị trả chủ xe — kho tạm đã bỏ 05/10; nay chủ xe mua ở quầy là SO bán hàng bên Web anh Tune, cấn trừ (collection-offset) khi lập đề nghị trả — kiểm ở `thu_doanh_thu_quay.py` G2 (06/10).
