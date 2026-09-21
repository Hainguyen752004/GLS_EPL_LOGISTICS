# EPL Lào — nghiệp vụ, cơ sở dữ liệu và API

Viết cho người tiếp nhận hệ thống: lập trình viên bảo trì tiếp, và kế toán bên anh Khang cần biết lấy
dữ liệu ở đâu. Cập nhật 21/09/2026.

Ba phần: **A. Nghiệp vụ** (việc chạy thế nào ngoài đời) · **B. Cơ sở dữ liệu** (32 bảng) · **C. API**
(118 đường). Cuối cùng là phần **D. Chạy và kiểm**.

---

# A. Nghiệp vụ

## A0. Một chuyến hàng đi qua hai phiếu

Từ 21/09/2026, một chuyến quặng từ mỏ ra cảng đi qua **hai phiếu xuất xe (DO)**, nối nhau qua kho hàng
ở bãi Thà Bốc. Bãi đứng giữa như một bưu cục.

```
   MỎ (Kasi)                    BÃI THÀ BỐC                     CẢNG / KHÁCH
      │                              │                                │
      │ ── DO GOM (kind = gom) ────► │                                │
      │    cân tại mỏ                │  NHẬP KHO (PNK_HH)             │
      │    không có cước             │  lô hàng nằm bãi               │
      │                              │                                │
      │                              │ ── DO GIAO (kind = giao) ────► │
      │                              │  XUẤT KHO (PXK_HH)   cân tại cảng
      │                              │  chọn lấy từ lô nào   có cước → hoá đơn → thu tiền
```

Điểm cần nhớ:

- **Xe hai chặng có thể khác nhau.** Chặng gom xe 341 chở về, chặng giao xe 342 chở đi — bình thường.
- **Dây nối hai phiếu là lô hàng.** Mỗi dòng hàng của DO giao ghi rõ nó lấy của DO gom nào
  (`trip_goods.tu_phieu_id`). Nhìn một DO giao là biết hàng từ chuyến nào về; nhìn một DO gom là biết
  lô đó đã đi những chuyến nào.
- **Một DO gom có thể chia cho nhiều DO giao**, và một DO giao có thể gom hàng của nhiều lô.
- **Hao hụt ghi thành một dòng** trên phiếu (`trip_goods.loai = 'hao_hut'`) chứ không bắt người đọc trừ
  nhẩm: chặng gom là *cân mỏ − cân bãi*, chặng giao là *tấn xuất kho − cân nơi giao*.
- **Chỉ DO giao mới có cước và hoá đơn.** Xuất hoá đơn cho DO gom bị máy chủ từ chối.
- **Phiếu gom đã nhập kho thì dòng hàng và hai ô cân đóng lại** (mã lỗi `HANG_DA_NHAP_KHO`): sổ kho đã ghi
  theo số đó, sửa phiếu mà không sửa sổ là hai bên nói hai số. Phiếu giao đã tới vẫn sửa được cân cuối,
  sửa xong máy tính lại dòng hao hụt. Loại phiếu không đổi được khi đã có dòng hàng hay sổ kho
  (`KHONG_DOI_LOAI`).
- **Sai số sau khi đã nhập kho thì lập phiếu điều chỉnh kho**, không xoá phiếu giao để làm lại. Kế toán (KT
  Thu/Chi VC hoặc Sếp) ghi một dòng `adj` có dấu (+ tăng, − giảm) kèm lý do bắt buộc vào lô, sinh chứng từ
  `DC_HH`. Tồn lô không được âm sau điều chỉnh (`TON_AM`) — hàng đã xuất cho phiếu giao thì không thể
  "chưa từng có". Lịch sử nhập/xuất giữ nguyên, ai xem sổ cũng thấy đã sửa gì, vì sao, lúc nào.
- Vẫn cho phép **chạy thẳng mỏ → cảng** không qua kho: lập một DO giao và không chọn lô nào, nhập cân
  tay như cũ.

## A1. Sáu mục của một phiếu và chuỗi duyệt

Mỗi phiếu có sáu mục như tờ giấy của họ:

