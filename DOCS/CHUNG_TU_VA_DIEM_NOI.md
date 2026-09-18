# Sổ chứng từ và điểm nối với module kế toán

Tài liệu này trả lời hai câu: **ai nhập ô nào trên phiếu xuất xe** và **mỗi bước sinh ra tờ chứng từ gì**, để module kế toán (anh Khang) nối vào tạo phiếu thu, phiếu chi, phiếu nhập kho, phiếu xuất kho. Bản đầy đủ có bấm được nằm ở màn **Quy trình** trong ứng dụng; bản này để gửi đi.

Nguyên tắc giữ xuyên suốt: bên vận hành **không có sổ kế toán**. Hệ này chỉ ghi lại "tờ nào sinh ra ở đâu, của ai, bao nhiêu tiền", kèm hai vế định khoản **gợi ý** theo đúng quy trình họ viết. Ghi sổ, cộng sổ, công nợ là việc của module kế toán.

## 1. Ai nhập ô nào (đã chốt)

| Mục trên phiếu | Admin Thà Bốc nhập | Bãi không thấy | Kế toán Viêng Chăn nhập hoặc sửa | Vai khác |
|---|---|---|---|---|
| I. Xe | loại xe, số xe, hai biển, tài xế, ngày, km đi | | kiểm | |
| I. Km về ước tính | máy tự tính = km đi + km tuyến, chỉ đọc | | đối với km về thật | |
| II. Vận chuyển | tuyến, khách, loại hàng, số phiếu quặng, **cân đầu**, **cân cuối** (khi xe về) | đơn giá USD/tấn, thành tiền, quy đổi LAK, khấu trừ xe liên kết, tổng kết | đơn giá, giá thuê xe liên kết, phí 2 %, ngưỡng tấn; kiểm cân | Kế toán doanh thu: hoá đơn, thu tiền |
| III. Nhiên liệu | số lít, nơi đổ | đơn giá, tiền tệ, thành tiền, mã TK | đơn giá dầu nếu kho chưa điền | Kho nhiên liệu kiểm và ghi sổ; thủ kho cấp theo phiếu lĩnh |
| IV. Đi đường | khoản mục, số lượng, đơn giá (tiền mặt cho tài xế) | | kiểm, ghi sổ | Quỹ chi theo phiếu tạm ứng |
| V. Sửa chữa | duyệt báo hỏng của tài xế: nguồn kho hay mua, phụ tùng, số tiền | | kiểm, ghi sổ | Tiền mặt lẻ Thà Bốc chi |
| VI. Khác | duyệt phát sinh | | kiểm, ghi sổ | Quỹ chi |

Hai điểm em chốt khác với ý đầu của anh, kèm lý do:

- **Cân đầu và cân cuối để Bãi nhập**, không ẩn. Tờ phiếu quặng của khách nằm ở bãi lúc bốc hàng; xe về cũng về bãi. Kế toán ở Viêng Chăn không cầm tờ đó nên chỉ kiểm lại con số. Cái Bãi không nên thấy là **tiền**: đơn giá, thành tiền, quy đổi, khấu trừ. Những ô này đã ẩn với vai Bãi bằng lớp `px-an-tien`.
- **Km về** có hai ô: **ước tính** (tự tính từ tuyến, chỉ đọc, hiện ngay lúc mở phiếu) và **thật** (Bãi nhập khi xe về). Kế toán đối hai số này ở bước kiểm lại; lệch nhiều là có chuyện.

## 2. Chứng từ sinh ra ở từng bước

Mỗi tờ có số riêng dạng `LOAI/YYMM/0001`, đếm theo loại và theo tháng. Một nguồn chỉ sinh **một** tờ (khoá `loai + nguon_bang + nguon_id`), gọi lại không sinh trùng. Vế "tiền mặt · ngân hàng" **không có mã** vì quy trình của họ không ghi; bên kế toán cấp.

