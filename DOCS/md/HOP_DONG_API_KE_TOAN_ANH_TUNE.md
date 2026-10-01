# Hợp đồng API KẾ TOÁN — trang điều xe EPL Lào ↔ hệ kế toán của anh Tune

Phiên bản đề nghị **v2.6 · 01/10/2026** (lịch sử các bản trước tra bằng Git). Bên soạn: trang điều xe **EPL_LAO_REAL** (logistics). Người nhận: **anh Tune** (công nợ, thu chi, sổ kế toán).

> **Hiện trạng 01/10/2026 (đọc trước):**
> - **Ranh giới tiền (chủ dự án chốt 01/10):** bỏ phần tiền của trang kế toán tạm `EPL_KETOAN` (8030). Trang đó chỉ còn là **kho tạm** tới khi nối hệ kho anh Toàn. Số tiền ở đó là **số thử, bỏ hết**. **Cắt sổ 01/10**: mọi DO đã khoá gửi SO sang hệ anh từ đầu; luật `DA_HOA_DON_TRANG_TAM` đã bỏ (12.11.1).
> - **Khoản đi qua tiền** thành **phiếu chi / phiếu thu bên anh**: tạm ứng (12.10), trả chủ xe có trừ hàng mua ở quầy (12.11.3), chi mục V – VI, tất toán tài xế (chi bù / thu hoàn), trả nhà cung cấp — chạy ở máy (mục 5). **Khoản không qua tiền** thành **bút toán chờ gửi** ở trang điều xe (màn "Bút toán chờ gửi"), gửi sang **API bút toán tổng hợp** bên anh (`b9227aa`) khi bật cờ `QLSX_GUI_BUT_TOAN` — API và đầu gửi đã có, **đã chạy thật trên DB demo 02/10** (chủ dự án áp script; phiếu thử qua máy thử trang điều xe: thuê xe `GL021020263` / `GL021020264`, xuất kho `GL021020265` · `GL021020267`, ST 13; mở khoá gỡ sạch, GET 404); host chưa áp (mục 8, 12.12.4).
> - **Người làm (chủ dự án chốt 01/10: "bên mình với anh Tune giờ là một"):** việc trước ghi "anh làm" nay **bên EPL làm (đang làm)**, kể cả trên source của anh. Việc cần máy chủ host (triển khai, dữ liệu trên DB host, token / mật khẩu tài khoản của anh) ghi **cần quyền host**.
> - **Token (chủ dự án chốt 01/10):** tạm gác tài khoản tích hợp; trang điều xe tiếp tục dùng **token của anh** (`EPL_ACC_CODE_TOKEN`). Hết hạn khoảng 10/10 thì thay token mới trong `.env`, hoặc đặt `QLSX_USERNAME` / `QLSX_PASSWORD` của anh để trang điều xe tự đăng nhập lại (12.11.4). Tài khoản tích hợp là **tuỳ chọn** (12.12.3).
> - Trang điều xe **thôi đẩy phong bì** `POST /api/v1/epl-lao/vouchers` (3.1). Các đường `/api/lien-thong/*` phần tiền đã gỡ (mục 4).
> - **Source của anh** bên em đã sửa: API `feat/HonTunedaHai@b9227aa`, WEB `feat/hontunedhai_Laos@7d168744` (12.9). Trong đó: nguồn DO đọc cấu hình `LogisticsSource`, thiếu `BaseUrl` thì 503; hệ anh **tự tính quy đổi từng dòng và tổng header** phiếu thu chi; nhật ký kiểm toán và log WEB che mật khẩu; **API bút toán tổng hợp** (12.12.4); WEB không đổi loại phiếu ngầm, không gán ngầm tiền tệ. Trang điều xe `f85078b`, `ca7b630`, `938b007` (dọn lớp tạm), `a938301`, `875a0cf` (gửi bút toán); kho tạm `EPL_KETOAN@1d8d91c`. Mã còn đổi nhỏ: chỗ chưa chắc ghi **đang chốt**.
> - **Dữ liệu** trên DB của `appsettings.laos.json`: đã mở 1371, 4021, 4022 (12.12.1); đối tượng `EPLKH-`, `EPLCX-`, `EPLTX-`, `EPLNCC-`; hai SO `TK-20261001-000162`, `…163` tạo ngày 01/10 trước giờ cắt sổ, **giữ nguyên**, là công nợ thật của hai DO đó.
> - Bản host `demo-lao-api.goldensme.com` chưa merge code hai nhánh; triển khai xong thì đổi link (12.12.2).
> - Bản đồ gọn "mình gọi gì, anh gọi gì, chứng từ đi đâu": **`NOI_API_ANH_TUNE`**. Trang tổng hợp: **`TONG_HOP_BAN_GIAO_ANH_TUNE`**.

## 0. Đọc tài liệu này thế nào

### 0.1. Ranh giới ba bên (chủ dự án chốt 29–30/09/2026)

| Bên | Làm gì |
|---|---|
| **Trang điều xe** EPL_LAO_REAL (bên em) | Phiếu xuất xe (DO), tuyến, xe, tài xế, theo dõi chuyến, duyệt từng mục trên phiếu. **Lập phiếu ĐỀ NGHỊ**: đề nghị tạm ứng (tiền), đề nghị xuất kho nhiên liệu (kho), đề nghị thu (cước). **Xem** công nợ, thu chi — chỉ xem |
| **Hệ kế toán** của anh Tune | Công nợ phải thu và phải trả, hoá đơn, phiếu thu, phiếu chi, trả chủ xe liên kết, trả nhà cung cấp, tất toán tài xế, sổ kế toán |
| **Hệ kho** của anh Toàn | Nhập, xuất, tồn, giá vốn (hợp đồng riêng: `HOP_DONG_API_KHO_ANH_TOAN`) |

**Trang kế toán tạm** `EPL_KETOAN` (cổng 8030, DB `epl_ketoan`): chủ dự án chốt 01/10 **bỏ phần tiền**, trang đó chỉ còn là **kho tạm** tới khi nối hệ kho anh Toàn. Số tiền đã ghi ở đó (hoá đơn, lần thu, đợt trả chủ xe, tất toán, trả nhà cung cấp, cấn trừ) là **số thử, bỏ hết**. **Cắt sổ 01/10**: mọi việc tiền từ nay chỉ ở hệ anh.

| Loại khoản | Đi đường nào |
|---|---|
| **Đề nghị thu** (cước) | SO + công nợ khách bên anh (3.2); mọi DO đã khoá gửi từ đầu |
| **Khoản đi qua tiền**: tạm ứng, trả chủ xe, chi mục V – VI, tất toán tài xế (chi bù / thu hoàn), trả nhà cung cấp | **phiếu chi / phiếu thu bên anh** (`cmpayment-receipt/save-and-commit`, `PostMode = None`); thủ quỹ bên anh chi / thu và ghi sổ; trang điều xe đọc lại `STATUS` (12.10, 12.11.3; chạy ở máy) |
| **Khoản không qua tiền**: chi phí thuê xe 621/4022, ghi nợ nhà cung cấp 625 · 614 / 4021, quyết toán tạm ứng 625/1601, hàng bán cho chủ xe 4022/707, **xuất kho cho chuyến** (xe nhà 625 · 614 / 1371 giá vốn; xe thuê 4022/707 giá bán + 607/1371 giá vốn) | **bút toán chờ gửi** giữ ở trang điều xe, đủ hai vế; gửi qua `integrations/logistics/journal-entries` bên anh (12.12.4) — API đã có (`b9227aa`), script đã áp DB demo và chạy thật 02/10; host: áp script rồi bật cờ |
| Hoá đơn, thu tiền khách, cấn trừ | việc của hệ anh, từ SO. Thu tiền: màn **Chi tiết công nợ khách hàng → Tạo phiếu thu → Xác nhận thu nợ** (TKN) → phiếu thu CMR 17 "Thu khác", Nợ 1021 / Có 1211 — **không** phải phiếu "Thu công nợ" (15). Trang điều xe chỉ đọc "đã thu" (12.11.2) |

Mọi đường và trường trong tài liệu này **chép từ mã đang chạy** (đọc ngày 30/09 và 01/10/2026).

Các API anh đã có được dùng ở đây:
- `POST /api/v1/integrations/logistics/sales-orders` — tài liệu anh viết ngày 11/09;
- `GET /api/v1/common/country-accounts` — danh mục tài khoản;
- nhóm phiếu thu chi `…/accounting/cmpayment-receipt/*` — hướng dẫn **API thu chi DemoLao** (`CM-CASH-VOUCHER-DEMOLAO-API-GUIDE.md`) và tài liệu hiện trạng `GLS-QLSX-APIs/docs/PHIEU-THU-CHI-DEMOLAO-TONG-HOP.md`;
- `master-data/*/upsert` (đối tượng), `sales/debt/customer-detail` (công nợ khách).

Mục **12** ghi từng việc bên em ↔ đường thật của anh.

### 0.2. Quy ước

- **LAO** là trang điều xe (`D:\Demo_Lao\EPL_LAO_REAL\backend\app`).
- **KT tạm** là bản tạm `D:\Demo_Lao\EPL_KETOAN\backend\app`.
- **QLSX** là hệ của anh.
- Vị trí mã ghi dạng `tệp:hàm (dòng)`.
- **Hướng gọi:** "LAO → QLSX" là bên em gọi anh; "QLSX → LAO" là anh gọi bên em.
- Mỗi mục ghi hai phần:
  - **Hiện trạng**: mã đang chạy (bên em, và source của anh ở 12.9);
  - **Đề nghị**: việc làm trong hệ của anh — bên EPL làm trên source (đang làm); phần cần máy chủ host ghi **cần quyền host**.
- **Tiền:**
  - luôn là số JSON, đi kèm **mã tiền tệ của chính chứng từ** (`LAK` · `USD` · `THB` · `VND` · `CNY`);
  - **không bao giờ giả định LAK hay VND**;
  - LAK là tiền gốc để ghi sổ.
- **Tỷ giá** là "bao nhiêu LAK cho một đơn vị". Tỷ giá **khoá trên phiếu lúc lập** (`rate_usd`, `rate_thb`, `rate_vnd`, `rate_cny`).
- **Ngày:** `YYYY-MM-DD`. Ngày giờ theo ISO 8601; đề nghị ghi múi giờ `+07:00`.

---

## 1. Danh mục tài khoản (chủ dự án chốt "cách A", 30/09)

Danh mục của anh (`country-accounts`, quốc gia `11` = Lào): host trả **494 mã**; DB của `appsettings.laos.json` (API chạy ở máy) trả **497 mã** sau khi mở ba mã con ngày 01/10 (12.12.1). Bên em chụp bản dự phòng vào `backend/app/services/danh_muc_tai_khoan_lao.json` (bản 01/10, đã có ba mã). Mỗi mã hệ thống in ra đã đối chiếu với danh mục này, với Excel của khách, và với quy trình kế toán của anh Khampla (kế toán EPL).

### 1.1. Ba mã con trong danh mục của EPL — đã mở 01/10

Anh Khampla ghi sổ bằng **mã con**, và chủ dự án chốt giữ đúng như vậy. Ba mã dưới đây **đã mở** qua `lao-accounts` trên DB của `appsettings.laos.json`; `137` và `402` thành tài khoản tổng hợp (12.12.1). Host trỏ DB khác thì chạy `tools/mo_ma_con_tune.py` (12.12.2):

| Mã | Cha | Tên Việt | Tên Lào | Loại | Dùng cho |
|---|---|---|---|---|---|
| **1371** | 137 (ສິນຄ້າ ໃນສາງ — hàng hoá tồn kho) | Kho hàng, vật tư | ສາງສິນຄ້າ, ວັດຖຸ | tài sản, ghi sổ được | kho dầu, kho phụ tùng của EPL |
| **4021** | 402 (ໜີ້ຕ້ອງສົ່ງ ຜູ້ສະໜອງ - ການບໍລິການ) | Phải trả nhà cung cấp | ໜີ້ຕ້ອງສົ່ງ ຜູ້ສະໜອງ | nợ phải trả, ghi sổ được | trạm dầu ghi nợ, chipping cửa khẩu, lốp, garage, thẻ cao tốc, nhập kho |
| **4022** | 402 | Phải trả chủ xe liên kết | ເຈົ້າໜີ້ເຈົ້າຂອງລົດຮ່ວມ | nợ phải trả, ghi sổ được | xe thuê (chủ xe liên kết): tiền thuê phải trả, trừ các khoản EPL ứng |

Trên màn LAO, mã nào danh mục của anh chưa trả thì mang nhãn vàng **"chưa mở"**; danh mục có mã thì nhãn tự mất, không phải sửa mã.

### 1.2. Các mã đã có sẵn trong danh mục, bên em đang dùng

| Mã | Tên (theo danh mục của anh) | Dùng cho |
|---|---|---|
| 625 | ຄ່າເດີນທາງ, ກອງປະຊຸມ, ຮັບແຂກ (đi lại, công tác phí) | chi phí dầu và đi đường của xe nhà — anh Khampla dùng 625 cho cả dầu, chủ dự án chốt giữ |
| 614 | ຄ່າບົວລະບັດ, ບຳລຸງຮັກສາ ແລະ ສ້ອມແປງ | sửa chữa xe nhà |
| 607 | ສິນຄ້າ (nhóm 60 — giá vốn hàng bán) | giá vốn khi bán dầu, phụ tùng |
| 1601 | ພະນັກງານ - ເງິນລ່ວງໜ້າ … (tạm ứng nhân viên) | tạm ứng cho tài xế xe nhà |
| 4201 | ພະນັກງານ - ຄ່າທົດແທນແຮງງານຕ້ອງສະສາງ (phải trả nhân viên) | tiền chuyến, tiền nước trả cùng lương |
| 1211 | ລູກຄ້າ-ຄ່າສິນຄ້າ (phải thu khách hàng) | phải thu cước — **giữ 1211 như Excel của khách** (chủ dự án chốt) |
| 708 | ຂາຍການບໍລິການອື່ນໆ (bán dịch vụ khác) | doanh thu cước vận chuyển |
| 707 | ຂາຍສິນຄ້າ (bán hàng hoá) | doanh thu bán dầu, phụ tùng |
| 1011 · 1012 · 1021 · 1022 | tiền mặt Kíp · tiền mặt ngoại tệ · ngân hàng Kíp · ngân hàng ngoại tệ | vế tiền |

- **"70" không dùng nữa.** Excel và quy trình của khách ghi doanh thu vào 70, nhưng 70 là tài khoản **nhóm**, không ghi sổ được.
- Theo đó cước đổi sang **708**, còn bán hàng đổi sang **707**.

### 1.3. Ba mã bên em còn chờ chốt

| Ô cấu hình bên LAO | Cần mã cho | Ghi chú |
|---|---|---|
| `ma_hang_khach_gui` | **hàng khách gửi giữ hộ** (quặng của khách nằm ở bãi Thà Bốc giữa hai chặng) | Hàng này **ngoài bảng**: EPL không sở hữu. Ghi đơn một vế, theo tấn |
| (mới) | **đối ứng khi cấn trừ** | Khách trả hộ EPL (thẻ cao tốc khách tự nạp, trạm dầu Việt Nam ghi nợ rồi khách trả). Hiện vế Nợ rơi vào ngân hàng 1021 — sai, vì không có tiền về (mục 8, lỗ hổng 5) |
| `ma_gia_von` | giá vốn hàng bán | đang dùng **607**; **đang chốt** |

---

## 2. Kết nối, xác thực, lỗi

### 2.1. Hiện trạng

**LAO gọi trang kế toán tạm (chỉ còn phần kho):**
- Từ 01/10 LAO **không đẩy chứng từ tiền** sang trang tạm nữa (3.1). Cấu hình kho đọc qua `services/goi_ke_toan.py` (`kho_api`, `kho_token`, `kho_web`).
- Header gửi kèm:

  ```
  Authorization: Bearer <ke_toan_token>
  Content-Type: application/json; charset=utf-8
  Accept: application/json
  X-Nguoi-Dung: <tên đăng nhập người bấm>        ← có ở các đường liên thông; KHÔNG có ở đường đẩy chứng từ
  ```

- Hết giờ sau 15 giây. HTTPS dùng bộ chứng chỉ `certifi`.
- Không nối được thì LAO báo 503 `CHUA_NOI_KE_TOAN`. **Không xếp hàng gửi sau**: chủ dự án chốt "chặn và báo rõ".

**Trang kế toán tạm gọi LAO (phần kho):**
- Bản tạm đọc địa chỉ LAO từ `dieu_xe_api` (env `EPL_KETOAN_DIEU_XE_API`) và khoá từ `dieu_xe_token` (env `EPL_KETOAN_DIEU_XE_TOKEN`).
- LAO kiểm khoá theo `cau_hinh.token_nhan_ke_toan` (env `EPL_LAO_TOKEN_NHAN_KE_TOAN`).
- Sếp tạo khoá bằng `POST /api/lien-thong/tao-khoa` (chỉ admin; khoá hiện **một lần**).
- `X-Nguoi-Dung` phải là **tên đăng nhập có thật ở LAO**. Mọi kiểm quyền sau đó dùng **vai bên LAO** của tên đó.

**Danh mục tài khoản:** env `EPL_ACC_CODE_API`, `EPL_ACC_CODE_TOKEN`, `EPL_ACC_CODE_COUNTRY` (mặc định `11`). Chi tiết ở mục 3.3.

**LAO gọi hệ anh (SO, phiếu thu chi, đối tượng, công nợ — mục 3.2, 12.10, 12.11):**
- Gốc: `QLSX_BASE_URL` nếu đặt; không thì giao thức + tên máy của `EPL_ACC_CODE_API` (hiện là `https://demo-lao-api.goldensme.com`; máy thử 8011 đặt `http://127.0.0.1:5090`, API của anh chạy ở máy).
- Token: `QLSX_ACCESS_TOKEN` nếu đặt; không thì **tự đăng nhập** (`QLSX_USERNAME` / `QLSX_PASSWORD` / `QLSX_ORG_ID`, 12.11.4); không thì `EPL_ACC_CODE_TOKEN`.
- Token đang dùng là **tài khoản cá nhân `tune`, hết hạn 10/10/2026 09:05 giờ Lào**. Chủ dự án chốt 01/10: tiếp tục dùng, tạm gác tài khoản tích hợp. Trước hạn thì thay token mới trong `.env`, hoặc đặt `QLSX_USERNAME` / `QLSX_PASSWORD` của anh để tự đăng nhập lại (12.11.4). Hết hạn mà chưa thay thì danh mục tài khoản rơi về bản chụp, còn SO và phiếu chi không gửi được.
- Hết giờ 60 giây. Token chỉ nằm ở máy chủ bên em, không xuống trình duyệt.

### 2.2. Đề nghị

1. **Tách địa chỉ theo việc.** Bên em thêm cấu hình riêng:

   | Khoá | Env | Dùng cho |
   |---|---|---|
   | `qlsx_api` | `EPL_QLSX_API` | địa chỉ hệ của anh |
   | `qlsx_client_id` | `EPL_QLSX_CLIENT_ID` | lấy và làm mới access token (câu hỏi 10.1) |
   | `qlsx_client_secret` | `EPL_QLSX_CLIENT_SECRET` | như trên |

   Chiều anh gọi sang bên em thì dùng khoá `token_nhan_qlsx`.

2. **Danh tính máy có phạm vi.** Hiện nay các đường LAO cho bên kế toán gọi chỉ kiểm khoá máy và một tên đăng nhập bất kỳ. Tên đó có thể là tài xế.

   Bên em sẽ thêm **tài khoản dịch vụ** `qlsx` với danh sách đường được gọi, rồi kiểm cả hai. `X-Nguoi-Dung` khi đó chỉ để ghi vết: ai bên anh bấm.

3. **Lỗi nghiệp vụ:**
   - Thân lỗi dạng `{"code" hoặc "ma", "message" hoặc "loi"}`, kèm mã HTTP đúng nghĩa.
   - LAO **in nguyên câu lỗi** lên màn của kế toán bên em, nên câu lỗi phải là câu người đọc hiểu.
   - Tài liệu SO của anh đã theo đúng cách này.

4. **Chống trùng:** mọi lời gọi GHI đều có khoá ổn định (mục 3.1 và 3.2). Gửi lại cùng khoá và cùng nội dung thì trả kết quả cũ.

### 2.3. Luật "hai bên không bao giờ lệch số" (phải giữ)

**Hiện trạng 01/10:** hệ anh **không ghi bản chép nào** sang LAO. LAO là bên hỏi lại: đọc `STATUS` của phiếu chi / thu bên anh (12.10) và số đã thu của SO (12.11.2), rồi tự ghi trạng thái phía mình. Phiếu bên anh đã ghi sổ thì LAO không xoá, không sửa. Thứ tự dưới đây là luật bản tạm từng dùng; giữ lại để áp dụng nếu sau này hệ anh gọi sang LAO để ghi.

Mọi thao tác tiền có bản chép sang phiếu bên LAO đều đi đúng thứ tự. Bản tạm làm ở `services/doanh_thu.py:chot`, dòng 112:

1. Bên kế toán ghi dòng của mình và sinh chứng từ, **chưa commit**.
2. Bên kế toán gọi đường ghi bên LAO (mục 4). LAO kiểm lại điều kiện với dòng phiếu bị khoá `FOR UPDATE`, rồi commit.
3. Bên kế toán commit.
4. Nếu commit ở bước 3 hỏng: rollback, rồi gọi **đường bù** để đưa bản chép bên LAO về đúng số đang lưu. Bù hỏng thì ghi log.

LAO tắt ở bước 2 thì bên kế toán báo 503 và **không lưu gì**.

---

## 3. Đường LAO → hệ của anh

### 3.1. Đẩy chứng từ — `POST /api/v1/epl-lao/vouchers` (đã thôi gửi từ 01/10)

**Hiện trạng.**
- Mỗi bước nghiệp vụ vẫn ghi một tờ vào bảng `chung_tu` của LAO (loại tờ ở mục 7), để in, xem và hiện định khoản ở màn Quy trình.
- LAO **không gửi tờ nào** đi đâu nữa. Trước 01/10 các tờ được đẩy sang trang kế toán tạm; trang đó nay bỏ phần tiền (0.1), còn hệ anh **không có** cửa `/api/v1/epl-lao/vouchers`. Mã gửi (`services/day_ke_toan.py`) không còn lời gọi HTTP nào; còn một đường giữ chỗ `POST /api/chung-tu/day` (trả tóm tắt rỗng, cho công cụ gieo mẫu); `POST /api/chung-tu/{cid}/day` và `GET /api/ke-toan/trang-thai` đã xoá (`938b007`).
- Cờ `da_day` của tờ chỉ còn nghĩa "bên kế toán đã nhận / đã đối chiếu", đánh tay qua `POST /api/chung-tu/{id}/da-day`.

**Tiền đi đường nào thay cho phong bì:**
- đề nghị thu → SO (3.2);
- khoản đi qua tiền → phiếu chi / phiếu thu bên anh (12.10, 12.11.3; chi mục V – VI, tất toán, trả nhà cung cấp — mục 5);
- khoản không qua tiền → bút toán chờ gửi ở LAO, gửi qua API bút toán tổng hợp bên anh khi bật cờ (mục 8, 12.12.4).

**Đề nghị:** hệ anh **không cần** dựng cửa nhận phong bì. Câu hỏi 10.13 đã chốt theo cách (2): mỗi loại đi một đường của anh.

### 3.2. Phiếu đề nghị thu (PDT) → `POST /api/v1/integrations/logistics/sales-orders` (API anh đã có)

**Ý nghĩa:**
- Xe về, có biên bản giao nhận hàng (POD), kế toán Viêng Chăn **khoá phiếu**. Lúc đó LAO sinh **phiếu đề nghị thu**.
- Một PDT tương ứng một SO và một khoản công nợ bên anh. Hoá đơn và thu tiền khách làm ở hệ anh, từ SO.
- **Cắt sổ 01/10:** mọi DO đã khoá gửi SO từ đầu, kể cả DO từng có hoá đơn / lần thu trên trang kế toán tạm (số thử).