| Mục | Nội dung | Ai nhập | Ai kiểm | Ai ghi sổ | Ai chi |
|---|---|---|---|---|---|
| I | Thông tin xe | Kho Thabok | KT Thu/Chi VC | — | — |
| II | Khách hàng, vận chuyển, hàng, cân, giá | Kho Thabok | KT Thu/Chi VC | — | — |
| III | Chi phí xăng dầu | Kho Thabok | KT kho xăng dầu VC | KT kho xăng dầu VC | Thủ quỹ VC |
| IV | Chi phí đi lại | Kho Thabok | KT Chi phí VC | KT Chi phí VC | Quỹ tiền mặt Thabok |
| V | Chi phí sửa chữa | Kho Thabok | KT Chi phí VC | KT Chi phí VC | Quỹ tiền mặt Thabok |
| VI | Chi phí khác | Kho Thabok | KT Chi phí VC | KT Chi phí VC | Quỹ tiền mặt Thabok |
| — | Hoá đơn, thu tiền khách | KT Doanh thu VC | — | KT Doanh thu VC | — |

Mỗi mục đi qua chuỗi `chờ → đã nhập → đã kiểm → đã ghi sổ → đã chi`. Người nhập chỉ sửa được khi mục
còn *chờ* hoặc *đã nhập*; kiểm rồi là khoá, muốn sửa phải **trả lại**. Chỉ Sếp mở khoá được.

Luật ở `services/phan_quyen.py`, một bảng duy nhất — sửa quyền thì sửa đúng chỗ đó.

## A2. Ai thấy tiền nào

**Kho Thabok thấy mọi khoản CHI** (dầu, đi đường, sửa chữa, giá nhập kho) vì chính họ chi và họ nhập.

**Kho Thabok không thấy TIỀN BÁN**: đơn giá cước, doanh thu, hoá đơn và tiền thu khách, giá thuê xe
liên kết, khấu trừ chủ xe, lãi chuyến, mã tài khoản. Đó là biên lợi nhuận của công ty (khách trả giá 2,
thuê lại xe ngoài giá 1).

Giao diện giấu bằng lớp CSS `tien` trên thân trang `vai-<vai>`; **máy chủ cũng bỏ hẳn các khoá đó** ở
hai báo cáo của màn Tổng quan (`thay_tien_ban()` trong `services/phan_quyen.py`). Các API khác còn trả
đủ — xem mục B1 trong `CONG_VIEC_CHO_ANH_KHAMPLA_CHOT.md`.

## A3. Nhiên liệu — hai đường

1. **Đổ ở kho dầu EPL**: Bãi khai số lít và nơi đổ → in **phiếu lĩnh có mã QR** → thủ kho quét mã, cấp
   dầu, nhập số lít thật → tồn kho trừ ngay, sinh **PXK_NL**, định khoản `625/371` (xe nhà) hoặc
   `4022/371` (xe liên kết).
2. **Đổ dọc đường bên Việt Nam**: tài xế khai trên điện thoại (lít, trạm, đơn giá VND) → KT kho xăng dầu
   duyệt → thành một dòng mua ngoài ở mục III, tự quy đổi LAK theo tỷ giá ghi trên phiếu.

## A4. Tiền đi đường trả đúng lúc

| Khoản | Cách trả | Phần mềm làm |
|---|---|---|
| Chi tiêu đi VN, điện thoại | Trả ngay khi xe xuất phát | **Phiếu tạm ứng có QR**, quỹ quét mã chi; chưa nhận tiền thì chưa bấm được *Xuất phát* |
| Tiền nước, tiền chuyến | Trả theo chuyến cùng lương | **Tất toán tài xế theo tháng**: đã ứng bao nhiêu, chi thật bao nhiêu, dương công ty trả thêm, âm tài xế nộp lại |
| Shipping Lào, Việt | Nợ nhà cung cấp | Màn **Theo dõi nhà cung cấp**, trả theo đợt |
| Cao tốc | Trả qua thẻ | Ghi như khoản chi thường (chưa theo dõi số dư thẻ) |

## A5. Xe về, khoá phiếu, hoá đơn, xe liên kết

- Xe tới nơi → Bãi bấm *Xe đã tới*, nhập cân cuối, km về, ngày về. **DO gom** thì hàng vào kho ngay lúc
  này; **DO giao** thì máy ghi dòng hao hụt.
