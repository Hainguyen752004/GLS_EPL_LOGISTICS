# Nối trang điều xe EPL Lào với hệ kế toán anh Tune — mình gọi gì, anh gọi gì, chứng từ đi đâu, source anh đổi gì

Bản ngày **01/10/2026**, viết theo hiện trạng. Soạn từ:

- mã đang chạy của trang điều xe `EPL_LAO_REAL@05fbc98` (gửi bút toán `gui_but_toan_tune.py`, `but_toan_cho.py` khớp giao ước API bút toán `b9227aa` ở `875a0cf`, xếp lỗi theo mã thật ở `3d4ba03` — mục 1.7; đọc lại "đã thu" `chi_tune._da_tra` ở `22dd4c8` — mục 1.5);
- kịch bản thử A→Z hai hệ `KICH_BAN_A_Z_EPL_TUNE` (KB-AZ, đã đi thật một chuyến THU-KBAZ ngày 01/10);
- các lần gọi thử trên API của anh chạy ở máy và trên máy `demo-lao-api.goldensme.com`;
- **source của anh**: API `GLS-QLSX-APIs` nhánh `feat/HonTunedaHai@b9227aa` (tách từ `31c98db`), WEB `GLS-QLSX-Web` nhánh `feat/hontunedhai_Laos@7d168744` (tách từ `de04913f`). Hai nhánh chưa push.
- kho tạm `EPL_KETOAN@1d8d91c`.

Mọi thay đổi bên em làm trên source của anh: **mục 8** (từng commit: tệp, đổi gì, DB đổi gì, nằm ở bước nào, thử lại thế nào). Dữ liệu bên em đã ghi vào DB demo của anh: **mục 9**. Chỗ chưa chắc ghi **đang chốt**.

**Người làm (chủ dự án chốt 01/10: "bên mình với anh Tune giờ là một"):** việc ghi "bên EPL làm" là bên EPL làm luôn, kể cả trên source của anh. Việc cần máy chủ host của anh (triển khai, dữ liệu trên DB host, token / mật khẩu tài khoản của anh) ghi **cần quyền host**.

**Token (chủ dự án chốt 01/10):** tạm gác tài khoản tích hợp; trang điều xe tiếp tục dùng token của anh (`EPL_ACC_CODE_TOKEN`). Hết hạn khoảng 10/10 thì thay token mới trong `.env`, hoặc đặt `QLSX_USERNAME` / `QLSX_PASSWORD` của anh để tự đăng nhập lại (đường này đã có sẵn). Mật khẩu tối đa 20 ký tự (`proc_LoginWithUsAndPw`, `VARCHAR(20)`); tài khoản phải được gán chi nhánh (`USERS_ORG`).

- Tài liệu này là **bản đồ**: mỗi đường nói để làm gì, gửi gì, nhận gì, bên anh ghi vào đâu, đang ở trạng thái nào.
- Từng trường chi tiết nằm ở **hợp đồng API kế toán** `HOP_DONG_API_KE_TOAN_ANH_TUNE`; hiện trạng phía anh ở `GLS-QLSX-APIs/docs/PHIEU-THU-CHI-DEMOLAO-TONG-HOP.md` mục 16.
- Quy ước:
  - **LAO** = trang điều xe (bên em);
  - **hệ anh** = hệ kế toán của anh Tune (QLSX: API + WEB);
  - **KT tạm** = trang kế toán tạm `EPL_KETOAN` (cổng 8030). Từ 01/10 trang này **không còn phần tiền**, chỉ là **kho tạm** tới khi nối hệ kho anh Toàn;
  - **API ở máy** = API của anh chạy trên máy em (`http://127.0.0.1:5090`, `Env=laos`), trỏ **DB demo Lào anh đã sao lưu sáng 01/10**. Mọi lần ghi dữ liệu đều qua API này; trên host chỉ gọi đường đọc.
- Không có token, mật khẩu, chuỗi kết nối nào trong tài liệu này.

**Ranh giới tiền (chủ dự án chốt 01/10/2026):**

- Mọi việc tiền chỉ ở hệ anh. Số tiền trên KT tạm là **số thử, bỏ hết**.
- **Cắt sổ 01/10:** mọi DO đã khoá gửi SO sang hệ anh **từ đầu**. Không còn luật chặn DO đã có hoá đơn / đã thu ở KT tạm (`DA_HOA_DON_TRANG_TAM` đã bỏ).
- **Khoản đi qua tiền** thành **phiếu chi / phiếu thu bên anh** (A4, A7 – A10). Thủ quỹ bên anh chi / thu và ghi sổ; LAO đọc lại.
- **Khoản không qua tiền** thành **bút toán chờ gửi** ở LAO (mục 1.6). Gửi sang hệ anh thành **chứng từ tổng hợp** qua API bút toán (A11, mục 1.7) — API đã viết, **chưa áp script DB**, cờ gửi bên em đang **tắt**.

---

## 0. Tóm tắt một trang

### 0.1. LAO gọi sang hệ anh

| # | Đường của anh | Để làm gì | Trạng thái 01/10 |
|---|---|---|---|
| A1 | `GET /api/v1/common/country-accounts?tryAutoId=11&onlyActive=true` | danh mục tài khoản Lào, cho ô chọn mã kế toán trên phiếu | **đang chạy**; API ở máy trả 497 mã (có 1371 / 4021 / 4022), host trả 494 |
| A2 | `POST /api/v1/integrations/logistics/sales-orders` | phiếu **đề nghị thu** → SO + công nợ khách bên anh | **chạy** qua API ở máy; mọi DO đã khoá gửi được; khách chưa có thì bên em tạo trước (A6) |
| A3 | các đường **chỉ đọc** ở mục 1.3 | lấy mã số: đơn vị, kỳ, loại chứng từ, tiền tệ… | đã đọc 30/09 và 01/10 |
| A4 | `POST /api/v1/accounting/cmpayment-receipt/save-and-commit` (CMP "Chi trước", DOTY 59) | **tạm ứng**: phiếu chi chờ; thủ quỹ bên anh chi và ghi sổ; LAO đọc `STATUS` 12/13 → mục IV đã chi | **chạy** (mục 1.4) |
| A5 | `POST /api/v1/sales/debt/customer-detail` | công nợ khách (chỉ xem); "thu một phần / đã thu" của từng SO theo `OrderCode`. Tiền thu thật làm ở màn **Chi tiết công nợ khách hàng** của anh (phiếu thu nợ TKN → phiếu thu CMR 17) | **chạy** (mục 1.5; KB-AZ đã thu thật hai SO) |
| A6 | `POST /api/v1/master-data/customers · suppliers · staff /list · /upsert` | đối tượng: khách `EPLKH-`, chủ xe `EPLCX-`, nhà cung cấp `EPLNCC-`, tài xế `EPLTX-` — tìm, chưa có thì tạo | **chạy** (cần `be123e9`) |
| A7 | `save-and-commit` (CMP "Chi khác", DOTY 60) | **trả chủ xe liên kết**: đứng tên chủ xe, Nợ 4022 | **chạy** |
| A8 | `save-and-commit` (CMP "Chi khác", DOTY 60) | **chi mục V – VI**: dòng quỹ trả ngay, định khoản theo tờ `PC_SC` | **chạy** ở máy |
| A9 | `save-and-commit` (CMP "Chi khác" 60 / CMR "Thu khác" 17) | **tất toán tài xế**: chi bù TT_CHI / thu hoàn TT_THU, đứng tên tài xế `EPLTX-` | **chạy** ở máy |
| A10 | `save-and-commit` (CMP "Chi khác", DOTY 60) | **trả nhà cung cấp**: Nợ 4021 / Có tiền, đứng tên nhà cung cấp `EPLNCC-` | **chạy** ở máy |
| A11 | `POST /api/v1/integrations/logistics/journal-entries` · `POST …/reverse` · `GET …/{SourceRef}` | **bút toán chờ gửi** (không qua tiền): thuê xe 621/4022, ghi nợ nhà cung cấp 625 · 614 / 4021, quyết toán tạm ứng 625/1601, hàng bán cho chủ xe 4022/707 → chứng từ tổng hợp DOTY 12, ghi sổ tạm (ST 13) bên anh | API **đã viết** (`b9227aa`), cấu hình đã có trên API ở máy, **chưa áp script DB** (gọi đang trả 503 `LOGISTICS_JOURNAL_SCRIPT_REQUIRED`); bên em gửi được (`875a0cf`) nhưng cờ `QLSX_GUI_BUT_TOAN` **tắt** → bút toán vẫn nằm ở LAO (mục 1.7) |
| — | `POST …/cmpayment-receipt/list` · `GET …/{id}` · `POST …/delete` | chống trùng, đọc trạng thái, rút phiếu chưa ghi sổ — dùng chung cho A4, A7 – A10 | **chạy** |

### 0.2. Hệ anh gọi sang LAO

| # | Đường của LAO | Để làm gì | Trạng thái 01/10 |
|---|---|---|---|
| B1 | `GET /api/handover/delivery-orders` | danh sách DO đã xong (đã về + đã khoá), đúng khuôn EPL_System; `q` tìm trên toàn bộ DO | **chạy**; màn Vụ việc của anh đọc qua `LogisticsSource` (`465748b`, `64ce7a4`, `ce95b3c`), thử ở máy (cổng 8011) |
| B2 | `GET /api/handover/delivery-orders/{do_id}` | header + details một DO (dòng thu, các dòng chi mục III–VI kèm mã kế toán) | như trên |
| — | nhóm `/api/lien-thong/*` | **phần tiền đã gỡ 01/10** (hoá đơn, đã thu, trả chủ xe, tất toán, nhà cung cấp, cấn trừ). Còn phần kho cho KT tạm (kho tạm), gồm `nguoi-mua` | hệ anh **không cần gọi**: LAO tự hỏi lại trạng thái phiếu bên anh |
| — | kho tạm `EPL_KETOAN`: `/api/lien-thong/ban-hang/cho-tru` · `tru` · `bo-tru` (LAO gọi kho tạm) | trừ hàng chủ xe mua ở quầy vào tiền trả chủ xe: giữ chỗ / chốt / thả phiếu bán | **chạy** (`1d8d91c`) |

### 0.3. Chứng từ LAO sinh ra

Tờ chứng từ vẫn sinh ở LAO để in, xem và hiện định khoản. Từ 01/10 LAO **không đẩy tờ nào** đi đâu (đường phong bì `POST /api/v1/epl-lao/vouchers` đã thôi gửi). Tiền đi theo cột bên phải:

| Tờ | Sinh lúc | Sang hệ anh bằng | Trạng thái |
|---|---|---|---|
| `DO` phiếu xuất xe | Bãi lập phiếu | hệ anh **đọc** qua B1/B2 | chạy |
| `PTU` đề nghị tạm ứng | lập / in tờ tạm ứng | A4: phiếu chi "Chi trước" | chạy |
| `PC_TU` chi tạm ứng | **không sinh ở LAO nữa**: thủ quỹ chi ở hệ anh. Sếp chi tay trên LAO chỉ khi hệ anh không vào được | — | — |
| `PLNL` đề nghị xuất kho nhiên liệu | lập / in tờ xuất kho | **không sang anh Tune**: việc kho (kho tạm, sau là hệ anh Toàn) | — |
| `PC_SC` chi mục V – VI | KT Chi phí ghi sổ mục | A8: phiếu chi "Chi khác" | chạy |
| `PDT` đề nghị thu | kế toán khoá phiếu | A2: SO + công nợ | chạy |
| `PC_CX` trả chủ xe | KT Thu/Chi lập đề nghị trả | A7: phiếu chi "Chi khác" | chạy |
| `QT_TU` quyết toán tạm ứng | KT Chi phí chốt tất toán | A11: bút toán nguồn `tat_toan` | giữ ở LAO (cờ tắt) |
| `TT_CHI` · `TT_THU` chênh tất toán | như trên | A9 | chạy |
| `PC_NCC` trả nhà cung cấp | KT Chi phí lập đề nghị trả | A10 | chạy |
| ghi nợ nhà cung cấp (625 · 614 / 4021) · thuê xe (621/4022) | khoá phiếu | A11: nguồn `no_ncc` · `thue_xe` | giữ ở LAO (cờ tắt) |
| hàng bán cho chủ xe (4022/707) | thủ quỹ bên anh đã chi phiếu trả chủ xe | A11: nguồn `ban_chu_xe` | giữ ở LAO (cờ tắt) |
| `PT` thu tiền khách | kế toán bên anh thu nợ SO | **việc của hệ anh**: **Chi tiết công nợ khách hàng → Tạo phiếu thu → Xác nhận thu nợ** → phiếu thu nợ **TKN** → hệ anh tự sinh phiếu thu **CMR 17 "Thu khác"** Nợ 1021 / Có 1211 (mục 1.5). **Không** thu bằng phiếu "Thu công nợ" CMR 15. LAO đọc "đã thu" qua A5 | chạy (KB-AZ) |
| `HD` hoá đơn | — | **việc của hệ anh**, từ SO (A2) | — |

### 0.4. Hệ anh cho LAO những gì

- **Đã có:**
  - token dùng chung (tài khoản cá nhân `tune`, **hết hạn 10/10/2026 09:05 giờ Lào**) — chủ dự án chốt tiếp tục dùng; hết hạn thì thay token hoặc tự đăng nhập bằng tài khoản anh (mục 5);
  - hướng dẫn `sales-orders` (11/09), hướng dẫn thu chi `CM-CASH-VOUCHER-DEMOLAO-API-GUIDE.md`, tài liệu hiện trạng `GLS-QLSX-APIs/docs/PHIEU-THU-CHI-DEMOLAO-TONG-HOP.md`;
  - danh mục tài khoản quốc gia 11 (497 mã trên DB của API ở máy);
  - các mã số đọc được ở mục 1.3.
- **Còn chờ:** mục 5.

### 0.5. Source của anh bên em đã đổi — một dòng mỗi commit

Chi tiết từng commit: mục 8. "DB" = có đổi thủ tục / bảng / dữ liệu trên DB của anh không.

