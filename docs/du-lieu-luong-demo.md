# Dữ liệu luồng của bộ demo EPL

Sinh bởi `backend/scripts/don_va_gieo_10_case_demo.py` lúc 09/09/2026 10:15 (giờ Việt Nam).

Mười case dừng ở **những chặng khác nhau** của luồng, có chủ ý: một bộ dữ
liệu toàn chuyến đã đóng sẽ làm màn Điều phối, màn Theo dõi và hàng đợi
"cần xử lý" trống trơn — tức ba màn của người vận hành không có gì để xem.

Luồng: **Dữ liệu gốc → Báo giá → khách chấp nhận → Lệnh giao hàng (DO) →
Trip → Điều phối → Mốc thực thi → POD → Hoá đơn → Chi phí thực → Báo cáo.**
Không còn bước Đơn hàng (SO).

## Mười case

| Case | Dừng ở | Khách hàng | Tuyến | Loại xe | Giá thành | Cước/chuyến | Biên | DO | Chuyến |
|---|---|---|---|---|---|---|---|---|---|
| C01 | Hoàn tất | NIDEC | VSIP2A-CATLAI | TRACTOR40 | 1.714.540 đ | 2.486.000 đ | 31.0% | 2 | TRIP-22EEE3A1-C01 |
| C02 | Hoàn tất | SGNFOOD | SONGTHAN-CATLAI | 20FT | 745.520 đ | 1.118.000 đ | 33.3% | 2 | TRIP-22EEE3A1-C02 |
| C03 | Hoàn tất | POUYUEN | LONGAN-CAIMEP | TRACTOR40 | 2.409.255 đ | 3.421.600 đ | 29.6% | 2 | TRIP-22EEE3A1-C03 |
| C04 | Đang giao | COLGATE | VSIP2A-CAIMEP | TRACTOR20 | 1.750.650 đ | 2.591.000 đ | 32.4% | 2 | TRIP-22EEE3A1-C04 |
| C05 | Đang giao | UNILEVER | CATLAI-AMATA | TRUCK15 | 1.124.690 đ | 1.710.000 đ | 34.2% | 2 | TRIP-22EEE3A1-C05 |
| C06 | Đã tách DO · chờ điều phối | NIDEC | SONGTHAN-CATLAI | 20FT | 745.520 đ | 1.096.000 đ | 32.0% | 3 | — |
| C07 | Đã tách DO · chờ điều phối | SGNFOOD | VSIP2A-CATLAI | TRUCK10 | 855.440 đ | 1.326.200 đ | 35.5% | 2 | — |
| C08 | Đã gửi · chờ khách | COLGATE | CATLAI-AMATA | TRUCK15 | 1.124.690 đ | 1.687.000 đ | 33.3% | — | — |
| C09 | Chờ duyệt nội bộ | POUYUEN | LONGAN-CAIMEP | TRACTOR40 | 2.409.255 đ | 2.650.000 đ | 9.1% | — | — |
| C10 | Nháp | UNILEVER | VSIP2A-CAIMEP | TRACTOR20 | 1.750.650 đ | 2.626.000 đ | 33.3% | — | — |

## Mở màn nào để xem case nào

| Màn hình | Case có dữ liệu | Xem được gì |
|---|---|---|
| Kinh doanh › Báo giá cước | cả 10 | dải 6 số liệu, 6 thẻ trạng thái, bảng 9 cột |
| Báo giá › phiếu chi tiết | C01 (đã tách) · C10 (nháp) | 8 mục, cột phải, thanh đáy đổi nút theo trạng thái |
| Báo giá › chờ duyệt nội bộ | C09 | biên dưới ngưỡng thì nút chính thành "Gửi duyệt nội bộ" |
| Lệnh giao hàng › cần xử lý | C06 · C07 | hàng đợi DO chờ lập Trip |
| Điều phối và thực thi | C04 · C05 | chuyến đã gán xe và tổ lái |
| Theo dõi và kiểm soát | C04 · C05 | mốc check-in → nhận hàng → xuất bến |
| Hoàn tất giao hàng | C01 · C02 · C03 | POD đã ký, giá cuối, phụ phí |
| Kế toán › hoá đơn | C01 · C02 · C03 | hoá đơn đã ghi sổ, bút toán 131/511 |
| Báo cáo doanh thu | C01 · C02 · C03 | doanh thu, giá thành, lãi gộp theo chuyến |
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
