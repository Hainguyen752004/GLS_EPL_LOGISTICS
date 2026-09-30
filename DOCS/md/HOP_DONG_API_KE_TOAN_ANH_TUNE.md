# Hợp đồng API KẾ TOÁN — trang điều xe EPL Lào ↔ hệ kế toán của anh Tune

Phiên bản đề nghị **v2 · 01/10/2026** (v1 ngày 30/09). Bên soạn: trang điều xe **EPL_LAO_REAL** (logistics). Người nhận: **anh Tune** (công nợ, thu chi, sổ kế toán).

> **Đổi từ v1 sang v2 (01/10/2026):**
> - **3.2 / 3.2.1:** bên em **đã dựng** gửi đề nghị thu → SO của anh (nút *Tạo SO bên kế toán*) và **đã gửi thử một DO**: hệ anh trả 422 `LOGISTICS_52905` vì **chưa có khách EPL Lào** trong danh mục của anh. Không tạo gì.
> - **3.1:** ghi rõ phong bì chứng từ hiện chỉ đi sang **KT tạm**; **chưa tờ nào** sang hệ anh bằng đường này.
> - **6.4:** sửa cho đúng các điều kiện mã đang kiểm.
> - **12.8.2:** mã khách bên em chỉ KT Thu/Chi Viêng Chăn và Sếp gán (theo Excel của khách).
> - **12.8.4:** địa chỉ ra Internet — chủ dự án host khi làm xong hết rồi mới gửi anh.
> - **10.12, 10.13:** hai câu hỏi mới. **§9** đánh dấu việc đã làm.
> - Bản đồ gọn "mình gọi gì, anh gọi gì, chứng từ đi đâu" ở tài liệu riêng **`NOI_API_ANH_TUNE`** (cùng ngày).

## 0. Đọc tài liệu này thế nào

### 0.1. Ranh giới ba bên (chủ dự án chốt 29–30/09/2026)

| Bên | Làm gì |
|---|---|
| **Trang điều xe** EPL_LAO_REAL (bên em) | Phiếu xuất xe (DO), tuyến, xe, tài xế, theo dõi chuyến, duyệt từng mục trên phiếu. **Lập phiếu ĐỀ NGHỊ**: đề nghị tạm ứng (tiền), đề nghị xuất kho nhiên liệu (kho), đề nghị thu (cước). **Xem** công nợ, thu chi — chỉ xem |
| **Hệ kế toán** của anh Tune | Công nợ phải thu và phải trả, hoá đơn, phiếu thu, phiếu chi, trả chủ xe liên kết, trả nhà cung cấp, tất toán tài xế, sổ kế toán |
| **Hệ kho** của anh Toàn | Nhập, xuất, tồn, giá vốn (hợp đồng riêng: `HOP_DONG_API_KHO_ANH_TOAN`) |

Phần tiền hiện **đang chạy tạm** trong dự án `EPL_KETOAN` (cổng 8030, DB `epl_ketoan`). Hệ của anh sẽ **thay nửa tiền** của bản tạm đó.

Mọi đường và trường trong tài liệu này **chép từ mã đang chạy** (đọc ngày 30/09 và 01/10/2026).

Hai API anh đã có được dùng ở đây:
- `POST /api/v1/integrations/logistics/sales-orders` — tài liệu anh viết ngày 11/09;
- `GET /api/v1/common/country-accounts` — danh mục tài khoản.

> **Cập nhật chiều 30/09.** Bên em đã nhận và đọc hướng dẫn **API thu chi DemoLao** của anh (`CM-CASH-VOUCHER-DEMOLAO-API-GUIDE.md`, nhánh
> `feat/DemoLao`). Mục **12** ghi từng việc bên em ↔ đường thật của anh. Phong bì đẩy chứng từ ở mục 3.1 là của **bản tạm**; khi nối hệ anh,
> tiền đi bằng phiếu **CMP / CMR** của anh (mục 12), bên em chỉ gửi đề nghị và gắn DO làm nguồn.

### 0.2. Quy ước

- **LAO** là trang điều xe (`D:\Demo_Lao\EPL_LAO_REAL\backend\app`).
- **KT tạm** là bản tạm `D:\Demo_Lao\EPL_KETOAN\backend\app`.
- **QLSX** là hệ của anh.
- Vị trí mã ghi dạng `tệp:hàm (dòng)`.
- **Hướng gọi:** "LAO → QLSX" là bên em gọi anh; "QLSX → LAO" là anh gọi bên em.
- Mỗi mục ghi hai phần:
  - **Hiện trạng**: bản tạm đang làm;
  - **Đề nghị**: xin anh làm trong hệ mới.
- **Tiền:**
  - luôn là số JSON, đi kèm **mã tiền tệ của chính chứng từ** (`LAK` · `USD` · `THB` · `VND` · `CNY`);
  - **không bao giờ giả định LAK hay VND**;
  - LAK là tiền gốc để ghi sổ.
- **Tỷ giá** là "bao nhiêu LAK cho một đơn vị". Tỷ giá **khoá trên phiếu lúc lập** (`rate_usd`, `rate_thb`, `rate_vnd`, `rate_cny`).
- **Ngày:** `YYYY-MM-DD`. Ngày giờ theo ISO 8601; đề nghị ghi múi giờ `+07:00`.

---

## 1. Việc cần anh làm TRƯỚC — danh mục tài khoản (chủ dự án chốt "cách A", 30/09)

Bên em đã gọi API danh mục của anh (`country-accounts`, quốc gia `11` = Lào) ngày 30/09. Danh mục trả **494 mã**, bên em đã chụp lại vào `backend/app/services/danh_muc_tai_khoan_lao.json`. Sau đó bên em đối chiếu từng mã hệ thống in ra với danh mục này, với Excel của khách, và với quy trình kế toán của anh Khampla (kế toán EPL).

### 1.1. Xin anh MỞ ba mã con trong danh mục của EPL

Anh Khampla ghi sổ bằng **mã con**, và chủ dự án chốt giữ đúng như vậy. Danh mục thật **chưa có** ba mã này, nên phiếu gửi sang mang các mã đó thì sổ của anh chưa ghi được:

| Mã | Cha | Tên Việt | Tên Lào | Loại | Dùng cho |
|---|---|---|---|---|---|
| **1371** | 137 (ສິນຄ້າ ໃນສາງ — hàng hoá tồn kho) | Kho hàng, vật tư | ສາງສິນຄ້າ, ວັດຖຸ | tài sản, ghi sổ được | kho dầu, kho phụ tùng của EPL |
| **4021** | 402 (ໜີ້ຕ້ອງສົ່ງ ຜູ້ສະໜອງ - ການບໍລິການ) | Phải trả nhà cung cấp | ໜີ້ຕ້ອງສົ່ງ ຜູ້ສະໜອງ | nợ phải trả, ghi sổ được | trạm dầu ghi nợ, chipping cửa khẩu, lốp, garage, thẻ cao tốc, nhập kho |
| **4022** | 402 | Phải trả chủ xe liên kết | ເຈົ້າໜີ້ເຈົ້າຂອງລົດຮ່ວມ | nợ phải trả, ghi sổ được | xe thuê (chủ xe liên kết): tiền thuê phải trả, trừ các khoản EPL ứng |

Trên màn LAO, ba mã này đang mang nhãn vàng **"chưa mở"**. Anh mở xong thì bên em gọi lại API danh mục; nhãn tự mất, không phải sửa mã.

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

### 1.3. Ba mã bên em còn chờ anh cấp

| Ô cấu hình bên LAO | Cần mã cho | Ghi chú |
|---|---|---|
| `ma_hang_khach_gui` | **hàng khách gửi giữ hộ** (quặng của khách nằm ở bãi Thà Bốc giữa hai chặng) | Hàng này **ngoài bảng**: EPL không sở hữu. Ghi đơn một vế, theo tấn |
| (mới) | **đối ứng khi cấn trừ** | Khách trả hộ EPL (thẻ cao tốc khách tự nạp, trạm dầu Việt Nam ghi nợ rồi khách trả). Hiện vế Nợ rơi vào ngân hàng 1021 — sai, vì không có tiền về (mục 8, lỗ hổng 5) |
| `ma_gia_von` | giá vốn hàng bán | đang dùng **607**; anh xác nhận |

---

## 2. Kết nối, xác thực, lỗi

### 2.1. Hiện trạng

**LAO gọi bên kế toán:**
- Địa chỉ đọc từ `cau_hinh.ke_toan_api` (env `EPL_KE_TOAN_API`), khoá từ `cau_hinh.ke_toan_token` (env `EPL_KE_TOAN_TOKEN`).
- Header gửi kèm:

  ```
  Authorization: Bearer <ke_toan_token>
  Content-Type: application/json; charset=utf-8
  Accept: application/json
  X-Nguoi-Dung: <tên đăng nhập người bấm>        ← có ở các đường liên thông; KHÔNG có ở đường đẩy chứng từ
  ```

- Hết giờ sau 15 giây. HTTPS dùng bộ chứng chỉ `certifi`.
- Không nối được thì LAO báo 503 `CHUA_NOI_KE_TOAN`. **Không xếp hàng gửi sau**: chủ dự án chốt "chặn và báo rõ".

**Bên kế toán gọi LAO:**
- Bản tạm đọc địa chỉ LAO từ `dieu_xe_api` (env `EPL_KETOAN_DIEU_XE_API`) và khoá từ `dieu_xe_token` (env `EPL_KETOAN_DIEU_XE_TOKEN`).
- LAO kiểm khoá theo `cau_hinh.token_nhan_ke_toan` (env `EPL_LAO_TOKEN_NHAN_KE_TOAN`).
- Sếp tạo khoá bằng `POST /api/lien-thong/tao-khoa` (chỉ admin; khoá hiện **một lần**).
- `X-Nguoi-Dung` phải là **tên đăng nhập có thật ở LAO**. Mọi kiểm quyền sau đó dùng **vai bên LAO** của tên đó.

**Danh mục tài khoản:** env `EPL_ACC_CODE_API`, `EPL_ACC_CODE_TOKEN`, `EPL_ACC_CODE_COUNTRY` (mặc định `11`). Chi tiết ở mục 3.3.

