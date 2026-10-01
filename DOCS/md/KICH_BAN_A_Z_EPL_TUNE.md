# Kịch bản thử A → Z — trang điều xe EPL Lào và hệ kế toán QLSX (anh Tune)

Bản ngày **01/10/2026**. Viết cho anh (chủ dự án) và anh Tune, để hai bên cùng thử một chuyến hàng **từ lúc lập phiếu tới lúc xe về, tiền xong**, trên hai hệ:

- **trang điều xe EPL Lào** (bên em, `EPL_LAO_REAL`) — gọi tắt **điều xe**;
- **hệ kế toán QLSX của anh Tune** (API `GLS-QLSX-APIs`, WEB `GLS-QLSX-Web`) — gọi tắt **QLSX**.

**Em đã đi thật một lượt** đúng kịch bản này ngày 01/10 trên máy thử (chuyến **THU-KBAZ**: phiếu gom `THU-KBAZ-G1/EPL` + phiếu giao `THU-KBAZ-T1/EPL`). Mỗi bước có dòng **Đã thử 01/10** ghi số chứng từ thật đã sinh ở hai bên, để anh Tune mở đúng tờ mà xem. Chữ nút trong tài liệu chép từ từ điển giao diện `frontend/js/ngon_ngu.js` và mã từng màn (bản tiếng Việt), không viết theo trí nhớ.

**Cách đọc mỗi bước:**

- **Ai** — vai và tài khoản đăng nhập (mật khẩu demo mọi tài khoản trang điều xe: `1234`).
- **Trang · Màn** — trang nào, menu nào → màn nào.
- **Thao tác** — bấm nút nào (chữ **đậm** đúng như trên nút), điền ô nào.
- **Máy tự làm** — máy làm gì, gọi API nào sang bên kia.
- **Máy chặn** — khi nào bị chặn, câu báo là gì.
- **Tờ sinh ra** — bên điều xe sinh tờ gì; bên QLSX sinh chứng từ gì.
- **QLSX xem ở đâu** — màn nào bên anh Tune, lọc gì, thấy số nào.
- **Ai làm tiếp.**
- Ô ☐ ở đầu mỗi bước để đánh dấu đã thử.

---

## 0. Chuẩn bị

### 0.1. Máy nào chạy gì

| Thành phần | Lúc thử ở máy | Sau khi triển khai | Ghi chú |
|---|---|---|---|
| Trang điều xe (máy thử) | `http://127.0.0.1:8011` | link thật của trang điều xe | DB **bản sao** — thử thoải mái. Không thử trên máy thật 8020 |
| Kho tạm `EPL_KETOAN` (máy thử) | `http://127.0.0.1:8031` | link kho tạm thật (8030) | từ 01/10 chỉ còn **kho**: Cấp phát dầu, Kho hàng (lô bãi). Không còn phần tiền |
| API QLSX | `http://127.0.0.1:5090` (`Env=laos`) | `https://demo-lao-api.goldensme.com` | DB demo Lào của anh Tune — **ghi qua đây là ghi thật vào DB demo** |
| WEB QLSX | `https://localhost:5014` (`Env=laoslocal` → 5090) | WEB host của anh Tune | anh Tune đăng nhập bằng tài khoản của anh |

- Trang điều xe 8011 đặt `QLSX_BASE_URL` = 5090; API 5090 đặt `LogisticsSource:BaseUrl` = `http://127.0.0.1:8011/api/` kèm khoá bàn giao. Hai đầu đã nối sẵn.
- **Triển khai xong chỉ đổi link**, không đổi kịch bản: bảng đổi link ở `HUONG_DAN_TRIEN_KHAI_ANH_TUNE` mục 7 và tài liệu của anh Tune `PHIEU-THU-CHI-DEMOLAO-TONG-HOP.md` mục 16.2.
- Em không có mật khẩu WEB QLSX, nên bước "bên anh Tune" trong lượt thử 01/10 em làm **qua API 5090** bằng đúng lời gọi WEB gửi (ghi rõ ở từng bước). Anh Tune thử lại trên WEB theo cột "QLSX xem ở đâu".

### 0.2. Tài khoản

Trang điều xe (mật khẩu `1234`). Màn đăng nhập có danh sách tài khoản, bấm tên là điền sẵn.

| Tên đăng nhập | Vai (chữ trên màn) | Việc trong kịch bản |
|---|---|---|
| `thabok` | Admin Thà Bốc | lập phiếu gom / giao, khai dầu, tiền đi đường, in hai tờ đề nghị, gửi kiểm, báo xe tới, nhập cân |
| `ketoan` | KT Thu/Chi Viêng Chăn | kiểm mục I – II, nhập số phiếu quặng, khoá phiếu, **Tạo SO bên kế toán**, lập đề nghị trả chủ xe |
| `ketoancp` | KT Chi phí VC | nhập giá, kiểm, ghi sổ mục IV – VI, chốt tất toán tài xế, lập đề nghị trả nhà cung cấp |
| `khonl` | KT kho xăng dầu VC | kiểm, ghi sổ mục III, nhập giá bán dầu cho chủ xe, duyệt khai đổ dầu dọc đường |
| `khotb` | Thủ kho nhiên liệu (một kho) — kho dầu Thà Bốc | cấp dầu theo phiếu đề nghị ở **kho tạm** |
| `totsua` | Tổ sửa chữa Thà Bốc | duyệt báo hỏng → mục V |
| `quytb` | Quỹ tiền mặt Thà Bốc | bấm **Cập nhật** xem bên QLSX đã chi chưa (không chi tiền trên trang điều xe nữa) |
| `quyvc` | Thủ quỹ VC | **Xác nhận đã chi** mục III (chỉ đổi trạng thái) |
| `tx02` · `tx03` | Tài xế (chỉ phiếu của mình) | màn **Phiếu của tôi**: xuất phát, báo cân, khai dầu, báo hỏng, ký nhận, báo về |
| `admin` | Sếp (xem tất cả) | xem mọi màn, mở khoá |

Bên QLSX: tài khoản WEB của anh Tune. Trang điều xe gọi API bằng token tài khoản `tune` (UserID 846) — người tạo phiếu bên anh hiện là `[dev01] Tune`.

**Mở nhiều người cùng lúc:** mỗi người một tab, lúc đăng nhập **bỏ tick ô Ghi nhớ đăng nhập** (có tick thì mọi tab chạy theo tài khoản đăng nhập sau cùng). Đổi người: bấm tên ở góc dưới thanh bên → **Đổi tài khoản**. Tab này bấm xong, tab kia bấm **F5** mới thấy.

### 0.3. Dữ liệu dùng trong kịch bản

| Loại | Dùng | Có sẵn trên máy thử |
|---|---|---|
| Khách | ຄຳຕຸ້ຍ — mã bên kế toán `EPLKH-0834a9e9606b` (ObjId 1608 bên QLSX), hợp đồng `HDVC-2026-001` | có |
| Bảng giá khách × tuyến | gom ກາສີ → ທ່າບົກ 12,5 USD/t · giao ທ່າບົກ → ທ່າເຮືອກະລໍ 30,5 USD/t (thuê xe 30 USD/t) | có |
| Tuyến | ກາສີ → ທ່າບົກ 145 + 145 km · ທ່າບົກ → ທ່າເຮືອກະລໍ 360 + 360 km, phí cao tốc 3.667.000 LAK | có |
| Xe nhà | **343** (công-tơ-mét 61.200) | có |
| Xe thuê ngoài | **ຮ່ວມ-07** của chủ xe **ທ້າວ ຄຳຫລ້າ** (phí 2 %/phiếu, gộp cuối tháng), hợp đồng thuê `HDTX-2026-001` | có |
| Tài xế | `tx02` ທ້າວ ບຸນມີ (DRV-02) chạy gom · `tx03` ທ້າວ ສົມພອນ chạy giao | có |
| Kho dầu | ສາງນໍ້າມັນ ທ່າບົກ (Kho dầu Thà Bốc) — thủ kho `khotb` | có |
| Nhà cung cấp | ຊີບປີງ ລາວ (ສາງພາສີ) — phí chipping Lào, trả theo đợt | có |
| Tỷ giá | 1 USD = 22.000 LAK (máy khoá vào phiếu lúc lập) | có |

**Số phiếu:** ô **Số phiếu** máy gợi ý `G4-xxxx-MM/EPL` / `T4-xxxx-MM/EPL`. Khi thử, gõ đè một số dễ lọc (ví dụ `THU-<tên>-G1/EPL`): số phiếu đi vào số tham chiếu và diễn giải mọi chứng từ bên QLSX, anh Tune tìm theo đó.

---

## 1. Bức tranh một chuyến

Một chuyến hàng tách **hai DO**: phiếu **Gom** (mỏ → bãi, xe nhà) và phiếu **Giao** (bãi → cảng, xe thuê ngoài). Tạm ứng và xuất dầu đi theo **loại xe** của phiếu.

| # | Việc | Ai | Bên điều xe | Bên QLSX |
|---|---|---|---|---|
| 1 | Danh mục | `ketoan` · `admin` | khách, tuyến, xe, tài xế, tỷ giá, bảng giá | đối tượng `EPLKH-` · `EPLCX-` · `EPLNCC-` · `EPLTX-` (tự tạo lần gửi đầu) |
| 2 – 3 | Lập phiếu gom, in hai tờ đề nghị | `thabok` | DO · PLNL · PTU | — |
| 4 – 6 | Kiểm mục I, III, IV; ghi sổ IV | `ketoan` · `khonl` · `ketoancp` | — | **CMP 59 "Chi trước"** chờ chi |
| 7 | Cấp dầu | `khotb` (kho tạm) | PLNL đã cấp · PXK_NL (kho) | — |
| 8 | Thủ quỹ chi tạm ứng | thủ quỹ **bên QLSX** | mục IV Đã chi · PTU Đã cấp | CMP 59 ghi sổ |
| 9 – 12 | Xuất phát, cân mỏ, đổ dầu dọc đường, báo hỏng, mục II | tài xế · duyệt · kế toán | dòng mục III mua · mục V | **CMP 60 "Chi khác"** (mục V) |
| 13 – 14 | Xe gom về bãi, khoá | `thabok` · `ketoan` | lô kho bãi · PDT | — |
| 15 – 19 | Phiếu giao xe thuê: kiểm, cấp dầu xuất bán, tạm ứng chủ xe, POD, khoá | như trên | DO · PLNL · PTU · POD · PDT · bút toán chờ | **CMP 59** đứng tên chủ xe |
| 20 | Tạo SO | `ketoan` | đề nghị thu Đã tạo SO | **SO + công nợ khách** |
| 21 | Thu tiền khách | kế toán **bên QLSX** | đọc lại: Đã thu đủ | phiếu **thu nợ TKN** → **CMR 17** |
| 22 | Tất toán tài xế | `ketoancp` · thủ quỹ QLSX | bản chốt · bút toán chờ QT_TU 625/1601 | **CMP 60 TT_CHI** hoặc **CMR 17 TT_THU** |
| 23 | Trả chủ xe | `ketoan` · thủ quỹ QLSX | phiếu Đã trả chủ xe | **CMP 60** Nợ 4022 |
| 24 | Trả nhà cung cấp | `ketoancp` · thủ quỹ QLSX | công nợ NCC giảm | **CMP 60** Nợ 4021 |
| 25 | Bàn giao DO | QLSX đọc | B1/B2 | modal **Vụ việc** thấy DO |
| 26 | Bút toán không qua tiền | — | màn **Bút toán chờ gửi** | (sau khi bật) chứng từ **Tổng hợp DOTY 12**, ghi sổ tạm ST 13 |
| 27 | Đóng chuyến | mọi vai | mọi tờ xong | mọi phiếu ghi sổ |

---

## 2. Kịch bản từng bước

### Phần A — Danh mục

### Bước 1 ☐ Danh mục đủ trước khi chạy

