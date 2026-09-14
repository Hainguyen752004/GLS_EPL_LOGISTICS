# EPL Lào — Quản lý vận tải theo Excel của bên Lào

Bản làm lại của EPL_System cho khách Lào, **đúng theo tệp Excel họ đang dùng** (`DOCS/ຂົນສົ່ງ EPL.xlsx`) và bản giao diện họ đã duyệt (`EPL-Transport-UI.html`). Không Trip, không báo giá, không công thức giá thành — một tờ **phiếu xuất xe** là đơn vị làm việc duy nhất. Xem [DOCS/BAN_DO_CHUC_NANG.md](DOCS/BAN_DO_CHUC_NANG.md) (có bản Word cạnh đó) để biết từng chức năng của EPL_System đi đâu.

## Chạy

```
cd D:\Demo_Lao\EPL_LAO_REAL
python backend\app\seed.py                       # lần đầu: dựng bảng + gieo dữ liệu mẫu từ Excel
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8010 --no-access-log
```
Hoặc bấm đúp `chay.bat`. Mở **http://localhost:8010** — giao diện và API cùng một cổng.

Tài khoản demo (mật khẩu tất cả là `1234`): `thabok` Bãi Thà Bốc · `ketoan` Kế toán Viêng Chăn · `khonl` Kế toán kho nhiên liệu · `quyvc` Quỹ Viêng Chăn · `quytb` Tiền mặt lẻ Thà Bốc · `doanhthu` Kế toán doanh thu · `admin`.

Cấu hình trong `.env` (không commit): `DATABASE_URL` trỏ vào DB **`epl_lao`** — DB riêng, cùng máy chủ PostgreSQL với EPL_System; `EPL_LAO_SECRET` để ký phiên đăng nhập.

## Cấu trúc — một module một bộ ba tệp

```
backend/app/
  main.py            FastAPI, phục vụ frontend ở / và API ở /api
  database.py        kết nối PostgreSQL, create_all (không migration)
  models.py          bảng — theo đúng Excel, có gì khai đó
  seed.py            gieo dữ liệu mẫu (5 phiếu chép từ Excel + bản mẫu)
  services/          tinh_toan.py (phép tính phiếu) · phan_quyen.py (ai làm gì) · bao_mat.py (đăng nhập)
  routes/            dang_nhap · danh_muc · phieu · bao_cao · kho · nha_cung_cap · quy_trinh
frontend/
  index.html         khung: đăng nhập, thanh điều hướng, nút ngôn ngữ, chỗ nạp module
  css/chung.css      bảng màu bên Lào đã duyệt, nút, bảng, ô nhập
  js/chung.js        gọi API, ngôn ngữ, đăng nhập, nạp module theo #/ten-module
  js/ngon_ngu.js     từ điển Việt · Lào · Anh (458 khoá) — SINH TỰ ĐỘNG, đừng sửa tay
  modules/<tên>/     <tên>.html · <tên>.css · <tên>.js — sai đâu mở đúng thư mục đó
kiem/
  thu_giao_dien.js   thử toàn giao diện trên jsdom, nối máy chủ thật
  thu_luong_api.py   đi trọn luồng: lập phiếu → kiểm → ghi sổ → chi → hoá đơn → thu tiền
  test_tinh_toan.py  bộ kiểm đơn vị phép tính và phân quyền
```

14 module: Tổng quan · Theo dõi phiếu vận chuyển · Phiếu xuất xe · Hoá đơn vận chuyển · Xe liên kết · Tiền chuyến & tiền nước tài xế · Theo dõi nhà cung cấp · Kho nhiên liệu · Kho phụ tùng · Khách hàng · Xe · Tài xế · Quy trình & trách nhiệm · Tài khoản.

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