**Tạo SO (mục 3.2, từ 01/10):**
- Gốc: `QLSX_BASE_URL` nếu đặt; không thì giao thức + tên máy của `EPL_ACC_CODE_API` (hiện là `https://demo-lao-api.goldensme.com`).
- Token: `QLSX_ACCESS_TOKEN` nếu đặt; không thì `EPL_ACC_CODE_TOKEN`.
- Token hiện có là **tài khoản cá nhân `tune`, hết hạn 10/10/2026 09:05 giờ Lào**. Sau ngày đó danh mục tài khoản rơi về bản chụp, còn tạo SO thì không gửi được (câu hỏi 10.1).
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
   - LAO **in nguyên câu lỗi** lên màn của kế toán bên em, nên xin anh viết câu người đọc hiểu.
   - Tài liệu SO của anh đã theo đúng cách này.

4. **Chống trùng:** mọi lời gọi GHI đều có khoá ổn định (mục 3.1 và 3.2). Gửi lại cùng khoá và cùng nội dung thì trả kết quả cũ.

### 2.3. Luật "hai bên không bao giờ lệch số" (phải giữ)

Mọi thao tác tiền có bản chép sang phiếu bên LAO đều đi đúng thứ tự. Bản tạm làm ở `services/doanh_thu.py:chot`, dòng 112:

1. Bên kế toán ghi dòng của mình và sinh chứng từ, **chưa commit**.
2. Bên kế toán gọi đường ghi bên LAO (mục 4). LAO kiểm lại điều kiện với dòng phiếu bị khoá `FOR UPDATE`, rồi commit.
3. Bên kế toán commit.
4. Nếu commit ở bước 3 hỏng: rollback, rồi gọi **đường bù** để đưa bản chép bên LAO về đúng số đang lưu. Bù hỏng thì ghi log.

LAO tắt ở bước 2 thì bên kế toán báo 503 và **không lưu gì**.

---

## 3. Đường LAO → hệ của anh

### 3.1. Đẩy chứng từ — `POST /api/v1/epl-lao/vouchers`

**Hiện trạng.**
- **Không tự động.** Mỗi bước nghiệp vụ ghi một tờ vào bảng `chung_tu` của LAO. Kế toán bên em bấm **Gửi bên công nợ** để đẩy:
  - `POST /api/chung-tu/day`: tối đa 200 tờ mỗi lượt, tờ cũ trước;
  - `POST /api/chung-tu/{cid}/day`: một tờ.
- Mỗi lần gọi là **một tờ**.
- **Đích hiện nay là KT tạm** (`ke_toan_api` trỏ vào EPL_KETOAN). **Hệ anh chưa có** `/api/v1/epl-lao/vouchers`, nên **chưa tờ nào đi sang hệ anh bằng phong bì này**. Riêng đề nghị thu đã đi thẳng sang SO của anh (mục 3.2). Anh chọn cách nhận các tờ còn lại ở câu hỏi 10.13.

**Gói tin** (`services/day_ke_toan.py:goi_tin`):

| Trường | Kiểu | Bắt buộc | Nghĩa |
|---|---|---|---|
| `source` | string | không | luôn `"EPL_LAO"` |
| `ref` | string | **có** | số chứng từ bên LAO, duy nhất, dạng `LOAI/YYMM/NNNN` (ví dụ `PC_TU/2609/0007`) |
| `type` | string | **có** | loại tờ (mục 7) |
| `type_name` | string | không | tên Việt của loại |
| `group` | string | không | `receipt` · `payment` · `stock_in` · `stock_out` · `stock_adjust` · `stock_transfer` · `invoice` · `receipt_request` · `settlement` · `other` |
| `date` | YYYY-MM-DD | **có** | ngày chứng từ |
| `trip_no` | string \| null | không | số phiếu xuất xe (ví dụ `T4-0428-08/EPL`) |
| `party.kind` · `party.name` | string \| null | không | `khach` · `ncc` · `tai_xe` · `kho` · `chu_xe` và tên |
| `amount.value` | number \| null | không | số tiền theo **tiền tệ gốc** của tờ |
| `amount.currency` | string | không (mặc định `LAK`) | `LAK USD THB VND CNY` |
| `amount.lak` | number \| null | **có khi `currency` ≠ LAK** | đã quy Kíp theo tỷ giá **khoá trên phiếu** — sổ ghi đúng số này, không quy đổi lần hai |
| `entry.debit` · `entry.credit` | string \| null | không | vế Nợ và vế Có **gợi ý** (mục 7). Vế chưa có mã thì `null`, kèm tên |
| `entry.debit_name` · `entry.credit_name` | string \| null | không | tên hai vế |
| `memo` | string | không | mô tả cho người đọc |
| `lines` | object | không | chi tiết theo loại (mục 7.2) |
| `created_by` · `created_at` | string | không | người sinh tờ; giờ UTC |

Ví dụ: chi tạm ứng xe nhà (sau đợt rà định khoản 30/09).

```json
{"source": "EPL_LAO", "ref": "PC_TU/2609/0007", "type": "PC_TU", "type_name": "Phiếu chi theo đề nghị tạm ứng",
 "group": "payment", "date": "2026-09-27", "trip_no": "T4-0428-08/EPL",
 "party": {"kind": "tai_xe", "name": "ທ້າວ ທັດສະດາພອນ"},
 "amount": {"value": 580000, "currency": "LAK", "lak": 580000},
 "entry": {"debit": "1601", "debit_name": "Tạm ứng nhân viên", "credit": "1011", "credit_name": "Tiền mặt bằng Kíp"},
 "memo": "Chi theo đề nghị tạm ứng PTU-T4-0428-08/EPL",
 "lines": {"voucher_doc_no": "PTU-T4-0428-08/EPL", "driver_id": "d0c0ffee0001", "truck_no": "341",
           "hinh_thuc": "noi_bo", "owner_id": null, "owner_name": null},
 "created_by": "Quỹ tiền mặt cảng cạn", "created_at": "2026-09-27T01:02:03"}
```

Xe thuê thì khác ba chỗ: `entry.debit` = `"4022"` (phải trả chủ xe liên kết), `lines.hinh_thuc` = `"cong_no_chu_xe"`, và có `owner_id`, `owner_name`.

**Bản tạm trả về:**

| HTTP | Thân | LAO hiểu |
|---|---|---|
| 200 | `{"id": "<mã tờ bên nhận>", "ref", "entry": "BT-000123"\|null, "ghi_don": bool}` | đã nhận. LAO đánh "đã đẩy" và lưu `ma_ben_ke_toan` = `id` |
| 409 | `{"ma": "DA_CO", "loi": "Tờ … đã nhận từ …", "id": "<mã cũ>"}` | `ref` đã có. LAO **cũng coi là đã đẩy** |
| 422 | `{"ma","loi","message"}`, `ma` ∈ `GOI_SAI THIEU_REF THIEU_LOAI NGAY_SAI TIEN_SAI TIEN_TE_SAI SO_SAI THIEU_LAK DINH_KHOAN_SAI THIEU_TIEN` | ghi câu lỗi lên tờ; người dùng sửa rồi đẩy lại |
| 401 · 503 · 5xx · không nối được | | giữ tờ chưa đẩy, ghi lỗi, đếm lần thử; người bấm đẩy lại |

**Luật vào sổ ở bên nhận (hiện trạng):**
- Một tờ sinh một bút toán. Hai vế lấy nguyên `entry`. Số tiền là `round(amount.lak)`.
- Mã tài khoản lạ thì tự thêm vào danh mục của sổ.
- Tờ một vế (hàng khách gửi) ghi đơn, ngoài bảng.

**Đề nghị:**

1. **Khoá chống trùng là cặp (`source`, `ref`)**, không chỉ `ref`.

   Hiện nay tờ `PC_SC` do LAO sinh và tờ `PC_SC` do bản tạm sinh (lệnh sửa chữa) có thể **trùng số**. LAO coi 409 là thành công, nên tờ của LAO bị bỏ lặng lẽ.

   Bên em cũng sẽ gửi header `Idempotency-Key: EPL_LAO:<ref>`.

2. **409 phải phân biệt hai trường hợp:**
   - trùng mà **cùng nội dung** thì trả 200 kèm `replayed: true`;
   - trùng mà **khác nội dung** thì trả 409 là xung đột thật.

   Bên em sẽ đổi phía mình: chỉ coi là thành công khi bên anh xác nhận cùng nội dung.

3. **Tờ huỷ:** hiện LAO xoá phiếu thì chỉ rút các tờ **chưa đẩy**. Sổ thật cần bút toán đảo có hợp đồng (câu hỏi 10.7).

### 3.2. Phiếu đề nghị thu (PDT) → `POST /api/v1/integrations/logistics/sales-orders` (API anh đã có)

**Ý nghĩa:**
- Xe về, có biên bản giao nhận hàng (POD), kế toán Viêng Chăn **khoá phiếu**. Lúc đó LAO sinh **phiếu đề nghị thu**.
- Một PDT tương ứng một SO và một khoản công nợ bên anh.
- Hiện nay bản tạm chỉ lưu PDT làm ngữ cảnh, còn hoá đơn thì lập tay.

**PDT bên em** (`services/de_nghi_thu.py`):
- Sinh lúc khoá phiếu (`routes/phieu.py:khoa_phieu`, vai `acct` hoặc `admin`). Điều kiện là `transport_status = "arrived"`.
- `tien` = doanh thu theo tiền cước (`price_ccy`). `tien_lak` = doanh thu quy Kíp theo tỷ giá khoá trên phiếu.
- **Mở khoá** (`mo_khoa_phieu`):
  - phiếu đã xuất hoá đơn thì 409 `DA_HOA_DON`;
  - PDT đã gửi thì 409 `DA_GUI_DE_NGHI_THU` ("… đã gửi bên công nợ — báo bên đó trước, rồi nhờ Sếp mở khoá"). Sếp vẫn mở được.
- Phiếu **gom** (mỏ về bãi) cũng sinh PDT, vì gom có cước riêng (chủ dự án xác nhận).
- Trạng thái hiện trên màn: `cho_khoa` → `chua_lap` / `cho_gui` → `da_gui` → `da_hoa_don` → `da_thu`. Hai trạng thái cuối lấy từ **bản chép anh gửi về** (mục 4, B6 và B8).