**PDT bên em** (`services/de_nghi_thu.py`):
- Sinh lúc khoá phiếu (`routes/phieu.py:khoa_phieu`, vai `acct` hoặc `admin`). Điều kiện là `transport_status = "arrived"`.
- `tien` = doanh thu theo tiền cước (`price_ccy`). `tien_lak` = doanh thu quy Kíp theo tỷ giá khoá trên phiếu.
- **Mở khoá** (`routes/phieu.py:mo_khoa_phieu`) chỉ xét những gì đã sang hệ anh, không xét cờ hoá đơn của trang tạm nữa:
  - DO đã có SO bên anh → 409 `DA_TAO_SO`; chỉ Sếp mở, sau khi báo anh;
  - lần gửi SO trước chưa rõ kết quả hoặc xung đột → 409 `SO_CHUA_RO`: gửi lại (cùng gói, cùng khoá) hoặc đối soát rồi mới mở;
  - phiếu đang nằm trong đề nghị trả chủ xe đã gửi / đã chi → chặn.
  - Chưa có SO thì tờ PDT bị rút; khoá lại thì sinh tờ mới theo số mới. Bút toán chờ của phiếu (thuê xe, ghi nợ nhà cung cấp) chưa gửi thì huỷ, đã gửi thì đánh "cần đảo".
- Phiếu **gom** (mỏ về bãi) cũng sinh PDT, vì gom có cước riêng (chủ dự án xác nhận).
- Trạng thái hiện trên màn (`services/de_nghi_thu.py`): `cho_khoa` → `chua_lap` / `cho_gui` → `da_tao_so` → `thu_mot_phan` → `da_thu`. "Đã tạo SO" theo lần gửi SO; hai trạng thái cuối **bên em đọc lại** từ `sales/debt/customer-detail`, ghép theo `OrderCode` của SO (12.11.2). Hệ anh không phải gửi gì về.

**Ánh xạ sang khuôn SO của anh:**

| Trường SO | Luật của anh | Lấy từ bên em | Tình trạng |
|---|---|---|---|
| gốc | chỉ `schemaVersion`, `header`, `details` | gói riêng cho PDT, dựng từ gói bàn giao DO (không dùng phong bì 3.1) | **đã làm 01/10** |
| `header.do_id` | ≤ 100, ASCII, duy nhất toàn bảng | **`EPLLAO-<Trip.id>`** (Trip.id là 12 ký tự hex). Không dùng số phiếu `T4-0428-08/EPL`, vì có dấu `/` | **đã làm** |
| `header.status` | `delivered` | phiếu đã về (`arrived`) **và** đã khoá | ổn |
| `header.customer_id` | = `PUBOBJECT.OBJ_OBJECTNO`, ≤ 50, mở đầu chữ / số, chỉ chữ, số, `_ . -` | ô **"Mã khách (bên kế toán)"** trên danh mục khách (có từ 30/09; chỉ `acct` và Sếp gán). Danh mục chặn mã trái luật và mã dài hơn 37 ký tự (ghép với mã tuyến ≤ 50, 12.9.1). Khách chưa có mã bên anh thì bên em tạo khách `EPLKH-…` qua `master-data/customers/upsert` rồi ghi mã (12.11.1) | **đã làm** |
| `header.route.id` / `name` / `distance_km` | ≤ 50, ASCII | `Trip.route_id` (hex 12) / tên tuyến / `total_km`. Phiếu không có tuyến thì chặn gửi và báo rõ | **đã làm** |
| `header.currency` = `currency_thu` | `VND` · `LAK` · `USD` | tiền cước `price_ccy` ∈ `LAK USD THB VND CNY` | **cước THB, CNY chưa gửi được** — câu hỏi 10.3 |
| `header.selling_price` = `final_selling_price` | > 0.01 | doanh thu (tấn × đơn giá, hoặc trọn chuyến) | **đã làm**: chặn khi ≤ 0,01; tổng khớp bằng Decimal |
| `header.customer_surcharge_total` | ≥ 0 | `0` (bên em không có phụ thu khách) | ổn |
| `header.billed_qty` | snapshot | tấn tính cước | có |
| `details[]` | có dòng `thu`, Σ thu = tổng | một dòng `{"line_no": 1, "kind": "thu", "name": "Cước vận chuyển <số phiếu> · <tấn> t × <đơn giá> <tiền>", "actual_amount": doanh thu, "currency": tiền cước}` | **chốt một dòng thu**: mã của anh chỉ ghép dòng `chi` thành chữ trên SO của khách (12.9.1, điều 1) |
| `origin` · `destination` · `trip_id` · `vehicle_id` · `driver_id` · `weight_kg` · `pod_receiver` · `pod_signed_at` | nên có | có đủ (`weight_kg` = tấn × 1000; `pod_signed_at` thêm `+00:00`) | có |
| `Idempotency-Key` | ổn định cho một DO | **`logistics:EPLLAO-<Trip.id>`**. Bên em **lưu nguyên gói đã gửi** (bảng `gui_so_tune`) để thử lại đúng gói | **đã làm** |
| `Authorization` | token QLSX, có làm mới | `QLSX_ACCESS_TOKEN` → tự đăng nhập (`QLSX_USERNAME` / `QLSX_PASSWORD`) → `EPL_ACC_CODE_TOKEN` (2.1). Đang dùng token cá nhân `tune`, hết hạn 10/10/2026 | **đã làm**; hết hạn thì thay token hoặc đặt tài khoản anh để tự đăng nhập (12.11.4) |

Gói đề nghị:

```http
POST {QLSX_BASE_URL}/api/v1/integrations/logistics/sales-orders
Authorization: Bearer <QLSX_ACCESS_TOKEN>
Content-Type: application/json
Idempotency-Key: logistics:EPLLAO-a1b2c3d4e5f6
```

```json
{"schemaVersion": 1,
 "header": {"do_id": "EPLLAO-a1b2c3d4e5f6", "status": "delivered", "customer_id": "<OBJ_OBJECTNO>",
            "route": {"id": "9e8d7c6b5a41", "name": "ມໍ່ກາສີ → ທ່າບົກ", "distance_km": 182},
            "currency": "USD", "currency_thu": "USD", "currency_chi": "LAK",
            "selling_price": 1025.5, "customer_surcharge_total": 0, "final_selling_price": 1025.5, "billed_qty": 41.02,
            "origin": "ມໍ່ກາສີ", "destination": "ທ່າບົກ", "trip_id": "a1b2c3d4e5f6", "vehicle_id": "341",
            "driver_id": "d0c0ffee0001", "weight_kg": 41020, "pod_receiver": "…", "pod_signed_at": "2026-09-29T02:40:00+00:00"},
 "details": [{"line_no": 1, "kind": "thu", "name": "Cước vận chuyển T4-0428-08/EPL · 41.02 t × 25 USD",
              "actual_amount": 1025.5, "currency": "USD"}]}
```

**Bên em sẽ xử lý câu trả lời của anh như sau:**

| Anh trả | Bên em làm |
|---|---|
| 201 `{"replayed": false, "data": {"orderId", "orderCode", "retkCode", "debtId", "totalAmount", "currency", …}}` | đánh PDT **đã gửi**, lưu `orderCode`, `orderId`, `retkCode`, `debtId`, `totalAmount`, `currency` |
| 200 `replayed: true` | như trên |
| **409 `LOGISTICS_52901`** (trùng mà khác) | **báo lỗi, không coi là thành công**, kế toán hai bên đối soát |
| 400 · 401 · 403 · 422 | ghi câu lỗi lên tờ, người dùng sửa |
| 422 `LOGISTICS_52903` · 503 · hết giờ | **thử lại đúng gói và đúng khoá đã lưu**, không dựng gói mới |

#### 3.2.1. Đã dựng và chạy (01/10/2026)

**Bên em đã dựng:**

- Màn **Phiếu đề nghị thu** có nút **"Tạo SO bên kế toán"**. Chỉ KT Thu/Chi Viêng Chăn (vai `acct`, người khoá phiếu) và Sếp (`admin`) bấm được; máy chủ chặn vai khác (403 `KHONG_CO_QUYEN`).
- Hai đường bên trang điều xe:
  - `GET /api/trips/{trip_id}/tao-so`: dựng và kiểm gói **không gọi sang hệ anh**; lỗi dữ liệu trả trong `loi`; khách chưa có mã thì báo trước mã sẽ tạo;
  - `POST /api/trips/{trip_id}/tao-so`: tạo khách nếu chưa có (`EPLKH-<mã khách bên em>`, 12.11.1), rồi gửi thật.
- Máy chủ bên em gọi `POST {gốc}/api/v1/integrations/logistics/sales-orders` bằng token ở máy chủ (2.1), giống bộ gửi của EPL_System. Token không xuống trình duyệt.
- Gói gửi đúng khuôn ở trên:
  - ba khoá gốc `schemaVersion`, `header`, `details`;
  - `header.customer_id` = ô **Mã khách** trên danh mục khách bên em;
  - **một dòng thu** (cước);
  - không gửi các khối `hire`, `fx_rates_on_trip`, `cost_by_section_lak`.
- Bên em kiểm trước khi gửi:
  - DO đã về và đã khoá;
  - khách đã có mã (sau bước tạo khách);
  - có tuyến;
  - mã ghép `khách_tuyến` ≤ 50 ký tự;
  - tiền là VND / LAK / USD;
  - tổng khớp chính xác bằng Decimal.
- **Không còn chặn theo trang kế toán tạm**: cắt sổ 01/10, mọi DO đã khoá gửi SO từ đầu.
- Mỗi DO lưu **một** bản ghi lượt gửi (bảng `gui_so_tune`), gồm:
  - nguyên gói đã gửi, khoá `logistics:EPLLAO-<Trip.id>`;
  - mã HTTP và thân trả về;
  - `orderCode`, `retkCode`, `totalAmount`… khi thành công;
  - số đã thu / còn nợ đọc lại từ `customer-detail` (12.11.2).
- Kết quả **chưa rõ** (mất mạng, hết giờ, 5xx, `52903`) thì lần sau bên em gửi lại **đúng gói, đúng khoá**. Bị từ chối rõ ràng (4xx dữ liệu) thì dựng gói mới theo số hiện tại.
- DO đã có SO thì kế toán bên em **không mở khoá được** (409 `DA_TAO_SO`); chỉ Sếp mở, sau khi báo anh.

**Đã chạy** qua API của anh chạy ở máy (DB của `appsettings.laos.json`):

| SO | DO | Khách | Tiền |
|---|---|---|---|
| `TK-20261001-000162` | T4-0449-09/EPL | ຄຳຕຸ້ຍ (`EPLKH-0834a9e9606b`) | 905,85 USD |
| `TK-20261001-000163` | T4-0442-09/EPL | ນາງ ວັນນາ | 1.676,90 USD |

Hai SO này tạo ngày 01/10 trước giờ cắt sổ, **giữ nguyên**, là công nợ thật của hai DO đó.

Lưu ý: SO hiện vào chi nhánh cố định **1368 "Demo EPL"** (quốc gia Việt Nam, tiền VND). Dùng thật cho Lào thì cần đơn vị EPL Lào (mục 12.7.5) — **cần quyền host**.

**Những thứ API SO chưa có mà bên em cần** (câu hỏi 10.5):
- sửa hoặc huỷ SO khi Sếp mở khoá phiếu;
- **hoá đơn gộp tháng** cho khách chọn nhận một hoá đơn cả tháng (mục 6.5);
- đường đọc trạng thái theo DO (hiện bên em đọc `customer-detail` theo khách rồi ghép `OrderCode`).

### 3.3. Danh mục tài khoản — `GET {EPL_ACC_CODE_API}/api/v1/common/country-accounts?tryAutoId=11&onlyActive=true`

- **Đang dùng.** Bên em gọi kèm `Authorization: Bearer <EPL_ACC_CODE_TOKEN>`, hết giờ 20 giây, giữ bộ nhớ 10 phút.
- Bên em đọc `Result[]`, lấy các trường `AccCode`, `AccName`, `AccDescription`, `AccParentId`, `AccAccountWrite` (ghi sổ được), `AccIsActive`.
- Không nối được thì bên em dùng **bản chụp ngày 01/10** (497 mã, đã có 1371, 4021, 4022).
- Nếu danh mục của EPL Lào khác danh mục chung của quốc gia 11 (ví dụ danh mục riêng theo công ty), anh cho tham số. Bên em chỉ đổi cấu hình.

### 3.4. Công nợ một khách — `POST /api/v1/sales/debt/customer-detail` (đang dùng)

- **Dùng ở:** màn *Khách hàng → tab Công nợ*, khối **"Công nợ bên hệ kế toán"**, chỉ xem; và trạng thái thu của phiếu đề nghị thu (3.2, 12.11.2).
- Đường cũ của trang kế toán tạm (`GET /api/lien-thong/doanh-thu/khach/{cid}`) là số thử từ 01/10, không dùng làm công nợ.
- **Đề nghị:** một đường đọc trạng thái theo DO (câu hỏi 10.5). Bên em chỉ hiện, không tính lại.

### 3.5. Cấn trừ cuối tháng

- Cấn trừ là việc của hệ anh (6.6). Số cấn trừ đã ghi ở trang kế toán tạm (`ref = CT-YYYYMM`) là số thử, không mang sang.
- Báo cáo cấn trừ cước bên em chỉ tính số trên phiếu (thẻ cao tốc khách cấp, dầu trạm Việt Nam ghi nợ); số cấn trừ đã ghi sổ là của hệ anh.

---

## 4. Đường hệ của anh → LAO (bên em cung cấp)

**Hiện trạng 01/10:** hệ anh chỉ cần **đọc DO** qua hai đường bàn giao (12.8):

- `GET /api/handover/delivery-orders` — danh sách DO đã về + đã khoá, có `q` tìm trên toàn bộ DO;
- `GET /api/handover/delivery-orders/{do_id}` — header + details một DO.

Xác thực bằng **khoá bàn giao** riêng cho hệ anh (12.8.1). Phía anh đọc qua `LogisticsSource` (12.9.2).

**Hệ anh không cần ghi gì sang LAO.** Trạng thái tiền do LAO tự hỏi lại hệ anh:

| Trạng thái trên màn LAO | LAO đọc ở hệ anh |
|---|---|
| tạm ứng "đã chi", tài xế được xuất phát | `GET …/cmpayment-receipt/{id}` của phiếu "Chi trước": `Master.STATUS` 12/13 (12.10) |
| phiếu xe "đã trả chủ xe" | như trên, phiếu "Chi khác" trả chủ xe (12.11.3) |
| mục V – VI "đã chi", tất toán "xong", trả nhà cung cấp | như trên |
| đề nghị thu "thu một phần / đã thu" | `sales/debt/customer-detail`, ghép `OrderCode` (12.11.2) |

**Nhóm `/api/lien-thong/*`:** phần tiền **đã gỡ 01/10** cùng với phần tiền của trang kế toán tạm. Các đường bản chép và đọc số trước đây ghi ở mục này — báo đã xuất / bỏ hoá đơn, đã thu, đã trả / bỏ trả chủ xe; đọc cước, chủ xe chờ trả, xe liên kết, tiền tài xế trả cùng lương, tất toán, nhà cung cấp, cấn trừ, tháng mới nhất, người mua ở quầy — **không còn**. Còn lại các đường **kho** cho trang tạm (kho tạm: điểm đổ, phụ tùng, cấp phát nhiên liệu, xe, sửa chữa) và hai đường tra cứu `GET /api/lien-thong/ty-gia`, `GET /api/lien-thong/ma-ke-toan`. Hệ anh không dùng nhóm này.

**Khi nào cần lại đường ghi sang LAO:** nếu sau này hệ anh muốn **đẩy** trạng thái thay vì để LAO hỏi lại (ví dụ khi trang điều xe ra Internet), bên em dựng đường mới theo luật 2.3 và tài khoản dịch vụ có phạm vi (2.2).

---

## 5. Một DO đi qua tiền — ai lập tờ gì, tiền đi đâu

| # | Bước | Ai bấm | Tờ | Định khoản | Sang hệ anh bằng |
|---|---|---|---|---|---|
| 1 | Lập phiếu xuất xe | Bãi | `DO` | không | hệ anh **đọc** qua bàn giao DO (12.8) |
| 2 | In phiếu **đề nghị tạm ứng** | Bãi / kế toán | `PTU` | không | — |
| 3 | In phiếu **đề nghị xuất kho nhiên liệu** (mỗi kho một tờ) | Bãi / kế toán | `PLNL` | không | không sang anh Tune: kho (kho tạm, sau là hệ anh Toàn) |
| 4 | Chi tạm ứng: KT Chi phí VC ghi sổ mục IV → **thủ quỹ bên anh** chi và ghi sổ | KT Chi phí · thủ quỹ bên anh | phiếu chi "Chi trước" bên anh | xe nhà **1601/1011** · xe thuê **4022/1011** | phiếu chi bên anh — **chạy** (12.10) |
| 5 | Thủ kho cấp dầu theo đề nghị | Thủ kho (kho tạm / anh Toàn) | `PXK_NL` | xe nhà 625/1371 · xe thuê 4022/707 (giá bán) + 607/1371 (giá vốn) — ghi lúc khoá phiếu (bước 7) | kho; bút toán sang anh qua bút toán chờ `xuat_noi_bo` / `xuat_ban` |
| 6 | Chi mục V – VI trả ngay: KT Chi phí VC ghi sổ mục → **thủ quỹ bên anh** | KT Chi phí · thủ quỹ bên anh | `PC_SC` → phiếu chi "Chi khác" bên anh | xe nhà 614 (V) · 625 (VI) / 1011 · xe thuê 4022/1011 | phiếu chi bên anh — **chạy** |
| 7 | Xe về, kế toán Viêng Chăn **khoá phiếu** | kế toán | **`PDT`** | không | SO + công nợ (3.2) — **chạy**. Cùng lúc: xe thuê ghi **bút toán chờ** 621/4022; dòng ghi nợ nhà cung cấp ghi **bút toán chờ** 625 · 614 / 4021; mỗi lần xuất kho dầu / phụ tùng cho chuyến ghi **bút toán chờ** `xuat_noi_bo` (xe nhà) / `xuat_ban` (xe thuê) (mục 8, 12.12.4) |
| 8 | Xuất hoá đơn (từng phiếu hoặc gộp tháng) | kế toán bên anh | `HD` | **1211/708** | việc của hệ anh, từ SO |
| 9 | Ghi một lần khách trả | kế toán bên anh | `PT` | tiền/1211 | việc của hệ anh; LAO đọc "đã thu" (12.11.2) |
| 10 | Cấn trừ cuối tháng | kế toán bên anh | `PT` (`offset`) | xem lỗ hổng 5 | việc của hệ anh |
| 11 | Trả chủ xe liên kết: KT Thu/Chi lập đề nghị → **thủ quỹ bên anh** | KT Thu/Chi · thủ quỹ bên anh | `PC_CX` → phiếu chi "Chi khác" bên anh | 4022/tiền | phiếu chi bên anh — **chạy** (12.11.3); số trả đã trừ hàng quầy, hàng bán ghi **bút toán chờ** 4022/707 |
| 12 | Tất toán tài xế theo tháng: KT Chi phí VC chốt kỳ | KT Chi phí · thủ quỹ bên anh | `QT_TU` + `TT_CHI` / `TT_THU` | **625/1601** · **1601/1011** · **1011/1601** | `QT_TU` → **bút toán chờ**; chênh → phiếu chi "Chi khác" / phiếu thu "Thu khác" bên anh — **chạy** |
| 13 | Trả nhà cung cấp: KT Chi phí lập đề nghị → **thủ quỹ bên anh** | KT Chi phí · thủ quỹ bên anh | `PC_NCC` → phiếu chi "Chi khác" bên anh | 4021/tiền | phiếu chi bên anh — **chạy** |

- Theo chốt 29/09 và 01/10, bên em chỉ gửi **đề nghị** và đọc trạng thái về. Mọi bước chi / thu tiền thật làm ở hệ anh.
- Quỹ trên trang điều xe không chi mục IV nữa (409 `CHI_O_KE_TOAN`); Sếp chi tay chỉ là đường dự phòng (12.10.2).
- Số tiền các bước 8 – 13 đã ghi trên trang kế toán tạm trước 01/10 là **số thử, bỏ hết**.

---

## 6. Luật nghiệp vụ phải giữ nguyên

### 6.1. Tiền tệ theo chứng từ

- Tiền hợp lệ: `LAK USD THB VND CNY`.
  - Cước tính theo `price_ccy` (mặc định USD).
  - Tiền thuê chủ xe tính theo `hire_ccy` (trống thì cùng tiền cước).
  - Mỗi dòng chi mang `currency` riêng, quy LAK rồi mới cộng.
- Làm tròn: LAK và VND làm tròn đơn vị; tiền khác giữ 2 số lẻ.
- Tờ `HD` mang **tiền cước**. Tờ `PT` mang **tiền của lần thu**, có thể khác tiền hoá đơn: hoá đơn USD mà khách trả Kíp là chuyện thường ở đây. Tờ `PT` gửi kèm:
  - `rate_to_lak` của ngày thu;
  - `hoa_don_ccy`, `hoa_don`, `hoa_don_lak` để đối chiếu.

  **Chênh lệch tỷ giá bên em chưa hạch toán — để anh quyết** (câu hỏi 10.8).
- Sổ ghi bằng Kíp = `amount.lak` bên em đã quy theo tỷ giá **khoá trên phiếu**.

### 6.2. Khối tính tiền của một phiếu (`services/tinh_toan.py:tinh_phieu`)

**Ký hiệu:** `w` = cân tại nơi giao (chưa cân thì lấy cân lúc đi). Phiếu "trọn chuyến" (`price_mode = "chuyen"`) thì không nhân tấn.

| Khoá | Công thức |
|---|---|
| `doanh_thu` | `price` (trọn chuyến) hoặc `w × price`, làm tròn theo tiền cước |
| `doanh_thu_lak` | `round(doanh_thu × tỷ giá phiếu)` |
| `chi{fuel, travel, repair, other}` | LAK. Xe thuê chỉ tính dòng **EPL ứng**. Đơn giá dòng = **giá bán** nếu là **xuất bán** (xe thuê, dầu mục III hoặc phụ tùng mục V lấy kho), không thì giá dòng |
| xe nhà `lai_lak` | `doanh_thu_lak − tong_chi_lak` |

**Xe liên kết** (`company = "joint"`) có thêm:

| Khoá | Công thức |
|---|---|
| `tien_thue` | `w × giá thuê` (hoặc trọn chuyến), theo `hire_ccy` |
| `phi` | `tien_thue × fee_pct / 100` (mặc định 2 %) |
| `tru_vuot` | `max(0, w − over_limit_t) × over_price` (mặc định ngưỡng 40 t, 1 đơn vị/tấn) |
| `ung_truoc` | **mọi khoản EPL ứng** quy về `hire_ccy`: tiền mặt tài xế, dầu và phụ tùng kho **theo giá bán**, dầu trạm ghi nợ, khoản ghi nợ nhà cung cấp, sửa ngoài |
| **`tra_chu_xe`** | **`tien_thue − phi − tru_vuot − ung_truoc`** |

Ví dụ: 41,02 t · thuê 20 USD/t · phí 2 % · ngưỡng 40 t × 1 USD · EPL ứng 2.780.000 LAK · tỷ giá 22.000. Kết quả:

- `tien_thue` = 820,40
- `phi` = 16,41
- `tru_vuot` = 1,02
- `ung_truoc` = 126,36
- **`tra_chu_xe` = 676,61 USD** (14.885.420 LAK)

Đề nghị trả chủ xe bên em lấy đúng số `tra_chu_xe` này, không gõ tay, rồi **trừ hàng chủ xe mua ở quầy**: số trả thực = Σ `tra_chu_xe` − Σ phiếu bán chờ trừ (phiếu bán ở kho tạm, 12.11.3). Hàng bán ghi bút toán chờ Nợ 4022 / Có 707 khi phiếu chi trả chủ xe đã chi.