| Mã | Tên | Sinh ở bước | Ai làm | Nợ | Có | Ghi chú |
|---|---|---|---|---|---|---|
| `DO` | Phiếu xuất xe | 1. Bãi mở phiếu | Bãi | | | Hồ sơ của cả chuyến, mọi tờ khác treo vào |
| `PLNL` | Phiếu lĩnh nhiên liệu (QR) | 3. Bãi lập | Bãi in, tài xế cầm | | | Số lượng tính bằng lít, chưa ra hàng nên chưa định khoản |
| `PTU` | Phiếu tạm ứng đi đường (QR) | 4. Bãi lập | Bãi in, tài xế cầm | | | Chưa ra tiền nên chưa định khoản |
| `PXK_NL` | Phiếu xuất kho nhiên liệu | 7. Thủ kho cấp; hoặc 6. kế toán kho ghi sổ | Thủ kho / kế toán kho | 625 (xe nhà) · 4022 (xe liên kết) | 371 | Trừ tồn ngay |
| `PC_TU` | Phiếu chi tạm ứng | 9. Quỹ quét QR chi tiền | Quỹ | 625 / 4022 | tiền mặt | Mục IV phải "đã ghi sổ" trước |
| `PXK_PT` | Phiếu xuất kho phụ tùng | 12. Duyệt sửa xe lấy kho; hoặc Kho phụ tùng xuất tay | Bãi / kế toán kho | 614 | 371 | Trừ tồn ngay |
| `PC_SC` | Phiếu chi sửa chữa · chi khác | 16. Quỹ chi mục V hoặc VI | Tiền mặt lẻ Thà Bốc | 614 / 625 | tiền mặt | Một tờ cho cả mục, từng dòng nằm trong `payload.lines`; dòng lấy kho không tính (đã có PXK_PT) |
| `HD` | Hoá đơn vận chuyển | 17. Kế toán doanh thu xuất hoá đơn | Kế toán doanh thu | 1211 | 70 | Tiền USD, kèm quy đổi LAK theo tỷ giá trên phiếu |
| `PT` | Phiếu thu tiền khách | 17. Đổi trạng thái sang Đã thanh toán | Kế toán doanh thu | tiền mặt | 1211 | |
| `TT_CHI` | Tất toán tài xế · chi bù | 19. Chốt kỳ, chi thật > ứng | Kế toán, quỹ | 625 | tiền mặt | |
| `TT_THU` | Tất toán tài xế · thu hoàn | 19. Chốt kỳ, chi thật < ứng | Kế toán, quỹ | tiền mặt | 625 | |
| `PNK_NL` | Phiếu nhập kho nhiên liệu | Kho nhiên liệu, nhập dầu | Kế toán kho | 371 | 402 | Ngoài chuyến |
| `PNK_PT` | Phiếu nhập kho phụ tùng | Kho phụ tùng, nhập tay | Kế toán kho | 371 | 402 | Ngoài chuyến |
| `PC_NCC` | Phiếu chi trả nhà cung cấp | Nhà cung cấp, trả theo đợt | Kế toán, quỹ | 402 | tiền mặt | Ngoài chuyến |
| `PC_CX` | Phiếu chi trả chủ xe liên kết | 18. Quỹ bấm Trả chủ xe | Quỹ | 4022 | tiền mặt | Phiếu phải đã khoá; mỗi phiếu trả một lần |
| `PXK_BAN` | Phiếu xuất kho bán hàng | 20. Lập phiếu bán | Kế toán, kho | giá vốn | 371 | Giá vốn hàng xuất; vế Nợ chờ mã của bên kế toán |
| `HD_BAN` | Hoá đơn bán hàng | 20. Lập phiếu bán | Kế toán | 1211 | 70 | Sinh cùng lúc với phiếu xuất kho bán |
| `PT_BAN` | Phiếu thu bán hàng | 20. Bấm Đã thu | Doanh thu, quỹ | tiền mặt | 1211 | |

## 2b. Bước 14 — kiểm lại toàn phiếu rồi khoá

Xe về rồi, kế toán Viêng Chăn bấm **Khoá phiếu** trên phiếu xuất xe. Máy rà một lượt
(`GET /api/trips/{id}/kiem-lai`) và liệt kê những điểm cần nhìn:

