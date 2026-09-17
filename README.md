# EPL Lào — Quản lý vận tải theo Excel của bên Lào

Bản làm lại của EPL_System cho khách Lào, **đúng theo tệp Excel họ đang dùng** (`DOCS/ຂົນສົ່ງ EPL.xlsx`) và bản giao diện họ đã duyệt (`EPL-Transport-UI.html`). Không Trip, không báo giá, không công thức giá thành — một tờ **phiếu xuất xe** là đơn vị làm việc duy nhất. Xem [DOCS/BAN_DO_CHUC_NANG.md](DOCS/BAN_DO_CHUC_NANG.md) (có bản Word cạnh đó) để biết từng chức năng của EPL_System đi đâu.

## Chạy

```
cd D:\Demo_Lao\EPL_LAO_REAL
python backend\app\seed.py                       # lần đầu: dựng bảng + gieo dữ liệu mẫu từ Excel
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8010 --no-access-log
```
Hoặc bấm đúp `chay.bat`. Mở **http://localhost:8010** — giao diện và API cùng một cổng.

Tài khoản demo (mật khẩu tất cả là `1234`): `thabok` Admin Thà Bốc · `ketoan` Kế toán Viêng Chăn · `khonl` Kế toán kho nhiên liệu · `quyvc` Quỹ Viêng Chăn · `quytb` Tiền mặt lẻ Thà Bốc · `doanhthu` Kế toán doanh thu · `admin` · `tx01` `tx02` `tx03` tài xế · `khotb` `khovc` thủ kho nhiên liệu.

Màn đăng nhập liệt kê sẵn mười tài khoản này — bấm một cái là vào thẳng, khỏi gõ.

Cấu hình trong `.env` (không commit): `DATABASE_URL` trỏ vào DB **`epl_lao`** — DB riêng, cùng máy chủ PostgreSQL với EPL_System; `EPL_LAO_SECRET` để ký phiên đăng nhập.

## Cấu trúc — một module một bộ ba tệp

```
backend/app/
  main.py            FastAPI, phục vụ frontend ở / và API ở /api
  database.py        kết nối PostgreSQL, create_all (không migration)
  models.py          bảng — theo đúng Excel, có gì khai đó
  seed.py            gieo dữ liệu mẫu (5 phiếu chép từ Excel + bản mẫu)
  services/          tinh_toan.py (phép tính phiếu) · phan_quyen.py (ai làm gì) · bao_mat.py (đăng nhập)
  routes/            dang_nhap · danh_muc · phieu · phieu_linh · tat_toan · theo_doi · vi_tri
                     tuyen · acc_code · bao_cao · kho · nha_cung_cap · quy_trinh
frontend/
  index.html         khung: đăng nhập, thanh điều hướng, nút ngôn ngữ, chỗ nạp module
  css/chung.css      bảng màu bên Lào đã duyệt, nút, bảng, ô nhập
  vendor/leaflet/    thư viện bản đồ để sẵn trong dự án, KHÔNG gọi CDN
  js/chung.js        gọi API, ngôn ngữ, đăng nhập, nạp module theo #/ten-module
  js/ngon_ngu.js     từ điển Việt · Lào · Anh (741 khoá) — SINH TỰ ĐỘNG, đừng sửa tay
  modules/<tên>/     <tên>.html · <tên>.css · <tên>.js — sai đâu mở đúng thư mục đó
kiem/
  thu_giao_dien.js   thử toàn giao diện trên jsdom, nối máy chủ thật
  thu_ngoai_tuyen.js màn Cấp phát khi MẤT MẠNG: lưu đệm · hàng đợi · tự gửi khi có mạng lại
  thu_phieu_linh.py  luồng phiếu lĩnh: QR · thủ kho cấp dầu · khai đổ dọc đường · tất toán
  thu_vi_tri.py      GPS thật: ai được gửi · lọc điểm dày · GPS cũ thì lùi về mốc
  thu_luong_api.py   đi trọn luồng: lập phiếu → kiểm → ghi sổ → chi → hoá đơn → thu tiền
  test_tinh_toan.py  bộ kiểm đơn vị phép tính và phân quyền
```

