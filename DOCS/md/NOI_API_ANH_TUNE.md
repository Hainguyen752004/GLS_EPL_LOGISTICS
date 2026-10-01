# Nối trang điều xe EPL Lào với hệ kế toán anh Tune — mình gọi gì, anh gọi gì, chứng từ đi đâu

Bản ngày **01/10/2026**, viết theo hiện trạng. Soạn từ mã đang chạy của trang điều xe (`EPL_LAO_REAL`), các lần gọi thử trên API của anh chạy ở máy và trên máy `demo-lao-api.goldensme.com`, và **source của anh**: API `GLS-QLSX-APIs` nhánh `feat/HonTunedaHai@ce95b3c`, WEB `GLS-QLSX-Web` nhánh `feat/hontunedhai_Laos@7e14421c` (mục 8).

- Tài liệu này là **bản đồ**: mỗi đường nói để làm gì, gửi gì, nhận gì, đang ở trạng thái nào.
- Từng trường chi tiết nằm ở **hợp đồng API kế toán** `HOP_DONG_API_KE_TOAN_ANH_TUNE`. Mỗi chỗ dưới đây ghi số mục để tra.
- Quy ước:
  - **LAO** = trang điều xe (bên em);
  - **hệ anh** = hệ kế toán của anh Tune (QLSX);
  - **KT tạm** = trang kế toán tạm `EPL_KETOAN` (cổng 8030). Từ 01/10 trang này **không còn phần tiền**, chỉ là **kho tạm** tới khi nối hệ kho anh Toàn.
- Không có token, mật khẩu nào trong tài liệu này.

**Ranh giới tiền (chủ dự án chốt 01/10/2026):**

- Mọi việc tiền chỉ ở hệ anh. Số tiền trên KT tạm là **số thử, bỏ hết**.
- **Cắt sổ 01/10:** mọi DO đã khoá gửi SO sang hệ anh **từ đầu**. Không còn luật chặn DO đã có hoá đơn / đã thu ở KT tạm (`DA_HOA_DON_TRANG_TAM` đã bỏ).
- **Khoản đi qua tiền** thành **phiếu chi / phiếu thu bên anh** (A4, A7 – A10). Thủ quỹ bên anh chi / thu và ghi sổ; LAO đọc lại.
- **Khoản không qua tiền** thành **bút toán chờ gửi** ở LAO, chờ API bút toán bên anh (mục 1.6).

---

## 0. Tóm tắt một trang

### 0.1. LAO gọi sang hệ anh

| # | Đường của anh | Để làm gì | Trạng thái 01/10 |
|---|---|---|---|
| A1 | `GET /api/v1/common/country-accounts?tryAutoId=11&onlyActive=true` | danh mục tài khoản Lào, cho ô chọn mã kế toán trên phiếu | **đang chạy**; API ở máy trả 497 mã (có 1371 / 4021 / 4022), host trả 494 |
| A2 | `POST /api/v1/integrations/logistics/sales-orders` | phiếu **đề nghị thu** → SO + công nợ khách bên anh | **chạy** qua API ở máy; mọi DO đã khoá gửi được; khách chưa có thì bên em tạo trước (A6) |
| A3 | các đường **chỉ đọc** ở mục 1.3 | lấy mã số: đơn vị, kỳ, loại chứng từ, tiền tệ… | đã đọc 30/09 và 01/10 |
| A4 | `POST /api/v1/accounting/cmpayment-receipt/save-and-commit` (CMP "Chi trước", DOTY 59) | **tạm ứng**: phiếu chi chờ; thủ quỹ bên anh chi và ghi sổ; LAO đọc `STATUS` 12/13 → mục IV đã chi | **chạy** (mục 1.4) |
| A5 | `POST /api/v1/sales/debt/customer-detail` | công nợ khách (chỉ xem); "thu một phần / đã thu" của từng SO theo `OrderCode` | **chạy** (mục 1.5) |
| A6 | `POST /api/v1/master-data/customers · suppliers · staff /list · /upsert` | đối tượng: khách `EPLKH-`, chủ xe `EPLCX-`, nhà cung cấp `EPLNCC-`, tài xế `EPLTX-` — tìm, chưa có thì tạo | **chạy** |
| A7 | `save-and-commit` (CMP "Chi khác", DOTY 60) | **trả chủ xe liên kết**: đứng tên chủ xe, Nợ 4022 | **chạy** |
| A8 | `save-and-commit` (CMP "Chi khác", DOTY 60) | **chi mục V – VI**: dòng quỹ trả ngay | **đang làm** |
| A9 | `save-and-commit` (CMP "Chi khác" 60 / CMR "Thu khác" 17) | **tất toán tài xế**: chi bù / thu hoàn, đứng tên tài xế | **đang làm** |
| A10 | `save-and-commit` (CMP "Chi khác", DOTY 60) | **trả nhà cung cấp**: Nợ 4021, đứng tên nhà cung cấp | **đang làm** |
| A11 | **chưa có đường** (đề nghị `POST /api/v1/integrations/logistics/journal-entries`) | **bút toán chờ gửi**: thuê xe 621/4022, ghi nợ nhà cung cấp, quyết toán tạm ứng | LAO giữ bút toán — **đang làm**; chờ API bên anh |
| — | `POST …/cmpayment-receipt/list` · `GET …/{id}` · `POST …/delete` | chống trùng, đọc trạng thái, rút phiếu chưa ghi sổ — dùng chung cho A4, A7 – A10 | **chạy** |