- **Ai:** `ketoan` (khách, mã bên kế toán, tỷ giá, hợp đồng, bảng giá); `admin` (xe, tài xế, tuyến, chủ xe).
- **Trang · Màn:** điều xe → nhóm **DANH MỤC**: **Khách hàng**, **Xe**, **Tài xế**, **Tỷ giá**, **Tuyến đường**; nhóm **MÔ-ĐUN VẬN TẢI**: **Xe liên kết** (chủ xe), **Nhà cung cấp**.

**Thao tác:**

1) **Khách hàng** → bấm khách → **Sửa** → ô **Mã khách (bên kế toán)**: để trống cũng được (lúc tạo SO máy tự tạo `EPLKH-<mã khách>`). Gõ tay thì: mở đầu bằng chữ Latinh hoặc số, chỉ chữ, số, `_ - .`, tối đa 37 ký tự → **Lưu thay đổi**.
2) Khách → tab **Hợp đồng**: có một hợp đồng còn hạn (phiếu tự điền số hợp đồng). Tab **Bảng giá**: có giá cho đúng khách × tuyến × loại hàng.
3) **Xe**: xe nhà loại **Xe công ty (EPL)**; xe thuê ngoài gắn **Chủ xe**. **Xe liên kết** → chủ xe: phí %/phiếu, tải cho phép, cách trả, **Hợp đồng** thuê xe còn hạn.
4) **Tài xế**: bằng lái còn hạn (người hết hạn bị chặn ở điều phối).
5) **Tỷ giá**: kiểm 1 USD = 22.000 LAK (hoặc số thật) → **Lưu tỷ giá mới** nếu đổi. Phiếu lập sau đó khoá đúng tỷ giá này.

- **Máy tự làm:** đối tượng bên QLSX tạo lúc gửi lần đầu: khách khi Tạo SO (`POST /api/v1/master-data/customers/upsert`), tài xế khi gửi phiếu chi tạm ứng xe nhà (`staff/upsert`), chủ xe khi gửi phiếu chi xe thuê (`suppliers/upsert`), nhà cung cấp khi lập đề nghị trả (`suppliers/upsert`). Tìm theo mã trước, có rồi thì dùng lại.
- **Máy chặn:** mã khách sai luật → không lưu được; Bãi mở form khách thì ô mã khoá lại.
- **Tờ sinh ra:** không.
- **QLSX xem ở đâu:** danh mục khách hàng / nhà cung cấp / nhân viên, tìm mã `EPLKH-…`, `EPLCX-…`, `EPLNCC-…`, `EPLTX-…` (chi nhánh 1368).
- **Đã thử 01/10:** dữ liệu ở 0.3 có sẵn, không sửa gì. Tỷ giá USD 22.000.
- **Ai làm tiếp:** `thabok` lập phiếu gom.

### Phần B — Chặng GOM (mỏ → bãi, xe nhà)

### Bước 2 ☐ Bãi lập phiếu GOM — mục I, II

- **Ai:** `thabok` (Admin Thà Bốc).
- **Trang · Màn:** điều xe → **Phiếu xuất xe** (hoặc **Tổng quan** → **Tạo phiếu xuất xe**).

**Thao tác:**

1) Bấm **+ Phiếu mới**. Dưới đầu tờ có hai thẻ lớn: bấm **Gom · Gom (mỏ → bãi)**.
2) Ô **Số phiếu** (góc phải tờ): để số máy gợi ý, hoặc gõ số dễ lọc.
3) Mục **I · Thông tin xe vận chuyển**: **Số xe** 343 (biển số, hãng xe tự điền; **Lúc đi** tự điền theo công-tơ-mét); **Tài xế** ທ້າວ ບຸນມີ; **Ngày lập phiếu**, **Ngày xe đi**.
4) Mục **II · Thông tin vận chuyển & doanh thu**: **Chọn tuyến** ກາສີ → ທ່າບົກ; **Khách hàng** ຄຳຕຸ້ຍ; **Loại hàng** Quặng sắt. Ô **Cân tại mỏ (t)** để trống (xe chưa đi). Ô **Hợp đồng vận chuyển** ghi *Lưu phiếu rồi số hợp đồng còn hạn tự điền*.
5) Bấm **Lưu** (nút xanh góc trên phải). Máy báo **Đã lưu**.

- **Máy tự làm:** đơn giá cước theo bảng giá khách × tuyến (Bãi không thấy); tỷ giá khoá vào phiếu; tự điền **HDVC-2026-001**; sinh tờ **DO** ở sổ chứng từ bên điều xe; xe và tài xế thành *Đang chạy*.
- **Máy chặn:** lưu phiếu **trắng** (không chọn xe) → *Chọn xe trước khi lưu phiếu xuất xe.*; có xe mà không tài xế → *Chọn tài xế trước khi lưu phiếu xuất xe.* — áp cho mọi vai, kể cả Sếp. Bãi không nhập được giá cước, số phiếu quặng, ngày về, km về, cân cuối.
- **Tờ sinh ra:** điều xe: **DO** (phiếu xuất xe). QLSX: chưa có gì.
- **QLSX xem ở đâu:** chưa có (DO chỉ hiện bên QLSX khi đã về và đã khoá — bước 25).
- **Đã thử 01/10:** phiếu trắng → 422 `THIEU_XE`; thiếu tài xế → 422 `THIEU_TAI_XE`. Lập `THU-KBAZ-G1/EPL` (xe 343, ທ້າວ ບຸນມີ), hợp đồng tự điền `HDVC-2026-001`.
- **Ai làm tiếp:** chính `thabok` làm bước 3.

### Bước 3 ☐ Bãi khai dầu, tiền đi đường; in hai tờ đề nghị; gửi kiểm

- **Ai:** `thabok`.
- **Trang · Màn:** điều xe → **Phiếu xuất xe** → phiếu vừa lập; danh sách mục ở cột bên phải.

**Thao tác:**

1) Mục **III · Chi phí nhiên liệu** → **Thêm dòng**: **Lít** 120, **Nơi đổ** chọn trong nhóm **Kho của EPL (lĩnh)** → ສາງນໍ້າມັນ ທ່າບົກ.
2) Mục **IV · Chi phí đi đường** → **Thêm dòng** từng khoản, **SL** 1: tiền ăn, điện thoại (ô cách trả máy chọn sẵn **Chi ngay khi xe đi**), tiền nước, tiền chuyến (máy chọn sẵn **Trả theo chuyến cùng lương**). Bãi không thấy cột đơn giá, thành tiền.
3) Bấm **Lưu**.
4) Cột bên phải, khối **Phiếu đề nghị**: bấm **Phiếu đề nghị xuất kho nhiên liệu** (mỗi kho một tờ có mã QR) và **Phiếu đề nghị tạm ứng** (tờ có mã QR). Máy mở màn in; bấm **In**, đưa tài xế.
5) Ở đầu mục **I**, **III**, **IV** bấm **Gửi kiểm tra**. Mục **II** của phiếu gom gửi sau, khi có cân tại mỏ (bước 12).

- **Máy tự làm:** dòng dầu kho mang giá bình quân của kho đó; phiếu **xe nhà** → đầu mục III ghi *Xuất nội bộ — xe công ty (EPL)*, mục IV *Tạm ứng nội bộ*. Tiền tạm ứng = các dòng **Chi ngay khi xe đi** (mục IV, VI) + dầu mua dọc đường trả tiền mặt; không gồm khoản cùng lương, nợ nhà cung cấp, trừ thẻ, dầu kho.
- **Máy chặn:** **Gửi kiểm tra** chỉ hiện khi phiếu đã lưu; mục trống → *Mục … chưa có dòng chi nào để gửi kiểm.*
- **Tờ sinh ra:** điều xe: **PLNL-…-1** (đề nghị xuất kho nhiên liệu), **PTU-…** (đề nghị tạm ứng). QLSX: chưa có.
- **QLSX xem ở đâu:** chưa có.
- **Đã thử 01/10:** `PLNL-THU-KBAZ-G1/EPL-1` 120 lít kho Thà Bốc; `PTU-THU-KBAZ-G1/EPL`. Gửi kiểm I, III, IV.
- **Ai làm tiếp:** ba kế toán làm song song (bước 4 – 6); thủ kho cấp dầu (bước 7).

### Bước 4 ☐ KT Thu/Chi kiểm mục I

- **Ai:** `ketoan`.
- **Trang · Màn:** điều xe → **Phiếu xuất xe** → chọn phiếu ở ô **Số phiếu** (hoặc từ **Tổng quan** → ô **Việc của tôi**). Màn tự mở đúng mục của vai.

**Thao tác:**

1) Đối chiếu xe, tài xế, ngày đi.
2) Đầu mục **I** bấm **Xác nhận kiểm tra**. Sai thì **Trả lại sửa**.

- **Máy tự làm:** mục I thành *Đã kiểm*.
- **Máy chặn:** KT Thu/Chi không kiểm mục III – VI; mục đã kiểm khoá, muốn sửa phải **Trả lại sửa**.
- **Tờ sinh ra:** không.
- **QLSX xem ở đâu:** không.
- **Đã thử 01/10:** mục I `THU-KBAZ-G1/EPL` đã kiểm.
- **Ai làm tiếp:** —

### Bước 5 ☐ KT kho xăng dầu kiểm mục III

- **Ai:** `khonl`.
- **Trang · Màn:** điều xe → **Phiếu xuất xe** → mục **III · Chi phí nhiên liệu**.

**Thao tác:**

1) Dòng dầu kho: giá là bình quân của kho, máy tự điền (ô xám). Dòng dầu mua ngoài: gõ **Đơn giá**.
2) Bấm **Xác nhận kiểm tra**. Chưa bấm **Ghi sổ kế toán** — phải chờ thủ kho cấp dầu (bước 7).

- **Máy tự làm:** lưu giá rồi mới kiểm.
- **Máy chặn:** dòng EPL trả mà đơn giá 0 → *Mục …: dòng … chưa có đơn giá — nhập đơn giá rồi kiểm lại.*
- **Tờ sinh ra:** không.
- **QLSX xem ở đâu:** không — dầu kho là việc kho (kho tạm, sau là hệ kho anh Toàn), **không sang QLSX**.
- **Đã thử 01/10:** mục III kiểm xong. Bấm **Ghi sổ kế toán** trước khi cấp → 409: *Mục III: dòng 1 (120 lít) lấy từ kho chưa được cấp theo phiếu đề nghị xuất kho nhiên liệu. Bãi in phiếu đề nghị, thủ kho cấp dầu ở Cấp phát, rồi mới ghi sổ mục III.*
- **Ai làm tiếp:** `khotb` cấp dầu.

### Bước 6 ☐ KT Chi phí nhập giá, kiểm, ghi sổ mục IV → phiếu chi "Chi trước" bên QLSX

- **Ai:** `ketoancp`.
- **Trang · Màn:** điều xe → **Phiếu xuất xe** → mục **IV · Chi phí đi đường**.

**Thao tác:**

1) Gõ **Đơn giá** từng dòng (ví dụ tiền ăn 100.000, điện thoại 150.000, tiền nước 60.000, tiền chuyến 1.800.000).
2) Bấm **Xác nhận kiểm tra** (máy lưu giá trước).
3) Bấm **Ghi sổ kế toán**.

