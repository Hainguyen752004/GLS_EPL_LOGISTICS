# Nối trang điều xe EPL Lào với hệ kế toán anh Tune — mình gọi gì, anh gọi gì, chứng từ đi đâu

Bản ngày **01/10/2026**, sửa chiều và tối cùng ngày. Soạn từ mã đang chạy của trang điều xe (`EPL_LAO_REAL`), các lần gọi thử thật trên máy `demo-lao-api.goldensme.com`, và **mã nguồn của anh** (`GLS-QLSX-APIs`, `GLS-QLSX-Web`, nhánh `feat/DemoLao`, đọc 01/10 — mục 8).

- Tài liệu này là **bản đồ**: mỗi đường nói để làm gì, gửi gì, nhận gì, đang ở trạng thái nào.
- Từng trường chi tiết nằm ở **hợp đồng API kế toán** `HOP_DONG_API_KE_TOAN_ANH_TUNE` (bản v2.1 cùng ngày). Mỗi chỗ dưới đây ghi số mục để tra.
- Quy ước:
  - **LAO** = trang điều xe (bên em);
  - **hệ anh** = hệ kế toán của anh Tune (QLSX, máy `demo-lao-api`);
  - **KT tạm** = trang kế toán tạm `EPL_KETOAN` (cổng 8030), đang giữ phần tiền cho tới khi hệ anh thay.
- Không có token, mật khẩu nào trong tài liệu này.

---

## 0. Tóm tắt một trang

### 0.1. LAO gọi sang hệ anh

| # | Đường của anh | Để làm gì | Trạng thái 01/10 |
|---|---|---|---|
| A1 | `GET /api/v1/common/country-accounts?tryAutoId=11&onlyActive=true` | danh mục tài khoản Lào (494 mã), cho ô chọn mã kế toán trên phiếu | **đang chạy** |
| A2 | `POST /api/v1/integrations/logistics/sales-orders` | phiếu **đề nghị thu** → SO + công nợ khách bên anh | **đã tạo SO thật 01/10** qua API chạy ở máy: `TK-20261001-000162`, `…163`; khách chưa có thì bên em tạo trước (A6) |
| A3 | 20 đường **chỉ đọc** (mục 1.3) | lấy mã số: đơn vị, kỳ, loại chứng từ, tiền tệ, khách… | đã đọc 30/09 và 01/10, **không nằm trong mã chạy** |
| A4 | `POST /api/v1/accounting/cmpayment-receipt/save-and-commit` (CMP) · `GET …/{id}` | phiếu **đề nghị tạm ứng** → phiếu chi "Chi trước" chờ ở hệ anh; thủ quỹ chi + ghi sổ bên anh; LAO đọc lại `STATUS` 12 → mục IV đã chi | **đã nối 01/10** (thử qua API chạy ở máy, mục 1.4) |
| A5 | `POST /api/v1/sales/debt/customer-detail` | màn Khách hàng → tab Công nợ, chỉ xem | **đã nối 01/10** (hợp đồng 12.11.2) |
| A6 | `POST /api/v1/master-data/customers · suppliers · staff /list · /upsert` | đối tượng bên anh: khách `EPLKH-`, chủ xe `EPLCX-`, tài xế `EPLTX-` — tìm, chưa có thì tạo | **đã nối 01/10** |
| A7 | `POST …/cmpayment-receipt/save-and-commit` (CMP "Chi khác") · `GET …/{id}` | **trả chủ xe liên kết**: phiếu chi đứng tên chủ xe, Nợ 4022; ghi sổ xong → "đã trả chủ xe" | **đã chạy thật 01/10** sau khi mở mã 4022 (hợp đồng 12.12.1) |

### 0.2. Hệ anh gọi sang LAO

| # | Đường của LAO | Để làm gì | Trạng thái 01/10 |
|---|---|---|---|
| B1 | `GET /api/handover/delivery-orders` | danh sách DO đã xong (đã về + đã khoá), đúng khuôn EPL_System | **đã dựng 30/09**, chờ địa chỉ ra Internet. **Mã phía anh đã sửa 01/10** (nhánh `feat/HonTunedaHai`): đọc địa chỉ + khoá từ cấu hình `LogisticsSource`, đã thử qua API chạy ở máy (mục 8.2) |
| B2 | `GET /api/handover/delivery-orders/{do_id}` | header + details một DO (dòng thu, các dòng chi mục III–VI kèm mã kế toán) | như trên |
| B3 | nhóm `/api/lien-thong/*` (hợp đồng mục 4) | anh báo lại **đã xuất hoá đơn**, **đã thu**, **đã trả chủ xe**, và đọc số của phiếu | **có sẵn**, KT tạm đang dùng; anh dùng khi thay KT tạm |

### 0.3. Chứng từ LAO sinh ra

| Tờ | Sinh lúc | Hôm nay đi đâu | Đã sang hệ anh chưa |
|---|---|---|---|
| `DO` phiếu xuất xe | Bãi lập phiếu | sổ chứng từ LAO → KT tạm | **chưa**; hệ anh đọc DO qua **B1/B2**, không cần đẩy |
| `PTU` đề nghị tạm ứng | lập / in tờ tạm ứng | sổ chứng từ → KT tạm | **chưa**; đề nghị đi A4 (CMP) |
| `PLNL` đề nghị xuất kho nhiên liệu | lập / in tờ xuất kho | sổ chứng từ → KT tạm; thủ kho cấp ở kho | **không sang anh Tune**: việc kho, sang hệ anh Toàn |
| `PC_TU` chi tạm ứng | **từ 01/10 thủ quỹ chi ở hệ anh** (phiếu chi "Chi trước"); Sếp chi tay trên LAO chỉ khi hệ anh không vào được | phiếu chi nằm ở hệ anh | **đã nối 01/10** (A4) |
| `PC_SC` chi sửa chữa · chi khác | quỹ chi mục V / VI trên LAO | sổ chứng từ → KT tạm | **chưa**; như `PC_TU` |
| `PDT` đề nghị thu | kế toán khoá phiếu | sổ chứng từ → KT tạm, **và** A2 → SO bên anh | **đã nối A2 ngày 01/10**; chờ anh tạo khách |

### 0.4. Hệ anh cho LAO những gì

- **Đã có:**
  - token dùng chung cho A1 và A2 (tài khoản cá nhân `tune`, **hết hạn 10/10/2026 09:05 giờ Lào**);
  - hướng dẫn `sales-orders` (11/09) và hướng dẫn thu chi `CM-CASH-VOUCHER-DEMOLAO-API-GUIDE.md`;
  - danh mục tài khoản 494 mã;
  - các mã số đọc được ở mục 1.3.