| Repo | Commit | Đổi gì | DB | Nằm ở bước nào (mục 3) |
|---|---|---|---|---|
| API | `465748b` | nguồn DO của modal Vụ việc đọc cấu hình `LogisticsSource`, gửi khoá bàn giao; DO hiện số phiếu, tên khách | không | kế toán chọn Vụ việc DO trên phiếu thu / chi (B1/B2) |
| API | `be123e9` | đối tượng tạo qua API không gửi `IsOrganization` → cá nhân (hết 500) | không đổi cấu trúc; `PUBOBJECT.OBJ_ISORG` nhận 0 thay vì NULL | A6 — bước 2, 7, 11, 13 |
| API | `64ce7a4` | tìm DO theo từ khoá ở phía LAO (`q`), `Total` đúng sau lọc | không | B1 |
| API | `ce95b3c` | nguồn DO ra service + client typed, bỏ mặc định 1506; **máy chủ tính tổng header phiếu thu / chi** | không đổi thủ tục; giá trị `CMP_BASEAMOUNT` / `CMR_BASEAMOUNT` do máy chủ tính | B1/B2; A4, A7 – A10 |
| API | `ed5aa0e` | nhật ký kiểm toán: hết "Đặt log sai", che mật khẩu / token / khoá | dòng audit **mới** ghi `***` | mọi lời gọi |
| API | `ae0e7f6` | **máy chủ tính quy đổi từng dòng** trước khi cộng tổng header | giá trị `ET_BASEAMOUNT` do máy chủ tính | A4, A7 – A10 (trả chủ xe ngoại tệ) |
| API | `e2ef52f` | script che bí mật trong dòng audit **cũ** | script `UPDATE` dữ liệu audit — **chưa chạy** | triển khai |
| API | `0d4eed9` | che thêm trường `jwt` / `cookie` trong audit | như `ed5aa0e` | mọi lời gọi |
| API | `b9227aa` | **API bút toán tổng hợp** `integrations/logistics/journal-entries` | script tạo 3 thủ tục mới — **chưa áp** | A11 — bước 7, mở khoá, 11, 12 |
| WEB | `f382a9e8` | modal Vụ việc: thoát ký tự, hiện số phiếu / xe / tài xế, tỷ giá đọc xuôi | không | B1/B2 trên màn phiếu thu / chi |
| WEB | `06a14189` | phiếu thu / chi: `isCash` theo hình thức thanh toán, tài khoản tiền mặc định, tổng xem trước, phân loại theo DOTY | không | thủ quỹ mở / sửa phiếu (A4, A7 – A10) |
| WEB | `7e14421c` | đổi hình thức / nội tệ / loại tiền thì vế tiền các dòng đổi theo; đổi quốc gia chặn trước khi nạp | không | như trên |
| WEB | `77bcb0a1` | loại phiếu không đổi ngầm (59 "Chi trước" chỉ xem); chặn XSS modal Vụ việc | không | thủ quỹ mở phiếu tạm ứng (A4) |
| WEB | `fce78c52` | tiền tệ ngoài danh mục không gán ngầm; công nợ xem trước theo tỷ giá header; tab **Tài khoản** ở hồ sơ nhân viên | không tự ghi; tab chỉ ghi khi người dùng bấm Tạo / Lưu (`account/upsert` có sẵn) | phiếu thu / chi; tài khoản tích hợp (tuỳ chọn) |
| WEB | `7d168744` | che bí mật trong log WEB | không (log tệp) | mọi lời gọi qua WEB |

Chưa commit (chỉ máy em, không đưa lên): mục 8.3.

---

## 1. LAO gọi sang hệ anh

### 1.1. A1 — danh mục tài khoản

| | |
|---|---|
| Đường | `GET {EPL_ACC_CODE_API}?tryAutoId=11&onlyActive=true`. `EPL_ACC_CODE_API` là đường đầy đủ tới `…/api/v1/common/country-accounts` |
| Header | `Authorization: Bearer <EPL_ACC_CODE_TOKEN>` |
| Hết giờ · bộ nhớ | 20 giây · giữ 10 phút |
| LAO đọc | `Result[]`, các trường `AccCode`, `AccName`, `AccDescription`, `AccParentId`, `AccAccountWrite` (ghi sổ được), `AccIsActive` |
| LAO trả cho màn | `GET /api/acc-codes` → `{data: [...], source}` (`routes/acc_code.py`) |
| Dùng ở | ô chọn **Mã kế toán** trên từng dòng chi của phiếu, màn **Phiếu đề nghị chi** |
| Không nối được | dùng bản chụp ngày 01/10 (`services/danh_muc_tai_khoan_lao.json`, đã có 1371, 4021, 4022) |
| Mã thật bên em dùng | bảng định khoản một chỗ `services/tai_khoan.py`: 625 · 614 · 621 · 607 · 1371 · 4021 · 4022 · 1601 · 4201 · 1211 · 708 · 707 · tiền 1011 / 1012 / 1021 / 1022 |

Ba mã con 1371 / 4021 / 4022 bên em mở trên DB demo qua chính API của anh (mục 9.1). Chi tiết: hợp đồng mục 1 và 3.3.

### 1.2. A2 — đề nghị thu → SO + công nợ

**Người bấm và chỗ bấm:**

1. Kế toán Viêng Chăn (vai `acct`) hoặc Sếp đăng nhập.
2. Menu **Phiếu đề nghị thu** → chọn **Tháng** → bấm một DO đã khoá ở danh sách bên trái.
3. Trên thanh nút của tờ, bấm **Tạo SO bên kế toán**.
4. Máy **xem trước** ở máy chủ, không gọi mạng. Thiếu gì thì hiện câu báo đỏ và **không gửi**. Khách chưa có mã bên anh thì hộp xem trước báo trước mã khách sẽ tạo (`EPLKH-<mã khách bên em>`).
5. Đủ điều kiện thì hiện hộp hỏi: *"Bên kế toán sẽ tạo SO và ghi công nợ khách … (mã …) số … USD"* → bấm **Tạo SO bên kế toán** trong hộp.
6. Thành công thì thanh nút hiện **Đã có SO SO-…**. Hỏng thì hiện **Lần gửi trước chưa được: …** kèm câu của hệ anh. Ở danh sách, DO có nhãn **SO** (xanh) hoặc **SO ⚠** (vàng).

**Máy chủ LAO gửi** (`services/gui_tune.py`):

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
- **Token** lấy theo thứ tự: `QLSX_ACCESS_TOKEN` nếu đặt; không thì **tự đăng nhập** (`QLSX_USERNAME` / `QLSX_PASSWORD` / `QLSX_ORG_ID` — đặt được tài khoản của anh; hợp đồng 12.11.4); không thì `EPL_ACC_CODE_TOKEN` (đang dùng).

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

**Bên anh ghi gì vào DB** (thủ tục `sp_Logistics_CreateSalesOrder`, script `Database/Scripts/20260911_logistics_sales_push.sql` của anh — **bên em không sửa** thủ tục này), một DO trong một transaction:

| Bảng | Ghi gì |
|---|---|
| `PUBITEMS` · `PUBITEMOFGROUP` · `LogisticsPushItem` | mặt hàng `mã khách_mã tuyến` (nhóm Thành phẩm, ĐVT Cái) — lần đầu của cặp khách-tuyến thì tạo, lần sau dùng lại |
| `TicketOrder` · `TicketOrderDetail` | SO (`proc_TicketOrder_CreateManual`), `OrderSource = 'LOGISTICS'`, `OrderSourceNo = do_id`; trạng thái đi 1 → 8 → 10 → 5 |
| `RESTICKET` · `RESTICKET_EXTEND` · `RESTICKET_TABLE` · `RESTICKETITEM` | phiếu bán ghi nợ (`sp_RES_Create_RESTICKET`), tiền đúng tiền DO, tỷ giá 1 |
| `RESCUSTOMERSDEBT` | công nợ khách (`proc_TicketOrder_InvoiceDebt`), chưa thu |
| `LogisticsPushOrder` | khoá chống trùng: `DoId`, `RequestKey`, băm gói, kết quả |

Chi nhánh 1368, người tạo 4, quốc gia 11 ghi cứng trong thủ tục (mục 8.4).

**Sau khi có SO:**

- Kế toán LAO **không mở khoá** DO đó được (409 `DA_TAO_SO`). Chỉ Sếp mở, sau khi đã báo anh.
- Kế toán bên anh thu tiền khách ở màn **Chi tiết công nợ khách hàng** (phiếu thu nợ TKN → phiếu thu CMR 17, mục 1.5).
- Trạng thái thu của DO ("thu một phần", "đã thu") LAO **đọc lại** từ A5, ghép theo `OrderCode` của SO. LAO không ghi gì sang hệ anh.

**Mã DO.** `do_id` = `EPLLAO-<Trip.id>`. Hướng dẫn của anh nói `doId` là duy nhất **toàn bảng**, không chia theo nguồn. Tiền tố `EPLLAO-` giữ cho DO bên Lào không bao giờ trùng DO của EPL_System (`DO-2026-…`).

**SO đã tạo trên DB demo:** mục 9.3.

Chi tiết: hợp đồng mục 3.2, 3.2.1, 12.11.1.

### 1.3. A3 — các đường chỉ đọc đã gọi thử (không nằm trong mã chạy)

Gọi bằng token cấu hình trên **máy host**, ngày 30/09 – 01/10, **chỉ đường xem, danh sách, tìm**. Không gọi đường tạo, lưu, commit, ghi sổ, xoá nào trên host.

| Đường | Đọc được |
|---|---|
| `GET /api/v1/ping` · `GET /api/v1/auth/info` · `GET /api/v1/auth/branches` | máy sống; người dùng `tune` (UserID 846, ObjectId 1503); chi nhánh được vào 1368 · 5 · 1369 |
| `GET /api/v1/common/GetCompanyAndBranch` | đơn vị 2, 1368, 5, 1369 — **đều quốc gia Việt Nam, tiền VND** |
| `GET /api/v1/common/GetFinancyCicle` | 22 kỳ tài chính; ID **không theo thứ tự tháng** (9/2026 = 20, 10/2026 = 19) |
| `GET /api/v1/common/GetAllCurrency` | **3 = VND, 26 = LAK**; USD có mã 2 nhưng đang tắt nên không trả; chưa có THB, CNY |
| `GET /api/v1/sales/debt/payment-methods` | 1 Tiền mặt · 3 Chuyển khoản · 6 Tiền mặt/Chuyển khoản; chưa có "cấn trừ" |
| `GET /api/v1/accounting/cmpayment-receipt/document-types?voucherType=ALL` | 14 Thu hoá đơn · 15 Thu công nợ · 16 Thu trước · 17 Thu khác · 57 Chi hoá đơn · 58 Chi công nợ · 59 Chi trước · 60 Chi khác · 68 Chuyển tiền nội bộ |
| `GET …/cmpayment-receipt/default-money-account?countryId=11&isCash=&isLocal=` (4 tổ hợp) | tiền mặt Kíp 1011 · tiền mặt ngoại tệ 1012 · ngân hàng Kíp 1021 · ngân hàng ngoại tệ 1022 |
| `GET /api/v1/accounting/lao-accounts` · `GET …/cmpayment-receipt/country-accounts?countryId=11` | host: 494 mã · 405 mã cho hạch toán, chưa có 1371, 4021, 4022. API ở máy: 497 mã, đã có ba mã (mục 9.1) |
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
- Bên em gửi `Header.Amount` / `Header.BaseAmount` = tổng các dòng; hệ anh **tự tính lại quy đổi từng dòng** (`ae0e7f6`: `Amount × tỷ giá dòng`, thiếu thì tỷ giá header) và **tổng header** (`ce95b3c`), 5 số lẻ, làm tròn nửa xa số 0. Phiếu trả chủ xe ngoại tệ bên em gửi tỷ giá riêng từng dòng để Kíp khoá từng phiếu xe không bị dịch.
- Phiếu bên em tạo mà bị **xoá tay** bên anh (`Master` null) → bên em đánh `PHIEU_CHI_MAT`; người lập gửi lại thì lập phiếu mới, không gọi xoá nữa.
- Mã số đọc từ cấu hình bên em (`.env`, có mặc định): `QLSX_ORG_ID` 1368, `QLSX_COUNTRY_ID` 11, `QLSX_DOTY_CHI_TAM_UNG` 59, `QLSX_DOTY_TRA_CHU_XE` / `QLSX_DOTY_CHI_KHAC` 60, `QLSX_DOTY_THU_KHAC` 17; tiền tra `GetAllCurrency` (LAK 26), tiền đang tắt thì đặt tay `QLSX_TIEN_USD=2`; kỳ tra `GetFinancyCicle` theo ngày.

| # | Đề nghị bên em | Phiếu bên anh | Đối tượng | Định khoản | Sau khi ghi sổ bên anh |
|---|---|---|---|---|---|
| A4 | tờ **PTU** (KT Chi phí VC ghi sổ mục IV) | CMP "Chi trước" (59, cấu hình `QLSX_DOTY_CHI_TAM_UNG`) | xe nhà: tài xế `EPLTX-`; xe thuê: chủ xe `EPLCX-` | xe nhà Nợ 1601 / Có 1011; xe thuê Nợ 4022 / Có 1011 | mục IV "đã chi", tờ PTU "đã cấp", tài xế **xuất phát được** |
| A7 | **đề nghị trả chủ xe** (màn Xe liên kết → *Trả qua kế toán*) | CMP "Chi khác" (60) | chủ xe `EPLCX-` | mỗi phiếu xe một dòng Nợ 4022 / Có 1011 · 1012 · 1021 · 1022, số trả **đã trừ hàng chủ xe mua ở quầy** | các phiếu xe "đã trả chủ xe"; phiếu bán ở kho tạm chốt `TUNE:<số phiếu chi>`, ghi bút toán chờ 4022/707 |
| A8 | **chi mục V – VI** (KT Chi phí VC ghi sổ mục), chỉ dòng quỹ trả ngay | CMP "Chi khác" (60) | xe nhà: tài xế; xe thuê: chủ xe | theo tờ `PC_SC`: xe nhà Nợ 614 (V) · 625 (VI) / Có 1011; xe thuê Nợ 4022 / Có 1011 | mục "đã chi"; Quỹ trên trang điều xe không chi nữa |
| A9 | **chênh tất toán tài xế** (KT Chi phí VC chốt kỳ) | chi bù: CMP "Chi khác" (60); thu hoàn: CMR "Thu khác" (17) | tài xế `EPLTX-` | chi bù Nợ 1601 / Có tiền; thu hoàn Nợ tiền / Có 1601 | bản chốt "xong", 1601 của tài xế về 0 cho kỳ; quyết toán 625/1601 là bút toán chờ |
| A10 | **đề nghị trả nhà cung cấp** (KT Chi phí) | CMP "Chi khác" (60) | nhà cung cấp `EPLNCC-` | Nợ 4021 / Có tiền | giảm nợ nhà cung cấp (màn Nhà cung cấp → "Trả qua kế toán") |

**Bên anh ghi gì vào DB** (thủ tục có sẵn của anh, bên em không sửa thủ tục nào; chỉ đổi **giá trị** quy đổi / tổng do máy chủ tính — `ce95b3c`, `ae0e7f6`):

| Bước | Đường | Thủ tục / bảng |
|---|---|---|
| bên em tạo phiếu | `save-and-commit` | bảng tạm (`sp_Doc_Insert_documentTmp`, `sp_CM_InsertUpdate_CMPAYMENTtmp`, `SP_COMMON_TMPDATAPROCESS_PUBENTRY`) → chuyển thật `SP_CM_MOVETEMPTOREAL_CMPAYMENT` / `…_CMRECEIPT`: `PUBDOCUMENT` (`DOC_REFDOCUMENTNO` = số đề nghị bên em), `CMPAYMENT` / `CMRECEIPT`, `PUBENTRY` (dòng Nợ / Có, `ET_BASEAMOUNT` máy chủ tính) |
| thủ quỹ bên anh ghi sổ | màn Phiếu chi / Phiếu thu (hoặc `POST …/post`) | `sp_PostTing_GeneralLedger` → `STATUS` 12 / 13 |
| bên em rút phiếu chưa ghi sổ | `POST …/delete` | `SP_CMP_DELETECMP_CMPAYMENT` / `SP_CMR_DELETEMCMR_CMRECEIPT` |
| đối tượng chưa có | A6 `…/upsert` | `sp_Meta_Insert_Update_PUBOBJECT` → `PUBOBJECT` (mã `EPLKH-` / `EPLCX-` / `EPLNCC-` / `EPLTX-`) |

