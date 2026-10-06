# Bộ kiểm lỗi thời

Bộ kiểm thứ đã bỏ / máy, DB không còn dùng — giữ để tra lịch sử, KHÔNG chạy. Mỗi dòng: tệp — lý do (ngày).

- `thu_day_ke_toan.py` — kiểm «không còn đẩy chứng từ sang trang kế toán tạm» và cấu hình / kết nối kho tạm 8031 (`EPL_KETOAN`); kho tạm và trang kế toán tạm đã bỏ 05/10 (`KHO_NGUON=qlsx`, kho ở Web anh Tune) (06/10).
- `thu_bao_cao_cu_moi.py` — so báo cáo với bản `b6dc7cb` (24/09, trước khi tiền dời sang hệ anh Tune 01/10) trên DB `epl_lao` — số đổi có chủ đích, so cũ ↔ mới không còn nghĩa; phần còn giá trị (gọi lại từ bộ đệm y hệt, dòng tổng Theo dõi theo ngày = cả tháng) chuyển vào `kiem/thu_dem_bao_cao.py` phần B, chạy trên d7 (06/10).
- `thu_danh_muc_cu_moi.py` — so danh mục / chờ trả chủ xe / tiền NCC / phiếu lĩnh QR với bản `b6dc7cb` trên `epl_lao` — phần tiền đã sang trang kế toán tạm (đã bỏ) rồi hệ anh Tune, QR phiếu lĩnh đổi; phần còn giá trị (tất toán `tinh_ky_lo` / bảng tháng = `tinh_ky`) chuyển vào `kiem/thu_dem_bao_cao.py` phần C (06/10).
