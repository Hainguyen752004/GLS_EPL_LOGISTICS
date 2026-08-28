# Thiết kế hiển thị tuyến đã lưu trên bản đồ

## Mục tiêu

Khi người dùng chọn một tuyến đã lưu trong Master Data, bản đồ phải hiển thị đúng các chặng của tuyến lấy từ PostgreSQL, không dùng dữ liệu mẫu.

## Phạm vi

Chỉ sửa lỗi chọn một tuyến đã lưu nhưng bản đồ nhận `null`. Không thay đổi API, schema, luồng lưu tuyến, khoảng cách hay các phần Master Data khác.

## Luồng dữ liệu

1. `GET /api/routes` trả về tuyến và `segments_json`.
2. `loadSavedRoutePreset` phân tích các chặng theo thứ tự.
3. Utility thuần chuyển các chặng thành danh sách địa điểm có thứ tự: với mỗi chặng, thêm `from` nếu khác điểm cuối hiện tại, rồi thêm `to` nếu khác điểm cuối hiện tại.
4. Ví dụ A→B, B→C thành A, B, C; A→B, C→D thành A, B, C, D.
5. Mỗi địa điểm được chuyển thành tọa độ bằng Nominatim. Chỉ khi tất cả địa điểm có tọa độ hợp lệ mới gọi hàm vẽ với waypoint không rỗng.
6. `initLeafletRouteMap` nhận danh sách waypoint và yêu cầu OSRM trả về hình học đường bộ; cơ chế đường thẳng dự phòng hiện có được giữ nguyên.

## Hành vi giao diện

- Chọn tuyến hợp lệ sẽ cập nhật bảng chặng và vẽ đường tuyến.
- Nếu `segments_json` rỗng/sai cấu trúc hoặc một địa điểm không geocode được, không vẽ tuyến sai và hiển thị thông báo không xác định được tọa độ.

## Kiểm thử

- Kiểm thử Node cho utility `buildOrderedRouteLocations`, `resolveRouteWaypoints`, và `drawSavedRoute`.
- Test mock `geocodeFn` và `drawFn` để xác nhận luồng chọn tuyến truyền waypoint không rỗng vào hàm bản đồ; nếu thiếu tọa độ thì không gọi map.
- Chạy `node --check` riêng cho từng tệp JavaScript được sửa.