- Kế toán bấm **Khoá phiếu**: máy rà km lệch quá 10 %, hao hụt quá 1,5 %, thiếu cân, thiếu phiếu quặng,
  thiếu dòng hàng, mục có chi mà chưa kiểm. Chỉ cảnh báo, kế toán xác nhận thì vẫn khoá được.
- **Chỉ phiếu đã khoá mới xuất hoá đơn** (`1211/70`) và mới ghi thu tiền.
- **Xe liên kết**: EPL trả chủ xe = giá thuê × tấn − 2 %/phiếu − 1 USD mỗi tấn vượt 40 t − các khoản EPL
  đã ứng. Lãi = tiền khách trả − tiền thuê. Quỹ bấm *Trả chủ xe* sau khi phiếu khoá.

## A6. Sổ chứng từ

Mỗi bước sinh tiền hoặc hàng để lại **một tờ có số** cho kế toán kéo về (`GET /api/chung-tu`), số dạng
`LOAI/YYMM/000n`:

| Mã | Tờ | Sinh khi |
|---|---|---|
| `DO` | Phiếu xuất xe | Lập phiếu |
| `PNK_HH` | **Phiếu nhập kho hàng** | DO gom về tới bãi |
| `PXK_HH` | **Phiếu xuất kho hàng** | DO giao lấy hàng khỏi lô |
| `DC_HH` | **Phiếu điều chỉnh kho hàng** | Kế toán sửa tồn một lô có lý do |
| `PLNL` | Phiếu lĩnh nhiên liệu | Bãi cấp phiếu QR cho tài xế |
| `PXK_NL` / `PNK_NL` | Xuất / nhập kho nhiên liệu | Thủ kho cấp dầu · nhập dầu |
| `PXK_PT` / `PNK_PT` | Xuất / nhập kho phụ tùng | Khai sửa chữa lấy kho · nhập phụ tùng |
| `PTU` / `PC_TU` | Phiếu tạm ứng · chi tạm ứng | Bãi lập · quỹ chi |
| `PC_SC` | Chi sửa chữa, chi khác | Quỹ chi mục V, VI |
| `PC_NCC` | Chi trả nhà cung cấp | Trả theo đợt |
| `PC_CX` | Chi trả chủ xe liên kết | Quỹ bấm trả chủ xe |
| `HD` / `PT` | Hoá đơn · phiếu thu khách | KT doanh thu |
| `TT_CHI` / `TT_THU` | Tất toán tài xế | Chốt tháng |
| `PXK_BAN` / `HD_BAN` / `PT_BAN` | Bán phụ tùng, xăng dầu ra ngoài | Màn Bán hàng |

**Đẩy sang kế toán**: mỗi tờ là một `POST {api}/api/v1/epl-lao/vouchers` với `ref` = số chứng từ làm khoá chống
trùng; bên kia trả `id` thì tờ đánh đã đẩy và giữ mã đó; trả lỗi thì tờ giữ nguyên, ghi câu lỗi lên dòng để bấm lại.
Hợp đồng JSON đầy đủ gửi anh Khang ở `HOP_DONG_API_ANH_KHANG.md`; lớp đẩy ở `services/day_ke_toan.py`.

Định khoản là **gợi ý** theo quy trình của họ, không phải sổ kế toán: bên mình không ghi bút toán,
không cộng sổ. Mã tài khoản đang dùng: kho `371`, nhà cung cấp `402`, phải thu `1211`, doanh thu `70`,
chi phí `625` (xe nhà) / `614` (sửa chữa) / `4022` (xe liên kết). **Mã tiền mặt và ngân hàng chưa có** —
để trống tên, chờ bên kế toán cấp (`TIEN` trong `services/chung_tu.py`).

---

# B. Cơ sở dữ liệu

PostgreSQL, DB riêng **`epl_lao`**, khai trong `.env` (`DATABASE_URL`, không commit). Không có tầng
migration: `tao_bang()` trong `database.py` chạy `create_all` rồi **so cột model với cột thật và ALTER
TABLE ADD COLUMN** cho phần thiếu — chỉ thêm, không đổi kiểu, không xoá, nên không bao giờ mất dữ liệu.

32 bảng, nhóm theo việc:

## B1. Người dùng và danh mục