Quỹ trên LAO **không chi mục IV nữa** (nút Chi, quét QR trả 409 `CHI_O_KE_TOAN`). Sếp chi tay được làm đường dự phòng khi hệ anh không vào được; khi đó bên em rút phiếu chi còn chờ bên anh trước. Đặt `EPL_CHI_TAM_UNG=tai_cho` thì quay về Quỹ chi trên LAO.

**Trừ hàng quầy (A7):** phiếu bán cho chủ xe nằm ở kho tạm. Lập đề nghị trả → bên em gọi kho tạm `POST /api/lien-thong/ban-hang/tru` giữ chỗ (`TUNE-CHO:<số đề nghị>`); thủ quỹ bên anh đã chi → chốt (`TUNE:<số phiếu chi>`) và ghi bút toán chờ Nợ 4022 / Có 707; bỏ đề nghị → `POST …/bo-tru` thả phiếu bán. Danh sách chờ trừ: `GET /api/lien-thong/ban-hang/cho-tru?owner_id=`. Kho tạm tắt thì không lập được đề nghị trả (503).

Mã bên em: `services/chi_tune.py` (A4, A7, A6, A5), `services/chi_muc_tune.py` (A8), `services/chi_tat_toan_tune.py` (A9, A10), `services/tra_chu_xe.py` (số trả chủ xe, trừ hàng quầy). Chi tiết: hợp đồng mục 12.10 (A4), 12.11.3 (A7).

### 1.5. Thu tiền khách bên anh và A5 — đọc lại "đã thu" của từng SO

**Thu tiền khách — việc của hệ anh** (KB-AZ bước 21 đã đi thật; kiểm trong source):

1. QLSX WEB → **Danh sách công nợ** → chi nhánh 1368 → mở khách → màn **Chi tiết công nợ khách hàng** (`/DebtCollection/CustomerDetail?objAutoId=<ObjId>&orgId=1368`).
2. Bảng **Chi tiết hóa đơn theo tuổi nợ**: tick các dòng `TK-…` cần thu (cùng loại tiền) → **Tạo phiếu thu**.
3. Hộp **Tạo phiếu thu**: Quốc gia kế toán Lào, Tài khoản tiền thu, Phương thức thanh toán, Ghi chú; bảng Phân bổ tiền thu theo hóa đơn → **Xác nhận thu nợ**.
4. **Danh sách phiếu thu** (loại **Thu khác**) → **Ghi sổ** phiếu vừa sinh.

Máy làm: WEB `debtCollectionCustomerDetail.js` gửi `documentType: "TKN"` → BFF → API `POST /api/v1/sales/debt/collection-upsert` (`SalesService.DebtCollection`, chỉ nhận TKN tạo mới) → thủ tục `sp_RES_CreateDebtCollection_COUNTRY` (script `20260910_sales_debt_collection_country.sql` của anh, bên em không sửa). Mỗi SO một lần thu:

| Bảng bên anh | Ghi gì |
|---|---|
| `RESDOCUMENT` · `RESDOCUMENT_TICKET` | phiếu thu nợ **TKN** (số dạng `4-TKN-1368-2-261001-0001`) gắn phiếu bán của SO |
| `RESCUSTOMERSDEBT` | `RCTD_DEBTMONEY` trừ số thu; về 0 thì `RCTD_ISPAID = 1`. **`RESTICKET.RETK_MONEYPAID` không đổi (vẫn 0)** |
| `PUBDOCUMENT` · `CMRECEIPT` · `PUBENTRY` | phiếu thu CM **DOTY 17 "Thu khác"** (số dạng `4-1368-TK-261001-00009`), chưa ghi sổ, tham chiếu = số TKN; một dòng **Nợ tiền / Có 1211** — vế Nợ theo tài khoản tiền chọn (`CMACCOUNTCONFIGCOUNTRY`, Ngân hàng nội tệ = **1021**), vế Có theo vai `CUSTOMER_GOODS` = **1211** |

- Công nợ SO nằm ở phân hệ **Bán hàng**, nên **không thu bằng phiếu thu "Thu công nợ" (CMR 15)** ở màn Phiếu thu: tìm chứng từ công nợ của khách ở đó trả 0 dòng (KB-AZ đã thử).
- **Lỗi bên anh, đang sửa (bên EPL):**
  - hộp Tạo phiếu thu gửi **tỷ giá cứng 1** (`buildCollectionPayload`: `rate: 1`, `amount = amountCur`) và ô tài khoản tiền chỉ có nội tệ → SO **USD** ghi thành Kíp: phiếu thu 495 USD có quy đổi 495, vế tiền 1021 (ngân hàng Kíp);
  - **mọi SO cùng mã phiếu bán** `RETK_CODE = "Demo EPL-2-261001000"` (SO 162, 164, 165) → diễn giải phiếu thu *"Thu khách nợ từ phiếu Demo EPL-2-261001000"* giống hệt nhau, khó phân biệt.

**A5 — LAO đọc lại "đã thu":**

- `POST /api/v1/sales/debt/customer-detail` với `{CustomerObjectId, OrgId}`, trả `Customer, Summary, Aging, Debts, Collections, Orders` (`services/chi_tune.py` `cong_no_khach`).
- **Đã thu của một SO** = `services/chi_tune.py` `_da_tra`: `max(RETK_MONEYPAID, RETK_PAYMENTAMOUNT − RCTD_DEBTMONEY)`, tức **tiền − còn nợ**. Lý do: thu sau bằng TKN thì bên anh để `RETK_MONEYPAID = 0` (chỉ là tiền trả lúc chốt phiếu bán), chỉ `RCTD_DEBTMONEY` về 0; đọc thẳng `RETK_MONEYPAID` thì ra "Đã thu 0 · Còn lại 0", lệch `Summary.TotalCollected`. Thiếu số thì giữ số bên anh gửi.
- **Trạng thái DO** = `services/de_nghi_thu.py` `ap_thu`: lấy dòng nợ cùng `OrderCode` với SO → `thu_tong`, `thu_da_thu`, `thu_con_no`; còn nợ ≤ nửa xu → **"đã thu"**; đã thu > nửa xu → **"thu một phần"**; còn lại "chưa thu". SO không còn trong danh sách nợ mà còn trong `Orders` của khách → "đã thu" đủ. Không thấy ở cả hai → giữ "đã tạo SO".
- Đọc lúc bấm **Cập nhật** ở **Phiếu đề nghị thu** (`doc_thu_tune`, theo từng khách, một khách tối đa một lần mỗi 60 giây).
- Màn Khách hàng → tab Công nợ có khối **"Công nợ bên hệ kế toán"**: tổng nợ, đã thu, quá hạn, tuổi nợ, từng SO còn nợ. **Chỉ xem**.
- Công nợ khách **chỉ còn ở hệ anh**. Số hoá đơn / đã thu trên KT tạm là số thử.
- KB-AZ: hai SO 164, 165 thu đủ qua TKN → bên em hai DO **Đã thu đủ**, khối công nợ đã thu 1.248,35 USD (mục 9.5).

### 1.6. Bút toán chờ gửi — khoản không qua tiền, LAO giữ

Khoản sổ phải ghi mà không đi qua tiền, LAO giữ ở bảng `but_toan_cho` (`services/but_toan_cho.py`), đủ hai vế từng dòng bằng mã thật. Cờ gửi tắt thì chỉ nằm đây để xem; cờ bật thì ghi xong tự gửi sang hệ anh (A11, mục 1.7).

| Nguồn | Sinh lúc · ai bấm | Định khoản | Đối tượng dòng | Ngày hạch toán |
|---|---|---|---|---|
| `thue_xe` | **khoá phiếu** xe thuê — KT Thu/Chi VC (`acct`) hoặc Sếp, `POST /api/trips/{tid}/khoa` | Nợ 621 / Có 4022, bằng tiền thuê (`hire.amount`), tiền của tiền thuê | chủ xe `EPLCX-` | ngày khoá |
| `no_ncc` | **khoá phiếu** có dòng chi EPL chịu mà vế Có 4021 (dầu trạm ghi nợ, thẻ cao tốc, sửa ngoài cho nợ…) — như trên | Nợ 625 · 614 (xe thuê 4022) / Có 4021, quy Kíp theo tỷ giá khoá trên phiếu; bỏ dòng mục V quỹ trả ngay (đã đi A8) | nhà cung cấp `EPLNCC-` (dòng không có nhà cung cấp: xe thuê thì chủ xe, không thì trống) | ngày khoá |
| `tat_toan` | **chốt tất toán** tài xế — KT Chi phí VC (`expacct`) hoặc Sếp, `POST /api/tat-toan` | quyết toán `QT_TU` Nợ 625 / Có 1601, bằng số tài xế đã chi thật | tài xế `EPLTX-` | ngày cuối kỳ |
| `ban_chu_xe` | thủ quỹ bên anh **đã chi** phiếu trả chủ xe có trừ hàng quầy — LAO đọc `STATUS` 12/13 | Nợ 4022 / Có 707, theo giá bán; một phiếu bán một bút toán | chủ xe `EPLCX-` | ngày bán |

- Khoá chống trùng (nguồn, mã nguồn); mã nguồn: `thue_xe` / `no_ncc` = `Trip.id`; `tat_toan` = `<tài xế>:<kỳ>:<mã bản chốt>`; `ban_chu_xe` = mã phiếu bán kho tạm.
- **Mã gửi đi** `source_ref` = `EPLLAO-<nguồn>-<mã nguồn>`; bản đã đảo mà nguồn ghi lại (mở khoá rồi khoá lại) thì thêm `-2`, `-3`… (cột `phien`), không đụng chứng từ đã đảo.
- Trạng thái: `cho_gui` · `da_gui` (có số chứng từ bên anh) · `huy`; cờ `can_dao` = đã gửi mà nguồn bị huỷ, chờ gỡ bên anh.
- Nguồn bị huỷ:
  - mở khoá phiếu (`POST /api/trips/{tid}/mo-khoa`), xoá phiếu (`DELETE /api/trips/{tid}`) → huỷ `thue_xe`, `no_ncc` của phiếu;
  - bỏ chốt tất toán (`DELETE /api/tat-toan/{driver_id}`) → rút `tat_toan`;
  - bản chưa gửi → `huy` (lần gửi trước chưa rõ kết quả thì hỏi lại bên anh trước, mục 1.7.5); bản đã gửi → gửi gỡ (A11 reverse), chưa gỡ được thì `can_dao`.
- Khoá lại phiếu → ghi lại theo số mới: bản chưa gửi được cập nhật; bản đã gửi **đứng yên** (đổi số phải gỡ trước).
- Màn **"Bút toán chờ gửi"** (`GET /api/but-toan-cho`, vai KT Thu/Chi VC, KT Chi phí VC, Sếp): lọc trạng thái / nguồn / kỳ, chi tiết Nợ / Có, chứng từ gốc, số chứng từ bên anh, lỗi lần gửi gần nhất, số lần thử, xuất Excel. Cờ bật thì có thêm nút **Gửi hết** (`POST /api/but-toan-cho/gui-het`), **Gửi** / **Cập nhật** từng bản (`POST /api/but-toan-cho/{id}/gui | cap-nhat`); cờ tắt các nút này trả 409 `GUI_DANG_TAT`.

### 1.7. A11 — API bút toán tổng hợp bên anh (`b9227aa`)

#### 1.7.1. Trạng thái và việc cần để bật

| | Trạng thái 01/10 |
|---|---|
| API bên anh | **đã viết**, nhánh `feat/HonTunedaHai@b9227aa`; build 0 lỗi; 82 kiểm unit-level với repository giả; script parse cú pháp 0 lỗi |
| Script DB `Backend.API/Database/Scripts/20261001_logistics_journal_entry.sql` | **chưa áp vào DB nào**. Lần áp từ máy em bị bộ an toàn chặn; **chờ chủ dự án tự chạy** trên DB demo (DB của API ở máy) |
| Cấu hình API `LogisticsJournalEntry` | **API ở máy: đã có** trong `appsettings.laos.json` (`Enabled: true`, `AllowedUserIds: [846]`, `OrgId: 1368`, `CountryId: 11`). Host: chưa (**cần quyền host**) |
| Gọi thử lúc này | API ở máy: `GET …/journal-entries/{SourceRef}` trả **503 `LOGISTICS_JOURNAL_SCRIPT_REQUIRED`** — đúng, vì script chưa áp |
| Bên em gửi | `services/gui_but_toan_tune.py` (`a938301`, khớp giao ước ở `875a0cf`); cờ `QLSX_GUI_BUT_TOAN` trong `.env` máy chủ trang điều xe **đang tắt** (mặc định tắt) |

Bật theo thứ tự (bước 1 – 4 trên DB demo / API ở máy trước, host sau — **cần quyền host**). Trên API ở máy, bước 3 đã xong; còn bước 1, 2, 4, 5:

1. **Áp script** lên DB kế toán mà API trỏ tới. Script chỉ `CREATE OR ALTER` ba thủ tục `proc_Logistics_JournalEntry_Save` / `_Reverse` / `_Get`, **không đổi bảng, không ghi dữ liệu**, chạy lại được; thiếu nền (bảng, thủ tục legacy, mức tương thích ≥ 130) thì báo lỗi và không tạo thủ tục.
2. **Đọc phần chẩn đoán cuối script** (chỉ đọc):
   - D1 ba thủ tục đã tạo; D2 nền phụ thuộc đủ;
   - **D3** tên tham số thủ tục legacy: `sp_PostTing_GeneralLedger` (`@LstDocID`, `@ST_AUTOID`, `@Obj_POSTTING` — như repository phiếu thu chi đang gọi), `sp_GL_Delete_GENERALLEDGER` (`@doc_ParrentID`), `sp_GL_Delete_GLBusiness` (`@GLB_DOCUMENTID`), `spGetconfigID` (gọi theo vị trí: 6, OUTPUT số chứng từ);
   - **D4** cột `PUBENTRY.OBJ_AUTOID` có cho NULL không (không cho thì dòng nào thiếu đối tượng bị 422);
   - D5 kỳ theo ngày hôm nay; D6 `SourceRef` trùng (phải 0 dòng); D7 đếm chứng từ tổng hợp có `SourceRef` (so trước / sau khi thử).
3. **Thêm mục cấu hình** vào `appsettings.<Env>.json` của API (tệp không đưa lên git; mẫu `Database/Scripts/logistics-journal-entry-config.example.json`), đọc lại mỗi request, không cần khởi động lại API. API ở máy (`Env=laos`) đã có; host thêm lúc triển khai:

   ```json
   "LogisticsJournalEntry": { "Enabled": true, "AllowedUserIds": [846], "OrgId": 1368, "CountryId": 11 }
   ```

   `AllowedUserIds` là claim `UserId` (846 = tài khoản `tune` đang dùng), như `LogisticsSalesPush`. Đơn vị / quốc gia lấy từ đây, không lấy từ gói gửi.
