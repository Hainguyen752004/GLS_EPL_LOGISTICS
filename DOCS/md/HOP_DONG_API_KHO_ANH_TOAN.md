# Hợp đồng API KHO — trang điều xe EPL Lào ↔ hệ kho của anh Toàn

Phiên bản đề nghị **v1 · 30/09/2026**. Bên soạn: trang điều xe **EPL_LAO_REAL** (logistics). Người nhận: **anh Toàn** (hệ kho).

## 0. Đọc tài liệu này thế nào

### 0.1. Ranh giới ba bên (chủ dự án chốt 29–30/09/2026)

| Bên | Làm gì | Không làm gì |
|---|---|---|
| **Trang điều xe** EPL_LAO_REAL (bên em) | Phiếu xuất xe (DO), tuyến, xe, tài xế, theo dõi chuyến, duyệt các mục trên phiếu. **Lập phiếu đề nghị**: đề nghị xuất kho nhiên liệu, đề nghị tạm ứng, đề nghị thu. **Xem kho** theo mặt hàng (chỉ xem) | Không nhập, xuất, tính tồn, tính giá vốn kho. Không ghi sổ kế toán |
| **Hệ kho** của anh Toàn | Nhập, xuất, tồn, cấp phát, giá vốn bình quân, sổ kho, danh mục kho dầu và phụ tùng, kho hàng khách gửi ở bãi | — |
| **Hệ kế toán** của anh Tune | Công nợ, hoá đơn, thu chi, phiếu thu, trả chủ xe, trả nhà cung cấp, tất toán tài xế, sổ kế toán | — (hợp đồng riêng: `HOP_DONG_API_KE_TOAN_ANH_TUNE`) |

Hiện nay phần kho **đang chạy tạm** trong dự án `EPL_KETOAN` (cổng 8030, DB `epl_ketoan`). Hệ của anh sẽ **thay nửa kho** của bản tạm đó.

Mọi đường và trường trong tài liệu này **chép từ mã đang chạy** (đọc ngày 30/09/2026), nên dùng được ngay làm đặc tả.

### 0.2. Quy ước

- **LAO** là trang điều xe, thư mục `D:\Demo_Lao\EPL_LAO_REAL\backend\app`. **KHO** là hệ kho: hôm nay là bản tạm `D:\Demo_Lao\EPL_KETOAN\backend\app`, mai là hệ của anh.
- Vị trí mã ghi dạng `tệp:hàm (dòng)`, tính từ thư mục `backend/app` của dự án nói tới.
- **Hướng gọi:**
  - **LAO → KHO**: bên em gọi sang anh. Anh phải cung cấp các đường này.
  - **KHO → LAO**: hệ kho gọi về bên em. Bên em đang cung cấp các đường này.
- Mỗi đường ghi hai phần:
  - **Hiện trạng**: bản tạm đang làm đúng như vậy.
  - **Đề nghị**: bên em xin anh làm như thế trong hệ mới.
- Chưa ghi đề nghị gì thì mặc định là **giữ nguyên hiện trạng**.
- Kiểu dữ liệu:
  - `string` · `number` (số JSON, không phải chuỗi) · `bool` · `YYYY-MM-DD` (ngày) · `ISO 8601` (ngày giờ).
  - Khi có ngày giờ, múi giờ đề nghị là `+07:00` (giờ Viêng Chăn).
- Đơn vị:
  - dầu tính bằng **lít**;
  - phụ tùng tính theo đơn vị của phụ tùng (`u_pc` = cái, `u_set` = bộ, `u_l` = lít);
  - hàng khách gửi ở bãi (quặng) tính bằng **tấn**.
- **Mọi giá vốn kho tính bằng LAK** (Kíp), là số JSON.

> **Cập nhật chiều 30/09.** Anh đã gửi bản API lõi kho (`Backend.API`, swagger dev). Mục **13** đối chiếu từng việc bên em với
> đường thật của anh. Vì API của anh là lõi dùng chung, bên em sẽ **tự viết lớp chuyển** gọi API của anh (mục 13.2);
> các mục 3–4 dưới đây là giao diện bên em đang dùng nội bộ, để anh hiểu bên em cần gì ở mỗi bước.

### 0.3. Đề nghị tổng quát — cách ít việc nhất cho cả hai bên

**Anh giữ nguyên đường, tên trường và khuôn trả về như mục 3 và 4.** Khi đó bên em chỉ đổi địa chỉ gốc và khoá, không phải sửa mã. Anh muốn đường hay tên khác thì ghi vào mục 10, bên em làm lớp chuyển.

---

## 1. Kết nối, xác thực, lỗi — dùng chung cho mọi đường

### 1.1. Địa chỉ và khoá

**Hiện trạng.** LAO dùng **một** cặp địa chỉ và khoá cho cả kho lẫn kế toán. Tên cấu hình đặt trong bảng `cau_hinh` của LAO (Sếp đặt ở màn *Chứng từ → Cấu hình*). Không đặt trong bảng thì lấy biến môi trường.

| Chiều | Bên gửi đọc | Bên nhận kiểm |
|---|---|---|
| LAO → KHO | địa chỉ `ke_toan_api` (env `EPL_KE_TOAN_API`) · khoá `ke_toan_token` (env `EPL_KE_TOAN_TOKEN`) — `services/goi_ke_toan.py:cau_hinh` | KHO: `cau_hinh.token_nhan` hoặc env `EPL_KETOAN_TOKEN` (`services/bao_mat.py:_token_nhan`) |
| KHO → LAO | KHO đọc `dieu_xe_api` (env `EPL_KETOAN_DIEU_XE_API`) · `dieu_xe_token` (env `EPL_KETOAN_DIEU_XE_TOKEN`) | LAO: `cau_hinh.token_nhan_ke_toan` hoặc env `EPL_LAO_TOKEN_NHAN_KE_TOAN`. Sếp tạo khoá bằng `POST /api/lien-thong/tao-khoa` (chỉ admin; khoá hiện **một lần**, khoá cũ mất hiệu lực ngay) rồi chép sang bên kho |
| Web kho (mở trang, in mã QR) | `ke_toan_web` (env `EPL_KE_TOAN_WEB`); trống thì dùng `ke_toan_api` | — |

**Đề nghị.** Tách riêng cho hệ của anh. Bên em thêm ba khoá cấu hình (anh không phải làm gì):

- `kho_api`, env `EPL_KHO_API`;
- `kho_token`, env `EPL_KHO_TOKEN`;
- `kho_web`, env `EPL_KHO_WEB`.

Chiều ngược lại, bên em thêm `token_nhan_kho`, env `EPL_LAO_TOKEN_NHAN_KHO`. Như vậy khoá của kho và của kế toán là hai khoá khác nhau. Anh chỉ cần cho bên em:

1. địa chỉ gốc API của anh;
2. khoá máy để bên em gọi anh;
3. địa chỉ web kho (dùng cho mã QR, xem 4.8).

### 1.2. Header mọi lời gọi (hai chiều như nhau)

```
Content-Type: application/json
Authorization: Bearer <khoá máy>
X-Nguoi-Dung: <tên đăng nhập người đang bấm>        ← chỉ các đường GHI
```

- Thân là JSON UTF-8. GET và DELETE không có thân.
- `X-Nguoi-Dung` là **tên đăng nhập**. Hai bên dùng **cùng tên đăng nhập**: bản tạm chép tài khoản bằng `EPL_KETOAN/tools/chep_tai_khoan_dieu_xe.py`, cùng tên và cùng vai, còn **tài xế thì không chép**.

**Hai mức xác thực bên kho (hiện trạng)** — `services/bao_mat.py`:

| Mức | Dùng cho | Kiểm | Lỗi |
|---|---|---|---|
| `may_dieu_xe_doc` | mọi đường ĐỌC (A1, A4, A7, A8, A13, A15) | chỉ khoá máy — người mở phiếu bên LAO có thể là tài xế, không có tài khoản bên kho | 503 `CHUA_DAT_TOKEN`, 401 `SAI_TOKEN` |
| `may_dieu_xe_goi` | mọi đường GHI (A2, A3, A5, A6, A9–A12) và A14 | khoá máy + `X-Nguoi-Dung` là tài khoản còn hoạt động bên kho; tên đầy đủ người đó ghi vào `by_user` | thêm 403 `KHONG_CO_TAI_KHOAN` |

**Đề nghị:** giữ hai mức này. Nếu hệ của anh không có danh sách người dùng trùng tên với LAO, xin anh nhận `X-Nguoi-Dung` như một **chuỗi tên để ghi vết** và chỉ kiểm khoá máy. Khi đó quyền người bấm do LAO kiểm trước khi gọi (LAO đang kiểm vai ở mọi bước).

### 1.3. Dạng lỗi

- LAO đọc lỗi thế này (`services/goi_ke_toan.py:goi`):
  1. nếu thân có `detail` là object thì đọc trong đó, không thì đọc ở gốc;
  2. lấy `ma` và `loi` (hoặc `message`);
  3. **giữ nguyên mã HTTP** và ném lại cho màn hình.

  Vì vậy **câu `loi` của anh hiện nguyên lên màn cho người dùng**. Xin anh viết câu người đọc hiểu, tiếng Việt hoặc Lào.
- **Đề nghị:** lỗi nghiệp vụ trả thân phẳng
  `{"ma": "MA_LOI", "loi": "Câu cho người đọc", "message": "…"}`
  với mã HTTP đúng nghĩa: 422 dữ liệu sai · 409 xung đột trạng thái hoặc không đủ tồn · 404 không thấy · 401/403 khoá, quyền · 503 hệ đang tắt.
- Dạng `{"detail": {"ma","loi"}}` (mặc định FastAPI) bên em cũng đọc được.

### 1.4. Hết giờ, hệ tắt — bên em KHÔNG xếp hàng gửi sau

- Hết giờ: LAO → KHO **15 giây**. KHO → LAO 15 giây, riêng cấp dầu (B8) **30 giây**.
- Khi bên kia tắt hoặc chưa cấu hình, LAO trả 503 `CHUA_NOI_KE_TOAN`. Lý do có thể là:
  - chưa đặt địa chỉ hoặc khoá;
  - lỗi mạng;
  - hết giờ;
  - thân 200 nhưng không phải JSON.

  Việc cần kho mà kho tắt thì **không làm được và báo rõ**. Đây là chủ dự án chốt ngày 28/09: *"chặn và báo rõ"*.