**Ánh xạ sang khuôn SO của anh:**

| Trường SO | Luật của anh | Lấy từ bên em | Tình trạng |
|---|---|---|---|
| gốc | chỉ `schemaVersion`, `header`, `details` | gói riêng cho PDT, dựng từ gói bàn giao DO (không dùng phong bì 3.1) | **đã làm 01/10** |
| `header.do_id` | ≤ 100, ASCII, duy nhất toàn bảng | **`EPLLAO-<Trip.id>`** (Trip.id là 12 ký tự hex). Không dùng số phiếu `T4-0428-08/EPL`, vì có dấu `/` | đề nghị |
| `header.status` | `delivered` | phiếu đã về (`arrived`) **và** đã khoá | ổn |
| `header.customer_id` | = `PUBOBJECT.OBJ_OBJECTNO`, ≤ 50 | ô **"Mã khách (bên kế toán)"** trên danh mục khách (có từ 30/09; chỉ `acct` và Sếp gán). Thiếu thì chặn gửi và báo rõ | **đã làm**; **chờ anh tạo khách EPL Lào** (3.2.1) |
| `header.route.id` / `name` / `distance_km` | ≤ 50, ASCII | `Trip.route_id` (hex 12) / tên tuyến / `total_km`. Phiếu không có tuyến thì chặn gửi và báo rõ | **đã làm** |
| `header.currency` = `currency_thu` | `VND` · `LAK` · `USD` | tiền cước `price_ccy` ∈ `LAK USD THB VND CNY` | **cước THB, CNY chưa gửi được** — câu hỏi 10.3 |
| `header.selling_price` = `final_selling_price` | > 0.01 | doanh thu (tấn × đơn giá, hoặc trọn chuyến) | **đã làm**: chặn khi ≤ 0,01; tổng khớp bằng Decimal |
| `header.customer_surcharge_total` | ≥ 0 | `0` (bên em không có phụ thu khách) | ổn |
| `header.billed_qty` | snapshot | tấn tính cước | có |
| `details[]` | có dòng `thu`, Σ thu = tổng | một dòng `{"line_no": 1, "kind": "thu", "name": "Cước vận chuyển <số phiếu> · <tấn> t × <đơn giá> <tiền>", "actual_amount": doanh thu, "currency": tiền cước}` | câu hỏi 10.4: anh có muốn nhận thêm dòng `chi` không |
| `origin` · `destination` · `trip_id` · `vehicle_id` · `driver_id` · `weight_kg` · `pod_receiver` · `pod_signed_at` | nên có | có đủ (`weight_kg` = tấn × 1000; `pod_signed_at` thêm `+00:00`) | có |
| `Idempotency-Key` | ổn định cho một DO | **`logistics:EPLLAO-<Trip.id>`**. Bên em **lưu nguyên gói đã gửi** (bảng `gui_so_tune`) để thử lại đúng gói | **đã làm** |
| `Authorization` | token QLSX, có làm mới | tạm dùng `EPL_ACC_CODE_TOKEN` (tài khoản `tune`, hết hạn 10/10/2026) — đã qua cửa xác thực khi gửi thử | **chờ tài khoản dịch vụ** (câu hỏi 10.1) |

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

#### 3.2.1. Đã dựng và gửi thử (01/10/2026)

**Bên em đã dựng:**

- Màn **Phiếu đề nghị thu** có nút **"Tạo SO bên kế toán"**. Chỉ KT Thu/Chi Viêng Chăn (vai `acct`, người khoá phiếu) và Sếp (`admin`) bấm được; máy chủ chặn vai khác (403 `KHONG_CO_QUYEN`).
- Hai đường bên trang điều xe:
  - `GET /api/trips/{trip_id}/tao-so`: dựng và kiểm gói **không gọi sang hệ anh**; lỗi dữ liệu trả trong `loi`.
  - `POST /api/trips/{trip_id}/tao-so`: gửi thật.
- Máy chủ bên em gọi `POST https://demo-lao-api.goldensme.com/api/v1/integrations/logistics/sales-orders`, bằng token đang có trong cấu hình (`EPL_ACC_CODE_TOKEN`, tài khoản `tune`), giống bộ gửi của EPL_System. Token không xuống trình duyệt.
- Gói gửi đúng khuôn ở trên:
  - ba khoá gốc `schemaVersion`, `header`, `details`;
  - `header.customer_id` = ô **Mã khách** trên danh mục khách bên em;
  - **một dòng thu** (cước);
  - không gửi các khối `hire`, `fx_rates_on_trip`, `cost_by_section_lak`.
- Bên em kiểm trước khi gửi:
  - DO đã về và đã khoá;
  - khách đã có mã;
  - có tuyến;
  - mã ghép `khách_tuyến` ≤ 50 ký tự;
  - tiền là VND / LAK / USD;
  - tổng khớp chính xác bằng Decimal.
- Mỗi DO lưu **một** bản ghi lượt gửi (bảng `gui_so_tune`), gồm:
  - nguyên gói đã gửi, khoá `logistics:EPLLAO-<Trip.id>`;
  - mã HTTP và thân trả về;
  - `orderCode`, `retkCode`, `totalAmount`… khi thành công.
- Kết quả **chưa rõ** (mất mạng, hết giờ, 5xx, `52903`) thì lần sau bên em gửi lại **đúng gói, đúng khoá**. Bị từ chối rõ ràng (4xx dữ liệu) thì dựng gói mới theo số hiện tại.
- DO đã có SO thì kế toán bên em **không mở khoá được** (409 `DA_TAO_SO`); chỉ Sếp mở, sau khi báo anh.

**Gửi thử một DO (máy thử, bản sao dữ liệu):**

| | |
|---|---|
| DO | `EPLLAO-779739f4b582` (phiếu T4-0449-09/EPL, 29,7 t × 30,5 USD = **905.85 USD**) |
| Mã khách gửi | `EPLLAO-THU-01`: **mã thử, cố ý không có** trong danh mục bên anh |
| Hệ anh trả | **HTTP 422 `LOGISTICS_52905`**: "Mã khách không tồn tại hoặc bị trùng trong PUBOBJECT.OBJ_OBJECTNO." |
| Nghĩa là | token qua cửa xác thực; gói qua bước kiểm khuôn (không bị 400 `INVALID_DO`); tiền USD được nhận; hệ anh dừng ở bước **tìm khách**. **Không có SO, công nợ, mặt hàng nào được tạo.** |

**Vì sao chưa tạo được SO thật:** danh mục khách chi nhánh **1368** bên anh (`POST /api/v1/master-data/customers/list`, đọc ngày 01/10) có **189 khách**, đều là khách của EPL_System bên Việt Nam (`DEMO-CUS-…`, `KH-0015`…). **Chưa có khách nào của EPL Lào.** Trên máy thử bên em có **13 DO đã khoá chờ gửi**, và cả 13 đang bị chặn ngay bên em vì khách chưa có mã bên kế toán.

**Xin anh:**

1. Tạo các khách EPL Lào trong danh mục đối tượng (PUBOBJECT), rồi gửi bên em `OBJ_OBJECTNO` của từng khách. Hoặc anh cho bên em tự tạo qua `POST /api/v1/master-data/customers/upsert`: đó là đường ghi, bên em chưa gọi.
2. Có mã rồi thì KT Thu/Chi Viêng Chăn ghi vào ô **Mã khách** (mục 12.8.2: chỉ vai `acct` và Sếp gán được), bấm **Tạo SO bên kế toán**, là hệ anh tạo SO + công nợ.
3. Lưu ý: SO hiện vào chi nhánh cố định **1368 "Demo EPL"** (quốc gia Việt Nam, tiền VND). Dùng thật cho Lào thì cần đơn vị EPL Lào (mục 12.7.5, việc 2).

Khách trên dữ liệu thử của bên em (danh mục thật lấy ở màn Khách hàng của máy thật):

| Khách | Số DO đã khoá chờ gửi |
|---|---|
| ຄຳຕຸ້ຍ | 9 |
| ນາງ ວັນນາ | 2 |
| ບໍລິສັດ ລາວ-ຈີນ ມີເນີໂຣ | 2 |

**Những thứ API SO chưa có mà bên em cần** (câu hỏi 10.5):
- sửa hoặc huỷ SO khi Sếp mở khoá phiếu;
- đọc **công nợ hiện tại** theo DO hoặc theo khách (đã thu, còn lại, ngày thu cuối);
- **hoá đơn gộp tháng** cho khách chọn nhận một hoá đơn cả tháng (mục 6.5).

### 3.3. Danh mục tài khoản — `GET {EPL_ACC_CODE_API}/api/v1/common/country-accounts?tryAutoId=11&onlyActive=true`

- **Đang dùng.** Bên em gọi kèm `Authorization: Bearer <EPL_ACC_CODE_TOKEN>`, hết giờ 20 giây, giữ bộ nhớ 10 phút.
- Bên em đọc `Result[]`, lấy các trường `AccCode`, `AccName`, `AccDescription`, `AccParentId`, `AccAccountWrite` (ghi sổ được), `AccIsActive`.
- Không nối được thì bên em dùng **bản chụp ngày 30/09**, cộng ba mã con đánh dấu "chưa mở".
- Nếu danh mục của EPL Lào khác danh mục chung của quốc gia 11 (ví dụ danh mục riêng theo công ty), anh cho tham số. Bên em chỉ đổi cấu hình.

### 3.4. Công nợ một khách — `GET /api/lien-thong/doanh-thu/khach/{cid}` (hiện có ở bản tạm)

- **Dùng ở:** màn *Khách hàng → tab Công nợ*, chỉ xem. `cid` là mã khách bên LAO.
- **Trả về:** mỗi hoá đơn một dòng, tờ gộp đứng trước.

```json
[{"loai": "gop", "id": "…", "so": "HDT-202609-01", "ngay": "2026-09-30", "ccy": "USD", "tien": 5120.4, "tien_lak": 112648800,
  "da_thu_lak": 50000000, "con_lai_lak": 62648800, "finance_status": "partial", "so_phieu": 5},
 {"loai": "phieu", "id": "<trip.id>", "so": "T4-0428-08/EPL", "ngay": "2026-09-27", "ccy": "USD", "tien": 1025.5,
  "tien_lak": 22561000, "da_thu_lak": 0, "con_lai_lak": 22561000, "finance_status": "unpaid", "so_phieu": 1}]
```