- **Máy tự làm:** ghi sổ xong, máy gửi phiếu chi tạm ứng sang QLSX: `POST /api/v1/accounting/cmpayment-receipt/save-and-commit`, loại **CMP DOTY 59 "Chi trước"**, `PostMode=None` (chưa ghi sổ), số tham chiếu = số tờ PTU, đối tượng tài xế `EPLTX-…`, **Nợ 1601 / Có 1011** đúng số tiền mặt. Chống trùng: tìm theo đối tượng + số tham chiếu trước khi tạo. Mục IV hiện ô *Chờ thủ quỹ chi ở hệ kế toán* + số phiếu + nút **Cập nhật**.
- **Máy chặn:** chưa ghi sổ thì chưa có phiếu chi; gửi hỏng (mất mạng, token hết hạn…) thì mục IV hiện *Chưa sang được kế toán* + nút **Gửi phiếu chi sang kế toán** (KT Chi phí).
- **Tờ sinh ra:** điều xe: PTU mang số tiền. QLSX: **CMP 59 "Chi trước"**, trạng thái chưa ghi sổ.
- **QLSX xem ở đâu:** WEB → **Danh sách phiếu chi** (`/CMPaymentReceipt/PaymentList`): chi nhánh 1368, ngày hôm nay, loại **Chi trước**; tìm số chứng từ `1368-CTR-…` hoặc số tham chiếu `PTU-<số phiếu>`. Loại 59 trên WEB **chỉ xem** (không sửa).
- **Đã thử 01/10:** **1368-CTR-261001-00072** (DocumentId 81417) · tham chiếu `PTU-THU-KBAZ-G1/EPL` · Nợ 1601 / Có 1011 **250.000 LAK** (tiền ăn + điện thoại; tiền nước, tiền chuyến trả cùng lương nên không vào) · đối tượng `[EPLTX-a6313dd63966] ທ້າວ ບຸນມີ` · diễn giải *Tạm ứng chuyến THU-KBAZ-G1/EPL · xe 343 · ທ້າວ ບຸນມີ*.
- **Ai làm tiếp:** thủ quỹ bên QLSX (bước 8).

### Bước 7 ☐ Thủ kho cấp dầu theo phiếu đề nghị; KT kho xăng dầu ghi sổ mục III

- **Ai:** `khotb` (thủ kho đúng kho ghi trên tờ), rồi `khonl`.
- **Trang · Màn:** **kho tạm** `8031` → nhóm **Kho** → **Cấp phát** (đăng nhập kho tạm cùng tên, cùng mật khẩu). Trang điều xe có màn **Phiếu đề nghị xuất kho** để xem, không cấp ở đó.

**Thao tác:**

1) Ô **Nhập mã QR**: quét mã trên tờ tài xế đưa (hoặc bấm thẳng dòng trong bảng **Chờ cấp**).
2) Khung **Đối chiếu trước khi cấp**: số xe, biển số, tài xế, khách, tuyến, các dòng dầu.
3) Bấm **Cấp dầu** → hộp: **Số lít duyệt** (chỉ xem), **Số lít cấp thật**, **Lý do cấp lệch số duyệt** (bắt buộc khi lệch) → **Cấp dầu**.
4) `khonl` quay lại trang điều xe → phiếu → mục III → **Ghi sổ kế toán**.

- **Máy tự làm:** kho tạm trừ tồn đúng kho, giá bình quân lúc cấp, sinh tờ kho **PXK_NL**; trang điều xe đánh tờ PLNL *Đã cấp*, dòng dầu mang giá lúc cấp. Mất mạng ở kho: việc vào hàng đợi, có mạng lại tự gửi (**Gửi lại ngay**).
- **Máy chặn:** thủ kho kho khác; cấp lệch không ghi lý do; cấp hai lần.
- **Tờ sinh ra:** điều xe: PLNL *Đã cấp*. Kho tạm: **PXK_NL**. QLSX: không.
- **QLSX xem ở đâu:** không.
- **Đã thử 01/10:** `khotb` cấp 120 lít, giá bình quân **28.500 LAK/l**; mục III ghi sổ.
- **Ai làm tiếp:** —

### Bước 8 ☐ Thủ quỹ bên QLSX chi tạm ứng → trang điều xe đọc lại

- **Ai:** thủ quỹ **bên QLSX**; bên điều xe `ketoancp` / `quytb` xem.
- **Trang · Màn:** QLSX WEB → **Danh sách phiếu chi**. Điều xe → **Phiếu đề nghị chi**.

**Thao tác (bên QLSX):**

1) Tìm phiếu theo số tham chiếu in trên tờ tài xế cầm tới (`PTU-…`), chi tiền mặt.
2) **Ghi sổ** phiếu (ghi sổ chính 12 hoặc ghi sổ tạm 13 đều được trang điều xe tính là đã chi).

**Thao tác (bên điều xe):**

3) **Phiếu đề nghị chi** → lọc **Tạm ứng** / **Chờ cấp** → bấm tờ PTU: thấy *Chờ thủ quỹ chi ở hệ kế toán · 1368-CTR-…* + **Cập nhật**; bấm **Cập nhật chi ở kế toán** (đầu màn) để hỏi lại cả danh sách.

- **Máy tự làm:** trang điều xe đọc `GET …/cmpayment-receipt/{id}?voucherType=CMP` lúc mở tờ, lúc tài xế bấm Xuất phát, lúc bấm Cập nhật. Thấy `STATUS` 12/13 → mục IV *Đã chi*, tờ PTU *Đã cấp* (người cấp `[dev01] Tune (hệ kế toán)`), nhật ký phiếu ghi tên người ghi sổ bên QLSX.
- **Máy chặn:** **Quỹ** bấm chi mục IV hoặc quét QR tờ tạm ứng trên trang điều xe → 409: *Tạm ứng chi ở hệ kế toán … Phiếu chi bên đó: 1368-CTR-….* Phiếu đã ghi sổ bên QLSX thì trang điều xe **không xoá phiếu xe được** (`DA_CHI_O_KE_TOAN`).
- **Tờ sinh ra:** QLSX: CMP 59 ghi sổ. Điều xe: không thêm tờ (PC_TU không sinh nữa).
- **QLSX xem ở đâu:** **Danh sách phiếu chi** → cột trạng thái *Ghi sổ chính*.
- **Đã thử 01/10:** em đóng vai thủ quỹ: `POST …/cmpayment-receipt/post` {DocumentId 81417, CMP, PostedFinal} → `1368-CTR-261001-00072` *Ghi sổ chính*; tờ `PTU-THU-KBAZ-G1/EPL` *Đã cấp*, *Đã chi (kế toán)*.
- **Ai làm tiếp:** tài xế xuất phát.

### Bước 9 ☐ Tài xế xuất phát

- **Ai:** `tx02` trên điện thoại (Bãi làm thay được: **Xe đã lăn bánh** ở cột bên phải phiếu).
- **Trang · Màn:** điều xe → **Phiếu của tôi** (tài xế chỉ có màn này).

**Thao tác:**

1) Chọn đúng chuyến ở tab **Chuyến đang chạy** (chuyến khác nằm trong danh sách bên cạnh vé).
2) Khung **Tạm ứng chuyến này** phải ghi *Đã nhận tiền*.
3) Bấm nút lớn **Xuất phát** → *Xác nhận xe chạy phiếu … đã lăn bánh?* → **Đồng ý**. Tuỳ chọn: **Chia sẻ vị trí**.

- **Máy tự làm:** hỏi lại QLSX phiếu chi tạm ứng; đã ghi sổ → phiếu *Đang vận chuyển*.
- **Máy chặn:** thủ quỹ chưa ghi sổ → nút tắt, dòng *Chưa nhận tiền tạm ứng thì chưa xuất phát*; gọi thẳng thì 409: *Phiếu chi tạm ứng 1368-CTR-… bên hệ kế toán chưa ghi sổ — tài xế chưa nhận tiền thì chưa xuất phát. Thủ quỹ chi và ghi sổ ở bên đó.*
- **Tờ sinh ra:** không.
- **QLSX xem ở đâu:** không.
- **Đã thử 01/10:** trước bước 8 → 409 `CHUA_NHAN_TAM_UNG` đúng câu trên; sau bước 8 → xuất phát được ngay.
- **Ai làm tiếp:** tài xế (bước 10).

### Bước 10 ☐ Trên đường: báo cân ở mỏ, khai đổ dầu dọc đường, báo hỏng; người duyệt

- **Ai:** `tx02` báo; `khonl` duyệt khai dầu; `totsua` duyệt báo hỏng.
- **Trang · Màn:** tài xế → **Phiếu của tôi**. Người duyệt → điều xe → **Theo dõi tuyến** → chọn xe → tab **Diễn biến**.

**Thao tác:**

1) Bốc xong ở mỏ: nút **Báo cân ở mỏ** → ô **Cân tại mỏ (t)** 40, **Ghi chú**, tuỳ chọn **Thêm ảnh phiếu cân · phiếu quặng** → **Gửi số cân**. Mất mạng vẫn bấm được (*Chờ gửi — tự gửi khi có mạng lại*).
2) Đổ thêm dầu ở trạm ngoài bằng tiền túi: ô **Khai đổ nhiên liệu** → **Đổ ở đâu** (chỉ trạm bán dầu bên ngoài), **Số lít** 30 → **Gửi khai dầu** (không ghi giá).
3) Nổ lốp, vá ở garage: ô **Báo hỏng / sự cố** → **Chuyện gì xảy ra?**, **Xe còn chạy được không?**, **Hỏng gì / việc gì**, tick **Có chi tiền**, **Số tiền dự kiến** 250.000, chọn **Chưa trả · cần EPL chi** → **Gửi báo sự cố**.
4) `khonl` → **Theo dõi tuyến** → xe → **Diễn biến** → dòng khai dầu → **Duyệt** → hộp *Duyệt · vào mục III nhiên liệu*: **Số lít**, **Đơn giá** 32.000, **Tiền tệ** LAK → **Duyệt**.
5) `totsua` → cùng chỗ → dòng báo hỏng → **Duyệt** → hộp *Duyệt · vào mục V sửa chữa*: **Nguồn** **Mua ngoài / garage (chi tiền)**, **Khoản mục**, **SL** 1, **Đơn giá** 250.000 → **Duyệt**. (Muốn từ chối: **Từ chối** + lý do.)

- **Máy tự làm:** cân mỏ có số thì máy ghi một dòng hàng theo **Loại hàng**; khai dầu duyệt xong thành dòng mục III nguồn **mua**, mục III mở lại *Đã nhập*; báo hỏng duyệt xong thành dòng mục V, mục V *Đã nhập*.
- **Máy chặn:** khai dầu chọn kho EPL → bảo dùng phiếu đề nghị xuất kho; báo cân khi mục II đã kiểm → *Mục II đã kiểm với cân tại mỏ … t*; chỉ tổ sửa chữa duyệt hỏng xe / lốp / tai nạn; chỉ Bãi hoặc KT kho xăng dầu duyệt khai dầu.
- **Tờ sinh ra:** không (mới là dòng trên phiếu).
- **QLSX xem ở đâu:** không.
- **Đã thử 01/10:** cân mỏ 40 t; khai 30 lít trạm dọc đường, duyệt 32.000 LAK/l; báo hỏng lốp, duyệt mục V 250.000 LAK.
- **Ai làm tiếp:** `khonl` kiểm lại mục III, `ketoancp` mục V (bước 11).

### Bước 11 ☐ Mục V trả ngay → phiếu chi "Chi khác" bên QLSX; mục III kiểm lại

- **Ai:** `khonl` (mục III); `ketoancp` (mục V); thủ quỹ bên QLSX; `quytb` · `quyvc` xem / đóng trạng thái.
- **Trang · Màn:** điều xe → **Phiếu xuất xe**; QLSX → **Danh sách phiếu chi**.

**Thao tác:**

1) `khonl`: mục III → kiểm giá dòng dầu mua → **Xác nhận kiểm tra** → **Ghi sổ kế toán**.
2) `ketoancp`: mục **V · Chi phí sửa chữa** → **Xác nhận kiểm tra** → **Ghi sổ kế toán**.
3) Thủ quỹ bên QLSX: tìm phiếu `1368-CKH-…` (tham chiếu `PCSC-V-<số phiếu>-1`) → chi → **Ghi sổ**.
4) `quytb`: mục V → nút **Cập nhật** → mục V *Đã chi*.
5) `quyvc`: mục III → **Xác nhận đã chi** (chỉ đổi trạng thái — xem ghi chú).