| Bảng | Giữ gì | Cột đáng chú ý |
|---|---|---|
| `users` | Tài khoản và vai | `role` (10 vai), `driver_id`, `place_id` (thủ kho gắn điểm đổ) |
| `customers` | Khách nhận quặng | `name`, `phone`, `active` |
| `customer_rates` | **Bảng giá khách × tuyến** | `price_usd`, `hire_price_usd`, `valid_from`, `goods_type` |
| `vehicles` | Đầu kéo | `truck_no`, `plate_head`, `owner_type` (EPL/joint), `trailer_id`, ba hạn giấy tờ, `odometer_km`, `next_service_km`, `fuel_norm`, `engine_cap`, `box_size`, `tyre` |
| `trailers` | Rơ-moóc (thực thể riêng) | `plate`, `trailer_type`, `capacity_t`, `status` |
| `trailer_assignments` | Lịch sử lắp/tháo | `attached_at`, `detached_at`, `reason` |
| `drivers`, `driver_licenses` | Tài xế và bằng lái | `license_no`, `expiry` |
| `routes`, `route_stops` | Tuyến và các chặng | `total_km`, `toll_lak`; mỗi chặng có `km_from_prev`, `lat`, `lng` |
| `suppliers`, `supplier_payments` | Nhà cung cấp và các đợt trả | |
| `exchange_rates` | Tỷ giá về LAK | USD, THB, VND |
| `fuel_places` | Điểm đổ dầu | `owner_type` (epl = kho mình, ngoài = mua) |

## B2. Phiếu xuất xe (DO) — trung tâm của hệ

| Bảng | Giữ gì |
|---|---|
| `trips` | Một phiếu. **`kind`** = `gom`/`giao`; số phiếu, ngày, xe và tài xế (chép giá trị vào phiếu, không chỉ khoá ngoại), khách, tuyến, cân đầu/cuối, giá cước, phần xe liên kết, tỷ giá khoá trên phiếu, `locked`, `owner_paid` |
| `trip_goods` | **Dòng hàng**: `loai` = `hang`/`hao_hut`, `goods_name`, `qty_t`, **`tu_phieu_id`** = lô lấy từ DO gom nào |
| `goods_moves` | **Sổ kho hàng ở bãi**: `kind` = `in`/`out`/`adj` (điều chỉnh, `qty_t` có dấu), `qty_t`, `lo_trip_id` (lô = DO gom), `trip_id` (phiếu sinh ra dòng này), `note` (lý do điều chỉnh) |
| `trip_expenses` | Dòng chi của bốn mục III–VI: `section`, `item_key`, `qty`, `unit_price`, `currency`, `source` (kho/mua), `acct_code`, `paid_by_epl`, `stock_move_id` |
| `trip_sections` | Trạng thái duyệt từng mục I–VI |
| `trip_logs` | Nhật ký thao tác trên phiếu |
| `trip_events` | Diễn biến trên đường: tới điểm, sự cố, sửa xe, đổ dầu dọc đường (có `status` chờ duyệt) |
| `trip_attachments` | Tệp đính kèm (phiếu quặng), tệp nằm trên đĩa `backend/tep`, bảng chỉ giữ tên |
| `vehicle_positions` | Vệt GPS do app tài xế gửi |

**Tồn kho hàng không có bảng riêng**: luôn cộng dồn từ `goods_moves`. Tồn của một lô = tấn nhập của lô
trừ tấn các DO giao đã lấy (`services/kho_hang.ton_lo`).

## B3. Kho, quỹ, chứng từ

| Bảng | Giữ gì |
|---|---|
| `fuel_moves` | Sổ kho nhiên liệu (nhập/xuất), tồn cộng dồn |
| `parts`, `part_moves` | Kho phụ tùng và sổ nhập xuất |
| `vouchers` | Phiếu lĩnh nhiên liệu và phiếu tạm ứng, có `token` cho mã QR, `status` chờ/đã cấp/huỷ |
| `driver_settlements` | Tất toán tài xế theo tháng |
| `chung_tu` | **Sổ chứng từ**: `loai`, `so`, `ngay`, `trip_id`, `tien_lak`, hai vế `no`/`co` gợi ý, `da_day`, `ma_ben_ke_toan` (mã phiếu bên anh Khang trả về), `loi_day` và `lan_thu` (đẩy hỏng vì sao, mấy lần), `payload` JSON chi tiết |
| `cau_hinh` | Cấu hình đặt trong màn hình: `ke_toan_api`, `ke_toan_token`; không có thì rơi về biến môi trường `EPL_<KHOA>` |
| `sales`, `sale_lines` | Bán phụ tùng, xăng dầu ra ngoài |