- `finance_status` có ba giá trị: `unpaid` (đã thu ≤ 1 LAK) · `partial` · `paid` (còn lại ≤ 1 LAK).
- **Đề nghị:** anh cho một đường đọc tương đương (theo mã khách bên anh). Bên em chỉ hiện, không tính lại.

### 3.5. Cấn trừ đã ghi — `GET /api/lien-thong/doanh-thu/can-tru?ref=CT-YYYYMM` (hiện có ở bản tạm)

- **Trả về:** `{"<customer_id>": <LAK đã ghi>}` — tổng các lần thu cách `offset` mang `ref` đó.
- **Dùng ở:** báo cáo cấn trừ cuối tháng. Không nối được thì cột để trống, không ghi 0.

---

## 4. Đường hệ của anh → LAO (bên em cung cấp)

- **Xác thực:** khoá máy của LAO cộng `X-Nguoi-Dung`, xem 2.1 và 2.2.
- **Tay cầm:** tất cả ở LAO `routes/lien_thong.py`.
- Có hai nhóm:
  - **ghi bản chép trạng thái**: anh báo "đã hoá đơn", "đã thu", "đã trả chủ xe";
  - **đọc số của phiếu**: để anh tính và lập chứng từ.

### 4.1. Ghi bản chép — bắt buộc để màn bên em đúng

**B6. `POST /api/lien-thong/doanh-thu/xuat` — đã xuất hoá đơn**

| Trường | Kiểu | Bắt buộc | Nghĩa |
|---|---|---|---|
| `trip_ids` | string[] | có | các `Trip.id` lên hoá đơn |
| `kieu` | `"phieu"` \| `"thang"` | không | hoá đơn riêng từng phiếu, hay tờ gộp tháng |
| `invoice_id` · `inv_no` | string | có với `thang` | mã và số tờ gộp (`HDT-202609-01`) |
| `ngay` | YYYY-MM-DD | không (hôm nay) | ngày hoá đơn |

- **LAO làm:**
  1. Khoá dòng các phiếu (`FOR UPDATE`).
  2. Kiểm lại **từng** phiếu.
  3. Đặt `invoiced = true`, `invoice_id`, `inv_no`, `invoiced_date`, và ghi nhật ký.
- **Trả về:** mảng số liệu từng phiếu (như B4).
- **Lỗi:**
  - 422 `THIEU_PHIEU`, `NGAY_SAI`;
  - 404 `KHONG_THAY`;
  - 409 (kèm `trip_id`, `doc_no`): `DA_HOA_DON` · `CHUA_KIEM` (mục II chưa kiểm) · `CHUA_KHOA` · `GOP_THANG` (khách gộp tháng mà xuất lẻ) · `KHONG_GOP_THANG`.
- **Tác dụng bên em:** phiếu đã hoá đơn thì không xoá được. Mở khoá thì chỉ Sếp làm được.

**B7. `POST /api/lien-thong/doanh-thu/bo-xuat` — bỏ hoá đơn**
- Thân `{"trip_ids": [...]}`.
- Phiếu đã thu thì 409 `DA_THU`. Gọi lại nhiều lần vô hại.

**B8. `POST /api/lien-thong/doanh-thu/da-thu` — tổng đã thu**

```json
{"dong": [{"trip_id": "a1b2c3d4e5f6", "collected_lak": 11000000, "last_paid_date": "2026-10-05"}], "nhat_ky": "thu"}
```

- `collected_lak` là **tổng đã thu quy Kíp từ trước tới nay**: số tuyệt đối, không phải số cộng thêm. Vì vậy gửi lại vô hại.
- `nhat_ky` có ba giá trị: `"thu"` · `"xoa"` · `null` (khi thu theo tờ gộp rồi rải xuống từng phiếu).
- LAO tính lại `finance_status` và trả về `{"<trip_id>": "unpaid|partial|paid"}`.
- **Lỗi:** 409 `CHUA_HOA_DON`.
- Phiếu `paid` thì bên em chặn ghi diễn biến, báo hỏng, báo nhiên liệu.

**B12. `POST /api/lien-thong/chu-xe/tra` — đã trả chủ xe liên kết**

```json
{"owner_payment_id": "p9", "dong": [{"trip_id": "t1", "tra_chu_xe": 676.61, "tra_chu_xe_lak": 14885420}]}
```

- **Lỗi:** 422 `THIEU` · 404 `KHONG_THAY` · 409 `KHONG_PHAI_LIEN_KET` · `CHUA_KHOA` · `DA_TRA`.
- Trả về `{"t1": true}`.
- **Đề nghị:** bên em sẽ so số `tra_chu_xe` anh gửi với số bên em tính (mục 6.2). Lệch quá 1 đơn vị thì báo 409, không lưu lặng lẽ.

**B13. `POST /api/lien-thong/chu-xe/bo-tra`**
- Thân `{"owner_payment_id": "p9", "trip_ids": [...]}`. `trip_ids` trống nghĩa là mọi phiếu của đợt.
- Trả về `{"so_phieu": n}`. Gọi lại vô hại.

**B25. Chi tạm ứng — `POST /api/lien-thong/cap-phat/{vid}/cap`** (tờ `kind = "advance"`, thân `{}`)
- **Hiện trạng:** quỹ tiền mặt cảng cạn (vai `cash`) chi tạm ứng **ngay ở LAO**, bằng cách quét mã QR hoặc bấm *Chi tiền* ở mục IV.
- Điều kiện: mục IV phải `booked`. Kết quả: mục IV thành `paid`, phiếu tạm ứng thành `da_cap`, LAO sinh `PC_TU`.
- **Câu hỏi 10.6:** việc CHI THẬT có chuyển sang hệ của anh không?
  - Nếu có: bên em chỉ gửi đề nghị tạm ứng (`PTU`), và anh gọi đường này để báo "đã chi".
  - Nếu không: giữ như hiện nay.

### 4.2. Đọc số của phiếu — để anh lập hoá đơn, trả chủ xe, tất toán, trả nhà cung cấp

| # | Đường | Trả về (tóm tắt) | Anh dùng để |
|---|---|---|---|
| B2 | `GET /api/lien-thong/doanh-thu/phieu?q=&locked=&invoiced=&limit=50` | `[{id, doc_no, doc_date, truck_no, company, customer_name, locked, invoiced, invoice_id, inv_no, finance_status}]`, mới trước | ô chọn phiếu |
| B3 | `GET /api/lien-thong/doanh-thu/phieu/{tid}` | toàn bộ phiếu (các cột, `tinh` — khối tính tiền mục 6.2, `expenses[]`, `events[]`, `goods`) + khối `doanh_thu` | xem, lập hoá đơn |
| B4 | `GET /api/lien-thong/doanh-thu/so-lieu?ids=a,b` | `{trip_id: {doc_no, kind, customer_id, customer_name, inv_mode, tan_tinh, price, cach_tinh, ccy, doanh_thu, doanh_thu_lak, da_thu_lak, con_lai_lak, ty_gia{LAK,USD,THB,VND,CNY}, trans_status, locked, invoiced, finance_status, …}}` | số liệu cước |
| B5 | `GET /api/lien-thong/doanh-thu/cho-gop?period=YYYY-MM&customer_id=` | phiếu chờ gộp tháng, tách theo **khách × tiền cước** | hoá đơn gộp tháng |
| B9 | `GET /api/lien-thong/chu-xe` | `[{id, name, pay_mode (phieu\|thang\|dot), so_xe[], fee_pct, over_limit_t, over_price, hire_ccy, cho_tra{so_phieu, tong{<tiền>}, tong_lak}}]` | danh mục chủ xe liên kết |
| B10 | `GET /api/lien-thong/chu-xe/{oid}/cho-tra` | `[{id, doc_no, doc_date, truck_no, tan_tinh, hire_ccy, tien_thue, phi, tru_vuot, ung_truoc, tra_chu_xe, tra_chu_xe_lak, …}]` | phiếu chờ trả chủ xe |
| B11 | `GET /api/lien-thong/chu-xe/phieu?ids=a,b` | `{trip_id: dòng như B10}` | lúc trả |
| B14 | `GET /api/lien-thong/xe-lien-ket?thang=` | phiếu xe liên kết trong tháng | bảng tháng |
| B15 | `GET /api/lien-thong/tien-tai-xe?thang=` | xe nhà, khoản trả **cùng lương** (tiền chuyến, tiền nước…) theo tài xế | trả lương |
| B16 | `GET /api/lien-thong/tat-toan?ky=YYYY-MM` | `[{driver_id, driver_code, driver_name, so_phieu, tong_ung_lak, tong_chi_lak, chenh_lech_lak}]` | tất toán tài xế |
| B17 | `GET /api/lien-thong/tat-toan/{driver_id}?ky=` | như B16, kèm `phieu[]` | chi tiết một tài xế |
| B18 · B19 | `GET /api/lien-thong/ncc` · `/ncc/{sid}` | `[{id, name, item_key, acct_code, payment_term, customer_id, so_dong, phat_sinh_lak, ghi_no_lak}]` | nợ nhà cung cấp (xem lỗ hổng 3) |
| B20 | `GET /api/lien-thong/can-tru?thang=` | theo khách: `cuoc_lak`, `the_lak` (thẻ cao tốc khách cấp), `dau_vn_lak` (trạm dầu VN ghi nợ), `can_tru_lak`, `con_thu_lak` | cấn trừ cuối tháng |
| B21 | `GET /api/lien-thong/thang-moi-nhat` | `{"lap": "2026-09", "xe_di": "2026-09"}` | tháng mặc định |
| B22 | `GET /api/lien-thong/nguoi-mua` | `{"khach": [...], "chu_xe": [...]}` | bán hàng ở quầy |
| B23 | `GET /api/lien-thong/ty-gia` | `{"USD": 22000, "THB": 700, "VND": 1.2, "CNY": 3000}` — bảng hiện hành (không phải tỷ giá khoá trên phiếu) | |
| B24 | `GET /api/lien-thong/ma-ke-toan` | `{"ma_hang_khach_gui", "ma_gia_von"}` | |