4. **Gọi thử tay một vòng** (mục 7): tạo → GET → tạo lại (200 `IsExisting`) → reverse → reverse lần hai (`Reversed=false`); đối chiếu sổ cái, `ST_AUTOID` = 13.
5. **Bật cờ bên em** `QLSX_GUI_BUT_TOAN=1` trong `.env` máy chủ trang điều xe, khởi động lại trang. Bấm **Gửi hết** ở màn "Bút toán chờ gửi" để gửi các bản đang chờ.

#### 1.7.2. Luồng — một phiếu xe thuê

1. KT Thu/Chi VC bấm **Khoá phiếu** (bước 7, mục 3) → LAO ghi bút toán chờ `thue_xe` **Nợ 621 / Có 4022** = tiền thuê, đối tượng chủ xe; cùng lúc `no_ncc` nếu phiếu có dòng ghi nợ nhà cung cấp.
2. Cờ bật: LAO **gửi ngay** trong lần khoá (chờ tối đa 8 giây; hỏng thì bản giữ `cho_gui` kèm lỗi, việc khoá phiếu vẫn xong).
3. Bên anh tạo **một chứng từ tổng hợp** trong một transaction: `spGetconfigID 6` cấp số → `PUBDOCUMENT` (hệ 6, phân hệ 38, `DOC_REFDOCUMENTNO` = SourceRef) → `GLBUSINESS` (DOTY **12 Tổng hợp**, chưa khoá) → các dòng `PUBENTRY` → `sp_PostTing_GeneralLedger @id, 13` = **ghi sổ tạm (ST 13)**, như phiếu thu chi `PostedTemp`. Không tạo `CMPAYMENT` / `CMRECEIPT` (không qua tiền).
4. LAO nhận `DocumentId`, `DocumentNo`, `StatusId` → bản thành `da_gui`, màn hiện số chứng từ bên anh.
5. Kế toán bên anh xem, **ghi sổ chính thức** (ST 12) trong QLSX khi đã kiểm. Bấm **Cập nhật** ở LAO thì đọc lại `StatusId`.
6. Mở khoá phiếu (hoặc xoá phiếu) → LAO gửi **gỡ** (`reverse`): bên anh `sp_GL_Delete_GENERALLEDGER` → `sp_GL_Delete_GLBusiness`, hậu kiểm chứng từ không còn hoạt động, dòng `PUBENTRY` còn sót đặt `ET_ISACTIVE = 0`. Gỡ xong → bản LAO thành `huy`.
7. Khoá lại phiếu → bút toán mới với SourceRef `…-2`.
8. Bên anh **chặn gỡ** chứng từ đã khoá (`GLB_ISLOCK = 1`) hoặc đã ghi sổ chính thức (ST 12): 409 `LOGISTICS_JOURNAL_52515`. LAO giữ `can_dao` kèm câu lỗi; kế toán bên anh gỡ ghi sổ trong QLSX trước, rồi bấm **Gửi** lại ở LAO.

Ba nguồn còn lại đi cùng khuôn: `no_ncc` (cùng lần khoá), `tat_toan` (chốt / bỏ chốt tất toán), `ban_chu_xe` (lúc LAO thấy phiếu chi trả chủ xe đã ghi sổ).

#### 1.7.3. Gói LAO gửi

```http
POST {gốc}/api/v1/integrations/logistics/journal-entries
Authorization: Bearer <token>
Idempotency-Key: EPLLAO-thue_xe-<Trip.id>
Content-Type: application/json
```

```json
{"SourceRef": "EPLLAO-thue_xe-<Trip.id>", "DocumentDate": "2026-10-01", "CountryId": 11, "OrgId": 1368,
 "FiciAutoId": 19,
 "Description": "Ghi nhận chi phí thuê xe liên kết phiếu T4-…/EPL (<tên chủ xe>)",
 "Entries": [{"DebitAccount": "621", "CreditAccount": "4022", "Amount": 1250.5, "ExchangeRate": 21950.5,
              "CurrencyId": 2, "ObjectId": "<OBJ_AUTOID chủ xe EPLCX-…>", "Note": "Chi phí thuê xe liên kết T4-…/EPL · <tên chủ xe>"}]}
```

Số trong ví dụ là số minh hoạ. `SourceRef`, `CountryId`, `OrgId` trong thân bên anh **bỏ qua** (SourceRef lấy ở header; đơn vị / quốc gia lấy ở cấu hình) — bên em gửi kèm cho dễ đọc nhật ký.

| Luật bên anh | Bên em |
|---|---|
| `Idempotency-Key` 1–100 ký tự `A-Z a-z 0-9 _ . : -`, đầu là chữ / số | `EPLLAO-<nguồn>-<mã nguồn>[-<phiên>]` — đúng mẫu (mã tất toán có `:`) |
| `DocumentDate`, `Description` (≤ 400) bắt buộc | ngày hạch toán của bản; diễn giải cắt ≤ 250 |
| `FiciAutoId` tuỳ chọn, có gửi thì phải đúng kỳ của ngày (sai 422) | tra `GetFinancyCicle` theo ngày; kỳ đã đóng thì bên em báo `KY_DA_DONG`, không gửi; không tra được thì bỏ trống |
| 1–200 dòng; Nợ ≠ Có; `Amount` > 0 (≤ 5 số lẻ); `ExchangeRate` > 0 | mỗi dòng bút toán một dòng; LAK tỷ giá 1; ngoại tệ tỷ giá khoá trên phiếu |
| `CurrencyId` có trong `PUBCURRENCY` | `ma_tien`: LAK 26; USD 2 (đang tắt trên danh mục → `QLSX_TIEN_USD=2`) |
| `ObjectId` tuỳ chọn chỉ khi `PUBENTRY.OBJ_AUTOID` cho NULL (D4) | đối tượng của dòng, tạo qua A6 nếu chưa có; dòng không có đối tượng thì trống |
| mọi tài khoản phải có trong danh mục quốc gia (đang dùng + cho hạch toán) | mã thật từ `services/tai_khoan.py`; 137 / 402 là tổng hợp nên không dùng |
| `BaseAmount` máy chủ tính `Round(Amount × ExchangeRate, 5, AwayFromZero)` | không gửi |

#### 1.7.4. Ánh xạ trường: LAO → gói → bảng bên anh

| LAO (`but_toan_cho`) | Gói | Bên anh |
|---|---|---|
| `source_ref` | header `Idempotency-Key` | `PUBDOCUMENT.DOC_REFDOCUMENTNO` |
| `ngay` | `DocumentDate` | `PUBDOCUMENT.DOC_DOCUMENTDATE` |
| kỳ của `ngay` | `FiciAutoId` | `GLBUSINESS.FICI_AUTOID` (bỏ trống: `fn_ACC_GetFINANCYCICLEbyDate`) |
| `dien_giai` | `Description` | `PUBDOCUMENT.DOC_DESCRIPTION`, `GLBUSINESS.GLB_NOTE` |
| — (cấu hình `LogisticsJournalEntry`) | — | `PUBDOCUMENT.ORG_AUTOID` = `OrgId`, `TRY_AUTOID` = `CountryId` |
| — (token) | — | claim `ObjectId` → `DOC_CREATEBY`, `DOC_POSTTINGBY`, `GLBUSINESS.OBJ_AUTOID` |
| — | — | `DOC_DOCUMENTNO` (số `spGetconfigID 6`), `DOC_OFSYSTEM` 6, `DOC_OFSUBSYSTEM` 38, `GLBUSINESS.DOTY_AUTOID` 12, `GLB_ISLOCK` 0, `ST_AUTOID` 13 sau ghi sổ tạm |
| `dong[i].no` · `co` | `DebitAccount` · `CreditAccount` | `PUBENTRY.ET_DEBTORACCOUNT` · `ET_CREDITACCOUNT` |
| `dong[i].tien` | `Amount` | `ET_TOTALAMOUNT` |
| `dong[i].ty_gia` (LAK = 1) | `ExchangeRate` | `ET_EXCHANGERATE`; `ET_BASEAMOUNT` = máy chủ tính |
| `dong[i].ccy` | `CurrencyId` | `PUBENTRY.CUR_AUTOID` |
| `dong[i].doi_tuong` (hoặc `doi_tuong_no`) | `ObjectId` | `PUBENTRY.OBJ_AUTOID` |
| `dong[i].dien_giai` | `Note` | `ET_NOTE` |
| ← `ma_ben_ke_toan` · `so_ben_ke_toan` · `tune_status` | `Result.DocumentId` · `DocumentNo` · `StatusId` | `DOC_DOCUMENTID` · `DOC_DOCUMENTNO` · `GLBUSINESS.ST_AUTOID` |

#### 1.7.5. Bên anh trả → LAO làm

Lỗi bên anh trả trong phong bì `{Success:false, Code, Message, Result:null, ErrorDetail:{ErrorCode, InvalidAccounts?, Errors?, TraceId}}`. Bên em đọc mã lỗi ở **`ErrorDetail.ErrorCode`** và danh sách mã sai ở **`ErrorDetail.InvalidAccounts`** (`875a0cf`), kèm `Message` hiện lên màn. Xếp lỗi theo **mã thật** (`3d4ba03`): `ErrorDetail.ErrorCode` trước, rồi `Code` trong thân (lỗi về HTTP 200 kèm `Success:false`), rồi mã HTTP; chỉ đoán theo chữ của câu lỗi khi không có `ErrorCode`.

| Bên anh trả | LAO làm (mã lỗi bên em) |
|---|---|
| 201 tạo mới · 200 `IsExisting=true` (cùng SourceRef, cùng nội dung) | `da_gui`, lưu `DocumentId`, `DocumentNo`, `StatusId` |
| 400 `ErrorDetail.ErrorCode = INVALID_ACCOUNTS`, `ErrorDetail.InvalidAccounts = [...]` | giữ `cho_gui`, `TAI_KHOAN_SAI` kèm danh sách mã; mở mã / sửa định khoản rồi Gửi lại |
| 400 `INVALID_JOURNAL_ENTRY` · `LOGISTICS_JOURNAL_525xx` · 422 | giữ `cho_gui`, hiện câu của anh (`BEN_KE_TOAN_TU_CHOI`) |
| 409 `LOGISTICS_JOURNAL_52512` (cùng SourceRef, khác số — lần gửi trước bên anh đã lưu mà mất phản hồi, rồi số bên em đổi) | bên em **tự gỡ chứng từ cũ** (`reverse`) rồi **POST lại cùng SourceRef** với bản đúng (bên anh cho tạo lại sau khi gỡ); gỡ không được (chứng từ đã khoá / ghi sổ chính thức) thì giữ lỗi `KHAC_NOI_DUNG`, nhờ kế toán kiểm |
| 409 `LOGISTICS_JOURNAL_52511` | giữ lỗi, đối soát |
| 401 | bỏ token đang nhớ, lần sau đăng nhập lại (`QLSX_TOKEN_HET_HAN`) |
| 403 · `LOGISTICS_JOURNAL_FORBIDDEN` | `KHONG_DUOC_PHEP`: thêm `UserId` vào `AllowedUserIds`; Gửi hết dừng |
| 503 `LOGISTICS_JOURNAL_DISABLED` · `_CONFIG_REQUIRED` · `_SCRIPT_REQUIRED` (bên anh chưa bật / chưa áp script — **đang gặp lúc này**) | `BEN_DO_CHUA_BAT`: bản giữ `cho_gui`, Gửi hết dừng ngay; bật xong bấm Gửi hết |
| mất mạng · hết giờ · 5xx khác (`52510` đang xử lý, `_DATABASE_ERROR`), hoặc HTTP 200 kèm `Success:false`, `Code` 500 | kết quả **chưa rõ** (`KHONG_GOI_DUOC` / `HTTP_5XX`): lần sau **hỏi lại** `GET …/{SourceRef}` trước; bên anh có rồi thì nhận số đó, chưa có thì gửi lại cùng SourceRef |
| 404 ở POST | `KHONG_CO_DUONG`: API chưa có bản mới; Gửi hết dừng |
| GET 404 kèm `ErrorCode = JOURNAL_ENTRY_NOT_FOUND` | bên anh **chưa có** chứng từ → gửi. GET 404 không kèm mã đó = chưa có đường, không coi là "không có" |
| HTTP 200 kèm `Success:false`, `Code` 400 (JSON sai kiểu bị bộ lọc chung bắt) | coi là lỗi dữ liệu |

Gỡ (`POST …/reverse {SourceRef}`):

| Bên anh trả | LAO làm |
|---|---|
| 200 `Reversed=true` | bản thành `huy`, bỏ `can_dao` |
| 200 `Reversed=false` + `DocumentId=null` (bên anh không còn chứng từ đang hoạt động của SourceRef này — ví dụ lần gỡ trước đã xong mà mất phản hồi) | bên em coi như **đã gỡ** → `huy` (không kẹt "chờ đảo") |
| 409 `52515` (đã khoá / ghi sổ chính thức) · `52516` (thủ tục legacy không gỡ được, đã rollback) | giữ `can_dao` kèm câu lỗi; kế toán xử lý trong QLSX rồi Gửi lại |
| 404 | bên anh không trả 404 khi gỡ → 404 = **chưa có đường**, giữ `can_dao` (không coi là đã gỡ) |
| lỗi mạng / 5xx | giữ `can_dao`; Gửi hết thử lại |

**Mở khoá phiếu (hoặc bỏ chốt, xoá phiếu) khi lần gửi trước chưa rõ kết quả** (mất mạng hoặc 5xx, bản vẫn `cho_gui`): cờ bật thì bên em **hỏi lại bằng `GET …/{SourceRef}` trước**. Bên anh có chứng từ → bản thành đã gửi và đi **đường gỡ** như bản đã gửi; bên anh không có → bản thành `huy`. Không bỏ sót chứng từ nào bên anh. Không hỏi được (mất mạng) thì bản vẫn bị bỏ ở LAO, mã lỗi cũ giữ trên bản để đối soát.

#### 1.7.6. Chỗ còn phải để ý

- **Chưa chạy trên DB thật lần nào.** Mọi kiểm bên anh là unit-level với repository giả; bên em kiểm `kiem/thu_gui_but_toan.py` với máy giả trả đúng giao ước (201, ST 13, `ErrorDetail`, 409 `52512`, gỡ lần hai, mất phản hồi, xếp lỗi theo mã thật — 36/36). Lần chạy thật đầu tiên sau khi áp script: đối chiếu sổ cái, kỳ, số chứng từ.
- **D4**: nếu `PUBENTRY.OBJ_AUTOID` không cho NULL thì dòng `no_ncc` không có nhà cung cấp (và không phải xe thuê) bị 422 `52507` — phải gán nhà cung cấp trên dòng chi.
- Phí 2 % và trừ quá tải của xe thuê **chưa có bút toán riêng** (chờ anh Khampla chọn cách ghi); `thue_xe` chỉ mang tiền thuê.
- Bút toán bằng THB, CNY: danh mục tiền bên anh chưa có, LAO báo `THIEU_TIEN_TE`.

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