21 module: Tổng quan · Theo dõi phiếu vận chuyển · **Theo dõi tuyến** (trung tâm điều hành: dải ô số, danh sách chuyến, **bản đồ tuyến**, tiến độ từng chặng, sổ sự cố, duyệt báo hỏng) · Phiếu xuất xe · Hoá đơn vận chuyển · **Chứng từ** (phiếu tạm ứng · **phiếu lĩnh nhiên liệu có mã QR** · phiếu thu) · **Phiếu của tôi** (màn tài xế: tiền tạm ứng, xuất phát, báo hỏng, khai đổ dầu dọc đường, **chia sẻ vị trí GPS**) · **Cấp phát** (thủ kho cấp dầu, quỹ chi tạm ứng, quét mã QR) · Xe liên kết · Tiền chuyến & tiền nước tài xế · **Tất toán tài xế** (theo tháng) · Theo dõi nhà cung cấp · Kho nhiên liệu · **Điểm đổ nhiên liệu** · Kho phụ tùng · Khách hàng · **Xe** (đầu kéo + rơ-moóc lắp/tháo được, giấy tờ & hạn, sửa chữa) · **Tài xế & bằng lái** · **Tuyến đường** (chặng, km, BOT) · Quy trình & trách nhiệm · Tài khoản.

Quy tắc kho: nhiên liệu đổ ở kho Thà Bốc → khi kế toán kho ghi sổ mục III thì tự sinh dòng xuất kho; sửa xe lấy phụ tùng từ kho → trừ tồn ngay lúc khai; mua ngoài → công nợ. Xe nhà định khoản `625/…`, `614/…`; xe liên kết `4022/…`. Chi tiết trong [DOCS/BAN_DO_CHUC_NANG.md](DOCS/BAN_DO_CHUC_NANG.md) mục 4b.

Điều hướng có **hai kiểu xem**, đổi ở nút tên người dùng → Cài đặt giao diện: *thanh bên* (thấy hết chức năng, có số việc đang chờ cạnh từng mục, thu gọn còn biểu tượng được) và *thanh trên* hai tầng (nhường trọn chiều ngang cho bảng). Máy nào nhớ theo máy đó.

Xe về thì kế toán bấm **Khoá phiếu** (máy rà km, hao hụt, phiếu quặng đính kèm, mục chưa kiểm rồi mới cho khoá); khoá xong mới xuất hoá đơn và mới trả được chủ xe liên kết. Bán phụ tùng, xăng dầu cho bên ngoài ở màn **Bán hàng**. Mỗi bước sinh ra tiền hoặc hàng để lại một tờ trong **Sổ chứng từ** (`GET /api/chung-tu`, màn Chứng từ → tab Sổ chứng từ) cho module kế toán kéo về: ai nhập ô nào, tờ nào sinh ở bước nào, định khoản gợi ý, mã còn thiếu — xem [DOCS/CHUNG_TU_VA_DIEM_NOI.md](DOCS/CHUNG_TU_VA_DIEM_NOI.md) (có bản Word cạnh đó).

Ngôn ngữ: **Tiếng Việt · ພາສາລາວ · English · VI + ລາວ** (nút ở góc trên phải và trên màn đăng nhập).

## Kiểm

```
python kiem\test_tinh_toan.py                    # đơn vị, không cần máy chủ
python kiem\thu_luong_api.py                     # cần máy chủ :8010 đang chạy
node kiem\thu_giao_dien.js                       # cần máy chủ :8010 + jsdom của EPL_System
```

## Thêm một module mới

1. Tạo `frontend/modules/<tên>/` với ba tệp `<tên>.html`, `<tên>.css`, `<tên>.js`.
2. Trong `.js`: `EPL.modules['<tên>'] = { init(root, ctx) {…}, onLang() {…} }`.
3. Thêm một dòng vào `MODULES` trong `js/chung.js` (id, nhóm, khoá tên, icon, vai được thấy).
4. Thêm khoá `nav_…` và `title_<tên_gạch_dưới>` vào `KHOA_MOI` trong script sinh từ điển rồi sinh lại `ngon_ngu.js`.
5. API mới thì thêm một tệp `routes/<tên>.py` và đăng ký trong `main.py`.