### 0.2. Hệ anh gọi sang LAO

| # | Đường của LAO | Để làm gì | Trạng thái 01/10 |
|---|---|---|---|
| B1 | `GET /api/handover/delivery-orders` | danh sách DO đã xong (đã về + đã khoá), đúng khuôn EPL_System; `q` tìm trên toàn bộ DO | **chạy**; màn Vụ việc của anh đọc qua `LogisticsSource` (`ce95b3c`), thử ở máy (cổng 8011) |
| B2 | `GET /api/handover/delivery-orders/{do_id}` | header + details một DO (dòng thu, các dòng chi mục III–VI kèm mã kế toán) | như trên |
| — | nhóm `/api/lien-thong/*` | **phần tiền đã gỡ 01/10** (hoá đơn, đã thu, trả chủ xe, tất toán, nhà cung cấp, cấn trừ, bán hàng). Còn phần kho cho KT tạm (kho tạm) | hệ anh **không cần gọi**: LAO tự hỏi lại trạng thái phiếu bên anh |

### 0.3. Chứng từ LAO sinh ra

Tờ chứng từ vẫn sinh ở LAO để in, xem và hiện định khoản. Từ 01/10 LAO **không đẩy tờ nào** đi đâu (đường phong bì `POST /api/v1/epl-lao/vouchers` đã thôi gửi). Tiền đi theo cột bên phải:

| Tờ | Sinh lúc | Sang hệ anh bằng | Trạng thái |
|---|---|---|---|
| `DO` phiếu xuất xe | Bãi lập phiếu | hệ anh **đọc** qua B1/B2 | chạy |
| `PTU` đề nghị tạm ứng | lập / in tờ tạm ứng | A4: phiếu chi "Chi trước" | chạy |
| `PC_TU` chi tạm ứng | **không sinh ở LAO nữa**: thủ quỹ chi ở hệ anh. Sếp chi tay trên LAO chỉ khi hệ anh không vào được | — | — |
| `PLNL` đề nghị xuất kho nhiên liệu | lập / in tờ xuất kho | **không sang anh Tune**: việc kho (kho tạm, sau là hệ anh Toàn) | — |
| `PC_SC` chi mục V – VI | KT Chi phí ghi sổ mục | A8: phiếu chi "Chi khác" | đang làm |
| `PDT` đề nghị thu | kế toán khoá phiếu | A2: SO + công nợ | chạy |
| `PC_CX` trả chủ xe | KT Thu/Chi lập đề nghị trả | A7: phiếu chi "Chi khác" | chạy |
| `QT_TU` quyết toán tạm ứng | KT Chi phí chốt tất toán | bút toán chờ (A11) | đang làm |
| `TT_CHI` · `TT_THU` chênh tất toán | như trên | A9 | đang làm |
| `PC_NCC` trả nhà cung cấp | KT Chi phí lập đề nghị trả | A10 | đang làm |
| ghi nợ nhà cung cấp (625 · 614 / 4021) · thuê xe (621/4022) | khoá phiếu | bút toán chờ (A11) | đang làm |
| `HD` hoá đơn · `PT` thu tiền khách | — | **việc của hệ anh**, từ SO (A2) | — |

### 0.4. Hệ anh cho LAO những gì

- **Đã có:**
  - token dùng chung (tài khoản cá nhân `tune`, **hết hạn 10/10/2026 09:05 giờ Lào**) cho tới khi có tài khoản tích hợp (mục 5);
  - hướng dẫn `sales-orders` (11/09), hướng dẫn thu chi `CM-CASH-VOUCHER-DEMOLAO-API-GUIDE.md`, tài liệu hiện trạng `GLS-QLSX-APIs/docs/PHIEU-THU-CHI-DEMOLAO-TONG-HOP.md`;
  - danh mục tài khoản quốc gia 11 (497 mã trên DB của API ở máy);
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
| Không nối được | dùng bản chụp ngày 01/10 (`services/danh_muc_tai_khoan_lao.json`, đã có 1371, 4021, 4022) |

Chi tiết: hợp đồng mục 1 và 3.3.

### 1.2. A2 — đề nghị thu → SO + công nợ

**Người bấm và chỗ bấm:**

1. Kế toán Viêng Chăn (vai `acct`) hoặc Sếp đăng nhập.
2. Menu **Phiếu đề nghị thu** → chọn **Tháng** → bấm một DO đã khoá ở danh sách bên trái.
3. Trên thanh nút của tờ, bấm **Tạo SO bên kế toán**.
4. Máy **xem trước** ở máy chủ, không gọi mạng. Thiếu gì thì hiện câu báo đỏ và **không gửi**. Khách chưa có mã bên anh thì hộp xem trước báo trước mã khách sẽ tạo (`EPLKH-<mã khách bên em>`).
5. Đủ điều kiện thì hiện hộp hỏi: *"Bên kế toán sẽ tạo SO và ghi công nợ khách … (mã …) số … USD"* → bấm **Tạo SO bên kế toán** trong hộp.
6. Thành công thì thanh nút hiện **Đã có SO SO-…**. Hỏng thì hiện **Lần gửi trước chưa được: …** kèm câu của hệ anh. Ở danh sách, DO có nhãn **SO** (xanh) hoặc **SO ⚠** (vàng).