- Một số chỗ vẫn chạy "mềm" khi kho tắt:
  - ô chọn phụ tùng dùng bản chép danh mục, không có tồn và giá (`khong_noi: true`);
  - mở phiếu gom thì ô "tồn lô" để trống;
  - màn Xe, tab Sửa chữa báo lỗi nhưng vẫn hiện phần mục V.
- **Hàng đợi mất mạng chỉ có ở màn Cấp phát của kho.** Frontend bản tạm lưu vào `localStorage` và tự gửi lại khi có mạng. Nếu anh làm màn cấp dầu ngoài hiện trường, xin giữ tính năng này, vì chủ dự án yêu cầu màn ngoài hiện trường chạy được cả khi mất mạng.

### 1.5. "Ghi rồi bù" — cách hai bên không lệch nhau

LAO dùng khuôn `GiaoDichKho` (`services/kho_ke_toan.py`, dòng 105–187):

```python
with KK.GiaoDichKho(db, user) as gd:
    r = gd.xuat_phu_tung(khoa="trip_expense:" + dong.id, ...)   # KHO ghi và COMMIT ngay
    dong.stock_move_id = r["move_id"]
# ra khỏi khối thì LAO commit. Hỏng ở đâu (kể cả lúc commit) → LAO rollback + gọi đường HUỶ cho từng lần đã ghi, ngược thứ tự
```

Bên em cần anh bảo đảm bốn điều:

1. **Mỗi đường ghi tự commit** và trả mã lần ghi (`move_id`).
2. **Mỗi đường ghi nhận khoá chống trùng `khoa`.** Gọi lại cùng khoá thì trả đúng lần cũ (`da_co: true`), **không ghi lần hai**.
3. **Có đường huỷ idempotent.** Huỷ cái không thấy thì trả 200 `{"ok": true, "da_huy": false}`, không trả lỗi.
4. **Đường huỷ nhận cả `khoa`** (không chỉ `move_id`).

   Lý do: nếu kho đã ghi mà câu trả lời không về kịp trong 15 giây, bên em chưa có `move_id`. Khi đó bên em sẽ huỷ theo `khoa`. Bên em đang sửa lớp gọi để làm việc này.

---

## 2. Luồng nghiệp vụ — việc nào gọi đường nào

| Việc (ai bấm, ở đâu) | Lời gọi | Khi kho tắt |
|---|---|---|
| Bãi lập hoặc sửa phiếu có dòng dầu mục III lấy kho EPL | **A4** (giá dòng = bình quân của đúng kho) | 503, không lưu được |
| Bãi lập phiếu đề nghị xuất kho nhiên liệu | không gọi kho (kho tự kéo danh sách, B6) | chạy bình thường |
| **Thủ kho cấp dầu theo phiếu đề nghị** (màn Cấp phát của kho, quét QR) | kho → **B7** tra cứu → **B8** cấp → LAO gọi **A5** → trả về | màn kho xếp hàng đợi |
| KT kho xăng dầu ghi sổ mục III | không gọi kho; LAO chặn nếu dòng dầu kho chưa cấp theo đề nghị (409 `CHUA_CAP_THEO_DE_NGHI`) | — |
| Tổ sửa chữa khai sửa xe lấy phụ tùng kho (màn Theo dõi tuyến) | **A1** (giá) + **A2** (xuất) | 503 |
| Tổ sửa chữa duyệt báo hỏng của tài xế, chọn lấy kho | **A1** + **A2** | 503 |
| Bãi bấm **Xe đã tới** trên phiếu **gom** (quặng về bãi) | **A9** (nhập kho hàng) | 503 |
| Bãi lập hoặc sửa phiếu **giao** lấy hàng từ lô | **A7** (ô chọn lô) + **A11** (xuất kho hàng) | 503 khi có lô |
| Mở một phiếu gom | **A8** (tồn lô) | tồn lô để trống |
| Sếp xoá phiếu | A8 → **A3** (từng dòng phụ tùng đã xuất) → **A6** (từng lần cấp dầu) → **A12** | 503 |
| Màn **Xem kho** (theo mặt hàng) | **A13** | 503 |
| Kho thêm, sửa, xoá kho dầu hoặc phụ tùng | kho → **B3 / B4 / B5** (bên em giữ bản chép) | kho rollback và báo rõ |

---

## 3. Đường LAO → KHO (anh cung cấp)

### A1. `GET /api/lien-thong/phu-tung` — danh mục phụ tùng + tồn + giá

- **Xác thực:** chỉ khoá máy. LAO không gửi `X-Nguoi-Dung`.
- **Khi nào:**
  - ô chọn phụ tùng trên phiếu (mục V) và màn Theo dõi tuyến;
  - lấy **giá bình quân** gán vào dòng phụ tùng lấy kho, gọi từ `kho_ke_toan.gia_phu_tung`, dùng khi lưu phiếu, khai sửa xe và duyệt báo hỏng.
- **Yêu cầu:** không tham số.
- **Trả về:** một mảng, mọi phụ tùng (kể cả ngưng dùng), xếp theo `name`.

| Trường | Kiểu | Nghĩa |
|---|---|---|
| `id` | string | mã phụ tùng — **cùng mã** với bản chép bên LAO (`parts.id`) |
| `name` | string | tên |
| `unit` | string | `u_pc` cái · `u_set` bộ · `u_l` lít |
| `qty` | number | tồn hiện tại |
| `min_qty` | number | tồn tối thiểu |
| `unit_price` | number | **giá bình quân hiện tại, LAK** |
| `last_date` | YYYY-MM-DD \| null | lần xuất gần nhất |
| `last_truck` | string \| null | xe nhận lần gần nhất |
| `active` | bool | đang dùng |
| `status` | `"st_low"` \| `"st_ok"` | `st_low` khi `min_qty > 0` và `qty ≤ min_qty` |

```json
[{"id": "a1b2c3d4e5f6", "name": "ຢາງລົດ 12R22.5", "unit": "u_pc", "qty": 8.0, "min_qty": 2.0,
  "unit_price": 1850000.0, "last_date": "2026-09-28", "last_truck": "341", "active": true, "status": "st_ok"}]
```

- **Lỗi:** chỉ lỗi xác thực. Ô chọn bên LAO bắt lỗi và dùng bản chép; lấy giá thì không bắt lỗi, nên việc đang làm bị chặn 503.

### A2. `POST /api/lien-thong/phu-tung/xuat` — xuất phụ tùng cho một dòng mục V

- **Xác thực:** khoá máy + `X-Nguoi-Dung`. Người bấm bên LAO là tổ sửa chữa (`repair`) hoặc Sếp (`admin`).
- **Khi nào:**
  1. Tổ sửa chữa khai sửa xe trên đường, lấy phụ tùng kho: `POST /api/trips/{tid}/events` với `repair.source = "kho"`, gọi từ `routes/phieu.py:ghi_su_kien`.
  2. Tổ sửa chữa duyệt báo hỏng của tài xế, chọn lấy kho: `routes/phieu.py:duyet_bao_hong`.

  LAO tạo dòng chi mục V trước, rồi gọi A2 **trong cùng giao dịch** (mục 1.5).
- **Yêu cầu** (LAO luôn gửi đủ các khoá):

| Trường | Kiểu | Bắt buộc | Nghĩa |
|---|---|---|---|
| `khoa` | string | có | khoá chống trùng: `"trip_expense:<id dòng chi mục V>"` |
| `part_id` | string | có | mã phụ tùng (A1 `id`) |
| `qty` | number > 0 | có | số lượng theo đơn vị phụ tùng |
| `ngay` | YYYY-MM-DD \| null | không (trống = hôm nay) | ngày xuất |
| `gia` | number \| null | không | đơn giá của **dòng** theo `tien_te`, chỉ để tính tiền tờ xuất kho. Trống thì dùng giá bình quân. LAO gửi giá bình quân đọc ở A1 |
| `tien_te` | string | không (mặc định `LAK`) | tiền của `gia`. Từ 30/09 dòng lấy kho **luôn là `LAK`** |
| `ty_gia` | number | không (mặc định 1) | LAK cho 1 đơn vị `tien_te`, theo tỷ giá khoá trên phiếu |
| `truck_no` | string \| null | không | số xe nội bộ (ví dụ `341`) |
| `trip_doc_no` | string \| null | không | số phiếu xuất xe |
| `expense_id` | string \| null | không | id dòng chi bên LAO |
| `company` | `"EPL"` \| `"joint"` | không (mặc định EPL) | `EPL` là xe nhà, `joint` là **xe thuê (liên kết)** — xem mục 5 |
| `section` | string | không (mặc định `repair`) | mục trên phiếu |
| `mo_ta` | string \| null | không | diễn giải tờ xuất kho |
| `note` | string \| null | không | ghi chú dòng sổ kho |
| `ghi_chung_tu` | bool | không (mặc định true) | false thì không sinh tờ xuất kho |
| `repair_order` | string \| null | không | số lệnh sửa chữa riêng (LAO gửi `null`) |

```json
{"khoa": "trip_expense:9f1c2a7b3d4e", "part_id": "a1b2c3d4e5f6", "qty": 2, "ngay": "2026-09-30",
 "gia": 1850000.0, "tien_te": "LAK", "ty_gia": 1.0, "truck_no": "341", "trip_doc_no": "T4-0447-09/EPL",
 "expense_id": "9f1c2a7b3d4e", "company": "EPL", "section": "repair",
 "mo_ta": "Xuất 2 ຢາງລົດ 12R22.5 sửa xe 341", "note": "Sửa xe trên đường — nổ lốp",
 "ghi_chung_tu": true, "repair_order": null}
```

- **Kho làm:**
  1. Khoá đã có thì trả lần cũ (`da_co: true`), không trừ lần hai. Hai lời gọi cùng khoá đến cùng lúc: cột `khoa` là UNIQUE, nên lời sau trả dòng của lời trước.
  2. Kiểm tồn: phải có `tồn ≥ qty`.
  3. Ghi sổ kho: `kind = "out"`, `unit_price` = **giá bình quân lúc xuất**. Trừ tồn.
  4. Sinh tờ `PXK_PT`, với `tien = qty × gia` và `tien_lak = tien × ty_gia`.
- **Trả về:**