- **Còn chờ:** mục 5.

---

## 1. LAO gọi sang hệ anh

### 1.1. A1 — danh mục tài khoản

| | |
|---|---|
| Đường | `GET {EPL_ACC_CODE_API}?tryAutoId=11&onlyActive=true`. `EPL_ACC_CODE_API` là đường đầy đủ tới `…/api/v1/common/country-accounts` |
| Header | `Authorization: Bearer <EPL_ACC_CODE_TOKEN>` |
| Hết giờ · bộ nhớ | 20 giây · giữ 10 phút |
| LAO đọc | `Result[]`, các trường `AccCode`, `AccName`, `AccDescription`, `AccParentId`, `AccAccountWrite` (ghi sổ được), `AccIsActive` |
| LAO trả cho màn | `GET /api/acc-codes` → `{data: [...], source}` |
| Dùng ở | ô chọn **Mã kế toán** trên từng dòng chi của phiếu, màn **Phiếu đề nghị chi** |
| Không nối được | dùng bản chụp ngày 30/09 (`services/danh_muc_tai_khoan_lao.json`), cộng ba mã con 1371, 4021, 4022 mang nhãn "chưa mở" |

Chi tiết: hợp đồng mục 1 và 3.3.

### 1.2. A2 — đề nghị thu → SO + công nợ

**Người bấm và chỗ bấm:**

1. Kế toán Viêng Chăn (vai `acct`) hoặc Sếp đăng nhập.
2. Menu **Phiếu đề nghị thu** → chọn **Tháng** → bấm một DO đã khoá ở danh sách bên trái.
3. Trên thanh nút của tờ, bấm **Tạo SO bên kế toán**.
4. Máy **xem trước** ở máy chủ, không gọi mạng. Thiếu gì thì hiện câu báo đỏ và **không gửi**, ví dụ: *"Khách ຄຳຕຸ້ຍ chưa có mã khách bên kế toán…"*.
5. Đủ điều kiện thì hiện hộp hỏi: *"Bên kế toán sẽ tạo SO và ghi công nợ khách … (mã …) số … USD"* → bấm **Tạo SO bên kế toán** trong hộp.
6. Thành công thì thanh nút hiện **Đã có SO SO-…**. Hỏng thì hiện **Lần gửi trước chưa được: …** kèm câu của hệ anh. Ở danh sách, DO có nhãn **SO** (xanh) hoặc **SO ⚠** (vàng).

**Máy chủ LAO gửi:**

```http
POST https://demo-lao-api.goldensme.com/api/v1/integrations/logistics/sales-orders
Authorization: Bearer <token>
Content-Type: application/json
Accept: application/json
Idempotency-Key: logistics:EPLLAO-779739f4b582
```

```json
{"schemaVersion": 1,
 "header": {"do_id": "EPLLAO-779739f4b582", "status": "delivered", "customer_id": "<mã khách bên anh>",
            "route": {"id": "0b840ad2a162", "name": "ທ່າບົກ → ທ່າເຮືອກະລໍ", "distance_km": 360.0},
            "currency": "USD", "currency_thu": "USD", "currency_chi": "LAK",
            "selling_price": 905.85, "customer_surcharge_total": 0, "final_selling_price": 905.85,
            "billed_qty": 29.7, "origin": "ທ່າບົກ (ສະໜາມ EPL)", "destination": "ທ່າເຮືອກະລໍ",
            "trip_id": "779739f4b582", "vehicle_id": "b8b4e98da702", "driver_id": "e7c9c73fdb21",
            "weight_kg": 29700.0, "pod_receiver": "ນາງ ມະນີ", "pod_signed_at": "2026-09-29T13:42:50+00:00"},
 "details": [{"line_no": 1, "kind": "thu", "charge_type": "freight",
              "name": "Cước vận chuyển T4-0449-09/EPL · 29.7 t × 30.5 USD", "actual_amount": 905.85, "currency": "USD"}]}
```

Đây là gói **thật** của DO T4-0449-09/EPL, chỉ thay mã khách.

- **Gốc** lấy theo thứ tự: `QLSX_BASE_URL` nếu đặt; không thì giao thức + tên máy của `EPL_ACC_CODE_API`.
- **Token** lấy theo thứ tự: `QLSX_ACCESS_TOKEN` nếu đặt; không thì `EPL_ACC_CODE_TOKEN`.

**Luật LAO kiểm trước khi gửi** (lỗi nào cũng báo rõ và không gửi):

| Luật | Mã lỗi bên LAO |
|---|---|
| DO đã về **và** đã khoá | `DO_CHUA_KHOA` |
| Khách có **mã khách bên kế toán** (ô *Mã khách (bên kế toán)* ở danh mục khách) | `THIEU_MA_KHACH_KE_TOAN` |
| Mã khách: mở đầu bằng chữ Latinh hoặc số, chỉ chữ, số, `_ - .`, không có `/`, **≤ 37 ký tự** (đúng luật mã của anh; danh mục khách chặn ngay lúc gán) | `MA_KHACH_SAI` |
| Phiếu có tuyến; mã tuyến hợp lệ | `THIEU_TUYEN` · `MA_TUYEN_SAI` |
| `mã khách + "_" + mã tuyến` ≤ 50 ký tự (hệ anh dùng làm mã mặt hàng; mã tuyến 12 ký tự nên mã khách ≤ 37) | `MA_GHEP_QUA_DAI` |
| Số tiền gửi được chính xác (không bị làm tròn khi thành số JSON) | `TIEN_QUA_NHIEU_SO` |
| Tiền cước là VND, LAK hoặc USD | `TIEN_TE_CHUA_NHAN` (cước THB, CNY) |
| Cước > 0,01; `selling_price + phụ thu = final_selling_price = dòng thu` (Decimal, khớp chính xác) | `CUOC_BANG_KHONG` · `TIEN_SAI` |
| Người bấm là `acct` hoặc `admin` | 403 `KHONG_CO_QUYEN` |

**Hệ anh trả → LAO làm:**