---

## 5. Một DO đi qua tiền — ai lập tờ gì

| # | Bước | Ai bấm | Tờ | Định khoản (sau 30/09) |
|---|---|---|---|---|
| 1 | Lập phiếu xuất xe | Bãi | `DO` | không |
| 2 | In phiếu **đề nghị tạm ứng** | Bãi / kế toán | `PTU` | không |
| 3 | In phiếu **đề nghị xuất kho nhiên liệu** (mỗi kho một tờ) | Bãi / kế toán | `PLNL` | không |
| 4 | Quỹ chi tạm ứng | Quỹ tiền mặt | `PC_TU` | xe nhà **1601/1011** · xe thuê **4022/1011** |
| 5 | Thủ kho cấp dầu theo đề nghị | Thủ kho (kho anh Toàn) | `PXK_NL` | xe nhà 625/1371 · xe thuê: xem lỗ hổng 2 |
| 6 | Quỹ chi mục V (garage trả ngay) | Quỹ tiền mặt | `PC_SC` | xe nhà 614/1011 · xe thuê 4022/1011 |
| 7 | Xe về, kế toán Viêng Chăn **khoá phiếu** | kế toán | **`PDT`** | không |
| 8 | Xuất hoá đơn (từng phiếu hoặc gộp tháng) | KT doanh thu | `HD` | **1211/708** |
| 9 | Ghi một lần khách trả | KT doanh thu | `PT` | tiền/1211 |
| 10 | Cấn trừ cuối tháng | KT doanh thu | `PT` (`offset`) | xem lỗ hổng 5 |
| 11 | Trả chủ xe liên kết | Quỹ | `PC_CX` | 4022/tiền |
| 12 | Tất toán tài xế theo tháng | KT chi phí, quỹ | `QT_TU` + `TT_CHI` / `TT_THU` | **625/1601** · **1601/1011** · **1011/1601** |
| 13 | Trả nhà cung cấp | KT chi phí, quỹ | `PC_NCC` | 4021/1011 |

- Theo chốt 29/09, bước 8 đến 13 là **việc của hệ anh**.
- Bên em chỉ gửi đề nghị (bước 1, 2, 3, 7) và nhận trạng thái về (mục 4.1).

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

Khi trả, bên tạm còn trừ thêm hàng chủ xe mua ở quầy.

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
- Xin anh áp cùng luật trên các màn của hệ anh.

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

## 8. Lỗ hổng sổ bên kế toán tạm — ghi lại để anh làm đúng trong hệ mới

Đây là phần của hệ anh. Bên em không sửa trong bản tạm; chủ dự án dặn *"note lại cho anh Tune"*.

1. **Tiền thuê xe liên kết chưa bao giờ ghi thành nợ phải trả chủ xe.**
   - Không có bút toán *Nợ chi phí thuê xe / Có 4022* cho `tien_thue`. Tài khoản 4022 chỉ có vế Nợ: tạm ứng xe thuê, chi mục V xe thuê, xuất kho cho xe thuê, chủ xe mua ở quầy, trả chủ xe.
   - Trên sổ thật, 4022 đang **dư Nợ 41.610.300 LAK**, tức là sổ nói *chủ xe nợ EPL*, ngược thực tế. Phí 2 % và trừ quá tải cũng chưa có bút toán riêng.
   - **Đề nghị:** lúc **khoá phiếu** xe thuê, ghi *Nợ [chi phí thuê xe] / Có 4022* bằng `tien_thue`. Phí và quá tải ghi theo cách anh Khampla chọn.
   - Danh mục thật có **621** (chi phí vận chuyển) và **611** (thuê ngoài). Excel của khách có dòng *"ມູນຄ່າ THB 1211/402 ຄ່າຂົນສົ່ງນອກ"* cho khoản này → **cần anh Khampla chốt tài khoản**.
   - Phiếu có `tra_chu_xe ≤ 0` (chủ xe nợ ngược EPL) cũng cần chỗ ghi.

2. **Dầu và phụ tùng kho bán cho chủ xe đang ghi theo giá vốn (Nợ 4022 / Có 1371).** Đúng ra xuất bán phải tách hai bút toán:
   - *Nợ 607 / Có 1371* theo **giá vốn** — tờ kho, hệ anh Toàn;
   - *Nợ 4022 / Có 707* theo **giá bán** — tờ bán, hệ anh.

   Giá bán nằm trên phiếu bên em (dòng `sale_price`):
   - dầu: KT kho xăng dầu gõ khi kiểm mục III;
   - phụ tùng: KT Chi phí gõ khi kiểm mục V.

   **Đề nghị:** lúc **ghi sổ** mục III hoặc V của phiếu xe thuê, bên em gửi một tờ bán kiểu `HD_BAN` với đối tượng `chu_xe`, số tiền = Σ lượng × giá bán, `lines` từng dòng. Anh ghi *Nợ 4022 / Có 707*. **Anh xác nhận khuôn** thì bên em làm (câu hỏi 10.9).

3. **Nợ nhà cung cấp đang cộng theo khoản mục, không xét cách trả** (`routes/nha_cung_cap.py:_cua_ncc`). Hệ quả:
   - dòng chipping mà người lập đổi sang tiền mặt vẫn bị tính là nợ nhà cung cấp — trong khi dòng đó đã nằm trong tạm ứng;
   - nhà cung cấp mang khoản mục `diesel` (trạm dầu Việt Nam) nuốt cả dầu lấy kho.

   **Đề nghị:** nợ nhà cung cấp = **các dòng có vế Có 4021** theo bảng 7.3. Bên em có thể trả đúng danh sách dòng đó ở B18.

4. **Chi phí ghi nợ chưa bao giờ vào sổ.** Không có tờ nào đưa các cặp sau vào sổ:
   - 625/4021 (dầu trạm ghi nợ, chipping, lốp, thẻ cao tốc);
   - 614/4021 (garage cho nợ);
   - 625/4201 (tiền chuyến, tiền nước trả cùng lương).

   Vì vậy `PC_NCC` ghi Nợ 4021 mà trước đó chưa có Có 4021, và 4201 không có bút toán nào. **Đề nghị:** lúc khoá phiếu, bên em gửi **một tờ "ghi nhận chi phí"** cho các dòng không phải tiền mặt và không lấy kho, mang đúng cặp mã từng dòng (câu hỏi 10.10).

5. **Cấn trừ ghi Nợ ngân hàng.** `PT` với cách `offset` rơi vào Nợ 1021 / Có 1211, tức là sổ ghi một khoản tiền về ngân hàng không có thật. Đúng ra phải xoá khoản phải trả trạm dầu Việt Nam (4021) hoặc tiền thẻ khách. **Cần anh cho tài khoản đối ứng** (mục 1.3).

6. **`PC_SC` bên em ghi đối tượng `tai_xe` và luôn Có tiền mặt**, trong khi mã dòng sửa ngoài là 614/4021 (garage). Garage trả ngay thì đúng. Garage cho nợ theo đợt (lốp — Excel ghi *ຕິດໜີ້ຜູ້ສະໜອງ ຈ່າຍເປັນງວດ*) thì bên em đã **bỏ khỏi `PC_SC`** từ 30/09. Anh cần nhận khoản đó qua tờ ghi nhận chi phí ở lỗ hổng 4.

7. **Huỷ, xoá không có thông điệp sang sổ.** Bản tạm huỷ hoá đơn, xoá lần thu, huỷ đợt trả hay bỏ chốt tất toán bằng cách **xoá tờ và bút toán của chính nó**. Sổ thật cần **bút toán đảo** (câu hỏi 10.7).

---

## 9. Việc bên em làm khi anh trả lời

| Việc | Khi nào |
|---|---|
| Ô **"Mã khách bên kế toán"** trên danh mục khách; chặn gửi PDT khi thiếu | **đã làm 30/09**; từ tối 30/09 chỉ KT Thu/Chi VC và Sếp gán |
| Bộ dựng gói SO cho PDT (3.2), lưu gói và khoá để thử lại đúng gói | **đã làm 01/10**, đã gửi thử một DO (3.2.1) |
| Chặn gửi PDT khi doanh thu = 0, phiếu không tuyến, cước THB / CNY (nếu anh chưa nhận) | **đã làm 01/10** (mục II chưa kiểm: xem 6.4) |
| Ghi mã khách anh cấp, gửi SO thật một DO, đối chiếu `orderCode`, `totalAmount` với tờ đề nghị thu | khi anh tạo khách EPL Lào (câu hỏi 10.12) |
| Phiếu chi tạm ứng CMP (12.3) | khi anh cấp mã số ở 12.7.5 và trả lời 10.6 |
| Nút tạo **khoá bàn giao** cho hệ anh ở màn Tài khoản (hiện chỉ có đường `POST /api/handover/tao-khoa`) | khi có địa chỉ ra Internet |
| Chống trùng (`source`, `ref`) + `Idempotency-Key`; phân biệt 409 thật với 409 cùng nội dung | khi anh xác nhận 3.1 |
| Tài khoản dịch vụ `qlsx` có phạm vi đường cho chiều anh gọi sang | trước khi nối thật |
| So số `tra_chu_xe` anh gửi với số bên em tính (B12) | trước khi nối thật |
| Tờ bán cho chủ xe (lỗ hổng 2), tờ ghi nhận chi phí (lỗ hổng 4) | khi anh chốt khuôn |
| **Đã làm ngày 30/09:** tạm ứng qua 1601 và quyết toán lúc tất toán · doanh thu 708/707 · bản in phiếu thu ghi Nợ tiền / Có 1211 · `PC_SC` không chi lại dòng đã tạm ứng, không trả tiền mặt khoản nợ nhà cung cấp · tên tài khoản theo danh mục thật | — |

## 10. Câu hỏi cần anh trả lời