| Trường | Kiểu | Nghĩa |
|---|---|---|
| `move_id` | string | mã dòng sổ kho — **LAO lưu vào `trip_expenses.stock_move_id`** |
| `unit_price` | number | giá bình quân LAK ghi trên dòng sổ (giá vốn thật) |
| `qty_con` | number \| null | tồn còn lại |
| `chung_tu` | string \| null | số tờ kho `PXK_PT/YYMM/NNNN` |
| `gia_dong` | number | giá dòng đã dùng cho tờ (chỉ khi `da_co = false`) |
| `da_co` | bool | true là trả lại lần xuất cũ theo `khoa` |

```json
{"move_id": "5e6f7a8b9c0d", "unit_price": 1850000.0, "qty_con": 6.0, "chung_tu": "PXK_PT/2609/0012", "gia_dong": 1850000.0, "da_co": false}
```

- **Lỗi:**
  - 422 `THIEU_KHOA`;
  - 422 `THIEU_PHU_TUNG` ("Lấy từ kho thì phải chọn phụ tùng.");
  - 422 `THIEU`, `SO_SAI`, `NGAY_SAI`;
  - **409 `KHONG_DU`** ("Kho chỉ còn … không đủ xuất …").

  Có lỗi thì LAO rollback cả lần lưu.
- **Đề nghị:** trả thêm `chung_tu` cả khi `da_co = true`. Bên em sẽ lưu số tờ kho cạnh `stock_move_id`, để phiếu xuất xe chỉ ra được tờ xuất kho nào.
- **Huỷ:** A3.

### A3. `POST /api/lien-thong/phu-tung/huy-xuat` — huỷ một lần xuất phụ tùng

- **Khi nào:**
  - bù khi LAO lưu hỏng sau A2;
  - Sếp xoá phiếu có dòng phụ tùng đã xuất.
- **Yêu cầu:** `{"move_id": "<id>" | null, "khoa": "<khoá>" | null}`. Tìm theo `move_id`, không có thì tìm theo `khoa`.
- **Kho làm:**
  1. Không thấy thì trả `{"ok": true, "da_huy": false}`.
  2. Dòng không phải `out` thì trả 409 `KHONG_PHAI_XUAT`.
  3. Còn lại: trả tồn, rút tờ `PXK_PT`, xoá dòng sổ. **Không tính lại giá bình quân.**
- **Trả về:** `{"ok": true, "da_huy": true, "qty_con": 8.0}`.

### A4. `GET /api/lien-thong/nhien-lieu/kho` — tồn và giá bình quân từng kho dầu

- **Xác thực:** chỉ khoá máy.
- **Khi nào:** mỗi lần **lưu phiếu** (lập hoặc sửa) có dòng dầu mục III lấy kho EPL. Giá dòng dầu kho chưa cấp được đọc lại mỗi lần lưu, cho tới lúc cấp.
- **Yêu cầu:** không tham số.
- **Trả về:** object, khoá là `place_id`, chỉ gồm kho EPL (`owner_type = "epl"`), kể cả kho ngưng dùng.

```json
{"k1a2b3c4d5e6": {"ton_lit": 12450.5, "gia_bq": 14250.0},
 "k9f8e7d6c5b4": {"ton_lit": 0.0, "gia_bq": 0.0}}
```

- `ton_lit` tính bằng lít, làm tròn 3 số lẻ. `gia_bq` tính bằng **LAK/lít**, làm tròn 2 số lẻ. Thuật toán ở mục 6.
- Dòng không ghi kho thì thuộc **kho gốc** `code = "KHO-TB"` (Thà Bốc).

### A5. `POST /api/lien-thong/nhien-lieu/xuat` — xuất dầu theo phiếu đề nghị

- **Xác thực:** khoá máy + `X-Nguoi-Dung`. Người bấm là:
  - thủ kho nhiên liệu (`depot`), chỉ kho của mình;
  - KT kho xăng dầu (`fuel`);
  - Sếp (`admin`).
- **Khi nào:** thủ kho cấp dầu theo **phiếu đề nghị xuất kho nhiên liệu**. Từ 30/09 đây là **đường duy nhất** để dầu kho rời kho.
- **Chuỗi gọi hiện tại** (vòng tròn): thủ kho bấm ở màn Cấp phát của kho → kho gọi **B8** sang LAO → LAO kiểm quyền, kiểm phiếu → LAO gọi **A5** sang kho → LAO commit → trả phiếu về kho.
- **Yêu cầu:**

| Trường | Kiểu | Bắt buộc | Nghĩa |
|---|---|---|---|
| `khoa` | string | có | `"voucher:<id phiếu đề nghị>"` — ổn định qua các lần thử lại |
| `place_id` | string | không (trống = kho gốc) | kho dầu EPL. Sai thì 422 `KHO_SAI` |
| `qty_l` | number > 0 | có | **lít cấp thật** |
| `ngay` | YYYY-MM-DD \| null | không | ngày cấp |
| `doc_no` | string \| null | không | số phiếu đề nghị, dạng `PLNL-<số phiếu xuất xe>-<n>` |
| `truck_no` | string \| null | không | số xe |
| `expense_id` | string \| null | không | id dòng dầu đầu tiên của kho đó |
| `voucher_id`, `voucher_doc_no` | string \| null | không | id và số phiếu đề nghị |
| `trip_no` | string \| null | không | số phiếu xuất xe |
| `company` | `"EPL"` \| `"joint"` | không | xe nhà / **xe thuê** (mục 5) |
| `gia_du_phong` | number \| null | không | giá dùng khi kho **chưa có giá bình quân** |
| `kiem_ton` | bool | không (false) | LAO **luôn gửi false**: cấp theo đề nghị không chặn theo tồn (xem câu hỏi 10.4) |
| `ghi_chung_tu` | bool | không (true) | false thì không sinh tờ `PXK_NL` |
| `mo_ta`, `note` | string \| null | không | diễn giải tờ, ghi chú sổ |

```json
{"khoa": "voucher:3c4d5e6f7a8b", "place_id": "k1a2b3c4d5e6", "qty_l": 200.0, "ngay": "2026-09-30",
 "doc_no": "PLNL-T4-0447-09/EPL-1", "truck_no": "341", "expense_id": "7d8e9f0a1b2c", "voucher_id": "3c4d5e6f7a8b",
 "voucher_doc_no": "PLNL-T4-0447-09/EPL-1", "trip_no": "T4-0447-09/EPL", "company": "EPL", "gia_du_phong": 14000.0,
 "kiem_ton": false, "ghi_chung_tu": true, "mo_ta": "Cấp 200.0 lít dầu theo PLNL-T4-0447-09/EPL-1", "note": "Cấp theo phiếu đề nghị"}
```

- **Kho làm:**
  1. Khoá có rồi thì trả lần cũ (`da_co: true`).
  2. Ghi sổ dầu: `kind = "out"`, `unit_price = unit_cost_lak` = giá bình quân của **đúng kho** lúc xuất (kho chưa có giá thì dùng `gia_du_phong`), `currency = "LAK"`.
  3. Sinh tờ `PXK_NL`.
- **Trả về:**
  `{"move_id": "0a1b2c3d4e5f", "unit_price": 14250.0, "qty_l": 200.0, "chung_tu": "PXK_NL/2609/0031", "da_co": false}`

  với `unit_price` tính bằng **LAK/lít**.
- **LAO lưu:**
  - Mọi dòng dầu kho chưa cấp của kho đó nhận `unit_price = r.unit_price`, `currency = "LAK"`, `stock_move_id = r.move_id`.
  - Cấp lệch và chỉ có một dòng thì dòng đó nhận `qty` = lít cấp thật.
  - Phiếu đề nghị nhận `granted_qty`, `granted_note`, `status = "da_cap"`, `granted_by`, `granted_at`.
- **Lỗi:** 422 `THIEU_KHOA` · 422 `KHO_SAI` · 422 `THIEU` / `SO_SAI` / `NGAY_SAI` · 409 `KHONG_DU` (chỉ khi `kiem_ton` = true).
- **Đề nghị:**
  1. Gọi lại cùng `khoa` mà **số lít khác** lần đầu thì trả **409 `KHAC_LAN_DAU`** (kèm số lít lần đầu), không trả lặng lẽ lần cũ. Hiện nay bên em có thể ghi 180 L trong khi kho đã ghi 200 L.
  2. Có thể **đảo chiều luồng**: kho tự xuất rồi gọi sang LAO báo "đã cấp", kèm `move_id`, `unit_price`, số lít, người cấp và giờ cấp. Anh chọn ở câu hỏi 10.5.

### A6. `POST /api/lien-thong/nhien-lieu/huy-xuat` — huỷ một lần xuất dầu

- **Khi nào:**
  - bù sau A5;
  - Sếp xoá phiếu. Mỗi `stock_move_id` khác nhau của dòng dầu kho gọi **một lần**.
- **Yêu cầu:** `{"move_id": "<id>" | null, "khoa": "<khoá>" | null}`.
- **Kho làm:** không thấy thì trả `{"ok": true, "da_huy": false}`. Dòng không phải `out`, hoặc là dòng chuyển kho, thì trả 409 `KHONG_PHAI_XUAT`. Còn lại: xoá dòng sổ, rút tờ `PXK_NL`.
- **Trả về:** `{"ok": true, "da_huy": true}`.
- Kho **chặn xoá tay** dòng sổ do LAO sinh: 409 `CUA_DIEU_XE`.

### A7. `GET /api/lien-thong/kho-hang/lo?tru_phieu=<trip_id>` — lô hàng khách gửi còn hàng

- Hàng khách gửi ở bãi là **quặng của khách** nằm ở bãi Thà Bốc giữa hai chặng: xe **gom** chở từ mỏ về bãi, xe **giao** chở từ bãi ra cảng. Hàng này **không phải tài sản EPL**, ghi ngoài bảng và tính bằng tấn.
- **Lô = một phiếu gom.**
- **Yêu cầu:** `tru_phieu` là phiếu giao đang sửa. Phần mà chính phiếu đó đang giữ không bị trừ khỏi tồn lô.
- **Trả về:** mảng lô còn hàng (`con_t > 0.0005`), xếp theo `ngay`, `doc_no`.

| Trường | Kiểu | Nghĩa |
|---|---|---|
| `lo_trip_id` | string | mã lô = **id phiếu gom bên LAO** |
| `doc_no` | string | số phiếu gom |
| `goods_name` | string | tên hàng (chữ — xem 10.9) |
| `ngay` | YYYY-MM-DD | ngày nhập đầu |
| `nhap_t`, `dieu_chinh_t`, `con_t` | number | tấn nhập · tấn điều chỉnh (có dấu) · tấn còn |
| `customer_name`, `origin`, `truck_no` | string \| null | chép lúc nhập |