| Hệ anh trả | LAO làm |
|---|---|
| 201, hoặc 200 `replayed: true`, kèm `data` | đánh **đã tạo SO**; lưu `orderId`, `orderCode`, `orderStatus`, `retkAutoId`, `retkCode`, `itemCode`, `currency`, `totalAmount`, `initialDebtAmount`. Bấm lại thì trả kết quả cũ, **không gọi nữa** |
| 409 (trùng DO / khoá khác nội dung) | đánh **xung đột**, **khoá nút gửi**: hai bên đối soát |
| 4xx dữ liệu (400 `INVALID_DO`, 422 `52905`…) | ghi câu lỗi lên DO. Lần sau **dựng gói mới** theo số hiện tại: hệ anh chưa ghi gì |
| 401 thân rỗng | báo **token sai hoặc hết hạn** |
| 403 thân rỗng | báo **tài khoản của token chưa nằm trong `LogisticsSalesPush.AllowedUserIds`** hoặc chưa gắn nhân viên |
| mất mạng · hết giờ · 5xx (gồm 503 `LOGISTICS_DISABLED`, `LOGISTICS_CONFIG_REQUIRED`, `LOGISTICS_DATABASE_ERROR`) · 422 `52903` | kết quả **chưa rõ**: lần sau gửi lại **đúng gói, đúng khoá** đã lưu |
| 200 kèm `Success: false` | coi là lỗi, dù HTTP 200 |

**Sau khi có SO:** kế toán LAO **không mở khoá** DO đó được (409 `DA_TAO_SO`). Chỉ Sếp mở, sau khi đã báo anh.

**Mã DO.** `do_id` = `EPLLAO-<Trip.id>`. Hướng dẫn của anh nói `doId` là duy nhất **toàn bảng**, không chia theo nguồn. Tiền tố `EPLLAO-` giữ cho DO bên Lào không bao giờ trùng DO của EPL_System (`DO-2026-…`).

**Kết quả gửi thử 01/10** (máy thử, bản sao dữ liệu):

| | |
|---|---|
| DO | `EPLLAO-779739f4b582` = phiếu **T4-0449-09/EPL**, 29,7 t × 30,5 USD = **905.85 USD** |
| Mã khách gửi | `EPLLAO-THU-01`: mã thử, **cố ý không có** trong danh mục bên anh |
| Hệ anh trả | `HTTP 422` · `{"code":"LOGISTICS_52905","message":"Mã khách không tồn tại hoặc bị trùng trong PUBOBJECT.OBJ_OBJECTNO."}` |
| Kết luận | token qua cửa xác thực; gói qua kiểm khuôn; USD được nhận; hệ anh dừng ở bước **tìm khách**. **Không tạo SO, công nợ, mặt hàng nào** |

**Vì sao chưa tạo được SO thật:** danh mục khách chi nhánh 1368 bên anh (đọc 01/10) có **189 khách**, đều của EPL_System bên Việt Nam (`DEMO-CUS-…`, `KH-0015`…). **Chưa có khách EPL Lào nào.**

Chi tiết: hợp đồng mục 3.2 và 3.2.1.

### 1.3. A3 — các đường chỉ đọc đã gọi thử (không nằm trong mã chạy)

Gọi bằng token cấu hình, **chỉ đường xem, danh sách, tìm**. Không gọi đường tạo, lưu, commit, ghi sổ, xoá nào.

| Đường | Đọc được |
|---|---|
| `GET /api/v1/ping` · `GET /api/v1/auth/info` · `GET /api/v1/auth/branches` | máy sống; người dùng `tune` (UserID 846, ObjectId 1503); chi nhánh được vào 1368 · 5 · 1369 |
| `GET /api/v1/common/GetCompanyAndBranch` | đơn vị 2, 1368, 5, 1369 — **đều quốc gia Việt Nam, tiền VND** |
| `GET /api/v1/common/GetFinancyCicle` | 22 kỳ tài chính; ID **không theo thứ tự tháng** (9/2026 = 20, 10/2026 = 19) |
| `GET /api/v1/common/GetAllCurrency` | **3 = VND, 26 = LAK**; chưa có USD, THB, CNY |
| `GET /api/v1/sales/debt/payment-methods` | 1 Tiền mặt · 3 Chuyển khoản · 6 Tiền mặt/Chuyển khoản; chưa có "cấn trừ" |
| `GET /api/v1/accounting/cmpayment-receipt/document-types?voucherType=ALL` | 14 Thu hoá đơn · 15 Thu công nợ · 16 Thu trước · 17 Thu khác · 57 Chi hoá đơn · 58 Chi công nợ · 59 Chi trước · 60 Chi khác · 68 Chuyển tiền nội bộ; **không có "chi tạm ứng"** |
| `GET …/cmpayment-receipt/default-money-account?countryId=11&isCash=&isLocal=` (4 tổ hợp) | tiền mặt Kíp 1011 · tiền mặt ngoại tệ 1012 · ngân hàng Kíp 1021 · ngân hàng ngoại tệ 1022 |
| `GET /api/v1/accounting/lao-accounts` · `GET …/cmpayment-receipt/country-accounts?countryId=11` | 494 mã · 405 mã cho hạch toán; **chưa có 1371, 4021, 4022** |
| `GET /api/v1/accounting/cash-voucher-references?type=DO` | 23 DO, **đều là DO mẫu của EPL_System** (khách `DEMO-CUS-…`) |
| `POST /api/v1/master-data/customers/list` · `POST …/suppliers/list` | chi nhánh 1368: **189 khách**, **517 nhà cung cấp**; không có đối tượng EPL Lào |

Các đường kho (`supply-chain/*`, `report/inventory/*`, `items/search`) cũng có đọc ngày 30/09, nhưng **kho là hệ riêng của anh Toàn**, bên em không dùng máy này cho kho.

Số chi tiết: hợp đồng mục 12.7.

### 1.4. A4 (đã nối 01/10) · A5 (chưa làm)

**A4 — đề nghị tạm ứng (PTU) → phiếu chi bên anh; thủ quỹ chi và ghi sổ bên anh; trạng thái về LAO.** Chủ dự án chốt 01/10: *"chi thật là anh Tune xong update trạng thái về bên mình"*. Chi tiết: hợp đồng mục 12.10.

**Người bấm và chỗ bấm:**

1. KT Chi phí VC ghi sổ mục IV trên phiếu xuất xe → máy tạo phiếu chi "Chi trước" bên anh (chưa ghi sổ).
2. Thủ quỹ mở hệ anh → Phiếu chi → tìm theo số tham chiếu (số PTU in trên tờ tài xế cầm tới) → chi tiền → **Ghi sổ**.
3. Trên LAO: màn **Phiếu đề nghị chi** hiện "Chờ thủ quỹ chi ở hệ kế toán · 1368-CTR-…"; ghi sổ xong thì thành "Đã chi (kế toán)". Ô mục IV trên phiếu xuất xe cũng hiện trạng thái đó.
4. Tài xế bấm **Xuất phát**: LAO hỏi lại hệ anh; đã ghi sổ thì đi được, chưa thì câu báo nói số phiếu chi đang chờ.

