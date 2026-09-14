# EPL Trợ lý

Chatbot quản lý vận hành cho EPL Logistics: hỏi bằng tiếng Việt, tiếng Anh hoặc tiếng Lào,
trợ lý tự đọc API của hệ EPL đang chạy rồi trả lời. Không có kịch bản cứng — mô hình
(Gemini 2.5 Flash) chọn công cụ cần gọi theo câu hỏi.

```
chay.bat                                         # bấm đúp — tự kiểm hệ EPL rồi bật trợ lý
python chay.py                                   # trang http://localhost:8090
python chay.py --api http://127.0.0.1:8001       # chạy với máy chủ EPL trên máy mình
```

**Mặc định trợ lý hỏi máy chủ đã host `http://senvangsolutions.com:1506`**, vì máy chủ đó
chạy vĩnh viễn — bật trợ lý là dùng được ngay, không cần bật gì thêm trên máy này.

Muốn chạy với máy chủ EPL trong nhà thì thêm `--api http://127.0.0.1:8001`, và bật nó trước
ở thư mục `EPL_System`:
`python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8001 --no-access-log`

Hai đường đó **cắm vào cùng một PostgreSQL**, nên dữ liệu nhìn thấy là một; khác nhau chỉ ở
chỗ đi qua máy chủ nào.

Khóa đọc từ `../EPL_System/.env` (hoặc biến môi trường): `GEMINI_API_KEY_GT`, `EPL_TMS_API_TOKEN`.
Cả hai nằm phía máy chủ; trình duyệt chỉ gửi câu hỏi lên `POST /hoi`.

## Cách chạy bên trong

```
trình duyệt ──POST /hoi {cau_hoi, lich_su, ngon_ngu}──► chay.py ──stream SSE──► trình duyệt
                                                          │      (công cụ đang tra, chữ chảy dần)
                                        tac_tu.tra_loi()  │  vòng lặp tối đa 8 lượt
                                                          ▼
                                     Gemini 2.5 Flash ◄──► cong_cu.py ──GET──► API EPL (1506)
                                        (function calling)   21 công cụ, chỉ đọc
                                                                    ▲
                        canh_bao.py ── mỗi 15 giây ─────────────────┘  (làm nóng bộ đệm,
                             │                                          phát thông báo)
trình duyệt ──GET /thong-bao?sau=ID ◄──────┘
```

- `cong_cu.py` — 21 công cụ, mỗi công cụ là một câu hỏi nghiệp vụ (tổng quan hôm nay, lệnh
  giao hàng, chuyến đang chạy, sự cố, báo giá, cơ hội, đội xe, xe, tài xế, khách hàng, tuyến,
  doanh thu, hồ sơ hoàn tất, bảo dưỡng, lịch tài xế, tỷ giá…). Kết quả được **cắt gọn** trước
  khi đưa cho mô hình. Dòng DO được nối sang báo giá để mang **mã tiền tệ**. Danh sách phân
  trang đọc từng trang 200 (API chặn trên 200).
- `tac_tu.py` — lời dẫn hệ thống (không bịa số, tiền kèm mã tiền tệ của chứng từ, viết VNĐ,
  chỉ đọc, xưng em–anh/chị, ngôn ngữ trả lời) và vòng lặp gọi công cụ có stream.
- `canh_bao.py` — bộ giám sát: so ảnh ba danh sách mỗi 15 giây, phát thông báo **báo giá
  mới · lệnh giao hàng mới · xe xuất phát · xe hoàn tất / lệnh giao xong**.
- `chay.py` — máy chủ thư viện chuẩn, nhiều luồng; `GET /suc-khoe` báo có khóa Gemini chưa,
  nối được EPL chưa, bộ giám sát đọc lần cuối lúc nào.
- `web/` — giao diện chat theo phong cách Claude, ba ngôn ngữ, sáng/tối, lịch sử lưu trong
  trình duyệt, chuông thông báo + toast + Notification của trình duyệt (khi cho phép).

## Tốc độ và trí nhớ

Đo 12/09: một vòng Gemini ≈ 1,3 s, một câu 2–3 vòng, API EPL 0,2–1 s. Nên thời gian nằm ở
Gemini, không ở EPL. Bốn việc đã làm:

1. **Stream** — chữ chảy về trình duyệt ngay khi mô hình bắt đầu viết; từng công cụ hiện lên
   lúc được gọi. Câu tổng quan: công cụ hiện ở giây 1,6, chữ chảy từ giây 3,2.
2. **Song song** — mô hình gọi nhiều công cụ một vòng thì chạy cùng lúc.
3. **Giữ kết nối** HTTPS tới Gemini theo luồng, bỏ bắt tay TLS mỗi vòng.
4. **Bộ đệm nóng** — bộ giám sát đọc ba danh sách mỗi 15 giây, công cụ dùng lại (0,0 s).

Trí nhớ: mỗi câu trả lời kèm `ngu_canh` — dữ liệu đã tra, rút gọn ≤ 6.000 ký tự. Lượt sau
gửi lại; máy chủ đưa vào lượt NGƯỜI DÙNG hiện tại dưới nhãn dữ liệu hệ thống. **Không** gắn
vào lượt của mô hình: đã đo thấy mô hình bắt chước và kết câu trả lời bằng một khối dữ liệu
tự chế (tên tài xế, giá tiền không tồn tại). Câu nối tiếp trả lời trong ~2,3 s không tra lại.

Ngân sách suy nghĩ mặc định 256 (`GEMINI_THINKING`): 0 nhanh hơn ~0,2 s/vòng nhưng đã đo
thấy đoán tên khách thay vì gọi công cụ.

## Phạm vi bản này

**Chỉ đọc.** Trợ lý trả lời mọi câu hỏi về dữ liệu nhưng không tạo, sửa, điều phối gì. Hỏi làm
việc đó, nó chỉ đúng màn hình để làm. Bước hành động (điều xe, duyệt báo giá, ghi sổ) cần một
lớp xác nhận riêng — để pha sau.

## Kiểm

```
python -m unittest discover -s kiem -v          # ngoại tuyến, không gọi Gemini, 16 bài
python docs/sinh_tai_lieu_test.py               # sinh lại bộ tài liệu kiểm thử
```

Bộ kịch bản kiểm thử thủ công nằm ở `docs/`:

- `KICH_BAN_TEST.docx` — chuẩn bị, 21 bước bấm, cách chấm, bốn lỗi phải soi kỹ.
- `CAU_HOI_TEST_3_NGON_NGU.xlsx` — 73 câu hỏi, mỗi câu ba ngôn ngữ, có ô chấm Đạt/Không đạt
  và trang Tổng hợp tự cộng theo nhóm.

Nội dung hai tệp lấy từ `docs/bo_cau_hoi.py` — sửa ở đó rồi chạy lại bộ sinh, hai tệp không lệch nhau.