- **Máy tự làm:** ghi sổ mục V / VI có khoản **quỹ trả ngay** → `save-and-commit` **CMP DOTY 60 "Chi khác"**, định khoản theo tờ PC_SC: xe nhà **Nợ 614 (mục V) · 625 (mục VI) / Có 1011**; xe thuê **Nợ 4022 / Có 1011**. Mục chỉ có khoản tài xế ứng / trả cùng lương / nợ NCC thì không lập phiếu chi.
- **Máy chặn:** **Quỹ** bấm **Xác nhận đã chi** mục V trên trang điều xe khi phiếu bên QLSX chưa ghi sổ → 409 *Chi mục V ở hệ kế toán … Phiếu chi bên đó: 1368-CKH-….* Mục V mở lại (khai thêm khoản sửa) → phiếu chi đang chờ bên QLSX bị **rút**, ghi sổ lại thì lập lần 2 (`…-2`).
- **Tờ sinh ra:** QLSX: **CMP 60 "Chi khác"** (chưa ghi sổ → ghi sổ). Điều xe: không.
- **QLSX xem ở đâu:** **Danh sách phiếu chi**, loại **Chi khác**, tham chiếu `PCSC-V-…` / `PCSC-VI-…`.
- **Ghi chú:** **Xác nhận đã chi** mục III **không sinh phiếu nào bên QLSX**: dầu kho không có tiền chi; dầu mua dọc đường tài xế trả bằng tiền túi đi vào **tất toán** (bước 22); dầu trạm ghi nợ đi vào bút toán chờ (bước 26).
- **Đã thử 01/10:** **1368-CKH-261001-00067** (81419) · tham chiếu `PCSC-V-THU-KBAZ-G1/EPL-1` · **Nợ 614 / Có 1011 250.000 LAK** · đối tượng tài xế `EPLTX-a6313dd63966`. Trước khi ghi sổ, `quytb` chi mục V → 409 `CHI_O_KE_TOAN`. Ghi sổ xong → mục V *Đã chi*. `quyvc` **Xác nhận đã chi** mục III → *Đã chi*.
- **Ai làm tiếp:** Bãi gửi mục II.

### Bước 12 ☐ Bãi gửi mục II; KT Thu/Chi nhập tay số phiếu quặng, kiểm mục II

- **Ai:** `thabok`, rồi `ketoan`.
- **Trang · Màn:** điều xe → **Phiếu xuất xe** → mục **II**.

**Thao tác:**

1) `thabok`: ô **Cân tại mỏ (t)** đã có 40 (tài xế báo) → **Gửi kiểm tra** ở đầu mục II.
2) `ketoan`: gõ **Số phiếu quặng**, **Ngày phiếu quặng** (phiếu quặng của khách **nhập tay được**, không bắt ảnh). Sửa giá cước nếu chuyến khác hợp đồng → **Xác nhận kiểm tra** (máy lưu trước).

- **Máy tự làm:** mục II *Đã kiểm*.
- **Máy chặn:** Bãi gõ ô số phiếu quặng → *Số và ngày phiếu quặng do kế toán nhập khi nhận giấy; Bãi chỉ đính kèm ảnh.*
- **Tờ sinh ra:** không.
- **QLSX xem ở đâu:** không.
- **Đã thử 01/10:** số phiếu quặng `PQ-KBAZ-0412` nhập tay; mục II đã kiểm.
- **Ai làm tiếp:** tài xế báo về, Bãi nhận xe.

### Bước 13 ☐ Xe gom về bãi — hàng vào kho bãi

- **Ai:** `tx02` báo về; `thabok` nhận xe.
- **Trang · Màn:** tài xế → **Phiếu của tôi**; Bãi → **Phiếu xuất xe** (cột bên phải).

**Thao tác:**

1) `tx02`: **Báo đã về** → **Ngày xe về**, **Km về (công-tơ-mét)** → **Xác nhận đã về**.
2) `thabok`: bấm **Xe đã tới · nhập cân cuối** → hộp: **Cân tại mỏ (t)** (đã điền sẵn), **Cân tại bãi khi về (t)** 39,6, **Ngày xe về**, **Km về (công-tơ-mét)** (điền sẵn theo tài xế) → **Đồng ý**.

- **Máy tự làm:** hàng vào **kho bãi** ở kho tạm thành một lô theo cân tại bãi, sinh tờ kho **PNK_HH**; phiếu tự ghi dòng hao hụt (cân mỏ − cân bãi); công-tơ-mét xe cập nhật; xe, tài xế rảnh nếu không còn chuyến khác.
- **Máy chặn:** chưa có cân tại mỏ → *Chưa có cân tại mỏ — nhập số tấn theo phiếu cân ở mỏ rồi mới báo xe tới: hàng vào kho theo số đó.*; kho tạm tắt → chưa báo tới được; đã vào kho thì dòng hàng và cân không sửa nữa.
- **Tờ sinh ra:** kho tạm: **PNK_HH** (ngoài bảng, theo tấn). QLSX: không.
- **QLSX xem ở đâu:** không (kho là hệ riêng). Lô xem ở điều xe → **Xem kho**, hoặc kho tạm → **Kho** → **Kho hàng**.
- **Đã thử 01/10:** km về 61.493 (đi 293 km); lô `THU-KBAZ-G1/EPL` nhập **39,6 t**, hao hụt 0,4 t.
- **Ai làm tiếp:** `ketoan` khoá phiếu gom.

### Bước 14 ☐ KT Thu/Chi khoá phiếu GOM → phiếu đề nghị thu

- **Ai:** `ketoan`.
- **Trang · Màn:** điều xe → **Phiếu xuất xe** → cột bên phải (nút chỉ hiện khi xe đã tới).

**Thao tác:**

1) Bấm **🔒 Khoá phiếu**. Hộp **Khoá phiếu** liệt kê điểm lệch (km lệch > 10 %, hao hụt > 1,5 %, thiếu cân cuối, thiếu km về, thiếu phiếu quặng, thiếu POD với phiếu giao, mục có chi chưa kiểm, hợp đồng hết hạn) hoặc *Phiếu không có điểm lệch. Khoá rồi Bãi không sửa được nữa.*
2) Bấm **Khoá phiếu** trong hộp.

- **Máy tự làm:** lập **phiếu đề nghị thu PDT** (cước theo đúng tiền của phiếu, kèm số quy Kíp theo tỷ giá khoá trên phiếu); khoản không qua tiền thành **bút toán chờ gửi** (xe thuê, dòng ghi nợ nhà cung cấp — phiếu gom xe nhà không có).
- **Máy chặn:** xe chưa về → *Xe chưa về (trạng thái …) thì chưa khoá phiếu.*; chỉ KT Thu/Chi (và Sếp) khoá; khoá rồi Bãi, tài xế không ghi thêm.
- **Tờ sinh ra:** điều xe: **PDT** *Chờ gửi*. QLSX: chưa có.
- **QLSX xem ở đâu:** chưa có (SO ở bước 20).
- **Đã thử 01/10:** không có điểm lệch; **PDT/2610/0001** — 39,6 t × 12,5 USD = **495,00 USD** (≈ 10.890.000 LAK).
- **Ai làm tiếp:** Bãi lập phiếu giao (bước 15); `ketoan` tạo SO (bước 20).

### Phần C — Chặng GIAO (bãi → cảng, xe thuê ngoài)

### Bước 15 ☐ Bãi lập phiếu GIAO lấy hàng từ lô, xe liên kết

- **Ai:** `thabok`.
- **Trang · Màn:** điều xe → **Phiếu xuất xe** → **+ Phiếu mới** → thẻ **Giao · Giao (bãi → khách)**.

**Thao tác:**

1) Mục I: **Số xe** ຮ່ວມ-07 (xe của chủ xe ທ້າວ ຄຳຫລ້າ — phiếu tự thành **Xe thuê ngoài**); **Tài xế** ທ້າວ ສົມພອນ; ngày.
2) Mục II: **Chọn tuyến** ທ່າບົກ → ທ່າເຮືອກະລໍ; **Khách hàng** ຄຳຕຸ້ຍ. Khung **Hàng trên phiếu** → **Thêm dòng**: **Mặt hàng**, **Lấy từ lô (phiếu gom)** chọn lô của phiếu gom (ô ghi còn bao nhiêu tấn), **Số tấn** 25.
3) Mục III: **Thêm dòng** 200 lít kho Thà Bốc, ô **Ai chi** **EPL ứng**.
4) Mục IV: sang Việt Nam, điện thoại (**Chi ngay khi xe đi**), chipping Lào (**Nợ NCC / trả theo đợt**); phí cao tốc máy tự thêm theo tuyến — chọn **Trả tiền mặt (không dùng thẻ)** hoặc chọn thẻ.
5) **Lưu** → **Phiếu đề nghị xuất kho nhiên liệu**, **Phiếu đề nghị tạm ứng** → **Gửi kiểm tra** ở mục I, II, III, IV.

- **Máy tự làm:** hàng **xuất khỏi kho bãi** ngay khi lưu (kho tạm sinh **PXK_HH**), **Cân đầu** = số tấn lấy; tự điền hợp đồng khách và **Hợp đồng thuê xe**; phí, ngưỡng tấn theo hồ sơ chủ xe; đầu mục III ghi *Xuất bán cho chủ xe · ທ້າວ ຄຳຫລ້າ*, mục IV *Tạm ứng ghi công nợ chủ xe*. Xe thuê không có "trả cùng lương" — khoản đó tự thành **Chi ngay khi xe đi**.
- **Máy chặn:** dòng hàng không chỉ rõ lô; lấy quá số tấn còn của lô (*Lô … chỉ còn … tấn*); kho tạm tắt thì không lưu được phiếu giao có lấy lô.
- **Tờ sinh ra:** điều xe: **DO**, **PLNL**, **PTU**. Kho tạm: **PXK_HH**. QLSX: chưa có.
- **QLSX xem ở đâu:** chưa có.
- **Đã thử 01/10:** `THU-KBAZ-T1/EPL`, xe ຮ່ວມ-07, hợp đồng `HDVC-2026-001` + `HDTX-2026-001`, lấy 25 t (lô gom còn **14,6 t**). `PLNL-THU-KBAZ-T1/EPL-1` 200 lít; `PTU-THU-KBAZ-T1/EPL` **4.247.000 LAK** (sang VN 430.000 + điện thoại 150.000 + cao tốc tiền mặt 3.667.000; chipping 620.000 là nợ nhà cung cấp, không vào tạm ứng).
- **Ai làm tiếp:** kế toán kiểm (bước 16 – 17).

### Bước 16 ☐ Kiểm I – II; giá bán dầu cho chủ xe; cấp dầu; ghi sổ III

- **Ai:** `ketoan` (I, II), `khonl` (III), `khotb` (cấp).
- **Trang · Màn:** điều xe → **Phiếu xuất xe**; kho tạm → **Kho** → **Cấp phát**.

**Thao tác:**

1) `ketoan`: mục I, II → **Xác nhận kiểm tra** (kiểm giá thuê xe mỗi tấn, phí, tải cho phép).
2) `khonl`: mục III → dòng dầu kho: dưới ô đơn giá (giá vốn, xám) gõ **Giá bán cho chủ xe** (ví dụ 33.000 LAK/l) → **Xác nhận kiểm tra**.
3) `khotb`: kho tạm → **Cấp phát** → **Cấp dầu** (như bước 7).
4) `khonl`: mục III → **Ghi sổ kế toán**.

- **Máy tự làm:** tiền dầu trừ chủ xe tính theo **giá bán**; giá vốn vẫn là bình quân kho.
- **Máy chặn:** chưa có giá bán → *Xe thuê: dầu lấy từ kho là xuất bán cho chủ xe ທ້າວ ຄຳຫລ້າ — dòng 1 (200 lít) chưa có giá bán. Nhập giá bán cho chủ xe rồi kiểm lại.*
- **Tờ sinh ra:** kho tạm: **PXK_NL**. QLSX: không.
- **QLSX xem ở đâu:** không.
- **Đã thử 01/10:** chặn giá bán đúng câu trên; giá bán 33.000 LAK/l → 200 lít = 6.600.000 LAK trừ chủ xe; cấp 200 lít; ghi sổ III.
- **Ai làm tiếp:** `ketoancp` (bước 17).

### Bước 17 ☐ Ghi sổ mục IV xe thuê → "Chi trước" đứng tên chủ xe; tài xế xuất phát