1. **Xác thực QLSX:** cách lấy và làm mới access token cho tài khoản tích hợp; `UserId` nào đưa vào allowlist? Hiện bên em tạm dùng token cá nhân của anh (hết hạn 10/10/2026).
2. **Ba mã con 1371, 4021, 4022** (mục 1.1): anh mở cho EPL được không, và mở ở danh mục quốc gia 11 hay danh mục riêng của công ty?
3. **Tiền THB, CNY:** SO của anh chỉ nhận VND · LAK · USD, trong khi cước bên Lào có phiếu ký bằng THB. Anh thêm được không?
4. **Dòng chi trong SO:** anh muốn nhận thêm các dòng `chi` (mục III–VI) trong `details` không? Nhận thì lộ biên lợi nhuận trên SO.
5. **Sau SO:**
   - cách sửa hoặc huỷ SO khi Sếp mở khoá phiếu;
   - đường đọc công nợ hiện tại (theo DO, theo khách);
   - hoá đơn gộp tháng làm thế nào;
   - "hoàn thành SO" có phải là "đã xuất hoá đơn" bên em không.
6. **Chi tạm ứng thật** ở hệ anh hay vẫn ở LAO (4.1, B25)?
7. **Bút toán đảo** khi huỷ: khuôn tờ huỷ (tham chiếu `ref` gốc)?
8. **Chênh lệch tỷ giá** (hoá đơn USD, khách trả Kíp): anh hạch toán ở đâu, theo tỷ giá nào?
9. **Tờ bán cho chủ xe** (lỗ hổng 2): khuôn nào, gửi lúc ghi sổ mục III / V được không?
10. **Tờ ghi nhận chi phí** (lỗ hổng 4) và **nợ thuê xe liên kết** (lỗ hổng 1): lúc khoá phiếu được không, tài khoản nào? (Hỏi thêm anh Khampla.)
11. **Tờ kho có định khoản** do hệ anh Toàn sinh: đi vào sổ anh qua đường nào? Có dùng phong bì 3.1 không?
12. **Khách EPL Lào** (mới, 01/10): anh tạo trong PUBOBJECT rồi gửi bên em `OBJ_OBJECTNO` từng khách, hay cho bên em tự tạo qua `POST /api/v1/master-data/customers/upsert`? Đây là việc **đang chặn** tạo SO (3.2.1).
13. **Cách nhận các tờ còn lại** (mới, 01/10) — `PTU`, `PC_TU`, `PC_SC`…:
    - (1) anh dựng một cửa `POST /api/v1/epl-lao/vouchers` nhận đúng phong bì 3.1, tự rẽ vào CMP / CMR theo `type`; bên em chỉ đổi địa chỉ; hay
    - (2) mỗi loại đi đường riêng của anh (SO đã làm, CMP cho tạm ứng…); bên em gọi từng đường.

## 11. Thử với nhau

Bên em có các bộ kiểm tự động chạy trên máy thử (bản sao DB), không đụng dữ liệu thật:

- `kiem/thu_dinh_khoan.py` — mọi mã in ra đều có trong danh mục của anh (trừ ba mã con), bảng dòng chi 18 trường hợp, tạm ứng 1601, `PC_SC` không trả tiền mặt nợ nhà cung cấp.
- `kiem/thu_de_nghi.py` — khoá phiếu sinh đề nghị thu đúng tiền tệ; mở khoá rút tờ chưa gửi; tờ đã gửi thì chặn mở khoá.
- `kiem/thu_cach_tra.py` — cách trả theo Excel, tạm ứng chỉ gồm khoản chi ngay khi xe đi.
- `kiem/thu_day_ke_toan.py` — dựng máy nhận giả đóng vai hệ anh, đẩy tờ mẫu, thử cả trả 500 và 409.
- `kiem/thu_tao_so.py` (01/10) — 22 chỗ kiểm cho tạo SO: quyền (Bãi, tài xế, KT doanh thu không gửi được), luật chặn (DO chưa khoá, thiếu mã khách, mã ghép quá 50 ký tự), khuôn gói (ba khoá gốc, `customer_id` = mã bên anh, một dòng thu, tổng khớp chính xác). **Không gọi sang hệ anh.**
- `kiem/thu_ban_giao.py` — 31 chỗ kiểm cho hai đường bàn giao DO (12.8).
- `kiem/thu_khach_hang_moi.py` — mã khách: chỉ `acct` và Sếp gán, không trùng, đúng dạng; `customer_code` trong gói bàn giao.
- Bên bản tạm `EPL_KETOAN/kiem`: `thu_tat_toan.py` (có tờ quyết toán `QT_TU`), `thu_nhan_chung_tu.py`, `thu_dot2.py` (sổ đối chiếu quỹ, công nợ, kho, chuyến).

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
| Base URL là **server Backend API**, không phải BFF web | cấu hình `qlsx_api` trỏ đúng server API |
| `Authorization: Bearer <access-token>`; người thao tác lấy từ token (`User.GetObjectId()`) | bên em đăng nhập bằng **tài khoản dịch vụ** (câu hỏi 10.1). Người bấm bên em ghi vào `Description`, không thay xác thực |
| Gửi `X-Correlation-Id` | bên em gửi `EPL_LAO:<số tờ đề nghị>:<lần thử>` và lưu lại cùng `RequestId` anh trả để đối soát |
| JSON **PascalCase**; một số report trả tên cột SQL | bên em đọc đúng hoa thường, không đổi |
| **Lỗi trả HTTP 200 kèm `Success = false`** | bên em kiểm **cả HTTP status lẫn `Success`**, không coi 200 là thành công |
| Có `TmpId` **không có nghĩa** đã có phiếu chính | bên em chỉ đánh "đã tạo" khi có `RealId` và `Status = "Committed"` |
| **Không có Idempotency-Key**; hết giờ không có nghĩa là chưa tạo | trước khi gửi lại, bên em tìm bằng `POST /list` theo `DocumentNo` / `RefDocumentNo` (số tờ đề nghị bên em). Giữ **`SessionId` ổn định** cho mỗi tờ |
| Mọi mã là **ID số trong DB**: `CountryId` 11, `OrgId`, `FiciAutoId` (kỳ tài chính), `DotyAutoId` (loại chứng từ), `CurrencyId`, `ObjectId` | bên em giữ bảng đối chiếu (12.4), Sếp nhập ở màn cấu hình |
| Nên `PostMode = None`, xác nhận `RealId` rồi mới ghi sổ riêng | bên em chỉ tạo phiếu ở `PostMode = None`. **Ghi sổ là việc của kế toán bên anh** |

### 12.2. Mỗi việc bên em cần ↔ đường của anh

| Việc | Đường của anh | Cách dùng | Còn thiếu / cần anh xác nhận |
|---|---|---|---|
| **Danh mục tài khoản** | `GET /api/v1/accounting/cmpayment-receipt/country-accounts?countryId=11` (chỉ tài khoản active **và cho hạch toán**) | bên em chuyển sang đường này, thay đường `common/country-accounts` đang gọi | có trả **1371, 4021, 4022** sau khi anh mở (mục 1.1) không |
| **Tài khoản tiền mặc định** | `GET …/default-money-account?countryId=11&isCash=&isLocal=&currencyId=` → `{AccountCode}` | vế tiền 1011 / 1012 / 1021 / 1022 thay vì bên em tự chọn | mapping `CMACCOUNTCONFIGCOUNTRY` cho quốc gia 11 đã có chưa |
| **Loại chứng từ** | `GET …/document-types?voucherType=ALL&orgAutoId=` | lấy `DotyAutoId` cho: chi tạm ứng, chi khác, thu khác, chi công nợ (ID 58), thu công nợ | tên loại "chi tạm ứng tài xế" có sẵn không |
| **Đề nghị tạm ứng (PTU) → phiếu chi (CMP)** | `POST …/save-and-commit` với `VoucherType = "CMP"`, `PostMode = "None"` | tạo phiếu chi **ở trạng thái chờ**, thủ quỹ bên anh chi tiền rồi ghi sổ. Khung ở 12.3 | ai bấm tạo: bên em gọi API, hay thủ quỹ bên anh tự lập từ tờ đề nghị (câu hỏi 10.6) |
| **Gắn DO làm nguồn** cho phiếu thu chi | `GET /api/v1/accounting/cash-voucher-references?type=DO` và `GET …/DO/{id}` → `SelectionToken`; rồi `SourceReferences[]` trong save-and-commit | phiếu thu chi của anh trỏ đúng DO bên em | **hệ anh đọc DO qua `handover/delivery-orders` của Logistics** (đang trỏ EPL_System) — xem 12.5 |
| **Đề nghị thu (PDT) → SO + công nợ** | `POST /api/v1/integrations/logistics/sales-orders` (mục 3.2) | không đổi | — |
| **Thu tiền khách** (hoá đơn, phiếu thu) | `POST …/save-and-commit` `VoucherType = "CMR"` với `Relations[{SourceType: "DEP", SourceDocumentIds}]` (lấy ở `…/debt-documents/search` với `DeptType = "rec"`) · hoặc `POST /api/v1/sales/debt/collection-upsert` theo `RetkAutoId` của SO | **việc của kế toán bên anh**, bên em không gọi | — |
| **Xem công nợ khách** (Khách hàng → tab Công nợ) | `POST /api/v1/sales/debt/customer-detail` `{CustomerObjectId, OrgId}` → `Customer, Summary, Aging, Debts, Collections, Orders` · hoặc `POST /api/v1/sales/debt/workspace` | bên em **chỉ đọc và hiện** thay cho đường tạm (3.4) | khuôn `Debts` / `Collections` (dynamic) — xin một mẫu thật |
| **Trạng thái "đã hoá đơn / đã thu" của một DO** | chưa có đường theo `do_id` | tạm thời: đọc `customer-detail`, ghép theo `RetkCode` / `orderCode` bên em đã lưu khi gửi PDT | câu hỏi 12.6 (2) |
| **Trả chủ xe liên kết** | `CMP` chi công nợ (`DotyAutoId` 58, nguồn `pay`) | việc của bên anh | **cần có khoản phải trả chủ xe trước** (lỗ hổng 1, mục 8) |
| **Tất toán tài xế** | `CMP` / `CMR` "khác" với `Entries` 625/1601, 1601/1011, 1011/1601 (mục 6.3) | việc của bên anh; số liệu đọc ở B16, B17 (mục 4.2) | — |
| **Chi mục V (garage trả ngay)** | `CMP` chi khác, `Entries` 614/1011 | việc của bên anh (mục V không có tờ đề nghị riêng) | — |
| **Báo cáo thu chi** | `/api/v1/accounting/gl-report/*` | chỉ xem | anh ghi: `accounts` còn legacy 111/112, không theo quốc gia — chưa dùng cho Lào |