### A8. `GET /api/lien-thong/kho-hang/phieu/{tid}` — hàng của một phiếu

- **Trả về:** `{"da_nhap": true, "ton_lo": 12.1, "lay_boi": ["T4-0450-09/EPL"], "xuat": [{"goods_name","qty_t","lo_trip_id"}]}`.
- **Dùng khi:**
  - mở phiếu gom, lấy `ton_lo`;
  - sửa cân phiếu gom (`da_nhap` = true thì LAO chặn 409 `HANG_DA_NHAP_KHO`);
  - xoá phiếu (`lay_boi` không rỗng thì LAO chặn 409 `LO_DA_XUAT`).

### A9. `POST /api/lien-thong/kho-hang/nhap` — xe gom về tới bãi, hàng vào kho bãi

- **Khi nào:** Bãi bấm **Xe đã tới** trên phiếu gom (`POST /api/trips/{tid}/transport-status` với `status = "arrived"`).
- **LAO tính trước khi gửi:**
  - `boc_len` = tấn cân tại mỏ;
  - `tan` = thực nhập, lấy cân tại bãi nếu có, không thì lấy `boc_len`;
  - `dong` = chia `tan` theo tỷ lệ các dòng hàng;
  - `hao_hut = boc_len − tan`.
- **Yêu cầu:**

| Trường | Kiểu | Bắt buộc | Nghĩa |
|---|---|---|---|
| `trip_id` | string | có | id phiếu gom (thành `lo_trip_id`) |
| `trip_doc_no` | string | không | số phiếu |
| `ngay` | YYYY-MM-DD \| null | không | ngày nhập |
| `dong` | `[{goods_name, qty_t}]` | có | tấn thực nhập từng mặt hàng; dòng ≤ 0 bị bỏ |
| `customer_name`, `origin`, `truck_no`, `company` | string \| null | không | chép vào lô |
| `tan`, `boc_len`, `hao_hut` | number | không | tổng thực nhập · cân tại mỏ · chênh |
| `ma_hang_gui` | string \| null | không | mã tài khoản ngoài bảng "hàng khách gửi" (bên kế toán cấp) |

- **Kho làm:**
  - Phiếu đã có dòng nhập thì trả `{"da_co": true}`. **Gọi lại không nhập trùng.**
  - Còn lại: ghi sổ hàng và sinh `PNK_HH` (tấn, `tien_lak = 0`, ngoài bảng).
- **Trả về:** `{"da_co": false, "so_dong": 1, "chung_tu": "PNK_HH/2609/0007"}`.
- **Lỗi:** 422 `THIEU_PHIEU` · 422 `NGAY_SAI`.
- **Đề nghị:** `qty_t` không phải số thì trả 422, không phải 500.

### A10. `POST /api/lien-thong/kho-hang/huy-nhap` — chỉ dùng để bù sau A9

- **Yêu cầu:** `{"trip_id": "<id>"}`.
- **Trả về:** `{"ok": true, "so_dong": 1}`.
- **Lỗi:** 409 `LO_DA_DUNG`: lô đã có phiếu giao lấy hoặc đã điều chỉnh.

### A11. `POST /api/lien-thong/kho-hang/xuat` — phiếu giao lấy hàng từ lô

- **Khi nào:** lập hoặc sửa phiếu **giao** có dòng hàng lấy từ lô. LAO kiểm trước: mỗi dòng phải có lô, và lô phải là một phiếu gom.
- **Yêu cầu:** `{"trip_id", "trip_doc_no", "ngay", "dong": [{goods_name, qty_t, lo_trip_id}], "company", "ma_hang_gui"}`.
  - `dong` là **toàn bộ** phần xuất mới của phiếu: thay thế, không cộng dồn.
  - `[]` nghĩa là bỏ hết phần xuất.
  - Khi bù, LAO gửi `dong = cu` (lần trước) kèm `"khoi_phuc": true`.
- **Kho làm:**
  1. Mỗi lô phải đã nhập (422 `LO_CHUA_NHAP`).
  2. Tổng tấn mỗi lô không được vượt tồn lô cộng phần phiếu này đang giữ (409 `KHONG_DU_HANG`).
  3. Xoá phần xuất cũ, ghi phần mới.
- **Trả về:** `{"cu": [<phần xuất TRƯỚC lần gọi này>], "chung_tu": "PXK_HH/2609/0009" | null}`.
- **Đề nghị:** khi sửa tấn hoặc lô của phiếu giao, **cập nhật tờ `PXK_HH`** theo. Hiện nay tờ chỉ sinh lần đầu, sửa sau không đổi tờ.

### A12. `POST /api/lien-thong/kho-hang/huy` — xoá hàng của một phiếu

- **Yêu cầu:** `{"trip_id": "<id>"}`.
- **Kho làm:** xoá mọi dòng sổ nhập, xuất, điều chỉnh của phiếu, và rút tờ.
- **Trả về:** `{"ok": true, "so_dong": 3}`.
- **Lỗi:** 409 `LO_DA_XUAT`: lô đã cho phiếu giao khác lấy.

### A13. `GET /api/lien-thong/kho/mat-hang?thang=YYYY-MM` — dữ liệu màn Xem kho (theo mặt hàng)

- **Việc:** màn **Xem kho** ở trang logistics. Sếp chốt ngày 30/09: *"kho thì mình dùng để quản lý tồn kho, quản lý theo item … bên mình chỉ để view"*.
- **Yêu cầu:** `thang` (tuỳ chọn, trống là tháng này). Sai dạng thì 422 `THANG_SAI`.
- **Trả về:**

```json
{"thang": "2026-09",
 "nhien_lieu": [{"place_id": "k1a2b3c4d5e6", "code": "KHO-TB", "name": "…", "country": "LA", "active": true,
                 "ton_lit": 12450.5, "gia_bq": 14250.0, "nhap_thang": 20000.0, "xuat_thang": 7549.5,
                 "gan_day": [{"ngay": "2026-09-30", "kind": "out", "qty": 200.0, "doc_no": "PLNL-T4-0447-09/EPL-1",
                              "truck_no": "341", "chuyen_kho": false, "gia": 14250.0}]}],
 "phu_tung": [{"id": "a1b2c3d4e5f6", "name": "…", "unit": "u_pc", "active": true, "ton": 8.0, "min_qty": 2.0,
               "gia_bq": 1850000.0, "nhap_thang": 10.0, "xuat_thang": 2.0,
               "gan_day": [{"ngay": "2026-09-30", "kind": "out", "qty": 2.0, "doc_no": "T4-0447-09/EPL", "truck_no": "341", "gia": 1850000.0}]}],
 "hang": [{"name": "ແຮ່ເຫຼັກ (quặng sắt)", "ton_t": 12.1, "nhap_thang": 32.1, "xuat_thang": 20.0,
           "lo": [{"doc_no": "G4-0104-09/EPL", "ngay": "2026-09-29", "customer_name": "…", "origin": "…", "truck_no": "341", "nhap_t": 32.1, "con_t": 12.1}],
           "gan_day": [{"ngay": "2026-09-30", "kind": "out", "qty": 20.0, "doc_no": "T4-0450-09/EPL", "truck_no": null, "customer_name": null}]}]}
```

| Khối | Quy tắc |
|---|---|
| `nhien_lieu` | mỗi kho EPL một dòng (cả ngưng dùng), xếp `country`, `name`; `nhap_thang` / `xuat_thang` là lít vào / ra trong tháng (tính cả chuyển kho); `gan_day` ≤ 10 dòng mới nhất; `gia` = giá vốn dòng |
| `phu_tung` | mọi phụ tùng; `ton` = tồn; `gia_bq` = bình quân LAK; `gan_day` ≤ 10 |
| `hang` | mỗi tên hàng một dòng, xếp tồn giảm dần; `lo` = các lô còn hàng; `gan_day` ≤ 10 (nhập, xuất, điều chỉnh) |

- **LAO tự thêm** (anh không phải làm):
  - với kho dầu: phiếu đề nghị chờ cấp (`de_nghi`), dòng dầu kho chưa có đề nghị (`chua_de_nghi`), `con_dung = tồn − chờ cấp − chưa đề nghị`;
  - với phụ tùng: dòng mục V lấy kho chưa rời kho (`tren_phieu`);
  - lọc giá theo vai.

### A14. `GET /api/lien-thong/kiem` — thử kết nối

- Sếp bấm **Kiểm kết nối** bên LAO. Cần `X-Nguoi-Dung`.
- **Trả về:** `{"ok": true, "ben": "<tên hệ>", "nguoi": "<username>", "vai": "<vai>"}`.

### A15. `GET /api/lien-thong/sua-chua/xe/{vid}` — lệnh sửa chữa riêng của một xe

- **Dùng ở:** màn Xe, tab Sửa chữa.
- **Trả về:** ≤ 80 dòng dạng `{doc_no, doc_date, item_key, item_name, qty, unit_price, currency, source, acct_code, tien_lak, lenh: true, kind: "bao_duong"|"sua_chua", status: "entered|verified|booked|paid"}`.
- Lệnh sửa chữa riêng (xe nằm xưởng, không gắn phiếu) đang ở bản tạm. **Cần chốt thuộc hệ nào** (câu hỏi 10.8).

---

## 4. Đường KHO → LAO (bên em cung cấp, hệ của anh gọi)

Chung cho mục này:

- **Xác thực:** khoá máy của LAO (1.1) + `X-Nguoi-Dung` là tài khoản còn hiệu lực ở LAO.
- **Quyền:** LAO kiểm quyền **theo vai của người đó bên LAO**.
- **Lỗi:** dạng `{"detail": {"ma","loi"}}`.

### B1. `GET /api/lien-thong/kiem`

Trả về `{"ok": true, "ben": "EPL_LAO_REAL", "nguoi": "<username>", "vai": "<role>"}`.

### B2. `GET /api/lien-thong/diem-do/thong-tin`

- Trả về `{"nha_cung_cap": [{"id","name"}], "cho_cap": {"<place_id>": 3}}`.
- `nha_cung_cap` là danh mục nhà cung cấp (bản gốc ở LAO). `cho_cap` là số phiếu đề nghị đang chờ, tính theo từng kho.

### B3. `PUT /api/lien-thong/ban-sao/diem-do/{pid}` · B4. `DELETE /api/lien-thong/ban-sao/diem-do/{pid}`