**Các đường của anh bên em gọi:**

| Đường | Để làm gì |
|---|---|
| `POST /api/v1/master-data/staff/list` · `staff/upsert` | đối tượng tài xế `EPLTX-<mã>`: tìm, chưa có thì tạo |
| `GET /api/v1/common/GetAllCurrency` · `GetFinancyCicle` | mã tiền LAK, mã kỳ theo ngày |
| `POST /api/v1/accounting/cmpayment-receipt/list` | chống trùng: đối tượng + `DOC_REFDOCUMENTNO` = số PTU |
| `POST /api/v1/accounting/cmpayment-receipt/save-and-commit` | tạo phiếu chi, `PostMode = None` |
| `GET /api/v1/accounting/cmpayment-receipt/{id}?voucherType=CMP` | đọc `Master.STATUS` (12/13 = đã chi), `POSTNAME`, `POSTDATE` |
| `POST /api/v1/accounting/cmpayment-receipt/delete` | rút phiếu chưa ghi sổ (số đổi, phiếu bên em bị xoá / huỷ, Sếp chi tay) |

**Còn mở:** xe thuê cần mã 4022 bên anh; tài khoản dịch vụ thay token cá nhân (hết hạn 10/10); đơn vị EPL Lào riêng (đang 1368).

**A5 — xem công nợ khách:** `POST /api/v1/sales/debt/customer-detail` với `{CustomerObjectId, OrgId}`, trả `Customer, Summary, Aging, Debts, Collections, Orders`. Bên em **chỉ đọc và hiện**, thay đường tạm của KT tạm. **Cần anh** một mẫu thân trả về thật (khối `Debts`, `Collections` là dynamic).

---

## 2. Hệ anh gọi sang LAO

### 2.1. Khoá bàn giao

- Mọi lời gọi B1, B2 mang `Authorization: Bearer <khoá bàn giao>`.
- Khoá **riêng cho hệ anh** (cấu hình `token_nhan_qlsx`), không dùng chung với khoá của KT tạm.
- **Sếp tạo khoá:** `POST /api/handover/tao-khoa` (chỉ vai `admin`). Khoá trả **đúng một lần**; tạo lại thì khoá cũ hết hiệu lực ngay.
  - Hiện **chưa có nút** trên màn. Màn **Tài khoản** chỉ có nút tạo khoá cho KT tạm.
  - Em thêm nút ở màn Tài khoản khi có địa chỉ ra Internet.
- Sếp xem đã có khoá chưa: `GET /api/handover/trang-thai` → `{co_khoa, so_do_ban_giao_duoc, duong_danh_sach, duong_chi_tiet}`.
- Kế toán / Sếp xem đúng gói hệ anh sẽ nhận của một phiếu, không cần khoá: `GET /api/handover/xem-truoc/{trip_id}`.
- Lỗi:
  - 401 `SAI_TOKEN`: thiếu khoá hoặc khoá sai;
  - 503 `CHUA_DAT_TOKEN`: bên em chưa tạo khoá.

### 2.2. B1 — danh sách DO đã xong

`GET /api/handover/delivery-orders?customer_id=&completed_from=YYYY-MM-DD&completed_to=YYYY-MM-DD&page=1&page_size=50`

- Chỉ trả phiếu **đã về và đã khoá**, mới khoá trước. `total` là tổng thật sau lọc.
- Tham số `customer_id` nhận **mã khách bên anh** (`OBJ_OBJECTNO`) **hoặc** mã khách nội bộ bên em (12 ký tự hex).
- **Đổi 01/10:** trong mỗi dòng, `customer_id` = **mã khách bên anh** (null khi kế toán chưa gán), trùng `customer_id` gửi SO. Màn "Vụ việc" bên anh hiện ô này làm tên khách. Mã nội bộ bên em ở `customer_ref`.
- Mỗi dòng có **14 khoá của EPL_System**: `do_id`, `status`, `customer_id`, `quotation_id`, `route_id`, `vehicle_id`, `driver_id`, `selling_price`, `customer_surcharge_total`, `final_selling_price`, `currency`, `completed_at`, `completed_by`, `detail_url`.
- Thêm các khoá đọc bằng mắt: `doc_no`, `customer_code`, `customer_ref`, `customer_name`, `truck_no`, `plate_head`, `driver_name`, `company`, `owner_name`, `final_selling_price_lak`.

```json
{"message": "Danh sách 13 lệnh giao hàng đã hoàn tất (trang 1).",
 "data": {"items": [{"do_id": "EPLLAO-779739f4b582", "status": "delivered", "doc_no": "T4-0449-09/EPL", "kind": "giao",
                     "customer_id": "<OBJ_OBJECTNO hoặc null>", "customer_code": "<như customer_id>",
                     "customer_ref": "<mã khách bên em>", "customer_name": "ຄຳຕຸ້ຍ",
                     "quotation_id": null, "route_id": "0b840ad2a162", "vehicle_id": "b8b4e98da702", "truck_no": "346",
                     "driver_id": "e7c9c73fdb21", "selling_price": 905.85, "customer_surcharge_total": 0,
                     "final_selling_price": 905.85, "currency": "USD", "final_selling_price_lak": 19928700,
                     "completed_at": "2026-09-29T06:42:51+00:00", "completed_by": "<người khoá>",
                     "detail_url": "/api/handover/delivery-orders/EPLLAO-779739f4b582"}],
          "total": 13, "page": 1, "page_size": 50}}
```

### 2.3. B2 — một DO: header + details

`GET /api/handover/delivery-orders/{do_id}` → `{"message", "data": {"header": {...}, "details": [...]}}`

- `header`:
  - DO, ngày, xe hai biển, tài xế, khách (`customer_id` = mã bên anh, `customer_ref` = mã bên em), tuyến;
  - cân đầu / cân cuối, biên bản giao nhận (POD);
  - tiền cước theo tiền của phiếu, tỷ giá khoá trên phiếu;
  - tổng chi EPL chịu theo mục III–VI, lãi;
  - **thêm 01/10** các khoá màn "Vụ việc" bên anh đọc: `trip_status`, `actual_cost_total`, `actual_cost_total_quy_doi`, `margin_amount`, `margin_percent`, `fx_rate`, `fx_rate_source`;
  - xe thuê có thêm khối `hire` (tiền thuê, phí 2 %, trừ quá tải, EPL đã ứng, còn phải trả chủ xe).