### 12.3. Khung phiếu chi tạm ứng bên em định gửi (từ một tờ PTU)

Các số `0` là chỗ sẽ điền từ bảng mã 12.4.

```json
{"TmpId": 0, "RealId": 0, "VoucherType": "CMP", "SessionId": "epllao-PTU-T4-0428-08-EPL", "PostMode": "None",
 "Header": {"CountryId": 11, "OrgId": 0, "FiciAutoId": 0, "DotyAutoId": 0, "CurrencyId": 0, "ObjectId": 0,
            "RefDocumentNo": "PTU-T4-0428-08/EPL", "DocumentDate": "2026-09-27",
            "Description": "Tạm ứng chuyến T4-0428-08/EPL · xe 341 · tài xế ທ້າວ ທັດສະດາພອນ (đề nghị từ trang điều xe)",
            "IsCash": true, "IsLocal": true, "IsDirect": false, "ExchangeRate": 1, "Amount": 580000, "BaseAmount": 580000,
            "ContactName": "ທ້າວ ທັດສະດາພອນ"},
 "Relations": [],
 "Entries": [{"SourceLineKey": "ENTRY:PTU-T4-0428-08/EPL", "ObjectId": 0, "CurrencyId": 0,
              "DebitAccount": "1601", "CreditAccount": "1011", "ExchangeRate": 1, "Amount": 580000, "BaseAmount": 580000,
              "Description": "Tạm ứng nhân viên (tài xế xe nhà)", "EntryTypeId": 11, "ValidateMoney": true}],
 "SourceReferences": [{"SourceLineKey": "ENTRY:PTU-T4-0428-08/EPL", "CostObjectId": null, "CostCenterCode": null,
                       "SourceReference": {"SourceSystem": "LOGISTICS", "SourceType": "DO", "SourceId": "<do_id>", "SelectionToken": "<token>"},
                       "ManualCostObject": null}]}
```

- **Xe thuê:** `DebitAccount = "4022"` (trừ vào tiền trả chủ xe), `ObjectId` = chủ xe.
- **Vế tiền:** lấy ở `default-money-account`.
- `SourceReferences` chỉ gửi được khi DO bên em đọc được qua 12.5. Chưa có thì gửi `null`, theo chế độ cũ.

### 12.4. Bảng mã số bên em cần anh cấp

| Cần mã | Trường | Bên em có |
|---|---|---|
| Quốc gia | `CountryId` | 11 (Lào) |
| Đơn vị | `OrgId` / `OrgAutoId` (SO dùng 1368) | EPL Lào — Thà Bốc, Viêng Chăn: một hay hai đơn vị? |
| Kỳ tài chính | `FiciAutoId` (ID, không ghép YYYYMM) | theo tháng của tờ |
| Loại chứng từ | `DotyAutoId` | chi tạm ứng · chi khác · thu khác · chi công nợ · thu công nợ |
| Tiền tệ | `CurrencyId` (ID, không phải chữ LAK/USD) | LAK · USD · THB · VND · CNY |
| Đối tượng | `ObjectId` (PUBOBJECT) + `OBJ_OBJECTNO` (cho SO) | từng khách, tài xế, chủ xe liên kết, nhà cung cấp — nên dùng **chung một danh mục đối tượng** với kho anh Toàn |
| Phương thức thanh toán | `PaymentMethodId` | tiền mặt · chuyển khoản · cấn trừ |

### 12.5. Việc bên em làm để hệ anh chọn được DO của bên Lào

Hệ anh đọc DO qua **API bàn giao của Logistics**. Hiện nay đó là đường của EPL_System:

- `GET /api/handover/delivery-orders?customer_id=&completed_from=&completed_to=&page=&page_size=`, trả về `{message, data: {items: [{do_id, status, customer_id, quotation_id, route_id, vehicle_id, driver_id, selling_price, customer_surcharge_total, final_selling_price, currency, completed_at, completed_by, detail_url}], total, page, page_size}}`;
- `GET /api/handover/delivery-orders/{do_id}`, trả về `{message, data: {header, details}}`.

**Bên em đã dựng đúng hai đường này ở trang điều xe EPL Lào (30/09, chi tiết ở mục 12.8)**, chỉ đọc:

- `do_id` = `EPLLAO-<Trip.id>` (trùng `do_id` gửi SO ở 3.2);
- `status = "delivered"` khi phiếu **đã về và đã khoá**;
- tiền theo tiền cước của phiếu;
- `details` = dòng thu (cước) và các dòng chi mục III–VI, kèm `acc_code` (bảng 7.3).

**Anh chỉ cần** cho hệ anh một cấu hình địa chỉ Logistics **theo từng khách / chi nhánh**, để phiếu Lào đọc đúng trang điều xe Lào, không đọc EPL_System bên Việt Nam.

### 12.6. Câu hỏi thêm cho anh

1. **Tài khoản dịch vụ và token** cho API CM: cách lấy, hạn, quyền theo chi nhánh.
2. **Trạng thái theo DO:** có đường nào trả "SO của DO này: đã hoá đơn chưa, đã thu bao nhiêu, còn nợ bao nhiêu" không? Nếu không, anh gọi các đường bản chép B6, B8, B12 (mục 4.1) sang bên em được không?
3. **Phiếu chi tạm ứng:**
   - bên em tạo sẵn phiếu chờ (`PostMode = None`, 12.3), thủ quỹ bên anh chỉ bấm chi và ghi sổ; hay
   - thủ quỹ tự lập từ tờ đề nghị in ra?

   Tạo sẵn thì cần `DotyAutoId` "chi tạm ứng".
4. **`handover/delivery-orders` theo tenant** (12.5): hệ anh cấu hình được nhiều địa chỉ Logistics không?
5. **Hai đường danh mục tài khoản** (`common/country-accounts` và `cmpayment-receipt/country-accounts`) có trả cùng danh mục cho quốc gia 11 không? Bên em sẽ dùng đường thứ hai (chỉ tài khoản cho hạch toán).
6. **Tiền THB, CNY** cho phiếu CMP / CMR có được không (`CurrencyId` của hai tiền này)?

### 12.7. Kết quả gọi thử máy `demo-lao-api` ngày 30/09 (chỉ đọc)

Bên em đã gọi thử bằng token cấu hình trong trang điều xe (`EPL_ACC_CODE_API`, `EPL_ACC_CODE_TOKEN`):

- **chỉ gọi các đường xem, danh sách, tìm**;
- **không gọi** đường tạo, lưu, commit, ghi sổ, xoá nào;
- không in token ra đâu.

#### 12.7.1. Token hiện có

| | |
|---|---|
| Người dùng | `tune` (UserID 846, ObjectId 1503, nhóm "Nhân viên", OrgId 2) — **tài khoản cá nhân của anh** |
| Hạn | **10/10/2026 09:05 giờ Lào** (02:05 UTC) |
| Chi nhánh được vào (`auth/branches`) | 1368 "Demo EPL" · 5 "EPL 2" · 1369 "EPL 3" |

Xin anh cấp **tài khoản dịch vụ** cho trang điều xe (câu hỏi 12.6 (1)). Nếu dùng tài khoản cá nhân thì:

- mọi phiếu bên em tạo sẽ ghi tên anh;
- tới 10/10 là tắt.

#### 12.7.2. Bảng mã 12.4 — số đọc được

| Cần mã | Số thật trên máy Lào | Còn thiếu |
|---|---|---|
| `CountryId` | 11 | — |
| `OrgId` | 2 "EPL 1" · 1368 "Demo EPL" · 5 "EPL 2" · 1369 "EPL 3" (`common/GetCompanyAndBranch`) | **cả bốn đều quốc gia Việt Nam, tiền VND (`CUR_AUTOID` 3)**. Xin anh tạo đơn vị EPL Lào (quốc gia Lào, tiền LAK) |
| `FiciAutoId` | 22 kỳ, đều "Kỳ mở". **ID không theo thứ tự tháng**: 9/2026 = **20**, 10/2026 = **19**, 11/2026 = 18, 12/2026 = 17, 10/2025 = 24, 1/2026 = 7 | bên em **tra theo `FICI_DATEFROM` / `FICI_DATETO`**, không đoán ID |
| `DotyAutoId` (thu chi) | 14 Thu hoá đơn · 15 Thu công nợ · 16 Thu trước · 17 Thu khác · 57 Chi hoá đơn · 58 Chi công nợ · 59 Chi trước · 60 Chi khác · 68 Chuyển tiền nội bộ | **không có loại "chi tạm ứng"**. Xin anh chốt: 59 "Chi trước" hay 60 "Chi khác" kèm Nợ 1601 |
| `CurrencyId` | **3 = VND, 26 = LAK** (`common/GetAllCurrency`) | **chưa có USD, THB, CNY**. Cước bên Lào thường là USD — xin anh thêm |
| `PaymentMethodId` | 1 Tiền mặt · 3 Chuyển khoản · 6 Tiền mặt/Chuyển khoản | **chưa có "cấn trừ"** (mục 6.6) |
| Vế tiền mặc định (`default-money-account`, quốc gia 11) | tiền mặt Kíp **1011** · tiền mặt ngoại tệ **1012** · ngân hàng Kíp **1021** · ngân hàng ngoại tệ **1022** | khớp đúng bảng định khoản bên em (mục 7) |
| `ObjectId` | danh mục hiện có **189 khách, 517 nhà cung cấp** (trang 100 dòng), đều là dữ liệu bên khác | xin anh tạo đối tượng cho khách, tài xế, chủ xe liên kết, nhà cung cấp của EPL Lào — hoặc cho bên em đồng bộ qua `master-data/customers/upsert`, `master-data/suppliers/upsert` |

#### 12.7.3. Danh mục tài khoản