Phía anh (`465748b`, `ce95b3c`): địa chỉ và khoá nằm ở cấu hình `LogisticsSource:BaseUrl` / `ApiKey` (ghi đè theo `Branches:<BranchId>`; chi nhánh có `BaseUrl` riêng thì dùng cả khoá của chi nhánh, không gửi khoá chung sang máy khác). **Thiếu `BaseUrl` thì màn Vụ việc báo 503**, không còn tự trỏ EPL_System 1506. Logistics trả 401/403 → anh báo 502 "Logistics từ chối khoá truy cập". Header `Authorization` không ghi vào log.

### 2.2. B1 — danh sách DO đã xong

`GET /api/handover/delivery-orders?customer_id=&completed_from=YYYY-MM-DD&completed_to=YYYY-MM-DD&q=&page=1&page_size=50`

- Chỉ trả phiếu **đã về và đã khoá**, mới khoá trước. `total` là tổng thật sau lọc, kể cả lọc theo `q`.
- `q` (≤ 200 ký tự): tìm không phân biệt hoa thường trên `do_id`, `doc_no`, `customer_id`, `customer_name`, `truck_no`, `plate_head`. `data.q` trả lại đúng chữ đã lọc (`null` khi không lọc); hệ anh dựa vào đó để biết đã tìm trên toàn bộ DO (`SearchScope=ALL`, `64ce7a4`). Dài hơn 200 → 422 `TU_KHOA_DAI`.
- Tham số `customer_id` nhận **mã khách bên anh** (`OBJ_OBJECTNO`) **hoặc** mã khách nội bộ bên em (12 ký tự hex).
- Trong mỗi dòng, `customer_id` = **mã khách bên anh** (null khi chưa gán), trùng `customer_id` gửi SO. Mã nội bộ bên em ở `customer_ref`.
- Mỗi dòng có **14 khoá của EPL_System**: `do_id`, `status`, `customer_id`, `quotation_id`, `route_id`, `vehicle_id`, `driver_id`, `selling_price`, `customer_surcharge_total`, `final_selling_price`, `currency`, `completed_at`, `completed_by`, `detail_url`.
- Thêm các khoá đọc bằng mắt: `doc_no`, `customer_code`, `customer_ref`, `customer_name`, `truck_no`, `plate_head`, `driver_name`, `company`, `owner_name`, `final_selling_price_lak`. Màn Vụ việc bên anh hiện số phiếu (`doc_no`), tên khách, "xe · biển số — tài xế" (`f382a9e8`).

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
  - `invoiced` = DO đã có SO bên anh, `inv_no` = số SO;
  - xe thuê có thêm khối `hire` (tiền thuê, phí 2 %, trừ quá tải, EPL đã ứng, còn phải trả chủ xe, `acc_code = "621/4022"`).
- `details`:
  - dòng 1 là **thu** (cước, `acc_code` 1211/708);
  - các dòng sau là **chi**, mỗi dòng có `section` (III–VI), số lượng, đơn giá, tiền của dòng, `amount_lak`, **`acc_code` Nợ/Có thật** trong danh mục Lào, `paid_by` (`epl` hay `chu_xe`);
  - mọi dòng có `calculation`, ví dụ `29.7 t × 30.5 USD`.
- Lỗi: 404 `DO_KHONG_THAY` · 409 `DO_CHUA_KHOA`.

Bên anh: chọn DO trên phiếu thu / chi thì lưu bản chụp DO (`proc_PP_CashVoucherSourceReference_Save`, có sẵn từ 12/09) khi phiếu được lưu. Bảng từng khoá: hợp đồng mục 12.8.3.

### 2.4. Nhóm `/api/lien-thong/*`

- **Phần tiền đã gỡ 01/10**: các đường KT tạm từng gọi để báo "đã hoá đơn", "đã thu", "đã trả chủ xe", và đọc số cước, tiền thuê, tất toán, nợ nhà cung cấp, cấn trừ, bán hàng ở quầy (B2–B22 cũ của hợp đồng mục 4) **không còn**.
- Hệ anh **không cần gọi sang LAO** để báo trạng thái tiền: LAO tự hỏi lại phiếu bên anh (mục 1.4, 1.5, 1.7).
- Phần **kho** của nhóm này còn giữ cho KT tạm (kho tạm), tới khi nối hệ anh Toàn, gồm `nguoi-mua`. Hệ anh không dùng.
- Chiều ngược lại, LAO gọi kho tạm ba đường trừ hàng quầy `/api/lien-thong/ban-hang/cho-tru`, `/tru`, `/bo-tru` (mục 1.4).

### 2.5. Địa chỉ ra Internet

B1, B2 chỉ gọi được từ host của anh khi trang điều xe Lào có địa chỉ ra Internet.

- **Chủ dự án chốt 01/10:** làm xong hết rồi mới host, lúc đó bên em gửi anh **địa chỉ gốc** và **khoá bàn giao**.
- Địa chỉ gửi anh phải là địa chỉ **cuối**, đúng `https://`: hệ anh tắt tự chuyển hướng.
- Anh đặt `LogisticsSource:BaseUrl` / `ApiKey` vào cấu hình host (không đưa lên git), rồi gọi thử `cash-voucher-references?type=DO`.

---

## 3. Một DO đi từng bước — ai bấm, sinh tờ gì, bên anh ghi gì

| # | Bước | Ai bấm · ở đâu | Tờ LAO | Đường bên anh | Bên anh sinh ra |
|---|---|---|---|---|---|
| 1 | Lập phiếu xuất xe | Bãi · menu **Phiếu xuất xe** → lưu phiếu | `DO` | — (hệ anh **đọc** sau qua B1/B2) | — |
| 2 | Lập / in đề nghị tạm ứng (tiền mặt tài xế cầm đi) | Bãi hoặc kế toán · in tờ tạm ứng có QR; KT Chi phí VC ghi sổ mục IV | `PTU` | **A6** tài xế / chủ xe · **A4** `save-and-commit` | `PUBOBJECT` (nếu chưa có) · phiếu chi "Chi trước" 59 chưa ghi sổ (`PUBDOCUMENT`, `CMPAYMENT`, `PUBENTRY`) |
| 3 | Lập / in đề nghị xuất kho nhiên liệu (mỗi kho một tờ) | Bãi hoặc kế toán · in tờ có QR | `PLNL` | — (kho tạm, sau là hệ anh Toàn) | — |
| 4 | Thủ quỹ chi tạm ứng | **Thủ quỹ bên anh** · ghi sổ phiếu "Chi trước" | — | LAO đọc `GET …/{id}` | `sp_PostTing_GeneralLedger` → `STATUS` 12/13; LAO cho tài xế xuất phát |
| 5 | Thủ kho cấp dầu theo đề nghị | Thủ kho · quét QR tờ xuất kho | `PXK_NL` (tờ kho) | — | — |
| 6 | Chi mục V – VI trả ngay | KT Chi phí VC ghi sổ mục → thủ quỹ bên anh | `PC_SC` | **A8** | phiếu chi "Chi khác" 60 |
| 7 | Xe về, **khoá phiếu** | KT Thu/Chi Viêng Chăn · **Phiếu xuất xe** → **Khoá phiếu** | `PDT` | **A11** (cờ bật) — `thue_xe`, `no_ncc` | chứng từ tổng hợp DOTY 12, ghi sổ tạm ST 13 (cờ tắt: bút toán nằm ở LAO) |
| 7a | Gửi SO | KT Thu/Chi · **Phiếu đề nghị thu** → *Tạo SO bên kế toán* | `PDT` | **A6** khách · **A2** | `PUBOBJECT` khách `EPLKH-` · SO + phiếu bán + công nợ (mục 1.2) |
| 7b | Mở khoá phiếu (sửa số) | KT Thu/Chi (chưa có SO) hoặc Sếp | — | **A11 reverse** (bản đã gửi) | chứng từ tổng hợp bị gỡ; khoá lại → chứng từ mới `…-2` |
| 8 | Thu tiền khách | **kế toán bên anh** · **Chi tiết công nợ khách hàng** → **Tạo phiếu thu** → **Xác nhận thu nợ**, rồi ghi sổ phiếu thu; bên em KT Thu/Chi bấm **Cập nhật** ở **Phiếu đề nghị thu** | `PT` | `sales/debt/collection-upsert` (TKN, WEB của anh gọi) · LAO đọc **A5** | phiếu thu nợ TKN + công nợ giảm (`RESCUSTOMERSDEBT`) + phiếu thu **CMR 17 "Thu khác"** Nợ 1021 / Có 1211; LAO: DO "đã thu đủ" / "thu một phần" |
| 9–10 | Hoá đơn, cấn trừ | kế toán bên anh | `HD` | việc của hệ anh, từ SO | — |
| 11 | Trả chủ xe liên kết | KT Thu/Chi lập đề nghị → thủ quỹ bên anh ghi sổ | `PC_CX` | **A7**; ghi sổ xong → **A11** `ban_chu_xe` | phiếu chi "Chi khác" 60 · chứng từ tổng hợp 4022/707 |
| 12 | Tất toán tài xế theo tháng | KT Chi phí VC chốt → thủ quỹ bên anh | `QT_TU` + `TT_CHI` / `TT_THU` | quyết toán → **A11** `tat_toan`; chênh → **A9** | chứng từ tổng hợp 625/1601 · phiếu "Chi khác" 60 / "Thu khác" 17 |
| 13 | Trả nhà cung cấp | KT Chi phí lập đề nghị → thủ quỹ bên anh | `PC_NCC` | **A10** | phiếu chi "Chi khác" 60 |

Bên em **chỉ gửi đề nghị** và đọc trạng thái về (chốt 29/09). Không có bước tiền nào chạy trên LAO hay KT tạm, trừ đường dự phòng Sếp chi tay tạm ứng. Kế toán / thủ quỹ bên anh chọn **Vụ việc DO** (B1/B2) trên phiếu thu / chi của chính anh ở bất kỳ bước nào cần gắn chi phí vào DO.

---

## 4. Tờ chứng từ ở LAO

- Mỗi bước nghiệp vụ vẫn ghi một tờ vào bảng `chung_tu` của LAO, để in, xem và hiện định khoản ở màn Quy trình.
- **Không đẩy đi đâu nữa.** Đường `POST {ke_toan_api}/api/v1/epl-lao/vouchers` sang KT tạm đã thôi gửi từ 01/10; hệ anh không cần dựng cửa nhận phong bì. Các nút "Đẩy" còn giữ tên nhưng không gọi mạng; cờ "đã đẩy" chỉ còn đánh tay là "bên kế toán đã đối chiếu".
- Tiền đi theo phiếu chi / thu bên anh (mục 1.4), SO (A2), hoặc bút toán chờ → chứng từ tổng hợp (mục 1.6, 1.7).

---

## 5. Việc còn lại

| # | Việc | Người làm |
|---|---|---|
| 1 | **Bật API bút toán tổng hợp** (mục 1.7.1): áp script `20261001_logistics_journal_entry.sql` trên DB demo, đọc chẩn đoán D3 / D4, gọi thử một vòng, rồi bật `QLSX_GUI_BUT_TOAN` bên em. Cấu hình `LogisticsJournalEntry` trên API ở máy đã có | áp script: **chủ dự án tự chạy** (bộ an toàn chặn máy em); phần còn lại bên EPL làm |
| 2 | **Cờ phân loại** ở `document-types` (công nợ / khác / "Chi trước"), để WEB và API bỏ mã DOTY ghi cứng; phiếu 59 "Chi trước" trên WEB hiện chỉ xem | bên EPL làm (đang làm) |
| 3 | SO nhận cước **THB, CNY** (hợp đồng câu hỏi 10.3) | bên EPL làm (đang làm) |
| 4 | **Triển khai** hai nhánh lên host, cấu hình `LogisticsSource:BaseUrl` (bắt buộc), `ApiKey`, `LogisticsSalesPush:*`, `LogisticsJournalEntry:*` (TONG_HOP mục 4); áp script bút toán trên DB host; kho tạm có `1d8d91c` | **cần quyền host** |
| 5 | **Token hết hạn khoảng 10/10**: thay token mới trong `.env`, hoặc đặt `QLSX_USERNAME` / `QLSX_PASSWORD` của anh để tự đăng nhập lại (hợp đồng 12.11.4). Tài khoản tích hợp **tạm gác** — tuỳ chọn (hợp đồng 12.12.3; nhân viên ảo `EPL-TICHHOP` ObjId 1622 trên DB demo, chưa có tài khoản; tab Tài khoản ở hồ sơ nhân viên WEB đã có từ `fce78c52`, chưa bấm tạo thật) | **cần quyền host** (token / mật khẩu của anh) |
| 6 | **Dữ liệu DB host**: mở 1371 / 4021 / 4022 nếu thiếu (`tools/mo_ma_con_tune.py`); bật LAK / USD (mã 2); lỗi `default-money-account` trên host; đơn vị EPL Lào (quốc gia 11, tiền LAK — Thà Bốc và Viêng Chăn một hay hai đơn vị?) | **cần quyền host** |
| 7 | **Nhật ký kiểm toán cũ** có thể còn mật khẩu dạng chữ thường (trước `ed5aa0e`): chạy script `20261001_audit_redact_secrets.sql` (`e2ef52f`; `@Apply = 0` chẩn đoán trước), cân nhắc đổi mật khẩu các tài khoản đã đăng nhập qua API | **cần quyền host** (DB demo: chủ dự án) |
| 8 | Chạy lại vòng nối kế toán với bản cuối hai bên (API `b9227aa`, trang điều xe `191ab29`); KB-AZ đã đi thật một chuyến THU-KBAZ (mục 9) | bên EPL làm (đang làm) |
| 9 | **Hộp Tạo phiếu thu (WEB của anh) gửi tỷ giá cứng 1**, ô tài khoản tiền chỉ có nội tệ → SO USD ghi thành Kíp (mục 1.5) | bên EPL làm (**đang sửa**) |
| 10 | **Mọi SO cùng mã phiếu bán** `Demo EPL-2-261001000` → diễn giải phiếu thu nợ giống nhau (mục 1.5) | bên EPL làm (**đang sửa**) |

---

## 6. Việc tiếp theo

| Ai | Việc |
|---|---|
| **Chủ dự án** | áp script bút toán lên DB demo (mục 1.7.1 bước 1), gửi bên em kết quả chẩn đoán D3 / D4; chạy script che audit trên DB demo; host trang điều xe Lào ra Internet khi làm xong hết, rồi chuyển địa chỉ + khoá bàn giao vào cấu hình host |
| **Bên EPL** (đang làm) | mục 5 việc 1 (sau khi có script), 2, 3, 8, 9, 10; thêm nút tạo khoá bàn giao ở màn Tài khoản |
| **Cần quyền host** | mục 5 việc 4 – 7; triển khai xong thì đổi link theo hợp đồng 12.12.2 |
| **Anh Tune** | review từng commit ở mục 8; xem mục 9 (dữ liệu bên em đã ghi vào DB demo) |