---

# C. API

112 đường, tất cả dưới `/api`, cùng cổng với giao diện. Xác thực: `POST /api/dang-nhap` trả token,
gửi lại ở `Authorization: Bearer <token>`. Vai nào gọi được gì ghi ngay dưới đây.

## C1. Đăng nhập và tài khoản — `routes/dang_nhap.py`

| Đường | Việc |
|---|---|
| `POST /api/dang-nhap` | Đăng nhập, trả token và thông tin người dùng |
| `GET /api/toi` | Người đang đăng nhập (khôi phục phiên) |
| `GET /api/tai-khoan-mau` | Danh sách tài khoản demo cho màn đăng nhập |
| `GET POST /api/users`, `PUT /api/users/{uid}` | Quản lý tài khoản (Sếp) |

## C2. Phiếu xuất xe — `routes/phieu.py`

| Đường | Việc |
|---|---|
| `GET /api/trips` | Danh sách phiếu (lọc `q`, `thang`…) |
| `GET /api/trips/{id}` | Một phiếu đầy đủ: dòng chi, **dòng hàng**, mục, nhật ký, diễn biến, chặng tuyến |
| `GET /api/trips-so-moi` | Cấp số phiếu kế tiếp |
| `POST /api/trips` | Lập phiếu. Nhận `kind` (`gom`/`giao`), `expenses[]`, **`goods[]`**. Chỉ Bãi và Sếp |
| `PUT /api/trips/{id}` | Sửa phiếu; chỉ ghi được ô của mục còn mở. Ô tiền của mục II do **người kiểm** mục đó sửa |
| `DELETE /api/trips/{id}` | Xoá phiếu; chặn nếu đã có mục được kiểm, đã xuất kho, hoặc **lô đã có người lấy hàng** |
| `POST /api/trips/{id}/sections/{muc}/{hanh_dong}` | Chuyển bước một mục: `send`, `verify`, `return`, `book`, `pay`, `unlock` |
| `POST /api/trips/{id}/transport-status` | Xuất phát / tới nơi. Tới nơi: DO gom **nhập kho**, DO giao **ghi hao hụt** |
| `POST /api/trips/{id}/khoa`, `/mo-khoa`, `GET /kiem-lai` | Khoá phiếu sau khi xe về; Sếp mở khoá |
| `POST /api/trips/{id}/invoice` | Xuất hoá đơn. **Từ chối nếu là DO gom** |
| `POST /api/trips/{id}/finance-status` | Ghi thu tiền khách |
| `POST /api/trips/{id}/tra-chu-xe` | Quỹ trả chủ xe liên kết → `PC_CX` |
| `GET POST DELETE /api/trips/{id}/tep`, `/api/tep/{aid}` | Tệp đính kèm (phiếu quặng) |
| `POST /api/trips/{id}/events`, `/bao-hong`, `/bao-nhien-lieu`, `/events/{eid}/duyet` | Diễn biến, báo hỏng, khai đổ dầu, duyệt |
| `GET /api/trips/{id}/phieu-chi`, `/phieu-thu` | Dữ liệu in phiếu chi, phiếu thu |
| `GET /api/khoan-muc` | Danh mục khoản chi và bảng định khoản mặc định |

## C3. Kho hàng ở bãi — `routes/kho_hang.py`

| Đường | Việc |
|---|---|
| `GET /api/kho-hang` | Tồn theo lô + sổ nhập xuất + tổng tồn |
| `GET /api/kho-hang/lo?tru_phieu=` | Các lô còn hàng, để DO giao chọn lấy từ đâu. `tru_phieu` = phiếu đang sửa, để nó không tự trừ mình |
| `POST /api/kho-hang/dieu-chinh` | Điều chỉnh tồn một lô `{lo_trip_id, qty_t (có dấu), ly_do}`. Chỉ KT Thu/Chi VC và Sếp |

## C4. Kho nhiên liệu, phụ tùng, phiếu lĩnh — `routes/kho.py`, `routes/phieu_linh.py`