- `details`:
  - dòng 1 là **thu** (cước, `acc_code` 1211/708);
  - các dòng sau là **chi**, mỗi dòng có `section` (III–VI), số lượng, đơn giá, tiền của dòng, `amount_lak`, **`acc_code` Nợ/Có thật** trong danh mục Lào, `paid_by` (`epl` hay `chu_xe`);
  - mọi dòng có `calculation` (thêm 01/10), ví dụ `29.7 t × 30.5 USD`.
- Lỗi: 404 `DO_KHONG_THAY` · 409 `DO_CHUA_KHOA`.

Bảng từng khoá: hợp đồng mục 12.8.3.

### 2.4. B3 — báo lại trạng thái và đọc số (nhóm `/api/lien-thong/*`)

Nhóm này KT tạm đang gọi. Khi hệ anh **thay KT tạm** thì hệ anh gọi các đường **ghi bản chép** dưới đây, để màn bên em hiện đúng "đã hoá đơn", "đã thu", "đã trả chủ xe".

| Mã | Đường | Anh báo gì |
|---|---|---|
| B6 | `POST /api/lien-thong/doanh-thu/xuat` | các phiếu đã lên hoá đơn (từng phiếu hoặc tờ gộp tháng) |
| B7 | `POST /api/lien-thong/doanh-thu/bo-xuat` | bỏ hoá đơn |
| B8 | `POST /api/lien-thong/doanh-thu/da-thu` | **tổng** đã thu quy Kíp của từng phiếu (số tuyệt đối, gửi lại vô hại) |
| B12 · B13 | `POST /api/lien-thong/chu-xe/tra` · `/bo-tra` | đã trả / bỏ trả chủ xe liên kết |
| B25 | `POST /api/lien-thong/cap-phat/{vid}/cap` | đã chi tạm ứng (nếu việc chi thật chuyển sang hệ anh, câu hỏi 10.6) |

Các đường **đọc số** (B2–B5, B9–B11, B14–B24): cước, tiền thuê chủ xe, tất toán tài xế, nợ nhà cung cấp, cấn trừ, tỷ giá.

- Xác thực nhóm này: khoá máy của LAO cộng `X-Nguoi-Dung` (tên đăng nhập có thật ở LAO).
- Bên em đề nghị thêm **tài khoản dịch vụ** `qlsx` có danh sách đường được gọi (hợp đồng mục 2.2).

Chi tiết: hợp đồng mục 4.

### 2.5. Địa chỉ ra Internet

B1, B2, B3 chỉ gọi được khi trang điều xe Lào có địa chỉ ra Internet.

- **Chủ dự án chốt 01/10:** làm xong hết rồi mới host, lúc đó bên em gửi anh **địa chỉ gốc** và **khoá bàn giao**.
- Địa chỉ gửi anh phải là địa chỉ **cuối**, đúng `https://`: hệ anh tắt tự chuyển hướng.
- Anh **sửa mã** nguồn DO cho đơn vị EPL Lào (mục 8.2), rồi gọi thử `cash-voucher-references?type=DO`.

---

## 3. Một DO đi từng bước — ai bấm, sinh tờ gì, tờ đi đâu

| # | Bước | Ai bấm · ở đâu | Tờ | Hôm nay đi đâu | Khi nối xong hệ anh |
|---|---|---|---|---|---|
| 1 | Lập phiếu xuất xe | Bãi · menu **Phiếu xuất xe** → lưu phiếu | `DO` | sổ chứng từ LAO → KT tạm | hệ anh **đọc** qua B1/B2 |
| 2 | Lập / in đề nghị tạm ứng (tiền mặt tài xế cầm đi) | Bãi hoặc kế toán · trên phiếu, in tờ tạm ứng có QR | `PTU` | sổ chứng từ → KT tạm | **A4**: phiếu chi chờ CMP ở hệ anh |
| 3 | Lập / in đề nghị xuất kho nhiên liệu (mỗi kho một tờ) | Bãi hoặc kế toán · in tờ có QR | `PLNL` | sổ chứng từ → KT tạm | **hệ kho anh Toàn** (không sang anh Tune) |
| 4 | Quỹ chi tạm ứng | Quỹ tiền mặt · quét QR tờ tạm ứng, hoặc bấm *Chi tiền* ở mục IV | `PC_TU` (xe nhà 1601/1011 · xe thuê 4022/1011) | sổ chứng từ → KT tạm | thủ quỹ bên anh chi → CMP ở hệ anh; anh báo lại bằng B25 |
| 5 | Thủ kho cấp dầu theo đề nghị | Thủ kho · quét QR tờ xuất kho | `PXK_NL` (tờ kho) | sinh ở **kho** (KT tạm, sau là hệ anh Toàn) | hệ kho anh Toàn |
| 6 | Quỹ chi mục V, VI trả ngay | Quỹ · duyệt mục trên phiếu | `PC_SC` (xe nhà 614/1011 · xe thuê 4022/1011) | sổ chứng từ → KT tạm | CMP ở hệ anh |
| 7 | Xe về, **khoá phiếu** | KT Thu/Chi Viêng Chăn · **Phiếu xuất xe** → nút **Khoá phiếu** | `PDT` | sổ chứng từ → KT tạm | **A2 → SO + công nợ** (nút *Tạo SO bên kế toán*) |
| 8–13 | Hoá đơn, thu tiền, cấn trừ, trả chủ xe, tất toán tài xế, trả nhà cung cấp | kế toán, quỹ | `HD`, `PT`, `PC_CX`, `QT_TU`, `TT_CHI`, `TT_THU`, `PC_NCC` | **sinh ở KT tạm**, không ở LAO | **việc của hệ anh**; anh báo lại bằng B6, B8, B12 |

Theo chốt 29/09, bên em **chỉ gửi đề nghị** (bước 1, 2, 3, 7) và nhận trạng thái về. Bước 4 và 6 đang chạy trên LAO **vì bản tạm**. Khi hệ anh làm việc chi thật, hai bước đó chuyển sang hệ anh (câu hỏi 10.6).

---

## 4. Phiếu đề nghị, chứng từ: đã đẩy sang hệ anh chưa, nối thế nào

### 4.1. Hiện trạng

Có **hai đường** đưa chứng từ ra khỏi trang điều xe:

1. **Sổ chứng từ → KT tạm.**
   - Mỗi bước ghi một tờ vào bảng `chung_tu` của LAO.
   - Người được đẩy bấm menu **Đề nghị theo DO** → nút **Đẩy** (một tờ) hoặc **Đẩy hết tờ chưa đẩy**.
   - LAO gọi `POST {ke_toan_api}/api/v1/epl-lao/vouchers`, mỗi lần một tờ (phong bì ở mục 4.3; bảng trường ở hợp đồng mục 3.1).
   - `ke_toan_api` hiện trỏ vào **KT tạm**. **Hệ anh chưa có đường `/api/v1/epl-lao/vouchers`**, nên **chưa tờ nào đi sang hệ anh bằng đường này**.
