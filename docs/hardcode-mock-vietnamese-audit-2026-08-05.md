# Báo Cáo Rà Soát Hardcode, Mock Data Và Tiếng Việt

Ngày kiểm tra: 05/08/2026

## Kết luận nhanh

Hệ thống đã được rà theo 3 nhóm: backend runtime, frontend runtime và nội dung demo/test phụ. Các điểm runtime có khả năng làm sai luồng thật đã được xử lý:

- Không còn trả GPS/POD giả khi chưa có dữ liệu.
- Không còn tự lập hóa đơn bằng khách hàng/số tiền mặc định.
- Không còn tự tạo sự cố bằng DO/xe/vị trí mặc định.
- Không còn fallback DO demo khi cập nhật POD trên frontend.
- Action Agent không còn báo "đã cập nhật thành công" khi thực tế chỉ bóc tách bản nháp.
- Scanner `ftfy` không phát hiện dòng mojibake thật trong backend/frontend chính.

## Các chỗ đã sửa

1. `backend/app/main.py`
   - `/api/tracking/{do_id}`: nếu chưa có GPS thì trả lỗi tiếng Việt `TRACKING_NOT_FOUND`, yêu cầu điều phối/cập nhật GPS.
   - `/api/pod/{do_id}`: nếu chưa có POD thì trả lỗi `POD_NOT_FOUND`, yêu cầu cập nhật chứng từ POD.
   - `/api/invoices/post`: bắt buộc có `do_id`, lấy khách hàng và số tiền từ DO/SO; không dùng khách hàng/số tiền mặc định.
   - `/api/incidents`: bắt buộc nhập DO, xe, loại sự cố, vị trí, người báo cáo.
   - `/api/data/all`: bỏ các fallback như ngày mặc định, tài xế mặc định, xe mặc định, giá bán mặc định.

2. `frontend/js/app.js`
   - Form tạo DO không tự điền `SO-2026-001`.
   - Xác nhận SO gửi trạng thái `Confirmed` đúng luồng.
   - POD không còn fallback `DO-2026-004`.
   - Khi lập hóa đơn từ POD chỉ gửi `do_id`; backend tự lấy nguồn dữ liệu thật.

3. `backend/app/agents/action_agent.py`
   - Không còn mock thông báo tạo SO/DO thành công.
   - Chỉ trả bản nháp và hướng người dùng sang đúng màn hình cấu hình/xác nhận.

## Các chỗ còn có dữ liệu mẫu nhưng không phải runtime nghiệp vụ chính

Các file sau vẫn chứa dữ liệu ví dụ/dàn cảnh để test hoặc minh họa UI. Không nên dùng các trang này khi demo khách hàng nếu yêu cầu "100% dữ liệu thật":

- `frontend/test_100_scenarios.html`
- `frontend/test_1000_scenarios.html`
- `frontend/test_5000_scenarios.html`
- `frontend/test_e2e.html`
- `frontend/smart_factory_demo.html`

Trong `frontend/index.html` vẫn có một số placeholder/VD như biển số xe, DO mẫu, tên người liên hệ. Đây là text hướng dẫn trên giao diện hoặc HTML tĩnh; khi chạy luồng demo thật, dữ liệu phải lấy từ Master Data và API.

## Kiểm tra đã chạy

- Backend tests: `53 passed`
- Backend compile: pass
- Frontend JS syntax: pass
- Frontend JSON parse: pass
- DB thật: `integrity_check = ok`, `foreign_key_check = 0`

## Lưu ý trước demo khách hàng

Không chạy seed/reset tự động trước demo. Nếu cần dữ liệu demo sạch, nhập theo kịch bản Master Data trong tài liệu `KICH_BAN_DEMO_KHACH_HANG_MASTERDATA_A_Z.md`.