- **Bản gốc** danh mục kho dầu và trạm dầu nằm ở **kho**. LAO giữ **bản chép chỉ đọc cùng `id`**, vì dòng chi, phiếu đề nghị và tài khoản thủ kho bên LAO đều trỏ vào `id` này.
- Kho thêm, sửa hay xoá thì gọi B3 hoặc B4 **trong cùng lần lưu**. LAO từ chối thì kho rollback.
- **B3 — thân:** `{"id","code","name","country","owner_type","supplier_id","address","note","active"}`.
  - `owner_type`: `"epl"` là kho công ty, dầu lấy ở đây là **xuất kho**; `"ngoai"` là trạm bán dầu, dầu lấy ở đây là **mua ngoài**.
  - `supplier_id` phải có trong danh mục nhà cung cấp của LAO.
  - Trả về `{"ok": true, "id": "<pid>"}`.
  - Lỗi: 422 `THIEU_TEN`, `LOAI_SAI`, `KHONG_THAY_NCC`.
- **B4 — xoá:** LAO chặn khi kho dầu còn nằm trên phiếu, sự kiện, phiếu đề nghị, sổ dầu cũ, phiếu bán hoặc tài khoản thủ kho: 409 `DANG_DUNG` ("… chỉ được ngưng dùng, không xoá").
- **Kho gốc** nhận diện bằng `code = "KHO-TB"` ở **cả hai bên**.

### B5. `PUT /api/lien-thong/ban-sao/phu-tung/{pid}`

- Thân: `{"name","unit","min_qty","active"}`.
- LAO chỉ giữ **danh mục**, không giữ tồn và giá (tồn và giá luôn đọc ở A1).
- Không có đường xoá phụ tùng. Muốn bỏ thì đặt `active = false`.

### B6. `GET /api/lien-thong/cap-phat?trang_thai=cho` — danh sách phiếu đề nghị chờ cấp

- **Quyền phía LAO:**
  - thủ kho nhiên liệu chỉ thấy phiếu dầu của **kho mình** (chưa gắn kho thì 409 `CHUA_GAN_KHO`);
  - tổ sửa chữa và thủ kho phụ tùng bị 403.

  Trả tối đa 500 tờ mới nhất.
- **Mỗi phần tử:**

| Trường | Nghĩa |
|---|---|
| `id`, `trip_id`, `kind` (`fuel` \| `advance`), `doc_no`, `doc_date` | phiếu đề nghị. `fuel` = đề nghị xuất kho nhiên liệu (của anh). `advance` = đề nghị tạm ứng (của anh Tune) |
| `place_id`, `place_name`, `place_country` | kho lĩnh |
| `driver_id`, `driver_name`, `truck_no` | |
| `qty_l` | lít được duyệt |
| `amount_lak` | tiền tạm ứng (chỉ phiếu `advance`; null với vai không thấy tiền) |
| `status` | `cho` \| `da_cap` \| `huy` |
| `token`, `qr`, `tra_cuu` | mã tra cứu; ảnh QR; đường mở web kho `<kho_web>/#/cap-phat?ma=<token>` |
| `hinh_thuc` | `noi_bo` (xe nhà — xuất nội bộ) · `xuat_ban` (xe thuê — **xuất bán cho chủ xe**) · `cong_no_chu_xe` (tạm ứng xe thuê) |
| `owner_name` | chủ xe (chỉ xe thuê) |
| `issued_by`, `issued_at`, `granted_by`, `granted_at`, `granted_qty`, `granted_note`, `note` | |
| `origin`, `destination`, `plate_head`, `plate_trailer`, `customer_name`, `trip_doc_no`, `trip_kind`, `company` | lấy từ phiếu xuất xe |

### B7. `GET /api/lien-thong/cap-phat/tra-cuu/{token}` — quét mã QR

- Trả về như một phần tử B6, cộng thêm:
  - `phieu`: `{doc_no, truck_no, plate_head, plate_trailer, driver_name, company, owner_name, origin, destination, customer_name, goods_type, weight_origin, out_date, transport_status}`;
  - `dong`: `[{item_key, item_name, qty, unit_price, currency, tien_lak, acct_code}]`.
- **Lọc tiền theo vai phía LAO** (sửa 30/09):
  - thủ kho **không nhận giá vốn**: `unit_price` và `tien_lak` của dòng dầu kho bị bỏ;
  - Bãi không nhận tiền nào.
- **Lỗi:** 404 `KHONG_THAY`.

### B8. `POST /api/lien-thong/cap-phat/{vid}/cap` — thủ kho bấm Cấp dầu

- **Thân:** `{"qty": 200, "note": ""}`.
  - `qty` là lít cấp thật (trống thì lấy số duyệt).
  - `note` là lý do, **bắt buộc khi lệch** quá 0,001 lít.
- **LAO làm:**
  1. Kiểm phiếu còn `cho`, vai `depot | fuel | admin`, và thủ kho đúng kho.
  2. Gọi **A5** với `khoa = "voucher:<vid>"`.
  3. Gán giá và `stock_move_id` vào dòng; phiếu chuyển `da_cap`.
- **Trả về:** phiếu đề nghị như B6.
- **Lỗi:**
  - 404 `KHONG_THAY`;
  - 409 `DA_CAP` ("Phiếu này đã cấp hoặc đã huỷ.");
  - 403 `KHONG_CO_QUYEN`, `KHAC_KHO`;
  - 422 `SO_LIT_SAI`, `THIEU_LY_DO`;
  - 409 `KHONG_CON_DONG`;
  - mọi lỗi của A5, và 503 khi LAO không nối được ngược sang kho.
- **Chống trùng:** gửi lại thì 409 `DA_CAP`. Lần xuất bên kho chống trùng bằng `voucher:<vid>`.
- **Đề nghị:** khi màn của anh gửi lại từ hàng đợi mất mạng, gửi kèm **giờ cấp thật** (`luc`, ISO 8601). Bên em sẽ ghi ngày xuất theo giờ đó, không theo giờ gửi được.

### B9. `GET /api/lien-thong/ty-gia`

- Trả về `{"USD": 22000.0, "THB": 700.0, "VND": 1.2, "CNY": 3000.0}` — **LAK cho 1 đơn vị**, bảng tỷ giá hiện hành.
- Kho dùng khi nhập kho bằng ngoại tệ, nếu người nhập không gõ tỷ giá.

### B10. `GET /api/lien-thong/ma-ke-toan`

Trả về `{"ma_hang_khach_gui": "<mã>" | null, "ma_gia_von": "<mã>" | null}`. Đây là hai mã tài khoản đặt ở cấu hình LAO.

### B11–B13 (lệnh sửa chữa riêng, bán hàng ở quầy — chờ chốt thuộc ai, 10.8)

| # | Đường | Làm gì |
|---|---|---|
| B11 | `GET /api/lien-thong/xe` | trả `[{id, truck_no, plate_head, owner_type, odometer_km, status, active}]` |
| B12 | `POST /api/lien-thong/xe/{vid}/sua-chua` | thân `{"vao": true\|false}` → xe vào xưởng (`maintenance`) hoặc ra xưởng |
| B13 | `GET /api/lien-thong/nguoi-mua` | trả `{"khach": [...], "chu_xe": [...]}` |

### 4.8. Mã QR trên phiếu giấy (không phải API nhưng là giao ước)

- Mã QR in trên phiếu đề nghị trỏ tới `<kho_web>/#/cap-phat?ma=<token>`.
- Phiếu giấy **đã in** mang địa chỉ này mãi. Vì vậy web của anh cần:
  - **nhận đúng đường `#/cap-phat?ma=<token>`**; hoặc
  - chuyển tiếp từ địa chỉ cũ.

---

## 5. Xe thuê (liên kết): dầu và phụ tùng kho là XUẤT BÁN

Chủ dự án chốt dầu ngày 29/09 và phụ tùng ngày 30/09. Khi DO chạy bằng **xe thuê** (`company = "joint"`) mà EPL ứng:

- **dầu lấy kho EPL** và **phụ tùng lấy kho EPL** là **bán cho chủ xe**, theo **giá bán riêng**:
  - dầu: KT kho xăng dầu gõ giá bán khi kiểm mục III;
  - phụ tùng: KT Chi phí gõ giá bán khi kiểm mục V.
- Tiền trả chủ xe trừ theo **giá bán**. Giá vốn vẫn là bình quân kho.

**Hiện trạng bên kho tạm:** tờ xuất kho của xe thuê ghi **Nợ 4022 / Có 1371 theo giá vốn**. Như vậy là sai, vì đây là một lần bán.

**Đề nghị cho hệ của anh:**

| Việc | Hệ ghi | Định khoản | Số tiền |
|---|---|---|---|
| Hàng rời kho khi bán cho chủ xe | **kho (anh)** | **Nợ 607 / Có 1371** | giá vốn bình quân |
| Doanh thu bán cho chủ xe, trừ vào tiền trả | **kế toán (anh Tune)** | **Nợ 4022 / Có 707** | giá bán |

- Kho nhận biết lần bán nhờ trường **`company = "joint"`**, đã có trong A2 và A5.
- Bên em đề nghị thêm hai trường nữa để anh ghi đúng bản chất và không phải suy luận:
  - `hinh_thuc` = `"xuat_ban"` hoặc `"noi_bo"`;
  - `owner_id` (mã chủ xe bên LAO).
- **Giá bán không gửi sang kho**, vì giá bán thường được gõ **sau** lúc xuất (phụ tùng xuất ngay lúc khai). Giá bán đi sang anh Tune cùng tờ bán.

---

## 6. Giá vốn bình quân — luật đang chạy (anh Khampla C5.3, "ລາຄາສະເລ່ຍ")

- **Dầu** — bản tạm `services/gia_von_dau.py`:
  - bình quân gia quyền **theo từng kho**;
  - chạy theo thứ tự ngày, rồi giờ tạo, rồi `id`.
  - **Nhập** cộng `lít × unit_cost_lak`. Giá nhập quy ra LAK theo **tỷ giá lúc nhập**.
  - **Xuất** (cho xe, bán, chuyển kho) trừ theo giá bình quân hiện hành, không theo giá ghi trên dòng.
  - Tồn ≤ 0,0001 thì giá trị về 0, còn giá giữ số cuối cùng.
  - Kết quả làm tròn: lít 3 số lẻ, giá 2 số lẻ.
- **Phụ tùng:**
  - mỗi lần nhập có giá > 0: `giá mới = (max(tồn,0) × giá cũ + qty × giá nhập) / (max(tồn,0) + qty)`, làm tròn 2;
  - nhập không giá thì giữ giá cũ;
  - xuất ghi giá bình quân lúc xuất;
  - huỷ xuất thì trả tồn, không tính lại giá.