2. **PDT → SO của anh (A2), từ 01/10.** Đây là đường **duy nhất** đang nối thẳng sang hệ anh.

**Kiểm lại tối 01/10 trên máy `demo-lao-api`** (tải swagger `/swagger/v1/swagger.json`, chỉ đọc):

- Hệ anh có **705 đường, không đổi** so với bản chụp 30/09.
- **Không có** đường nhận phong bì chứng từ (`/api/v1/epl-lao/vouchers`) hay đường "phiếu đề nghị" nào.
- Đường dành cho logistics chỉ có `POST /api/v1/integrations/logistics/sales-orders` (đã nối, A2).
- Đường **có thể dùng** cho đề nghị tạm ứng: nhóm phiếu thu chi `…/cmpayment-receipt/*`, tức `save-and-commit`, hoặc chuỗi `create-session` → `save-session` → `commit-session`; mục 1.4. Muốn dùng thì cần mã số ở mục 1.4, và **đối tượng tài xế** phải có trong danh mục của anh (`ObjectId` bắt buộc > 0).
- Nhóm `/api/v1/hr/salary-advances/*` là **tạm ứng lương** của nhân sự, **không phải** tạm ứng chuyến (Nợ 1601 theo từng DO), nên bên em không dùng.

Số tờ trên máy thử (bản sao dữ liệu) ngày 01/10, cột "đã đẩy" là đã đẩy sang **KT tạm**:

| Tờ | Tổng | Đã đẩy |
|---|---|---|
| `DO` | 53 | 30 |
| `PTU` | 41 | 20 |
| `PLNL` | 29 | 10 |
| `PC_TU` | 28 | 24 |
| `PDT` | 0 | 0 |

- 13 DO đã khoá trên máy thử khoá **trước ngày có đề nghị thu** (30/09), nên chưa có tờ `PDT`.
- Nút *Tạo SO bên kế toán* **không cần** tờ `PDT` có sẵn: gói SO dựng thẳng từ phiếu.

### 4.2. Từng loại

| Tờ | Có tiền không | Hôm nay | Đề nghị nối với hệ anh | Anh cần làm |
|---|---|---|---|---|
| `DO` | không | đẩy sang KT tạm | **không đẩy**: anh đọc qua B1/B2 (đủ header, dòng thu, dòng chi, mã kế toán) | trỏ nguồn Logistics của EPL Lào sang LAO (câu hỏi 12.8 (2)) |
| `PTU` | LAK | đẩy sang KT tạm | **A4**: CMP ở trạng thái chờ, hoặc thủ quỹ bên anh tự lập từ tờ in | mã số và trả lời ở mục 1.4 |
| `PLNL` | không (lít) | đẩy sang KT tạm | **không sang anh Tune**: phiếu đề nghị xuất kho đi sang **hệ kho anh Toàn** (hợp đồng kho riêng) | — |
| `PDT` | tiền cước | đẩy sang KT tạm **và** A2 | **A2 đã nối** | tạo khách EPL Lào (mục 5) |
| `PC_TU` · `PC_SC` | LAK | sinh khi quỹ chi **trên LAO**, đẩy sang KT tạm | khi chi thật ở hệ anh thì **không sinh ở LAO nữa**; anh báo lại "đã chi" (B25 hoặc đường mới) | trả lời câu hỏi 10.6 |
| tờ kho `PXK_*`, `PNK_*`, `CK_NL`, `*_HH` | giá vốn | sinh ở kho (KT tạm) | hệ kho anh Toàn | câu hỏi 10.11: tờ kho có định khoản vào sổ anh bằng đường nào |

### 4.3. Phong bì chứng từ (đường 1) — mẫu thật

Mỗi tờ một lần gọi. `ref` = số tờ bên em, dùng làm khoá chống trùng.

**PTU — đề nghị tạm ứng** (không định khoản; tiền LAK):

```json
{"source": "EPL_LAO", "ref": "PTU/2609/0036", "type": "PTU", "type_name": "Phiếu đề nghị tạm ứng", "group": "other",
 "date": "2026-09-30", "trip_no": "THU-PL-30153319/EPL", "party": {"kind": "tai_xe", "name": "ທ້າວ ທັດສະດາພອນ"},
 "amount": {"value": 200000.0, "currency": "LAK", "lak": 200000.0},
 "entry": {"debit": null, "debit_name": null, "credit": null, "credit_name": null},
 "memo": "Đề nghị tạm ứng phiếu THU-PL-30153319/EPL",
 "lines": {"voucher_id": "1a1de91b4d21", "doc_no": "PTU-THU-PL-30153319/EPL", "hinh_thuc": "noi_bo", "owner_id": null, "owner_name": null},
 "created_by": "ສົມໄຊ (Somchai)", "created_at": "2026-09-30T08:33:21.141238"}
```

**PLNL — đề nghị xuất kho nhiên liệu** (không tiền; số lít ở `lines.qty_l`):

```json
{"source": "EPL_LAO", "ref": "PLNL/2609/0029", "type": "PLNL", "type_name": "Phiếu đề nghị xuất kho nhiên liệu", "group": "other",
 "date": "2026-09-30", "trip_no": "THU-PL-30153319/EPL", "party": {"kind": "kho", "name": "ສາງນໍ້າມັນ ທ່າບົກ (Kho dầu Thà Bốc)"},
 "amount": {"value": null, "currency": "LAK", "lak": null},
 "entry": {"debit": null, "debit_name": null, "credit": null, "credit_name": null},
 "memo": "Lĩnh 60.0 lít tại ສາງນໍ້າມັນ ທ່າບົກ (Kho dầu Thà Bốc)",
 "lines": {"voucher_id": "fc6a2e23167f", "doc_no": "PLNL-THU-PL-30153319/EPL-1", "qty_l": 60.0, "hinh_thuc": "noi_bo", "owner_id": null, "owner_name": null},
 "created_by": "ສົມໄຊ (Somchai)", "created_at": "2026-09-30T08:33:19.873296"}
```

**PC_TU — chi tạm ứng** (có định khoản gợi ý; từng dòng mang mã kế toán):