- km về thật lệch quá 10 % so với km ước tính (km đi + km tuyến);
- hao hụt vượt 1,5 %;
- thiếu cân cuối, thiếu km về;
- chưa đính kèm phiếu quặng của khách;
- mục nào có dòng chi mà chưa kiểm.

Đây chỉ là **cảnh báo**, không chặn: số thật đôi khi lệch thật. Kế toán đọc rồi xác nhận khoá
(`POST /api/trips/{id}/khoa` với `{"xac_nhan": true}`).

Khoá rồi thì: Bãi và tài xế **không ghi thêm gì** (sửa phiếu, đổi trạng thái, lập phiếu lĩnh, đính kèm,
xoá phiếu đều bị chặn với mã `DA_KHOA`); kế toán, quỹ, kho nhiên liệu vẫn kiểm, ghi sổ và chi tiếp.
**Chỉ phiếu đã khoá mới xuất được hoá đơn**, và **chỉ phiếu đã khoá mới trả được chủ xe liên kết**.
Kế toán mở khoá lại được, trừ khi đã xuất hoá đơn.

## 2c. Tệp đính kèm (phiếu quặng của khách)

Bãi chụp phiếu quặng lúc bốc hàng và đưa lên ngay trên phiếu xuất xe, ô **Phiếu quặng đính kèm**
(ngay dưới số phiếu quặng). Nhận ảnh JPG, PNG, WEBP, HEIC hoặc PDF, tối đa 8 MB một tệp.
Chỉ Bãi và kế toán được đưa lên; tài xế không. Người đưa lên hoặc kế toán xoá được, và phiếu đã khoá
thì không đổi tệp nữa.

| Việc | Gọi |
|---|---|
| Danh sách tệp của phiếu | `GET /api/trips/{id}/tep` |
| Đưa tệp lên | `POST /api/trips/{id}/tep` (multipart: `tep`, `kind`, `note`) |
| Mở tệp | `GET /api/tep/{id}` — thẻ `<img>` không gửi được header nên nhận phiên qua `?tk=…`; không có phiên là 401 |
| Xoá tệp | `DELETE /api/tep/{id}` |

Tệp nằm trên đĩa máy chủ, thư mục `backend/tep/<id phiếu>/` (đổi được bằng biến môi trường
`EPL_LAO_TEP`). Thư mục này **không đẩy lên git**.

## 3. Cách module kế toán kéo về

Tất cả đều cần đăng nhập bằng vai kế toán (`acct` KT Thu/Chi VC, `expacct` KT Chi phí VC, `rev`, `treasury`, `cash`, `fuel`, `depot`, `admin`). Vai Bãi và tài xế bị từ chối vì đây là số kế toán.

| Việc | Gọi |
|---|---|
| Danh mục loại và định khoản mặc định | `GET /api/chung-tu/loai` |
| Kéo tờ chưa đối chiếu | `GET /api/chung-tu?chua_day=1` |
| Lọc | `?loai=PC_TU,PC_SC&tu=2026-08-01&den=2026-08-31&trip_id=…&doi_tuong=tai_xe&limit=500` |
| Một tờ | `GET /api/chung-tu/{id}` |
| Báo đã nhận | `POST /api/chung-tu/{id}/da-day` (thân `{"da_day": false}` để mở lại) |

Một tờ trả về có dạng:

```json
{
  "id": "…", "loai": "PC_TU", "loai_ten": "Phiếu chi tạm ứng", "loai_ten_lo": "ໃບຈ່າຍເງິນລ່ວງໜ້າ",
  "so": "PC_TU/2608/0003", "ngay": "2026-08-23",
  "trip_id": "…", "trip_doc_no": "T4-0432-08/EPL",
  "doi_tuong_loai": "tai_xe", "doi_tuong_ten": "ທ້າວ ບຸນມີ",
  "tien": 640000, "tien_te": "LAK", "tien_lak": 640000,
  "no": "625", "no_ten": "Chi phí vận chuyển",
  "co": null, "co_ten": "Tiền mặt · ngân hàng (mã do bên kế toán cấp)",
  "mo_ta": "Chi tạm ứng đi đường theo PTU-T4-0432-08/EPL",
  "nguon_bang": "vouchers", "nguon_id": "…", "by_user": "ທ້າວ ບຸນມາ (Bounma)",
  "ts": "2026-09-17T09:12:33", "da_day": false, "day_luc": null,
  "payload": { "voucher_doc_no": "PTU-T4-0432-08/EPL", "driver_id": "…", "truck_no": "342" }
}
```

