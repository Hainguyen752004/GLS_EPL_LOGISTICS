# EPL Logistics TMS

Hệ thống quản lý vận tải từ Master Data, báo giá, SO, DO, Trip, điều phối, GPS/POD,
Parking List/QR đến chốt giá, hóa đơn và báo cáo tài chính.

## Khởi động nhanh

Yêu cầu: Python 3.11+, PostgreSQL 14+.

```powershell
cd D:\Demo_Lao\EPL_System
Copy-Item .env.example .env
C:\Users\zinnn\miniconda3\python.exe -m pip install -r backend\requirements.txt
C:\Users\zinnn\miniconda3\python.exe -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8001 --no-access-log
```

Sửa `DATABASE_URL` trong `.env` để trỏ đến PostgreSQL thật trước khi chạy. Ứng dụng tự
chạy migration lúc khởi động; tài khoản PostgreSQL cần quyền tạo/thay đổi bảng trong
schema của ứng dụng.

### Vì sao có `--no-access-log`, và cái bẫy console của Windows

Cửa sổ Console/PowerShell của Windows bật sẵn **QuickEdit** (`HKCU\Console\QuickEdit = 1`).
Ở chế độ đó, chỉ cần bấm chuột vào trong cửa sổ là console vào "mark mode" và **tạm dừng
mọi đầu ra**. Lệnh ghi tiếp theo bị chặn vô thời hạn — và uvicorn ghi một dòng access log
cho *mỗi* yêu cầu, nên máy chủ đứng luôn:

- tiến trình vẫn sống, vẫn giữ cổng 8001 và vẫn giữ kết nối PostgreSQL;
- nhưng không nhận thêm yêu cầu nào;
- giao diện hiện "Nạp thất bại" ở **mọi** màn hình, và mọi nút bấm trông như bị vô hiệu hóa;
- log **không có dòng lỗi nào**, vì chính việc ghi log mới là chỗ bị chặn.

Đã bắt được tại trận: các luồng của tiến trình máy chủ đều ở trạng thái `Wait` với
`WaitReason = EventPairLow` — tức đang chờ một lời gọi sang tiến trình console host.

Cách xử lý:

- **Đang bị treo:** bấm `Esc` (hoặc một phím bất kỳ) trong cửa sổ đó — máy chủ chạy lại ngay,
  không cần khởi động lại.
- **Chặn hẳn:** `--no-access-log` như trên cắt gần hết lượng ghi console. Muốn chắc chắn
  thì tắt QuickEdit: `Set-ItemProperty -Path 'HKCU:\Console' -Name QuickEdit -Value 0`
  rồi mở lại cửa sổ.
- **Chạy nền:** ghi thẳng ra tệp, đừng để đầu ra vào một console/pipe không ai đọc:
  `... --no-access-log *> uvicorn.log`, rồi xem bằng `Get-Content uvicorn.log -Wait`.

Kiểm tra:

- Ứng dụng: `http://127.0.0.1:8001`
- Health check: `http://127.0.0.1:8001/api/health`
- Swagger API: `http://127.0.0.1:8001/docs`
- OpenAPI JSON: `http://127.0.0.1:8001/openapi.json`

## Cấu hình môi trường

| Biến | Bắt buộc | Ý nghĩa |
|---|---:|---|
| `DATABASE_MODE` | Có | Dùng `postgres` trên môi trường thật. |
| `DATABASE_URL` | Có | Chuỗi kết nối PostgreSQL; không commit mật khẩu. |
| `EPL_TMS_API_TOKEN` | Có | Bearer token bảo vệ API nghiệp vụ. |
| `EPL_TMS_API_PRINCIPAL` | Có | Danh tính kỹ thuật ghi vào audit. |
| `GEMINI_API_KEY_GT` | Không | Chỉ dùng cho chức năng trợ lý AI. |
| `QLSX_BASE_URL` | Không | Gốc HTTPS của QLSX (hệ công nợ) để ghi sổ kinh doanh. Trống thì dùng `EPL_ACC_CODE_API`. |
| `QLSX_ACCESS_TOKEN` | Không | Token tích hợp QLSX. Trống thì dùng `EPL_ACC_CODE_TOKEN` (cùng hệ). Không có cả hai thì nút "Ghi sổ kinh doanh" báo 503 rõ ràng, không gọi mò. |

Không commit `.env`, database cục bộ, POD/upload, log hoặc model AI. `.gitignore` đã
được cấu hình cho các dữ liệu này.

## Tài liệu

- [Mô tả 71 bảng database](docs/DATABASE_SCHEMA_VI.md)
- [Mô tả chi tiết 170 API](docs/API_REFERENCE_VI.md)
- [Hướng dẫn tái sinh tài liệu](docs/README.md)
- [Kịch bản test A-Z](DEMO_TEST_A_Z.md)

Tái sinh tài liệu sau khi thay đổi model/router:

```powershell
C:\Users\zinnn\miniconda3\python.exe backend\scripts\generate_system_docs.py
```

## Dependency AI tùy chọn

Luồng nhận diện camera/biển số cần OpenCV, NumPy, Ultralytics và PaddleOCR. Các gói
này không nằm trong dependency lõi vì dung lượng lớn; cài riêng trên máy xử lý AI.

