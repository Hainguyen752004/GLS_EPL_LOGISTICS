# TMS Core 4 – Execution Events và GPS bất biến

## Mục tiêu

Xây dựng chuỗi sự kiện thực thi cho Freight Order theo nguyên tắc chỉ ghi thêm, đủ thông tin “việc gì, lúc nào, ở đâu, nguồn nào và vì sao”, đồng thời giữ tương thích với màn GPS/POD hiện hữu.

## Kiến trúc và dữ liệu

Migration `006_tms_execution_events` tạo:

- `transport_events`: ID, Freight Order, loại sự kiện, thời điểm thực tế, tọa độ, địa điểm, nguồn, thiết bị, lý do/ghi chú, người tạo, thời điểm ghi nhận và `idempotency_key` duy nhất theo Freight Order.
- `transport_event_documents`: metadata chứng từ gắn với sự kiện, gồm loại chứng từ, URL lưu trữ, tên file, MIME type, checksum và người tải lên. Core 4 không lưu blob vào PostgreSQL.
- `freight_order_legacy_links`: ánh xạ một-một Freight Order mới với Delivery Order cũ. Chỉ khi có link này service mới cập nhật projection `vehicle_tracking`/`pod`; nếu không có, event store vẫn hoạt động độc lập.

Sự kiện và chứng từ là bất biến ở API: không cung cấp PUT/PATCH/DELETE. Bảng GPS/POD cũ tiếp tục tồn tại để giao diện cũ hoạt động; service mới có thể cập nhật projection tương thích sau khi event được ghi thành công.

## Luồng trạng thái

Chuỗi chính:

`dispatched → check_in → pickup → departure → arrival → unloading → delivered`

Mỗi bước chỉ được ghi khi bước trước đã tồn tại. Event chính không được lặp. `incident`, `delay`, `route_deviation` là sự kiện ngoại lệ, được phép xuất hiện khi Freight Order đang thực thi và không làm thay đổi vị trí trong chuỗi chính.

`delivered` bắt buộc có chứng từ POD hợp lệ. Khi thêm sự kiện chính, service cập nhật trạng thái và version của Freight Order trong cùng transaction. Client phải gửi `expected_version`; xung đột trả `409 VERSION_CONFLICT`.

## API

- `GET /api/tms/freight-orders/{id}/events`: lịch sử tăng dần theo `event_time`, rồi `recorded_at`.
- `POST /api/tms/freight-orders/{id}/events`: ghi sự kiện mới và trả envelope `{message, data}`.
- `GET /api/tms/freight-orders/{id}/latest-position`: projection vị trí mới nhất.

POST yêu cầu `Idempotency-Key`; cùng key và cùng payload trả lại kết quả cũ, cùng key khác payload trả `409 IDEMPOTENCY_KEY_REUSED`. Actor lấy từ principal tin cậy, không lấy từ header người dùng tùy ý.

## Validation và an toàn

- Tọa độ phải hữu hạn, latitude trong `[-90, 90]`, longitude trong `[-180, 180]`; tốc độ và quãng đường không âm.
- `device` source phải có `device_id`; event thủ công phải có actor và lý do đối với sự kiện ngoại lệ.
- `event_time` không được vượt quá thời gian máy chủ theo ngưỡng cấu hình và không được lùi trước event chính gần nhất.
- Freight Order, vehicle và driver phải khớp assignment đang active.
- Mọi command ghi AuditLog; lỗi trả mã ổn định và thông báo tiếng Việt, không lộ exception/CSDL.
- PostgreSQL sử dụng row lock và unique constraints để chống ghi đồng thời; SQLite chỉ dùng trong test cô lập.

## Tương thích

Sau khi event hợp lệ được flush, service cập nhật `vehicle_tracking` theo latest-position và tạo/cập nhật POD projection cho màn hình cũ. Event store mới là nguồn sự thật; projection có thể tái tạo từ event/document, không được dùng projection để sửa ngược lịch sử.

## Kiểm thử

- Domain: đúng thứ tự, chặn bỏ bước/lặp/lùi thời gian, ngoại lệ không đổi trạng thái, delivered cần POD.
- Idempotency và concurrency: cùng key chỉ một event/audit; version cũ bị từ chối.
- GPS: kiểm tra biên tọa độ, nguồn thiết bị và latest-position.
- Migration: SQLite cô lập, PostgreSQL dry-run, rollback có kiểm soát, head `006` và readiness tables.
- API: envelope, lịch sử bất biến, actor/audit, thông báo tiếng Việt.
- Chạy toàn bộ backend regression; không kết nối PostgreSQL Linux khi kiểm thử.

## Ngoài phạm vi

Streaming WebSocket/MQTT thực, tích hợp nhà cung cấp GPS, object storage thật, geofencing nâng cao, tính cước và settlement thuộc increment kế tiếp.
