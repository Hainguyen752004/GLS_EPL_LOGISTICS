# Dữ liệu luồng của bộ demo EPL

Sinh bởi `backend/scripts/don_va_gieo_10_case_demo.py` lúc 09/09/2026 23:30 (giờ Việt Nam).

19 case dừng ở **những chặng khác nhau** của luồng, có chủ ý: một bộ dữ
liệu toàn chuyến đã đóng sẽ làm màn Điều phối, màn Theo dõi và hàng đợi
"cần xử lý" trống trơn — tức ba màn của người vận hành không có gì để xem.

Luồng: **Dữ liệu gốc → Báo giá → khách chấp nhận → Lệnh giao hàng (DO) →
Trip → Điều phối → Mốc thực thi → POD → Hoá đơn → Chi phí thực → Báo cáo.**
Không còn bước Đơn hàng (SO).

## 19 case

| Case | Dừng ở | Khách hàng | Tuyến | Loại xe | Giá thành | Cước/chuyến | Biên | DO | Chuyến | Sổ thu–chi |
|---|---|---|---|---|---|---|---|---|---|---|
| C01 | Hoàn tất | NIDEC | VSIP2A-CATLAI | TRACTOR40 | 1.714.540 đ | 2.486.000 đ | 31.0% | 1 | TRIP-7FCC99CA-C01 | 6 dòng · 6 dòng chờ acc code |
| C02 | Hoàn tất | SGNFOOD | SONGTHAN-CATLAI | 20FT | 745.520 đ | 1.118.000 đ | 33.3% | 1 | TRIP-7FCC99CA-C02 | 6 dòng · 6 dòng chờ acc code |
| C03 | Hoàn tất | POUYUEN | LONGAN-CAIMEP | TRACTOR40 | 2.409.255 đ | 3.421.600 đ | 29.6% | 1 | TRIP-7FCC99CA-C03 | 6 dòng · 6 dòng chờ acc code |
| C15 | Hoàn tất | POUYUEN | VSIP2A-CAIMEP | TRACTOR20 | 1.750.650 đ | 2.556.000 đ | 31.5% | 1 | TRIP-7FCC99CA-C15 | 6 dòng · 6 dòng chờ acc code |
| C16 | Hoàn tất | SGNFOOD | CATLAI-AMATA | REEFER5 | 1.117.900 đ | 1.789.000 đ | 37.5% | 1 | TRIP-7FCC99CA-C16 | 6 dòng · 6 dòng chờ acc code |
| C04 | Đang giao | COLGATE | VSIP2A-CAIMEP | TRACTOR20 | 1.750.650 đ | 2.591.000 đ | 32.4% | 1 | TRIP-7FCC99CA-C04 | — |
| C05 | Đang giao | UNILEVER | CATLAI-AMATA | TRUCK15 | 1.124.690 đ | 1.710.000 đ | 34.2% | 1 | TRIP-7FCC99CA-C05 | — |
| C17 | Đang giao | NIDEC | SONGTHAN-CATLAI | 20FT | 745.520 đ | 1.074.000 đ | 30.6% | 1 | TRIP-7FCC99CA-C17 | — |
| C19 | Đang giao | POUYUEN | LONGAN-CAIMEP | TRACTOR40 | 2.409.255 đ | 3.445.050 đ | 30.1% | 1 | TRIP-7FCC99CA-C19 | — |
| C18 | Đã đến · chờ POD | UNILEVER | SONGTHAN-CATLAI | 20FT | 745.520 đ | 1.118.000 đ | 33.3% | 1 | TRIP-7FCC99CA-C18 | — |
| C13 | Đã đến · chờ POD | SGNFOOD | VSIP2A-CATLAI | TRUCK10 | 855.440 đ | 1.283.000 đ | 33.3% | 1 | TRIP-7FCC99CA-C13 | — |
| C06 | Đã tách DO · chờ điều phối | NIDEC | SONGTHAN-CATLAI | TRACTOR20 | 1.277.310 đ | 1.878.000 đ | 32.0% | 2 | — | — |
| C07 | Đã tách DO · chờ điều phối | SGNFOOD | VSIP2A-CATLAI | TRUCK10 | 855.440 đ | 1.326.200 đ | 35.5% | 1 | — | — |
| C14 | Đã tách · một DO bị huỷ | UNILEVER | SONGTHAN-CATLAI | TRUCK15 | 1.040.694 đ | 1.561.000 đ | 33.3% | 2 | — | — |
| C08 | Đã gửi · chờ khách | COLGATE | CATLAI-AMATA | TRUCK15 | 1.124.690 đ | 1.687.000 đ | 33.3% | — | — | — |
| C11 | Khách từ chối | COLGATE | SONGTHAN-CATLAI | 20FT | 745.520 đ | 1.208.000 đ | 38.3% | — | — | — |
| C12 | Hết hạn | NIDEC | CATLAI-AMATA | TRUCK10 | 825.200 đ | 1.238.000 đ | 33.3% | — | — | — |
| C09 | Chờ duyệt nội bộ | POUYUEN | LONGAN-CAIMEP | TRACTOR40 | 2.409.255 đ | 2.650.000 đ | 9.1% | — | — | — |
| C10 | Nháp | UNILEVER | VSIP2A-CAIMEP | TRACTOR20 | 1.750.650 đ | 2.626.000 đ | 33.3% | — | — | — |