- **Hàng khách gửi:** không có giá (tấn, ngoài bảng).
- Kho chưa có giá dầu thì A5 dùng `gia_du_phong`. LAO chặn bước kiểm mục khi dòng EPL trả có đơn giá 0 (409 `THIEU_DON_GIA`).

## 7. Ai được thấy giá vốn kho (chủ dự án chốt 30/09)

| Vai | Thấy giá vốn kho? |
|---|---|
| Bãi (`yard`), tài xế (`driver`) | không (vốn đã không thấy tiền chi) |
| **Thủ kho nhiên liệu (`depot`), thủ kho phụ tùng (`parts`), tổ sửa chữa (`repair`)** | **không** — thủ kho giữ số lượng, kế toán giữ giá trị; lộ giá vốn là lộ lãi bán dầu cho chủ xe |
| Kế toán, quỹ, Sếp | có |

- Các đường đọc của kho (A1, A4, A13) **trả giá cho mọi người gọi**, rồi LAO tự lọc trước khi hiện.
- **Xin anh áp cùng luật này trên màn của hệ kho.** Màn kho của bản tạm hiện chỉ che giá với Bãi.

## 8. Mã dùng chung và bên giữ bản gốc

| Mã | Gốc ở | Bên kia giữ | Ghi chú |
|---|---|---|---|
| Kho dầu, trạm dầu `fuel_places.id` (12 hex), `code` | **kho** | LAO: bản chép chỉ đọc cùng `id` (B3, B4) | kho gốc `KHO-TB` |
| Phụ tùng `parts.id` | **kho** (tồn, giá, sổ) | LAO: bản chép danh mục (B5) | |
| Dòng sổ kho `move_id` | **kho** | LAO lưu ở `trip_expenses.stock_move_id` | dòng có `stock_move_id` thì không xoá, không đổi số lượng trên phiếu được (409 `DA_XUAT_KHO`) |
| Số tờ kho `PXK_PT`, `PXK_NL`, `PNK_*`, `CK_NL`, `*_HH` dạng `LOAI/YYMM/NNNN` | **kho** sinh | LAO sẽ lưu (A2 đề nghị) | |
| Lô hàng `lo_trip_id` | **LAO** (id phiếu gom) | kho chép | |
| Phiếu xuất xe, dòng chi, phiếu đề nghị (`id`, `doc_no`, `token`) | **LAO** | kho chép vào `expense_id`, `voucher_id`, `trip_doc_no`, `khoa` | |
| Xe, tài xế, nhà cung cấp, khách, chủ xe, tỷ giá | **LAO** | kho hỏi B2, B9, B11, B13 | |
| Người dùng | mỗi bên một bảng, **cùng `username`** | | tài xế không có tài khoản bên kho |

- Nếu hệ của anh dùng **id riêng** cho kho dầu và phụ tùng, xin anh tiếp tục gọi B3 và B5 để bên em chép theo id của anh. Khi đó mọi khoá ngoại bên em vẫn đúng.

## 9. Chứng từ kho gửi sổ kế toán (hệ anh Tune)

Mỗi lần nhập hay xuất ở kho sinh một **tờ kho có định khoản**. Sổ của anh Tune nhận các tờ này. Bảng dưới là định khoản sau đợt rà ngày 30/09 (theo Excel của khách, quy trình của anh Khampla, và danh mục tài khoản thật của bên kế toán):

| Tờ | Khi nào | Nợ | Có | Tiền |
|---|---|---|---|---|
| `PXK_NL` | cấp dầu theo đề nghị (A5) | xe nhà **625** · xe thuê **607** (đề nghị, mục 5) | **1371** | LAK giá vốn |
| `PXK_PT` | xuất phụ tùng (A2) | mục V xe nhà **614** · xe thuê **607** (đề nghị) | **1371** | LAK |
| `PNK_NL`, `PNK_PT` | nhập kho (màn kho) | **1371** | **4021** (nợ nhà cung cấp) | tiền nhập, kèm quy LAK |
| `CK_NL` | chuyển dầu giữa hai kho EPL | — | — | không bút toán (tài sản vẫn ở 1371) |
| `PNK_HH` · `PXK_HH` · `DC_HH` | nhập, xuất, điều chỉnh hàng khách gửi | mã **ngoài bảng** `ma_hang_khach_gui` (ghi đơn) | | 0 (tấn trong `lines`) |
| `PXK_BAN` | bán dầu, phụ tùng ở quầy | **607** | **1371** | LAK giá vốn |

- `1371` (con của 137) và `4021` (con của 402) là **mã con của anh Khampla**. Chủ dự án chốt giữ hai mã này. Bên kế toán đang được nhờ mở chúng trong danh mục (hợp đồng với anh Tune).
- **Nội dung `lines` từng tờ (hiện trạng):**
  - `PXK_NL`: `{qty_l, unit_price, currency: "LAK", place_id, truck_no, voucher_doc_no}`
  - `PXK_PT`: `{part_id, qty, unit_price, currency, truck_no, repair_order}`
  - `PNK_NL`: `{qty_l, unit_price, currency, unit_cost_lak, place_id, place_name, supplier_id, doc_no}`
  - `CK_NL`: `{transfer_no, qty_l, unit_cost_lak, from_place_id, from_place, to_place_id, to_place}`
  - `PNK_HH`: `{tan, boc_len, hao_hut}`
  - `PXK_HH`: `{tan, dong: [{hang, tan, lo}]}`
  - `DC_HH`: `{chieu: "tang"|"giam", tan, lo, ly_do}`
- **Ai đẩy tờ kho vào sổ kế toán, theo khuôn nào:** anh và anh Tune chốt với nhau. Bên em đề nghị dùng đúng phong bì tờ trong hợp đồng với anh Tune (`source`, `ref`, `type`, `amount`, `entry`, `lines`).

## 10. Câu hỏi cần anh trả lời

1. **Đường và tên trường:** anh giữ nguyên như mục 3 và 4 được không? Nếu không, anh gửi bảng đổi tên.
2. **Người bấm:** hệ của anh có danh sách người dùng trùng `username` với LAO không, hay chỉ nhận `X-Nguoi-Dung` để ghi vết (1.2)?
3. **Huỷ theo `khoa`:** anh nhận huỷ theo `khoa` (không có `move_id`) được không (1.5)?
4. **Tồn âm dầu:** cấp theo đề nghị hiện không chặn theo tồn (`kiem_ton = false`). Hệ của anh có cho tồn âm không? Nếu không, bên em xử lý 409 `KHONG_DU` thế nào — chặn cấp hay báo Sếp?
5. **Luồng cấp dầu:**
   - (a) giữ vòng tròn như hiện nay (kho gọi B8, LAO gọi A5); hay
   - (b) kho xuất trước rồi gọi một đường mới bên LAO để báo "đã cấp".

   Bên em làm được cả hai.
6. **Xuất bán cho xe thuê (mục 5):** anh ghi PXK theo Nợ 607 được không, và cần thêm `hinh_thuc`, `owner_id` không?
7. **Số tờ kho:** anh trả `chung_tu` cả khi `da_co = true` được không (A2)?
8. **Lệnh sửa chữa riêng và bán hàng ở quầy** (A15, B11–B13) thuộc hệ của anh, của anh Tune, hay về logistics? Chủ dự án sẽ chốt.
9. **Mã mặt hàng:** hàng khách gửi hiện định danh bằng **tên chữ** (`goods_name`). Sếp muốn "quản lý theo item". Anh có mã mặt hàng chung (dầu diesel, từng phụ tùng, quặng sắt…) để hai bên dùng không?
10. **Mã QR cũ (4.8):** web của anh nhận đường `#/cap-phat?ma=<token>` được không?
11. **Màn của anh che giá vốn** với thủ kho và tổ sửa chữa (mục 7) được không?

## 11. Việc bên em làm khi anh trả lời

| Việc | Khi nào |
|---|---|
| Thêm cấu hình riêng `kho_api`, `kho_token`, `kho_web`, `token_nhan_kho` | khi anh cho địa chỉ và khoá |
| Huỷ theo `khoa` khi hết giờ (tránh lần xuất mồ côi) | ngay khi anh xác nhận câu 3 |
| Lưu số tờ kho cạnh `stock_move_id` | khi anh xác nhận câu 7 |
| Gửi `hinh_thuc`, `owner_id` ở A2 và A5 | khi anh xác nhận câu 6 |
| Đổi luồng cấp dầu theo cách anh chọn | câu 5 |
| **Đã sửa ngày 30/09:** thủ kho không còn thấy giá vốn khi quét QR (B7); dòng phụ tùng lấy kho luôn mang tiền `LAK` | — |

## 12. Thử với nhau

Bên em có các bộ kiểm tự động chạy trên máy thử (bản sao DB), không đụng dữ liệu thật:

- `kiem/thu_luong_api.py` — đi trọn luồng một phiếu. Có:
  - xuất phụ tùng kho, trừ tồn, huỷ khi xoá phiếu;
  - cấp dầu theo đề nghị;
  - xe gom tới bãi, lô hàng.
- `kiem/thu_phieu_linh.py` — cấp dầu theo mã QR, cấp lệch phải có lý do, cấp hai lần bị chặn.
- `kiem/thu_kho_xem.py` — màn Xem kho theo mặt hàng, lọc giá theo vai.
- `kiem/thu_quyen_de_nghi_kho.py` — ma trận 12 vai, giá vốn kho ẩn với thủ kho và tổ sửa chữa.

Khi anh có môi trường thử:

1. Sếp đặt `kho_api` và `kho_token` trỏ sang máy thử của anh.
2. Bên em chạy các bộ trên.
3. Chỗ nào khác khuôn thì bộ kiểm báo đúng tên trường.

Liên hệ kỹ thuật bên em: [tên · điện thoại].

---

## 13. Đối chiếu với API anh gửi chiều 30/09 (lõi kho Golden SME)

### 13.1. Những gì bên em nhận được và đã đọc