- **Ai:** `ketoancp`; thủ quỹ bên QLSX; `tx03`.
- **Trang · Màn:** điều xe → **Phiếu xuất xe** mục IV; QLSX → **Danh sách phiếu chi**; tài xế → **Phiếu của tôi**.

**Thao tác:**

1) `ketoancp`: gõ **Đơn giá** các dòng mục IV → **Xác nhận kiểm tra** → **Ghi sổ kế toán**.
2) Thủ quỹ QLSX: chi tiền mặt, **Ghi sổ** phiếu `1368-CTR-…`.
3) `tx03`: **Xuất phát**.

- **Máy tự làm:** như bước 6 nhưng đối tượng là **chủ xe** `EPLCX-<mã chủ xe>` và định khoản **Nợ 4022 / Có 1011** (tạm ứng ghi công nợ chủ xe — trừ vào tiền trả chủ xe ở bước 23, **không** tất toán với tài xế).
- **Máy chặn:** danh mục tài khoản bên QLSX thiếu 4022 → bên đó từ chối, câu lỗi hiện trên mục IV, KT Chi phí **Gửi phiếu chi sang kế toán** sau khi mở mã.
- **Tờ sinh ra:** QLSX: **CMP 59 "Chi trước"** đứng tên chủ xe.
- **QLSX xem ở đâu:** **Danh sách phiếu chi**, loại **Chi trước**, đối tượng `EPLCX-…`.
- **Đã thử 01/10:** **1368-CTR-261001-00073** (81421) · tham chiếu `PTU-THU-KBAZ-T1/EPL` · **Nợ 4022 / Có 1011 4.247.000 LAK** · đối tượng `[EPLCX-0a073ea75bb3] ທ້າວ ຄຳຫລ້າ` · diễn giải *Tạm ứng chuyến THU-KBAZ-T1/EPL · xe ຮ່ວມ-07 · ທ້າວ ສົມພອນ · xe thuê của ທ້າວ ຄຳຫລ້າ*. Ghi sổ xong, `tx03` xuất phát được.
- **Ai làm tiếp:** tài xế giao hàng.

### Bước 18 ☐ Giao hàng: ký nhận POD trên máy tài xế; Bãi nhập cân cuối

- **Ai:** `tx03`, rồi `thabok`.
- **Trang · Màn:** tài xế → **Phiếu của tôi**; Bãi → **Phiếu xuất xe**.

**Thao tác:**

1) `tx03` tới cảng: nút lớn **Giao hàng hoàn tất · ký nhận** → **Người ký nhận**, **Điện thoại người nhận**, **Tình trạng hàng** (**Đủ** / **Thiếu** / **Hư hỏng**), người nhận ký ở ô **Người nhận ký** (**Ký lại** nếu sai), tuỳ chọn **Thêm ảnh biên bản · phiếu cân** → **Gửi**. Mất mạng vẫn ký được, có mạng tự gửi.
2) `tx03` về: **Báo đã về** → **Xác nhận đã về**.
3) `thabok`: **Xe đã tới · nhập cân cuối** → **Cân cuối (tấn)** 24,7, **Ngày xe về**, **Km về (công-tơ-mét)**, **Số POD**, **Người ký nhận** → **Đồng ý**. Khung **Biên bản giao nhận hàng (POD)** có **In biên bản giao nhận**.

- **Máy tự làm:** ghi chữ ký, giờ, vị trí, số POD (trống thì `POD-<số phiếu>`); dòng hao hụt chặng giao (25 − 24,7). Mỗi phiếu xuất xe mang **cả hợp đồng và POD** — hai thứ này đi theo phiếu sang tờ đề nghị thu và gói bàn giao.
- **Máy chặn:** chưa xuất phát → *Xe chưa xuất phát — chưa ghi giao hàng hoàn tất được.*; không chữ ký mà không ảnh → *Cần chữ ký người nhận hoặc ít nhất một ảnh biên bản / phiếu cân.*; hàng thiếu / hỏng không ghi chú → chặn.
- **Tờ sinh ra:** điều xe: chữ ký + ảnh POD đính kèm phiếu.
- **QLSX xem ở đâu:** sau khi khoá: modal **Vụ việc** (bước 25) hiện *Ký nhận POD*.
- **Đã thử 01/10:** POD `POD-THU-KBAZ-T1`, người nhận *ນາງ ມະນີ (THU-KBAZ)*, ký trên máy; cân cảng 24,7 t, hao hụt 0,3 t.
- **Ai làm tiếp:** `ketoan` khoá.

### Bước 19 ☐ Khoá phiếu GIAO → đề nghị thu + bút toán chờ (xe thuê)

- **Ai:** `ketoan`.
- **Trang · Màn:** điều xe → **Phiếu xuất xe** → **🔒 Khoá phiếu**.

**Thao tác:** như bước 14. Phiếu giao không có phiếu quặng → hộp cảnh báo *Chưa có phiếu quặng của khách — đính kèm ảnh, hoặc nhập tay số phiếu quặng.* → đọc, đúng thì **Khoá phiếu**.

- **Máy tự làm:** lập **PDT**; ghi **bút toán chờ gửi**: thuê xe **Nợ 621 / Có 4022** bằng tiền thuê; dòng ghi nợ nhà cung cấp (chipping) — xe thuê **Nợ 4022 / Có 4021**, xe nhà Nợ 625 · 614 / Có 4021.
- **Máy chặn:** như bước 14. Mở khoá sau khi đã có SO: KT Thu/Chi bị chặn *Bên công nợ đã tạo SO … — báo bên đó trước, rồi nhờ Sếp mở khoá.*; phiếu nằm trong đề nghị trả chủ xe → không mở khoá được (kể cả Sếp).
- **Tờ sinh ra:** điều xe: **PDT**, hai **bút toán chờ gửi**. QLSX: chưa có (bút toán chờ bật API — mục 3).
- **QLSX xem ở đâu:** chưa có.
- **Đã thử 01/10:** **PDT/2610/0002** — 24,7 t × 30,5 USD = **753,35 USD** (≈ 16.573.700 LAK). Bút toán chờ: `EPLLAO-thue_xe-ea99922a96ee` **621/4022 741,00 USD** (24,7 t × 30 USD = 16.302.000 LAK) và `EPLLAO-no_ncc-ea99922a96ee` **4022/4021 620.000 LAK**.
- **Ai làm tiếp:** `ketoan` tạo SO; thủ quỹ / kế toán QLSX.

### Phần D — Tiền ở QLSX, trang điều xe đọc lại

### Bước 20 ☐ Tạo SO bên kế toán (mỗi DO một lần)

- **Ai:** `ketoan` (hoặc Sếp).
- **Trang · Màn:** điều xe → **Phiếu đề nghị thu** (hoặc trên phiếu: khối **Phiếu đề nghị** → **Phiếu đề nghị thu**).

**Thao tác:**

1) Ô **Tháng** chọn tháng của DO. Thanh trạng thái: **Chưa lập đề nghị · Chờ gửi · Đã tạo SO · Thu một phần · Đã thu đủ · Chờ khoá phiếu · Tất cả**.
2) Bấm DO ở danh sách bên trái → tờ **PHIẾU ĐỀ NGHỊ THU** bên phải.
3) Bấm **Tạo SO bên kế toán** → hộp *Gửi DO này sang bên kế toán?* (*Bên kế toán sẽ tạo SO và ghi công nợ khách … (mã …) số …*; khách chưa có mã thì báo mã sẽ tạo) → **Tạo SO bên kế toán**.
4) Thanh nút hiện **Đã có SO TK-…**; danh sách đổi sang **Đã tạo SO**.

- **Máy tự làm:** xem trước ở máy chủ (không gọi mạng), đủ luật mới gửi `POST /api/v1/integrations/logistics/sales-orders` (`Idempotency-Key: logistics:EPLLAO-<id>`), một dòng thu cước. Bấm lại không gọi lần hai.
- **Máy chặn:** DO chưa khoá (`DO_CHUA_KHOA`), thiếu khách / mã khách / tuyến, mã khách + mã tuyến > 50 ký tự, cước 0, tiền THB / CNY (`TIEN_TE_CHUA_NHAN`); người bấm không phải KT Thu/Chi / Sếp → 403. Bên QLSX từ chối → *Lần gửi trước chưa được: …* kèm câu của bên đó.
- **Tờ sinh ra:** QLSX: **SO** (`TK-…`, trạng thái 5 *Hoàn thành*) + **công nợ khách** (phiếu bán `RETK`, nợ = cước).
- **QLSX xem ở đâu:** WEB → **Bán hàng** → **Đơn hàng bán** (`/TicketOrder/Index`) tìm `TK-…`; công nợ: **Danh sách công nợ** (`/DebtCollection/Workspace`) → khách ຄຳຕຸ້ຍ → **Chi tiết công nợ khách hàng** → bảng **Chi tiết hóa đơn theo tuổi nợ** (cột mã đơn = `TK-…`).
- **Đã thử 01/10:** **TK-20261001-000164** (gom, **495,00 USD**, mặt hàng `EPLKH-0834a9e9606b_b9213bcb64b9`) và **TK-20261001-000165** (giao, **753,35 USD**, `EPLKH-0834a9e9606b_0b840ad2a162`) — HTTP 201, nợ ban đầu bằng cước.
- **Ai làm tiếp:** kế toán bên QLSX thu tiền khách.

### Bước 21 ☐ QLSX thu tiền khách → trang điều xe đọc "Đã thu đủ"

- **Ai:** kế toán / thủ quỹ **bên QLSX**; bên điều xe `ketoan` bấm Cập nhật.
- **Trang · Màn:** QLSX WEB → **Danh sách công nợ** → **Chi tiết công nợ khách hàng**. Điều xe → **Phiếu đề nghị thu**; **Khách hàng** → khách → **Công nợ**.

**Thao tác (bên QLSX):**

1) **Danh sách công nợ** → chọn chi nhánh 1368 → mở khách ຄຳຕຸ້ຍ (`/DebtCollection/CustomerDetail?objAutoId=1608&orgId=1368`).
2) Bảng **Chi tiết hóa đơn theo tuổi nợ**: tick các dòng `TK-…` cần thu (cùng loại tiền) → **Tạo phiếu thu**.
3) Hộp **Tạo phiếu thu**: **Quốc gia kế toán** Lào, **Tài khoản tiền thu**, **Phương thức thanh toán** (Tiền mặt / Chuyển khoản), **Ghi chú**; bảng **Phân bổ tiền thu theo hóa đơn** → **Xác nhận thu nợ**.
4) **Danh sách phiếu thu** (`/CMPaymentReceipt/ReceiptList`): mỗi lần thu nợ sinh một phiếu thu → **Ghi sổ**.

**Thao tác (bên điều xe):**

5) `ketoan` → **Phiếu đề nghị thu** → **Cập nhật** → DO chuyển **Đã thu đủ** (thu thiếu: **Thu một phần**).
6) **Khách hàng** → ຄຳຕຸ້ຍ → tab **Công nợ** → khối **Công nợ bên hệ kế toán** (*Chỉ xem — thu tiền, hoá đơn ở hệ kế toán.*): tổng nợ, đã thu, từng SO.

