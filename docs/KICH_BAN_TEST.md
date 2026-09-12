# EPL Trợ lý — Kịch bản kiểm thử

Bộ kịch bản để chạy thử **toàn bộ** trợ lý trước khi demo: chuẩn bị máy chủ, từng bước bấm, bộ câu hỏi ba ngôn ngữ, và cách chấm một câu trả lời là đạt hay không.

Tài liệu này đi cùng bảng **CAU_HOI_TEST_3_NGON_NGU.xlsx** — 73 câu hỏi, mỗi câu có sẵn bản tiếng Việt, tiếng Anh và tiếng Lào để chép thẳng vào ô chat.

Soạn ngày 12/09/2026 · Trợ lý dùng Gemini 2.5 Flash · Bộ kiểm mã nguồn: 16/16 đạt

---

## 1. Trợ lý làm được gì, và KHÔNG làm được gì

**Bản này CHỈ ĐỌC.** Trợ lý trả lời được mọi câu hỏi về dữ liệu đang có trong hệ EPL, nhưng **không tạo, không sửa, không xoá, không điều phối** bất cứ thứ gì. Nhờ nó làm nghiệp vụ thì nó từ chối và chỉ đúng màn hình để tự làm.

| Trợ lý làm được | Trợ lý KHÔNG làm được (phải vào hệ EPL) |
|---|---|
| Đọc và tóm tắt tình hình hôm nay | Điều phối xe và tài xế |
| Tra lệnh giao hàng, chuyến, sự cố, báo giá, cơ hội | Lập, gửi, duyệt báo giá |
| Tra xe, tài xế, bằng lái, giấy tờ, lịch ca | Tạo hoặc xoá lệnh giao hàng |
| Tra khách hàng, tuyến, tỷ giá | Ký nhận POD, chốt giá, hoàn tất giao hàng |
| Đọc doanh thu, giá thành, lợi nhuận, hồ sơ hoàn tất | Ghi sổ kinh doanh sang kế toán |
| So sánh, đếm, xếp hạng trên dữ liệu thật | Ghi mốc, báo sự cố, sửa dữ liệu gốc |

> Vì sao dừng ở đây: để trợ lý tự ghi vào hệ thống thì một câu đọc sai ngữ cảnh là một chuyến xe điều nhầm. Bước hành động cần một lớp xác nhận riêng — người bấm duyệt trước khi ghi — và đó là việc của pha sau, không phải bản này.

Nhóm câu **K** trong bảng Excel là để kiểm đúng ranh giới này. Nếu một câu nhóm K mà trợ lý nhận lời làm, đó là lỗi nặng nhất của cả bộ kiểm.

## 2. Chuẩn bị — ba máy chủ

Trợ lý không có cơ sở dữ liệu riêng; nó đọc API của hệ EPL. Nên phải bật EPL trước.

| Máy chủ | Thư mục | Lệnh | Địa chỉ |
|---|---|---|---|
| Hệ EPL (bắt buộc) | `EPL_System` | `python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8001 --no-access-log` | http://localhost:8001 |
| Trợ lý | `EPL_TroLy` | `chay.bat` hoặc `python chay.py` | http://localhost:8090 |
| Trang tài xế (nếu cần) | `EPL_TaiXe` | `python chay.py --api http://127.0.0.1:8001 --cong 8099` | http://localhost:8099 |

Trợ lý tự đọc `GEMINI_API_KEY_GT` và `EPL_TMS_API_TOKEN` từ `EPL_System\.env`. Hai khoá này nằm ở máy chủ, trình duyệt không bao giờ thấy.

**Kiểm trước khi thử:** mở `http://localhost:8090/suc-khoe`, phải thấy `gemini_co_khoa: true`, `epl_ok: true`, `so_cong_cu: 21`.

Muốn trợ lý đọc máy chủ đã host thay vì máy mình: `python chay.py --api http://senvangsolutions.com:1506`.

## 3. Cách chấm một câu trả lời

Chấm theo bốn điều, thiếu một là **Không đạt**:

1. **Con số đúng.** Mở màn hình gốc trong hệ EPL đối chiếu. Cột *Cần thấy gì* trong bảng Excel nói rõ phải thấy gì.
2. **Không bịa.** Mọi mã lệnh, tên khách, tên tài xế, biển số, số tiền phải có thật. Một cái tên không tồn tại là Không đạt, kể cả khi phần còn lại đúng.
3. **Tiền đúng đơn vị.** Số tiền phải kèm mã tiền tệ **của chính chứng từ đó** — phiếu LAK phải hiện LAK. Quy đổi thầm sang VNĐ là Không đạt.
4. **Trọn một ngôn ngữ.** Chọn tiếng Lào thì cả câu tiếng Lào, không chen câu tiếng Việt.

