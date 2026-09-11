# Trang tài xế EPL (bản demo)

Một trang web **đứng riêng**, ngoài dự án `EPL_System`, dành cho tài xế mở trên
điện thoại. Nó không có cơ sở dữ liệu riêng: mọi con số đọc thẳng từ API EPL đã
host tại `http://senvangsolutions.com:1506`.

## Chạy

```
python chay.py
```

Rồi mở `http://localhost:8080`. Điện thoại trong cùng mạng LAN thì mở
`http://<ip-máy-này>:8080` (ví dụ `http://192.168.1.20:8080`).

Vài tuỳ chọn:

```
python chay.py --cong 9000                     # đổi cổng
python chay.py --api http://127.0.0.1:8001     # trỏ về máy chủ chạy trên máy mình
python chay.py --token <token>                 # khi nào máy chủ bật token
```

Trên trang còn một nút **"Đổi địa chỉ máy chủ API"** hiện ra khi gọi API thất
bại, để đổi nhanh mà không phải khởi động lại.

## Vì sao phải có `chay.py`, không mở thẳng `web/index.html`

Máy chủ EPL chỉ cho phép CORS từ chính nó (`EPL_CORS_ORIGINS`, mặc định
`localhost:8001`). Một trang đặt ở địa chỉ khác gọi thẳng sẽ bị trình duyệt chặn
ngay bước tiền kiểm — đo được: `OPTIONS /api/drivers` với `Origin` lạ trả về
`400 Bad Request`. `chay.py` vừa phục vụ `web/`, vừa chuyển tiếp `/api/...` sang
máy chủ EPL, nên trình duyệt chỉ thấy **một** địa chỉ duy nhất và không có CORS
nào để vướng. Cách này **không cần sửa cấu hình máy chủ EPL đang chạy thật**.

Token (khi nào bật) được gắn ở phía `chay.py`, nên nó không nằm trong điện thoại
tài xế.

## Hai màn hình

**Màn 1 — Chuyến của tôi.** Logo EPL, tên tài xế đang chọn, rồi danh sách thẻ: mỗi
thẻ là một lệnh giao hàng với tuyến đi → đến, trạng thái, số chặng đã xong, biển số
xe, hạn giao và số sự cố chưa đóng.

**Màn 2 — Chi tiết chuyến**, mở khi chạm vào một thẻ. Đây là một màn RIÊNG che kín,
có nút Quay lại ở góc, chứ không phải nội dung đổ xuống dưới danh sách: trên điện
thoại, đổ xuống dưới bắt người ta cuộn qua danh sách mỗi lần muốn xem, và nút việc
thì nằm tít cuối trang.

Màn này gồm, từ trên xuống:

* **Bản đồ thật** (Leaflet + OpenStreetMap): vẽ tuyến đường bộ thật của chuyến —
  phần **đã đi tô đỏ đậm**, phần **còn lại nét đứt xám**, ghim điểm đi (xanh), từng
  điểm dừng đánh số, điểm đến (đỏ), và **ghim xe 🚚 tại vị trí hiện tại**.
* Dải số: đã đi bao nhiêu %, còn bao nhiêu km, tốc độ, giờ đến dự kiến.
* **Thanh mốc** sáu bước (vào bãi → lấy hàng → xuất bến → đến điểm giao → dỡ hàng →
  giao xong): bước đã ghi có dấu ✓ xanh, bước đang tới khoanh đỏ. Thanh tự cuộn tới
  bước đang tới.
* Thẻ thông tin lệnh, cảnh báo (quá hạn / có sự cố / vị trí đang là mô phỏng), và
  danh sách chặng của chuyến.