| Đường | Kết quả |
|---|---|
| `GET /api/v1/accounting/lao-accounts` | **494 mã**, khớp bản bên em chụp ngày 30/09. Cột: `ACC_CODE`, `ACC_NAME`, `ACC_PARENTID`, `ACC_STRUCTURE`, `ACC_ISACTIVE`, `ACC_ISMONEYCURENTCY`, `TRY_AUTOID`, `Version`… Tài khoản `tune` có `CanCreate`, `CanWrite`, `CanDelete` = true |
| `GET …/cmpayment-receipt/country-accounts?countryId=11` | **405 mã** cho hạch toán (cột viết PascalCase: `AccCode`, `AccName`, `AccParentId`…). **Có đủ** 1011, 1012, 1021, 1022, 1211, 137, 1601, 401, 402, 4201, 607, 614, 625, 707, 708 |
| Ba mã con bên em cần | **1371, 4021, 4022 chưa có ở cả hai đường**. Xin anh mở theo mục 1.1: tạo trong `lao-accounts`, sau đó chúng phải hiện ở `country-accounts` |

#### 12.7.4. Nguồn DO của phiếu thu chi

`GET /api/v1/accounting/cash-voucher-references?type=DO` chạy được, trả **23 DO**. Nhưng đó là **DO mẫu của EPL_System bên Việt Nam**:

- khách `DEMO-CUS-…`, tuyến `DEMO-RT-…`;
- ví dụ `DO-2026-0047-DO01`: `DEMO-CUS-DUCGIANG`, 3.829.000 LAK, `delivered`.

Mỗi dòng có khuôn:

```json
{"SourceSystem": "LOGISTICS", "SourceType": "DO", "SourceId": "<do_id>", "SourceCode": "<do_id>",
 "SourceName": "<customer_id>", "Status": "delivered",
 "Summary": {"do_id", "status", "customer_id", "quotation_id", "route_id", "vehicle_id", "driver_id",
             "selling_price", "customer_surcharge_total", "final_selling_price", "currency",
             "completed_at", "completed_by", "detail_url"}}
```

`Summary` chính là một dòng của `GET /api/handover/delivery-orders`. Như vậy chỉ cần bên em dựng **đúng khuôn đó** ở trang điều xe Lào (mục 12.5), và anh **trỏ nguồn Logistics của đơn vị EPL Lào** sang trang điều xe Lào.

#### 12.7.5. Việc xin anh làm — xếp theo thứ tự cần trước

1. **Mở 1371, 4021, 4022** (mục 1.1).
2. **Tạo đơn vị EPL Lào** (quốc gia 11, tiền LAK). Trả lời luôn: Thà Bốc và Viêng Chăn là một đơn vị hay hai?
3. **Thêm tiền USD, THB** (và CNY nếu bên Lào dùng), cho anh biết `CurrencyId`.
4. **Tài khoản dịch vụ** cho trang điều xe, quyền trên đơn vị EPL Lào.
5. **Chốt `DotyAutoId` cho phiếu chi tạm ứng** (59 hay 60).
6. **Đối tượng** cho khách, tài xế, chủ xe, nhà cung cấp EPL Lào (hoặc cho bên em đồng bộ). **Từ 01/10 phần khách đang chặn tạo SO** (3.2.1, câu hỏi 10.12).
7. **Trỏ nguồn DO** của đơn vị EPL Lào sang trang điều xe Lào. Hai đường bàn giao **đã dựng xong** (mục 12.8); còn chờ địa chỉ ra Internet (chủ dự án host khi làm xong hết, 12.8.4).
8. Phương thức **"cấn trừ"**, nếu anh muốn ghi cấn trừ cuối tháng bằng phiếu thu chi.

### 12.8. Hai đường bàn giao DO đã dựng ở trang điều xe Lào (30/09)

Bên em đã dựng xong hai đường ở mục 12.5, **đúng khuôn EPL_System**. Hệ anh chỉ cần đổi **địa chỉ Logistics** và **khoá** cho đơn vị EPL Lào; cách đọc giữ nguyên.

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
| `customer_id` | chuỗi | mã khách **bên em** (12 ký tự hex) **hoặc mã khách bên anh** (`OBJ_OBJECTNO`, ô "Mã khách" trên danh mục khách bên em) |
| `completed_from`, `completed_to` | `YYYY-MM-DD` | ngày khoá phiếu (gồm cả hai đầu, theo giờ UTC). Sai dạng → 422 `NGAY_SAI` |
| `page` | số ≥ 1 | mặc định 1 |
| `page_size` | 1–200 | mặc định 50 |

- Chỉ trả phiếu **đã về** (`transport_status = "arrived"`) **và đã khoá** (kế toán Viêng Chăn khoá sau khi có biên bản giao nhận).
- Xếp **mới khoá trước**.
- `total` là tổng thật sau khi lọc (không phải tổng chưa lọc).

Trả về:

```json
{"message": "Danh sách 13 lệnh giao hàng đã hoàn tất (trang 1).",
 "data": {"items": [
   {"do_id": "EPLLAO-779739f4b582", "status": "delivered",
    "doc_no": "T4-0449-09/EPL", "kind": "giao",
    "customer_id": "<mã khách bên em>", "customer_code": "<OBJ_OBJECTNO bên anh hoặc null>", "customer_name": "<tên khách>",
    "quotation_id": null, "contract_no": "<số hợp đồng>",
    "route_id": "<mã tuyến>", "origin": "…", "destination": "…",
    "vehicle_id": "<mã xe>", "truck_no": "346", "plate_head": "<biển đầu kéo>",
    "driver_id": "<mã tài xế>", "driver_name": "…",
    "company": "EPL", "owner_name": null,
    "selling_price": 905.85, "customer_surcharge_total": 0, "final_selling_price": 905.85,
    "currency": "USD", "final_selling_price_lak": 19928700,
    "completed_at": "2026-09-29T06:42:51+00:00", "completed_by": "<người khoá>",
    "detail_url": "/api/handover/delivery-orders/EPLLAO-779739f4b582"}],
  "total": 13, "page": 1, "page_size": 50}}
```

- 14 khoá của EPL_System **có đủ**: `do_id`, `status`, `customer_id`, `quotation_id`, `route_id`, `vehicle_id`, `driver_id`, `selling_price`, `customer_surcharge_total`, `final_selling_price`, `currency`, `completed_at`, `completed_by`, `detail_url`.
- Khoá thêm để thủ quỹ **đọc được bằng mắt** khi chọn DO: `doc_no`, `customer_name`, `truck_no`, `plate_head`, `driver_name`, `company`, `owner_name`, `final_selling_price_lak`.
- `customer_code` = **mã khách bên anh** (`OBJ_OBJECTNO`) mà bên em ghi ở ô "Mã khách" của danh mục khách (thêm 30/09). Khách chưa ghi mã thì `null`.
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
| `customer_id`, `customer_code`, `customer_name`, `contract_no` | khách (mã bên em, **mã bên anh**), hợp đồng vận chuyển |
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
| `invoiced`, `inv_no` | đã xuất hoá đơn chưa (bản chép bên em) |
| `completed_at`, `completed_by` | lúc khoá (UTC, `+00:00`), người khoá |
| `hire` (**chỉ xe thuê**) | `{currency, unit_price, amount, amount_lak, fee_pct, fee, over_limit_t, over_t, over_deduction, advanced_by_epl, pay_owner, pay_owner_lak, owner_self_paid_lak, acc_code: null, acc_code_note}` |

- `hire.amount` = tiền thuê xe, `fee` = phí 2 %, `over_deduction` = trừ quá tải, `advanced_by_epl` = EPL đã ứng (quy về tiền thuê), `pay_owner` = còn phải trả chủ xe.
- `hire.acc_code` **cố ý để `null`**: tài khoản chi phí thuê xe còn chờ anh Khampla chốt (mục 8, lỗ hổng 1). Bên em không tự đặt mã.

**`details[]`** — dòng 1 là **thu**, các dòng sau là **chi**:

| Khoá | Dòng thu | Dòng chi |
|---|---|---|
| `line_no`, `kind` | 1, `thu` | 2, 3…, `chi` |
| `charge_type` | `freight` | khoá khoản mục (`diesel`, `x_toll`, `x_tire`…) hoặc tên mục |
| `section`, `section_name` | `null` | `III` · `IV` · `V` · `VI` và tên mục |
| `item_key`, `name`, `name_lo` | — | khoá khoản mục; tên tiếng Việt, tiếng Lào (tên phụ tùng nếu lấy kho) |
| `qty`, `unit_price`, `actual_amount`, `currency` | tấn (hoặc 1), đơn giá, cước, tiền cước | lượng, đơn giá, thành tiền **theo tiền của dòng** |
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
- Mọi `acc_code` là **mã thật** trong danh mục Lào 494 mã. Riêng **1371, 4021, 4022** là ba mã con chờ anh mở (mục 1.1).

#### 12.8.4. Thử với nhau

- Bên em đã thử trên bản sao dữ liệu (`kiem/thu_ban_giao.py`): **13 DO đã khoá**, trong đó 2 phiếu xe thuê; **đạt cả 31 chỗ kiểm**.
- Để hệ anh gọi được sang, trang điều xe Lào phải có **địa chỉ ra Internet**. **Chủ dự án chốt 01/10:** làm xong hết rồi mới host, lúc đó bên em gửi anh địa chỉ gốc và khoá bàn giao.
- Khi có địa chỉ, bên em gửi anh: **địa chỉ gốc** và **khoá bàn giao**. Anh đổi cấu hình Logistics của đơn vị EPL Lào, rồi gọi thử `cash-voucher-references?type=DO`.

**Câu hỏi 12.8:**

1. ~~(Chủ dự án) Trang điều xe Lào ra Internet ở địa chỉ nào?~~ — chủ dự án host khi làm xong hết (01/10), rồi gửi anh.
2. (Anh Tune) Hệ anh **lưu khoá Logistics theo từng đơn vị** được không, để EPL Lào đọc trang điều xe Lào, còn đơn vị khác vẫn đọc EPL_System?
3. ~~Lọc theo mã khách bên anh~~ — **đã làm 30/09:** danh mục khách bên em có ô "Mã khách" (= `OBJ_OBJECTNO` bên anh, ≤ 50 ký tự Latinh / số / `- _ . /`, không trùng). Mỗi dòng và header trả `customer_code`; tham số `customer_id` nhận cả mã đó. Xin anh gửi danh sách mã khách của EPL Lào để bên em ghi vào.