| Thứ anh gửi | Bên em đọc được gì |
|---|---|
| Bản biên dịch `Backend.API.dll` (ngày 28/09) kèm `Backend.API.xml` (mô tả từng đường) | 17 nhóm controller. Liên quan tới kho: `WarehouseController` (17 đường), `StocktakingController` (21), `InventoryReportController` (3), `ItemController`, `ItemGroupController`, `UomController`, `ObjectManagementController`, `CommonController`, `POController` |
| Swagger bản dev `https://cantinbv-backend-api-dev.goldensme.com/swagger` ("Căn tin - Bệnh viện - DEVELOPMENT") | 228 đường, 111 kiểu dữ liệu. Xác thực bằng **JWT Bearer**, lấy qua `POST /api/auth/login` với thân `{Username, Password, OrgID}` |
| Ghi chú `anhtoan.txt` | *"trỏ DB chạy cho đúng với bên Lào, còn thiếu stored nào thì vào DB coi cầm sang cho Lào … để ý thử cái appsettings"* |
| `appsettings.dev.json`, `appsettings.prod.json` | có các khoá `ConnectionStrings.Master`, `ConnectionStrings.BI`, `CenterConnectionStrings`, `JWT.Secret`, `ApiKey`… Bên em **không đọc giá trị**, **không đưa lên git**, và không gửi đi đâu |

- Bên em **chưa gọi thử bản dev của anh**, vì chưa có tài khoản đăng nhập. Phần kho cùng lõi trên máy `demo-lao-api` thì bên em đã gọi thử các đường chỉ đọc ngày 30/09 — kết quả ở **mục 13.6**.
- Swagger **không mô tả khuôn trả về** (mọi `200` đều không có schema). Vì vậy dưới đây chỉ chắc phần **thân gửi đi**. Phần trả về, bên em xin anh một mẫu thật cho mỗi đường (câu hỏi 13.5).

### 13.2. Cách nối — bên em viết lớp chuyển

- API của anh là **lõi kho dùng chung**: phiếu nhập, xuất qua bảng tạm; tồn tức thời; xuất nội bộ; kiểm kho. API này không làm theo đường riêng của trang điều xe.
- Vì vậy **bên em tự viết lớp chuyển** (`services/kho_toan.py`), dịch mỗi việc ở mục 3 sang đường của anh.
- Mã nghiệp vụ bên em (`GiaoDichKho`, luật "ghi rồi bù", quyền theo vai) **giữ nguyên**, chỉ đổi lớp gọi.
- **Để chạy được, bên em cần anh:**
  1. **Máy chạy API cho bên Lào**, trỏ vào **DB của bên Lào** (theo ghi chú của anh). Việc này cần chủ dự án chốt với anh:
     - ai host, ở đâu;
     - DB nào;
     - bổ sung stored procedure còn thiếu thế nào.
  2. **Một tài khoản dịch vụ** để trang điều xe đăng nhập (`/api/auth/login`) và lấy JWT, kèm thời hạn token và cách làm mới.
  3. **Bảng mã số** ở mục 13.4.

### 13.3. Mỗi việc bên em cần ↔ đường của anh

| Việc bên em (mục 3) | Đường của anh | Bên em dùng thế nào | Còn thiếu / cần anh xác nhận |
|---|---|---|---|
| Danh mục **kho dầu, kho phụ tùng** (A4, A13; bản chép B3) | `GET /api/warehouse/GetWarehouseActive?ORG_Id=&LangId=` | map mỗi kho EPL (`fuel_places.id`, ví dụ `KHO-TB` Thà Bốc) ↔ `WarehouseId` của anh | khuôn trả về; kho dầu và kho phụ tùng là hai kho riêng hay một kho |
| Danh mục **mặt hàng** — dầu diesel, từng phụ tùng (A1, B5) | `POST /api/items/search`, `POST /api/items/find`, `GET /api/items/quick-search?ItemNo=` · đơn vị `GET /api/uom/units` | map `parts.id` ↔ `ItemId` / `ItemNo` / `UnitAutoId`. Dầu diesel là **một mặt hàng** tính bằng **lít** | mã hàng dầu diesel và đơn vị lít; bên anh giữ bản gốc danh mục phụ tùng, bên em chép theo |
| **Tồn + giá vốn bình quân** từng kho (A1, A4, A13) | `POST /api/inventory/now` thân `{OrgId, ChoiceOrgId, WhId, ItemNos, LangId}` · báo cáo kỳ `InventoryReportController.GetGeneralReport` (`WarehouseId, FromDate, ToDate, ItemId…`) | giá dòng dầu, phụ tùng lấy kho; màn Xem kho | **đường có trả giá vốn bình quân không**. Bên em cần giá vốn theo từng kho (anh Khampla chốt bình quân theo kho, mục 6) |
| **Xuất dầu theo phiếu đề nghị** (A5) | `POST /api/warehouse/CreateStockOut` thân `CreateStockInOutDirectRequest` | xem khung gửi bên dưới | **loại chứng từ / `OfSubsystem` cho "xuất dùng nội bộ" (xe nhà) và "xuất bán" (xe thuê)**. Swagger chỉ ghi 31 = nhập, 32/33 = xuất chuyển kho |
| **Xuất phụ tùng cho dòng mục V** (A2) | như trên | `RefDocumentNo` = số phiếu xuất xe + id dòng | như trên |
| **Huỷ lần xuất** (A3, A6) | `POST /api/warehouse/DeleteDocument?documentId=` | theo `DocumentId` anh trả | huỷ **phiếu đã vào sổ chính** có được không, hay phải phiếu nhập trả |
| **Chống trùng** khi thử lại (mục 1.5) | không có khoá trong contract | bên em gửi `RefDocumentNo` ổn định, trước khi thử lại thì hỏi `POST /api/warehouse/GetStockList` theo số đó | xin anh **chặn trùng theo `RefDocumentNo`** (hoặc nhận một khoá riêng) |
| Chuyển dầu giữa hai kho EPL | `GetXnbWithDetails`, `TransferXnbToNnb` (xuất nội bộ → nhập nội bộ) | màn của anh | — |
| Nhập kho (mua dầu, phụ tùng) | `CreateStockIn` (`OfSubsystem` 31, `ObjAutoId` = nhà cung cấp) · `POController.CreateAutoStockInManual` | màn của anh | nhà cung cấp dùng chung mã với bên kế toán (PUBOBJECT) |
| Kiểm kho, **kể cả mất mạng** | `StocktakingController` (Init, Upsert, SaveItems, Approve, CreateAdjustment, AcceptAdjustment; `OfflineBootstrap`, `OfflineCatalogPage`, `OfflinePushCounts` có `SyncBatchId` chống gửi trùng) | màn của anh | — (khách cần chạy được khi mất mạng; phần này anh đã có) |
| **Cấp dầu theo mã QR** (B6–B8) | không có | — | câu hỏi 13.5 (4) |
| **Hàng khách gửi ở bãi** (quặng, A7–A12) | `/api/plot/*` (lô hàng) | — | đây là hàng **của khách, ngoài bảng**, không phải tài sản EPL. Bên em đề nghị **giữ ở trang điều xe** (lô = phiếu gom), anh không phải làm |
| **Xem kho theo mặt hàng** (A13) | ghép `inventory/now` + `GetStockList` (các lần nhập, xuất gần đây) | bên em ghép, anh không phải làm đường mới | khuôn trả về của hai đường |

**Khung gửi `CreateStockOut` bên em định dùng.** Các số 0 là chỗ sẽ điền từ bảng mã 13.4.

```json
{"Header": {"DocumentId": null, "ComitToMain": true, "FiciAutoId": 0, "OfSubsystem": 0, "OrgAutoId": 0,
            "DocumentDate": "2026-09-30T08:15:00+07:00", "DocTypeAutoId": 0,
            "RefDocumentNo": "PLNL-T4-0447-09/EPL-1", "Description": "Cấp 200 lít dầu theo đề nghị PLNL-T4-0447-09/EPL-1 · xe 341",
            "ReceiveBy": "<tài xế>", "CurAutoId": 0, "CurRate": 1, "IsActive": true, "ObjAutoId": null},
 "Details": [{"WarehouseId": 0, "ItemId": 0, "ItemNo": "<mã dầu diesel>", "ItemName": "Dầu diesel", "UnitAutoId": 0,
              "InOutQty": 200, "Description": "Phiếu xuất xe T4-0447-09/EPL"}]}
```

- Xe thuê (xuất bán): `ObjAutoId` = mã chủ xe trong danh mục đối tượng của anh (PUBOBJECT).
- **Giá bán không gửi sang kho** (mục 5). Giá vốn do kho của anh tính.

### 13.4. Bảng mã số bên em cần anh cấp

Mọi đường của anh dùng **ID số trong DB của anh**. Bên em sẽ giữ một bảng đối chiếu, Sếp nhập ở màn cấu hình.

| Cần mã | Trường ở API của anh | Bên em có |
|---|---|---|
| Công ty | `FiciAutoId` ("Mã công ty — BẮT BUỘC") | EPL Lào |
| Đơn vị / chi nhánh | `OrgAutoId`, `OrgId`, `OrgID` (lúc đăng nhập) | Thà Bốc · Viêng Chăn |
| Kho | `WarehouseId` | từng kho dầu EPL (`KHO-TB`…), kho phụ tùng Thà Bốc |
| Mặt hàng, đơn vị tính | `ItemId`, `ItemNo`, `UnitAutoId` | dầu diesel (lít), từng phụ tùng |
| Loại chứng từ | `DocTypeAutoId` (lấy ở `POST /api/warehouse/GetDocType`), `OfSubsystem` | xuất dùng nội bộ · xuất bán cho chủ xe · (hệ anh tự dùng: nhập, chuyển kho) |
| Tiền tệ | `CurAutoId` (lấy ở `GET /api/common/GetAllCurrency`; mặc định của anh là 1 = VND) | LAK · USD · THB · VND · CNY — **bên Lào tính giá vốn bằng LAK**, không để mặc định VND |
| Đối tượng | `ObjAutoId` (`ObjManage/SearchObj`) | chủ xe liên kết, nhà cung cấp — nên **cùng mã** với bên kế toán anh Tune |

### 13.5. Câu hỏi thêm cho anh

1. **Chạy cho bên Lào** (ghi chú của anh):
   - DB của bên Lào là DB nào, ai giữ;
   - stored procedure nào còn thiếu — anh gửi danh sách hay bên em tự đối chiếu;
   - máy chạy API do ai host.

   Chủ dự án sẽ chốt việc này, bên em không tự trỏ DB thật.