```json
{"source": "EPL_LAO", "ref": "PC_TU/2609/0024", "type": "PC_TU", "type_name": "Phiếu chi theo đề nghị tạm ứng", "group": "payment",
 "date": "2026-09-30", "trip_no": "LOHONG-30142631/EPL", "party": {"kind": "tai_xe", "name": "ທ້າວ ຄຳສີ"},
 "amount": {"value": 2133500.0, "currency": "LAK", "lak": 2133500.0},
 "entry": {"debit": "1601", "debit_name": "Tạm ứng nhân viên", "credit": "1011", "credit_name": "Tiền mặt bằng Kíp"},
 "memo": "Chi mục IV đi đường phiếu LOHONG-30142631/EPL",
 "lines": {"truck_no": "341", "driver_id": "fbd34d1a367e", "hinh_thuc": "noi_bo", "owner_id": null, "owner_name": null,
           "lines": [{"item": "x_food", "qty": 2.0, "unit_price": 150000.0, "currency": "LAK", "acct_code": "625/1601"},
                     {"item": "x_toll", "qty": 1.0, "unit_price": 1833500.0, "currency": "LAK", "acct_code": "625/1601"}]},
 "created_by": "ນາງ ດາວ (Dao)", "created_at": "2026-09-30T07:26:35.429485"}
```

**DO — phiếu xuất xe** (không tiền; chỉ để bên nhận biết có chuyến):

```json
{"source": "EPL_LAO", "ref": "DO/2609/0048", "type": "DO", "type_name": "Phiếu xuất xe · đề nghị xuất xe", "group": "other",
 "date": "2026-09-30", "trip_no": "THU-PL-30153319/EPL", "party": {"kind": "khach", "name": "ຄຳຕຸ້ຍ"},
 "amount": {"value": null, "currency": "LAK", "lak": null},
 "entry": {"debit": null, "debit_name": null, "credit": null, "credit_name": null},
 "lines": {"truck_no": "354", "driver_name": "ທ້າວ ທັດສະດາພອນ", "company": "EPL"},
 "created_by": "ສົມໄຊ (Somchai)", "created_at": "2026-09-30T08:33:19.321787"}
```

(Số phiếu `THU-PL-…`, `LOHONG-…` là phiếu của bộ kiểm trên máy thử.)

### 4.4. Anh chọn cách nhận các tờ còn lại (câu hỏi 10.13)

| Cách | Anh làm | Bên em làm |
|---|---|---|
| **(1) Một cửa nhận phong bì** | dựng `POST /api/v1/epl-lao/vouchers` nhận đúng phong bì 4.3, tự rẽ vào CMP / CMR / kho theo `type` và `group` | chỉ đổi địa chỉ `ke_toan_api` sang hệ anh |
| **(2) Mỗi loại một đường của anh** | không làm đường mới | gọi từng đường của anh: SO (đã làm), CMP cho `PTU` (A4)… và bỏ đẩy phong bì |

Bên em làm được cả hai. Cách (2) khớp các đường anh đã có. Cách (1) ít việc cho bên em nhất.

---

## 5. Hệ anh cho LAO: đã có, còn chờ

**Đã có:**

- token cho A1, A2 (tài khoản `tune`, **hết hạn 10/10/2026 09:05 giờ Lào**; sau ngày đó A1 rơi về bản chụp danh mục, A2 không gửi được);
- hướng dẫn `sales-orders`, hướng dẫn thu chi CM;
- danh mục tài khoản 494 mã;
- mã số ở mục 1.3.

**Còn chờ, xếp theo thứ tự cần trước:**

1. **Khách EPL Lào** trong danh mục đối tượng (PUBOBJECT), kèm `OBJ_OBJECTNO`. Hoặc anh cho bên em tự tạo qua `POST /api/v1/master-data/customers/upsert`: đường ghi, bên em chưa gọi.
   - **Chặn A2 ngay lúc này.**
   - Trên dữ liệu thử có 3 khách: ຄຳຕຸ້ຍ (9 DO chờ), ນາງ ວັນນາ (2), ບໍລິສັດ ລາວ-ຈີນ ມີເນີໂຣ (2). Danh mục thật lấy ở màn **Khách hàng** của máy thật.
2. **Tài khoản dịch vụ** cho trang điều xe, thay token cá nhân sắp hết hạn.
3. **Mở ba mã con** 1371, 4021, 4022 (hợp đồng mục 1.1).
4. **Đơn vị EPL Lào** (quốc gia 11, tiền LAK). Hiện SO vào chi nhánh cố định 1368 "Demo EPL" (Việt Nam, VND). Thà Bốc và Viêng Chăn là một hay hai đơn vị?
5. **Tiền USD, THB, CNY** trong danh mục tiền của CM (`CurrencyId`), và SO nhận THB / CNY (câu hỏi 10.3).
6. ~~**Chi tạm ứng:** `DotyAutoId`, ai lập phiếu chi~~ — **đã nối 01/10**: 59 "Chi trước", LAO lập phiếu chờ, thủ quỹ bên anh chi và ghi sổ (mục 1.4).
7. **Đối tượng** tài xế, chủ xe liên kết, nhà cung cấp EPL Lào.
8. **Cách nhận các tờ còn lại** (mục 4.4).
9. **Mẫu `customer-detail` thật** cho màn công nợ (A5).
10. ~~**Nguồn DO theo đơn vị**~~ — **bên em đã sửa** `CashVoucherReferenceController` trên nhánh `feat/HonTunedaHai` (mục 8.2). Lên máy chủ demo thì thêm mục `LogisticsSource` vào `appsettings.laos.json`.
11. **`AllowedUserIds`:** thêm `UserId` của tài khoản dịch vụ bên em vào `LogisticsSalesPush.AllowedUserIds` (mục 8.1).
12. ~~**Màn "Vụ việc"**~~ — **bên em đã sửa** trên nhánh Web `feat/hontunedhai_Laos` (mục 8.2).

---

## 6. Việc tiếp theo

| Ai | Việc |
|---|---|
| **Anh Tune** | mục 5, từ việc 1; đọc lại hợp đồng v2.1 (nhất là mục 12.9) và soạn lại phía anh |
| **Bên em** | khi có mã khách: ghi mã (KT Thu/Chi VC), gửi SO thật một DO, đối chiếu `orderCode`, `totalAmount` với tờ đề nghị thu · khi có mã số mục 1.4: dựng A4 · khi có mẫu: dựng A5 · thêm nút tạo khoá bàn giao ở màn Tài khoản |
| **Chủ dự án** | host trang điều xe Lào ra Internet khi làm xong hết, rồi gửi anh Tune địa chỉ + khoá bàn giao (mục 2.5) |

---

## 7. Thử lại bằng tay (cho chủ dự án)

