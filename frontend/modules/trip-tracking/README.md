# Theo dõi chuyến – EPL (HTML / CSS / JS thuần)

Trang theo dõi chuyến vận chuyển được thiết kế lại theo bố cục 3 cột: **danh sách chuyến** (trái) · **bản đồ tuyến + mốc chặng + tab Diễn biến / Chi phí sửa chữa / Chứng từ** (giữa) · **hồ sơ chuyến** (phải). Khối Diễn biến và Chi phí cuộn **bên trong** thẻ nên không tràn xuống dưới trang.

Mở `trips.html` bằng trình duyệt là chạy được, không cần build.

## File

| File | Vai trò |
|---|---|
| `trips.html` | Khung trang, thanh công cụ, ô thống kê, 3 cột, chỗ gắn `TRIPS_CONFIG` |
| `trips.css` | Token màu (giữ bảng màu EPL: navy `#1b2530`, tan `#f0e4cc`, xanh `#2f7d5b`, đỏ `#c0392b`, vàng `#b7791f`, xanh dương `#2c5f8a`), toàn bộ component, responsive < 1200 / < 960 px |
| `trips.js` | Dữ liệu mẫu, tính toán chỉ số, render, modal, lưu `localStorage` |

## Tính năng

- **Ô thống kê** tính từ dữ liệu: đang chạy, chưa xuất bến, đi lâu chưa về (≥ 25 ngày), đã tới chờ hóa đơn, sự cố chưa duyệt, phiếu lĩnh chờ cấp, chưa thu tiền. Bấm ô để lọc danh sách, bấm lại để bỏ lọc.
- **Danh sách chuyến**: tìm theo số phiếu / xe / biển số / tài xế / khách hàng; sắp xếp Ưu tiên (sự cố → đi lâu → đang chạy), Ngày đi, Khách hàng; hộp "Chỉ phiếu chưa xong" ẩn chuyến đã thu tiền.
- **Bản đồ**: chế độ *Đội xe* (mọi xe, màu theo trạng thái, bấm điểm để chọn chuyến) và *Tuyến đang chọn* (các điểm dừng, đoạn đã đi tô đậm, vị trí xe ước tính, nhãn km).
- **Mốc chặng** (stepper): điểm đã tới ✓, điểm tiếp theo viền xanh; bấm để làm nổi trên bản đồ.
- **Tab Diễn biến / Chi phí sửa chữa / Chứng từ** với số lượng, bảng cuộn trong khung, dòng tổng dưới cùng (tổng chi phí LAK, ghi vào mục V). Nút *Ghi chú diễn biến*, *Khai sửa xe*, *Thêm chứng từ*; nút *Duyệt* trên từng khoản chi.
- **Hồ sơ chuyến**: thông tin xe / tài xế / khách / cân, trình tự duyệt I–VI (bấm để đổi trạng thái), cước dự kiến & chưa thu, nút *Xác nhận tới điểm N* (tự chuyển trạng thái: xuất xe → đang vận chuyển → đã giao hàng), *Cấp phiếu lĩnh*, *Ghi nhận thu tiền*, *Báo sự cố / sửa xe*.
- **Sổ sự cố & sửa chữa**: mọi sự cố và khoản chi của tất cả chuyến, duyệt tại chỗ; có nút *Đặt lại dữ liệu mẫu*.
- **Tự cập nhật 30 giây** và nút *Cập nhật*, có tem giờ.
- Thay đổi lưu trong `localStorage` (khóa `epl_trips_v1`) để làm demo.

## Nối vào hệ thống thật

Sửa `window.TRIPS_CONFIG` trong `trips.html` (trước khi nạp `trips.js`):

```js
window.TRIPS_CONFIG = {
  trips: dataFromApi,                       // mảng chuyến theo cấu trúc bên dưới
  today: null,                              // null = dùng ngày hệ thống (mẫu đặt "2026-09-17")
  lateDays: 25,                             // ngưỡng "đi lâu chưa về"
  onEvent: (tripId, event) => fetch(`/api/trips/${tripId}/events`, { method: "POST", body: JSON.stringify(event) }),
  onCost:  (tripId, cost)  => fetch(`/api/trips/${tripId}/costs`,  { method: "POST", body: JSON.stringify(cost) }),
  openTicketUrl: (trip) => `/tickets/${encodeURIComponent(trip.code)}`,
  storageKey: "epl_trips_v1",
};
```

Cấu trúc một chuyến:

```js
{
  id: "t432", code: "T4-0432-08/EPL", vehicle: "342", plate: "ບອ 3311", driver: "ທ້າວ ບຸນມີ", customer: "ຖໍ່ເຫຼືອ",
  cargo: "Quặng sắt", weightIn: 41.9, weightOut: null,
  depart: "2026-08-23", arrived: null,          // ISO yyyy-mm-dd
  status: "planned" | "running" | "arrived" | "closed",
  fuelTicket: "pending" | "issued",
  fare: 18500000, paid: 0, currency: "LAK",
  stops: [{ name, sub, km, done, at, x, y }],   // x, y: tọa độ trên bản đồ 700×250 (thay bằng lat/lng khi dùng bản đồ thật)
  approvals: ["done","done","pending","pending","check","pending"],   // I Xuất xe · II Cân đầu · III Tới điểm · IV Cân cuối · V Chi phí · VI Thu tiền
  events: [{ date, time, type: "depart"|"stop"|"arrive"|"fuel"|"warn"|"incident"|"note"|"cost"|"money", text, by, approved }],
  costs:  [{ id, item, qty, price, amount, voucher, status: "entered"|"check"|"approved", date }],
  docs:   [{ name, date, status: "ok"|"missing" }],
}
```

`window.Trips` (store, ui, render, addEvent, addCost, confirmStop) được lộ ra để module khác gọi. Bản đồ hiện là SVG minh họa; khi có GPS, thay `renderMap()` bằng Leaflet/Google Maps và giữ nguyên các phần còn lại.
