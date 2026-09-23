# Kế hoạch sửa theo câu trả lời của anh Khampla (bản 23/09/2026)

Nguồn: `DOCS/word/ຄຳຖາມວິຊາການ_EPL.docx` (anh Khampla đánh dấu 23/09). Sau đợt này: chạy lại toàn bộ bộ
kiểm → sửa UI/UX → anh test → bàn giao khách.

## Rà trước khi làm — cái ĐÃ CÓ (không làm lại)

| Ý của anh Khampla | Tình trạng trong mã |
|---|---|
| Mã tiền 1011 / 1012 / 1021 / 1022 (C5.6) | Đã có — `services/chung_tu.py` `MA_TIEN`, chọn theo cách chi + tiền tệ |
| Kho 1371 (con của 137), NCC 4021 (con của 402) (C5.4, C5.5) | Đã có — giữ nguyên |
| 7 kho dầu (C5.2) | Đã có trong DB `epl_lao` (KHO-TB, KHO-VC, KM28-VC, TB-HL, THAVAI, TK, KM28-TK) |
| Lệnh sửa chữa riêng khi xe không chạy (C7.3) | Đã có — `repair_orders` / `routes/sua_chua.py` |
| Phí 2 % · ngưỡng tấn theo từng chủ xe (C4.2) | Đã có — `owners.fee_pct / over_limit_t / over_price` |
| Trả chủ xe từng phiếu / gộp / theo đợt (C4.3) | Đã có — `owner_payments` |

## Việc phải làm, theo thứ tự

### 1. Bãi không thấy tiền, không nhập giá (A2, C5.1, C4.1)
- Máy chủ bỏ HẲN đơn giá, thành tiền, tỷ giá, tổng tiền mục khỏi gói phiếu trả cho Bãi và tài xế
  (không chỉ che trên giao diện).
- Bãi lưu phiếu: đơn giá KHÔNG lấy từ Bãi. Dòng cũ giữ giá cũ; dòng mới lấy giá tự động
  (dầu/phụ tùng kho → giá bình quân của kho; phí cầu đường → theo tuyến; còn lại 0).
- Người KIỂM mục (KT kho xăng dầu mục III, KT Chi phí mục IV–VI) nhập/sửa đơn giá và tiền tệ khi mục
  ở "đã nhập"; chặn "dòng giá 0" chuyển từ lúc Bãi GỬI sang lúc kế toán KIỂM.
- Giá cước, giá thuê xe, phí, ngưỡng tấn: Bãi không gửi được (lập hay sửa). Giá thuê xe do KT Viêng Chăn nhập (C4.1).
- Tài xế báo đổ dầu: chỉ số lít + trạm, không nhập giá (C5.1).
- Còn phải hỏi anh Khampla: Bãi nhập "chi phí dọc đường" có được thấy số tiền không — tạm thời: KHÔNG thấy.

### 2. Giá vốn bình quân + mã giá vốn 607 (C5.3)
- Dầu: giá bình quân gia quyền theo TỪNG kho (quy LAK theo tỷ giá lúc nhập).
- Phụ tùng: đơn giá phụ tùng thành bình quân mỗi lần nhập.
- Áp cho: xuất dầu theo phiếu, phiếu lĩnh dầu, bán hàng, xuất phụ tùng.
- Mã giá vốn mặc định 607 (cấu hình vẫn đổi được). EPL_KETOAN ghi PXK_BAN đủ hai vế 607 / 1371.

### 3. Phiếu chuyển kho + mua dầu Việt Nam qua kho (C5.2, A3)
- Sổ kho dầu tính tồn theo TỪNG kho.
- Phiếu chuyển kho: kho A → kho B, số lít; mang giá bình quân kho A sang.
- Thêm "Kho xe (dầu mua Việt Nam)": nhập 1.000 lít (NCC, số đơn mua, VND) → phiếu xuất xe lấy 600 lít
  từ kho này → chuyển 400 lít về Thà Bốc / kho hiện trường.

### 4. Chủ xe mua ở quầy → trừ vào tiền trả chủ xe
- Phiếu bán hàng chọn "người mua là chủ xe liên kết". Định khoản: Nợ 4022 (phải trả chủ xe) / Có 70.
- Đợt trả chủ xe tự trừ các phiếu bán chưa trừ của chủ đó; trả một phiếu lẻ cũng trừ.

### 5. Chạy thử trọn luồng tách chặng (B1–B4) + lệnh sửa riêng
- Mỏ → kho (xe A, cước chặng gom) → hàng nằm kho → kho → cảng (xe B) → hoá đơn gộp tháng.

### 6. Kiểm
- Bộ kiểm API cũ + bộ kiểm mới cho từng mục trên, chạy tiền cảnh từng nhóm.
- Bấm tay bằng trình duyệt thật: màn phiếu (Bãi không thấy tiền, kế toán nhập giá), kho, bán hàng, chủ xe.

## Kết quả (23/09/2026 chiều)

| Việc | Trạng thái |
|---|---|
| 1. Bãi không thấy / không nhập tiền; kế toán kiểm mục nhập giá; giá cước, giá thuê do KT VC | Xong — `thu_lo_hong_23_09`, `thu_no_ky_thuat`, bấm tay trình duyệt thật |
| 2. Giá vốn bình quân theo kho, phụ tùng; mã giá vốn 607; bổ sung vế 3 tờ PXK_BAN cũ ở EPL_KETOAN | Xong — `thu_ban_hang`, `thu_kho_xe_23_09`, `thu_hai_dau` (sổ cân) |
| 3. Sổ kho theo từng kho, phiếu chuyển kho, kho xe dầu mua Việt Nam | Xong — `thu_kho_xe_23_09` |
| 4. Chủ xe mua ở quầy trừ vào tiền trả | Xong — `thu_chu_xe` |
| 5. Tách chặng + lệnh sửa riêng | Đã có sẵn, chạy lại đạt — `thu_hai_do`, `thu_hoa_don_gop`, `thu_sua_chua` |
| 6. Kiểm | 19 bộ API + 16 bài tính toán + giao diện 27 module (4 ngôn ngữ) + 4 bộ EPL_KETOAN + hai đầu — **đạt hết** |

Phát sinh khi kiểm (đã sửa): bộ kiểm tỷ giá hỏng giữa chừng để sót USD 26.620 trong DB dùng chung (đã trả về
22.000, nay luôn trả trong `finally`); bộ kiểm đẩy kế toán xoá trắng cấu hình nối sổ (nay trả về như cũ).