- **Máy tự làm (QLSX):** `POST /api/v1/sales/debt/collection-upsert` (phiếu thu nợ **TKN**, mỗi SO một phiếu) → tự sinh **phiếu thu CM DOTY 17 "Thu khác"**, **Nợ 1021 / Có 1211**, chưa ghi sổ, tham chiếu = số TKN.
- **Máy tự làm (điều xe):** đọc `POST /api/v1/sales/debt/customer-detail` của khách (mỗi khách tối đa một lần / 60 giây), ghép dòng nợ theo `OrderCode` = SO: còn nợ ≤ nửa xu → **Đã thu đủ**; đã trả > 0 → **Thu một phần**. Chỉ đọc, không ghi gì sang QLSX.
- **Máy chặn (QLSX):** chọn dòng khác loại tiền → *Chỉ thu các khoản cùng loại tiền …*; tiền thu > nợ còn lại → chặn.
- **Tờ sinh ra:** QLSX: **TKN** + **CMR 17**. Điều xe: không (chỉ đổi trạng thái thu của DO).
- **QLSX xem ở đâu:** **Chi tiết công nợ khách hàng** → **Lịch sử thanh toán gần nhất**; **Danh sách phiếu thu** loại **Thu khác**, số `4-1368-TK-…`.
- **Lưu ý:** công nợ SO nằm ở phân hệ **Bán hàng**, nên **không thu bằng phiếu thu "Thu công nợ" (DOTY 15)** ở màn phiếu thu: tìm chứng từ công nợ của khách ở đó trả **0 dòng** (đã thử). Đường đúng là **Tạo phiếu thu** ở màn công nợ như trên.
- **Đã thử 01/10:** em gửi đúng lời gọi WEB gửi (`TKN`, chi nhánh 1368, Ngân hàng nội tệ, Chuyển khoản, tỷ giá 1): **4-TKN-1368-2-261001-0001** (495 USD, SO 164) → phiếu thu **4-1368-TK-261001-00009** (81423); **4-TKN-1368-2-261001-0002** (753,35 USD, SO 165) → **4-1368-TK-261001-00010** (81424); cả hai **Nợ 1021 / Có 1211**, ghi sổ xong. Bên điều xe: hai DO **Đã thu đủ**; khối Công nợ bên hệ kế toán: đã thu 1.248,35 USD. **Lỗi số** em gặp ở bước này: xem mục 6, điểm 1.
- **Ai làm tiếp:** `ketoancp` tất toán; `ketoan` trả chủ xe.

### Bước 22 ☐ Tất toán tạm ứng tài xế (xe nhà) theo tháng

- **Ai:** `ketoancp` chốt; thủ quỹ bên QLSX chi / thu; `quytb` bấm Cập nhật.
- **Trang · Màn:** điều xe → **Tất toán tài xế** (vai KT Chi phí VC, Quỹ tiền mặt, Thủ quỹ VC).

**Thao tác:**

1) Ô **Tháng** → bấm tài xế ở danh sách: **Phiếu trong kỳ**, **Đã ứng**, **Đã chi thật**, **Chênh lệch** (*Công ty chi bù* / *Tài xế nộp lại* / *Vừa đủ*), bảng phiếu.
2) Bấm **Chốt tất toán** → hộp *Tất toán kỳ … cho …?*, **Chi / thu bằng** (Tiền mặt / Chuyển khoản), **Ghi chú** → **Chốt tất toán**.
3) Thủ quỹ QLSX: chi bù (hoặc thu hoàn) → **Ghi sổ**.
4) `quytb` / `ketoancp`: **Cập nhật** → *Đã tất toán xong*.

- **Máy tự làm:** **Đã ứng** = phiếu chi tạm ứng đã ghi sổ bên QLSX; **Đã chi thật** = khoản tài xế móc tiền túi (mục IV, VI tiền mặt + dầu mua dọc đường), không tính khoản trả cùng lương, nợ NCC, trừ thẻ, dầu kho. Chênh dương → **TT_CHI**: CMP **60 "Chi khác"** **Nợ 1601 / Có tiền**; chênh âm → **TT_THU**: CMR **17 "Thu khác"** **Nợ tiền / Có 1601**; đứng tên tài xế `EPLTX-…`. Đồng thời bút toán chờ **QT_TU Nợ 625 / Có 1601** bằng số đã chi thật. Xe thuê không có trong màn này.
- **Máy chặn:** tài xế còn tạm ứng chưa chi xong bên QLSX → *Còn tạm ứng chưa chi xong ở hệ kế toán — chưa chốt được*; chốt lần hai → 409; Quỹ bỏ chốt → 403 (chỉ KT Chi phí **Bỏ chốt**; phiếu chưa ghi sổ bên QLSX bị rút).
- **Tờ sinh ra:** điều xe: bản chốt + bút toán chờ QT_TU. QLSX: **CMP 60** (TT_CHI) hoặc **CMR 17** (TT_THU).
- **QLSX xem ở đâu:** **Danh sách phiếu chi** loại **Chi khác**, tham chiếu `TTX-<kỳ>-…` (hoặc **Danh sách phiếu thu** loại **Thu khác**).
- **Đã thử 01/10:** ທ້າວ ບຸນມີ kỳ 10/2026: đã ứng 250.000, đã chi thật 1.210.000 (250.000 + 30 lít × 32.000 dầu mua dọc đường), chênh **960.000** → **1368-CKH-261001-00068** (81427) · tham chiếu `TTX-202610-99c2aab4` · **Nợ 1601 / Có 1011 960.000 LAK** · ghi sổ → *Đã tất toán xong*. Bút toán chờ `EPLLAO-tat_toan-a6313dd63966:2026-10:99c2aab478f2` **625/1601 1.210.000 LAK**.
- **Ai làm tiếp:** —

### Bước 23 ☐ Trả chủ xe liên kết (trừ hàng mua ở quầy nếu có)

- **Ai:** `ketoan` (KT Thu/Chi) lập; thủ quỹ QLSX chi.
- **Trang · Màn:** điều xe → **Xe liên kết** → dòng chủ xe → **Trả qua kế toán**.

**Thao tác:**

1) Hộp *Trả qua kế toán · ທ້າວ ຄຳຫລ້າ*: **Các lần đề nghị trả**, **Phiếu chờ trả** (phiếu xe thuê đã khoá chưa trả, mỗi dòng **Tiền thuê**, **Còn phải trả**). Tick phiếu trả đợt này (cùng một loại tiền thuê), xem khung hàng mua ở quầy chờ trừ nếu có, chọn **Cách trả** **Tiền mặt** / **Chuyển khoản** → **Lập đề nghị trả**.
2) Toast *Đã lập đề nghị trả · phiếu chi … bên kế toán*.
3) Thủ quỹ QLSX: chi → **Ghi sổ**.
4) `ketoan`: mở lại hộp → **Cập nhật** ở dòng đề nghị → *Đã chi (kế toán)*; phiếu xe hiện **Đã trả chủ xe**.

- **Máy tự làm:** số trả = tiền thuê − phí quản lý % − cắt quá tải − mọi khoản EPL đã ứng (dầu kho theo **giá bán**, tạm ứng, nợ NCC trả thay), không gõ tay; **trừ tiếp hàng chủ xe mua ở quầy** (phiếu bán ở kho tạm, giữ chỗ `TUNE-CHO:<số đề nghị>`). Gửi `save-and-commit` **CMP 60 "Chi khác"** đứng tên chủ xe `EPLCX-…`, mỗi phiếu xe một dòng **Nợ 4022 / Có 1011 · 1012 · 1021 · 1022** (theo cách trả, nội / ngoại tệ), tỷ giá riêng từng dòng. Thủ quỹ ghi sổ xong → phiếu bán chốt `TUNE:<số phiếu chi>` và ghi bút toán chờ **Nợ 4022 / Có 707** (hàng bán cho chủ xe).
- **Máy chặn:** chọn phiếu khác loại tiền thuê → *Các phiếu chọn khác tiền thuê — mỗi đề nghị một loại tiền*; phiếu còn phải trả ≤ 0 → không lập; Bãi xem → 403; Quỹ lập → 403; phiếu đang nằm đề nghị → không vào đề nghị khác, không mở khoá được; kho tạm tắt → không lập được (503). **Bỏ đề nghị** → rút phiếu chi chưa ghi sổ bên QLSX, phiếu về chờ trả.
- **Tờ sinh ra:** QLSX: **CMP 60**. Điều xe: phiếu *Đã trả chủ xe*; (nếu có hàng quầy) bút toán chờ 4022/707.
- **QLSX xem ở đâu:** **Danh sách phiếu chi** loại **Chi khác**, tham chiếu `TCX-…`, đối tượng `EPLCX-…`.
- **Đã thử 01/10:** `THU-KBAZ-T1/EPL`: tiền thuê 741,00 − phí 2 % 14,82 − EPL đã ứng 521,23 (dầu 300,00 + tạm ứng 193,05 + chipping 28,18) = **204,95 USD** (4.508.900 LAK). Đề nghị `TCX-261001104415-0a07` → **1368-CKH-261001-00069** (81429) · **Nợ 4022 / Có 1012 204,95 USD** (tiền mặt ngoại tệ) · ghi sổ → phiếu *Đã trả chủ xe* (`TUNE:1368-CKH-261001-00069`). Chủ xe này **không có hàng quầy chờ trừ** trên DB thử → phần trừ hàng và bút toán 4022/707 **chưa đi thật** lượt này.
- **Ai làm tiếp:** —

### Bước 24 ☐ Trả nhà cung cấp (chipping, dầu trạm ghi nợ…)

- **Ai:** `ketoancp` lập; thủ quỹ QLSX chi; `quytb` Cập nhật.
- **Trang · Màn:** điều xe → **Nhà cung cấp** → dòng nhà cung cấp → **Trả qua kế toán**.

**Thao tác:**

1) Hộp: công nợ (**Phát sinh (LAK)**, **Đã trả**, **Chờ chi**, **Còn nợ**), phần **Lập đề nghị trả**: **Số tiền trả**, **Tiền tệ**, **Tỷ giá sang Kíp**, **Cách trả**, **Ghi chú** → **Lập đề nghị trả**.
2) Thủ quỹ QLSX: chi → **Ghi sổ**. Bên điều xe: **Cập nhật** → *Đã chi (kế toán)*.

- **Máy tự làm:** `save-and-commit` **CMP 60 "Chi khác"** đứng tên `EPLNCC-…`, **Nợ 4021 / Có tiền**.
- **Máy chặn:** số tiền 0; trả vượt số còn nợ → hỏi *Trả vượt số còn nợ?* rồi mới lập; KT Thu/Chi lập → 403; Quỹ **Bỏ đề nghị** → 403.
- **Tờ sinh ra:** QLSX: **CMP 60**.
- **QLSX xem ở đâu:** **Danh sách phiếu chi**, tham chiếu `TNCC-…`, đối tượng `EPLNCC-…`.
- **Đã thử 01/10:** ຊີບປີງ ລາວ (ສາງພາສີ) — trả 620.000 (khoản chipping của `THU-KBAZ-T1`): `TNCC-261001104417-804c` → **1368-CKH-261001-00070** (81431) · **Nợ 4021 / Có 1021 620.000 LAK** · ghi sổ → *Đã chi (kế toán)*.
- **Ai làm tiếp:** —

### Bước 25 ☐ Bàn giao DO: QLSX đọc DO qua modal Vụ việc (B1/B2)

- **Ai:** kế toán bên QLSX.
- **Trang · Màn:** QLSX WEB → mở / tạo một phiếu chi hoặc phiếu thu (`/CMPaymentReceipt/Upsert`) → dòng định khoản → cột **Vụ việc** → **Chọn Vụ việc** → nguồn **DO**.

**Thao tác:**

1) Trong modal, ô tìm gõ số phiếu (ví dụ `THU-KBAZ`), tên khách hoặc biển số.
2) Bấm một DO → khung chi tiết: thông tin vận chuyển, POD, tổng hợp tài chính DO (doanh thu, chi phí thực tế theo mục, lãi gộp, tỷ giá).
3) Chọn DO cho dòng → lưu phiếu (chỉ là tham chiếu, không tạo thanh toán DO).

- **Máy tự làm:** API QLSX gọi trang điều xe `GET /api/handover/delivery-orders?q=…` (B1) và `GET /api/handover/delivery-orders/{do_id}` (B2), mang khoá bàn giao. Chỉ DO **đã về và đã khoá**.
- **Máy chặn:** thiếu `LogisticsSource:BaseUrl` → 503; khoá sai → 502 *Logistics từ chối khoá truy cập*; DO chưa khoá → 409.
- **Tờ sinh ra:** QLSX: ảnh chụp DO lưu kèm phiếu (snapshot).
- **QLSX xem ở đâu:** như trên.
- **Đã thử 01/10:** `GET /api/v1/accounting/cash-voucher-references?type=DO&keyword=THU-KBAZ` trả **2 DO** `EPLLAO-ea99922a96ee` (`THU-KBAZ-T1/EPL`) và `EPLLAO-37367086d283` (`THU-KBAZ-G1/EPL`), *delivered*, Total 2, SearchScope ALL; chi tiết từng DO có `SelectionToken`. Gói DO giao: doanh thu 753,35 USD, chi thực tế 11.467.000 LAK, lãi 12,35 USD, khối thuê xe `621/4022`, `invoiced` = có SO `TK-20261001-000165`.
- **Ai làm tiếp:** —