### 6.3. Tạm ứng và tất toán tài xế — đổi ngày 30/09 cho đúng luật

- **Tiền mặt tài xế cầm đi** là các dòng thoả đủ:
  - EPL ứng, không lấy kho;
  - thuộc mục III, IV hoặc VI;
  - không ghi nợ trạm, không trừ thẻ cao tốc;
  - với mục IV và VI: cách trả là *chi ngay khi xe đi*.
- **Xe nhà.** Tiền ứng là **tạm ứng nhân viên**, chưa phải chi phí:
  - quỹ chi → `PC_TU` Nợ **1601** / Có 1011;
  - cuối tháng tất toán → `QT_TU` Nợ **625** / Có **1601**, theo **số tài xế đã chi thật**;
  - chi thật > ứng → `TT_CHI` Nợ 1601 / Có 1011;
  - chi thật < ứng → `TT_THU` Nợ 1011 / Có 1601.

  Sau tất toán, số dư 1601 của tài xế về 0. Trước ngày 30/09 bản tạm ghi thẳng tạm ứng vào 625, tức là tiền chưa tiêu đã thành chi phí.
- **Xe thuê.** Tiền EPL ứng là **công nợ chủ xe**: `PC_TU` Nợ **4022** / Có 1011, trừ vào tiền trả chủ xe. Xe thuê **không vào tất toán tài xế**.
- **Trả cùng lương** (tiền chuyến, tiền nước của xe nhà) là **phải trả nhân viên 4201**.

### 6.4. Phiếu đề nghị thu

Xem mục 3.2 và 3.2.1. Mã bên em (`services/gui_tune.py:dung_goi`) chỉ gửi khi đủ các điều kiện sau:

- phiếu **đã về và đã khoá**;
- khách **có mã bên kế toán**, mã hợp lệ;
- phiếu **có tuyến**; mã ghép `khách_tuyến` ≤ 50 ký tự;
- cước là **VND, LAK hoặc USD** và **> 0,01**.

Khoá phiếu hiện chỉ **cảnh báo** (người khoá xem rồi xác nhận) chứ không bắt buộc mục II đã kiểm. Bên em **chưa chặn** gửi SO theo mục II. Anh cần chặn thì bên em thêm.

### 6.5. Hoá đơn gộp tháng

- Khách có `invoice_mode = "thang"` nhận **một hoá đơn cả tháng**. Khách `phieu` nhận hoá đơn từng phiếu.
- Một tờ gộp = **một khách × một tháng × một tiền cước**. Số tờ dạng `HDT-YYYYMM-NN`.
- Thu ở tờ gộp thì **rải xuống từng phiếu**: phiếu cũ trước, phần thừa dồn vào phiếu cuối.

### 6.6. Cấn trừ cuối tháng

- "Khách trả hộ EPL" gồm hai khoản:
  - (a) EPL quẹt thẻ cao tốc **do khách cấp**;
  - (b) dầu **ghi nợ** tại trạm Việt Nam mà trạm tính vào tiền của khách.
- Ghi thành `PT` với `method = "offset"`, `ref = "CT-YYYYMM"`, bằng LAK. Bù vào hoá đơn cũ trước.
- Không ghi thu dư: phần thừa để sang tháng sau.

### 6.7. Ai thấy tiền (`services/phan_quyen.py`)

| Luật | Không thấy |
|---|---|
| tiền **bán** (cước, doanh thu, giá thuê xe, trả chủ xe, lãi, giá bán dầu và phụ tùng cho chủ xe) | Bãi, tài xế, thủ kho nhiên liệu, thủ kho phụ tùng, tổ sửa chữa |
| tiền **chi** (đơn giá, thành tiền, tỷ giá) | Bãi |
| **giá vốn kho** | Bãi, thủ kho nhiên liệu, thủ kho phụ tùng, tổ sửa chữa |

- Số anh trả về (công nợ, đã thu…) bên em cho qua cùng cổng này trước khi hiện.
- Các màn của hệ anh áp cùng luật — bên EPL làm (đang làm).

---

## 7. Danh mục loại chứng từ và định khoản (sau đợt rà 30/09)

### 7.1. Bảng

| `type` | Tên | Nhóm | Nợ | Có | Tiền của tờ |
|---|---|---|---|---|---|
| `DO` | Phiếu xuất xe · đề nghị xuất xe | other | — | — | không |
| `PLNL` | Phiếu đề nghị xuất kho nhiên liệu | other | — | — | không (lít trong `lines`) |
| `PTU` | Phiếu đề nghị tạm ứng | other | — | — | LAK |
| `PDT` | Phiếu đề nghị thu | receipt_request | — | — | tiền cước |
| `PC_TU` | Phiếu chi theo đề nghị tạm ứng | payment | xe nhà **1601** · xe thuê **4022** | 1011 | LAK |
| `PC_SC` | Phiếu chi sửa chữa · chi khác | payment | xe nhà 614 · xe thuê 4022 | 1011 | LAK |
| `PC_NCC` | Phiếu chi trả nhà cung cấp | payment | 4021 | tiền | LAK |
| `PC_CX` | Phiếu chi trả chủ xe liên kết | payment | 4022 | tiền (theo cách chi × `hire_ccy`) | `hire_ccy` |
| `HD` | Hoá đơn vận chuyển | invoice | 1211 | **708** | tiền cước |
| `PT` | Phiếu thu tiền khách | receipt | tiền (theo cách thu × tiền lần thu) | 1211 | tiền lần thu |
| `QT_TU` | Quyết toán tạm ứng tài xế (**mới**) | settlement | **625** | **1601** | LAK |
| `TT_CHI` | Tất toán tài xế · chi bù | payment | **1601** | 1011 | LAK |
| `TT_THU` | Tất toán tài xế · thu hoàn | receipt | 1011 | **1601** | LAK |
| `PXK_BAN` | Xuất kho bán hàng ở quầy | stock_out | 607 | 1371 | LAK giá vốn |
| `HD_BAN` | Hoá đơn bán hàng | invoice | 1211 (người mua là chủ xe: **4022**, trừ vào tiền trả) | **707** | tiền bán |
| `PT_BAN` | Phiếu thu bán hàng | receipt | tiền | 1211 | tiền bán |
| tờ kho `PXK_NL`, `PXK_PT`, `PNK_*`, `CK_NL`, `*_HH` | (hệ kho anh Toàn sinh) | stock_* | xem hợp đồng kho, mục 9 | | |

**Vế tiền:**

| Cách thu / chi | Kíp | Ngoại tệ |
|---|---|---|
| tiền mặt | 1011 | 1012 |
| ngân hàng | 1021 | 1022 |

Cách `offset` và `other` hiện xếp vào ngân hàng — xem lỗ hổng 5.

### 7.2. `lines` từng loại (đúng mã dựng hiện nay)

| `type` | `lines` |
|---|---|
| `DO` | `{truck_no, driver_name, company}` |
| `PTU` | `{voucher_id, doc_no, hinh_thuc, owner_id, owner_name}` |
| `PLNL` | `{voucher_id, doc_no, qty_l, hinh_thuc, owner_id, owner_name}` |
| `PDT` | `{doc_no, kind, company, owner_name, customer_id, customer_name, contract_no, origin, destination, goods_type, truck_no, plate_head, plate_trailer, driver_name, out_date, back_date, weight_origin, weight_dest, tan_tinh, cach_tinh, don_gia, ccy, rate_to_lak, doanh_thu, doanh_thu_lak, pod_no, pod_date, pod_receiver, pod_signed, ore_bill_no}` |
| `PC_TU` (quét QR) | `{voucher_doc_no, driver_id, truck_no, hinh_thuc, owner_id, owner_name}` |
| `PC_TU` (bấm chi mục IV) | `{truck_no, driver_id, hinh_thuc, owner_id, owner_name, lines: [{item, qty, unit_price, currency, acct_code}]}` |
| `PC_SC` | `{lines: [{item, qty, unit_price, currency, acct_code}]}` |
| `HD` (từng phiếu) | `{tan_tinh, don_gia, currency, cach_tinh, rate_to_lak}` |
| `HD` (gộp tháng) | `{inv_no, period, currency, so_phieu, phieu: [{doc_no, doc_date, tan_tinh, don_gia, cach_tinh, thanh_tien, thanh_tien_lak, rate_to_lak}]}`, `trip_no = null` |
| `PT` | `{rate_to_lak, method, ref, hoa_don_ccy, hoa_don, hoa_don_lak}` (tờ gộp thêm `inv_no, period, phan_bo: [{doc_no, phan_bo_lak}]`) |
| `PC_CX` | `{phieu: [{doc_no, tien_thue, phi, tru_vuot, ung_truoc, tra_chu_xe}], currency, method, ref, note, gross, sales_deducted, ban_tru: [...]}` |
| `QT_TU`, `TT_CHI`, `TT_THU` | `{period, tong_ung_lak, tong_chi_lak, driver_id}` |
| `PC_NCC` | `{supplier_id, item_key, acct_code}` |
| `HD_BAN`, `PXK_BAN` | `{doc_no, rate_to_lak, lines: [{line_no, item_type, name, qty, unit_price, amount, part_id, place_id, cost_lak}], owner_id}` |

### 7.3. Định khoản GỢI Ý trên từng dòng chi của phiếu (`acct_code`)

- Mỗi dòng chi trên phiếu mang một cặp mã (hiện ở cột *Mã kế toán*, và đi theo `lines`).
- **Vế Có đi theo cách trả**, vì mỗi cách trả là một đối tượng nợ khác nhau:

| Dòng chi | Xe nhà | Xe thuê (liên kết) |
|---|---|---|
| III dầu lấy kho EPL | 625/1371 | **4022/707** (xuất bán, giá bán riêng) |
| III dầu trạm ngoài, trạm ghi nợ | 625/4021 | 4022/4021 |
| III dầu trạm ngoài, tài xế trả tiền mặt | **625/1601** | 4022/1011 |
| IV · VI tài xế cầm tiền mặt đi (tạm ứng) | **625/1601** | 4022/1011 |
| IV trả cùng lương | **625/4201** | (xe thuê không có) |
| IV · VI ghi nợ nhà cung cấp, trừ thẻ cao tốc | 625/4021 | 4022/4021 |
| V phụ tùng lấy kho | 614/1371 | **4022/707** (xuất bán) |
| V sửa ngoài, garage | 614/4021 | 4022/4021 |
| Chủ xe tự chi | không định khoản | không định khoản |

---

## 8. Lỗ hổng sổ của trang kế toán tạm — và cách làm đúng ở hệ anh

Bảy lỗ hổng dưới đây bên em thấy ở sổ của trang kế toán tạm. Từ 01/10 trang tạm **không còn phần tiền**, số ở đó là số thử (0.1); mục này ghi lại để hệ anh làm đúng, kèm **hiện trạng** bên em đã làm tới đâu. Chủ dự án dặn *"note lại cho anh Tune"*.

**Hai đường bên em dùng thay cho sổ tạm:**

- **khoản đi qua tiền** → phiếu chi / phiếu thu bên anh (12.10, 12.11.3; chi mục V – VI, tất toán, trả nhà cung cấp — mục 5);
- **khoản không qua tiền** → **bút toán chờ gửi** ở trang điều xe (bảng `but_toan_cho`, `services/but_toan_cho.py`; màn "Bút toán chờ gửi", `GET /api/but-toan-cho`):

  | Nguồn | Sinh lúc | Định khoản | Mã nguồn |
  |---|---|---|---|
  | `thue_xe` | khoá phiếu xe thuê | Nợ 621 / Có 4022, bằng tiền thuê (`hire.amount`) | `Trip.id` |
  | `no_ncc` | khoá phiếu có dòng ghi nợ nhà cung cấp | Nợ 625 · 614 (xe thuê 4022) / Có 4021, theo bảng 7.3 | `Trip.id` |
  | `tat_toan` | KT Chi phí VC chốt tất toán một tài xế một kỳ | `QT_TU` Nợ 625 / Có 1601, bằng số tài xế đã chi thật | mã bản chốt |
  | `ban_chu_xe` | phiếu chi trả chủ xe có trừ hàng quầy đã chi | Nợ 4022 / Có 707, theo giá bán | mã phiếu bán (kho tạm) |
  | `xuat_noi_bo` | khoá phiếu xe nhà có dầu / phụ tùng kho đã rời kho | xuất nội bộ: dầu Nợ 625 / Có 1371 · phụ tùng Nợ 614 / Có 1371, theo giá vốn bình quân kho | `dau:` · `pt:<mã lần xuất>` |
  | `xuat_ban` | khoá phiếu xe thuê (EPL ứng) có dầu / phụ tùng kho đã rời kho | xuất bán cho chủ xe: Nợ 4022 / Có 707 theo giá bán + Nợ 607 / Có 1371 theo giá vốn | như trên |

  - Mỗi bút toán đủ hai vế từng dòng, bằng mã thật trong danh mục (`services/tai_khoan.py`), kèm tiền tệ của dòng, đối tượng (chủ xe, nhà cung cấp, tài xế) và diễn giải.
  - Chống trùng theo (nguồn, mã nguồn). Mã gửi đi `source_ref` = `EPLLAO-<nguồn>-<mã nguồn>`; bản đã gỡ mà nguồn ghi lại thì phiên mới `…-2`.
  - Trạng thái `cho_gui` → `da_gui`; `huy`. Mở khoá phiếu: bản chưa gửi bị huỷ, khoá lại ghi theo số mới; bản đã gửi thì gửi **gỡ** sang bên anh (chưa gỡ được thì "chờ đảo").
  - Đường nhận bên anh: `integrations/logistics/journal-entries` (`b9227aa`, 12.12.4) — **đã chạy thật trên DB demo 02/10** (chủ dự án áp script; phiếu thử qua máy thử trang điều xe: thuê xe `GL021020263` / `GL021020264`, xuất kho `GL021020265` · `GL021020267`, ST 13; mở khoá gỡ sạch, GET 404); host chưa áp. Cờ gửi `QLSX_GUI_BUT_TOAN` chỉ bật trên máy thử lúc chạy lượt thật; máy chưa bật thì các bản nằm "chờ gửi", không mất khoản nào.

**Bảy lỗ hổng:**

1. **Tiền thuê xe liên kết chưa bao giờ ghi thành nợ phải trả chủ xe.**
   - Sổ tạm không có bút toán *Nợ chi phí thuê xe / Có 4022* cho `tien_thue`; 4022 chỉ có vế Nợ (tạm ứng xe thuê, chi mục V xe thuê, xuất kho cho xe thuê, chủ xe mua ở quầy, trả chủ xe). Trên sổ tạm 4022 **dư Nợ 41.610.300 LAK**, tức là sổ nói *chủ xe nợ EPL*, ngược thực tế.
   - **Đã chốt 01/10 (chủ dự án):** *Nợ **621** ຄ່າຂົນສົ່ງ – chi phí vận chuyển / Có **4022** phải trả chủ xe*, bằng `tien_thue`, lúc khoá phiếu. 621 khớp chữ "ຄ່າຂົນສົ່ງນອກ" của Excel; vế Có 402 trong Excel là mã cha của 4022. Bàn giao DO đưa cặp này ở `hire.acc_code` (12.8.3).
   - **Hiện trạng:** bút toán chờ nguồn `thue_xe` lúc khoá phiếu; gửi qua API bút toán tổng hợp bên anh khi bật cờ (12.12.4).
   - Phí 2 % và trừ quá tải chưa có tài khoản riêng (anh Khampla chốt). Phiếu có `tra_chu_xe ≤ 0` (chủ xe nợ ngược EPL) cũng cần chỗ ghi.

2. **Dầu và phụ tùng kho bán cho chủ xe ghi theo giá vốn (Nợ 4022 / Có 1371).** Đúng ra xuất bán phải tách hai bút toán:
   - *Nợ 607 / Có 1371* theo **giá vốn** — tờ kho, hệ anh Toàn;
   - *Nợ 4022 / Có 707* theo **giá bán** — tờ bán, hệ anh.

   Giá bán nằm trên phiếu bên em (dòng `sale_price`): dầu do KT kho xăng dầu gõ khi kiểm mục III; phụ tùng do KT Chi phí gõ khi kiểm mục V. Dòng chi bán cho chủ xe mang `acc_code = "4022/707"` trong bàn giao DO.

   **Hiện trạng:** hàng chủ xe mua ở quầy (phiếu bán ở kho tạm) được trừ vào tiền trả chủ xe; khi phiếu chi trả chủ xe đã chi, bên em ghi bút toán chờ nguồn `ban_chu_xe` *Nợ 4022 / Có 707* theo giá bán, một phiếu bán một bút toán. Dầu / phụ tùng kho xuất cho chuyến trên phiếu (mục III, V): **chủ dự án chốt 01/10** ("xuất dầu là xuất nội bộ và còn là xuất bán") — lúc khoá phiếu, mỗi lần xuất kho thành một bút toán chờ: xe nhà `xuat_noi_bo` (625 · 614 / 1371 theo giá vốn), xe thuê `xuat_ban` (4022/707 theo giá bán + 607/1371 theo giá vốn) — lấy kho EPL cho xe thuê luôn là xuất bán, không có "chủ xe tự trả"; thiếu giá bán thì không khoá được (12.12.4).

3. **Nợ nhà cung cấp trên sổ tạm cộng theo khoản mục, không xét cách trả.** Hệ quả: dòng chipping đổi sang tiền mặt vẫn bị tính là nợ nhà cung cấp, và nhà cung cấp khoản mục `diesel` nuốt cả dầu lấy kho.

   **Cách làm đúng:** nợ nhà cung cấp = **các dòng có vế Có 4021** theo bảng 7.3. **Hiện trạng:** lúc khoá phiếu, các dòng đó thành bút toán chờ nguồn `no_ncc`; trả nhà cung cấp là phiếu chi "Chi khác" Nợ 4021 / Có tiền bên anh, đứng tên nhà cung cấp `EPLNCC-…`.

4. **Chi phí ghi nợ chưa bao giờ vào sổ.** Sổ tạm không có tờ nào đưa các cặp sau vào sổ:
   - 625/4021 (dầu trạm ghi nợ, chipping, lốp, thẻ cao tốc);
   - 614/4021 (garage cho nợ);
   - 625/4201 (tiền chuyến, tiền nước trả cùng lương).

   **Hiện trạng:** 625/4021 và 614/4021 (xe thuê 4022/4021) thành bút toán chờ nguồn `no_ncc` lúc khoá phiếu. **625/4201 chưa có nguồn** bút toán chờ — cách ghi phải trả nhân viên **đang chốt** (câu hỏi 10.10).

5. **Cấn trừ ghi Nợ ngân hàng.** `PT` với cách `offset` rơi vào Nợ 1021 / Có 1211, tức là sổ ghi một khoản tiền về ngân hàng không có thật. Đúng ra phải xoá khoản phải trả trạm dầu Việt Nam (4021) hoặc tiền thẻ khách. Cấn trừ nay là việc của hệ anh; tài khoản đối ứng **đang chốt** (mục 1.3).

6. **`PC_SC` trên sổ tạm ghi đối tượng `tai_xe` và luôn Có tiền mặt**, trong khi mã dòng sửa ngoài là 614/4021 (garage).
   - **Hiện trạng:** chi mục V – VI chỉ lập phiếu chi bên anh cho **dòng quỹ trả ngay** (xe nhà Nợ 614 · 625 / Có 1011, xe thuê Nợ 4022 / Có 1011), đối tượng tài xế (xe nhà) hoặc chủ xe (xe thuê).
   - Garage cho nợ theo đợt (lốp — Excel ghi *ຕິດໜີ້ຜູ້ສະໜອງ ຈ່າຍເປັນງວດ*) không vào phiếu chi; thành bút toán chờ `no_ncc` (lỗ hổng 4).

7. **Huỷ, xoá không có thông điệp sang sổ.** Sổ tạm huỷ hoá đơn, xoá lần thu, huỷ đợt trả hay bỏ chốt tất toán bằng cách **xoá tờ và bút toán của chính nó**. Sổ thật cần **bút toán đảo** (câu hỏi 10.7).
   - **Hiện trạng bên em:** phiếu chi / thu bên anh chưa ghi sổ thì bên em rút (`delete`); đã ghi sổ thì không xoá, không sửa, báo đối soát. Bút toán chờ đã gửi thì gửi `…/journal-entries/reverse` (gỡ ghi sổ + xoá chứng từ bên anh); bị chặn thì "chờ đảo" (12.12.4).

---

## 9. Việc bên em — đã làm, đang làm, cần quyền host

| Việc | Trạng thái |
|---|---|
| Ô **"Mã khách bên kế toán"** trên danh mục khách; chỉ KT Thu/Chi VC và Sếp gán; luật mã theo bên anh (không `/`, ≤ 37 ký tự) | **đã làm** |
| Gửi đề nghị thu → SO (3.2): lưu gói và khoá để thử lại đúng gói; tự tạo khách `EPLKH-…` khi chưa có; mọi DO đã khoá gửi được (cắt sổ 01/10); phiếu xuất xe hiện "Đã tạo SO" | **đã làm**, SO đã tạo qua API ở máy (3.2.1) |
| Chặn gửi PDT khi doanh thu = 0, phiếu không tuyến, cước THB / CNY | **đã làm** (mục II chưa kiểm: xem 6.4) |
| Đọc "thu một phần / đã thu" của SO từ `customer-detail` | **đã làm** (12.11.2) |
| Đối chiếu và sửa source của anh (nguồn DO, Vụ việc, `IsOrganization`, tổng header, quy đổi từng dòng, nhật ký kiểm toán, WEB phiếu thu chi) | **đã làm** — đến `b9227aa`, `7d168744` (12.9) |
| Phiếu chi tạm ứng "Chi trước" bên anh; xe chỉ xuất phát khi thủ quỹ bên anh ghi sổ | **đã làm** (12.10) |
| Trả chủ xe liên kết qua phiếu chi "Chi khác" bên anh, trừ hàng chủ xe mua ở quầy (kho tạm), tỷ giá riêng từng dòng | **đã làm** (12.11.3) |
| Chi mục V – VI qua phiếu chi "Chi khác" bên anh; Quỹ trên trang điều xe không chi nữa | **đã làm** (`f85078b`) |
| Tất toán tài xế: chênh → phiếu chi "Chi khác" / phiếu thu "Thu khác" bên anh; quyết toán `QT_TU` → bút toán chờ; màn Tất toán tài xế | **đã làm** (`f85078b`) |
| Trả nhà cung cấp qua phiếu chi "Chi khác" bên anh (Nợ 4021); màn Nhà cung cấp → "Trả qua kế toán" | **đã làm** (`f85078b`) |
| Bút toán chờ gửi (thuê xe 621/4022, ghi nợ nhà cung cấp, quyết toán tạm ứng, hàng bán cho chủ xe 4022/707); màn "Bút toán chờ gửi" | **đã làm** (`f85078b`, `ca7b630`) |
| API bút toán tổng hợp nhận bút toán chờ (12.12.4) | **đã làm** (`b9227aa`) — **đã chạy thật trên DB demo 02/10** (chủ dự án áp script; phiếu thử qua máy thử trang điều xe: thuê xe `GL021020263` / `GL021020264`, xuất kho `GL021020265` · `GL021020267`, ST 13; mở khoá gỡ sạch, GET 404); DB host **cần quyền host** |
| Gửi bút toán chờ sang API đó; gỡ khi nguồn bị huỷ; giữ hai sổ không lệch khi mất phản hồi | **đã làm** (`a938301`, `875a0cf`), cờ `QLSX_GUI_BUT_TOAN` tắt tới khi áp script |
| Phiếu bị xoá tay bên anh (`Master` null) → `PHIEU_CHI_MAT`, gửi lại thì lập phiếu mới | **đã làm** |
| Token: tiếp tục dùng token của anh (`EPL_ACC_CODE_TOKEN`); hết hạn khoảng 10/10 thì thay token mới trong `.env` hoặc đặt `QLSX_USERNAME` / `QLSX_PASSWORD` của anh (12.11.4) | đường tự đăng nhập **đã làm**; token / mật khẩu của anh — **cần quyền host** |
| Tài khoản tích hợp riêng (`epl_logistics`) | **tạm gác** (chủ dự án 01/10), tuỳ chọn (12.12.3) |
| Nút tạo **khoá bàn giao** cho hệ anh ở màn Tài khoản (hiện chỉ có đường `POST /api/handover/tao-khoa`) | khi có địa chỉ ra Internet |
| Dầu / phụ tùng kho xuất cho chuyến (lỗ hổng 2): xuất nội bộ / xuất bán cho chủ xe | **đã làm** — bút toán chờ `xuat_noi_bo`, `xuat_ban` lúc khoá phiếu (12.12.4); gửi sang anh khi bật cờ |
| Dọn lớp tạm ở mã trang điều xe: gói bàn giao `invoiced` / `inv_no` theo SO bên anh, xoá đường đẩy không ai gọi | **đã làm** (`938b007`); còn đổi tên cấu hình kho (`kho_*` thay `ke_toan_*`) — bên EPL làm (**đang làm**) |
| **Đã làm ngày 30/09:** tạm ứng qua 1601 và quyết toán lúc tất toán · doanh thu 708/707 · bản in phiếu thu ghi Nợ tiền / Có 1211 · `PC_SC` không chi lại dòng đã tạm ứng, không trả tiền mặt khoản nợ nhà cung cấp · tên tài khoản theo danh mục thật | — |

