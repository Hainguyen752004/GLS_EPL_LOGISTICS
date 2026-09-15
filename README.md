# Packing List Demo

Bản demo tách riêng, dựng lại module Packing List của EPL_System và nối thêm
phần còn thiếu: **đơn hàng của khách ở đầu luồng** và **giao hàng ở cuối luồng**.

```
Danh mục khách hàng
        ↓ (chọn, không gõ tay)
Đơn hàng khách (SO)  →  nhiều Packing List  →  chuyến giao hàng  →  theo dõi xe trên bản đồ  →  ký nhận
```

## Chạy

```bash
cd D:\Demo_Lao\parking_list_demo
python chay.py
```

Mở http://127.0.0.1:8042

Muốn có sẵn dữ liệu để bấm thử:

```bash
python backend\app\gieo_demo.py
```

## Cơ sở dữ liệu

Bản demo dùng **database riêng** tên `parking_list_demo` trên cùng máy chủ
PostgreSQL, **không đụng vào `epl_logistics`** của EPL_System. Đường dẫn nằm
trong `parking_list_demo/.env`, và `config.py` chặn thẳng nếu ai đó trỏ nhầm vào
database của EPL_System.

## Bốn thứ tiếng

Nút ngôn ngữ ở góc trên bên phải có bốn chế độ: **VI · EN · ລາວ · VI+ລາວ**.
Chế độ cuối hiện tiếng Việt ở dòng trên và tiếng Lào ở dòng dưới, dùng khi ngồi
bàn giao cho bên Lào.

Mọi chữ đều lấy theo KHOÁ từ `frontend/lang.json`, không đoán theo nội dung —
nên không bao giờ có câu nửa Việt nửa Lào.

## Danh mục khách hàng

Nút **KH** trên thanh đầu trang. Ba loại trong cùng một danh mục: khách nhận
hàng, nhà cung cấp, kho xuất hàng. Phiếu đơn hàng **chọn** khách và nhà cung cấp
từ đây — máy chủ từ chối đơn không có `customer_id` (`SO_NO_CUSTOMER`). Toạ độ
khai ở đây là thứ màn Theo dõi dùng để vẽ đường xe.

## Theo dõi xe

Nút **④ Theo dõi xe**. Bản đồ Leaflet, nền OSM hoặc ảnh vệ tinh Esri — cùng
thư viện và nền với EPL_System. Mỗi chuyến đang chạy hiện: vị trí hiện tại, vệt
đường đã đi, kho → điểm giao, còn cách bao xa, tốc độ, lần cập nhật cuối. GPS
cũ quá 15 phút thì cảnh báo.

Vị trí lấy từ `POST /api/tracking/{chuyến}/position` — điểm cuối cho thiết bị
GPS hay app tài xế gửi lên. Bản demo chưa có thiết bị nên có nút **Chạy tiếp
(mô phỏng)** nhích xe dọc tuyến; tới đích thì chuyến tự sang *Đã tới nơi*.

## Điều bản demo phải làm cho đúng

**1. Không đóng vượt số đã đặt.** Mỗi lần đóng gói đều so với phần còn lại của
từng dòng hàng trên đơn. Vượt là máy chủ từ chối và nói rõ dòng nào vượt bao
nhiêu.

**2. Kiện nào cũng truy ngược được.** Mỗi dòng trong Packing List bắt buộc gắn
với một dòng hàng của đơn (`so_line_id` không cho rỗng). Quét tem QR trên một
kiện là ra ngay: kiện số mấy trên tổng mấy, thuộc Packing List nào, đơn nào, PO
nào, và trong đó có những dòng hàng nào. Tem in ra cũng ghi thẳng mã đơn và PO
lên giấy, để người giao hàng không cần mở máy.

**3. Huỷ thì trả hàng về cho đơn.** Huỷ một Packing List thì số hàng trong đó
được cộng lại vào phần chưa đóng của đơn, không mất đi.

## Cấu trúc

```
backend/app/
  models.py                  bảng dữ liệu
  services/don_hang_service.py    đơn hàng, tính phần còn lại
  services/packing_service.py     đóng gói, tem QR, đổi trạng thái
  services/giao_hang_service.py   chuyến giao hàng, ký nhận
  services/khach_hang_service.py  danh mục khách hàng / nhà cung cấp / kho
  services/theo_doi_service.py    vị trí xe, vệt đường, mô phỏng chạy
  routes/api_routes.py            điểm cuối HTTP
  seed.py / gieo_demo.py          dữ liệu mẫu
backend/tests/
  test_luong_a_z.py          chạy trọn luồng trên DB thật, có đi cả lối sai
  test_api_http.py           gọi thật các điểm cuối HTTP
frontend/
  index.html  css/khung.css  js/khung.js   khung chung, bốn ngôn ngữ
  lang.json                                toàn bộ chữ
  modules/don-hang/         .html .css .js
  modules/packing-list/     .html .css .js
  modules/giao-hang/        .html .css .js
  modules/quet-tem/         .html .css .js
  modules/khach-hang/       .html .css .js
  modules/theo-doi/         .html .css .js   (Leaflet)
  tests/kiem-giao-dien.js   cú pháp JS, khoá dịch, bốn chế độ
  tests/kiem-ve-man.js      dựng thật sáu màn trong jsdom
```

Mỗi module một bộ **html + css + js riêng** — sai màn nào sửa đúng màn đó.

## Bộ kiểm

```bash
python backend\tests\test_luong_a_z.py     # nghiệp vụ, chạy trên DB thật
python backend\tests\test_api_http.py      # API và tệp tĩnh
node frontend\tests\kiem-giao-dien.js      # giao diện và bản dịch
```

Hoặc chạy cả bốn:

```bash
chay_kiem.bat
```

## Trạng thái

**Đơn hàng:** mới → đang đóng gói → đã đóng đủ → đang giao → đã giao.
Trạng thái đơn được **tính ra** từ dữ liệu thật, không ai đặt tay, nên đơn không
bao giờ nói một đằng còn Packing List nói một nẻo.

**Packing List:** sẵn sàng in tem → đã vào bãi chờ → đã qua cổng → đã bốc lên xe
→ đã xuất bãi → đã giao. Đi lần lượt, không nhảy cóc, không lùi.

**Chuyến giao hàng:** đã lên kế hoạch → đang bốc hàng → đang trên đường → đã tới
nơi → đã giao xong. Cho chuyến xuất phát thì mọi Packing List trên xe tự chuyển
sang "đã xuất bãi"; đóng chuyến thì phải có đủ POD của từng phiếu.

## Lấy gì từ EPL_System

Giữ lại: mô hình Packing List (phiếu, dòng hàng, tem QR, sự kiện), chuỗi trạng
thái từ bãi ra đường, và cách ghi POD.

Bỏ đi: điều phối, công thức giá thành, sắp ca, lịch xe, quyết toán, báo giá.
Bản demo này chỉ trả lời một câu hỏi — *hàng trong kiện này thuộc đơn nào* — nên
mọi thứ không phục vụ câu đó đều là thứ làm người dùng rối.