## Mở màn nào để xem case nào

| Màn hình | Case có dữ liệu | Xem được gì |
|---|---|---|
| Kinh doanh › Báo giá cước | cả 19 | dải số liệu, thẻ trạng thái đủ: nháp · chờ duyệt · chờ khách · từ chối · hết hạn · đã tách |
| Báo giá › phiếu chi tiết | C01 (đã tách) · C10 (nháp) · C11 (từ chối) · C12 (hết hạn) | đủ 8 mục: pallet, giá trị hàng, nhiệt độ (C16), bảo hiểm, niêm phong |
| Báo giá › chờ duyệt nội bộ | C09 | biên dưới ngưỡng thì nút chính thành "Gửi duyệt nội bộ" |
| Lệnh giao hàng › cần xử lý | C06 · C07 · C14 (một DO đã huỷ, một DO còn chờ) | hàng đợi DO chờ lập Trip |
| Bãi xe | C06 | phiếu bãi xe, nhãn QR đã in, đã quét vào bãi + qua cổng |
| Điều phối và thực thi | C04 · C05 · C13 | chuyến đã gán xe và tổ lái |
| Theo dõi và kiểm soát | C04 (có sự cố mở) · C05 · C13 (đã đến) | mốc check-in → nhận hàng → xuất bến → đến nơi |
| Hoàn tất giao hàng | C13 (chờ POD) · C01 · C02 · C03 · C15 · C16 | POD đã ký, giá cuối, phụ phí, **sổ thu–chi từng dòng** (Acc code chờ danh mục từ API bên công nợ) |
| Hồ sơ hoàn tất › phí của xe | C15 | dòng xăng dầu mang đơn giá ghi đè của xe DEMO-51C-129.03 (`rate_source = vehicle`) |
| Kế toán › hoá đơn | C01 · C02 · C03 · C15 · C16 | hoá đơn đã ghi sổ, bút toán 131/511 |
| Kế toán › Finance Cockpit | 5 bảng chi phí chờ duyệt | thẻ số liệu đếm toàn bảng từ máy chủ |
| Báo cáo doanh thu | C01 · C02 · C03 · C15 · C16 | doanh thu, giá thành, lãi gộp theo chuyến |
| Dữ liệu gốc › Công thức giá thành | 6 loại xe | mỗi khoản mục có ô chọn **Acc code** — danh mục chờ API bên công nợ (`EPL_ACC_CODE_API`) |
| Dữ liệu gốc › Phương tiện | DEMO-51C-129.03 (ghi đè dầu +12%) · DEMO-61H-112.34 (phiếu bảo dưỡng mở) | ghi đè giá thành theo xe, phiếu sửa chữa |
| Dữ liệu gốc › Tuyến đường | 5 tuyến DEMO | sơ đồ lộ trình vẽ bằng đường bộ thật |

## Ba điều cần biết khi demo

1. **Mốc thời gian neo vào lúc chạy tệp này.** Các chuyến "đang giao" có
   mốc xuất bến khoảng ba giờ trước, nên chúng hiện trên màn Theo dõi. Chạy
   lại tệp vào ngày khác thì bộ dữ liệu tự dịch theo ngày đó.
2. **Giá không viết cứng.** Đơn giá của từng case suy ra từ giá thành thật
   (công thức loại xe × số km đường bộ) nhân một hệ số. Sửa giá dầu ở màn
   Dữ liệu gốc rồi chạy lại là cả mười case đổi theo.
3. **C09 cố ý biên mỏng** (~9%) để thấy cửa duyệt nội bộ. Nó VẪN TRÊN giá
   thành — báo giá lỗ bị chặn hẳn, không vào được trạng thái chờ duyệt.

## Chạy lại bộ dữ liệu — HAI BƯỚC, hai người

```
python scripts/don_va_gieo_10_case_demo.py       # người vận hành
python scripts/duyet_chi_phi_bang_nguoi_khac.py  # trưởng phòng tài chính
```

Bước hai là một tệp riêng vì **quy tắc bốn mắt**: bảng chi phí thực đi qua
hai tay — người vận hành trình, trưởng phòng duyệt — và máy chủ chặn người
tạo tự duyệt bảng của mình. Bộ gieo chạy dưới một danh tính nên nó chỉ
trình được; nếu bỏ bước hai thì báo cáo doanh thu chỉ cộng phần chi phí
*vượt kế hoạch* đã duyệt, không cộng giá thành kế hoạch, và lãi gộp hiện
cao giả tạo.

Đây cũng là một thứ đáng cho người xem thấy: hệ thống không cho một người
vừa nhập vừa xác nhận con số của chính mình.

## Ba con số của báo cáo doanh thu

Báo cáo hiện **ba** cột chi phí, không gộp thành một:

| Cột | Nghĩa |
|---|---|
| Giá thành kế hoạch | công thức loại xe × số km đường bộ, đúng con số màn Báo giá hiện |
| Chênh lệch đã duyệt | phần chi phí thực vượt kế hoạch, đã qua trưởng phòng |
| Giá thành | tổng hai cột trên — mẫu số của lãi gộp |

Gộp thành một cột thì người đọc không biết chuyến vượt kế hoạch bao nhiêu,
mà đó chính là câu hỏi của người quản lý đội xe.