### Bước 26 ☐ Bút toán chờ gửi (khoản không qua tiền)

- **Ai:** `ketoan`, `ketoancp`, Sếp (chỉ ba vai này thấy màn).
- **Trang · Màn:** điều xe → **Bút toán chờ gửi** (hoặc trên phiếu: khối **Bút toán chờ gửi** ở cột bên phải → **Mở màn Bút toán chờ**).

**Thao tác:**

1) Lọc **Tất cả · Chờ gửi · Đã gửi · Đã huỷ · Chờ bút toán đảo**, **Tháng**, nguồn (**Chi phí thuê xe liên kết** · **Ghi nợ nhà cung cấp** · **Quyết toán tạm ứng tài xế** · **Hàng bán cho chủ xe**).
2) Bấm một dòng → chi tiết Nợ / Có, đối tượng, chứng từ gốc.
3) (Chỉ khi đã bật — mục 3) **Gửi sang kế toán** từng dòng, **Gửi hết**, **Cập nhật**.

- **Máy tự làm:** hiện **chưa bật** (`QLSX_GUI_BUT_TOAN` tắt): bút toán nằm ở đây đủ hai vế, chờ API. Bật rồi thì ghi xong tự gửi, gỡ khi nguồn bị huỷ (xem mục 3).
- **Máy chặn:** cờ tắt mà bấm **Gửi hết** → 409 *Chưa bật gửi bút toán sang hệ kế toán (QLSX_GUI_BUT_TOAN) — bên đó chưa có đường nhận; bút toán nằm ở đây để xem.*
- **Tờ sinh ra:** điều xe: bút toán chờ. QLSX: **chưa có** — sau khi bật: **chứng từ Tổng hợp DOTY 12, ghi sổ tạm ST 13**.
- **QLSX xem ở đâu:** sau khi bật — xem mục 3.
- **Đã thử 01/10:** 3 bản *Chờ gửi* của chuyến: thuê xe 621/4022 741,00 USD · ghi nợ NCC 4022/4021 620.000 LAK · quyết toán tạm ứng 625/1601 1.210.000 LAK. **Gửi hết** → 409 `GUI_DANG_TAT`. API 5090 `GET …/journal-entries/EPLLAO-thue_xe-ea99922a96ee` → 503 `LOGISTICS_JOURNAL_SCRIPT_REQUIRED` (đúng: chưa áp script).
- **Ai làm tiếp:** chủ dự án áp script (mục 3).

### Bước 27 ☐ Đóng chuyến — kiểm trạng thái cuối

- **Ai:** `ketoan` hoặc Sếp; anh Tune bên QLSX.
- **Trang · Màn:** điều xe → **Đề nghị theo DO** (tab **Theo DO**, lọc **Chi còn chờ · Xuất kho còn chờ · Thu còn chờ**); **Phiếu xuất xe**; QLSX → **Danh sách phiếu chi / thu**, **Chi tiết công nợ khách hàng**.

**Thao tác:** đối chiếu bảng ở mục 4. Một chuyến xong khi:

1) Hai phiếu **Đã khoá**, các mục có chi đều **Đã chi** (mục III dầu kho: **Xác nhận đã chi** để đóng trạng thái).
2) Đề nghị thu **Đã thu đủ**.
3) Tờ tạm ứng **Đã cấp**, phiếu chi bên QLSX ghi sổ; tài xế xe nhà **Đã tất toán xong** cho kỳ.
4) Phiếu xe thuê **Đã trả chủ xe**; nhà cung cấp đã trả (hoặc còn nợ theo đợt).
5) Bút toán chờ: **Chờ gửi** (chưa bật) hoặc **Đã gửi** có số chứng từ bên QLSX (đã bật).

- **Máy tự làm:** gói bàn giao trả `trip_status = completed`.
- **Máy chặn:** —
- **Đã thử 01/10:** `THU-KBAZ-G1/EPL` và `THU-KBAZ-T1/EPL` *Đã giao hàng · Đã thanh toán · Đã tạo SO · Đã khoá*; mục chi đều *Đã chi*; T1 *Đã trả chủ xe*. Xe 343 và ຮ່ວມ-07 vẫn *Đang chạy* vì trên DB thử hai xe còn chuyến khác chưa về (không phải lỗi).

---

## 3. Bút toán tổng hợp — bật thế nào, kiểm ở đâu (kỳ vọng sau khi bật)

**Hiện trạng 01/10:** API bên anh Tune đã có (`feat/HonTunedaHai@b9227aa`, `POST /api/v1/integrations/logistics/journal-entries`, `/reverse`, `GET /{SourceRef}`); cấu hình `LogisticsJournalEntry` đã có ở API máy thử (`Enabled`, `AllowedUserIds` 846, `OrgId` 1368, `CountryId` 11); **script DB chưa áp** → GET trả 503 `LOGISTICS_JOURNAL_SCRIPT_REQUIRED`; cờ `QLSX_GUI_BUT_TOAN` ở trang điều xe **tắt**. Bước 26 vì vậy ghi "kỳ vọng sau khi bật".

**Bật theo thứ tự** (chi tiết lệnh, cách đọc D1 – D7: `HUONG_DAN_TRIEN_KHAI_ANH_TUNE` mục 4.6):

1) Áp `Backend.API/Database/Scripts/20261001_logistics_journal_entry.sql` vào **DB kế toán API dùng cho phiếu thu chi** (máy thử: chủ dự án tự chạy; host: cần quyền host). Script chỉ `CREATE OR ALTER` ba thủ tục `proc_Logistics_JournalEntry_Save / _Reverse / _Get`, chạy lại được. Đọc diagnostics D1 – D7.
2) Cấu hình `LogisticsJournalEntry` (đã có ở máy thử; host thì thêm).
3) Đặt `QLSX_GUI_BUT_TOAN=1` trong `.env` trang điều xe máy thử 8011, khởi động lại.
4) Gọi thử bằng tay (SourceRef không bắt đầu `EPLLAO-`), rồi qua trang điều xe.

**Kỳ vọng sau khi bật — cách kiểm:**

| ☐ | Làm | Phải thấy bên điều xe | Phải thấy bên QLSX |
|---|---|---|---|
| ☐ | Mở **Bút toán chờ gửi** | dòng ghi chú báo gửi đang **bật**; có nút **Gửi sang kế toán**, **Gửi hết**, **Cập nhật** | — |
| ☐ | Bấm **Gửi hết** (chỉ trên máy thử dùng DB bản sao) | các bản *Chờ gửi* → *Đã gửi*, cột **Số chứng từ bên kế toán** có số | mỗi bút toán một **chứng từ Tổng hợp** (phân hệ 38, **DOTY 12**), **ghi sổ tạm ST 13**, `DOC_REFDOCUMENTNO` = SourceRef `EPLLAO-<nguồn>-<mã nguồn>` |
| ☐ | Khoá một phiếu xe thuê mới | bút toán thuê xe tự gửi trong lúc khoá (chờ tối đa 8 giây), *Đã gửi* | chứng từ Nợ 621 / Có 4022, đối tượng chủ xe |
| ☐ | Mở khoá phiếu đó (Sếp) | bản đã gửi được **gỡ** (đảo); gỡ chưa được thì *Chờ bút toán đảo* | chứng từ cũ bị gỡ; khoá lại → SourceRef mới `…-2` |
| ☐ | Gọi `GET …/journal-entries/EPLLAO-thue_xe-<trip_id>` | — | `DocumentNo`, `StatusId` 13 |
| ☐ | Tài khoản không có trong danh mục Lào | bản đó giữ *Chờ gửi*, cảnh báo *Tài khoản chưa ghi sổ được bên kế toán* | 400 `INVALID_ACCOUNTS` kèm danh sách mã |

- **QLSX xem ở đâu:** WEB nhánh `feat/hontunedhai_Laos` **chưa có màn** xem chứng từ Tổng hợp; anh Tune xem ở màn chứng từ Tổng hợp của QLSX bản đang dùng (DOTY 12) hoặc gọi `GET …/journal-entries/{SourceRef}`.
- Lúc bật trên máy thử, ba bản *Chờ gửi* của chuyến THU-KBAZ (bước 26) là bộ thử sẵn: thuê xe, ghi nợ NCC, quyết toán tạm ứng. Bản *Đã huỷ* không gửi.

---

## 4. Một chuyến đi xong — bên điều xe có gì, bên QLSX có gì

Số thật của chuyến THU-KBAZ ngày 01/10.

| Việc | Bên điều xe | Bên QLSX | Định khoản | Số tiền |
|---|---|---|---|---|
| Lập phiếu | DO `THU-KBAZ-G1/EPL`, `THU-KBAZ-T1/EPL` | đọc qua B1/B2 (modal Vụ việc) | — | — |
| Dầu kho | PLNL `…-G1/EPL-1` (120 l), `…-T1/EPL-1` (200 l) đã cấp; kho tạm PXK_NL | không | (kho) | — |
| Tạm ứng xe nhà | PTU `PTU-THU-KBAZ-G1/EPL` *Đã cấp* | CMP 59 `1368-CTR-261001-00072` ghi sổ | Nợ 1601 / Có 1011 | 250.000 LAK |
| Tạm ứng xe thuê | PTU `PTU-THU-KBAZ-T1/EPL` *Đã cấp* | CMP 59 `1368-CTR-261001-00073` ghi sổ | Nợ 4022 / Có 1011 | 4.247.000 LAK |
| Mục V garage | mục V *Đã chi* | CMP 60 `1368-CKH-261001-00067` ghi sổ | Nợ 614 / Có 1011 | 250.000 LAK |
| Hàng vào / ra kho bãi | lô 39,6 t → giao lấy 25 t → còn 14,6 t | không | (ngoài bảng) | — |
| POD | ký trên máy, `POD-THU-KBAZ-T1` | thấy trong chi tiết DO | — | — |
| Đề nghị thu | `PDT/2610/0001` 495,00 USD · `PDT/2610/0002` 753,35 USD — **Đã thu đủ** | SO `TK-20261001-000164`, `TK-20261001-000165` | — | 1.248,35 USD |
| Thu tiền khách | đọc lại: Đã thu đủ | TKN `4-TKN-1368-2-261001-0001` / `-0002` → CMR 17 `4-1368-TK-261001-00009` / `-00010` ghi sổ | Nợ 1021 / Có 1211 | 495,00 + 753,35 USD |
| Tất toán tài xế | bản chốt *Đã tất toán xong* (ບຸນມີ 10/2026) | CMP 60 `1368-CKH-261001-00068` ghi sổ | Nợ 1601 / Có 1011 | 960.000 LAK |
| Trả chủ xe | T1 *Đã trả chủ xe* | CMP 60 `1368-CKH-261001-00069` ghi sổ | Nợ 4022 / Có 1012 | 204,95 USD |
| Trả nhà cung cấp | công nợ chipping Lào giảm | CMP 60 `1368-CKH-261001-00070` ghi sổ | Nợ 4021 / Có 1021 | 620.000 LAK |
| Thuê xe (không qua tiền) | bút toán chờ `EPLLAO-thue_xe-ea99922a96ee` | (sau khi bật) chứng từ Tổng hợp DOTY 12 | Nợ 621 / Có 4022 | 741,00 USD |
| Ghi nợ NCC (không qua tiền) | bút toán chờ `EPLLAO-no_ncc-ea99922a96ee` | (sau khi bật) | Nợ 4022 / Có 4021 | 620.000 LAK |
| Quyết toán tạm ứng | bút toán chờ `EPLLAO-tat_toan-a6313dd63966:2026-10:99c2aab478f2` | (sau khi bật) | Nợ 625 / Có 1601 | 1.210.000 LAK |
| Hàng bán cho chủ xe | (chỉ khi có hàng quầy trừ khi trả chủ xe) | (sau khi bật) | Nợ 4022 / Có 707 | — |