---

## 7. Thử lại bằng tay (cho chủ dự án)

**Gửi SO một DO:**

1. Đăng nhập **ketoan** (KT Thu/Chi Viêng Chăn).
2. Menu **Phiếu đề nghị thu** → **Tháng** chọn tháng của DO → bấm một DO đã khoá.
3. Bấm **Tạo SO bên kế toán** → đọc hộp hỏi (khách, mã — có thể là mã sẽ tạo, số tiền) → bấm **Tạo SO bên kế toán**.
4. Thành công: thanh nút hiện **Đã có SO …**, danh sách có nhãn **SO**. Hỏng: hiện **Lần gửi trước chưa được: …** với câu của hệ anh.
5. Muốn gán mã khách bằng tay: menu **Khách hàng** → bấm khách → **Sửa** → ô **Mã khách (bên kế toán)** → **Lưu thay đổi**. Vai Bãi mở form này thì ô mã **khoá lại**.

**Thu tiền khách và đọc lại "đã thu":**

1. Bên anh (QLSX WEB): **Danh sách công nợ** → khách → **Chi tiết công nợ khách hàng** → tick dòng `TK-…` → **Tạo phiếu thu** → **Xác nhận thu nợ** → **Danh sách phiếu thu** loại **Thu khác** → **Ghi sổ**.
2. Bên em: **ketoan** → **Phiếu đề nghị thu** → **Cập nhật** → DO chuyển **Đã thu đủ** (thu thiếu: **Thu một phần**).
3. **Khách hàng** → khách → tab **Công nợ** → khối **Công nợ bên hệ kế toán**: đã thu đúng tổng các lần thu.

**Xem đúng gói DO hệ anh sẽ đọc:** em chạy giúp `GET /api/handover/xem-truoc/<trip_id>` bằng tài khoản kế toán / Sếp. Mở thẳng đường này trên trình duyệt thì bị 401, vì trang giữ khoá đăng nhập trong máy chứ không dùng cookie.

**Bút toán tổng hợp (sau khi đã áp script — mục 1.7.1 bước 1 – 2; cấu hình bước 3 đã có trên API ở máy; máy thử 8011 nối API ở máy):**

1. Đặt `QLSX_GUI_BUT_TOAN=1` trong `.env` máy thử, khởi động lại trang điều xe máy thử.
2. Đăng nhập **ketoan** → **Phiếu xuất xe** → mở một phiếu **xe thuê** đã về → **Khoá phiếu**.
3. Menu **Bút toán chờ gửi** → lọc nguồn **thuê xe**: bản của phiếu đó **đã gửi**, có số chứng từ bên kế toán. Lỗi thì dòng hiện câu lỗi và số lần thử → sửa rồi bấm **Gửi**.
4. Bấm **Cập nhật** trên dòng: trạng thái bên kế toán = 13 (ghi sổ tạm).
5. Quay lại phiếu → **Mở khoá phiếu** → màn Bút toán chờ gửi: bản đó **huỷ** (đã gỡ bên kế toán). Khoá lại → bản mới, mã nguồn đuôi `-2`.
6. Bản nào kẹt **chờ đảo** (kế toán đã ghi sổ chính thức): kế toán gỡ ghi sổ trong QLSX → bấm **Gửi** trên dòng đó.

**Bộ kiểm tự động** (máy thử):

- `kiem/thu_tao_so.py`: quyền, luật chặn, khuôn gói SO (không gọi sang hệ anh);
- `kiem/thu_tao_so_that.py`: gửi SO thật qua API chạy ở máy;
- `kiem/thu_luat_so_ben_tune.py`: luật kiểm của anh Tune chạy trên gói SO của mọi DO đã khoá (13/13 qua);
- `kiem/thu_ban_giao.py`: B1/B2, gồm các khoá màn Vụ việc đọc và `q`;
- `kiem/thu_khach_hang_moi.py`: mã khách, chỉ `acct` và admin gán, đúng luật mã bên anh;
- `kiem/thu_chi_tam_ung_ke_toan.py`, `kiem/thu_xe_thue_ke_toan.py`, `kiem/thu_chu_xe.py`, `kiem/thu_tru_hang_quay.py`: A4, A7 (gồm trừ hàng quầy) qua API chạy ở máy;
- `kiem/thu_chi_muc_tune.py`: A8; `kiem/thu_tat_toan_tune.py`: A9, A10; `kiem/thu_but_toan_cho.py`: bút toán chờ (cờ tắt);
- `kiem/thu_gui_but_toan.py`: gửi / gỡ / hỏi lại bút toán với **máy giả** theo giao ước `b9227aa` (không gọi API thật);
- `kiem/thu_giao_dien.js`: 22 màn, gồm màn Tất toán tài xế, Nhà cung cấp, Bút toán chờ gửi;
- kho tạm `EPL_KETOAN/kiem/thu_tru_hang_chu_xe.py` (máy thử 8031): ba đường trừ hàng quầy.

Các bài nối thật đạt trên máy thử 8011 ↔ API ở máy với `f85078b`, `938b007` (bộ sau cắt sổ `8bf84f9`: 47/48). Chạy lại với API `b9227aa`: mục 5 việc 8.

---

## 8. Đối chiếu source của anh — từng commit (`feat/HonTunedaHai@b9227aa`, `feat/hontunedhai_Laos@7d168744`)

Chủ dự án cho bên em sửa thẳng source của anh từ 01/10 (anh review). Mọi commit bên em đánh dấu `Created by / Modified by: EPL Logistics` trong tệp. Xem toàn bộ: `git log --oneline 31c98db..feat/HonTunedaHai` (API), `git log --oneline de04913f..feat/hontunedhai_Laos` (WEB). Mỗi khối dưới đây: tệp · đổi gì · DB · nằm ở bước nào (mục 3) · đã kiểm · thử lại.

### 8.1. API `GLS-QLSX-APIs` — 9 commit

#### 8.1.1. `465748b` — nguồn DO đọc cấu hình, gửi khoá; DO hiện số phiếu / tên khách

| | |
|---|---|
| Tệp | `Modules/Finance/Accounting/Api/V1/CashVoucherReferenceController.cs`; mẫu `Database/Scripts/logistics-source-config.example.json` |
| Đổi gì | bỏ địa chỉ ghi cứng `senvangsolutions.com:1506`; đọc `LogisticsSource` (`BaseUrl`, `ApiKey`, `Branches:<BranchId>`), gửi `Authorization: Bearer <khoá bàn giao>`; lỗi nói rõ: khoá sai 401/403 → 502, DO không có → 404, DO chưa khoá → 409; DO: `SourceCode` = `doc_no`, `SourceName` = `customer_name` (không có thì `do_id` / `customer_id`); tìm theo số phiếu, tên khách, số xe |
| DB | không |
| Bước | B1/B2 — kế toán / thủ quỹ bên anh chọn Vụ việc DO trên phiếu thu / chi |
| Đã kiểm | API ở máy đọc 13 DO trang điều xe bản thử, chi tiết có `SelectionToken`; khoá sai → 502; DO không có → 404 |
| Thử lại | `GET /api/v1/accounting/cash-voucher-references?type=DO` khi cấu hình trỏ trang điều xe máy thử |

#### 8.1.2. `be123e9` — đối tượng không gửi `IsOrganization` mặc định cá nhân

| | |
|---|---|
| Tệp | `Modules/Shared/ObjectManagement/Application/ObjectService.cs` (`ApplyDomainDefaults`: `IsOrganization ??= false`) |
| Đổi gì | trước đây `master-data/customers · suppliers /upsert` không gửi `IsOrganization` thì `INSERT PUBOBJECT` văng "Cannot insert NULL into OBJ_ISORG" → 500 |
| DB | không đổi cấu trúc; `PUBOBJECT.OBJ_ISORG` = 0 khi không gửi (`sp_Meta_Insert_Update_PUBOBJECT`) |
| Bước | A6 — bước 2 (tài xế / chủ xe), 7a (khách), 11 (chủ xe), 13 (nhà cung cấp) |
| Đã kiểm | gặp khi trang điều xe tạo khách cho SO ngày 01/10 (lỗi 500); sau sửa bên em tạo được khách / chủ xe / nhà cung cấp qua API ở máy (mục 9.2) |
| Thử lại | `POST /api/v1/master-data/customers/upsert` không có `IsOrganization` → 200 |

#### 8.1.3. `64ce7a4` — tìm DO theo `q` ở phía Logistics

| | |
|---|---|
| Tệp | `CashVoucherReferenceController.cs` (sau `ce95b3c` nằm ở `CashVoucherReferenceService`) |
| Đổi gì | có từ khoá thì gửi `q` cùng `page` / `page_size`; nguồn trả lại `data.q` khớp thì dùng thẳng, `HasMore` theo `Total`, `SearchScope=ALL`; nguồn chưa biết `q` (EPL_System 1506) thì lọc trong trang như cũ |
| DB | không |
| Bước | B1 — ô tìm của modal Vụ việc |
| Đã kiểm | 13 DO: "341" → 3 dòng, Total 3; "T4" cỡ trang 3 → 3 + 3 + 3 + 1, Total 10, trang cuối `HasMore=false`; 201 ký tự → 400 |
| Thử lại | `…cash-voucher-references?type=DO&keyword=341` |

#### 8.1.4. `ce95b3c` — theo chuẩn QLSX: service + client typed; máy chủ tính tổng header phiếu thu / chi

| | |
|---|---|
| Tệp | mới: `Application/CashVoucherReferenceService.cs`, `ICashVoucherReferenceService.cs`, `Application/CashVoucherHeaderTotals.cs`, `Infrastructure/LogisticsDeliveryOrderClient.cs`, `ILogisticsDeliveryOrderClient.cs`, `Contracts/V1/CashVoucherSourceReferenceModels.cs`; sửa: `CashVoucherReferenceController.cs` (chỉ còn HTTP / claims / envelope), `CMPaymentReceiptService.cs` (`ApplyServerHeaderTotals` ở create-session, save-session, save-and-commit), `CashVoucherReferenceTicket.cs` (`LifetimeSeconds` 7200), `CashVoucherModels.cs` (chú thích), `AccountingModule.cs` (đăng ký service + typed HttpClient 15 giây, ≤ 2 MB, không chuyển hướng, che header `Authorization` trong log) |
| Đổi gì | thiếu `LogisticsSource:BaseUrl` → **503** (bỏ mặc định ngầm 1506); `Header.Amount` / `Header.BaseAmount` = Σ dòng, 5 số lẻ, nửa xa số 0 — số trình duyệt gửi bị thay; dòng IV/IC hay công nợ thiếu số tiền thì giữ số header client gửi (đường tương thích) |
| DB | không đổi thủ tục; giá trị xuống `CMP_BASEAMOUNT` / `CMR_BASEAMOUNT` qua thủ tục header tạm là số máy chủ tính |
| Bước | B1/B2; A4, A7 – A10 (bước 2, 6, 11, 12, 13) và mọi phiếu WEB tạo |
| Đã kiểm | build 0 lỗi; 15 GET chỉ đọc so bản cũ: 14 giống từng byte, 1 khác `SelectionToken` / thời điểm chụp; tổng header 15/15 unit-level (header xuống `SaveHeaderTmpAsync` là Σ dòng dù client gửi 999999) |
| Thử lại | bỏ cấu hình `LogisticsSource` → DO trả 503, DEAL / QUOTE vẫn chạy; tạo phiếu chi với `Header.BaseAmount` sai → phiếu lưu Σ dòng |

#### 8.1.5. `ed5aa0e` — nhật ký kiểm toán: hết "Đặt log sai", che bí mật

| | |
|---|---|
| Tệp | `Modules/Platform/AuditLog/Filters/ApiAuditAutoLogFilter.cs` (bỏ tham số `CancellationToken` khỏi payload; query string qua `RedactQuery`), `Application/ApiAuditLogger.cs` (lỗi serialize ghi `ILogger` kèm exception), mới `Application/ApiAuditPayloadSanitizer.cs` |
| Đổi gì | 16 controller có `CancellationToken` từng mất payload ("Đặt log sai"); che theo tên trường mọi cấp: kết thúc `token` / `pwd`, chứa `password`, `passwd`, `secret`, `apikey`, `connectionstring`, `authorization`, `credential` → `***` |
| DB | không đổi cấu trúc; dòng audit **từ commit này** (bảng mà `proc_PP_AuditActionLog_Write` ghi) không còn mật khẩu / token. Dòng cũ: `e2ef52f` |
| Bước | mọi lời gọi vào API (đăng nhập, phiếu, SO…) |
| Đã kiểm | build 0 lỗi; 10 đường chỉ đọc: trước 4 dòng "Đặt log sai", sau 0; che trường 6/6 |
| Thử lại | đăng nhập một lần, xem dòng audit mới nhất: `Password` là `***` |

#### 8.1.6. `ae0e7f6` — máy chủ tính quy đổi từng dòng

| | |
|---|---|
| Tệp | `Application/CashVoucherHeaderTotals.cs` (`ApplyLineBaseAmounts`), `CMPaymentReceiptService.cs` (gọi trước `Compute`) |
| Đổi gì | dòng: `BaseAmount = Round(Amount × (tỷ giá dòng ?? tỷ giá header), 5, AwayFromZero)`; công nợ DEP/DEPT có `PaymentBaseAmount` thì tính lại theo tỷ giá header (như `SP_CM_IMPORTDEPTDOC_COUNTRY_CASHVOUCHER`); giữ số client khi thiếu nguyên tệ, tỷ giá ≤ 0, dòng IV/IC, relation không ID |
| DB | không đổi thủ tục; `PUBENTRY.ET_BASEAMOUNT` là số máy chủ tính |
| Bước | A7 — trả chủ xe ngoại tệ (bước 11): bên em gửi tỷ giá riêng từng dòng, Kíp khoá từng phiếu xe giữ đúng; mọi phiếu khác |
| Đã kiểm | service thật + repository giả 27/27; build 0 lỗi |
| Thử lại | lập đề nghị trả chủ xe USD → mở phiếu bên anh: mỗi dòng quy đổi = nguyên tệ × tỷ giá dòng, header = Σ |

#### 8.1.7. `e2ef52f` — script che bí mật trong audit cũ

| | |
|---|---|
| Tệp | mới `Database/Scripts/20261001_audit_redact_secrets.sql` |
| Đổi gì | tự tìm bảng audit / error log (bảng `proc_PP_AuditActionLog_Write` / `proc_PP_AuditDataChangeLog_Write` / `proc_PP_ErrorLog_Write` ghi vào, và `PP_Audit%` / `PP_ErrorLog%`), cột payload tên chứa Json / Payload; che bằng `JSON_MODIFY` mọi cấp, chữ không phải JSON / query string theo mẫu; một transaction; chẩn đoán trước / sau (`RowsWithSecret` phải 0); `@Apply = 0` chỉ chẩn đoán; chạy lại an toàn |
| DB | **ghi dữ liệu**: `UPDATE` cột payload của các dòng audit cũ (không đổi cấu trúc). **Chưa chạy trên DB demo hay host** |
| Bước | triển khai (mục 5 việc 7) |
| Đã kiểm | LocalDB riêng dữ liệu bịa: lần 1 che 10 dòng, lần 2 không đổi |
| Thử lại | chạy `@Apply = 0` trước, đọc chẩn đoán; rồi `@Apply = 1` |