* **Thanh việc dán ở đáy màn** — luôn trong tầm ngón tay, không phải cuộn xuống tìm:
   - **📍 Ghi mốc** — mốc kế tiếp theo đúng thứ tự (xuất bến → đến điểm lấy → lấy
     hàng → đang chạy → đến điểm giao → dỡ hàng). Ghi mốc là ghi **thật** vào
     `POST /api/tms/freight-orders/{id}/events`, vị trí trên bản đồ điều độ nhích
     theo.
   - **✍ Mở hoàn tất giao hàng** — chỉ bật khi đã ghi mốc *đến điểm giao*. Mở ra
     phiếu ký nhận cho **từng điểm giao** của lệnh: giờ giao, người nhận, số điện
     thoại, kết quả, ảnh biên bản, **chữ ký vẽ tay**, ghi chú; kèm bảng giá thật
     lấy từ hồ sơ quyết toán để nhập khoản khách trả thêm.
   - **⚠ Báo sự cố** — loại sự cố, mức độ, mô tả, vị trí; đẩy vào
     `POST /api/incidents`.

Chuyến nhiều điểm giao thì phải ký đủ **mọi** điểm mới đóng được lệnh — đúng như
luồng trên hệ chính, và chỉ khi đó hồ sơ mới sang bên công nợ.

## Bản đồ

Thư viện Leaflet 1.9.4 lấy từ `unpkg.com`; ảnh nền thử lần lượt ba nguồn và **nhớ
nguồn nào chạy được**: `tile.openstreetmap.de` → `tile.openstreetmap.org` → Esri.
Nhiều nguồn là có lý do đo được: trên mạng của dự án, `tile.openstreetmap.org`
**không tới được**, và một bản đồ chỉ có một nguồn ảnh nền thì ra ô xám trơn — có
tuyến, có toạ độ, nhưng người xem đọc ra là "bản đồ hỏng".

Mất mạng ra ngoài (không tải được Leaflet) thì trang **nói thẳng** là không tải được
thư viện bản đồ và mọi thứ còn lại vẫn dùng bình thường — ghi mốc, ký nhận, báo sự
cố đều không cần bản đồ.

## API mà trang này dùng (chỉ bốn nhóm)

| Việc | Điểm cuối |
|---|---|
| Danh sách chuyến | `GET /api/tracking/control-tower` (lọc theo `driver_id`/`co_driver_id`) |
| Ghi mốc | `POST /api/tms/freight-orders/{fo}/events` |
| Báo sự cố | `POST /api/incidents` |
| Hoàn tất giao hàng | `GET /api/delivery-orders/{do}/closeout` + `POST /api/delivery-orders/{do}/complete-delivery` |

## Khổ điện thoại

Trang dựng theo lối *mobile-first*: khung rộng tối đa `34rem`, nút cao 52px cho
ngón tay, mọi ô nhập cỡ chữ `1rem` (iOS không tự phóng to khi bấm vào ô), lưới
tự xếp lại một cột khi màn hẹp, các hộp thoại trồi lên từ đáy màn hình, và có
chừa lề `env(safe-area-inset-*)` cho máy có tai thỏ.

## Giới hạn của bản demo — nói rõ để không ai hiểu nhầm

**Việc "tài xế nào chỉ thấy chuyến của mình" ở đây là lọc ở phần TRÌNH BÀY, không
phải bảo mật.** Không có đăng nhập: ai mở trang cũng chọn được tên người khác, và
API trả về toàn bộ chuyến rồi trang tự lọc theo `driver_id`. Muốn thật thì phải
có đăng nhập tài xế và lọc ở máy chủ — phần xác thực thuộc hệ thống cha, không
thuộc module EPL này.

## Cấu trúc

```
EPL_TaiXe/
├─ chay.py            máy chủ tĩnh + chuyển tiếp /api
├─ README.md
└─ web/
   ├─ index.html          toàn bộ giao diện + CSS (màu lấy từ logo EPL)
   ├─ img/logo-epl.jpg    logo, dùng luôn làm favicon và icon khi lưu ra màn hình chính
   └─ js/tai-xe.js        toàn bộ logic; thư viện ngoài duy nhất là Leaflet (bản đồ)
```
