# EPL Logistics TMS

Hệ thống quản lý vận tải từ Master Data, báo giá, SO, DO, Trip, điều phối, GPS/POD,
Parking List/QR đến chốt giá, hóa đơn và báo cáo tài chính.

## Khởi động nhanh

Yêu cầu: Python 3.11+, PostgreSQL 14+.

```powershell
cd D:\Demo_Lao\EPL_System
Copy-Item .env.example .env
C:\Users\zinnn\miniconda3\python.exe -m pip install -r backend\requirements.txt
C:\Users\zinnn\miniconda3\python.exe -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8001
```

Sửa `DATABASE_URL` trong `.env` để trỏ đến PostgreSQL thật trước khi chạy. Ứng dụng tự
chạy migration lúc khởi động; tài khoản PostgreSQL cần quyền tạo/thay đổi bảng trong
schema của ứng dụng.

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