**Gửi SO một DO:**

1. Đăng nhập **ketoan** (KT Thu/Chi Viêng Chăn).
2. Menu **Khách hàng** → bấm khách → **Sửa** → ô **Mã khách (bên kế toán)** → gõ mã anh Tune cấp → **Lưu thay đổi**.
   - Vai Bãi mở form này thì ô mã **khoá lại**, ghi *"KT Thu/Chi Viêng Chăn gán mã theo bên kế toán"*.
3. Menu **Phiếu đề nghị thu** → **Tháng** chọn tháng của DO → bấm DO đã khoá của khách đó.
4. Bấm **Tạo SO bên kế toán** → đọc hộp hỏi (khách, mã, số tiền) → bấm **Tạo SO bên kế toán**.
5. Thành công: thanh nút hiện **Đã có SO …**, danh sách có nhãn **SO**. Hỏng: hiện **Lần gửi trước chưa được: …** với câu của hệ anh.

**Xem đúng gói DO hệ anh sẽ đọc:** em chạy giúp `GET /api/handover/xem-truoc/<trip_id>` bằng tài khoản kế toán / Sếp. Mở thẳng đường này trên trình duyệt thì bị 401, vì trang giữ khoá đăng nhập trong máy chứ không dùng cookie.

**Bộ kiểm tự động** (máy thử, không gọi sang hệ anh):

- `kiem/thu_tao_so.py`: 23 chỗ kiểm, gồm quyền, luật chặn, khuôn gói SO;
- `kiem/thu_luat_so_ben_tune.py`: luật kiểm của anh Tune chạy trên gói SO của mọi DO đã khoá (13/13 qua);
- `kiem/thu_ban_giao.py`: 32 chỗ kiểm cho B1/B2, gồm các khoá màn "Vụ việc" đọc;
- `kiem/thu_khach_hang_moi.py`: mã khách, chỉ `acct` và admin gán, đúng luật mã bên anh.

---

## 8. Đọc mã nguồn của anh (01/10/2026)

Chủ dự án lấy về `GLS-QLSX-APIs` (commit `31c98db`) và `GLS-QLSX-Web` (commit `de04913f`), nhánh `feat/DemoLao`. Bên em **chỉ đọc**: không sửa, không chạy, không mở cấu hình bí mật. Chi tiết đầy đủ: hợp đồng mục 12.9.

### 8.1. Tạo SO (A2) — khớp

- Bên em chép đúng luật của `LogisticsPushValidator` và phần kiểm đầu của `sp_Logistics_CreateSalesOrder` thành bộ kiểm `kiem/thu_luat_so_ben_tune.py`. Chạy trên 13 DO đã khoá: **cả 13 qua**.
- **Dòng `chi`:** hệ anh chỉ ghép chúng thành chữ trên SO của khách, không thành bút toán → bên em **giữ một dòng thu** (câu hỏi 10.4 đã có lời đáp).
- **403 thân rỗng** = tài khoản token chưa nằm trong `LogisticsSalesPush.AllowedUserIds`, hoặc chưa gắn nhân viên. Bên em nay báo đúng lý do.
- **Chi nhánh 1368, người tạo 4, quốc gia 11 ghi cứng** trong thủ tục. Tạo đơn vị riêng cho EPL Lào thì thủ tục phải đổi theo.
- **Mã khách:** mở đầu bằng chữ / số, chỉ chữ, số, `_ . -`; ghép với mã tuyến ≤ 50 ký tự. Bên em sửa danh mục khách cho khớp (không `/`, tối đa 37 ký tự).

### 8.2. Nguồn DO cho phiếu thu chi (B1, B2) — phía anh cần sửa

- **Đã sửa 01/10 trên nhánh `feat/HonTunedaHai` (commit `465748b`)** — trước đó: `CashVoucherReferenceController` gọi Logistics bằng một địa chỉ **ghi cứng**: `http://senvangsolutions.com:1506/api/` (EPL_System bên Việt Nam), **không kèm `Authorization`**.
- Trang điều xe Lào là dữ liệu khách thật nên **đòi khoá bàn giao**. Anh cần đưa địa chỉ + khoá ra cấu hình **theo đơn vị** và gửi `Authorization: Bearer <khoá bàn giao>`. Gợi ý mã ở hợp đồng 12.9.2.
- Giới hạn bên anh: hết giờ 15 giây, gói ≤ 2 MB, không chuyển hướng. Gói bên em: một DO 4–7,4 KB, một trang 13 DO 11 KB, mỗi lời gọi dưới 0,4 giây.
- **Bên em đã sửa gói theo màn "Vụ việc" của anh:** `customer_id` = mã khách bên anh (null khi chưa gán), mã bên em ở `customer_ref`; thêm `trip_status`, `actual_cost_total`, `actual_cost_total_quy_doi`, `margin_amount`, `margin_percent`, `fx_rate`, `fx_rate_source`, `details[].calculation`. Trước đó màn của anh sẽ hiện chi phí và lãi bằng 0.
- **Xin anh xem ở màn "Vụ việc":** hiện `doc_no`, `truck_no` / `plate_head`, `driver_name` thay vì mã nội bộ 12 ký tự; thoát ký tự trước khi chèn chuỗi từ Logistics vào HTML.

### 8.3. Hoá đơn điện tử

Dịch vụ mới `Backend.LaoInvoice` (01/10) **chưa nối SO hay DO**. Bên em không gọi.

### 8.4. Nối thêm buổi trưa 01/10

Chi tiết ở hợp đồng mục 12.11:
- SO đã tạo thật, khách tự tạo;
- công nợ khách xem từ hệ anh;
- xe thuê: tạm ứng đứng tên chủ xe, trả chủ xe qua phiếu chi bên anh;
- tài khoản tích hợp tự đăng nhập.

**Còn chặn:** bật USD, tạo tài khoản tích hợp, API bút toán tổng hợp để ghi chi phí thuê xe *Nợ 621 / Có 4022* (đã chốt 01/10) (12.11.5).

### 8.5. Chiều 01/10

Chi tiết ở hợp đồng mục 12.12:
- **đã mở 1371 / 4021 / 4022** (137, 402 thành tài khoản tổng hợp); tạm ứng xe thuê, trả chủ xe chạy thật;
- **bản host nối DB khác** bản chạy ở máy: lúc triển khai phải mở lại ba mã trên DB host;
- **tài khoản tích hợp:** 6 bước làm cụ thể (12.12.3);
- **bút toán chi phí thuê xe:** đề nghị đường `integrations/logistics/journal-entries` (12.12.4).