2. **Khuôn trả về thật** của `auth/login`, `inventory/now`, `GetWarehouseActive`, `GetDocType`, `items/search`, `CreateStockOut`, `GetStockList`, `DeleteDocument`. Chỉ cần một mẫu mỗi đường, lấy ở bản dev.
3. **Xuất dùng nội bộ và xuất bán** dùng `OfSubsystem`, `DocTypeAutoId` nào? Có tự tính **giá vốn bình quân** lúc xuất và trả về không?
4. **Cấp dầu theo mã QR:** thủ kho ngoài bãi bấm cấp ở đâu?
   - (a) màn của anh, thêm ô quét mã phiếu đề nghị, rồi gọi sang bên em báo "đã cấp";
   - (b) giữ màn Cấp phát bên em, bên em gọi `CreateStockOut` của anh.

   Bên em làm được cả hai; cách (b) anh không phải làm màn mới.
5. **Chống trùng theo `RefDocumentNo`** được không?
6. **Huỷ phiếu xuất đã vào sổ chính:** `DeleteDocument` hay phiếu nhập trả?
7. Tài khoản dịch vụ và **quyền theo chi nhánh**: một tài khoản cho cả Thà Bốc và Viêng Chăn, hay mỗi nơi một tài khoản?

### 13.6. Kết quả gọi thử ngày 30/09 — phần kho trên máy `demo-lao-api` (chỉ đọc)

Bên em **chưa có tài khoản** trên bản dev của anh (`cantinbv-backend-api-dev`), nên chưa gọi được bản đó.

Nhưng máy **`demo-lao-api.goldensme.com`** (máy kế toán anh Tune, bên em đã có token) cũng **chạy phần kho Golden SME**, dưới tiền tố `/api/v1/supply-chain/`. Bên em đã gọi thử phần kho ở đó:

- **chỉ gọi đường xem, danh sách, tìm**;
- không gọi `CreateStockIn`, `CreateStockOut`, `DeleteDocument` hay đường ghi nào.

#### 13.6.1. Hai bản — cùng lõi, khác nhánh

| | Bản anh gửi (`/api/…`, 28/09) | Máy `demo-lao-api` (`/api/v1/supply-chain/…`) |
|---|---|---|
| Xuất nhập | `CreateStockIn`, `CreateStockOut`, `DeleteDocument`, `GetDocType`, `GetDocStatus`, `GetStockList`, `GetStockDocumentDetail`, `GetWarehouseActive`, `GetXnbWithDetails`, `TransferXnbToNnb`, `PrintStockOut` | có đủ |
| Tồn | `inventory/now` | có, thêm `inventory/balance-by-dimension`, `inventory/report/stock-join-general` |
| Mặt hàng | `items/search`, `items/find`, `items/quick-search`, `uom/units` | có đủ |
| Kiểm kho, kể cả mất mạng | `stocktaking/*` + `offline/bootstrap`, `catalog-page`, `push-counts`, `uom-changes` | có, **tên đường khác**: `adjustment/create`, `adjustment/accept`, `items/save`, `items/search` (bản anh: `create-adjustment`, `accept-adjustment`, `save-items`, `search-items`) |
| Chỉ bản anh có | luồng bảng tạm `InsertUpdateItemIntoTmp`, `InsertUpdateTmpItems`, `GetItemDetailTmp`, `CreateTmpOrCreateUpdateMainByTmp`, `MainToTempStock`; `GetInOutStockDetail`; `GetPlot`; `stocktaking/update-item`, `delete-item`; phần bếp căn tin | — |
| Chỉ `demo-lao-api` có | — | quản lý kho `master/list`, `master/upsert`, `master/lookups`, `master/set-active`; vị trí trong kho `location-tree-view`, `upsert-line-location`; lệnh sản xuất `GetProductionOrders`, `process-step-tree`; `search-for-stock-out` |

**Bên em nối kho vào API RIÊNG của anh** (bản anh gửi), không nối vào phần kho trên máy `demo-lao-api`. Chủ dự án đã chốt ngày 30/09.

- Phần kho trên `demo-lao-api` bên em **chỉ dùng để tham khảo**: khuôn trả về và tên loại chứng từ của lõi Golden SME. Các số ID ở 13.6.2 là **ID của máy `demo-lao-api`**. Trên máy của anh, ID có thể khác — xin anh cấp lại theo bảng 13.4.
- Máy chạy API của anh, và DB bên Lào: chủ dự án chốt với anh (13.5 (1)). Bên em không tự dựng hay trỏ DB bản nào.

#### 13.6.2. Số thật đọc được

| Cần mã (13.4) | Số thật trên `demo-lao-api` (chỉ để tham khảo) | Việc trên API của anh |
|---|---|---|
| Đơn vị | 1368 "Demo EPL" · 5 "EPL 2" · 1369 "EPL 3" (và 2 "EPL 1") — **đều quốc gia Việt Nam, tiền VND** | đơn vị EPL Lào (anh Tune tạo, hợp đồng kế toán 12.7) |
| Kho (`GetWarehouseActive?ORG_Id=`) | đơn vị 1368: 8 Kho giấy cuộn (`WGC`) · 9 Kho giấy tấm (`WGT`) · 10 Kho vật tư (`WVT`) · 11 Kho thành phẩm (`WTP`) · 12 Kho hàng hoá (`WHH`) · 13 Kho tem in (`WTI`). Đơn vị 5: 18, 19 `[Test] Kho A/B`. Đơn vị 1369: 14–17 `[Test] Kho 1–4`. Cột: `WH_AUTOID`, `WH_DEFINEID`, `WH_NAME`, `ORG_AUTOID`, `WH_ISACTIVE`… | **chưa có kho nào của EPL Lào**. Xin anh tạo: kho dầu Thà Bốc, kho dầu Viêng Chăn (và các kho dầu khác theo danh sách điểm đổ bên em), kho phụ tùng Thà Bốc |
| Mặt hàng (`items/search`) | **2.861 mặt hàng**, đều là thùng carton, giấy của nhà máy mẫu. Cột: `PIT_AUTOID`, `PIT_ITEMNO`, `PIT_NAME`, `UOM_AUTOID`, `UOM_NAME`, `CurrentStock`, `LatesPurPrice`, `UNITPRICE`, `WH_AUTOID`… | **chưa có dầu diesel** (đơn vị **lít**) và **danh mục phụ tùng xe** |
| Loại chứng từ kho (`GetDocType {OrgId, LangId}`) | 26 loại. Bên em cần: **65 "Xuất nội bộ"** (xe nhà) · **44 "Xuất kho hàng bán"** (xe thuê — xuất bán, mục 5) · 42 "Nhập kho hàng hoá" · 33 "Xuất chuyển kho" · 66 "Nhập kho nội bộ" · 39 / 40 Xuất / Nhập điều chỉnh · 64 "Xuất hủy". Cột trả về chỉ có `DOTY_AUTOID`, `DOTY_NAME`, `DOTY_ISICINPUT`, `DOTY_ISICOUTPUT` — **không có `OfSubsystem`** | xin anh xác nhận **65 và 44 đúng cho hai việc này**, và `OfSubsystem` đi kèm là số nào. Gửi `IsInput: 1` thì trả **rỗng**; gửi `IsInput: true` thì **lỗi 400** |
| Tên loại chứng từ | mã 151–154 hiện **chữ lỗi mã hoá** (kiểu "Nháº…p kho nguyÃªn…"). Đúng ra là "Nhập kho nguyên vật liệu", "Nhập kho sản xuất", "Xuất kho sản xuất", "Xuất kho nguyên vật liệu" | xin anh sửa dữ liệu tên |
| Trạng thái chứng từ (`GetDocStatus`) | 1 Tạo mới · 4 Sổ kho · 12 Ghi sổ chính · 13 Ghi sổ tạm · 14 Lỗi · 16 Đã sửa lỗi | bên em coi "đã cấp" khi phiếu ở **12 Ghi sổ chính** — anh xác nhận |
| Tiền tệ | 3 = VND, 26 = LAK | **giá vốn bên Lào tính bằng LAK** → `CurAutoId` = 26, không để mặc định |

#### 13.6.3. Tồn và giá vốn

| Đường | Kết quả |
|---|---|
| `POST /api/v1/supply-chain/inventory/now` `{OrgId, ChoiceOrgId, WhId, ItemNos: "", LangId}` | kho thử 18 (đơn vị 5) và kho 12 (đơn vị 1368): **trả rỗng**, không lỗi |
| `GET /api/v1/report/inventory/now/1368` | **lỗi 500** ("Hệ thống chưa xử lý được yêu cầu…"). Nhiều khả năng đây là thủ tục lưu còn thiếu, đúng như ghi chú của anh |
| `GET /api/v1/report/inventory/now/5` | chạy, **12 dòng**, nhưng là hàng của **đơn vị 1368** (kho 8, 9…). Tham số đường có vẻ không lọc theo đơn vị — xin anh xem lại |
| Cột của báo cáo tồn | `WH_AUTOID`, `WH_NAME`, `PIT_AUTOID`, `PIT_ITEMNO`, `PIT_NAME`, `UOM_NAME`, `BeginStock`, `InQty`, `OutQty`, `StockTake`, `Balance` — **chỉ có số lượng, không có giá** |

Bên em cần **giá vốn bình quân theo kho × mặt hàng** (mục 6), ở một trong hai chỗ:

- trong tồn tức thời; hoặc
- trả về lúc `CreateStockOut` (giá vốn của chính lần xuất đó).

Có giá đó thì dòng dầu kho, phụ tùng kho trên phiếu xuất xe và màn Xem kho mới đúng.

#### 13.6.4. Việc xin anh làm — xếp theo thứ tự cần trước

1. **Chốt máy chạy API của anh và DB bên Lào** (13.5 (1)), cùng chủ dự án.
2. **Bổ sung thủ tục lưu** còn thiếu vào DB bên Lào (đúng ghi chú của anh). Trên máy `demo-lao-api`, `report/inventory/now/{orgId}` lỗi 500 và `inventory/now` trả rỗng — xin anh kiểm hai đường này trên bản của anh.
3. **Tạo đơn vị và kho EPL Lào** (kho dầu, kho phụ tùng) trên hệ của anh.
4. **Tạo mặt hàng** dầu diesel (lít) và danh mục phụ tùng.
5. **Xác nhận loại chứng từ 65 / 44** và `OfSubsystem` đi kèm.
6. **Trả giá vốn bình quân** (13.6.3).
7. **Chặn trùng theo `RefDocumentNo`** (13.5 (5)).
8. Sửa **tên loại chứng từ 151–154**.
9. Trả lời 13.5 (4): **cấp dầu theo mã QR** ở màn nào.