---

## 5. Lỗi thường gặp → cách xử lý

| Thấy | Ở đâu | Vì sao | Làm gì |
|---|---|---|---|
| *Chọn xe trước khi lưu phiếu xuất xe.* / *Chọn tài xế …* | Lưu phiếu | phiếu trắng bị chặn | chọn xe, tài xế rồi **Lưu** |
| *Mục III: dòng … lấy từ kho chưa được cấp theo phiếu đề nghị …* | Ghi sổ mục III | thủ kho chưa cấp | Bãi in tờ, thủ kho **Cấp dầu** ở kho tạm, rồi ghi sổ |
| *Xe thuê: dầu lấy từ kho là xuất bán cho chủ xe … chưa có giá bán* | Kiểm mục III | thiếu giá bán | KT kho xăng dầu gõ **Giá bán cho chủ xe** |
| *Phiếu chi tạm ứng 1368-CTR-… bên hệ kế toán chưa ghi sổ — tài xế chưa nhận tiền …* | Tài xế **Xuất phát** | thủ quỹ QLSX chưa ghi sổ | thủ quỹ QLSX ghi sổ phiếu đó; tài xế bấm lại |
| *Tạm ứng chi ở hệ kế toán … Phiếu chi bên đó: …* (409 `CHI_O_KE_TOAN`) | Quỹ bấm chi mục IV / V / VI hoặc quét QR | từ 01/10 tiền chi ở QLSX | chi ở QLSX; trang điều xe **Cập nhật** |
| *Chưa sang được kế toán* (mục IV / V / VI, tờ PTU) | Phiếu xuất xe · Phiếu đề nghị chi | mất mạng, token hết hạn, thiếu mã TK, thiếu tiền tệ bên QLSX | rê chuột đọc câu lỗi; sửa xong KT Chi phí bấm **Gửi phiếu chi sang kế toán** |
| *Phiếu bị xoá bên kế toán* | như trên | ai đó xoá tay phiếu bên QLSX | **Gửi phiếu chi sang kế toán** lập phiếu mới; bên QLSX đừng xoá tay phiếu do trang điều xe tạo |
| *Lần gửi trước chưa được: …* | Phiếu đề nghị thu | QLSX từ chối SO (mã khách, tiền tệ…) | sửa theo câu báo, bấm lại **Tạo SO bên kế toán** (gói dựng lại theo số mới) |
| 401 / *token sai hoặc hết hạn* | mọi lời gọi sang QLSX | token tài khoản `tune` hết hạn (~10/10) | thay token trong `.env` hoặc đặt `QLSX_USERNAME` / `QLSX_PASSWORD` cho tự đăng nhập |
| 403 thân rỗng khi tạo SO | Tạo SO | token không nằm trong `LogisticsSalesPush:AllowedUserIds` | thêm UserId vào cấu hình API QLSX |
| *Bên công nợ đã tạo SO … — báo bên đó trước, rồi nhờ Sếp mở khoá.* | Mở khoá phiếu | đã có SO | đối soát với anh Tune, Sếp mở khoá |
| *Còn tạm ứng chưa chi xong ở hệ kế toán — chưa chốt được* | Tất toán | phiếu chi tạm ứng còn chờ | thủ quỹ QLSX ghi sổ phiếu đó trước |
| *Các phiếu chọn khác tiền thuê — mỗi đề nghị một loại tiền* | Trả chủ xe | tick phiếu USD lẫn LAK | lập hai đề nghị |
| Modal Vụ việc báo 503 / 502 | QLSX phiếu thu chi | thiếu `LogisticsSource:BaseUrl` / khoá bàn giao sai | đặt cấu hình; khoá do Sếp tạo ở trang điều xe (`POST /api/handover/tao-khoa`, hiện chưa có nút) |
| *Chưa bật gửi bút toán …* (409 `GUI_DANG_TAT`) | Bút toán chờ gửi | cờ tắt | đúng hiện trạng; bật theo mục 3 |
| 503 `LOGISTICS_JOURNAL_SCRIPT_REQUIRED` | API bút toán QLSX | chưa áp script | áp script (mục 3 bước 1) |
| Tìm chứng từ công nợ ở phiếu thu "Thu công nợ" ra 0 dòng | QLSX phiếu thu | công nợ SO nằm ở phân hệ Bán hàng | thu ở **Chi tiết công nợ khách hàng** → **Tạo phiếu thu** (bước 21) |

---

## 6. Lượt thử 01/10 — những điểm cần sửa / cần xem

1) **Lỗi trang điều xe — "Đã thu đủ" mà vẫn báo còn phải thu đủ số.** Sau bước 21, màn **Phiếu đề nghị thu** hiện hai DO **Đã thu đủ** nhưng ô **Còn phải thu** vẫn **27.463.700 LAK** (= đúng tổng cước hai DO); **Tổng quan** báo *27.5M LAK Chưa thu*.
   - Tái hiện: bước 20 → 21 (thu đủ một SO ở QLSX) → **Phiếu đề nghị thu** → **Cập nhật**.
   - Nguyên nhân: `customer-detail` bên QLSX giữ `RETK_MONEYPAID = 0` sau khi thu nợ (chỉ `RCTD_DEBTMONEY` về 0). Trang điều xe lấy "đã trả" từ `RETK_MONEYPAID` (`services/chi_tune.py` dòng 649) → `de_nghi_thu.ap_thu` ghi `thu_da_thu = 0` → `da_thu_lak = 0`, `con_lai_lak` = cả cước. Trạng thái thì đúng (theo còn nợ).
   - Hướng sửa (không phải tệp của em, em chưa sửa): còn nợ ≤ nửa xu thì đã thu = tiền − còn nợ; hoặc cộng `Collections` theo `OrderCode`.
2) **Thu tiền khách không đi "Thu công nợ" DOTY 15.** Thực tế thu nợ SO (TKN) sinh phiếu thu **DOTY 17 "Thu khác"**, Nợ 1021 / Có 1211. Anh Tune xem có đúng ý không (kịch bản đã viết theo thực tế).
3) **Bên QLSX — hộp Tạo phiếu thu cho SO USD:** ô **Tài khoản tiền thu** chỉ có *Tiền mặt nội tệ* / *Ngân hàng nội tệ*, tỷ giá gửi cứng 1 → phiếu thu 495 USD ghi BaseAmount 495 và vế tiền 1021 (ngân hàng Kíp). Anh Tune xem lại quy đổi và tài khoản ngoại tệ.
4) **Bên QLSX — mọi SO cùng mã phiếu bán** `RETK_CODE = "Demo EPL-2-261001000"` (SO 162, 164, 165), nên diễn giải phiếu thu *Thu khách nợ từ phiếu Demo EPL-2-261001000* giống hệt nhau, khó phân biệt.
5) **Giao diện trang điều xe (cho các agent UI):** mục I, II hiện *Đã kiểm · chờ ghi sổ* dù hai mục này không có bước ghi sổ; phiếu đã khoá mà `ketoan` vẫn thấy **Trả lại sửa** ở mục I; câu báo 409 `CHI_O_KE_TOAN` còn chữ ghi chú nội bộ *(chủ dự án 01/10)*.
6) **Kho tạm:** kho dầu Thà Bốc âm tồn sau lượt cấp (kho tạm không chặn cấp theo tồn — đúng như thiết kế cũ, nhưng nên có nhập kho trước khi demo).
7) **Chưa đi thật lượt này:** trừ hàng mua ở quầy khi trả chủ xe và bút toán 4022/707 (DB thử không có phiếu bán quầy chờ trừ của chủ xe này — bài `kiem/thu_tru_hang_quay.py` có sẵn); gửi bút toán tổng hợp (chờ áp script); thao tác trên WEB QLSX (em không có mật khẩu WEB — đã làm bằng đúng lời gọi WEB gửi).

---

## 7. Chứng từ thử THU-KBAZ đã ghi vào DB demo của anh Tune (5090)

Tất cả ngày 01/10/2026, chi nhánh 1368, đã **ghi sổ chính (12)** — em đóng vai thủ quỹ / kế toán bên QLSX. Giữ lại làm mẫu, hoặc anh Tune gỡ ghi sổ rồi xoá nếu muốn dọn.

| Chứng từ | DocumentId | Loại | Tham chiếu | Đối tượng | Định khoản · số tiền |
|---|---|---|---|---|---|
| `1368-CTR-261001-00072` | 81417 | CMP 59 Chi trước | `PTU-THU-KBAZ-G1/EPL` | `EPLTX-a6313dd63966` | Nợ 1601 / Có 1011 · 250.000 LAK |
| `1368-CTR-261001-00073` | 81421 | CMP 59 Chi trước | `PTU-THU-KBAZ-T1/EPL` | `EPLCX-0a073ea75bb3` | Nợ 4022 / Có 1011 · 4.247.000 LAK |
| `1368-CKH-261001-00067` | 81419 | CMP 60 Chi khác | `PCSC-V-THU-KBAZ-G1/EPL-1` | `EPLTX-a6313dd63966` | Nợ 614 / Có 1011 · 250.000 LAK |
| `1368-CKH-261001-00068` | 81427 | CMP 60 Chi khác (TT_CHI) | `TTX-202610-99c2aab4` | `EPLTX-a6313dd63966` | Nợ 1601 / Có 1011 · 960.000 LAK |
| `1368-CKH-261001-00069` | 81429 | CMP 60 Chi khác (trả chủ xe) | `TCX-261001104415-0a07` | `EPLCX-0a073ea75bb3` | Nợ 4022 / Có 1012 · 204,95 USD |
| `1368-CKH-261001-00070` | 81431 | CMP 60 Chi khác (trả NCC) | `TNCC-261001104417-804c` | `EPLNCC-804c0e8ff1d8` | Nợ 4021 / Có 1021 · 620.000 LAK |
| SO `TK-20261001-000164` | order 164 | SO + công nợ | DO `EPLLAO-37367086d283` | `EPLKH-0834a9e9606b` | 495,00 USD |
| SO `TK-20261001-000165` | order 165 | SO + công nợ | DO `EPLLAO-ea99922a96ee` | `EPLKH-0834a9e9606b` | 753,35 USD |
| `4-TKN-1368-2-261001-0001` | 86 | thu nợ TKN | SO 164 | `EPLKH-0834a9e9606b` | 495,00 USD |
| `4-TKN-1368-2-261001-0002` | 87 | thu nợ TKN | SO 165 | `EPLKH-0834a9e9606b` | 753,35 USD |
| `4-1368-TK-261001-00009` | 81423 | CMR 17 Thu khác | `4-TKN-1368-2-261001-0001` | `EPLKH-0834a9e9606b` | Nợ 1021 / Có 1211 · 495,00 USD |
| `4-1368-TK-261001-00010` | 81424 | CMR 17 Thu khác | `4-TKN-1368-2-261001-0002` | `EPLKH-0834a9e9606b` | Nợ 1021 / Có 1211 · 753,35 USD |

Bên trang điều xe máy thử 8011 (DB bản sao): phiếu `THU-KBAZ-G1/EPL` (id `37367086d283`) và `THU-KBAZ-T1/EPL` (id `ea99922a96ee`), tờ `PTU-…`, `PLNL-…`, `PDT/2610/0001`, `PDT/2610/0002`, bản chốt tất toán ທ້າວ ບຸນມີ kỳ 10/2026, đề nghị trả chủ xe `TCX-261001104415-0a07`, đề nghị trả NCC `TNCC-261001104417-804c`, ba bút toán chờ gửi. Kho tạm 8031: lô `THU-KBAZ-G1/EPL` (còn 14,6 t), hai lần xuất dầu kho Thà Bốc (120 + 200 lít).
