# Route Map Display Implementation Plan

**Goal:** Hiển thị tuyến Master Data đã lưu trên bản đồ bằng dữ liệu chặng thật từ PostgreSQL.

**Architecture:** Tạo utility JavaScript thuần để parse `segments_json`, tạo chuỗi địa điểm A → B → C, geocode thành waypoint, và gọi hàm vẽ bản đồ qua callback. `loadSavedRoutePreset` chỉ nối dữ liệu API vào utility này. Backend và schema PostgreSQL giữ nguyên.

**Tech Stack:** JavaScript, Leaflet, OpenStreetMap Nominatim, OSRM, FastAPI, PostgreSQL.

## Chunk 1: Sửa luồng tải và vẽ tuyến

### Task 1: Tạo chuỗi địa điểm từ chặng đã lưu

**Files:**
- Create: `frontend/js/route-map-utils.js`
- Create: `frontend/tests/route-map-utils.test.js`
- Modify: `frontend/index.html`

- [ ] Viết test dùng `node:assert` cho fixture A→B, B→C, kỳ vọng `[A,B,C]`.
- [ ] Viết test cho chặng không liền nhau A→B, C→D, kỳ vọng `[A,B,C,D]`.
- [ ] Viết test cho dữ liệu rỗng/sai.
- [ ] Chạy `node frontend/tests/route-map-utils.test.js`, kỳ vọng FAIL vì utility chưa tồn tại.
- [ ] Viết utility UMD `buildOrderedRouteLocations(segments)`, `resolveRouteWaypoints(route, geocodeFn)`, và `drawSavedRoute(route, geocodeFn, drawFn)` để browser và Node cùng sử dụng.
- [ ] Chèn `route-map-utils.js` trước `app.js` trong `frontend/index.html`.
- [ ] Chạy lại test, kỳ vọng PASS.

### Task 2: Nối tuyến đã chọn với bản đồ

**Files:**
- Modify: `frontend/js/app.js`
- Test: `frontend/tests/route-map-utils.test.js`

- [ ] Test `drawSavedRoute` với `geocodeFn` và `drawFn` giả, truyền route có `segments_json` A→B→C và xác nhận map được gọi một lần với ba waypoint đúng thứ tự.
- [ ] Test trường hợp geocode thiếu một điểm thì không gọi map.
- [ ] Thêm hàm `geocodeRouteLocation(location)` trong `app.js`.
- [ ] Trong `loadSavedRoutePreset`, parse segments một lần và gọi `window.RouteMapUtils.drawSavedRoute`.
- [ ] Khi thành công gọi `initLeafletRouteMap(waypoints, id, name)`; khi thất bại xóa lớp tuyến cũ và báo không xác định được tọa độ.
- [ ] Chạy `node frontend/tests/route-map-utils.test.js`.
- [ ] Chạy `node --check frontend/js/route-map-utils.js`.
- [ ] Chạy `node --check frontend/js/app.js`.