| Đường | Việc |
|---|---|
| `GET POST DELETE /api/fuel-moves` | Sổ kho nhiên liệu |
| `GET POST PUT /api/parts`, `/api/parts/{id}/moves` | Kho phụ tùng |
| `GET POST /api/fuel-places`, `PUT DELETE /api/fuel-places/{id}` | Điểm đổ nhiên liệu |
| `POST GET /api/trips/{id}/vouchers`, `GET /api/vouchers` | Phiếu lĩnh và phiếu tạm ứng |
| `GET /api/vouchers/{id}/qr.png`, `GET /api/vouchers/tra-cuu/{token}` | Mã QR và tra cứu khi thủ kho quét |
| `POST /api/vouchers/{id}/cap`, `/huy` | Thủ kho cấp dầu · quỹ chi tiền · huỷ phiếu |

## C5. Danh mục — `routes/danh_muc.py`, `routes/tuyen.py`

| Đường | Việc |
|---|---|
| `GET POST PUT /api/customers` | Khách hàng |
| `GET POST /api/customers/{id}/bang-gia`, `PUT DELETE /api/bang-gia/{id}` | **Bảng giá khách × tuyến**. Chỉ KT Thu/Chi VC và Sếp sửa; Bãi không xem được |
| `GET /api/bang-gia/tra?customer_id=&route_id=` | Hỏi giá hợp đồng — màn phiếu dùng để tự điền |
| `GET POST PUT /api/vehicles`, `GET /api/vehicles/{id}` | Xe đầu kéo, chi tiết kèm lịch sử rơ-moóc, chi phí sửa chữa, phiếu gần đây |
| `GET /api/vehicles/{id}/lich?tuan=` | **Lịch xe theo tuần** dựng từ phiếu và dòng sửa chữa |
| `POST /api/vehicles/{id}/trailer` | Lắp rơ-moóc; `trailer_id` rỗng là tháo. Máy chủ tự tháo khỏi xe cũ và ghi lịch sử |
| `GET POST PUT /api/trailers`, `GET /api/trailers/{id}` | Rơ-moóc, chi tiết kèm lịch sử lắp |
| `GET POST PUT /api/drivers`, `POST /api/drivers/{id}/licenses` | Tài xế và bằng lái |
| `GET PUT /api/rates` | Tỷ giá |
| `GET POST PUT /api/routes` | Tuyến đường và các chặng |

## C6. Theo dõi, báo cáo, chứng từ

| Đường | Việc |
|---|---|
| `GET /api/theo-doi`, `/api/theo-doi/su-co` | Trung tâm điều hành: dải ô số, danh sách chuyến, sổ sự cố |
| `GET /api/bao-cao/tong-quan?thang=` | Bốn con số, tiến trình, cơ cấu chi, việc cần xử lý |
| `GET /api/bao-cao/xu-huong?thang=` | Sáu tháng, theo ngày, hao hụt, hiệu suất xe, vận hành, xem nhanh, dòng thời gian |
| `GET /api/bao-cao/theo-doi`, `/xe-lien-ket`, `/tien-tai-xe` | Ba bảng báo cáo trong Excel của họ |
| `GET /api/dem-viec` | Số việc đang chờ của từng màn, theo vai đang đăng nhập |
| `GET /api/chung-tu`, `/loai`, `/{id}`, `POST /{id}/da-day` | **Sổ chứng từ** cho bên kế toán kéo về hoặc đánh dấu tay |
| `POST /api/chung-tu/day`, `POST /api/chung-tu/{id}/day` | **Đẩy chứng từ sang kế toán anh Khang** (hết tờ chưa đẩy · một tờ). KT Thu/Chi VC và Sếp. Chưa cấu hình → `CHUA_CAU_HINH`; bên kia hỏng → `DAY_HONG`, tờ giữ nguyên kèm câu lỗi |
| `GET /api/ke-toan/trang-thai` | Đã nối chưa, bao nhiêu tờ đã/chưa/lỗi, lần đẩy gần nhất |
| `GET PUT /api/ke-toan/cau-hinh` | Sếp đặt địa chỉ API và token kế toán ngay trong màn hình, không cần khởi động lại; token không trả về trình duyệt |
| `GET /api/acc-codes` | Danh mục mã tài khoản (gọi API bên anh Khang, có danh mục dự phòng) |
| `GET POST DELETE /api/tat-toan` | Tất toán tài xế theo tháng |
| `GET POST /api/suppliers`, `/api/suppliers/{id}/payments` | Nhà cung cấp và các đợt trả |
| `GET POST DELETE /api/ban-hang`, `POST /api/ban-hang/{id}/thu` | Bán phụ tùng, xăng dầu ra ngoài |
| `POST /api/trips/{id}/vi-tri`, `GET /api/trips/{id}/vet` | GPS: app tài xế gửi vị trí, màn theo dõi lấy vệt |
| `GET /api/quy-trinh` | Sơ đồ quy trình và ma trận vai × mục (màn Quy trình đọc từ đây) |