**Máy chủ LAO gửi:**

```http
POST {gốc}/api/v1/integrations/logistics/sales-orders
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

Đây là gói thật của DO T4-0449-09/EPL, chỉ thay mã khách.

- **Gốc** lấy theo thứ tự: `QLSX_BASE_URL` nếu đặt; không thì giao thức + tên máy của `EPL_ACC_CODE_API`.
- **Token** lấy theo thứ tự: `QLSX_ACCESS_TOKEN` nếu đặt; không thì **tài khoản tích hợp** (`QLSX_USERNAME` / `QLSX_PASSWORD` / `QLSX_ORG_ID`, tự đăng nhập — hợp đồng 12.11.4); không thì `EPL_ACC_CODE_TOKEN`.

**Luật LAO kiểm trước khi gửi** (lỗi nào cũng báo rõ và không gửi):

| Luật | Mã lỗi bên LAO |
|---|---|
| DO đã về **và** đã khoá | `DO_CHUA_KHOA` |
| Phiếu có khách | `THIEU_KHACH` |
| Khách có **mã khách bên kế toán** sau bước tạo khách (A6) | `THIEU_MA_KHACH_KE_TOAN` |
| Mã khách: mở đầu bằng chữ Latinh hoặc số, chỉ chữ, số, `_ - .`, không có `/`, **≤ 37 ký tự** (đúng luật mã của anh; danh mục khách chặn ngay lúc gán) | `MA_KHACH_SAI` |
| Phiếu có tuyến; mã tuyến hợp lệ | `THIEU_TUYEN` · `MA_TUYEN_SAI` |
| `mã khách + "_" + mã tuyến` ≤ 50 ký tự (hệ anh dùng làm mã mặt hàng; mã tuyến 12 ký tự nên mã khách ≤ 37) | `MA_GHEP_QUA_DAI` |
| Số tiền gửi được chính xác (không bị làm tròn khi thành số JSON) | `TIEN_QUA_NHIEU_SO` |
| Tiền cước là VND, LAK hoặc USD | `TIEN_TE_CHUA_NHAN` (cước THB, CNY) |
| Cước > 0,01; `selling_price + phụ thu = final_selling_price = dòng thu` (Decimal, khớp chính xác) | `CUOC_BANG_KHONG` · `TIEN_SAI` |
| Người bấm là `acct` hoặc `admin` | 403 `KHONG_CO_QUYEN` |

Không còn luật chặn theo KT tạm: cắt sổ 01/10, mọi DO đã khoá gửi SO từ đầu.

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

**Sau khi có SO:**

- Kế toán LAO **không mở khoá** DO đó được (409 `DA_TAO_SO`). Chỉ Sếp mở, sau khi đã báo anh.
- Trạng thái thu của DO ("thu một phần", "đã thu") LAO **đọc lại** từ A5, ghép theo `OrderCode` của SO. LAO không ghi gì sang hệ anh.

**Mã DO.** `do_id` = `EPLLAO-<Trip.id>`. Hướng dẫn của anh nói `doId` là duy nhất **toàn bảng**, không chia theo nguồn. Tiền tố `EPLLAO-` giữ cho DO bên Lào không bao giờ trùng DO của EPL_System (`DO-2026-…`).

**Dữ liệu thử trên DB của API ở máy:** `TK-20261001-000162` (T4-0449-09/EPL, ຄຳຕຸ້ຍ, 905,85 USD) và `TK-20261001-000163` (T4-0442-09/EPL, ນາງ ວັນນາ, 1.676,90 USD). Đây là **SO thử, nhờ anh huỷ**. Huỷ xong, anh cho bên em biết cách gửi lại hai DO đó: khoá `logistics:EPLLAO-<Trip.id>` của chúng vẫn còn bên anh.

Chi tiết: hợp đồng mục 3.2, 3.2.1, 12.11.1.

### 1.3. A3 — các đường chỉ đọc đã gọi thử (không nằm trong mã chạy)

Gọi bằng token cấu hình trên **máy host**, ngày 30/09 – 01/10, **chỉ đường xem, danh sách, tìm**. Không gọi đường tạo, lưu, commit, ghi sổ, xoá nào.

| Đường | Đọc được |
|---|---|
| `GET /api/v1/ping` · `GET /api/v1/auth/info` · `GET /api/v1/auth/branches` | máy sống; người dùng `tune` (UserID 846, ObjectId 1503); chi nhánh được vào 1368 · 5 · 1369 |
| `GET /api/v1/common/GetCompanyAndBranch` | đơn vị 2, 1368, 5, 1369 — **đều quốc gia Việt Nam, tiền VND** |
| `GET /api/v1/common/GetFinancyCicle` | 22 kỳ tài chính; ID **không theo thứ tự tháng** (9/2026 = 20, 10/2026 = 19) |
| `GET /api/v1/common/GetAllCurrency` | **3 = VND, 26 = LAK**; USD có mã 2 nhưng đang tắt nên không trả; chưa có THB, CNY |
| `GET /api/v1/sales/debt/payment-methods` | 1 Tiền mặt · 3 Chuyển khoản · 6 Tiền mặt/Chuyển khoản; chưa có "cấn trừ" |
| `GET /api/v1/accounting/cmpayment-receipt/document-types?voucherType=ALL` | 14 Thu hoá đơn · 15 Thu công nợ · 16 Thu trước · 17 Thu khác · 57 Chi hoá đơn · 58 Chi công nợ · 59 Chi trước · 60 Chi khác · 68 Chuyển tiền nội bộ |
| `GET …/cmpayment-receipt/default-money-account?countryId=11&isCash=&isLocal=` (4 tổ hợp) | tiền mặt Kíp 1011 · tiền mặt ngoại tệ 1012 · ngân hàng Kíp 1021 · ngân hàng ngoại tệ 1022 |
| `GET /api/v1/accounting/lao-accounts` · `GET …/cmpayment-receipt/country-accounts?countryId=11` | host: 494 mã · 405 mã cho hạch toán, chưa có 1371, 4021, 4022. API ở máy (DB `appsettings.laos.json`): 497 mã, đã có ba mã (hợp đồng 12.12.1) |
| `GET /api/v1/accounting/cash-voucher-references?type=DO` | host: 23 DO, **đều là DO mẫu của EPL_System** (host chưa có code nhánh, còn trỏ 1506) |
| `POST /api/v1/master-data/customers/list` · `POST …/suppliers/list` | chi nhánh 1368 trên host: 189 khách, 517 nhà cung cấp, chưa có đối tượng EPL Lào |

Các đường kho (`supply-chain/*`, `report/inventory/*`, `items/search`) cũng có đọc ngày 30/09, nhưng **kho là hệ riêng của anh Toàn**, bên em không dùng máy này cho kho.

Số chi tiết: hợp đồng mục 12.7.

### 1.4. Phiếu chi / phiếu thu bên anh — A4, A7, A8, A9, A10

**Luật chung** (cùng một chỗ nói chuyện với hệ anh, `services/chi_tune.py`):

- Mỗi đề nghị bên em thành **một phiếu** bên anh, `PostMode = None` (chưa ghi sổ). **Thủ quỹ bên anh chi / thu tiền và ghi sổ** ở màn Phiếu chi / Phiếu thu.
- **Chống trùng** (API phiếu thu chi không có Idempotency-Key): trước mỗi lần tạo, bên em tìm qua `POST …/list` theo **đối tượng + `DOC_REFDOCUMENTNO` = số đề nghị bên em**. Có rồi thì dùng lại phiếu đó.
- **Đọc lại** `GET …/{id}?voucherType=CMP|CMR`: `Master.STATUS` 12 (ghi sổ chính) hoặc 13 (ghi sổ tạm) = đã chi / đã thu. Bên em hỏi lại lúc mở tờ, lúc cần quyết định (xe xuất phát…), và khi bấm Cập nhật.
- **Rút** phiếu chưa ghi sổ bằng `POST …/delete` khi số đổi hoặc bên em huỷ đề nghị. Phiếu đã ghi sổ thì bên em **không xoá, không sửa**; báo đối soát.
- Lỗi về dạng HTTP 200 kèm `Success: false` cũng được đọc ra; câu lỗi của anh hiện lên màn để người lập **Gửi lại**.
- Bên em gửi `Header.Amount` / `Header.BaseAmount` = tổng các dòng; từ `ce95b3c` hệ anh **tự tính lại tổng header từ `Entries`** (5 số lẻ, làm tròn nửa xa số 0).

| # | Đề nghị bên em | Phiếu bên anh | Đối tượng | Định khoản | Sau khi ghi sổ bên anh |
|---|---|---|---|---|---|
| A4 | tờ **PTU** (KT Chi phí VC ghi sổ mục IV) | CMP "Chi trước" (59, cấu hình `QLSX_DOTY_CHI_TAM_UNG`) | xe nhà: tài xế `EPLTX-`; xe thuê: chủ xe `EPLCX-` | xe nhà Nợ 1601 / Có 1011; xe thuê Nợ 4022 / Có 1011 | mục IV "đã chi", tờ PTU "đã cấp", tài xế **xuất phát được** |
| A7 | **đề nghị trả chủ xe** (màn Xe liên kết → *Trả qua kế toán*) | CMP "Chi khác" (60) | chủ xe `EPLCX-` | mỗi phiếu xe một dòng Nợ 4022 / Có 1011 · 1012 · 1021 · 1022 | các phiếu xe "đã trả chủ xe" |
| A8 | **chi mục V – VI** (KT Chi phí VC ghi sổ mục), chỉ dòng quỹ trả ngay | CMP "Chi khác" (60) | xe nhà: tài xế; xe thuê: chủ xe | xe nhà Nợ 614 (V) · 625 (VI) / Có 1011; xe thuê Nợ 4022 / Có 1011 | mục "đã chi" — **đang làm** |
| A9 | **chênh tất toán tài xế** (KT Chi phí VC chốt kỳ) | chi bù: CMP "Chi khác" (60); thu hoàn: CMR "Thu khác" (17) | tài xế `EPLTX-` | chi bù Nợ 1601 / Có tiền; thu hoàn Nợ tiền / Có 1601 | bản chốt "xong", 1601 của tài xế về 0 cho kỳ — **đang làm** |
| A10 | **đề nghị trả nhà cung cấp** (KT Chi phí) | CMP "Chi khác" (60) | nhà cung cấp `EPLNCC-` | Nợ 4021 / Có tiền | giảm nợ nhà cung cấp — **đang làm** |

Quỹ trên LAO **không chi mục IV nữa** (nút Chi, quét QR trả 409 `CHI_O_KE_TOAN`). Sếp chi tay được làm đường dự phòng khi hệ anh không vào được; khi đó bên em rút phiếu chi còn chờ bên anh trước. Đặt `EPL_CHI_TAM_UNG=tai_cho` thì quay về Quỹ chi trên LAO.

Chi tiết: hợp đồng mục 12.10 (A4), 12.11.3 (A7).

### 1.5. A5 — công nợ khách, đã thu của từng SO

- `POST /api/v1/sales/debt/customer-detail` với `{CustomerObjectId, OrgId}`, trả `Customer, Summary, Aging, Debts, Collections, Orders`.
- Màn Khách hàng → tab Công nợ có khối **"Công nợ bên hệ kế toán"**: tổng nợ, đã thu, quá hạn, tuổi nợ, từng SO còn nợ. **Chỉ xem**: thu tiền, hoá đơn làm ở hệ anh.
- Phiếu đề nghị thu đọc lại số đã thu theo `OrderCode` của SO: còn nợ ≤ nửa xu → "đã thu"; đã trả > 0 → "thu một phần". Một khách đọc tối đa một lần mỗi 60 giây.
- Công nợ khách **chỉ còn ở hệ anh**. Số hoá đơn / đã thu trên KT tạm là số thử.
- **Cần anh** một mẫu thân trả về thật (khối `Debts`, `Collections` là dynamic).

### 1.6. Bút toán chờ gửi — khoản không qua tiền (đang làm)

Khoản sổ phải ghi mà không đi qua tiền thì hệ anh **chưa có đường nhận** (source chưa có chứng từ bút toán tổng hợp, hợp đồng 12.12.4). Bên em không đoán cấu trúc sổ cái để ghi thẳng, nên **giữ bút toán ở LAO** (bảng `but_toan_cho`), đủ hai vế từng dòng bằng mã thật, chờ có API thì gửi.

| Nguồn | Sinh lúc | Định khoản |
|---|---|---|
| `thue_xe` | khoá phiếu xe thuê | Nợ 621 / Có 4022, bằng tiền thuê (`hire.amount`) |
| `no_ncc` | khoá phiếu có dòng ghi nợ nhà cung cấp | Nợ 625 · 614 (xe thuê 4022) / Có 4021 |
| `tat_toan` | chốt tất toán tài xế | quyết toán `QT_TU` Nợ 625 / Có 1601, bằng số tài xế đã chi thật |

- Khoá chống trùng (nguồn, mã nguồn). Mã gửi đi (`source_ref`): `EPLLAO-<nguồn>-<mã nguồn>`.
- Trạng thái: `cho_gui` (chờ API) · `da_gui` · `huy`. Mở khoá phiếu → bản chưa gửi bị huỷ; bản đã gửi đánh "cần đảo", chờ bút toán đảo.
- Có đường bên anh thì bên em gửi theo đề nghị `POST /api/v1/integrations/logistics/journal-entries` (+ `/reverse`), hợp đồng 12.12.4.

---

## 2. Hệ anh gọi sang LAO

### 2.1. Khoá bàn giao

- Mọi lời gọi B1, B2 mang `Authorization: Bearer <khoá bàn giao>`.
- Khoá **riêng cho hệ anh** (cấu hình `token_nhan_qlsx`), không dùng chung với khoá của KT tạm.
- **Sếp tạo khoá:** `POST /api/handover/tao-khoa` (chỉ vai `admin`). Khoá trả **đúng một lần**; tạo lại thì khoá cũ hết hiệu lực ngay. Hiện **chưa có nút** trên màn; em thêm nút ở màn Tài khoản khi có địa chỉ ra Internet.
- Sếp xem đã có khoá chưa: `GET /api/handover/trang-thai` → `{co_khoa, so_do_ban_giao_duoc, duong_danh_sach, duong_chi_tiet}`.
- Kế toán / Sếp xem đúng gói hệ anh sẽ nhận của một phiếu, không cần khoá: `GET /api/handover/xem-truoc/{trip_id}`.
- Lỗi:
  - 401 `SAI_TOKEN`: thiếu khoá hoặc khoá sai;
  - 503 `CHUA_DAT_TOKEN`: bên em chưa tạo khoá.

Phía anh (`ce95b3c`): địa chỉ và khoá nằm ở cấu hình `LogisticsSource:BaseUrl` / `ApiKey` (ghi đè theo `Branches:<BranchId>`). **Thiếu `BaseUrl` thì màn Vụ việc báo 503**, không còn tự trỏ EPL_System 1506. Logistics trả 401/403 → anh báo 502 "Logistics từ chối khoá truy cập".

### 2.2. B1 — danh sách DO đã xong

`GET /api/handover/delivery-orders?customer_id=&completed_from=YYYY-MM-DD&completed_to=YYYY-MM-DD&q=&page=1&page_size=50`

- Chỉ trả phiếu **đã về và đã khoá**, mới khoá trước. `total` là tổng thật sau lọc, kể cả lọc theo `q`.
- `q` (≤ 200 ký tự): tìm không phân biệt hoa thường trên `do_id`, `doc_no`, `customer_id`, `customer_name`, `truck_no`, `plate_head`. `data.q` trả lại đúng chữ đã lọc (`null` khi không lọc); hệ anh dựa vào đó để biết đã tìm trên toàn bộ DO (`SearchScope=ALL`). Dài hơn 200 → 422 `TU_KHOA_DAI`.
- Tham số `customer_id` nhận **mã khách bên anh** (`OBJ_OBJECTNO`) **hoặc** mã khách nội bộ bên em (12 ký tự hex).
- Trong mỗi dòng, `customer_id` = **mã khách bên anh** (null khi chưa gán), trùng `customer_id` gửi SO. Mã nội bộ bên em ở `customer_ref`.
- Mỗi dòng có **14 khoá của EPL_System**: `do_id`, `status`, `customer_id`, `quotation_id`, `route_id`, `vehicle_id`, `driver_id`, `selling_price`, `customer_surcharge_total`, `final_selling_price`, `currency`, `completed_at`, `completed_by`, `detail_url`.
- Thêm các khoá đọc bằng mắt: `doc_no`, `customer_code`, `customer_ref`, `customer_name`, `truck_no`, `plate_head`, `driver_name`, `company`, `owner_name`, `final_selling_price_lak`. Màn Vụ việc bên anh hiện số phiếu (`doc_no`), tên khách, "xe · biển số — tài xế".

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
          "total": 13, "page": 1, "page_size": 50, "q": null}}
```

### 2.3. B2 — một DO: header + details

`GET /api/handover/delivery-orders/{do_id}` → `{"message", "data": {"header": {...}, "details": [...]}}`

- `header`:
  - DO, ngày, xe hai biển, tài xế, khách (`customer_id` = mã bên anh, `customer_ref` = mã bên em), tuyến;
  - cân đầu / cân cuối, biên bản giao nhận (POD);
  - tiền cước theo tiền của phiếu, tỷ giá khoá trên phiếu;
  - tổng chi EPL chịu theo mục III–VI, lãi;
  - các khoá màn Vụ việc bên anh đọc: `trip_status`, `actual_cost_total`, `actual_cost_total_quy_doi`, `margin_amount`, `margin_percent`, `fx_rate`, `fx_rate_source`;
  - xe thuê có thêm khối `hire` (tiền thuê, phí 2 %, trừ quá tải, EPL đã ứng, còn phải trả chủ xe, `acc_code = "621/4022"`).
- `details`:
  - dòng 1 là **thu** (cước, `acc_code` 1211/708);
  - các dòng sau là **chi**, mỗi dòng có `section` (III–VI), số lượng, đơn giá, tiền của dòng, `amount_lak`, **`acc_code` Nợ/Có thật** trong danh mục Lào, `paid_by` (`epl` hay `chu_xe`);
  - mọi dòng có `calculation`, ví dụ `29.7 t × 30.5 USD`.
- Lỗi: 404 `DO_KHONG_THAY` · 409 `DO_CHUA_KHOA`.

Bảng từng khoá: hợp đồng mục 12.8.3.

### 2.4. Nhóm `/api/lien-thong/*`

- **Phần tiền đã gỡ 01/10**: các đường KT tạm từng gọi để báo "đã hoá đơn", "đã thu", "đã trả chủ xe", và đọc số cước, tiền thuê, tất toán, nợ nhà cung cấp, cấn trừ, bán hàng ở quầy (B2–B22 cũ của hợp đồng mục 4) **không còn**.
- Hệ anh **không cần gọi sang LAO** để báo trạng thái tiền: LAO tự hỏi lại phiếu bên anh (mục 1.4, 1.5).
- Phần **kho** của nhóm này còn giữ cho KT tạm (kho tạm), tới khi nối hệ anh Toàn. Hệ anh không dùng.

### 2.5. Địa chỉ ra Internet

B1, B2 chỉ gọi được từ host của anh khi trang điều xe Lào có địa chỉ ra Internet.

- **Chủ dự án chốt 01/10:** làm xong hết rồi mới host, lúc đó bên em gửi anh **địa chỉ gốc** và **khoá bàn giao**.
- Địa chỉ gửi anh phải là địa chỉ **cuối**, đúng `https://`: hệ anh tắt tự chuyển hướng.
- Anh đặt `LogisticsSource:BaseUrl` / `ApiKey` vào cấu hình host (không đưa lên git), rồi gọi thử `cash-voucher-references?type=DO`.

---

## 3. Một DO đi từng bước — ai bấm, sinh tờ gì, tiền đi đâu

| # | Bước | Ai bấm · ở đâu | Tờ | Tiền / sổ đi đâu |
|---|---|---|---|---|
| 1 | Lập phiếu xuất xe | Bãi · menu **Phiếu xuất xe** → lưu phiếu | `DO` | hệ anh **đọc** qua B1/B2 |
| 2 | Lập / in đề nghị tạm ứng (tiền mặt tài xế cầm đi) | Bãi hoặc kế toán · in tờ tạm ứng có QR | `PTU` | KT Chi phí VC ghi sổ mục IV → **A4** phiếu chi "Chi trước" |
| 3 | Lập / in đề nghị xuất kho nhiên liệu (mỗi kho một tờ) | Bãi hoặc kế toán · in tờ có QR | `PLNL` | kho (kho tạm, sau là hệ anh Toàn) — không sang anh Tune |
| 4 | Thủ quỹ chi tạm ứng | **Thủ quỹ bên anh** · ghi sổ phiếu "Chi trước" | — | LAO đọc `STATUS` 12/13 → tài xế xuất phát |
| 5 | Thủ kho cấp dầu theo đề nghị | Thủ kho · quét QR tờ xuất kho | `PXK_NL` (tờ kho) | kho |
| 6 | Chi mục V – VI trả ngay | KT Chi phí VC ghi sổ mục → thủ quỹ bên anh | `PC_SC` | **A8** — đang làm |
| 7 | Xe về, **khoá phiếu** | KT Thu/Chi Viêng Chăn · **Phiếu xuất xe** → **Khoá phiếu** | `PDT` | **A2 → SO + công nợ** (nút *Tạo SO bên kế toán*); xe thuê và dòng ghi nợ nhà cung cấp → **bút toán chờ** (mục 1.6) |
| 8–10 | Hoá đơn, thu tiền khách, cấn trừ | kế toán bên anh | `HD`, `PT` | **việc của hệ anh**, từ SO; LAO đọc "đã thu" qua A5 |
| 11 | Trả chủ xe liên kết | KT Thu/Chi lập đề nghị → thủ quỹ bên anh | `PC_CX` | **A7** |
| 12 | Tất toán tài xế theo tháng | KT Chi phí VC chốt → thủ quỹ bên anh | `QT_TU` + `TT_CHI` / `TT_THU` | quyết toán → bút toán chờ; chênh → **A9** — đang làm |
| 13 | Trả nhà cung cấp | KT Chi phí lập đề nghị → thủ quỹ bên anh | `PC_NCC` | **A10** — đang làm |

Bên em **chỉ gửi đề nghị** và đọc trạng thái về (chốt 29/09). Không có bước tiền nào chạy trên LAO hay KT tạm, trừ đường dự phòng Sếp chi tay tạm ứng.

---

## 4. Tờ chứng từ ở LAO

- Mỗi bước nghiệp vụ vẫn ghi một tờ vào bảng `chung_tu` của LAO, để in, xem và hiện định khoản ở màn Quy trình.
- **Không đẩy đi đâu nữa.** Đường `POST {ke_toan_api}/api/v1/epl-lao/vouchers` sang KT tạm đã thôi gửi từ 01/10; hệ anh không cần dựng cửa nhận phong bì. Các nút "Đẩy" còn giữ tên nhưng không gọi mạng; cờ "đã đẩy" chỉ còn đánh tay là "bên kế toán đã đối chiếu".
- Tiền đi theo phiếu chi / thu bên anh (mục 1.4), SO (A2), hoặc bút toán chờ (mục 1.6).

---

## 5. Hệ anh cho LAO: còn chờ

Xếp theo thứ tự cần trước:

1. **API bút toán** (không qua tiền) cho mọi bút toán chờ (mục 1.6). Đề nghị ở hợp đồng 12.12.4; hoặc anh gửi định nghĩa `sp_PostTing_GeneralLedger` và loại chứng từ cho bút toán khác để bên em viết.
2. **Huỷ hai SO thử** `TK-20261001-000162`, `…163`, và cho biết cách gửi lại hai DO đó.
3. **Tài khoản tích hợp** thay token cá nhân sắp hết hạn: tệp tạo đã sẵn (hợp đồng 12.12.3); anh thêm `UserId` vào `LogisticsSalesPush:AllowedUserIds` của host.
4. **Cờ phân loại** ở `document-types` (công nợ / khác / "Chi trước"), để WEB và API bỏ mã DOTY ghi cứng. Phiếu "Chi trước" (59) bên em tạo hiện không có trong ô chọn của WEB.
5. **Đơn vị EPL Lào** (quốc gia 11, tiền LAK). Hiện SO và phiếu vào chi nhánh cố định 1368 "Demo EPL". Thà Bốc và Viêng Chăn là một hay hai đơn vị?
6. **Tiền USD** (bật mã 2), **THB, CNY** trong danh mục tiền của CM, và SO nhận THB / CNY (hợp đồng câu hỏi 10.3).
7. **Mẫu `customer-detail` thật** cho màn công nợ (A5).
8. **Cấu hình host** khi triển khai: `LogisticsSource:BaseUrl` (bắt buộc), `ApiKey`, `LogisticsSalesPush:*` (TONG_HOP mục 4).

---

## 6. Việc tiếp theo

| Ai | Việc |
|---|---|
| **Anh Tune** | mục 5, từ việc 1; triển khai hai nhánh rồi đổi link theo hợp đồng 12.12.2 |
| **Bên em** | làm xong A8, A9, A10 và bút toán chờ; chạy lại vòng nối kế toán với `ce95b3c`; thêm nút tạo khoá bàn giao ở màn Tài khoản |
| **Chủ dự án** | chạy tệp tạo tài khoản tích hợp; host trang điều xe Lào ra Internet khi làm xong hết, rồi gửi anh Tune địa chỉ + khoá bàn giao |

---

## 7. Thử lại bằng tay (cho chủ dự án)

**Gửi SO một DO:**

1. Đăng nhập **ketoan** (KT Thu/Chi Viêng Chăn).
2. Menu **Phiếu đề nghị thu** → **Tháng** chọn tháng của DO → bấm một DO đã khoá.
3. Bấm **Tạo SO bên kế toán** → đọc hộp hỏi (khách, mã — có thể là mã sẽ tạo, số tiền) → bấm **Tạo SO bên kế toán**.
4. Thành công: thanh nút hiện **Đã có SO …**, danh sách có nhãn **SO**. Hỏng: hiện **Lần gửi trước chưa được: …** với câu của hệ anh.
5. Muốn gán mã khách bằng tay: menu **Khách hàng** → bấm khách → **Sửa** → ô **Mã khách (bên kế toán)** → **Lưu thay đổi**. Vai Bãi mở form này thì ô mã **khoá lại**.

**Xem đúng gói DO hệ anh sẽ đọc:** em chạy giúp `GET /api/handover/xem-truoc/<trip_id>` bằng tài khoản kế toán / Sếp. Mở thẳng đường này trên trình duyệt thì bị 401, vì trang giữ khoá đăng nhập trong máy chứ không dùng cookie.

**Bộ kiểm tự động** (máy thử):

- `kiem/thu_tao_so.py`: quyền, luật chặn, khuôn gói SO (không gọi sang hệ anh);
- `kiem/thu_tao_so_that.py`: gửi SO thật qua API chạy ở máy;
- `kiem/thu_luat_so_ben_tune.py`: luật kiểm của anh Tune chạy trên gói SO của mọi DO đã khoá (13/13 qua);
- `kiem/thu_ban_giao.py`: B1/B2, gồm các khoá màn Vụ việc đọc và `q`;
- `kiem/thu_khach_hang_moi.py`: mã khách, chỉ `acct` và admin gán, đúng luật mã bên anh;
- `kiem/thu_chi_tam_ung_ke_toan.py`, `kiem/thu_xe_thue_ke_toan.py`: A4, A7 qua API chạy ở máy;
- `kiem/thu_tat_toan_tune.py`: A9, A10 — đang làm.

---

## 8. Đối chiếu source của anh (`feat/HonTunedaHai@ce95b3c`, `feat/hontunedhai_Laos@7e14421c`)

Chủ dự án cho bên em sửa thẳng source của anh từ 01/10 (anh review). Các commit và việc còn lại ghi ở mục 16 tài liệu hiện trạng của anh và ở TONG_HOP mục 2.

### 8.1. Tạo SO (A2) — khớp

- Bên em chép đúng luật của `LogisticsPushValidator` và phần kiểm đầu của `sp_Logistics_CreateSalesOrder` thành bộ kiểm `kiem/thu_luat_so_ben_tune.py`. Chạy trên 13 DO đã khoá: **cả 13 qua**.
- **Dòng `chi`:** hệ anh chỉ ghép chúng thành chữ trên SO của khách, không thành bút toán → bên em **giữ một dòng thu**.
- **403 thân rỗng** = tài khoản token chưa nằm trong `LogisticsSalesPush.AllowedUserIds`, hoặc chưa gắn nhân viên. Bên em báo đúng lý do.
- **Chi nhánh 1368, người tạo 4, quốc gia 11 ghi cứng** trong thủ tục. Tạo đơn vị riêng cho EPL Lào thì thủ tục phải đổi theo.
- **Mã khách:** mở đầu bằng chữ / số, chỉ chữ, số, `_ . -`; ghép với mã tuyến ≤ 50 ký tự. Danh mục khách bên em chặn theo đúng luật đó (không `/`, tối đa 37 ký tự).

### 8.2. Nguồn DO cho phiếu thu chi (B1, B2)

- `CashVoucherReferenceController` chỉ còn HTTP / claims / envelope. Đọc, lọc, phân trang nằm ở `CashVoucherReferenceService`; gọi Logistics ở `LogisticsDeliveryOrderClient` (typed HttpClient: 15 giây, ≤ 2 MB, không chuyển hướng, không ghi header `Authorization` vào log).
- Cấu hình `LogisticsSource` (`BaseUrl`, `ApiKey`, ghi đè theo `Branches:<BranchId>`); mẫu khoá ở `Database/Scripts/logistics-source-config.example.json`. **Thiếu `BaseUrl` → 503.**
- DO: `SourceCode` = số phiếu `doc_no`, `SourceName` = tên khách; chi tiết DO phải `delivered` và đúng `do_id`, không thì 409.
- Gói bàn giao bên em một DO 4–7,4 KB, một trang 13 DO 11 KB, mỗi lời gọi dưới 0,4 giây — dưới giới hạn bên anh.

### 8.3. Phiếu thu chi (A4, A7 – A10)

- **Tổng header** do `CashVoucherHeaderTotals` tính ở create-session, save-session, save-and-commit: Σ `Entries` (5 số lẻ, nửa xa số 0); số client gửi bị thay. Phiếu có dòng IV/IC hay công nợ thiếu số tiền thì giữ số header client gửi (đường tương thích). Mọi phiếu bên em chỉ có `Entries`, nên luôn được tính lại.
- `ObjectService`: tạo đối tượng không gửi `IsOrganization` thì là cá nhân. Bên em vẫn luôn gửi ô này.
- WEB (`06a14189`, `7e14421c`): `isCash` theo hình thức thanh toán; tài khoản tiền mặc định đọc `AccountCode`; đổi hình thức / nội tệ / loại tiền khi đã có dòng thì vế tiền dòng đổi theo; phân loại công nợ / khác theo DOTY 58/60, 15/17 ghi cứng — loại 59 "Chi trước" không có trong ô chọn.

### 8.4. Hoá đơn điện tử

Dịch vụ `Backend.LaoInvoice` (01/10) **chưa nối SO hay DO**. Bên em không gọi.
