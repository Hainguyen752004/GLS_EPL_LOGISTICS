# Cách chạy Trang Tài xế và Trợ lý EPL

Ghi chú vận hành — đọc trước buổi demo.

## Tóm tắt một trang

| | Trang Tài xế | Trợ lý (chatbot) |
|---|---|---|
| Thư mục | `D:\Demo_Lao\EPL_TaiXe` | `D:\Demo_Lao\EPL_TroLy` |
| Bấm đúp | `chay.bat` | `chay.bat` |
| Mở trình duyệt | `http://localhost:8080` | `http://localhost:8090` |
| Hỏi API ở đâu | `http://senvangsolutions.com:1506` | `http://senvangsolutions.com:1506` |
| Cần bật gì thêm không | Không | Không |

Cả hai **mặc định hỏi máy chủ đã host ở cổng 1506**, vì máy chủ đó chạy vĩnh viễn. Bấm đúp là dùng được ngay, không cần mở cửa sổ uvicorn nào trên máy mình.

## Trang Tài xế

Bấm đúp `D:\Demo_Lao\EPL_TaiXe\chay.bat`, rồi mở `http://localhost:8080`.

Hoặc gõ tay:

```
cd D:\Demo_Lao\EPL_TaiXe
python chay.py
```

Các cờ có thể dùng:

```
python chay.py --cong 9000                      # đổi cổng
python chay.py --api http://127.0.0.1:8001      # chạy với máy chủ EPL trên máy mình
python chay.py --token <token>                  # khi máy chủ EPL bật xác thực
```

Trang có ba ngôn ngữ: **Tiếng Việt · English · ລາວ**, đổi bằng nút ở đầu trang.

### Vì sao phải chạy qua chay.py, không mở thẳng tệp HTML

Máy chủ EPL chỉ cho phép CORS từ chính nó. Một trang đặt ở địa chỉ khác gọi thẳng API sẽ bị trình duyệt chặn ngay ở bước tiền kiểm — đo được: `OPTIONS /api/drivers` với `Origin` lạ trả về `400 Bad Request`. `chay.py` vừa phục vụ trang vừa chuyển tiếp `/api/...`, nên trình duyệt chỉ thấy **một** địa chỉ duy nhất và không có CORS nào để vướng. Cách này cũng không phải sửa cấu hình máy chủ EPL đang chạy thật.

### Token nằm ở đâu

Nếu sau này máy chủ EPL bật xác thực, token được gắn **ở phía máy chủ chay.py**, không nằm trong điện thoại tài xế. Đặt qua biến môi trường `EPL_TMS_API_TOKEN` hoặc cờ `--token`.

### Giới hạn của bản demo — nói rõ để không ai hiểu nhầm

Trang này lọc chuyến theo tài xế ở phần **trình bày**. Ai mở trang cũng chọn được tên người khác. Muốn thành thật thì phải đăng nhập và lọc ở máy chủ — việc đó thuộc hệ thống cha.

## Trợ lý (chatbot)

Bấm đúp `D:\Demo_Lao\EPL_TroLy\chay.bat`, rồi mở `http://localhost:8090`.

Hoặc gõ tay:

```
cd D:\Demo_Lao\EPL_TroLy
python chay.py
```

Các cờ có thể dùng:

```
python chay.py --cong 9090                      # đổi cổng
python chay.py --api http://127.0.0.1:8001      # chạy với máy chủ EPL trên máy mình
python chay.py --khong-giam-sat                 # tắt bộ giám sát thông báo
```

Hỏi được bằng **Tiếng Việt · English · ລາວ**, đổi bằng nút ở góc dưới bên trái.

### Khóa lấy từ đâu

`GEMINI_API_KEY_GT` và `EPL_TMS_API_TOKEN` đọc từ `..\EPL_System\.env`. Hai khóa này nằm **phía máy chủ**; trình duyệt chỉ gửi câu hỏi lên. Khi chép thư mục `EPL_TroLy` sang máy khác thì máy đó cũng phải có `.env` đặt cạnh, nếu không chat sẽ báo thiếu khóa.

### Kiểm nhanh khi nghi ngờ

Mở `http://localhost:8090/suc-khoe`. Nó trả về: có khóa Gemini chưa, đang dùng mô hình nào, đang hỏi máy chủ EPL nào, nối được chưa, có bao nhiêu công cụ, bộ giám sát thông báo chạy tới đâu.

### Bộ giám sát thông báo

Cứ 15 giây quét một lần và báo chuông khi có: **báo giá mới · lệnh giao hàng mới · xe xuất phát · xe hoàn tất**.

## Trước buổi demo — chạy một lệnh làm tươi dữ liệu

Dữ liệu mẫu có hạn giao cố định, để lâu sẽ quá hạn hết. Sáng ngày demo chạy:

```
cd D:\Demo_Lao\EPL_System
python backend\scripts\keo_dai_khung_demo.py --den 2026-09-30 --ghi
```

Hoặc bấm đúp `D:\Demo_Lao\EPL_System\lam_tuoi_du_lieu.bat`.

Ba điều cần nhớ:

- Bỏ `--ghi` thì chỉ xem trước, không đụng vào dữ liệu.
- Chạy lại bao nhiêu lần cũng được — nó đặt lại mốc chứ không cộng dồn.
- Nó rải hạn giao tính từ **lúc bấm lệnh**, nên chạy sáng ngày demo là đẹp nhất. Chạy thêm một lần nữa sau khi tự điều phối chuyến mới, nếu hôm sau vẫn muốn bấm mốc trên chuyến đó.

## Ba cổng, ai là ai

| Cổng | Là gì | Bắt buộc bật không |
|---|---|---|
| `1506` | Máy chủ EPL đã host, chạy vĩnh viễn | Không cần làm gì — luôn sống |
| `8080` | Trang Tài xế | Bật khi cần demo trang tài xế |
| `8090` | Trợ lý | Bật khi cần demo chatbot |
| `8001` | Máy chủ EPL chạy trên máy mình | Chỉ khi muốn thử bản đang sửa |

Máy chủ `1506` và máy chủ `8001` **cắm vào cùng một PostgreSQL**, nên dữ liệu nhìn thấy là một. Khác nhau chỉ ở chỗ đi qua máy chủ nào.

## Hỏng thì xem chỗ nào

| Hiện tượng | Nguyên nhân thường gặp |
|---|---|
| Trang trắng, không CSS không JS | Mở thẳng tệp HTML thay vì chạy qua `chay.py` |
| "Không nối được hệ thống EPL" | Mất mạng tới `senvangsolutions.com:1506`, hoặc đã đổi `--api` sang `8001` mà chưa bật máy chủ đó |
| Chat báo thiếu khóa | Không tìm thấy `GEMINI_API_KEY_GT` trong `..\EPL_System\.env` |
| Sửa giao diện mà không thấy đổi | Trình duyệt còn giữ bản cũ — bấm `Ctrl+F5` |
| Cửa sổ máy chủ tự đứng im | Console Windows bật QuickEdit: lỡ bấm chuột vào cửa sổ là nó tạm dừng. Bấm `Esc` trong cửa sổ đó là chạy lại |
