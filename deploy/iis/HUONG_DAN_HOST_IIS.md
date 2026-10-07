# Host trang điều xe EPL Lào trên Windows Server (IIS)

Trang điều xe là Python (FastAPI) + PostgreSQL; giao diện HTML / CSS / JS phục vụ cùng một cổng (`/` giao diện, `/api` API). Chạy dưới IIS
giống API / Web C# của anh Tune: IIS giữ địa chỉ và HTTPS, **HttpPlatformHandler** bật tiến trình Python. Không cần Visual Studio.

## 1. Cài một lần trên máy host

1. **Python 3.12 (64-bit)** — <https://www.python.org/downloads/windows/>, tích «Install for all users». Ghi lại đường dẫn
   `python.exe` (thường `C:\Program Files\Python312\python.exe` hoặc `C:\Python312\python.exe`).
2. **IIS** + **HttpPlatformHandler v1.2** (Microsoft) — tải bản x64 trên trang Microsoft «HttpPlatformHandler», cài, rồi mở lại IIS Manager.
3. Kiểm máy host gọi được PostgreSQL của trang điều xe (máy `DATABASE_URL` trong `.env`) và gọi được `https://demo-lao-api.goldensme.com`.

## 2. Lấy mã và thư viện

```powershell
cd D:\Sites
git clone -b EPL_laoreal https://github.com/Hainguyen752004/GLS_EPL_LOGISTICS.git epl_lao
cd epl_lao
& "C:\Python312\python.exe" -m pip install -r requirements.txt
```
Chép tệp `.env` của máy thật vào `D:\Sites\epl_lao\.env` (qua kênh riêng — tệp có mật khẩu DB). Tệp đã trỏ API / Web anh Tune và bật gửi
bút toán; xem README mục «Cấu hình».

Chạy thử tay một lần (thấy «Application startup complete» rồi Ctrl+C) — lần đầu máy tự thêm bảng / cột mới vào DB:
```powershell
& "C:\Python312\python.exe" -X utf8 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8099
```

## 3. Tạo site IIS

1. Chép `deploy\iis\web.config` ra **thư mục gốc** `D:\Sites\epl_lao\web.config`; sửa `processPath` đúng đường `python.exe` ở bước 1.
2. Tạo thư mục `D:\Sites\epl_lao\logs`.
3. IIS Manager → **Add Website**: tên `epl-lao-dieu-xe`, Physical path `D:\Sites\epl_lao`, binding **https** + tên miền + chứng chỉ
   (điện thoại tài xế chỉ lấy được GPS trên HTTPS; API anh Tune không đi theo chuyển hướng → dùng đúng địa chỉ https này).
4. Application Pool của site: **No Managed Code**, Identity cần quyền **ghi** `D:\Sites\epl_lao\tep` (ảnh, hợp đồng) và `logs`
   (Properties → Security → thêm `IIS AppPool\epl-lao-dieu-xe` → Modify).
5. Mở `https://<tên miền>/` → màn đăng nhập. Lỗi thì xem `logs\uvicorn.log`.

Cập nhật bản mới: `git pull` trong `D:\Sites\epl_lao`, `pip install -r requirements.txt` nếu đổi thư viện, rồi **Recycle** Application Pool.

## 4. Sau khi có địa chỉ https

1. Sếp tạo **khoá bàn giao** trên trang điều xe (`POST /api/handover/tao-khoa`), gửi anh Tune cùng địa chỉ → anh Tune đặt
   `LogisticsSource:BaseUrl = https://<tên miền>/api/`, `LogisticsSource:ApiKey = <khoá>` trong `appsettings.laos.json` host, restart API.
2. Chạy bài kiểm chỉ đọc: `python -X utf8 tools\kiem_sau_trien_khai.py https://demo-lao-api.goldensme.com https://<tên miền>`.
3. Một lần: Sếp gọi `POST /api/muc/qua-chi-ton` (tài liệu triển khai anh Tune mục 7.3).

## Ghi chú

- **Một tiến trình** (`processesPerApplication="1"`): trang có luồng tự đồng bộ nền 5 phút; nhiều tiến trình là chạy trùng.
- Không mở cổng uvicorn ra ngoài — chỉ IIS (443) nhận yêu cầu.
- Cách khác không dùng HttpPlatformHandler: chạy uvicorn thành dịch vụ Windows (NSSM) ở `127.0.0.1:<cổng>` rồi IIS **URL Rewrite + ARR**
  chuyển tiếp vào cổng đó.