Dưới mỗi câu trả lời có dòng **Đã xem: …** liệt kê trợ lý đã tra những gì, và thời gian chạy. Dùng dòng đó để biết nó thật sự đi đọc dữ liệu hay trả lời từ trí nhớ.

## 4. Kịch bản theo bước


### Chuẩn bị

| Mã | Bước | Cách làm | Kết quả mong đợi |
|---|---|---|---|
| S1 | Bật máy chủ EPL | Ở D:\Demo_Lao\EPL_System chạy: python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8001 --no-access-log | Log hiện 'Application startup complete'. Mở http://localhost:8001 thấy hệ EPL. |
| S2 | Bật máy chủ trợ lý | Ở D:\Demo_Lao\EPL_TroLy bấm đúp chay.bat (hoặc: python chay.py) | Cửa sổ hiện: Trang http://localhost:8090 · API EPL có token · Gemini có khóa · Công cụ 21 · Giám sát mỗi 15 giây. |
| S3 | Kiểm sức khoẻ | Mở http://localhost:8090/suc-khoe | gemini_co_khoa: true · epl_ok: true · so_cong_cu: 21. Nếu epl_ok false thì máy chủ EPL chưa bật. |

### Giao diện

| Mã | Bước | Cách làm | Kết quả mong đợi |
|---|---|---|---|
| S4 | Mở trang, nhìn màn chào | Mở http://localhost:8090 | Logo EPL, lời chào theo buổi, 6 gợi ý câu hỏi, ô nhập ở giữa. KHÔNG có dải đỏ báo lỗi ở đầu trang. |
| S5 | Đổi ba ngôn ngữ | Bấm lần lượt Tiếng Việt · English · ລາວ ở góc dưới trái | Toàn bộ nhãn, lời chào và 6 gợi ý đổi theo. Chữ Lào hiện đúng dấu, không ô vuông. |
| S6 | Đổi sáng/tối | Bấm 'Giao diện' ở góc dưới trái | Nền đổi sáng ↔ tối, chữ vẫn đọc được, ghi nhớ khi tải lại trang. |
| S7 | Trò chuyện mới và lịch sử | Hỏi 1 câu → bấm 'Trò chuyện mới' → hỏi câu khác → bấm lại cuộc cũ ở thanh bên | Hai cuộc nằm riêng ở thanh bên; mở lại cuộc cũ thấy nguyên nội dung. Tải lại trang (F5) vẫn còn. |
| S8 | Xoá một cuộc | Rê chuột lên một cuộc trong thanh bên, bấm dấu × | Cuộc đó biến mất, các cuộc khác giữ nguyên. |

### Tốc độ

| Mã | Bước | Cách làm | Kết quả mong đợi |
|---|---|---|---|
| S9 | Xem stream khi hỏi | Hỏi câu A1 và nhìn đồng hồ | Trong ~2 giây hiện chip 'Đang tra: Tổng quan hôm nay'; chữ bắt đầu chảy trước giây thứ 5; xong trong khoảng 5–9 giây. Không ngồi nhìn ba chấm suốt. |
| S10 | Câu nối tiếp nhanh hơn | Hỏi tiếp J1 ngay sau A1 | Xong trong ~2–3 giây và KHÔNG có chip công cụ nào. |

### Thông báo

| Mã | Bước | Cách làm | Kết quả mong đợi |
|---|---|---|---|
| S11 | Chuông khi có báo giá mới | Mở màn Báo giá của hệ EPL, tạo một báo giá nháp mới | Trong vòng ~15 giây: chuông góc phải hiện số, một toast trượt ra ghi 'Báo giá mới QT-… cho <khách> · giá …'. |
| S12 | Chuông khi có lệnh mới | Trên hệ EPL, cho khách chấp nhận một báo giá (sinh DO tự động) | Thông báo 'Lệnh giao hàng mới DO-… cho <khách>'. |
| S13 | Chuông khi xe xuất phát | Trên màn Điều phối, chốt điều phối và xuất bến một chuyến | Thông báo 'Xe <biển số> đã xuất phát — chuyến TRIP-…'. |
| S14 | Chuông khi xe báo xong | Hoàn tất giao hàng cho một lệnh (ký POD, chốt giá) | Thông báo 'Lệnh … đã giao xong cho <khách>' hoặc 'Xe … đã báo hoàn tất chuyến …'. |
| S15 | Bảng thông báo và đánh dấu đã đọc | Bấm chuông → xem danh sách → bấm 'Đánh dấu đã đọc' | Danh sách có giờ, biểu tượng theo loại; bấm xong thì số trên chuông biến mất. |
| S16 | Hỏi thẳng từ thông báo | Trong bảng thông báo, bấm 'Hỏi em về việc này' | Câu hỏi soạn sẵn về đúng mã đó được gửi vào chat và trả lời được. |
| S17 | Báo khi ở tab khác | Tích 'Báo cả khi đang ở tab khác', cho phép quyền, chuyển sang tab khác rồi tạo một báo giá | Trình duyệt bật thông báo hệ thống ngoài tab. |