## 10. Câu hỏi nghiệp vụ còn mở

Câu đã có lời đáp giữ số để các mục khác tra, ghi gọn lời đáp. Từ 01/10 bên EPL làm các việc này luôn (đang làm); câu nào cần máy chủ host ghi **cần quyền host**.

1. **Tài khoản tích hợp:** chủ dự án chốt 01/10 **tạm gác** — trang điều xe tiếp tục dùng token của anh (hết hạn 10/10/2026). Đường tự đăng nhập đã có (`POST /api/v1/auth/login`, token 30 ngày, đăng nhập lại khi còn dưới 5 phút hoặc bị 401 — 12.11.4): hết hạn thì thay token mới trong `.env`, hoặc đặt `QLSX_USERNAME` / `QLSX_PASSWORD` của anh. Tài khoản riêng là tuỳ chọn (12.12.3).
2. **Ba mã con 1371, 4021, 4022** — **đã mở 01/10** ở danh mục quốc gia 11 trên DB của `appsettings.laos.json` (12.12.1). Host khác DB thì bên em chạy `tools/mo_ma_con_tune.py`.
3. **Tiền THB, CNY:** SO chỉ nhận VND · LAK · USD, trong khi cước bên Lào có phiếu ký bằng THB — mở thêm trong source: bên EPL làm (đang làm). Bật USD (mã 2) và thêm tiền trên DB host: **cần quyền host**.
4. **Dòng chi trong SO** — đã có lời đáp trong mã: dòng `chi` chỉ được ghép thành chữ vào mô tả mặt hàng và ghi chú dòng SO của khách, không thành bút toán. Bên em giữ một dòng thu (12.9.1, điều 1).
5. **Sau SO:**
   - cách sửa hoặc huỷ SO khi Sếp mở khoá phiếu (khoá chống trùng `logistics:EPLLAO-<Trip.id>` còn sau khi huỷ);
   - đường đọc trạng thái theo DO (hiện bên em đọc `customer-detail` theo khách, ghép `OrderCode`);
   - hoá đơn gộp tháng làm thế nào;
   - "hoàn thành SO" có phải là "đã xuất hoá đơn" bên em không.
6. **Chi tiền thật ở đâu** — chủ dự án chốt 01/10: **ở hệ anh**, trạng thái về trang điều xe. Áp cho tạm ứng (12.10), trả chủ xe (12.11.3), chi mục V – VI, tất toán tài xế, trả nhà cung cấp.
7. **Bút toán đảo** khi huỷ — đã có lời đáp trong mã: `…/journal-entries/reverse { "SourceRef" }` gỡ ghi sổ và xoá chứng từ tổng hợp bằng thủ tục legacy, không tạo tờ đảo riêng; chứng từ đã khoá / đã ghi sổ chính thức thì 409, kế toán gỡ trong QLSX (12.12.4).
8. **Chênh lệch tỷ giá** (hoá đơn USD, khách trả Kíp): hạch toán ở đâu, theo tỷ giá nào — **đang chốt**.
9. **Hàng bán cho chủ xe** (lỗ hổng 2): hàng mua ở quầy đã ghi bút toán chờ `ban_chu_xe` 4022/707 khi trả chủ xe; dầu / phụ tùng kho xuất cho chuyến trên phiếu (mục III, V) — **đã chốt 01/10**, bút toán chờ `xuat_noi_bo` / `xuat_ban` (12.12.4). Còn hỏi anh Khampla: nếu sau này tờ kho của hệ anh Toàn (`PXK_NL`, `PXK_PT` có định khoản) cũng vào sổ anh (câu hỏi 10.11) thì vế Có 1371 phải chọn **một** nơi ghi — không ghi cả hai.
10. **Ghi nhận chi phí không qua tiền** (lỗ hổng 1, 4): tài khoản đã chốt — thuê xe 621/4022, ghi nợ nhà cung cấp 625 · 614 / 4021, quyết toán tạm ứng 625/1601; bên em giữ thành bút toán chờ. **API bút toán** đã có (`b9227aa`, 12.12.4), đã chạy thật trên DB demo 02/10 (cả xuất kho cho chuyến). Còn lại cách ghi **625/4201** (tiền chuyến, tiền nước trả cùng lương — **đang chốt**).
11. **Tờ kho có định khoản** do hệ anh Toàn sinh: đi vào sổ anh qua đường nào? (Phong bì 3.1 đã thôi dùng.)
12. **Khách EPL Lào** — đã có lời đáp: bên em tự tạo qua `POST /api/v1/master-data/customers/upsert`, mã `EPLKH-<mã khách bên em>` (12.11.1).
13. **Cách nhận các tờ còn lại** — đã chốt cách (2): mỗi loại đi đường riêng của anh (SO, phiếu chi / thu `cmpayment-receipt`, bút toán khi có API). Bên em không đẩy phong bì nữa (3.1).

## 11. Thử với nhau

Bên em có các bộ kiểm tự động chạy trên máy thử (bản sao DB), không đụng dữ liệu thật:

- `kiem/thu_dinh_khoan.py` — mọi mã in ra đều có trong danh mục của anh (trừ ba mã con), bảng dòng chi 18 trường hợp, tạm ứng 1601, `PC_SC` không trả tiền mặt nợ nhà cung cấp.
- `kiem/thu_de_nghi.py` — khoá phiếu sinh đề nghị thu đúng tiền tệ; mở khoá rút tờ chưa gửi; tờ đã gửi thì chặn mở khoá.
- `kiem/thu_cach_tra.py` — cách trả theo Excel, tạm ứng chỉ gồm khoản chi ngay khi xe đi.
- `kiem/thu_day_ke_toan.py` — kiểm bên em **không còn** lời gọi `/api/v1/epl-lao/vouchers` nào; các đường đẩy cũ trả đúng kiểu nhưng không gọi mạng (3.1).
- `kiem/thu_tao_so_that.py` — gửi SO thật qua API của anh chạy ở máy.
- `kiem/thu_chi_tam_ung_ke_toan.py`, `kiem/thu_xe_thue_ke_toan.py`, `kiem/thu_chu_xe.py`, `kiem/thu_tru_hang_quay.py` — tạm ứng, tạm ứng xe thuê, trả chủ xe có trừ hàng quầy qua phiếu chi bên anh (12.10, 12.11.3).
- `kiem/thu_chi_muc_tune.py` — chi mục V – VI; `kiem/thu_tat_toan_tune.py` — tất toán tài xế, trả nhà cung cấp; `kiem/thu_but_toan_cho.py` — bút toán chờ gửi. Đạt trên máy thử 8011 với `f85078b`.
- `kiem/thu_gui_but_toan.py` — gửi bút toán sang **máy giả** theo giao ước `b9227aa` (201, ST 13, `ErrorDetail`, 409 khác số, gỡ lần hai, mất phản hồi); không gọi API thật, không chạy trên máy thật 8010 / 8020.
- `kiem/thu_giao_dien.js` — 22 màn, gồm Tất toán tài xế, Nhà cung cấp, Bút toán chờ gửi (`ca7b630`).
- Kho tạm `EPL_KETOAN/kiem/thu_tru_hang_chu_xe.py` — ba đường trừ hàng quầy, máy thử 8031 (`1d8d91c`).
- `kiem/thu_tao_so.py` (01/10) — 23 chỗ kiểm cho tạo SO: quyền (Bãi, tài xế, KT doanh thu không gửi được), luật chặn (DO chưa khoá, thiếu mã khách, mã khách quá 37 ký tự bị chặn ngay ở danh mục), khuôn gói (ba khoá gốc, `customer_id` = mã bên anh, một dòng thu, tổng khớp chính xác). **Không gọi sang hệ anh.**
- `kiem/thu_luat_so_ben_tune.py` (01/10) — chép đúng luật `LogisticsPushValidator` và phần kiểm đầu của `sp_Logistics_CreateSalesOrder`, chạy trên gói SO của mọi DO đã khoá: **13/13 qua**. Không gọi sang hệ anh, không ghi DB.
- `kiem/thu_ban_giao.py` — 32 chỗ kiểm cho hai đường bàn giao DO (12.8), gồm các khoá màn "Vụ việc" đọc; **thêm 01/10 11 chỗ cho `q`** (sáu ô tìm, `total` sau lọc, phân trang khi tìm, `%` không là ký tự đại diện, quá 200 ký tự → 422). Đặt `KHOA_BAN_GIAO_TEP=<tệp khoá>` thì bài dùng khoá có sẵn, không tạo lại — chạy được trên máy thử dùng chung DB mà không làm hỏng khoá máy kia đang cầm.
- `kiem/thu_khach_hang_moi.py` — mã khách: chỉ `acct` và Sếp gán, không trùng, đúng luật mã của anh (không `/`, ≤ 37 ký tự); `customer_id` = `customer_code` trong gói bàn giao.
- Bên bản tạm `EPL_KETOAN/kiem` còn các bài của phần tiền cũ (`thu_tat_toan.py`, `thu_nhan_chung_tu.py`, `thu_dot2.py`); từ 01/10 phần tiền đó bỏ, chỉ phần kho còn dùng.

Khi anh có môi trường thử:

1. Sếp đặt địa chỉ và khoá trỏ sang máy thử của anh.
2. Bên em chạy các bộ trên.
3. Tờ nào anh từ chối sẽ hiện câu lỗi của anh ngay trên dòng đó.

Liên hệ kỹ thuật bên em: [tên · điện thoại].

---

## 12. Đối chiếu với API thu chi DemoLao anh gửi (nhánh `feat/DemoLao`, commit `8b55dfa`, đối chiếu 26/09)

Bên em đã đọc hết `CM-CASH-VOUCHER-DEMOLAO-API-GUIDE.md`. Mục này ghi, với từng việc bên em cần:

- dùng **đường nào của anh**;
- **gửi gì**;
- **còn thiếu gì**.

Ngày 30/09 bên em đã **gọi thử các đường chỉ đọc** trên máy `demo-lao-api` bằng token trong cấu hình. Kết quả và số thật ở **mục 12.7**.

### 12.1. Hệ quả chung cho cách bên em nối

| Luật trong hướng dẫn của anh | Bên em làm theo |
|---|---|
| Base URL là **server Backend API**, không phải BFF web | `QLSX_BASE_URL` (hoặc máy của `EPL_ACC_CODE_API`) trỏ đúng server API (2.1) |
| `Authorization: Bearer <access-token>`; người thao tác lấy từ token (`User.GetObjectId()`) | bên em đăng nhập bằng **tài khoản dịch vụ** (câu hỏi 10.1). Người bấm bên em ghi vào `Description`, không thay xác thực |
| Gửi `X-Correlation-Id` | **chưa gửi**. Đối soát hiện dựa vào số tham chiếu (`RefDocumentNo` = số đề nghị bên em) và thân trả về bên em lưu cho từng lượt gửi |
| JSON **PascalCase**; một số report trả tên cột SQL | bên em đọc đúng hoa thường, không đổi |
| **Lỗi trả HTTP 200 kèm `Success = false`** | bên em kiểm **cả HTTP status lẫn `Success`**, không coi 200 là thành công |
| Có `TmpId` **không có nghĩa** đã có phiếu chính | bên em chỉ đánh "đã tạo" khi có `RealId` và `Status = "Committed"` |
| **Không có Idempotency-Key**; hết giờ không có nghĩa là chưa tạo | trước mỗi lần tạo, bên em tìm bằng `POST /list` theo **đối tượng + `DOC_REFDOCUMENTNO`** (số đề nghị bên em); có rồi thì dùng lại. `SessionId` mỗi lượt gửi một mã (`epllao-…`) |
| Tổng header (`Header.Amount` / `BaseAmount`) và quy đổi từng dòng | bên em gửi = Σ dòng; hệ anh **tự tính lại** quy đổi từng dòng (`ae0e7f6`) và tổng header (`ce95b3c`), 5 số lẻ, nửa xa số 0; số bên em gửi không có thẩm quyền. Phiếu trả chủ xe ngoại tệ bên em gửi tỷ giá riêng từng dòng |
| Mọi mã là **ID số trong DB**: `CountryId` 11, `OrgId`, `FiciAutoId` (kỳ tài chính), `DotyAutoId` (loại chứng từ), `CurrencyId`, `ObjectId` | bên em giữ bảng đối chiếu (12.4), Sếp nhập ở màn cấu hình |
| Nên `PostMode = None`, xác nhận `RealId` rồi mới ghi sổ riêng | bên em chỉ tạo phiếu ở `PostMode = None`. **Ghi sổ là việc của kế toán bên anh** |

### 12.2. Mỗi việc bên em cần ↔ đường của anh

| Việc | Đường của anh | Cách dùng | Trạng thái |
|---|---|---|---|
| **Danh mục tài khoản** | `GET /api/v1/common/country-accounts?tryAutoId=11` (đang gọi) · `GET …/cmpayment-receipt/country-accounts?countryId=11` (chỉ tài khoản active **và cho hạch toán**) | ô chọn mã kế toán (3.3) | 1371, 4021, 4022 đã có trên DB của API ở máy (12.12.1) |
| **Tài khoản tiền mặc định** | `GET …/default-money-account?countryId=11&isCash=&isLocal=&currencyId=` → `{AccountCode}` | vế tiền 1011 / 1012 / 1021 / 1022 | khớp bảng định khoản bên em (7.1); `currencyId` chỉ có tác dụng khi có `bankId` |
| **Loại chứng từ** | `GET …/document-types?voucherType=ALL&orgAutoId=` | `DotyAutoId`: tạm ứng **59 "Chi trước"**; trả chủ xe, chi mục V – VI, chi bù tất toán, trả nhà cung cấp **60 "Chi khác"**; thu hoàn tất toán **17 "Thu khác"** (đổi được bằng cấu hình `QLSX_DOTY_*`) | `document-types` trả **cờ phân loại**: bên EPL làm (đang làm). WEB sửa được 58/60, 15/17; phiếu 59 và loại khác mở chỉ xem |
| **Đề nghị tạm ứng (PTU) → phiếu chi** | `POST …/save-and-commit`, `VoucherType = "CMP"`, `PostMode = "None"` | bên em tạo phiếu chờ, thủ quỹ bên anh chi và ghi sổ | **chạy** (12.10) |
| **Trả chủ xe liên kết** | `save-and-commit` CMP "Chi khác", `Entries` Nợ 4022 / Có tiền | bên em lập đề nghị, thủ quỹ bên anh chi | **chạy** (12.11.3). Khoản phải trả chủ xe ghi bằng bút toán chờ 621/4022 (mục 8, lỗ hổng 1) |
| **Chi mục V – VI** (dòng quỹ trả ngay) | `save-and-commit` CMP "Chi khác", `Entries` 614 · 625 / 1011 (xe thuê 4022/1011) | KT Chi phí VC ghi sổ mục → bên em tạo phiếu chờ | **chạy** ở máy |
| **Tất toán tài xế** | `save-and-commit` CMP "Chi khác" (chi bù, Nợ 1601 / Có tiền) · CMR "Thu khác" (thu hoàn, Nợ tiền / Có 1601) | KT Chi phí VC chốt kỳ → bên em tạo phiếu chờ; quyết toán 625/1601 là bút toán chờ | **chạy** ở máy |
| **Trả nhà cung cấp** | `save-and-commit` CMP "Chi khác", `Entries` Nợ 4021 / Có tiền | KT Chi phí lập đề nghị → bên em tạo phiếu chờ | **chạy** ở máy |
| **Bút toán không qua tiền** (thuê xe, ghi nợ nhà cung cấp, quyết toán tạm ứng, hàng bán cho chủ xe) | `POST /api/v1/integrations/logistics/journal-entries` (+ `/reverse`, `GET /{SourceRef}`), `Idempotency-Key` = SourceRef (`b9227aa`) | bên em gửi bút toán chờ (mục 8) khi bật cờ `QLSX_GUI_BUT_TOAN`; gỡ khi nguồn bị huỷ | API và đầu gửi đã có; **chạy thật trên DB demo 02/10**, host chưa áp (12.12.4) |
| **Gắn DO làm nguồn** cho phiếu thu chi | `GET /api/v1/accounting/cash-voucher-references?type=DO` và `GET …/DO/{id}` → `SelectionToken`; rồi `SourceReferences[]` trong save-and-commit | kế toán bên anh gắn DO ở màn Vụ việc | nguồn DO đọc qua `LogisticsSource` (`ce95b3c`, 12.9.2). Phiếu bên em tạo **chưa gửi** `SourceReferences` (cần `SelectionToken` cấp theo người xem) — số phiếu xe nằm trong diễn giải và số tham chiếu |
| **Đề nghị thu (PDT) → SO + công nợ** | `POST /api/v1/integrations/logistics/sales-orders` (mục 3.2) | mọi DO đã khoá | **chạy** |
| **Thu tiền khách** của SO | WEB **Chi tiết công nợ khách hàng → Tạo phiếu thu → Xác nhận thu nợ** → `POST /api/v1/sales/debt/collection-upsert` (`DocumentType = "TKN"`, theo `RetkAutoId` của SO) → phiếu thu nợ RES `4-TKN-1368-2-…` + phiếu thu **CMR 17 "Thu khác"** `4-1368-TK-…`, Nợ 1021 (hoặc 1011) / Có 1211. **Không** qua `save-and-commit` CMR 15 "Thu công nợ": tìm công nợ SO ở đó ra 0 dòng | **việc của kế toán bên anh**, bên em không gọi | KB-AZ đi thật 01/10. Hai lỗi: hộp Tạo phiếu thu chỉ có tài khoản nội tệ, tỷ giá cứng 1 → SO USD ghi thành Kíp (UI-4 đang sửa); mọi SO cùng mã phiếu bán "Demo EPL-2-261001000" (UI-4 đang tìm nguồn) |
| **Xem công nợ khách**, "đã thu" của SO | `POST /api/v1/sales/debt/customer-detail` `{CustomerObjectId, OrgId}` | bên em **chỉ đọc và hiện**; ghép theo `OrderCode` (12.11.2) | **chạy**; xin một mẫu thân thật (`Debts`, `Collections` là dynamic) |
| **Trạng thái theo DO** | chưa có đường theo `do_id` | tạm thời đọc `customer-detail` theo khách | câu hỏi 10.5 |
| **Báo cáo thu chi** | `/api/v1/accounting/gl-report/*` | chỉ xem | `accounts` còn legacy 111/112, không theo quốc gia — chưa dùng cho Lào |

### 12.3. Khung phiếu chi tạm ứng bên em đang gửi (từ một tờ PTU)

Giá trị thật trên DB demo ở 12.10.1 (`DotyAutoId` 59, LAK = 26, kỳ theo ngày lập). Khuôn chung cho mọi phiếu bên em tạo (A4, A7 – A10 ở `NOI_API_ANH_TUNE` mục 1.4): một header, `Relations` rỗng, `Entries` mang đúng cặp Nợ / Có của bên em.

```json
{"TmpId": 0, "RealId": 0, "VoucherType": "CMP", "SessionId": "epllao-<mã tờ>-<giờ gửi>", "PostMode": "None",
 "Header": {"CountryId": 11, "OrgId": 1368, "FiciAutoId": 19, "DotyAutoId": 59, "CurrencyId": 26, "ObjectId": "<ObjectId của tài xế EPLTX-…>",
            "RefDocumentNo": "PTU-T4-0428-08/EPL", "DocumentDate": "2026-10-01",
            "Description": "Tạm ứng chuyến T4-0428-08/EPL · xe 341 · ທ້າວ ທັດສະດາພອນ",
            "IsCash": true, "IsLocal": true, "IsDirect": true, "ExchangeRate": 1, "Amount": 580000, "BaseAmount": 580000,
            "ContactName": "ທ້າວ ທັດສະດາພອນ"},
 "Relations": [],
 "Entries": [{"SourceLineKey": "EPLLAO:<mã tờ>:PTU", "ObjectId": "<như header>", "CurrencyId": 26,
              "DebitAccount": "1601", "CreditAccount": "1011", "ExchangeRate": 1, "Amount": 580000, "BaseAmount": 580000,
              "EntryTypeId": 11, "Description": "Tạm ứng tiền mặt đi đường T4-0428-08/EPL", "ValidateMoney": true}]}
```

- **Xe thuê:** `DebitAccount = "4022"` (trừ vào tiền trả chủ xe), `ObjectId` = chủ xe `EPLCX-…`.
- **Vế tiền:** theo cách trả và tiền tệ (1011 / 1012 / 1021 / 1022, bảng 7.1), khớp `default-money-account` của anh.
- Quy đổi từng dòng (`ae0e7f6`) và `Header.Amount` / `BaseAmount` (`ce95b3c`) hệ anh tính lại từ `Entries`.
- `SourceReferences` **chưa gửi** (12.2, dòng "Gắn DO làm nguồn").

### 12.4. Bảng mã số bên em dùng

| Cần mã | Trường | Hiện trạng |
|---|---|---|
| Quốc gia | `CountryId` | 11 (Lào) |
| Đơn vị | `OrgId` / `OrgAutoId` | đang dùng chi nhánh 1368 "Demo EPL" (cấu hình `QLSX_ORG_ID`). EPL Lào — Thà Bốc, Viêng Chăn: một hay hai đơn vị? |
| Kỳ tài chính | `FiciAutoId` (ID, không ghép YYYYMM) | tra theo ngày ở `GetFinancyCicle` |
| Loại chứng từ | `DotyAutoId` | 59 "Chi trước" · 60 "Chi khác" · 17 "Thu khác" (12.2) |
| Tiền tệ | `CurrencyId` (ID, không phải chữ LAK/USD) | LAK 26, VND 3; USD 2 đang tắt (bên em tạm đặt `QLSX_TIEN_USD=2`); chưa có THB, CNY |
| Đối tượng | `ObjectId` (PUBOBJECT) + `OBJ_OBJECTNO` (cho SO) | bên em tự tạo: khách `EPLKH-`, chủ xe `EPLCX-`, nhà cung cấp `EPLNCC-`, tài xế `EPLTX-` — nên dùng **chung một danh mục đối tượng** với kho anh Toàn |
| Phương thức thanh toán | `PaymentMethodId` | tiền mặt · chuyển khoản; chưa có "cấn trừ" |

### 12.5. Hệ anh chọn được DO của bên Lào

Hệ anh đọc DO qua **API bàn giao của Logistics**, đúng khuôn EPL_System:

- `GET /api/handover/delivery-orders?customer_id=&completed_from=&completed_to=&q=&page=&page_size=`, trả về `{message, data: {items: [{do_id, status, customer_id, quotation_id, route_id, vehicle_id, driver_id, selling_price, customer_surcharge_total, final_selling_price, currency, completed_at, completed_by, detail_url, …}], total, page, page_size, q}}`;
- `GET /api/handover/delivery-orders/{do_id}`, trả về `{message, data: {header, details}}`.

**Bên em đã dựng hai đường này ở trang điều xe EPL Lào (chi tiết ở mục 12.8)**, chỉ đọc:

- `do_id` = `EPLLAO-<Trip.id>` (trùng `do_id` gửi SO ở 3.2);
- `status = "delivered"` khi phiếu **đã về và đã khoá**;
- tiền theo tiền cước của phiếu;
- `details` = dòng thu (cước) và các dòng chi mục III–VI, kèm `acc_code` (bảng 7.3).

**Phía anh** (`ce95b3c`, 12.9.2): địa chỉ Logistics và khoá nằm ở cấu hình `LogisticsSource`, ghi đè được theo chi nhánh. Thiếu `BaseUrl` thì màn Vụ việc báo 503, không tự trỏ EPL_System. Host chưa có code này nên vẫn đọc EPL_System 1506 cho tới khi triển khai lên host (**cần quyền host**).

### 12.6. Câu hỏi thêm

1. **Tài khoản dịch vụ và token** cho API CM — đã có cách: tự đăng nhập `auth/login`, token 30 ngày, không có refresh (12.11.4). Tạm dùng token / tài khoản của anh (`AllowedUserIds` giữ `846`); tài khoản riêng tuỳ chọn (12.12.3).
2. **Trạng thái theo DO:** có đường nào trả "SO của DO này: đã hoá đơn chưa, đã thu bao nhiêu, còn nợ bao nhiêu" không? Hiện bên em đọc `customer-detail` theo khách rồi ghép `OrderCode` (12.11.2); các đường bản chép cũ bên em đã gỡ (mục 4).
3. **Phiếu chi tạm ứng** — đã chốt: bên em tạo sẵn phiếu chờ (`PostMode = None`), thủ quỹ bên anh chi và ghi sổ; `DotyAutoId` 59 "Chi trước" (12.10). Cùng khuôn cho trả chủ xe, chi mục V – VI, tất toán, trả nhà cung cấp.
4. **`handover/delivery-orders` theo tenant** — đã có trong `ce95b3c`: `LogisticsSource:Branches:<BranchId>` ghi đè `BaseUrl` / `ApiKey` theo chi nhánh (12.9.2).
5. **Hai đường danh mục tài khoản** (`common/country-accounts` và `cmpayment-receipt/country-accounts`): trên DB của API ở máy, đường thứ nhất trả 497 mã, đường thứ hai chỉ trả tài khoản cho hạch toán (không còn 137, 402). Bên em đang gọi đường thứ nhất và đọc cờ "ghi sổ được" ở `AccAccountWrite`.
6. **Tiền THB, CNY** cho phiếu CMP / CMR: thêm tiền và `CurrencyId` trên DB host, bật USD (mã 2) — **cần quyền host**; phần source bên EPL làm (đang làm), như câu hỏi 10.3.

### 12.7. Số đọc được trên máy host `demo-lao-api` (30/09 – 01/10, chỉ đọc)

Bên em đã gọi thử bằng token cấu hình trong trang điều xe (`EPL_ACC_CODE_API`, `EPL_ACC_CODE_TOKEN`):

- **chỉ gọi các đường xem, danh sách, tìm**;
- **không gọi** đường tạo, lưu, commit, ghi sổ, xoá nào trên host;
- không in token ra đâu.

Host chưa có code hai nhánh và có thể trỏ DB khác API ở máy (12.12.2), nên một số số dưới đây khác bản ở máy; cột cuối ghi hiện trạng.

#### 12.7.1. Token hiện có

| | |
|---|---|
| Người dùng | `tune` (UserID 846, ObjectId 1503, nhóm "Nhân viên", OrgId 2) — **tài khoản cá nhân của anh** |
| Hạn | **10/10/2026 09:05 giờ Lào** (02:05 UTC) |
| Chi nhánh được vào (`auth/branches`) | 1368 "Demo EPL" · 5 "EPL 2" · 1369 "EPL 3" |

Dùng tài khoản cá nhân thì mọi phiếu bên em tạo ghi tên anh. Chủ dự án chốt 01/10: chấp nhận, tạm gác tài khoản tích hợp. Tới 10/10 token hết hạn: thay token mới trong `.env`, hoặc đặt `QLSX_USERNAME` / `QLSX_PASSWORD` của anh để tự đăng nhập lại (12.11.4).

#### 12.7.2. Bảng mã 12.4 — số đọc được

| Cần mã | Số đọc trên host | Hiện trạng |
|---|---|---|
| `CountryId` | 11 | — |
| `OrgId` | 2 "EPL 1" · 1368 "Demo EPL" · 5 "EPL 2" · 1369 "EPL 3" (`common/GetCompanyAndBranch`) — **cả bốn đều quốc gia Việt Nam, tiền VND (`CUR_AUTOID` 3)** | bên em dùng 1368 (`QLSX_ORG_ID`); tạo đơn vị EPL Lào (quốc gia Lào, tiền LAK) trên DB host — **cần quyền host** |
| `FiciAutoId` | 22 kỳ, đều "Kỳ mở". **ID không theo thứ tự tháng**: 9/2026 = **20**, 10/2026 = **19**, 11/2026 = 18, 12/2026 = 17, 10/2025 = 24, 1/2026 = 7 | bên em **tra theo `FICI_DATEFROM` / `FICI_DATETO`**, không đoán ID |
| `DotyAutoId` (thu chi) | 14 Thu hoá đơn · 15 Thu công nợ · 16 Thu trước · 17 Thu khác · 57 Chi hoá đơn · 58 Chi công nợ · 59 Chi trước · 60 Chi khác · 68 Chuyển tiền nội bộ | đã chốt: tạm ứng 59; chi khác 60; thu khác 17 (12.2) |
| `CurrencyId` | **3 = VND, 26 = LAK** (`common/GetAllCurrency`) | USD có mã 2 nhưng đang tắt (bên em tạm đặt `QLSX_TIEN_USD=2`); chưa có THB, CNY |
| `PaymentMethodId` | 1 Tiền mặt · 3 Chuyển khoản · 6 Tiền mặt/Chuyển khoản | **chưa có "cấn trừ"** (mục 6.6) |
| Vế tiền mặc định (`default-money-account`, quốc gia 11) | tiền mặt Kíp **1011** · tiền mặt ngoại tệ **1012** · ngân hàng Kíp **1021** · ngân hàng ngoại tệ **1022** | khớp đúng bảng định khoản bên em (mục 7) |
| `ObjectId` | **189 khách, 517 nhà cung cấp** (trang 100 dòng) ở chi nhánh 1368, đều là dữ liệu bên khác | bên em tự tạo đối tượng qua `master-data/*/upsert` (12.11) |

#### 12.7.3. Danh mục tài khoản

| Đường | Số đọc trên host | Hiện trạng |
|---|---|---|
| `GET /api/v1/accounting/lao-accounts` | **494 mã**. Cột: `ACC_CODE`, `ACC_NAME`, `ACC_PARENTID`, `ACC_STRUCTURE`, `ACC_ISACTIVE`, `ACC_ISMONEYCURENTCY`, `TRY_AUTOID`, `Version`… Tài khoản `tune` có `CanCreate`, `CanWrite`, `CanDelete` = true | DB của API ở máy: 497 mã sau khi mở ba mã con (12.12.1) |
| `GET …/cmpayment-receipt/country-accounts?countryId=11` | **405 mã** cho hạch toán (cột PascalCase: `AccCode`, `AccName`, `AccParentId`…). Có đủ 1011, 1012, 1021, 1022, 1211, 137, 1601, 401, 402, 4201, 607, 614, 625, 707, 708 | DB của API ở máy: có 1371, 4021, 4022; không còn 137, 402 (đã là tổng hợp) |

#### 12.7.4. Nguồn DO của phiếu thu chi trên host

`GET /api/v1/accounting/cash-voucher-references?type=DO` trên host trả **23 DO mẫu của EPL_System bên Việt Nam** (khách `DEMO-CUS-…`, tuyến `DEMO-RT-…`; ví dụ `DO-2026-0047-DO01`: `DEMO-CUS-DUCGIANG`, 3.829.000 LAK, `delivered`), vì host còn chạy code đọc EPL_System 1506.

Mỗi dòng có khuôn (`CashVoucherReferenceRow` trong `ce95b3c`):

```json
{"SourceSystem": "LOGISTICS", "SourceType": "DO", "SourceId": "<do_id>", "SourceCode": "<doc_no hoặc do_id>",
 "SourceName": "<customer_name hoặc customer_id>", "Status": "delivered",
 "Summary": {"<một dòng của GET /api/handover/delivery-orders>": "…"}}
```

`Summary` chính là một dòng của `GET /api/handover/delivery-orders`. Bên em đã dựng đúng khuôn đó ở trang điều xe Lào (12.8); API ở máy với `LogisticsSource` trỏ trang điều xe thử đã đọc đúng DO bên Lào.

#### 12.7.5. Việc còn lại — xếp theo thứ tự cần trước

| # | Việc | Người làm |
|---|---|---|
| 1 | **Bút toán tổng hợp** nhận bút toán chờ (mục 8, 12.12.4): API đã có (`b9227aa`); áp script `20261001_logistics_journal_entry.sql`, rồi cấu hình, bật cờ, gọi thử | áp script DB demo: **chủ dự án tự chạy**; DB host: **cần quyền host**; bật cờ, gọi thử: bên EPL |
| 2 | **Triển khai hai nhánh** lên host, đặt cấu hình `LogisticsSource` (bắt buộc), `LogisticsSalesPush:AllowedUserIds` (12.12.2) và `LogisticsJournalEntry` (12.12.4); kho tạm có `1d8d91c` | **cần quyền host** |
| 3 | **Token hết hạn khoảng 10/10**: thay token mới trong `.env`, hoặc đặt `QLSX_USERNAME` / `QLSX_PASSWORD` của anh (12.11.4). Tài khoản tích hợp tạm gác — tuỳ chọn (12.12.3) | **cần quyền host** (token / mật khẩu của anh) |
| 4 | **Cờ phân loại** ở `document-types` (12.2) | bên EPL làm (đang làm) |
| 5 | **Dữ liệu DB host**: mở 1371 / 4021 / 4022 nếu thiếu; bật LAK / USD, thêm THB (và CNY nếu dùng); lỗi `default-money-account` trên host; đơn vị EPL Lào (quốc gia 11, tiền LAK — Thà Bốc và Viêng Chăn một hay hai đơn vị?) | **cần quyền host** |
| 6 | **Nhật ký kiểm toán cũ** có thể còn mật khẩu dạng chữ thường (trước `ed5aa0e`): chạy script che `20261001_audit_redact_secrets.sql` (`e2ef52f`), cân nhắc đổi mật khẩu | **cần quyền host** |
| 7 | Phương thức **"cấn trừ"** và tài khoản đối ứng cấn trừ (mục 1.3, lỗ hổng 5) | **đang chốt** |

Đã xong: mở 1371 / 4021 / 4022 (12.12.1); `DotyAutoId` tạm ứng 59 (12.10); đối tượng bên em tự tạo (12.11); nguồn DO theo cấu hình, có khoá (12.9.2).

### 12.8. Hai đường bàn giao DO đã dựng ở trang điều xe Lào (30/09)

Bên em đã dựng xong hai đường ở mục 12.5, **đúng khuôn EPL_System**, cộng thêm các khoá màn "Vụ việc" của anh đọc (12.9.2). Phía anh đọc qua cấu hình `LogisticsSource` (`BaseUrl`, `ApiKey`, ghi đè theo chi nhánh) từ `ce95b3c`.

#### 12.8.1. Xác thực

- Mọi lời gọi mang header `Authorization: Bearer <khoá bàn giao>`.
- Khoá do **Sếp bên em tạo** (`POST /api/handover/tao-khoa`, vai admin), trả **đúng một lần** để chép sang cấu hình bên anh. Tạo lại thì khoá cũ hết hiệu lực ngay.
- Khoá này **riêng** cho hệ anh, không dùng chung với khoá của trang kế toán tạm. Phiên đăng nhập của người dùng bên em **không** thay được khoá này.
- Không cần `X-Nguoi-Dung`: hệ anh chỉ **đọc**, không ghi gì vào trang điều xe.

| Lỗi | Khi nào |
|---|---|
| 401 `SAI_TOKEN` | thiếu khoá hoặc khoá sai |
| 503 `CHUA_DAT_TOKEN` | bên em chưa tạo khoá |

Mọi lỗi trả dạng `{"detail": {"ma": "<MÃ>", "loi": "<câu tiếng Việt>"}}`, **HTTP status đúng lỗi**. Bên em không trả 200 kèm lỗi.

#### 12.8.2. `GET /api/handover/delivery-orders` — danh sách

Tham số (đều tuỳ chọn):

| Tham số | Kiểu | Ý nghĩa |
|---|---|---|
| `customer_id` | chuỗi | **mã khách bên anh** (`OBJ_OBJECTNO`, ô "Mã khách" trên danh mục khách bên em) **hoặc** mã khách nội bộ bên em (`customer_ref`, 12 ký tự hex) |
| `completed_from`, `completed_to` | `YYYY-MM-DD` | ngày khoá phiếu (gồm cả hai đầu, theo giờ UTC). Sai dạng → 422 `NGAY_SAI` |
| `q` | chuỗi ≤ 200 ký tự | (thêm 01/10) **tìm theo chữ trên toàn bộ DO**, không phân biệt hoa thường, khớp một phần của: `do_id`, `doc_no` (số phiếu), `customer_id` (mã khách bên anh), `customer_name`, `truck_no` (số xe), `plate_head` (biển đầu kéo) — đúng sáu ô màn "Vụ việc" tìm. `%` và `_` là chữ thường, không phải ký tự đại diện. Cắt dấu cách hai đầu; rỗng = không lọc. Dài hơn 200 → 422 `TU_KHOA_DAI` |
| `page` | số ≥ 1 | mặc định 1 |
| `page_size` | 1–200 | mặc định 50 |

- Chỉ trả phiếu **đã về** (`transport_status = "arrived"`) **và đã khoá** (kế toán Viêng Chăn khoá sau khi có biên bản giao nhận).
- Xếp **mới khoá trước**.
- `total` là tổng thật sau khi lọc (không phải tổng chưa lọc), **kể cả lọc theo `q`**; `page` / `page_size` phân trang trên kết quả đã lọc.
- `data.q` trả lại đúng chữ đã dùng để lọc (`null` khi không lọc). Hệ anh dựa vào khoá này để biết trang điều xe đã tìm hộ; bản cũ không có khoá này thì hệ anh tự lọc trong trang đã tải (12.9.2).

Trả về:

```json
{"message": "Danh sách 13 lệnh giao hàng đã hoàn tất (trang 1).",
 "data": {"items": [
   {"do_id": "EPLLAO-779739f4b582", "status": "delivered",
    "doc_no": "T4-0449-09/EPL", "kind": "giao",
    "customer_id": "<OBJ_OBJECTNO bên anh hoặc null>", "customer_code": "<như customer_id>",
    "customer_ref": "<mã khách nội bộ bên em>", "customer_name": "<tên khách>",
    "quotation_id": null, "contract_no": "<số hợp đồng>",
    "route_id": "<mã tuyến>", "origin": "…", "destination": "…",
    "vehicle_id": "<mã xe>", "truck_no": "346", "plate_head": "<biển đầu kéo>",
    "driver_id": "<mã tài xế>", "driver_name": "…",
    "company": "EPL", "owner_name": null,
    "selling_price": 905.85, "customer_surcharge_total": 0, "final_selling_price": 905.85,
    "currency": "USD", "final_selling_price_lak": 19928700,
    "completed_at": "2026-09-29T06:42:51+00:00", "completed_by": "<người khoá>",
    "detail_url": "/api/handover/delivery-orders/EPLLAO-779739f4b582"}],
  "total": 13, "page": 1, "page_size": 50, "q": null}}
```

- 14 khoá của EPL_System **có đủ**: `do_id`, `status`, `customer_id`, `quotation_id`, `route_id`, `vehicle_id`, `driver_id`, `selling_price`, `customer_surcharge_total`, `final_selling_price`, `currency`, `completed_at`, `completed_by`, `detail_url`.
- Khoá thêm để thủ quỹ **đọc được bằng mắt** khi chọn DO: `doc_no`, `customer_name`, `truck_no`, `plate_head`, `driver_name`, `company`, `owner_name`, `final_selling_price_lak`.
- `customer_id` = `customer_code` = **mã khách bên anh** (`OBJ_OBJECTNO`) mà bên em ghi ở ô "Mã khách" của danh mục khách (thêm 30/09). Khách chưa ghi mã thì cả hai là `null`. **Đổi 01/10:** trước đây `customer_id` là mã nội bộ bên em; màn "Vụ việc" của anh hiện ô này làm tên khách nên nay để mã bên anh, trùng `customer_id` trong gói tạo SO (12.9.2).
- `customer_ref` = mã khách **nội bộ bên em** (12 ký tự hex), luôn có.
- **Ai ghi mã bên em** (chốt tối 30/09, theo Excel của khách, sheet ໜ້າວຽກ: *ລົງຂໍ້ມູນ ລູກຄ້າ* — Bãi Thà Bốc nhập, *ບັນຊີລາຍຈ່າຍ/ຮັບ ວຽງຈັນ* xác nhận): Bãi nhập tên, điện thoại, địa chỉ của khách; **chỉ KT Thu/Chi Viêng Chăn (vai `acct`) hoặc Sếp (`admin`) gán / đổi mã khách**. Vai khác gửi mã khác mã đang có thì máy chủ trả 403 `MA_KHACH_KE_TOAN` và không ghi gì. Nên khách Bãi vừa thêm sẽ có `customer_code = null` cho tới khi kế toán gán mã theo danh sách của anh.
- `quotation_id` luôn `null`: bên Lào không có báo giá.
- `currency` là **tiền cước của phiếu**: `USD`, `THB`, `LAK`, `VND` hoặc `CNY`.

#### 12.8.3. `GET /api/handover/delivery-orders/{do_id}` — header + details

- `do_id` = `EPLLAO-<Trip.id>`. Số phiếu (`T4-0449-09/EPL`) **không** dùng làm mã được → 404.
- 404 `DO_KHONG_THAY`: không có mã này.
- 409 `DO_CHUA_KHOA`: phiếu chưa về hoặc chưa khoá.

**`header`:**

| Khoá | Ý nghĩa |
|---|---|
| `do_id`, `status` (`delivered`), `source_system` (`EPL_LAO`), `trip_id`, `doc_no`, `kind` | mã DO, số phiếu; `kind` = `gom` (đi lấy hàng về bãi) hoặc `giao` (đi giao hàng) |
| `doc_date`, `out_date`, `back_date` | ngày lập, ngày xe đi, ngày xe về (`YYYY-MM-DD`) |
| `company` | `EPL` (xe nhà) hoặc `joint` (xe thuê / liên kết) |
| `owner_id`, `owner_name`, `hire_contract_no` | chỉ có với xe thuê |
| `customer_id` = `customer_code`, `customer_ref`, `customer_name`, `contract_no` | khách: **mã bên anh** (null khi chưa gán), mã nội bộ bên em, tên; hợp đồng vận chuyển |
| `trip_status` | `completed` (DO bàn giao luôn là chuyến đã xong) |
| `route` | `{id, name, origin, destination, distance_km}` hoặc `null` |
| `origin`, `destination`, `goods_type`, `ore_bill_no`, `ore_bill_date` | hàng, phiếu quặng của khách |
| `weight_origin_t`, `weight_dest_t`, `loss_pct`, `weight_kg` | cân đầu, cân cuối (tấn), hao hụt %, tấn tính cước × 1000 |
| `vehicle_id`, `truck_no`, `plate_head`, `plate_trailer`, `driver_id`, `driver_name` | xe có **hai biển**: đầu kéo và rơ-moóc |
| `pod_no`, `pod_date`, `pod_receiver`, `pod_condition`, `pod_signed_at`, `pod_signature_count` | biên bản giao nhận. `pod_condition`: `du` (đủ), `thieu` (thiếu), `hong` (hư hỏng) |
| `currency` = `currency_thu` | tiền cước |
| `currency_chi` | `LAK` — tổng chi cộng bằng Kíp |
| `fx_rate_to_lak`, `fx_rates_on_trip` | tỷ giá **khoá trên phiếu**: 1 đơn vị tiền = bao nhiêu Kíp |
| `price_basis`, `billed_qty`, `unit_price` | `ton` (theo tấn) hoặc `trip` (trọn chuyến); số tấn tính cước; đơn giá |
| `selling_price` = `final_selling_price`, `customer_surcharge_total` (luôn 0), `final_selling_price_lak` | cước |
| `actual_cost_total_lak`, `cost_by_section_lak` | tổng chi **EPL chịu**, và theo mục `III` nhiên liệu · `IV` đi đường · `V` sửa chữa · `VI` chi khác |
| `margin_lak`, `margin`, `margin_currency` | lãi: xe nhà = cước − chi; xe thuê = cước − tiền thuê |
| `actual_cost_total`, `actual_cost_total_quy_doi` | (thêm 01/10 cho màn "Vụ việc") tổng chi theo `currency_chi` (LAK) = `actual_cost_total_lak`; tổng chi quy về tiền cước, `null` khi cước là Kíp |
| `margin_amount`, `margin_percent` | (thêm 01/10) = `margin`; tỷ suất lãi % trên cước |
| `fx_rate`, `fx_rate_source` | (thêm 01/10) 1 LAK = bao nhiêu tiền cước, theo tỷ giá khoá trên phiếu; `null` khi cước là Kíp |
| `invoiced`, `inv_no` | giữ tên khoá; từ 01/10 hoá đơn là SO bên anh: `invoiced` = DO đã có SO (gửi SO `synced`), `inv_no` = số SO (`TK-…`), chưa có thì `null`. Trạng thái thu tiền đọc lại ở hệ anh (12.11.2) |
| `completed_at`, `completed_by` | lúc khoá (UTC, `+00:00`), người khoá |
| `hire` (**chỉ xe thuê**) | `{currency, unit_price, amount, amount_lak, fee_pct, fee, over_limit_t, over_t, over_deduction, advanced_by_epl, pay_owner, pay_owner_lak, owner_self_paid_lak, acc_code: "621/4022", acc_code_note}` |

- `hire.amount` = tiền thuê xe, `fee` = phí 2 %, `over_deduction` = trừ quá tải, `advanced_by_epl` = EPL đã ứng (quy về tiền thuê), `pay_owner` = còn phải trả chủ xe.
- `hire.acc_code` = **`621/4022`** (chốt 01/10): Nợ 621 chi phí vận chuyển / Có 4022 phải trả chủ xe, bằng `amount`, lúc khoá phiếu (mục 8, lỗ hổng 1). Bên em ghi khoản này thành **bút toán chờ** nguồn `thue_xe` lúc khoá phiếu, gửi qua API bút toán tổng hợp bên anh khi bật cờ (12.12.4). Phí và trừ quá tải chưa có bút toán riêng.

**`details[]`** — dòng 1 là **thu**, các dòng sau là **chi**:

