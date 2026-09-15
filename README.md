# Packing List Demo

Bản demo tách riêng, dựng lại module Packing List của EPL_System và nối thêm
phần còn thiếu: **đơn hàng của khách ở đầu luồng** và **giao hàng ở cuối luồng**.

```
Email khách gửi / phiếu tải lên  →  máy đọc  →  hộp chờ duyệt  →  người duyệt
                                                                      ↓
Danh mục khách hàng + Tuyến đường                                     ↓
        ↓ (chọn, không gõ tay)                                        ↓
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

Lệnh này còn để sẵn **một phiếu trong hộp chờ duyệt** của màn Nhận đơn, đã được
máy đọc thật, để bấm thử nút Duyệt ngay mà không cần cấp quyền hộp thư.

Lệnh này **luôn giữ đủ ba trạng thái** để demo: một đơn **chưa đóng gì**, một
đơn **đóng dở** (để thấy cột *Còn lại* hoạt động), và một chuyến **đang giao**
còn phiếu chưa ký nhận. Bấm hết kịch bản rồi chạy lại là có ngay bộ mới — mỗi
bước chỉ sinh thêm khi trạng thái đó không còn cái nào, nên chạy bao nhiêu lần
cũng không đẻ ra một đống đơn rác.

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

## Nhận đơn tự động

Nút **0 · Nhận đơn**. Phiếu đặt hàng của khách vào hệ thống theo hai đường:

- **Quét hộp thư** — đọc thư chưa đọc trong hộp thư đặt hàng, lấy tệp đính kèm.
- **Tải phiếu lên** — dùng khi khách gửi qua Zalo, WhatsApp, hay cầm giấy tới quầy.

Máy đọc phiếu bằng Gemini, ra một **bản nháp** nằm trong hộp chờ duyệt. Màn hình
đặt **tệp gốc ngay cạnh bản nháp** để người duyệt soi từng dòng; sửa được mọi ô,
thêm bớt được dòng hàng, rồi bấm **Duyệt** để tạo đơn hàng thật.

**Vì sao phải có người duyệt.** AI đọc phiếu nhanh nhưng không phải lúc nào cũng
đúng, mà một đơn sai đi thẳng vào luồng đóng gói nghĩa là hàng ra khỏi kho sai.
Nên **không có đường nào từ email đi thẳng vào đơn hàng**. Bản nháp nằm ở bảng
riêng `inbound_orders`; lúc duyệt mới gọi đúng `don_hang_service.tao` như khi gõ
tay, nên mọi ràng buộc của đơn hàng áp y hệt: phải có PO, PO không trùng, phải
chọn khách từ danh mục, dòng hàng phải có số lượng.

Máy đọc còn nói ra **độ chắc chắn** và **những chỗ nó không chắc** — đó là danh
sách người duyệt nhìn vào để biết soi kỹ dòng nào.

Duyệt hai lần bị chặn (`IB_ALREADY_APPROVED`), tệp không phải phiếu đặt hàng bị
chặn (`IB_FILE_TYPE`), và phiếu đã duyệt thì không đọc lại được nữa.

Điều dễ đọc sai nhất là cột `UNIT QUANTITY (UNIT/PACK/CASE)`: ô ghi `24CT` nghĩa
là **24 thùng**, không phải 24 cái. Bộ kiểm `test_nhan_don.py` gọi Gemini thật và
đối chiếu đúng con số đó cho từng dòng, vì đọc sai chỗ này là kho lấy thiếu hàng
mà không ai biết.

### Cấu hình

Hai thứ nằm trong `.env` (tệp này **không** lên GitHub):

| Khoá | Dùng để |
|---|---|
| `GEMINI_API_KEY_GT` | máy đọc phiếu |
| `GMAIL_CREDENTIALS_PATH` · `GMAIL_TOKEN_PATH` | đọc hộp thư |

Màn Nhận đơn hiện sẵn trạng thái của cả hai. Hộp thư báo *chưa nối* thì chạy:

```bash
python cap_quyen_hop_thu.py
```

Lệnh này mở trình duyệt để đăng nhập Google rồi ghi quyền vào `secrets/token.json`.
Bản demo chỉ xin quyền **đọc** thư và đánh dấu đã đọc, không xin quyền gửi thư.
Nếu Google trả lỗi `invalid_client` thì khoá OAuth cũ đã bị thu hồi: tạo OAuth
client ID mới kiểu *Desktop app* trong Google Cloud Console, tải về và thay
`secrets/OAuth2.json`.

Chưa cấu hình gì thì màn vẫn mở được, chỉ là nút Quét hộp thư mờ đi và nó nói rõ
lý do kèm đúng lệnh cần chạy. Phần tải phiếu lên không cần hộp thư.

## Danh mục khách hàng

Nút **KH** trên thanh đầu trang. Ba loại trong cùng một danh mục: khách nhận
hàng, nhà cung cấp, kho xuất hàng. Phiếu đơn hàng **chọn** khách và nhà cung cấp
từ đây — máy chủ từ chối đơn không có `customer_id` (`SO_NO_CUSTOMER`). Toạ độ
khai ở đây là thứ màn Theo dõi dùng để vẽ đường xe.

## Tuyến đường

Nút **TĐ** trên thanh đầu trang — dựng theo module Tuyến đường của EPL_System.

Một tuyến là một **chuỗi chặng A → B → C**, không phải một đoạn thẳng nối hai
đầu. Màn có: ô chọn tuyến đã lưu, mã và tên tuyến, **bảng các chặng** với tổng
quãng đường tự cộng, khung **thêm chặng mới**, và **sơ đồ lộ trình** vẽ đường
xanh đi qua đúng thứ tự các chặng.

**Tổng km LÀ tổng các chặng** — không ai gõ tay một con số rồi quên sửa. Thêm
hay bớt một chặng là tổng đổi theo ngay.

Điểm đi / điểm đến của mỗi chặng gõ tự do, nhưng có gợi ý từ danh mục khách
hàng; gõ trúng tên trong danh mục thì chặng lấy luôn toạ độ và hiện trên bản
đồ, gõ tên lạ thì vẫn lưu được, chỉ là chặng đó không vẽ ra.

Ô "Tuyến giao" trên phiếu đóng gói **chọn** từ đây thay vì gõ tay, nên phiếu in
ra không còn để trống. Màn Theo dõi vẽ đường theo đúng lộ trình nhiều chặng.
Xoá tuyến đang có Packing List dùng thì bị chặn (`RT_IN_USE`).

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

**3. Hai bản in theo đúng mẫu.** Tem kiện (mẫu 1) có RDC LAOS, bốn ô STORE ·
ROUTE · WAVE · GATE, dòng TO, QR riêng của từng kiện và số kiện n/N — mỗi kiện
một trang. Phiếu Packing List (mẫu 2) có RDC / mã phiếu / mã đơn ở góc trái,
**QR của cả phiếu** ở góc phải, bảng Date · Store · Store ID · Box và bảng hàng
kết thúc bằng dòng TOTAL. Quét QR của phiếu ra **phiếu + đơn + toàn bộ dòng
hàng**; quét tem kiện ra thêm kiện số mấy trên tổng mấy.

Nhãn khung của hai biểu mẫu giữ nguyên **tiếng Anh** ở mọi chế độ ngôn ngữ —
đây là biểu mẫu chuẩn của kho, y như chữ PURCHASE ORDER trên phiếu CP ALL, và
tem đi qua Việt · Lào · Thái nên nhãn tiếng Anh là thứ cả ba bên đọc được.

**4. Huỷ thì trả hàng về cho đơn.** Huỷ một Packing List thì số hàng trong đó
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
  services/tuyen_service.py       danh mục tuyến đường
  services/doc_don_ai.py          máy đọc phiếu (gọi thẳng REST của Gemini)
  services/gmail_service.py       đọc hộp thư đặt hàng
  services/nhan_don_service.py    hộp chờ duyệt, duyệt ra đơn hàng thật
  routes/api_routes.py            điểm cuối HTTP
  seed.py / gieo_demo.py          dữ liệu mẫu
backend/tests/
  test_luong_a_z.py          chạy trọn luồng trên DB thật, có đi cả lối sai
  test_api_http.py           gọi thật các điểm cuối HTTP
  test_nhan_don.py           nhận đơn tự động, gọi THẬT Gemini để soát số lượng
frontend/
  index.html  css/khung.css  js/khung.js   khung chung, bốn ngôn ngữ
  lang.json                                toàn bộ chữ
  modules/don-hang/         .html .css .js
  modules/packing-list/     .html .css .js
  modules/giao-hang/        .html .css .js
  modules/quet-tem/         .html .css .js
  modules/khach-hang/       .html .css .js
  modules/theo-doi/         .html .css .js   (Leaflet)
  modules/tuyen-duong/      .html .css .js
  modules/nhan-don/         .html .css .js
  tests/kiem-giao-dien.js   cú pháp JS, khoá dịch, bốn chế độ
  tests/kiem-ve-man.js      dựng thật tám màn trong jsdom
  tests/kiem-ban-in.js      hai bản in có đúng hai mẫu không
```

Mỗi module một bộ **html + css + js riêng** — sai màn nào sửa đúng màn đó.

## Bộ kiểm

```bash
python backend\tests\test_luong_a_z.py     # nghiệp vụ, chạy trên DB thật
python backend\tests\test_api_http.py      # API và tệp tĩnh
python backend\tests\test_nhan_don.py      # nhận đơn tự động, gọi thật Gemini
node frontend\tests\kiem-giao-dien.js      # giao diện và bản dịch
```

Hoặc chạy cả sáu:

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