### Ranh giới

| Mã | Bước | Cách làm | Kết quả mong đợi |
|---|---|---|---|
| S18 | Chạy cả nhóm K | Hỏi lần lượt K1 → K6 | Cả sáu đều bị từ chối đúng cách và chỉ đúng màn hình. K6 nói không tìm thấy, không bịa. |

### Chịu lỗi

| Mã | Bước | Cách làm | Kết quả mong đợi |
|---|---|---|---|
| S19 | Tắt máy chủ EPL giữa chừng | Tắt cửa sổ chạy EPL (cổng 8001), rồi hỏi một câu bất kỳ | Đầu trang hiện 'Không nối được hệ thống EPL'; câu trả lời nói không lấy được dữ liệu — KHÔNG bịa số. Bật lại EPL thì hỏi lại chạy bình thường. |
| S20 | Bấm Thử lại | Khi một câu bị lỗi, bấm nút 'Thử lại' dưới câu đó | Hỏi lại đúng câu vừa rồi, không phải gõ lại. |

### Điện thoại

| Mã | Bước | Cách làm | Kết quả mong đợi |
|---|---|---|---|
| S21 | Mở trên điện thoại | Trên điện thoại cùng Wi-Fi, mở http://<IP máy>:8090 | Thanh bên thu vào, có nút ☰ để mở; ô nhập và chuông vẫn bấm được; chữ không tràn ngang. |

## 5. Bộ câu hỏi — 73 câu, mỗi câu ba ngôn ngữ

Nội dung đầy đủ nằm trong **CAU_HOI_TEST_3_NGON_NGU.xlsx** (trang *Câu hỏi 3 ngôn ngữ*). Bảng dưới đây là bản đồ các nhóm để biết đang phủ những gì.

| Nhóm | Số câu | Nội dung |
|---|---|---|
| Tổng quan | 5 | Câu hỏi mở màn — thứ người quản lý hỏi đầu ngày. |
| Lệnh giao hàng | 8 | DO: quá hạn, gần trễ, chờ xe, chi tiết một lệnh. |
| Chuyến | 7 | Chuyến đang chạy, tài xế, mốc, POD, lệch tuyến. |
| Sự cố | 4 | Sự cố trên đường: loại, mức độ, vị trí. |
| Báo giá | 8 | Báo giá cước: trạng thái, hạn, biên lợi nhuận, tiền tệ. |
| Cơ hội | 3 | CRM: cơ hội theo giai đoạn, lý do mất. |
| Khách hàng | 4 | Danh mục khách và hồ sơ 360°. |
| Đội xe | 6 | Xe, giấy tờ, bảo dưỡng. |
| Tài xế | 2 | Tài xế, bằng lái, ca làm việc. |
| Tuyến | 3 | Tuyến đường và chặng. |
| Tỷ giá | 1 | Bốn tiền tệ và tỷ giá. |
| Doanh thu | 3 | Báo cáo doanh thu, giá thành, lợi nhuận. |
| Hoàn tất | 4 | Hồ sơ đã ký POD, chốt giá, chờ bàn giao kế toán. |
| Trí nhớ | 5 | Câu nối tiếp — kiểm trợ lý có nhớ dữ liệu lượt trước không. |
| Ranh giới | 6 | Câu PHẢI BỊ TỪ CHỐI: bản này chỉ đọc, không làm nghiệp vụ. |
| Ngôn ngữ | 2 | Ba ngôn ngữ và cách viết số. |
| Tiền tệ | 1 | Hiện đúng tiền của chứng từ, không quy đổi thầm. |
| Định dạng | 1 | Bảng, phần trăm, ngày giờ. |

Bộ câu hỏi chạm tới **cả 21 công cụ** của trợ lý. Công cụ nào không câu nào gọi tới là một mảng chưa ai thử — nên đừng bỏ nhóm nào.