| Khoá | Dòng thu | Dòng chi |
|---|---|---|
| `line_no`, `kind` | 1, `thu` | 2, 3…, `chi` |
| `charge_type` | `freight` | khoá khoản mục (`diesel`, `x_toll`, `x_tire`…) hoặc tên mục |
| `section`, `section_name` | `null` | `III` · `IV` · `V` · `VI` và tên mục |
| `item_key`, `name`, `name_lo` | — | khoá khoản mục; tên tiếng Việt, tiếng Lào (tên phụ tùng nếu lấy kho) |
| `qty`, `unit_price`, `actual_amount`, `currency` | tấn (hoặc 1), đơn giá, cước, tiền cước | lượng, đơn giá, thành tiền **theo tiền của dòng** |
| `calculation` | `29.7 t × 30.5 USD` hoặc `trọn chuyến` | `120 × 12,500 LAK` (thêm 01/10 cho màn "Vụ việc") |
| `amount_lak` | cước quy Kíp | thành tiền quy Kíp theo tỷ giá khoá trên phiếu |
| `acc_code` | `1211/708` | **Nợ/Có** theo bảng 7.3 (ví dụ `625/1371`, `625/4021`, `614/1601`, `4022/707`) |
| `missing_acc_code` | `false` | `true` nếu dòng EPL chịu mà chưa có mã (thử 30/09: **không có dòng nào**) |
| `paid_by` | `null` | `epl` — EPL chi; `chu_xe` — chủ xe tự trả, **không có `acc_code`** và không cộng vào tổng chi |
| `source` | `cuoc` | `kho` (lấy kho), `mua` (mua ngoài), `null` (khoản đi đường) |
| `sale_to_owner` | — | `true`: dầu / phụ tùng kho **bán cho chủ xe** (xe thuê). `unit_price` là **giá bán**, `acc_code` là `4022/707` |
| `ghi_no`, `place_id`, `supplier_id`, `part_id`, `note`, `ref_id` | `ref_id` = mã phiếu | ghi nợ trạm / nhà cung cấp; điểm đổ; nhà cung cấp; phụ tùng; ghi chú; mã dòng bên em |

Luật con số:

- Σ `amount_lak` các dòng `paid_by = "epl"` = `actual_cost_total_lak`. Có thể lệch **tối đa 1 Kíp mỗi dòng**, vì tổng được làm tròn theo mục.
- Dòng thu: `actual_amount` = `header.final_selling_price` và `currency` = `header.currency`.
- Mọi `acc_code` là **mã thật** trong danh mục Lào, kể cả ba mã con **1371, 4021, 4022** (đã mở 01/10 trên DB của API ở máy, mục 1.1).

#### 12.8.4. Thử với nhau

- Bên em đã thử trên bản sao dữ liệu (`kiem/thu_ban_giao.py`): **13 DO đã khoá**, trong đó 2 phiếu xe thuê; **đạt cả 32 chỗ kiểm** (01/10, gồm cả các khoá màn "Vụ việc" đọc).
- Để hệ anh gọi được sang, trang điều xe Lào phải có **địa chỉ ra Internet**. **Chủ dự án chốt 01/10:** làm xong hết rồi mới host, lúc đó bên em gửi anh địa chỉ gốc và khoá bàn giao.
- Khi có địa chỉ, bên em gửi anh: **địa chỉ gốc** (địa chỉ cuối, `https://`, không chuyển hướng) và **khoá bàn giao**. Đặt `LogisticsSource:BaseUrl` / `ApiKey` vào cấu hình host (không đưa lên git — **cần quyền host**), rồi gọi thử `cash-voucher-references?type=DO`.
- Trên máy: API của anh bản `ce95b3c` chạy ở cổng riêng, `LogisticsSource` trỏ trang điều xe thử 8011, đọc đúng DO bên Lào; 15 lệnh GET so với bản trước đó cho kết quả như nhau (mục 16.7 tài liệu hiện trạng của anh).

**Câu hỏi 12.8 (đã có lời đáp):**

1. (Chủ dự án) Trang điều xe Lào ra Internet ở địa chỉ nào — chủ dự án host khi làm xong hết (01/10), rồi gửi anh địa chỉ và khoá.
2. Lưu khoá Logistics theo từng đơn vị — có trong `ce95b3c`: `LogisticsSource:Branches:<BranchId>` (12.9.2).
3. Lọc theo mã khách bên anh — danh mục khách bên em có ô "Mã khách" (= `OBJ_OBJECTNO` bên anh, không trùng), theo luật mã của anh: mở đầu bằng chữ Latinh hoặc số, chỉ chữ, số và `_ . -` (không `/`), tối đa 37 ký tự. Mỗi dòng và header trả mã đó ở `customer_id` và `customer_code`; tham số `customer_id` nhận cả mã đó. Khách chưa có mã thì lúc gửi SO bên em tự tạo `EPLKH-…` (12.11.1).

### 12.9. Source của anh — đối chiếu và phần bên em đã sửa

Hai kho mã của anh, tách từ nhánh `feat/DemoLao` (`31c98db` / `de04913f`):

| Repo | Nhánh | Commit hiện tại |
|---|---|---|
| `GLS-QLSX-APIs` | `feat/HonTunedaHai` | `b9227aa` |
| `GLS-QLSX-Web` | `feat/hontunedhai_Laos` | `7d168744` |

Từ chiều 01/10 chủ dự án cho bên em **sửa thẳng** source của anh; "bên mình với anh Tune giờ là một", nên các việc trên source bên EPL làm luôn. Bên em thử bằng API và WEB chạy ở máy, trên DB demo Lào anh đã sao lưu; không tự chạy migration, không sửa thủ tục có sẵn, không mở cấu hình bí mật vào tài liệu. Hai script mới (`e2ef52f` che audit cũ, `b9227aa` thêm ba thủ tục bút toán) **chưa chạy** ở DB nào. Chưa push nhánh nào lên GitHub. Tài liệu hiện trạng phía anh: `GLS-QLSX-APIs/docs/PHIEU-THU-CHI-DEMOLAO-TONG-HOP.md` (mục 16 là phần bàn giao).

| Commit | Nội dung |
|---|---|
| `465748b` | nguồn DO đọc cấu hình `LogisticsSource`, gửi khoá; DO hiện số phiếu / tên khách; báo rõ lỗi khoá / DO |
| `be123e9` | `ObjectService`: tạo đối tượng không gửi `IsOrganization` thì là cá nhân (trước đó 500, `OBJ_ISORG` NULL) |
| `64ce7a4` | Vụ việc: có từ khoá thì gửi `q`, tìm trên toàn bộ DO |
| `ce95b3c` | theo chuẩn QLSX: `CashVoucherReferenceService` + `LogisticsDeliveryOrderClient`, contract typed, thiếu `LogisticsSource:BaseUrl` → 503; `CashVoucherHeaderTotals` — máy chủ tự tính tổng header phiếu thu chi |
| WEB `f382a9e8` | modal Vụ việc: thoát ký tự chuỗi DO; số phiếu, xe, tài xế; tỷ giá nhỏ hơn 1 đọc xuôi |
| WEB `06a14189` | phiếu thu / chi: `isCash` theo hình thức thanh toán; `AccountCode` + `currencyId`; tổng xem trước; phân loại theo DOTY |
| `ed5aa0e` | nhật ký kiểm toán: bỏ `CancellationToken` khỏi payload (hết "Đặt log sai"); che mật khẩu / token / khoá trong payload và query string |
| `ae0e7f6` | máy chủ tự tính quy đổi từng dòng (`Amount × tỷ giá dòng`, thiếu thì tỷ giá header) trước khi cộng tổng header |
| WEB `7e14421c` | đổi hình thức / nội tệ / loại tiền thì vế tiền dòng đổi theo; đổi quốc gia chặn trước khi nạp; DOTY gom một chỗ |
| WEB `77bcb0a1` | loại phiếu không đổi ngầm (58/60, 15/17 sửa được, loại khác chỉ xem); đổi tài khoản tiền theo cờ `moneyAccountIsDefault`; hình thức không rõ thì chặn lưu; modal Vụ việc thoát ký tự cả DEAL / QUOTE |
| `e2ef52f` | script `20261001_audit_redact_secrets.sql`: che mật khẩu / token / khoá trong dòng audit cũ (UPDATE dữ liệu; từ `2b4e274` trong tệp `@Apply` mặc định **0** — chỉ chẩn đoán; lưu kết quả chẩn đoán rồi sửa thành 1 để che) — chạy lúc triển khai |
| `0d4eed9` | nhật ký kiểm toán che thêm trường `jwt`, `cookie` |
| WEB `fce78c52` | tiền tệ ngoài danh mục giữ đúng mã, phiếu chỉ xem; phiếu mới thiếu tiền tệ chặn lưu; công nợ xem trước theo tỷ giá header; tab **Tài khoản** ở hồ sơ nhân viên |
| WEB `7d168744` | log WEB che mật khẩu / token / khoá / jwt / cookie; không in `Authorization` vào log |
| `b9227aa` | **API bút toán tổng hợp** `integrations/logistics/journal-entries` (tạo + ghi sổ tạm, gỡ, đọc lại) + script `20261001_logistics_journal_entry.sql` (đã áp DB demo 02/10; host chưa) — 12.12.4 |

#### 12.9.1. Tạo SO — `LogisticsPushController`, `LogisticsPushValidator`, `sp_Logistics_CreateSalesOrder`

Gói bên em gửi khớp từng luật kiểm của anh. Bên em chép đúng các luật đó thành một bộ kiểm (`kiem/thu_luat_so_ben_tune.py`, không gọi sang máy anh) rồi chạy trên **13 DO đã khoá: cả 13 đều qua**.

| Luật bên anh | Bên em |
|---|---|
| Chỉ ba khoá gốc `schemaVersion`, `header`, `details`; `schemaVersion = 1` | đúng |
| `Idempotency-Key` khớp `[A-Za-z0-9][A-Za-z0-9_.:-]{0,99}` | `logistics:EPLLAO-<12 ký tự>` |
| `do_id` ≤ 100, `customer_id` ≤ 50, `route.id` ≤ 50 ký tự. Mở đầu bằng chữ hoặc số, sau đó chỉ chữ, số, `_ . -` | đúng. **Sửa 01/10:** danh mục khách bên em trước cho phép `/` và cho mở đầu bằng `- _ .`; nay chặn ngay lúc gán mã, theo đúng luật của anh |
| `customer_id + "_" + route.id` ≤ 50 ký tự (mã mặt hàng) | mã tuyến bên em dài 12 ký tự, nên **mã khách tối đa 37 ký tự**. Danh mục khách chặn ngay lúc gán (sửa 01/10) |
| `status = "delivered"`; tiền VND, LAK hoặc USD; `currency = currency_thu` | đúng. Cước THB, CNY bên em chặn trước khi gửi (câu hỏi 10.3) |
| Tiền là số JSON, decimal(18,5), từ 0 tới 9 999 999 999 999 | đúng. **Thêm 01/10:** số có quá nhiều chữ số lẻ để gửi chính xác thì bên em chặn, không gửi một số đã bị làm tròn |
| `selling_price + customer_surcharge_total = final_selling_price` > 0,01; Σ dòng thu = tổng; dòng thu cùng tiền với tổng | đúng, kiểm bằng Decimal |
| Băm SHA-256 trên JSON đã sắp khoá, nên gửi lại phải **cùng nội dung** | lần trước chưa rõ kết quả thì bên em gửi lại **đúng gói đã lưu**, cùng khoá |
| Khách phải có **đúng một** `PUBOBJECT.OBJ_OBJECTNO`, đang hoạt động, tên ≤ 100 ký tự (lỗi 52905) | bên em chỉ kiểm được "có mã hay chưa". Trạng thái và tên là dữ liệu bên anh |

Điều mới biết nhờ đọc mã:

1. **Dòng `chi` — câu hỏi 10.4 đã có lời đáp trong mã.**
   - Anh nhận dòng `chi` và không kiểm tiền tệ của nó.
   - Nhưng dòng `chi` **chỉ được ghép thành chữ** vào mô tả mặt hàng (`PIT_DESCRIPTION`) và ghi chú dòng SO của **khách**; nó không thành bút toán chi.
   - Mô tả dài quá sức chứa của cột thì lỗi 52909.
   - → Bên em **giữ một dòng thu**, không gửi dòng chi. Gửi thì chi phí của EPL hiện lên SO của khách.
2. **403 thân rỗng.** Hệ anh trả 403 không kèm thân khi tài khoản của token không nằm trong `LogisticsSalesPush.AllowedUserIds`, hoặc chưa gắn nhân viên (`ObjectId`). Trước đây bên em chỉ báo "HTTP 403"; nay báo đúng lý do đó. 401 (token sai hoặc hết hạn) cũng được báo rõ.
3. **503 `LOGISTICS_DISABLED`, `LOGISTICS_CONFIG_REQUIRED`, `LOGISTICS_DATABASE_ERROR`.** Bên em coi là "chưa rõ kết quả": lần bấm sau gửi lại đúng gói, cùng khoá — đúng như câu lỗi của anh dặn.
4. **Chi nhánh 1368, người tạo `OBJ_AUTOID = 4`, quốc gia 11 được ghi cứng trong thủ tục.** Khi có **đơn vị riêng cho EPL Lào** trên host (12.7.5, việc 5 — **cần quyền host**) thì thủ tục phải đổi theo: bên EPL làm. Bên em không gửi chi nhánh trong gói.
5. **Kết quả một lần tạo.** SO lên trạng thái 5 (hoàn thành), kèm phiếu bán `RESTICKET` và một dòng công nợ `RESCUSTOMERSDEBT` chưa trả. Không có hoá đơn, phiếu thu, sản xuất hay kho. Bên em lưu lại `orderCode`, `retkCode`, `totalAmount`, `initialDebtAmount` mà anh trả về.
6. **Các ô thủ tục dùng thêm:**
   - `header.route.name` (cắt còn 200 ký tự), `route.distance_km`;
   - `origin` → `destination` (ghép thành thông tin tuyến);
   - `destination` (địa chỉ giao).

   Bên em gửi đủ các ô này.

#### 12.9.2. Nguồn DO cho phiếu thu chi — `CashVoucherReferenceService` và màn "Vụ việc"

**Hiện trạng (`ce95b3c`):**

- `CashVoucherReferenceController` chỉ còn HTTP / claims / envelope. Kiểm tham số, lọc, phân trang, map dòng typed (`CashVoucherReferenceRow`, `CashVoucherReferenceListResult`, `CashVoucherReferenceDetailResult`) và cấp phiếu xác nhận nằm ở `CashVoucherReferenceService`.
- Gọi Logistics ở `LogisticsDeliveryOrderClient` (typed HttpClient đăng ký ở `AccountingModule`): hết giờ 15 giây, gói tối đa 2 MB, **không chuyển hướng**, không ghi header `Authorization` vào log.
- Cấu hình (không đưa lên git; mẫu khoá ở `Database/Scripts/logistics-source-config.example.json`):

  ```json
  "LogisticsSource": { "BaseUrl": "https://<địa chỉ trang điều xe Lào>/api/", "ApiKey": "<khoá bàn giao>",
                       "Branches": { "1368": { "BaseUrl": "…", "ApiKey": "…" } } }
  ```

  Chi nhánh trong claims có `BaseUrl` riêng thì dùng cả `BaseUrl` lẫn `ApiKey` của chi nhánh — khoá chung không gửi sang máy khác.
- **Thiếu hoặc sai `BaseUrl` → 503** "Chưa cấu hình nguồn Logistics". Không còn địa chỉ mặc định EPL_System 1506.
- Lỗi nguồn: Logistics 401/403 → 502 "Logistics từ chối khoá truy cập"; chi tiết DO 404 → 404, 409 → 409 "DO chưa hoàn tất hoặc chưa khoá"; quá 15 giây → 504; lỗi khác / JSON hỏng → 502.
- Danh sách: có `keyword` thì gửi `q` cùng `page` / `page_size`; nguồn trả lại đúng `data.q` thì `Total` / `HasMore` theo kết quả đã lọc, `SearchScope = ALL`; nguồn không hiểu `q` thì lọc trong trang đã tải (`SearchScope = CURRENT_PAGE`).
- Dòng DO: `SourceCode` = `doc_no` (không có thì `do_id`), `SourceName` = `customer_name` (không có thì `customer_id`), `Summary` = dòng gốc.
- Chi tiết DO phải `header.status = delivered` và `header.do_id` đúng mã đã chọn, không thì 409.
- **Đã thử** ở máy: bản `ce95b3c` và bản trước đó, cùng 15 lệnh GET trỏ trang điều xe thử 8011 — 14 phản hồi giống từng byte, chi tiết DO chỉ khác phiếu xác nhận và thời điểm chụp; bỏ cấu hình thì DO trả 503.
- Gói bên em: một DO 4–7,4 KB (4–10 dòng); một trang 13 DO 11 KB; mỗi lời gọi dưới 0,4 giây — dưới giới hạn trên.

**Gói bàn giao bên em đã theo màn của anh (01/10).** Khoá cũ giữ nguyên tên; chỉ đổi nghĩa `customer_id` và thêm khoá mới.

| Màn "Vụ việc" đọc | Trước | Nay |
|---|---|---|
| `customer_id` — hiện làm "Khách hàng / Tên", dùng để tìm | mã khách nội bộ bên em (12 ký tự hex), thủ quỹ đọc không hiểu | **mã khách bên anh** (`OBJ_OBJECTNO`), trùng `customer_id` trong gói tạo SO. Khách chưa được gán mã thì `null`. Mã nội bộ bên em chuyển sang **`customer_ref`** |
| `trip_status` | không có | `completed` |
| `actual_cost_total` (theo `currency_chi`) | không có, màn hiện 0 | tổng chi EPL chịu, bằng Kíp |
| `actual_cost_total_quy_doi` | không có | tổng chi quy về tiền cước (chỉ khi cước không phải Kíp) |
| `margin_amount`, `margin_percent` | bên em đặt tên `margin`, màn hiện 0 | lãi theo tiền cước; tỷ suất lãi % |
| `fx_rate`, `fx_rate_source` | không có | 1 `currency_chi` (LAK) bằng bao nhiêu tiền cước, theo tỷ giá khoá trên phiếu (chỉ khi cước không phải Kíp) |
| `details[].calculation` | không có | cách tính một dòng, ví dụ `29.7 t × 30.5 USD`, `120 × 12,500 LAK` |

**Màn "Vụ việc"** (`wwwroot/ViewAssets/scripts/ACC/cm-source-reference-modal.js`, WEB `f382a9e8`): DO hiện số phiếu, dòng phụ "số xe · biển số — tài xế"; chuỗi DO được thoát ký tự trước khi chèn HTML; tỷ giá nhỏ hơn 1 hiện đảo chiều ("1 USD = 22.000 LAK"). Phần DEAL / QUOTE của modal chưa thoát ký tự (mục 16.8 tài liệu của anh).

#### 12.9.3. Hoá đơn điện tử (commit `3b5d159`, 01/10)

Anh vừa thêm một dịch vụ riêng, `Backend.LaoInvoice`: mẫu hoá đơn, tờ khai đăng ký phát hành, hoá đơn đầu ra (ký thử, chưa gửi cơ quan thuế).

- Dịch vụ này **chưa nối với SO hay DO**, nên bên em **không gọi**.
- Hoá đơn vẫn là việc bên anh (mục 0.1). Khi anh nối hoá đơn với SO, bên em chỉ cần đọc lại số hoá đơn (câu hỏi 10.5).

#### 12.9.4. Phiếu thu chi — tổng header và WEB

- **Tổng header do máy chủ tính** (`CashVoucherHeaderTotals`, `ce95b3c`), ở create-session, save-session, save-and-commit, trước khi lưu header tạm: `Header.Amount` = Σ `Amount`, `Header.BaseAmount` = Σ `BaseAmount` của `Entries` (relation công nợ có ID thì Σ `PaymentAmount` / `PaymentBaseAmount`). Làm tròn từng dòng 5 số lẻ, nửa xa số 0. Chỉ `BaseAmount` xuống thủ tục header (`CMP_BASEAMOUNT` / `CMR_BASEAMOUNT`).
  - Phiếu có relation IV/IC, hoặc relation công nợ thiếu số tiền: máy chủ chưa tính được, **giữ số header client gửi** (đường tương thích).
  - Mọi phiếu bên em chỉ có `Entries`, nên luôn được tính lại. Ví dụ trả chủ xe ngoại tệ: header quy đổi = Σ quy đổi các dòng, không lấy số tổng bên em tính riêng.
  - `BaseAmount` **từng dòng** máy chủ tự tính trước khi cộng (`ApplyLineBaseAmounts`, `ae0e7f6`): `Amount` × (tỷ giá dòng, thiếu thì tỷ giá header), 5 số lẻ, nửa xa số 0; công nợ DEP/DEPT có `PaymentBaseAmount` thì tính lại theo tỷ giá header. Giữ số client khi thiếu nguyên tệ, tỷ giá ≤ 0, dòng IV/IC. Bên em gửi tỷ giá riêng từng dòng cho phiếu trả chủ xe ngoại tệ (mỗi phiếu xe một tỷ giá khoá).
- **WEB** (`06a14189`, `7e14421c`, `77bcb0a1`): `isCash` theo hình thức thanh toán; tài khoản tiền mặc định đọc đúng `AccountCode`, gửi kèm `currencyId` (chỉ có tác dụng khi có `bankId`; WEB chưa có ô chọn ngân hàng); đổi hình thức / nội tệ / loại tiền khi đã có dòng thì vế tiền dòng đổi theo, dòng tự chọn giữ nguyên; đổi quốc gia khi đã có dòng thì chặn trước khi nạp danh mục; đổi tài khoản tiền theo cờ `moneyAccountIsDefault`; hình thức không rõ thì chặn lưu; modal Vụ việc thoát ký tự cả DEAL / QUOTE.
- **Phân loại loại chứng từ** ở WEB và API ghi cứng DOTY 58/60, 15/17, vì `document-types` chỉ trả `DOTY_AUTOID`, `DOTY_ISCMP`, `DOTY_ISCMR`, `DOTY_NAME`. Từ `77bcb0a1` WEB không đổi loại phiếu ngầm: phiếu 59 "Chi trước" (tạm ứng bên em tạo) và loại khác ngoài 58/60, 15/17 mở **chỉ xem**, không mất dòng. Cờ phân loại ở `document-types`: bên EPL làm (đang làm).

**Việc còn lại:**

1. `LogisticsSalesPush.AllowedUserIds` trên host giữ `846` (tài khoản `tune`, trang điều xe đang dùng). Nếu sau này có tài khoản tích hợp (tuỳ chọn, câu hỏi 10.1, 12.12.3) thì thêm `UserId` của nó — **cần quyền host**.
2. Nếu tạo đơn vị riêng cho EPL Lào: đổi chi nhánh 1368 đang ghi cứng trong `sp_Logistics_CreateSalesOrder` (12.9.1, điều 4) — bên EPL làm khi có đơn vị (tạo đơn vị: **cần quyền host**).
3. Cho `document-types` trả cờ phân loại (công nợ / khác / trước) — bên EPL làm (đang làm).
4. Nhật ký kiểm toán đã sửa (`ed5aa0e`, `0d4eed9`); dòng audit cũ có thể còn mật khẩu dạng chữ thường: chạy script che `20261001_audit_redact_secrets.sql` (`e2ef52f`) trên DB host, cân nhắc đổi mật khẩu — **cần quyền host**.

### 12.10. Tạm ứng: chi thật ở hệ anh, trạng thái về trang điều xe (đã nối 01/10/2026)

**Chủ dự án chốt chiều 01/10:** tiền tạm ứng chi thật ở hệ anh; chi xong thì trạng thái về bên em. Câu hỏi 10.6 đã có lời đáp. Cũng từ chiều 01/10, chủ dự án cho bên em sửa thẳng mã nguồn của anh (anh bận); nối thử bằng API chạy ở máy (localhost) trên DB demo Lào anh đã sao lưu.

#### 12.10.1. Luồng