## C7. Quy ước lỗi

Mọi lỗi trả JSON `{"detail": {"ma": "MA_LOI", "loi": "câu tiếng Việt cho người dùng"}}`.

| Mã | Nghĩa |
|---|---|
| `KHONG_CO_QUYEN` (403) | Vai này không được làm việc đó |
| `MUC_DA_KHOA` (409) | Mục đã kiểm, phải trả lại mới sửa |
| `SAI_BUOC` (409) | Chuyển bước không đúng thứ tự |
| `DA_KHOA` (409) | Phiếu đã khoá |
| `KHONG_DU_HANG` (409) | Lấy quá tồn của lô |
| `LO_DA_XUAT` (409) | Xoá DO gom mà hàng đã có người lấy |
| `HANG_DA_NHAP_KHO` (409) | Sửa dòng hàng hoặc cân của DO gom đã nhập kho |
| `KHONG_DOI_LOAI` (409) | Đổi loại gom/giao khi phiếu đã có dòng hàng hay sổ kho |
| `TON_AM` (409) | Điều chỉnh giảm quá tồn của lô |
| `THIEU_LY_DO` (422) | Điều chỉnh kho không ghi lý do |
| `PHIEU_GOM` (409) | Xuất hoá đơn cho phiếu gom |
| `THANG_SAI`, `TUAN_SAI`, `SO_SAI`… (422) | Dữ liệu gửi lên sai dạng |

---

# D. Chạy và kiểm

```
python backend\app\seed.py                       # dựng bảng + gieo dữ liệu mẫu (có sẵn một cặp DO gom/giao)
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8010 --no-access-log
```

Chín bộ kiểm, chạy khi máy chủ đang bật:

| Lệnh | Kiểm gì |
|---|---|
| `python kiem\test_tinh_toan.py` | Phép tính phiếu và phân quyền (không cần máy chủ) |
| `python kiem\thu_hai_do.py` | **Luồng hai DO**: gom → nhập kho → giao lấy lô → xuất kho → hao hụt, và ba chỗ phải bị từ chối |
| `python kiem\thu_luong_api.py` | Trọn luồng: lập phiếu → kiểm → ghi sổ → chi → hoá đơn → thu tiền |
| `python kiem\thu_phieu_linh.py` | Phiếu lĩnh QR, thủ kho cấp dầu, khai đổ dọc đường, tất toán |
| `python kiem\thu_ban_hang.py` | Bán phụ tùng, xăng dầu ra ngoài |
| `python kiem\thu_vi_tri.py` | GPS: ai được gửi, lọc điểm dày, GPS cũ |
| `python kiem\thu_day_ke_toan.py` | **Đẩy chứng từ sang kế toán** với máy nhận giả đóng vai API anh Khang: cấu hình, gói tin, bên kia hỏng, 409, đẩy hết, không gửi trùng |
| `node kiem\thu_giao_dien.js` | Toàn giao diện trên jsdom, nối máy chủ thật |
| `node kiem\thu_ngoai_tuyen.js` | Màn Cấp phát khi mất mạng |
| `node kiem\ra_vai.js` · `ra_tong_quan.js` · `ra_xe.js` | Báo cáo rà từng vai và từng màn (không phải đạt/hỏng) |

Từ điển ba thứ tiếng sinh tự động: sửa `tools/sinh_ngon_ngu.py` rồi chạy nó, **đừng sửa tay**
`frontend/js/ngon_ngu.js`.