#### 8.1.8. `0d4eed9` — che thêm `jwt` / `cookie`

| | |
|---|---|
| Tệp | `ApiAuditPayloadSanitizer.cs` (thêm `jwt`, `cookie` vào danh sách) |
| Đổi gì | trường `JWTKey` (token đăng nhập) và cookie cũng thành `***`; cùng luật với log WEB (`7d168744`) |
| DB | như `ed5aa0e` |
| Bước | mọi lời gọi |
| Thử lại | như `ed5aa0e` |

#### 8.1.9. `b9227aa` — API bút toán tổng hợp `integrations/logistics/journal-entries`

| | |
|---|---|
| Tệp | mới: `Modules/Finance/Accounting/Api/V1/LogisticsJournalEntryController.cs` (HTTP / auth / envelope / audit), `Application/LogisticsJournalEntryService.cs` + `ILogisticsJournalEntryService.cs` (kiểm đầu vào, danh mục tài khoản qua `proc_PUBAccountCountry_GetList`, tính `BaseAmount`), `Infrastructure/LogisticsJournalEntryRepository.cs` + `ILogisticsJournalEntryRepository.cs` (gọi thủ tục, đọc OUTPUT, bảng mã lỗi SQL), `Contracts/V1/LogisticsJournalEntryModels.cs`; sửa `AccountingModule.cs` (đăng ký); mẫu `Database/Scripts/logistics-journal-entry-config.example.json`; script `Database/Scripts/20261001_logistics_journal_entry.sql` |
| Đổi gì | `POST` tạo + ghi sổ tạm (idempotent theo SourceRef, `sp_getapplock`, 409 khi cùng SourceRef khác nội dung); `POST reverse` gỡ; `GET {sourceRef}` đọc lại; cổng cấu hình `LogisticsJournalEntry` (`Enabled`, `AllowedUserIds`, `OrgId`, `CountryId`) đọc mỗi request |
| DB | script tạo **3 thủ tục mới** `proc_Logistics_JournalEntry_Save` / `_Reverse` / `_Get` (`CREATE OR ALTER`), **không đổi bảng**, dải lỗi riêng 52500 – 52516. Khi chạy, thủ tục ghi `PUBDOCUMENT`, `GLBUSINESS`, `PUBENTRY` và gọi `spGetconfigID`, `sp_PostTing_GeneralLedger`, `sp_GL_Delete_GENERALLEDGER`, `sp_GL_Delete_GLBusiness` (thủ tục có sẵn, không sửa). **Script chưa áp vào DB nào** |
| Bước | A11 — bước 7 (khoá phiếu), 7b (mở khoá → gỡ), 11 (`ban_chu_xe`), 12 (`tat_toan`) |
| Đã kiểm | build 0 lỗi; 82 kiểm unit-level (đầu vào, danh mục, quy đổi, khoá JSON, idempotent / 409, gỡ hai lần, cổng 401 / 403 / 503, bảng mã SQL); parse script 0 lỗi. **Chưa chạy trên DB** |
| Thử lại | mục 1.7.1 bước 1 – 4, mục 7 |

### 8.2. WEB `GLS-QLSX-Web` — 6 commit

Bên em chưa bấm thử trên giao diện WEB (không có mật khẩu đăng nhập WEB); các commit kiểm bằng `dotnet build` và bộ kiểm node chạy bản gốc / bản sửa với dữ liệu giả.

#### 8.2.1. `f382a9e8` — màn Vụ việc: thoát ký tự, DO hiện số phiếu / xe / tài xế

| | |
|---|---|
| Tệp | `wwwroot/ViewAssets/scripts/ACC/cm-source-reference-modal.js` |
| Đổi gì | `esc()` mọi chuỗi lấy từ Logistics trước khi ghép HTML; danh sách thêm dòng "số xe · biển — tài xế"; chi tiết: Mã chuyến = `doc_no`, Phương tiện = `truck_no · plate_head`, Tài xế = `driver_name`; `fx_rate` < 1 hiện ngược "1 USD = 22.000 LAK"; `margin_percent` null không in "null%" |
| DB | không |
| Bước | B1/B2 trên màn Phiếu chi / Phiếu thu của anh |
| Thử lại | mở modal Vụ việc → DO: thấy `T4-…/EPL`, tên khách Lào, xe · biển — tài xế |

#### 8.2.2. `06a14189` — `isCash`, tài khoản tiền mặc định, tổng xem trước, DOTY

| | |
|---|---|
| Tệp | `Controllers/Modules/Accounting/CMPaymentReceiptController.cs` (BFF `GetDefaultMoneyAccount` chuyển tiếp `currencyId`), `ACC/cm-payment-upsert.js`, `ACC/cm-receipt-upsert.js` |
| Đổi gì | `isCash` theo `PayIsCash` của hình thức đang chọn; tài khoản tiền mặc định đọc đúng `AccountCode` (trước đọc "account" nên chưa bao giờ tự điền) và gửi `currencyId`; `Header.Amount` = Σ nguyên tệ, `Header.BaseAmount` = Σ quy đổi; công nợ / khác phân theo `DOTY_AUTOID` (58/60, 15/17), không so tên hiển thị |
| DB | không |
| Bước | thủ quỹ bên anh mở / sửa phiếu bên em tạo (bước 4, 6, 11, 12, 13) và phiếu của chính anh |
| Thử lại | phiếu chi mới → chọn Chuyển khoản → tài khoản tiền tự điền 1021 |

#### 8.2.3. `7e14421c` — vế tiền đổi theo hình thức / nội tệ / loại tiền

| | |
|---|---|
| Tệp | `ACC/cm-payment-upsert.js`, `ACC/cm-receipt-upsert.js`, `Base/Localization/lo.json` |
| Đổi gì | `syncEntryMoneyAccounts`: vế tiền (chi: TK Có, thu: TK Nợ) của dòng còn mang tài khoản mặc định cũ đổi sang tài khoản mới; dòng người dùng tự chọn giữ nguyên; đổi quốc gia khi có dòng: chặn **trước** khi nạp danh mục; mã DOTY gom một chỗ; sửa chính tả `ACC_CLEAR_LINES_BEFORE_CHANGE_COUNTRY` |
| DB | không |
| Bước | như `06a14189` |
| Thử lại | đổi Tiền mặt → Chuyển khoản: dòng mặc định 1011 → 1021, dòng tự chọn giữ |

#### 8.2.4. `77bcb0a1` — loại phiếu không đổi ngầm; chặn XSS modal Vụ việc

| | |
|---|---|
| Tệp | `ACC/cm-payment-upsert.js`, `ACC/cm-receipt-upsert.js`, `ACC/cm-source-reference-modal.js`, `Base/Localization/vi.json · lo.json · en.json` |
| Đổi gì | ô loại hiện đúng loại phiếu đang mở; chỉ 58/60, 15/17 sửa được — 57, **59 "Chi trước" (bên em tạo)**, 68, 14, 16 chỉ xem, khoá Chỉnh sửa có báo (trước đây sửa phiếu 59 thì lưu thành 58, mất dòng); hình thức không rõ thì chặn lưu; đổi tài khoản tiền theo cờ `moneyAccountIsDefault`; dòng đã lưu gửi nguyên quy đổi API trả; modal thoát ký tự cả DEAL / QUOTE và câu lỗi máy chủ; khoá câu `ACC_DOCUMENT_TYPE_VIEW_ONLY`, `ACC_MONEY_ACCOUNT_KEPT_ON_LINES` |
| DB | không |
| Bước | bước 4 — thủ quỹ mở phiếu tạm ứng 59 bên em tạo: xem và ghi sổ ở danh sách / chi tiết, không sửa |
| Thử lại | mở một phiếu "Chi trước" → nút Chỉnh sửa khoá, có câu báo |

#### 8.2.5. `fce78c52` — tiền tệ ngoài danh mục không gán ngầm; tab Tài khoản hồ sơ nhân viên

| | |
|---|---|
| Tệp | `ACC/cm-payment-upsert.js`, `ACC/cm-receipt-upsert.js`; `Controllers/Modules/Organization/OrganizationHr/OrganizationHrController.cs` (BFF `AccountBranches` chỉ đọc), `Views/Modules/Organization/OrganizationHr/Employees.cshtml`, `scripts/api/organizationHrApi.js`, mới `scripts/modules/organizationHr/employee-account.js`; 19 khoá câu vi / lo / en |
| Đổi gì | bỏ mọi chỗ gán ngầm tiền tệ mã 1 / "loại đầu danh mục": mã tiền ngoài danh mục giữ đúng, phiếu chỉ xem, có báo; phiếu mới thiếu tiền tệ bị chặn lưu; quy đổi công nợ xem trước theo tỷ giá header (khớp `ae0e7f6`); phiếu chi mở lại đọc đúng tỷ giá (trước luôn 1). Tab **Tài khoản**: xem qua `account-lookups`; tạo / sửa (tên đăng nhập, nhóm, chi nhánh, kích hoạt, mật khẩu), đặt lại mật khẩu; kiểm trùng tên; hỏi xác nhận |
| DB | không tự ghi. Tab chỉ ghi khi người dùng bấm Tạo / Lưu / Đặt lại — qua BFF `UpsertAccount` / `ResetPassword` có sẵn → API `object-auth/account/upsert` (`sp_META_InsertUpdate_USERS`) |
| Bước | phiếu thu / chi (bước 4, 6, 11 – 13); tài khoản tích hợp (tuỳ chọn, mục 5 việc 5) |
| Đã kiểm | harness t6 đạt, hồi quy t2 – t4 giống từng byte, build 0 lỗi; **chưa bấm tạo tài khoản thật** |
| Thử lại | Nhân sự → Nhân viên → mở `EPL-TICHHOP` → tab Tài khoản |

#### 8.2.6. `7d168744` — che bí mật trong log WEB

| | |
|---|---|
| Tệp | mới `Backend.Common/Logging/LogPayloadSanitizer.cs`; sửa `Backend.Common/BackofficeApiService.cs`, `Backend/Base/Helpers/AppLoggingHelper.cs`, `Backend/Base/Middlewares/ExceptionLoggingMiddleware.cs`, `wwwroot/ViewAssets/scripts/_helpers/commonScripts.js` |
| Đổi gì | che mật khẩu / token / khoá / jwt / cookie theo tên trường (cùng luật `ApiAuditPayloadSanitizer`); header không ghi giá trị; body lỗi rỗng không còn ném `RequestMessage.ToString()` (từng in `Authorization: Bearer …` vào log và câu báo); console trình duyệt cũng che |
| DB | không (log tệp `Backend/.Logs`) |
| Bước | mọi lời gọi qua WEB |
| Đã kiểm | bản trước lộ 5 chỗ, bản sau 10/10; build 0 lỗi; log ở máy 0 dòng lộ |

### 8.3. Chưa commit (chỉ máy em, không đưa lên)

| Repo | Tệp | Vì sao |
|---|---|---|
| API | `Backend.API/Backend.API.csproj` | Visual Studio đổi `UserProperties`; bên em không sửa có chủ đích |
| API | `docs/PHIEU-THU-CHI-DEMOLAO-TONG-HOP.md` | tài liệu hiện trạng của anh **chưa có trong git** (cả thư mục `docs/` chưa track) |
| WEB | `Backend/Properties/launchSettings.json` | thêm `ASPNETCORE_URLS` vì Visual Studio bỏ qua `applicationUrl` (chạy WEB ở máy) |
| WEB | `Backend/package-lock.json` | npm tự đổi |
| WEB | `ACC/cm-payment-*.js`, `ACC/cm-receipt-*.js`, `ACC/cm-source-reference-modal.js`, `Localization/*.json`, `Views/Modules/Organization/Hr/Employees*` | bên EPL **đang sửa**, chưa commit — ghi vào mục 8.2 khi commit |
| cả hai | `appsettings*.json` | cấu hình từng môi trường (`LogisticsSource`, `LogisticsSalesPush`, `LogisticsJournalEntry` — mục cuối đã thêm vào `appsettings.laos.json` của API ở máy) — không đưa lên git; mẫu ở `Database/Scripts/*.example.json` |

### 8.4. Tạo SO (A2) — khớp

- Bên em chép đúng luật của `LogisticsPushValidator` và phần kiểm đầu của `sp_Logistics_CreateSalesOrder` thành bộ kiểm `kiem/thu_luat_so_ben_tune.py`. Chạy trên 13 DO đã khoá: **cả 13 qua**.
- **Dòng `chi`:** hệ anh chỉ ghép chúng thành chữ trên SO của khách, không thành bút toán → bên em **giữ một dòng thu**. Chi phí đi phiếu chi (A4, A7 – A10) và bút toán tổng hợp (A11).
- **403 thân rỗng** = tài khoản token chưa nằm trong `LogisticsSalesPush.AllowedUserIds`, hoặc chưa gắn nhân viên. Bên em báo đúng lý do.
- **Chi nhánh 1368, người tạo 4, quốc gia 11 ghi cứng** trong thủ tục. Tạo đơn vị riêng cho EPL Lào thì thủ tục phải đổi theo (API bút toán thì lấy từ cấu hình `LogisticsJournalEntry`).
- **Mã khách:** mở đầu bằng chữ / số, chỉ chữ, số, `_ . -`; ghép với mã tuyến ≤ 50 ký tự. Danh mục khách bên em chặn theo đúng luật đó (không `/`, tối đa 37 ký tự).

### 8.5. Nguồn DO cho phiếu thu chi (B1, B2)

- `CashVoucherReferenceController` chỉ còn HTTP / claims / envelope. Đọc, lọc, phân trang nằm ở `CashVoucherReferenceService`; gọi Logistics ở `LogisticsDeliveryOrderClient` (typed HttpClient: 15 giây, ≤ 2 MB, không chuyển hướng, không ghi header `Authorization` vào log).
- Cấu hình `LogisticsSource` (`BaseUrl`, `ApiKey`, ghi đè theo `Branches:<BranchId>`); mẫu khoá ở `Database/Scripts/logistics-source-config.example.json`. **Thiếu `BaseUrl` → 503.**
- DO: `SourceCode` = số phiếu `doc_no`, `SourceName` = tên khách; chi tiết DO phải `delivered` và đúng `do_id`, không thì 409. `SelectionToken` gắn người xem, hạn 7200 giây.
- Gói bàn giao bên em một DO 4–7,4 KB, một trang 13 DO 11 KB, mỗi lời gọi dưới 0,4 giây — dưới giới hạn bên anh.

### 8.6. Phiếu thu chi (A4, A7 – A10)