1. Bãi lập phiếu, in tờ **đề nghị tạm ứng** (PTU). KT Chi phí VC kiểm, rồi **ghi sổ mục IV** trên trang điều xe.
2. Ghi sổ xong, trang điều xe **tự tạo phiếu chi bên anh**, chưa ghi sổ:

   | Ô | Giá trị |
   |---|---|
   | `VoucherType` | `CMP` |
   | `DotyAutoId` | **59 "Chi trước"** (cấu hình `QLSX_DOTY_CHI_TAM_UNG`) |
   | `ObjectId` | xe nhà: **tài xế** — bên em tạo nhân viên qua `master-data/staff/upsert`, mã `EPLTX-<mã tài xế bên em>`; xe thuê: **chủ xe** `EPLCX-…` (12.11.3) |
   | `CurrencyId` | LAK, tra ở `GetAllCurrency` (máy demo: 26) |
   | `FiciAutoId` | kỳ chứa ngày lập, tra ở `GetFinancyCicle` (10/2026: 19) |
   | `RefDocumentNo` | **số tờ PTU** bên em, ví dụ `PTU-T4-0449-09/EPL` |
   | `Entries` | một dòng, định khoản theo bảng bên em: xe nhà **Nợ 1601 / Có 1011**; xe thuê Nợ 4022 / Có 1011 |
   | `PostMode` | `None` (chưa ghi sổ) |

3. **Thủ quỹ chi tiền mặt cho tài xế và GHI SỔ phiếu đó ngay trong hệ anh** (màn Phiếu chi, nút Ghi sổ).
4. Trang điều xe **hỏi lại** phiếu (`GET …/cmpayment-receipt/{id}?voucherType=CMP`). Thấy `Master.STATUS` là 12 (ghi sổ chính) hoặc 13 (ghi sổ tạm) thì:
   - mục IV thành **"đã chi"**, ghi nhật ký là người ghi sổ bên anh;
   - tờ PTU thành **"đã cấp"** (Tất toán đếm "đã ứng" theo tờ này);
   - tài xế **xuất phát được**.

Bên em hỏi lại lúc mở tờ ở màn Phiếu đề nghị chi, lúc tài xế bấm Xuất phát, và khi bấm nút Cập nhật. Trang điều xe chưa ra Internet nên **hệ anh không cần gọi sang bên em**.

#### 12.10.2. Điều bên em đã giữ

- **Chống trùng** (API phiếu chi không có Idempotency-Key): trước mỗi lần tạo, bên em tìm qua `POST …/list` theo **đối tượng + `DOC_REFDOCUMENTNO` = số PTU**. Có rồi thì dùng lại phiếu đó, không tạo phiếu thứ hai.
- **Số tạm ứng đổi khi phiếu bên anh chưa ghi sổ:** bên em xoá phiếu cũ (`POST …/delete`) rồi lập phiếu đúng số.
- **Phiếu đã ghi sổ bên anh** thì bên em không xoá, không sửa. Số tạm ứng đổi sau đó thì phần chênh tính lúc tất toán tài xế.
- **Xoá phiếu xuất xe, hoặc huỷ tờ tạm ứng, bên em:**
  - phiếu chi bên anh **chưa ghi sổ** thì bên em **rút** (xoá bên anh);
  - **đã ghi sổ** thì bên em chặn xoá (409 `DA_CHI_O_KE_TOAN`), đối soát bên anh trước.
- **Quỹ trên trang điều xe không chi mục IV nữa** (nút Chi, quét QR đều trả 409 `CHI_O_KE_TOAN`).
  - Sếp vẫn chi tay được, cho lúc hệ anh không vào được.
  - Sếp chi tay thì bên em rút phiếu chi còn chờ bên anh trước, để thủ quỹ không chi lần nữa.
- Lỗi về dạng HTTP 200 kèm `Success: false` cũng được đọc ra; câu lỗi của anh hiện lên màn để KT Chi phí **Gửi lại**.
- **Phiếu bị xoá tay bên anh** (`Master` null): bên em đánh `PHIEU_CHI_MAT`, không kẹt "chờ chi"; gửi lại thì lập phiếu mới, không gọi xoá nữa. Áp cho mọi phiếu bên em tạo (tạm ứng, trả chủ xe, chi mục V – VI, tất toán, trả nhà cung cấp).
- Dự phòng: đặt `EPL_CHI_TAM_UNG=tai_cho` thì quay về Quỹ chi trên trang điều xe như trước.

#### 12.10.3. Đã thử (máy thử, API chạy ở máy, DB demo Lào)

`kiem/thu_chi_tam_ung_ke_toan.py` — **29 chỗ kiểm, đạt hết**, gồm:

- ghi sổ mục IV → phiếu `1368-CTR-261001-…` "Chi trước" 580.000 LAK, `STATUS` 1, Nợ 1601 / Có 1011, tham chiếu đúng PTU;
- Bãi thấy trạng thái nhưng không thấy số tiền;
- Quỹ bấm chi / quét QR → 409;
- tài xế bấm Xuất phát → 409, câu báo nói số phiếu chi;
- (đóng vai thủ quỹ) ghi sổ bên anh → tài xế xuất phát được ngay; mục IV đã chi, PTU đã cấp, nhật ký ghi tên người ghi sổ bên anh;
- gửi lại không tạo phiếu thứ hai;
- xoá phiếu có phiếu chi chờ → phiếu chi bên anh được rút.

Các phiếu thử bên anh có số tham chiếu `PTU-THU-CK-…` và `PTU-T4-CHO-…`. Đối tượng thử là `EPLTX-THU01`.

#### 12.10.4. Còn mở

- **Mã 4022** đã mở trên DB của API ở máy (12.12.1); tạm ứng xe thuê đứng tên **chủ xe**, Nợ 4022, đã chạy (`1368-CTR-261001-00013`). DB nào còn thiếu mã thì màn bên em hiện rõ câu từ chối, KT Chi phí gửi lại sau khi mở mã.
- **Token:** đang dùng token cá nhân `tune`, hết hạn 10/10/2026. Hết hạn thì không tạo được phiếu chi, tài xế không xuất phát được (Sếp chi tay được). Trước hạn: thay token mới trong `.env`, hoặc đặt `QLSX_USERNAME` / `QLSX_PASSWORD` của anh để tự đăng nhập lại (12.11.4).
- **Đơn vị:** đang ghi vào chi nhánh 1368 "Demo EPL" (cấu hình `QLSX_ORG_ID`). Có đơn vị EPL Lào riêng thì đổi cấu hình.
- **WEB:** phiếu 59 "Chi trước" không có trong ô chọn loại chứng từ của WEB (12.9.4); thủ quỹ xem và ghi sổ ở danh sách / chi tiết, đừng mở sửa.

### 12.11. Xe thuê ngoài, SO, khách, công nợ, token đăng nhập

Tất cả đã thử qua API chạy ở máy (localhost), trên DB demo Lào anh đã sao lưu.

#### 12.11.1. Đề nghị thu → SO

- Khách **chưa có mã bên anh**: lúc KT Thu/Chi bấm "Tạo SO", bên em tạo khách bên anh qua `master-data/customers/upsert`, mã `EPLKH-<mã khách bên em>`. Mã đó ghi luôn vào ô "Mã khách (bên kế toán)" bên em. Hộp xác nhận báo trước mã sẽ tạo.
- Khách **đã có mã**: bên em kiểm mã đó có thật bên anh trước khi gửi, báo sớm thay vì chờ lỗi 52905.
- **Cắt sổ 01/10 (chủ dự án):** mọi DO đã khoá gửi SO **từ đầu**. Bên em **không còn** chặn DO đã có hoá đơn / đã thu ở trang kế toán tạm — luật `DA_HOA_DON_TRANG_TAM` đã bỏ, vì số tiền trên trang tạm là số thử, bỏ hết. Công nợ khách chỉ còn ở hệ anh.
- **Đã tạo** `TK-20261001-000162` (T4-0449-09/EPL, ຄຳຕຸ້ຍ, 905,85 USD) và `TK-20261001-000163` (T4-0442-09/EPL, ນາງ ວັນນາ, 1.676,90 USD) trên DB demo anh đã sao lưu. Hai SO tạo ngày 01/10 trước giờ cắt sổ, **giữ nguyên**, là công nợ thật của hai DO đó.
- **Lỗi bên anh, bên em đã sửa** (`be123e9`): tạo khách qua API mà không gửi `IsOrganization` thì cột `OBJ_ISORG` bị NULL, máy chủ văng 500. `ObjectService.ApplyDomainDefaults` nay mặc định **cá nhân**. Bên em cũng luôn gửi ô này.

#### 12.11.2. Công nợ khách và "đã thu" của SO: đọc từ hệ anh

- Màn Khách hàng → tab Công nợ có khối **"Công nợ bên hệ kế toán"**. Khối đọc `POST /api/v1/sales/debt/customer-detail` và hiện: tổng nợ, đã thu, quá hạn, tuổi nợ, từng SO còn nợ. **Chỉ xem**: thu tiền, hoá đơn làm ở hệ anh.
- **Kế toán bên anh thu tiền SO** ở WEB **Chi tiết công nợ khách hàng** (`/DebtCollection/CustomerDetail`) → **Tạo phiếu thu** → **Xác nhận thu nợ** → `POST /api/v1/sales/debt/collection-upsert` (`DocumentType = "TKN"`) → `sp_RES_CreateDebtCollection_COUNTRY`: phiếu thu nợ RES (số dạng `4-TKN-1368-2-261001-0001`), trừ dư nợ `RESCUSTOMERSDEBT` của đúng `RetkAutoId`, và sinh **phiếu thu CMR 17 "Thu khác"** chưa ghi sổ (`ST_AUTOID` 1; số `<CounterId>-<số DOTY 17>`, dạng `4-1368-TK-261001-00009`), một dòng Nợ tài khoản tiền theo vai (`BANK_LOCAL` → 1021, `CASH_LOCAL` → 1011) / Có tài khoản vai `CUSTOMER_GOODS` (1211). Không dùng phiếu thu "Thu công nợ" (CMR 15): công nợ SO không hiện ở đó (0 dòng).
- Hai lỗi đã thấy khi đi thật luồng này (01/10): (1) hộp **Tạo phiếu thu** chỉ có tài khoản tiền **nội tệ** (`CASH_LOCAL`, `BANK_LOCAL`) và gửi tỷ giá cứng `rate: 1`, `amount = amountCur` (`debtCollectionCustomerDetail.js`), nên SO USD bị ghi số USD thành Kíp — đang sửa (UI-4); (2) mọi SO tạo từ trang điều xe mang **cùng một mã phiếu bán** (`RETK_CODE`) "Demo EPL-2-261001000" — đang tìm nguồn (UI-4).
- Phiếu đề nghị thu đọc lại từ cùng đường này, ghép dòng nợ theo `OrderCode` = SO của DO: còn nợ ≤ nửa xu → **"đã thu"**; đã trả > 0 → **"thu một phần"**; SO không còn trong danh sách nợ mà còn trong đơn hàng của khách → "đã thu". Một khách đọc tối đa một lần mỗi 60 giây; đọc khi bấm Cập nhật.
- Số hoá đơn / đã thu trên trang kế toán tạm là **số thử**, không dùng làm công nợ.

#### 12.11.3. Xe thuê ngoài (xe liên kết)

**Tạm ứng xe thuê:** phiếu chi "Chi trước" đứng tên **chủ xe**. Bên em tạo nhà cung cấp `EPLCX-<mã chủ xe>` qua `master-data/suppliers/upsert`. Định khoản Nợ **4022** phải trả chủ xe / Có 1011. EPL ứng thì trừ vào tiền trả chủ xe.

**Trả chủ xe** (màn Xe liên kết → nút **Trả qua kế toán** của từng chủ xe):

1. Bên em liệt kê phiếu xe thuê **đã khoá, chưa trả**, kèm số còn phải trả = tiền thuê − phí − trừ quá tải − EPL đã ứng (cùng số bên em vẫn tính).
2. KT Thu/Chi VC (hoặc Sếp) chọn phiếu, chọn tiền mặt hay chuyển khoản → **Lập đề nghị trả**.
3. Bên anh nhận phiếu chi **"Chi khác"** (DOTY 60):
   - đứng tên chủ xe;
   - mỗi phiếu xe một dòng **Nợ 4022 / Có 1011 · 1012 · 1021 · 1022** (theo cách trả và tiền thuê);
   - số tham chiếu `TCX-…`.
4. Thủ quỹ chi và **ghi sổ** bên anh. Bên em đọc lại; `STATUS` 12/13 thì các phiếu thành **"đã trả chủ xe"**.

Luật bên em giữ:
- mỗi đề nghị một loại tiền;
- tổng ≤ 0 (EPL ứng nhiều hơn tiền thuê) thì không lập;
- phiếu đang nằm đề nghị thì không vào đề nghị khác, không mở khoá được;
- chỉ đề nghị trả qua hệ anh mới đánh "đã trả chủ xe" (cắt sổ 01/10: đợt trả trên trang kế toán tạm là số thử, bỏ; đánh "đã trả" theo đường khác bị chặn 409 `TRA_QUA_KE_TOAN`);
- bỏ đề nghị chưa chi thì rút phiếu chi bên anh, thả phiếu bán về chờ trừ;
- đã chi thì không huỷ.

**Mã 4022** đã mở (12.12.1); tạm ứng xe thuê và trả chủ xe đã chạy thật. DB nào còn thiếu mã thì phiếu bị từ chối "Tài khoản không hợp lệ theo quốc gia của phiếu", màn bên em hiện rõ câu đó kèm mã đang dùng.

Trong phiếu chi trả chủ xe, hệ anh tính lại quy đổi từng dòng theo tỷ giá dòng bên em gửi (`ae0e7f6`) rồi `Header.BaseAmount` = Σ quy đổi các dòng (`ce95b3c`, 12.9.4).

**Ghi nhận chi phí thuê xe:** đã chốt *Nợ 621 / Có 4022* bằng tiền thuê, lúc khoá phiếu (mục 8, lỗ hổng 1). Bàn giao DO có `hire.acc_code = "621/4022"`. Bên em ghi khoản này thành **bút toán chờ** nguồn `thue_xe` và gửi qua API bút toán tổng hợp bên anh khi bật cờ (12.12.4); phần **ứng** và **trả** đi phiếu chi bên anh như trên.

#### 12.11.4. Token đăng nhập — dùng token của anh, tự đăng nhập lại

**Chủ dự án chốt 01/10: tạm gác tài khoản tích hợp.** Trang điều xe tiếp tục dùng **token của anh** (`EPL_ACC_CODE_TOKEN`, tài khoản `tune`, hết hạn khoảng 10/10/2026). Trước hạn, chọn một:

- thay token mới vào `.env` máy chủ trang điều xe;
- hoặc đặt `QLSX_USERNAME` / `QLSX_PASSWORD` của anh (cùng `QLSX_ORG_ID`, mặc định 1368) để trang điều xe tự đăng nhập lại.

Đường **tự đăng nhập** đã có sẵn: bên em gọi `POST /api/v1/auth/login`, nhớ token và đăng nhập lại khi token còn dưới 5 phút (token bên anh sống 30 ngày); bị 401 thì đăng nhập lại. Thứ tự ưu tiên: `QLSX_ACCESS_TOKEN` → tự đăng nhập → `EPL_ACC_CODE_TOKEN`.

Lưu ý kỹ thuật: `proc_LoginWithUsAndPw` nhận mật khẩu tối đa **20 ký tự** (`VARCHAR(20)`); tài khoản phải được gán chi nhánh (`USERS_ORG`).

Token / mật khẩu là của anh — **cần quyền host**; chỉ đặt vào `.env` máy chủ trang điều xe, không gửi qua chat. Tài khoản riêng: tuỳ chọn, **12.12.3**.

#### 12.11.5. Việc còn lại

| Việc | Vì sao | Người làm |
|---|---|---|
| **Bút toán** cho thuê xe *Nợ 621 / Có 4022*, ghi nợ nhà cung cấp, quyết toán tạm ứng, hàng bán cho chủ xe | API **đã có** (`b9227aa`), đầu gửi đã có (`875a0cf`); **đã chạy thật trên DB demo 02/10** (script `20261001_logistics_journal_entry.sql` đã áp; chứng từ thử `GL0210202xx`, gỡ sạch — 12.12.4) | host: **cần quyền host**; bật cờ ở máy dùng thật: chủ dự án quyết |
| **Bật tiền USD** trong danh mục tiền tệ | USD có (mã 2) nhưng đang tắt nên `GetAllCurrency` không trả; SO vẫn tạo được, nhưng phiếu chi bằng USD cần mã tiền. Tạm thời đặt `QLSX_TIEN_USD=2` là chạy | **cần quyền host** |
| **Token hết hạn khoảng 10/10** (12.11.4) | thay token mới trong `.env`, hoặc đặt `QLSX_USERNAME` / `QLSX_PASSWORD` của anh; tài khoản tích hợp tạm gác, tuỳ chọn (12.12.3) | **cần quyền host** (token / mật khẩu của anh) |
| Mở **1371, 4021, 4022** trên DB host | đã mở trên DB của API ở máy (12.12.1); host khác DB thì còn thiếu (12.12.2) | **cần quyền host** |

### 12.12. Mã tài khoản, hai DB khác nhau, tài khoản tích hợp (tuỳ chọn), bút toán

#### 12.12.1. Đã mở 1371, 4021, 4022 (chủ dự án cho phép)

Làm qua chính API của anh, `accounting/lao-accounts` (API chạy ở máy em, `Env=laos`). Không sửa thẳng DB.

| Bước | Gọi | Kết quả |
|---|---|---|
| 1 | `POST lao-accounts/update` mã **137**, `Posting=false` (giữ tên, cha 13, số dư, nhóm, loại, `Version`) | 137 thành tài khoản **tổng hợp** |
| 2 | `POST lao-accounts` mã **1371**, cha 137, `Posting=true`, dư Nợ, tên ລາວ "ສາງສິນຄ້າ, ວັດຖຸ" | tài khoản lá |
| 3 | `POST lao-accounts/update` mã **402**, `Posting=false` | 402 thành tài khoản **tổng hợp** |
| 4 | `POST lao-accounts` mã **4021** (ໜີ້ຕ້ອງສົ່ງ ຜູ້ສະໜອງ) và **4022** (ເຈົ້າໜີ້ເຈົ້າຂອງລົດຮ່ວມ), cha 402, `Posting=true`, dư Có | tài khoản lá |

Kiểm lại:
- `GET cmpayment-receipt/country-accounts?countryId=11` có đủ 1371, 4021, 4022; không còn 137, 402 (vì đã là tổng hợp).
- `common/country-accounts?tryAutoId=11` trả **497 mã** (trước là 494). Bên em đã chụp lại bản dự phòng (`services/danh_muc_tai_khoan_lao.json`).

**Ảnh hưởng — anh xem giúp:**
- 137 và 402 **không ghi sổ trực tiếp được nữa**. Bên em đã tìm trong cả `GLS-QLSX-APIs` lẫn `GLS-QLSX-Web`: không có chỗ nào ghi cứng 137 / 402, ngoài tệp nạp danh mục `20260909_country_account_import_lao.sql`. Nếu có thủ tục SQL hay màn cũ nào ghi thẳng 137 / 402 thì sẽ bị từ chối, phải đổi sang 1371 / 4021.
- Muốn trả lại như cũ: xoá 1371, 4021, 4022 (khi chưa có bút toán), rồi `update` 137 / 402 với `Posting=true`.

**Đã chạy thật** qua API ở máy (bài thử tự rút phiếu sau khi kiểm):
- tạm ứng xe thuê, phiếu chi "Chi trước" đứng tên chủ xe, Nợ 4022: `1368-CTR-261001-00013`;
- trả chủ xe, phiếu chi "Chi khác" 28.359.600 LAK, Nợ 4022 / Có 1021: `1368-CKH-261001-00001` và `…00002`;
- tạm ứng xe nhà, Nợ 1601: `1368-CTR-261001-00016`.

#### 12.12.2. Bản host chưa có code mới — làm ở máy, triển khai xong đổi link

Chủ dự án chốt 01/10: `demo-lao-api.goldensme.com` **chưa merge** code hai nhánh. Bên em làm và thử mọi thứ trên API chạy ở máy; triển khai lên host xong (**cần quyền host**) thì **chỉ đổi link**.

Gọi cùng một token ngày 01/10, hai bản trả khác nhau:

| | API ở máy (`Env=laos`) | API đang host |
|---|---|---|
| Danh mục quốc gia 11 | 497 mã, có 1371/4021/4022, 137 là tổng hợp | 494 mã, chưa có ba mã |
| Khách `EPLKH-0834a9e9606b` (ObjId 1608) và SO `TK-20261001-000162` | có | không thấy |

Khác vì host chạy code cũ, hoặc host trỏ DB khác. Bên em không xem được cấu hình của host; lệnh kiểm ở dưới trả lời câu này.

| Bên | Khoá | Lúc thử (bây giờ) | Sau khi triển khai lên host |
|---|---|---|---|
| Trang điều xe, máy thử 8011 | `QLSX_BASE_URL`, `EPL_ACC_CODE_API` | cả hai `http://127.0.0.1:5090` (API ở máy): gửi SO, phiếu chi, đối tượng, công nợ và danh mục tài khoản đều đi vòng trong máy | bỏ đi → về host |
| Trang điều xe, máy thật 8020 | `QLSX_BASE_URL` | không đặt → dùng máy của `EPL_ACC_CODE_API` = `https://demo-lao-api.goldensme.com` | giữ nguyên — tự gọi bản mới |
| API anh, cấu hình host | `LogisticsSource:BaseUrl` | máy thử `http://127.0.0.1:8011/api/` | địa chỉ `/api/` của trang điều xe thật — **bắt buộc** từ `ce95b3c`, thiếu thì màn Vụ việc báo 503 |
| API anh, cấu hình host | `LogisticsSource:ApiKey` | khoá của máy thử | khoá Sếp tạo ở trang điều xe thật (`POST /api/handover/tao-khoa`) |
| API anh, cấu hình host | `LogisticsSource:Branches:<BranchId>` | không đặt | chỉ khi chi nhánh có trang điều xe riêng |
| WEB anh | `BACKOFFICE_API_URL` | bản ở máy dùng `Env=laoslocal` trỏ 5090 | `Env=laos` trỏ API host (đã đúng sẵn) |

**Kiểm một lệnh lúc triển khai:** `GET <host>/api/v1/common/country-accounts?tryAutoId=11&onlyActive=true`:
- trả **497 mã** (có 1371 / 4021 / 4022): host cùng DB với bản ở máy, dữ liệu đã có, không làm gì thêm;
- trả **494 mã**: host trỏ DB khác. Chạy `python tools/mo_ma_con_tune.py https://<API host>` (bên em chạy được). Khách, chủ xe, tài xế không cần chép: lần gửi đầu bên em tự tạo.

#### 12.12.3. Tài khoản tích hợp — tuỳ chọn, tạm gác

**Chủ dự án chốt 01/10: tạm gác.** Trang điều xe tiếp tục dùng token của anh (12.11.4). Mục này giữ lại để làm sau nếu cần; **không** phải làm trước triển khai.

Để làm gì: trang điều xe gọi API của anh bằng **một tài khoản riêng của hệ thống**. Hiện bên em đang mượn token cá nhân (`EPL_ACC_CODE_TOKEN`). Người đó đổi mật khẩu hay nghỉ việc thì mọi lần gửi đều hỏng, và sổ của anh ghi người tạo phiếu là người đó.

Code bên anh làm thế này (bên em đọc từ source):

- **Đăng nhập:** `POST /api/v1/auth/login {Username, Password, OrgID}` → thủ tục `proc_LoginWithUsAndPw`.
  - Tên đăng nhập dài 3–20 ký tự; mật khẩu tối đa **20 ký tự** (`VARCHAR(20)`); tài khoản phải được gán chi nhánh (`USERS_ORG`).
  - Token sống **30 ngày** (`Base/Jwt/JwtService.cs`), không có refresh token.
  - Mã người dùng nằm ở claim `UserId` (= `dbo.Users.UserID`).
