# Host trang điều xe EPL Lào trên máy chủ Linux bằng Docker

Một container: FastAPI (`/api`) + giao diện (`/`), một tiến trình. Tuỳ chọn thêm Caddy tự lấy HTTPS.
Cần HTTPS: điện thoại tài xế chỉ lấy được GPS trên `https://`; Web anh Tune gọi ngược về trang này qua `https://` (không đi theo chuyển hướng).

## 1. Cài Docker (một lần, Ubuntu / Debian)

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER      # đăng xuất / đăng nhập lại để dùng docker không cần sudo
docker compose version              # phải có "Docker Compose version v2…"
```

## 2. Lấy mã + cấu hình

```bash
cd /opt
sudo git clone -b EPL_laoreal https://github.com/Hainguyen752004/GLS_EPL_LOGISTICS.git epl_lao
sudo chown -R $USER /opt/epl_lao && cd /opt/epl_lao
nano .env      # dán NỘI DUNG tệp .env của máy thật (gửi qua kênh riêng — có mật khẩu DB), lưu lại
chmod 600 .env
```
Tệp `.env` đã trỏ đúng DB (`DATABASE_URL`), API / Web anh Tune và bật gửi bút toán. Máy chủ Linux phải **ra được** máy PostgreSQL
trong `DATABASE_URL` và `https://demo-lao-api.goldensme.com`.

## 3. Chạy

**Cách A — máy chủ CHƯA có nginx / web server nào chiếm cổng 80, 443** (Caddy tự lấy chứng chỉ HTTPS):
```bash
echo "DOMAIN=dieuxe.tenmien-cua-anh.com" >> .env      # tên miền đã trỏ (bản ghi A) về IP máy chủ; mở cổng 80 + 443
docker compose --profile https up -d --build
```

**Cách B — máy chủ ĐÃ có nginx** (trang nghe `127.0.0.1:8020`, nginx giữ HTTPS):
```bash
docker compose up -d --build
```
Thêm vào nginx một server block rồi `sudo nginx -t && sudo systemctl reload nginx`:
```nginx
server {
    listen 443 ssl;
    server_name dieuxe.tenmien-cua-anh.com;
    ssl_certificate     /etc/letsencrypt/live/dieuxe.tenmien-cua-anh.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/dieuxe.tenmien-cua-anh.com/privkey.pem;
    client_max_body_size 50m;
    location / {
        proxy_pass http://127.0.0.1:8020;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;
    }
}
```
(chứng chỉ: `sudo certbot --nginx -d dieuxe.tenmien-cua-anh.com`).

Lần chạy đầu, trang tự thêm bảng / cột mới vào DB (không phải chạy script).

## 4. Kiểm

```bash
docker compose ps                    # dieu-xe: running (healthy) sau khoảng 1 phút
docker compose logs -f dieu-xe       # thấy "Application startup complete"; Ctrl+C để thoát xem
curl -I https://dieuxe.tenmien-cua-anh.com/      # HTTP/2 200
```
Mở `https://<tên miền>/` → màn đăng nhập.

## 5. Cập nhật bản mới / khởi động lại

```bash
cd /opt/epl_lao && git pull && docker compose up -d --build      # cách A thêm: --profile https
docker compose up -d --force-recreate dieu-xe                      # sau khi sửa .env: tạo lại container để nạp giá trị mới
docker compose restart dieu-xe                                     # chỉ khởi động lại — KHÔNG đọc lại .env
```
Ảnh / hợp đồng đính kèm và nhật ký nằm ở volume `tep`, `logs` — giữ nguyên qua mỗi lần cập nhật.
Sao lưu ảnh: `docker run --rm -v epl_lao_tep:/d -v $PWD:/b alpine tar czf /b/tep_$(date +%F).tgz -C /d .`

## 6. Sau khi có địa chỉ https

1. Gửi em (bên trang điều xe) tên miền → em tạo **khoá bàn giao**, gửi anh Tune đặt `LogisticsSource:BaseUrl = https://<tên miền>/api/`
   và `LogisticsSource:ApiKey = <khoá>` trong `appsettings.laos.json` của API host, restart API.
2. Bài kiểm chỉ đọc (từ máy có mã nguồn): `python -X utf8 tools/kiem_sau_trien_khai.py https://demo-lao-api.goldensme.com https://<tên miền>`.
3. Một lần: Sếp gọi `POST /api/muc/qua-chi-ton` (tài liệu triển khai anh Tune mục 7.3).