- **Quy đổi từng dòng** (`ae0e7f6`, `ApplyLineBaseAmounts`): `BaseAmount = Round(Amount × (tỷ giá dòng ?? tỷ giá header), 5, AwayFromZero)`; giữ số client khi thiếu nguyên tệ, tỷ giá ≤ 0, dòng IV/IC.
- **Tổng header** (`ce95b3c`, `CashVoucherHeaderTotals`) ở create-session, save-session, save-and-commit: Σ `Entries` (5 số lẻ, nửa xa số 0); số client gửi bị thay. Phiếu có dòng IV/IC hay công nợ thiếu số tiền thì giữ số header client gửi (đường tương thích). Mọi phiếu bên em chỉ có `Entries`, nên luôn được tính lại.
- **Nhật ký kiểm toán** (`ed5aa0e`, `0d4eed9`): payload che mật khẩu / token / khoá / jwt / cookie; dòng audit cũ che bằng script `e2ef52f` (chưa chạy, mục 5 việc 7).
- `ObjectService` (`be123e9`): tạo đối tượng không gửi `IsOrganization` thì là cá nhân. Bên em vẫn luôn gửi ô này.
- WEB (`06a14189`, `7e14421c`, `77bcb0a1`, `fce78c52`): `isCash` theo hình thức thanh toán, không rõ thì chặn lưu; tài khoản tiền mặc định đọc `AccountCode`; đổi hình thức / nội tệ / loại tiền thì chỉ dòng mang cờ `moneyAccountIsDefault` đổi vế tiền; loại phiếu không đổi ngầm — 58/60, 15/17 sửa được, loại khác (57, 59 "Chi trước", 68, 14, 16) chỉ xem; tiền tệ ngoài danh mục không bị thay bằng loại đầu; modal Vụ việc thoát ký tự cả DEAL / QUOTE.

### 8.7. Hoá đơn điện tử

Dịch vụ `Backend.LaoInvoice` (`3b5d159`, có trước khi tách nhánh) **chưa nối SO hay DO**. Bên em không gọi, không sửa.

---

## 9. Dữ liệu đã ghi vào DB demo của anh qua API ở máy

DB: DB demo Lào anh sao lưu sáng 01/10, qua **API ở máy** (`Env=laos`). Mọi thay đổi đi qua **API của chính hệ anh**; bên em **không sửa thẳng DB, không chạy script nào** trên DB này. Trên **host** `demo-lao-api.goldensme.com` bên em **không ghi gì** (chỉ đường đọc, mục 1.3). Số liệu lấy từ tài liệu và bộ kiểm bên em, không truy vấn DB.

### 9.1. Danh mục tài khoản quốc gia 11

| Đã làm | Đường API | Thủ tục / bảng | Trả lại thế nào |
|---|---|---|---|
| `137` → tài khoản **tổng hợp** (`Posting=false`, giữ tên, cha 13, số dư, nhóm, loại) | `POST /api/v1/accounting/lao-accounts/update` | `proc_LaoAccounts_CRUD` (script `20260913_lao_accounts_crud.sql` của anh) → danh mục `PUBACCOUNTCOUNTRY` quốc gia 11 | `update` 137 với `Posting=true` |
| thêm **`1371`** "ສາງສິນຄ້າ, ວັດຖຸ" (kho hàng, vật tư), cha 137, lá, dư Nợ | `POST …/lao-accounts` | như trên | xoá 1371 khi chưa có bút toán |
| `402` → tài khoản **tổng hợp** | `POST …/lao-accounts/update` | như trên | `update` 402 với `Posting=true` |
| thêm **`4021`** "ໜີ້ຕ້ອງສົ່ງ ຜູ້ສະໜອງ" (phải trả nhà cung cấp), **`4022`** "ເຈົ້າໜີ້ເຈົ້າຂອງລົດຮ່ວມ" (phải trả chủ xe liên kết), cha 402, lá, dư Có | `POST …/lao-accounts` | như trên | xoá khi chưa có bút toán |

- Làm bằng `tools/mo_ma_con_tune.py` (chạy lại không sao; mã đã có thì bỏ qua). Sau đó `country-accounts?tryAutoId=11` trả **497 mã** (trước 494); 137, 402 không còn trong danh sách cho hạch toán.
- **Ảnh hưởng:** 137 và 402 không ghi sổ trực tiếp được nữa. Trong `GLS-QLSX-APIs` và `GLS-QLSX-Web` không có chỗ nào ghi cứng 137 / 402, ngoài tệp nạp danh mục `20260909_country_account_import_lao.sql`. Thủ tục SQL hay màn cũ nào ghi thẳng 137 / 402 sẽ bị từ chối, phải đổi sang 1371 / 4021.
- Hiện đã có phiếu chi dùng 4022 (mục 9.4), nên muốn trả lại phải xoá / gỡ các phiếu đó trước.

### 9.2. Đối tượng (`PUBOBJECT`, qua `master-data/*/upsert` → `sp_Meta_Insert_Update_PUBOBJECT`)

| Loại | Mã | Danh mục bên anh | Ví dụ đã tạo |
|---|---|---|---|
| khách | `EPLKH-<mã khách bên em>` | `customers` | `EPLKH-0834a9e9606b` ຄຳຕຸ້ຍ (ObjId 1608) |
| chủ xe liên kết | `EPLCX-<mã chủ xe bên em>` | `suppliers` (cá nhân) | chủ xe của các phiếu xe thuê đã thử; KB-AZ `EPLCX-0a073ea75bb3` ທ້າວ ຄຳຫລ້າ |
| nhà cung cấp | `EPLNCC-<mã nhà cung cấp bên em>` | `suppliers` (tổ chức) | nhà cung cấp của bài trả nhà cung cấp; KB-AZ `EPLNCC-804c0e8ff1d8` ຊີບປີງ ລາວ |
| tài xế | `EPLTX-<mã tài xế bên em>` | `staff` | tài xế các phiếu đã thử; tài xế thử **`EPLTX-THU01`**; KB-AZ `EPLTX-a6313dd63966` ທ້າວ ບຸນມີ |
| nhân viên ảo | `EPL-TICHHOP` "EPL Logistics (tích hợp)" | nhân viên chi nhánh 1368 | ObjId **1622**, **chưa có tài khoản đăng nhập** |

Tất cả thuộc chi nhánh 1368, quốc gia 11. Để nguyên không ảnh hưởng gì; host khác DB thì bên em tự tạo lại ở lần gửi đầu.

### 9.3. SO + công nợ khách (qua `integrations/logistics/sales-orders` → `sp_Logistics_CreateSalesOrder`)

| SO | DO | Khách | Số tiền | Bảng ghi |
|---|---|---|---|---|
| `TK-20261001-000162` | T4-0449-09/EPL (`EPLLAO-779739f4b582`) | ຄຳຕຸ້ຍ `EPLKH-0834a9e9606b` | 905,85 USD | `TicketOrder`, `TicketOrderDetail`, `RESTICKET*`, `RESCUSTOMERSDEBT`, `PUBITEMS` / `PUBITEMOFGROUP` / `LogisticsPushItem` (mặt hàng khách_tuyến), `LogisticsPushOrder` |
| `TK-20261001-000163` | T4-0442-09/EPL | ນາງ ວັນນາ | 1.676,90 USD | như trên |
| `TK-20261001-000164` | KB-AZ `THU-KBAZ-G1/EPL` (gom, `EPLLAO-37367086d283`) | ຄຳຕຸ້ຍ `EPLKH-0834a9e9606b` | 495,00 USD · mặt hàng `EPLKH-0834a9e9606b_b9213bcb64b9` | như trên; **đã thu đủ** (mục 9.5) |
| `TK-20261001-000165` | KB-AZ `THU-KBAZ-T1/EPL` (giao, `EPLLAO-ea99922a96ee`) | ຄຳຕຸ້ຍ `EPLKH-0834a9e9606b` | 753,35 USD · mặt hàng `EPLKH-0834a9e9606b_0b840ad2a162` | như trên; **đã thu đủ** (mục 9.5) |

SO 162, 163 tạo ngày 01/10 trước giờ cắt sổ, **giữ nguyên**, là công nợ thật của hai DO đó. SO 164, 165 là chuyến thử KB-AZ (HTTP 201, nợ ban đầu bằng cước), đã thu xong; giữ làm mẫu. Cả bốn SO cùng mã phiếu bán `Demo EPL-2-261001000` (lỗi bên anh, mục 1.5).

### 9.4. Phiếu chi / phiếu thu thử (qua `cmpayment-receipt/save-and-commit`; bài kiểm đóng vai thủ quỹ bằng `…/post`)

| Phiếu | Loại | Nội dung | Còn hay đã rút |
|---|---|---|---|
| `1368-CTR-261001-00013` | 59 "Chi trước" | tạm ứng xe thuê, đứng tên chủ xe, Nợ 4022 / Có 1011 | bài thử tự rút sau khi kiểm |
| `1368-CTR-261001-00016` | 59 "Chi trước" | tạm ứng xe nhà, Nợ 1601 / Có 1011 | bài thử tự rút sau khi kiểm |
| `1368-CKH-261001-00001`, `…00002` | 60 "Chi khác" | trả chủ xe 28.359.600 LAK, Nợ 4022 / Có 1021 | bài thử tự rút sau khi kiểm |
| `1368-CTR-261001-…` (số tham chiếu `PTU-THU-CK-…`, `PTU-T4-CHO-…`, đối tượng `EPLTX-THU01`) | 59 "Chi trước" | bài `kiem/thu_chi_tam_ung_ke_toan.py`: 580.000 LAK, Nợ 1601 / Có 1011, **ghi sổ** để thử tài xế xuất phát | **còn lại** trên DB (đã ghi sổ, bài không xoá) — mỗi lần chạy bài thêm một phiếu |
| phiếu "Chi khác" mục V – VI, chi bù / thu hoàn tất toán, trả nhà cung cấp | 60 / 17 | bài `thu_chi_muc_tune.py`, `thu_tat_toan_tune.py` | cuối bài **gỡ ghi sổ** (`…/unpost`) rồi **xoá** (`…/delete`) |
| `1368-CTR-261001-00072` (DocumentId 81417) | 59 "Chi trước" | KB-AZ tạm ứng xe nhà `PTU-THU-KBAZ-G1/EPL`, `EPLTX-a6313dd63966`, Nợ 1601 / Có 1011 · 250.000 LAK | **còn lại**, đã ghi sổ chính (12) |
| `1368-CTR-261001-00073` (81421) | 59 "Chi trước" | KB-AZ tạm ứng xe thuê `PTU-THU-KBAZ-T1/EPL`, chủ xe `EPLCX-0a073ea75bb3`, Nợ 4022 / Có 1011 · 4.247.000 LAK | **còn lại**, đã ghi sổ chính |
| `1368-CKH-261001-00067` (81419) | 60 "Chi khác" | KB-AZ chi mục V garage `PCSC-V-THU-KBAZ-G1/EPL-1`, `EPLTX-a6313dd63966`, Nợ 614 / Có 1011 · 250.000 LAK | **còn lại**, đã ghi sổ chính |
| `1368-CKH-261001-00068` (81427) | 60 "Chi khác" | KB-AZ tất toán TT_CHI `TTX-202610-99c2aab4`, `EPLTX-a6313dd63966`, Nợ 1601 / Có 1011 · 960.000 LAK | **còn lại**, đã ghi sổ chính |
| `1368-CKH-261001-00069` (81429) | 60 "Chi khác" | KB-AZ trả chủ xe `TCX-261001104415-0a07`, `EPLCX-0a073ea75bb3`, Nợ 4022 / Có 1012 · 204,95 USD | **còn lại**, đã ghi sổ chính |
| `1368-CKH-261001-00070` (81431) | 60 "Chi khác" | KB-AZ trả nhà cung cấp `TNCC-261001104417-804c`, `EPLNCC-804c0e8ff1d8`, Nợ 4021 / Có 1021 · 620.000 LAK | **còn lại**, đã ghi sổ chính |

Bảng ghi: `PUBDOCUMENT`, `CMPAYMENT` / `CMRECEIPT`, `PUBENTRY` (qua bảng tạm và `SP_CM_MOVETEMPTOREAL_*`); ghi sổ `sp_PostTing_GeneralLedger`; rút `SP_CMP_DELETECMP_CMPAYMENT` / `SP_CMR_DELETEMCMR_CMRECEIPT`. Phiếu chưa ghi sổ do bên em tạo đều đã rút. Chứng từ KB-AZ em đóng vai thủ quỹ ghi sổ (`…/post` PostedFinal), giữ lại làm mẫu; anh muốn dọn thì gỡ ghi sổ rồi xoá.

### 9.5. Thu nợ khách thử (KB-AZ, qua `sales/debt/collection-upsert` → `sp_RES_CreateDebtCollection_COUNTRY`)

Em gửi đúng lời gọi WEB gửi khi bấm **Xác nhận thu nợ** (`TKN`, chi nhánh 1368, Ngân hàng nội tệ, Chuyển khoản, tỷ giá 1), rồi ghi sổ phiếu thu.

| Phiếu thu nợ | SO | Số thu | → Phiếu thu CM | Định khoản | Bảng ghi |
|---|---|---|---|---|---|
| `4-TKN-1368-2-261001-0001` | `TK-20261001-000164` | 495,00 USD | `4-1368-TK-261001-00009` (DocumentId 81423), CMR 17 "Thu khác", đã ghi sổ | Nợ 1021 / Có 1211 | `RESDOCUMENT`, `RESDOCUMENT_TICKET`, `RESCUSTOMERSDEBT` (nợ về 0, `RCTD_ISPAID = 1`), `PUBDOCUMENT`, `CMRECEIPT`, `PUBENTRY` |
| `4-TKN-1368-2-261001-0002` | `TK-20261001-000165` | 753,35 USD | `4-1368-TK-261001-00010` (81424), CMR 17, đã ghi sổ | Nợ 1021 / Có 1211 | như trên |

Cả hai mang lỗi tỷ giá cứng 1 (quy đổi = nguyên tệ USD, vế tiền ngân hàng Kíp) — mục 1.5, mục 5 việc 9. Bên em: hai DO **Đã thu đủ**, khối Công nợ bên hệ kế toán đã thu 1.248,35 USD.

### 9.6. Những gì chưa ghi

- **Bút toán tổng hợp:** chưa có chứng từ nào (script chưa áp, cờ gửi tắt).
- **Bản chụp DO trên phiếu** (`proc_PP_CashVoucherSourceReference_Save`): bên em chỉ gọi đường đọc của modal Vụ việc (KB-AZ: `type=DO&keyword=THU-KBAZ` trả 2 DO), chưa lưu phiếu nào có Vụ việc DO.
- **Bút toán chờ KB-AZ** (ví dụ `EPLLAO-tat_toan-a6313dd63966:2026-10:99c2aab478f2` 625/1601 · 1.210.000 LAK) chỉ nằm ở LAO, chưa sang DB của anh.
- **Trừ hàng quầy 4022/707** chưa đi thật lượt KB-AZ (chủ xe không có phiếu bán chờ trừ).
- **Script che audit** (`e2ef52f`): chưa chạy.
- **Nhật ký kiểm toán:** mỗi lời gọi của bên em vào API ở máy có một dòng audit (thủ tục ghi audit có sẵn). Dòng trước `ed5aa0e` có thể còn mật khẩu của lần đăng nhập — cần chạy script `e2ef52f` (mục 5 việc 7).