- **Tạo tài khoản:** `POST /api/v1/master-data/object-auth/account/upsert` (`ObjectAuthController`, thủ tục `sp_META_InsertUpdate_USERS`). Hồ sơ nhân viên bên WEB đã có tab "Tài khoản" (`fce78c52`) gọi đường này; chưa bấm tạo tài khoản thật.
  - `UserId = null` để tạo mới;
  - `ObjectAutoId`: mã nhân viên (`PUBOBJECT`), bắt buộc;
  - `UserName`, `Password`, `IsActive=true`;
  - `OrgAutoId`;
  - `GroupId`: nhóm trong `dbo.UserGroup`.
- **Gửi SO:** `LogisticsSalesPushController` chỉ nhận người có `UserId` nằm trong `LogisticsSalesPush:AllowedUserIds`. Danh sách rỗng thì ai cũng bị 403. Bản `laos` hiện có `[846]`.
- **Phiếu thu chi, tạo khách / nhà cung cấp / nhân viên, công nợ khách:** chỉ cần token hợp lệ, không xét quyền theo chức năng. Phiếu ghi người lập là `ObjectId` của token.

Các bước:

1. Tạo (hoặc chọn) một **nhân viên** tên ví dụ "EPL Logistics (tích hợp)", thuộc chi nhánh **1368** (Logistics).
2. Gọi `account/upsert` tạo tài khoản cho nhân viên đó, ví dụ `UserName = epl_logistics`, mật khẩu ngẫu nhiên **tối đa 20 ký tự**, gán chi nhánh 1368.
3. Lấy `UserId`: `POST /api/v1/hr/employees/account-lookups {UserName}`, hoặc đọc claim `UserId` trong token sau khi đăng nhập thử.
4. Trong cấu hình bản host (`appsettings.<Env>.json`, tệp không đưa lên git), thêm `UserId` đó vào `LogisticsSalesPush:AllowedUserIds` **và** `LogisticsJournalEntry:AllowedUserIds` (giữ `846` nếu còn cần), `Enabled=true`. Cấu hình đọc lại mỗi lần gọi, không cần khởi động lại API.
5. Bên trang điều xe, trong tệp `.env` của máy chủ (không đưa lên git):
   - `QLSX_USERNAME=epl_logistics`
   - `QLSX_PASSWORD=<mật khẩu>`
   - `QLSX_ORG_ID=1368`

   Xoá `QLSX_ACCESS_TOKEN` nếu có, vì biến đó được ưu tiên trước. Khởi động lại.
6. Từ đó bên em tự đăng nhập, nhớ token, đăng nhập lại khi token còn dưới 5 phút. Bị 401 cũng đăng nhập lại ngay.

**Trạng thái 01/10.** Nhân viên ảo `EPL-TICHHOP` "EPL Logistics (tích hợp)" (ObjId **1622**, chi nhánh 1368) đã tạo trên DB demo, **chưa có tài khoản dùng được**. Tab "Tài khoản" ở hồ sơ nhân viên bên WEB đã có (`fce78c52`), dùng khi cần. Khi làm: tạo tài khoản theo các bước trên (mật khẩu ≤ 20 ký tự, gán `USERS_ORG`), thêm `UserId` vào `AllowedUserIds` — trên host thì **cần quyền host**; host khác DB thì tạo lại cả nhân viên.

#### 12.12.4. Bút toán không qua tiền — API bút toán tổng hợp bên anh (`b9227aa`) và đầu gửi bên em (`875a0cf`)

**Trạng thái 02/10:**
- **API bên anh đã có** trong source: `GLS-QLSX-APIs` `feat/HonTunedaHai@b9227aa` (`LogisticsJournalEntryController`). Mô tả đầy đủ (khuôn ghi sổ, mã lỗi, bất biến): tài liệu của anh `PHIEU-THU-CHI-DEMOLAO-TONG-HOP.md` mục 16.9.
- Script `Backend.API/Database/Scripts/20261001_logistics_journal_entry.sql` **đã áp** vào DB demo (chủ dự án chạy, 02/10). **Đã chạy thật** qua máy thử trang điều xe với phiếu thử: thuê xe `GL021020263` / `GL021020264`; xuất kho — xe nhà `GL021020265` *Nợ 625 / Có 1371* 1.590.000 LAK, xe thuê `GL021020267` *Nợ 4022 / Có 707* 1.400.000 LAK (ObjectId chủ xe 1606) + *Nợ 607 / Có 1371* 1.272.000 LAK; ST 13. Mở khoá → gỡ sạch, GET trả 404 `JOURNAL_ENTRY_NOT_FOUND`; không còn chứng từ thử nào trên DB demo.
- Cấu hình `LogisticsJournalEntry` **đã có** ở API chạy ở máy (`Enabled`, `AllowedUserIds` 846, `OrgId` 1368, `CountryId` 11).
- **Đầu gửi bên em đã có**: `services/gui_but_toan_tune.py`, `services/but_toan_cho.py` (`a938301`, `875a0cf`). Cờ `QLSX_GUI_BUT_TOAN` bật trên máy thử lúc chạy lượt thật; máy dùng thật bật khi chủ dự án quyết. `kiem/thu_gui_but_toan.py`, `kiem/thu_but_toan_xuat_kho.py` chạy với máy giả theo đúng giao ước dưới đây (không gọi API thật).
- Host `demo-lao-api`: chưa có code, script, cấu hình — **cần quyền host**.
- Thứ tự bật: **áp script → cấu hình → bật cờ `QLSX_GUI_BUT_TOAN=1` → gọi thử** (lệnh và cách đọc kết quả: `HUONG_DAN_TRIEN_KHAI_ANH_TUNE` mục 4.6).

**Nguồn bút toán** (mục 8; màn "Bút toán chờ gửi", `GET /api/but-toan-cho`). Một bút toán chờ = một lần gọi = một chứng từ tổng hợp bên anh, `Entries` mang đủ các dòng của bản đó:

| Nguồn | Sinh lúc | Định khoản | Mã nguồn | Đối tượng dòng (`ObjectId`) | Tiền của dòng |
|---|---|---|---|---|---|
| `thue_xe` | khoá phiếu xe thuê | Nợ 621 / Có 4022, bằng tiền thuê (`hire.amount`) | `Trip.id` | chủ xe `EPLCX-…` | tiền thuê, theo tiền tệ thuê; tỷ giá khoá trên phiếu |
| `no_ncc` | khoá phiếu có dòng ghi nợ nhà cung cấp | Nợ 625 · 614 (xe thuê 4022) / Có 4021, mỗi dòng chi một dòng | `Trip.id` | nhà cung cấp `EPLNCC-…` của dòng; dòng chưa gán nhà cung cấp: xe thuê lấy chủ xe, còn lại **trống** | quy Kíp theo tỷ giá khoá (`ExchangeRate` 1) |
| `tat_toan` | KT Chi phí VC chốt tất toán tài xế (`QT_TU`) | Nợ 625 / Có 1601, bằng số tài xế đã chi thật | `<tài xế>:<YYYY-MM>:<mã bản chốt>` | tài xế `EPLTX-…` | Kíp |
| `ban_chu_xe` | phiếu chi trả chủ xe có trừ hàng quầy đã chi | Nợ 4022 / Có 707, theo giá bán; một phiếu bán một bút toán | mã phiếu bán (kho tạm) | chủ xe `EPLCX-…` | tiền phiếu bán; tỷ giá = Kíp quy đổi ÷ nguyên tệ |
| `xuat_noi_bo` | khoá phiếu **xe nhà** có dầu kho (mục III, đã cấp theo phiếu đề nghị) / phụ tùng kho (mục V) đã rời kho | **Xuất nội bộ**: dầu Nợ 625 / Có 1371 · phụ tùng Nợ 614 / Có 1371, mỗi dòng chi một dòng | `dau:<mã lần xuất>` · `pt:<mã lần xuất>` (dòng sổ kho bên kho tạm) — **một lần xuất một bút toán** | **trống** (hàng của mình, không ai nợ) | giá vốn = số lượng × giá bình quân của kho lúc xuất, Kíp |
| `xuat_ban` | khoá phiếu **xe thuê** có dầu / phụ tùng kho đã rời kho (lấy kho EPL cho xe thuê **luôn** là xuất bán) | **Xuất bán cho chủ xe**, hai dòng cho mỗi dòng chi: Nợ 4022 / Có 707 theo **giá bán** + Nợ 607 / Có 1371 theo **giá vốn** | như trên | dòng 4022/707: chủ xe `EPLCX-…`; dòng 607/1371: trống | giá bán = số trừ vào tiền trả chủ xe; giá vốn như trên; Kíp |

**Xuất kho cho chuyến** (`xuat_noi_bo`, `xuat_ban` — chủ dự án 01/10: "xuất dầu là xuất nội bộ và còn là xuất bán"):
- Chỉ dòng **đã rời kho**: dầu kho thủ kho đã cấp theo phiếu đề nghị (lần cấp ở kho tạm), phụ tùng kho đã xuất lúc khai sự cố. Dòng kho còn trên phiếu mà **chưa rời kho** thì **không khoá được** (02/10): dầu mục III chưa cấp theo phiếu đề nghị → 409 `DAU_KHO_CHUA_CAP` (xe nhà lẫn xe thuê; câu nói dòng nào, KT kho xăng dầu / thủ kho cấp ở màn Cấp phát); phụ tùng ghi "lấy từ kho" trên bảng mục V mà chưa xuất (phụ tùng chỉ rời kho khi tổ sửa khai «Sửa xe» lấy kho, hoặc duyệt báo hỏng) → 409 `PT_KHO_CHUA_XUAT`. Nhờ vậy tiền chi và tiền trừ chủ xe không tính hàng chưa xuất.
- **Xe thuê: dầu / phụ tùng lấy kho EPL luôn là xuất bán** (chủ dự án 30/09, nhắc lại 02/10) — không có "chủ xe tự trả" (`paid_by_epl = false`) cho dòng kho: lập / sửa dòng, lấy phụ tùng kho như vậy → 422 `KHO_XE_THUE_XUAT_BAN`. Chủ xe trả tiền ngay thì đi **quầy bán hàng** (phiếu bán kho tạm → `ban_chu_xe`). Dòng cũ còn ghi "chủ xe tự trả": **khoá phiếu bị chặn** (409 `KHO_XE_THUE_XUAT_BAN`, câu chỉ cách sửa: bấm "EPL ứng", gõ giá bán) — không tự đổi, vì đổi là đổi số trừ tiền trả chủ xe mà không ai bấm.
- **Giá vốn**: giá bình quân của đúng kho **lúc xuất**, do kho tạm tính (anh Khampla C5.3) và trả về lúc cấp dầu / xuất phụ tùng; trang điều xe ghi lên dòng chi (`unit_price`), sau đó không sửa được. **Giá bán**: KT kho xăng dầu gõ ở mục III, KT Chi phí gõ ở mục V; **chưa gõ thì không khoá được** (409 `THIEU_GIA_BAN`, câu nói mục nào, dòng nào, ai gõ — chủ dự án 02/10), kiểm mục cũng chặn như vậy.
- **Ghi lúc khoá phiếu**, không lúc xuất: giá bán chỉ có sau khi kiểm mục (sau lúc xuất), còn tiền trả chủ xe tính từ phiếu đã khoá — ghi lúc khoá thì Có 707 đúng bằng số trừ vào tiền trả. Mở khoá / xoá phiếu thì huỷ hoặc gỡ cùng `thue_xe`, `no_ncc`.
- **Sau khoá** (02/10): những gì đã vào bút toán khoá phiếu **đứng yên** — tiền thuê xe (giá thuê, tiền tệ thuê, phí, quá tải, cả cân cuối / tỷ giá làm đổi các số đó; so theo số hiệu lực), dòng kho và dòng ghi nợ nhà cung cấp (giá bán, đơn giá, số lượng, ai trả, thêm / bỏ dòng, cấp thêm dầu hay lấy thêm phụ tùng kho, đổi chủ xe) → 409 `DA_KHOA`, kể cả KT Thu/Chi, KT kho xăng dầu, KT Chi phí và Sếp. Lưu lại đúng số cũ thì được. Muốn sửa: KT Thu/Chi mở khoá (bút toán huỷ / gỡ), sửa, khoá lại (ghi theo số mới).
- Câu lỗi các mã trên (`KHO_XE_THUE_XUAT_BAN`, `THIEU_GIA_BAN`, `DAU_KHO_CHUA_CAP`, `PT_KHO_CHUA_XUAT`, `DA_KHOA`) đủ ba tiếng (`loi`, `loi_lo`, `loi_en`); màn trang điều xe hiện theo tiếng đang xem.
- **Không trùng `ban_chu_xe`**: `ban_chu_xe` là phiếu **bán ở quầy** của kho tạm, trừ riêng vào đề nghị trả (12.11.3); `xuat_ban` là dòng kho **trên phiếu xuất xe**, trừ qua "EPL đã ứng". Hai nguồn không bao giờ chung một khoản.
- Dòng kho mang mã người dùng tự chọn có vế Có 4021 thì đã nằm trong `no_ncc` — không lặp ở đây.
- Ghi chú dòng (`Note`) và diễn giải ghi rõ bằng chữ "Xuất nội bộ" / "Xuất bán cho chủ xe — doanh thu / giá vốn", số lượng, đơn giá, số DO, số phiếu đề nghị xuất kho.

**SourceRef** = `EPLLAO-<nguồn>-<mã nguồn>`, cắt 100 ký tự. Bản đã gỡ mà nguồn ghi lại (mở khoá rồi khoá lại) → **phiên mới** `…-2`, `…-3`. Ví dụ `EPLLAO-thue_xe-662386527e56`, rồi `EPLLAO-thue_xe-662386527e56-2`; xuất kho `EPLLAO-xuat_ban-dau:f90d299c071e`. Đúng luật khoá bên anh (`[A-Za-z0-9][A-Za-z0-9_.:-]{0,99}`, phân biệt hoa thường).

**Gửi** — `POST /api/v1/integrations/logistics/journal-entries`, header `Idempotency-Key` = SourceRef (ID dưới đây minh hoạ):

```json
{
  "SourceRef": "EPLLAO-thue_xe-662386527e56",
  "DocumentDate": "2026-10-01",
  "CountryId": 11, "OrgId": 1368,
  "Description": "Ghi nhận chi phí thuê xe liên kết phiếu T4-0442-09/EPL (…)",
  "FiciAutoId": 19,
  "Entries": [
    { "DebitAccount": "621", "CreditAccount": "4022", "Amount": 1350, "ExchangeRate": 21500,
      "CurrencyId": 2, "ObjectId": 1610, "Note": "Chi phí thuê xe liên kết T4-0442-09/EPL · …" }
  ]
}
```

- `SourceRef`, `CountryId`, `OrgId` trong thân: bên anh **bỏ qua** — SourceRef lấy ở header, đơn vị / quốc gia lấy ở cấu hình `LogisticsJournalEntry`. Bên em giữ trong gói để đọc lại cho dễ. **Không có** `CostObject` hay mã DO trong gói; diễn giải đã ghi số phiếu.
- **Không gửi `BaseAmount`**: bên anh tự tính `Round(Amount × ExchangeRate, 5, AwayFromZero)`. Dòng Kíp gửi `ExchangeRate` 1. `CurrencyId` tra ở `GetAllCurrency` (chỉ tiền đang bật; USD tạm `QLSX_TIEN_USD=2`).
- `FiciAutoId`: bên em tra kỳ theo ngày (`GetFinancyCicle`). Kỳ đã đóng thì bên em chặn trước (`KY_DA_DONG`); không tra được thì bỏ trống để bên anh tự lấy theo ngày. Gửi thì phải khớp kỳ của ngày, lệch là 422.
- `DocumentDate`: khoá phiếu → ngày khoá; **xuất kho cho chuyến → ngày xuất thật** (ngày cấp dầu / ngày lấy phụ tùng; dòng cũ không tìm được thì ngày xe đi); tất toán → ngày cuối kỳ (kỳ chưa hết thì hôm nay); bán chủ xe → ngày bán.
- `Description`, `Note` bên em cắt 250 ký tự (bên anh nhận tới 400).
- Mọi mã Nợ / Có phải có trong danh mục quốc gia 11 và hạch toán được (cùng danh sách ô chọn của phiếu thu chi).

**Kết quả:**
- 201 `Result {SourceRef, DocumentId, DocumentNo, StatusId: 13, IsExisting: false}` — chứng từ tổng hợp (DOTY 12), **ghi sổ tạm**. Bên em ghi `DocumentId`, `DocumentNo`, `StatusId` lên bản, bản thành "đã gửi".
- Gửi lại cùng SourceRef, cùng nội dung → 200 `IsExisting: true`, cùng `DocumentId` — không ghi hai lần.
- Kế toán ghi sổ chính thức (12) trong QLSX thì từ đó bên em không gỡ được nữa (409).

**Gỡ** — `POST …/journal-entries/reverse`, thân `{"SourceRef": "…"}` (header `Idempotency-Key` bên em gửi kèm `<SourceRef>:dao`, bên anh bỏ qua). Gửi khi nguồn bị huỷ: mở khoá phiếu, xoá phiếu, bỏ chốt tất toán.
- 200 `Reversed: true` → bản thành "huỷ".
- 200 `Reversed: false` **và** `DocumentId: null` → bên anh không còn chứng từ đang hoạt động (lần gỡ trước đã xong mà mất phản hồi) → bên em **coi như đã gỡ**, bản thành "huỷ".
- 409 `LOGISTICS_JOURNAL_52515` (chứng từ đã khoá / đã ghi sổ chính thức) hoặc `52516` (thủ tục xoá không gỡ được, đã rollback) → bản giữ "đã gửi", đánh **chờ đảo**, câu lỗi hiện trên màn; **Gửi hết** thử lại sau khi kế toán xử lý.
- Gỡ = gỡ ghi sổ + xoá chứng từ bằng thủ tục legacy (`sp_GL_Delete_GENERALLEDGER` → `sp_GL_Delete_GLBusiness`), **không** tạo chứng từ đảo riêng (câu hỏi 10.7).
- Nguồn ghi lại sau khi đã gỡ → phiên mới `…-2`. Bên anh cũng cho POST lại cùng SourceRef sau khi gỡ; bên em vẫn dùng phiên mới để hai lần ghi không trùng mã.

**Đọc lại** — `GET …/journal-entries/{SourceRef}`: 200 kèm `DocumentId`, `DocumentNo`, `StatusId` và các dòng; 404 `JOURNAL_ENTRY_NOT_FOUND` khi không có (kể cả đã gỡ). Nút **Cập nhật** dùng đường này để đọc lại trạng thái (13 → 12 khi kế toán ghi chính thức).

**Mất phản hồi — bên em giữ cho hai sổ không lệch** (`875a0cf`):
1. **Lần gửi trước chưa rõ** (mất mạng, hết giờ, HTTP 5xx): lần gửi sau **GET trước**. Bên anh đã có chứng từ thì nhận số đó, không POST nữa.
2. **Mở khoá / bỏ một bản "chờ gửi" mà lần gửi trước chưa rõ** (cờ đang bật): GET trước. Bên anh có chứng từ thì bản đó thành "đã gửi" rồi **gỡ** ngay — không để sót chứng từ bên anh. GET không được thì vẫn bỏ ở bên em, mã lỗi cũ giữ trên bản để đối soát.
3. **409 `LOGISTICS_JOURNAL_52512`** — bên anh đã có chứng từ cùng SourceRef nhưng khác số (từ một lần gửi mất phản hồi, rồi nguồn đổi số): bên em **tự gỡ chứng từ cũ** rồi POST lại **cùng SourceRef** với bản đúng. Gỡ bị chặn (đã ghi sổ chính thức) thì báo lỗi, kế toán xử lý.

**Lỗi bên em đọc.** Thân `{Success, Code, Message, Result, ErrorDetail: {ErrorCode, InvalidAccounts, Errors, TraceId}}`; đọc cả khi HTTP 200 mà `Success: false`. Mã lỗi đọc ở `ErrorDetail.ErrorCode`, danh sách mã tài khoản sai ở `ErrorDetail.InvalidAccounts`.

| Bên anh trả | Bên em ghi trên bản | Bên em làm |
|---|---|---|
| 400 `INVALID_ACCOUNTS` | `TAI_KHOAN_SAI` kèm danh sách mã | giữ "chờ gửi"; mở mã rồi Gửi lại |
| 409 `LOGISTICS_JOURNAL_52512` | tự gỡ rồi gửi lại; không xong thì `KHAC_NOI_DUNG` | kế toán kiểm chứng từ cùng SourceRef |
| 400 / 409 / 422 khác, hoặc HTTP 200 `Success: false` | `BEN_KE_TOAN_TU_CHOI` kèm câu của anh | giữ "chờ gửi"; sửa theo câu rồi Gửi lại |
| HTTP 5xx (503 chưa áp script, chưa cấu hình, lỗi DB, đang xử lý cùng SourceRef) | `HTTP_5XX` — chưa rõ | lần sau GET trước |
| mất mạng, hết giờ (30 giây; tự gửi lúc khoá chờ 8 giây) | `KHONG_GOI_DUOC` — chưa rõ | lần sau GET trước; **Gửi hết** dừng |
| 401 | `QLSX_TOKEN_HET_HAN` | bỏ token nhớ, lần sau đăng nhập lại |
| 404 khi gửi | `KHONG_CO_DUONG` — API chưa có `b9227aa` | **Gửi hết** dừng |

Từ khi bật cờ: khoá phiếu, chốt tất toán, trả chủ xe có hàng quầy là **tự gửi**; hỏng thì giữ "chờ gửi", không chặn việc khoá. Nút **Gửi** (một bản), **Gửi hết** (mọi bản chờ gửi, cũ trước, và mọi bản chờ đảo), **Cập nhật** — vai KT Thu/Chi VC, KT Chi phí VC, Sếp.

**Điểm còn mở:**
- Dòng `no_ncc` chưa gán nhà cung cấp gửi `ObjectId` trống. Diagnostics D4 của script cho thấy `PUBENTRY.OBJ_AUTOID` **không** cho NULL thì bên anh trả 422 `LOGISTICS_JOURNAL_52507`, cả bút toán của phiếu đó không ghi — **cần quyết sau khi áp script** (bắt gán nhà cung cấp trước khi khoá, hoặc chốt một đối tượng mặc định).
- Đầu gửi coi HTTP 404 khi **gỡ** là "bên anh không còn chứng từ". Với API `b9227aa` gỡ không bao giờ trả 404 (thiếu chứng từ là `Reversed: false`), nên 404 chỉ có khi trỏ API cũ — **đừng bật cờ** trên máy còn trỏ API chưa có `b9227aa`.
- HTTP 200 `Success: false`, `Code: 500` (lỗi chưa bắt bên anh) được xếp `BEN_KE_TOAN_TU_CHOI`, không phải "chưa rõ": bỏ bản lúc đó thì không GET trước. Gửi lại vẫn an toàn nhờ cùng SourceRef.
- 403 `LOGISTICS_JOURNAL_FORBIDDEN` ("Tài khoản này không được gọi tích hợp bút toán.") bị xếp `TAI_KHOAN_SAI` vì câu có chữ "tài khoản" — câu hiện ra vẫn đúng.
- Phí 2 % và trừ quá tải xe thuê chưa có bút toán (anh Khampla chốt); `625/4201` chưa có nguồn (câu hỏi 10.10).
- **Xuất kho cho chuyến** (`xuat_noi_bo`, `xuat_ban`): tờ kho `PXK_NL` / `PXK_PT` ở kho tạm (sau là hệ anh Toàn) cũng mang định khoản (xe thuê ghi 4022/1371 theo giá vốn — luật cũ). Hiện tờ đó **không** sang sổ anh; nếu sau này có đường đưa tờ kho vào sổ anh (câu hỏi 10.11) thì vế Có 1371 phải ghi ở **một** nơi — chờ anh Khampla / chủ dự án chọn.
- Cấp dầu **lệch số duyệt** khi một tờ đề nghị gồm **nhiều dòng** cùng kho: dòng trên phiếu giữ số lít cũ (chỉ phiếu một dòng mới ghi theo số cấp thật), nên bút toán theo số lít trên phiếu — đúng số trừ chủ xe, có thể lệch số lít kho tạm đã xuất.