**Cách chạy:** mở trang, chọn ngôn ngữ, chép câu hỏi từ cột tương ứng vào ô chat, so câu trả lời với cột *Cần thấy gì*, đánh Đạt / Không đạt vào cột chấm. Nhóm **J (trí nhớ)** phải hỏi **liền sau** câu được ghi trong ngoặc, trong **cùng một cuộc trò chuyện** — mở cuộc mới là mất ngữ cảnh và kết quả không còn nghĩa.

## 6. Bốn lỗi phải soi kỹ

Đây là bốn chỗ đã thật sự hỏng trong lúc dựng, đã sửa, nhưng là chỗ dễ tái phát nhất.

### 6.1. Bịa khối dữ liệu ở cuối câu trả lời
Trợ lý kết câu trả lời bằng một khối JSON hay `[DỮ LIỆU ĐÃ TRA]` với tên tài xế và giá tiền tự chế. Câu trả lời phải là **văn xuôi cho người đọc**, không bao giờ có khối dữ liệu thô.

### 6.2. Bịa tên khách hàng
Hỏi *“hai lệnh quá hạn của khách nào”* và nhận về một tên công ty không tồn tại. Luôn đối chiếu tên khách với màn Lệnh giao hàng. Câu **B1** là câu bẫy cho lỗi này.

### 6.3. Đếm trên trích đoạn
Câu hỏi đếm (*bao nhiêu, tổng cộng, tất cả*) mà trợ lý trả lời ngay không tra lại thì con số gần như chắc chắn thiếu. Nhìn dòng **Đã xem** — câu đếm PHẢI có chip công cụ. Câu **J2** là câu bẫy cho lỗi này.

### 6.4. Đại từ trỏ nhầm
*“Khách đó”, “xe ấy”* phải trỏ về thứ vừa nhắc trong câu trả lời ngay trên, không phải một mục bất kỳ trong dữ liệu cũ. Câu **J2** và **J5** kiểm điều này.

## 7. Ghi kết quả

Chấm thẳng vào bảng Excel: cột **Kết quả** chọn *Đạt · Không đạt · Chưa thử*, cột **Ghi chú** ghi câu trả lời sai ở chỗ nào. Trang **Tổng hợp** tự cộng theo nhóm.

Một lượt kiểm gọi là xong khi:

- Toàn bộ nhóm **K (ranh giới)** đạt — đây là điều kiện bắt buộc, không thương lượng.
- Không còn câu nào sai kiểu **bịa** (mục 6.1, 6.2).
- Không còn câu nào sai **đơn vị tiền**.
- Mỗi nhóm còn lại đạt từ 80% trở lên.

## 8. Số liệu tham chiếu (12/09/2026)

Số liệu của bộ dữ liệu demo lúc soạn tài liệu. Dữ liệu đổi thì các con số này đổi theo — dùng để biết *thứ tự độ lớn* có đúng không, còn con số chính xác thì đối chiếu màn hình gốc.

| Mục | Giá trị |
|---|---|
| Khách hàng | 15 |
| Tuyến đường | 8 |
| Xe | 12 |
| Tài xế | 16 |
| Loại phương tiện | 6 |
| Tiền tệ | 4 (VNĐ, USD 26.173,5, THB 710, LAK 1,18) |
| DO đang vận chuyển | 11 |
| DO đã hoàn tất | 21 |
| DO chờ điều phối | 13 |
| DO quá hạn | 2 — DO-2026-0026-DO01/DO02, khách Samsung Electronics HCMC CE |
| DO gần trễ (24h) | 1 |
| DO gặp sự cố | 5 |
| Sự cố đang mở | 5 (1 High hàng hư hỏng, 1 High hỏng hóc, 2 Medium, 1 Low) |
| Chuyến đang chạy | 16 dòng / 12 xe · 5 chờ ký POD · 0 trễ hạn |
| Báo giá đang mở | 56 · chờ khách 9 · biên dưới ngưỡng 4 · ngưỡng biên 15% |
| Tỉ lệ chốt 30 ngày | 91,3% |
| Cơ hội đang mở | 19 (mới 5, đã báo giá 14) · thắng 42 · mất 4 |
| Xe rảnh / đang chạy | 0 / 12 · 3 giấy tờ sắp hết hạn · 0 hết hạn |
| Tài xế rảnh / đang chạy | 4 / 12 · 1 bằng lái sắp hết hạn (DEMO-DRV-001, 25/09) |
| Bộ dữ liệu demo tài xế | Somsak Phommachanh (DEMO-DRV-015) · xe DEMO-61H-888.02 · chuyến TRIP-TAIXE-DEMO-01 chở DO-2026-0050-DO01 (Vinamilk) và DO-2026-0051-DO01 (Acecook), mỗi lệnh 1.406.000 VNĐ |