`doi_tuong_loai` nhận: `khach`, `ncc`, `tai_xe`, `kho`, `chu_xe`. `tien_te` nhận `LAK`, `USD`, `THB`, `VND` và `L` (lít, chỉ ở `PLNL`). `tien_lak` đã quy đổi theo tỷ giá **ghi trên phiếu xuất xe**, không lấy tỷ giá hôm nay.

Khi nguồn bị xoá (bỏ chốt tất toán, xoá phiếu thử, xoá dòng kho) thì tờ **chưa đối chiếu** của nó bị rút theo; tờ đã đối chiếu thì giữ để hai bên còn đối được.

## 4. Mã còn thiếu, cần anh Khang xác nhận

Danh mục Acc code bên anh Khang hiện có `402`, `614`, `625`, `1211`, `70`, `137`. Quy trình của họ dùng thêm:

| Trong quy trình họ viết | Bên mình đang gợi ý | Cần chốt |
|---|---|---|
| `…/37`, `…/371` (kho) | `371`, ghi rõ "danh mục anh Khang chưa có" | Kho là `371` hay `137`? |
| `4021`, `402` (nhà cung cấp) | `402` | Có tách `4021` không? |
| `4022` (xe liên kết) | `4022` | Chưa có trong danh mục |
| tiền mặt, ngân hàng | để trống mã | Bên kế toán cấp mã, hoặc cho API trả về |
| giá vốn hàng bán (tờ `PXK_BAN`) | để trống mã | Bên kế toán cấp mã |

Chỗ nào chốt khác thì chỉ sửa một bảng `dinh_khoan()` trong `backend/app/services/chung_tu.py`; các tờ đã sinh không đổi (định khoản đã khoá vào tờ lúc sinh), nên cần chốt sớm trước khi chạy thật.

## 5. Bán phụ tùng và xăng dầu (bước 20)

Đây là việc **ngoài chuyến**: EPL bán hàng cho người ngoài, không phải chi cho một phiếu xuất xe.
Màn **Bán hàng** (nhóm Mô-đun kho). Kế toán, kế toán doanh thu hoặc kho nhiên liệu lập phiếu:
chọn khách (hoặc gõ tên người mua), tiền tệ, rồi thêm dòng — **phụ tùng** (trừ tồn ngay) hoặc
**dầu kho** (ghi một dòng xuất trong sổ kho nhiên liệu). Lưu phiếu là xuất kho và hoá đơn bán ra cùng lúc.
Kế toán doanh thu hoặc quỹ bấm **Đã thu** thì sinh phiếu thu. Chưa thu thì còn bỏ phiếu được:
hàng về kho, tờ chứng từ chưa đối chiếu rút theo.

| Việc | Gọi |
|---|---|
| Danh sách phiếu bán | `GET /api/ban-hang?thang=YYYY-MM` |
| Lập phiếu | `POST /api/ban-hang` |
| Ghi đã thu | `POST /api/ban-hang/{id}/thu` |
| Bỏ phiếu chưa thu | `DELETE /api/ban-hang/{id}` |

Giá vốn: phụ tùng lấy đơn giá trong danh mục kho; dầu lấy đơn giá **lần nhập gần nhất**
(họ không tính bình quân gia quyền). Giá vốn nằm ở tờ `PXK_BAN`, giá bán ở tờ `HD_BAN`,
nên bên kế toán tự tính được lãi gộp mà không cần bên mình cộng sổ.

## 6. Còn để lại

- Bảng giá bán riêng cho phụ tùng (hiện gõ tay đơn giá từng lần, mặc định lấy giá kho).
- Bán chịu theo công nợ khách (hiện một phiếu chỉ có hai trạng thái: đã lập, đã thu).
- Mã tiền mặt, mã giá vốn hàng bán chờ bên anh Khang cấp (mục 4).
