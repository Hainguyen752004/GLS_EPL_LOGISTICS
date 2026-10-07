# EPL Lào — Trang điều xe (Quản lý vận tải EPL)

Trang điều xe của EPL Lào, làm **đúng theo tệp Excel bên Lào đang dùng** (`DOCS/ຂົນສົ່ງ EPL.xlsx`). Một tờ **phiếu xuất xe (DO)** là đơn vị làm việc. Tiền và kho **không** nằm ở đây: kế toán (phiếu chi / thu, công nợ, SO, sổ cái) và kho (tồn, giá vốn, phiếu nhập / xuất) chạy trên hệ **GLS-QLSX** của anh Tune (API `GLS-QLSX-APIs` nhánh `feat/HonTunedaHai` · Web `GLS-QLSX-Web` nhánh `feat/hontunedhai_Laos`). Trang này lập DO, điều xe, theo dõi chuyến, gom chi phí theo mục và **gửi đề nghị** sang hệ đó qua API.

```
 Trang điều xe (repo này, FastAPI + PostgreSQL)           Hệ GLS-QLSX của anh Tune (API .NET + Web)
 ─────────────────────────────────────────────            ──────────────────────────────────────────
 DO gom / giao · mục I–VI · kiểm / ghi sổ từng mục  ──→   phiếu chi «Chi trước» (tạm ứng), «Chi khác» (mục V/VI, lương)
 khoá DO → bút toán chờ gửi (thuê xe, nợ NCC, cùng lương) → chứng từ tổng hợp (LogisticsJournalEntry)
 Tạo SO (cước, SO nhiên liệu)                        ──→   đơn hàng bán, công nợ khách, thu nợ, cấn trừ
 phiếu đề nghị xuất kho (dầu / phụ tùng)             ──→   kho QLSX: thủ kho cấp, phiếu xuất 48 / 44, giá vốn bình quân
 app tài xế: xuất phát, GPS, cân, khai dầu, mất mạng       Web đọc DO qua API bàn giao (khoá riêng) — màn Vụ việc, phiếu chi DO
 tự đồng bộ nền (5 phút) đọc lại trạng thái phiếu   ←──    (đã ghi sổ / đã chi / đã cấp / đã thu)
```

Tài liệu nghiệp vụ, cơ sở dữ liệu và API: [DOCS/md/NGHIEP_VU_DB_API.md](DOCS/md/NGHIEP_VU_DB_API.md) · bản đồ chức năng [DOCS/md/BAN_DO_CHUC_NANG.md](DOCS/md/BAN_DO_CHUC_NANG.md) · luồng hai trang [DOCS/md/LUONG_A_Z_HAI_TRANG.md](DOCS/md/LUONG_A_Z_HAI_TRANG.md) (bản Word ở `DOCS/word/`). Bộ tài liệu bàn giao (triển khai cho anh Tune, kho cho anh Toàn, hướng dẫn sử dụng tiếng Việt / tiếng Lào cho người dùng) gửi riêng, **không** nằm trong repo.

## Chạy

```
cd EPL_LAO_REAL
copy .env.example .env                           # rồi điền DATABASE_URL, EPL_LAO_SECRET và các khoá ở mục «Cấu hình»
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8010 --no-access-log
```
Hoặc bấm đúp `chay.bat` (cổng 8010; đổi cổng tuỳ máy). Giao diện và API cùng một cổng (`/` và `/api`). Bảng tự dựng khi khởi động (`create_all`, không migration).
`backend/app/seed.py` chỉ dùng cho DB demo trống — **không** chạy trên DB đang có dữ liệu.

Mỗi người dùng một tài khoản do Sếp tạo ở màn **Tài khoản**; vai quyết định thấy màn nào, sửa / kiểm / ghi sổ mục nào (`backend/app/services/phan_quyen.py`, theo bảng nhiệm vụ của khách). Màn đăng nhập **không** liệt kê tài khoản trừ khi bật `EPL_LAO_DANG_NHAP_MAU=1` (chỉ máy thử / demo).

## Cấu hình (`.env`, không commit)

| Khoá | Ý nghĩa |
|---|---|
| `DATABASE_URL` | PostgreSQL của trang điều xe (DB riêng `epl_lao`) |
| `EPL_LAO_SECRET` | khoá ký phiên đăng nhập |
| `EPL_ACC_CODE_API` · `EPL_ACC_CODE_COUNTRY` | danh mục tài khoản của API anh Tune (`…/api/v1/common/country-accounts`), quốc gia Lào `11`; gốc API lấy theo địa chỉ này |
| `QLSX_BASE_URL` | gốc API anh Tune — chỉ đặt khi khác máy của `EPL_ACC_CODE_API` (máy thử: `http://127.0.0.1:5090`) |
| `EPL_ACC_CODE_TOKEN` · hoặc `QLSX_USERNAME` + `QLSX_PASSWORD` + `QLSX_ORG_ID` · hoặc `QLSX_ACCESS_TOKEN` | đăng nhập API anh Tune |
| `QLSX_WEB_URL` | địa chỉ Web anh Tune — câu nhắc «cấp dầu / ghi sổ ở Web» trỏ về đó |
| `KHO_NGUON` | `qlsx` (mặc định: kho ở hệ anh Tune) · `kho_tam` chỉ để quay lui |
| `QLSX_GUI_BUT_TOAN` | `1` = gửi bút toán chờ (khoá DO, tất toán…) sang API — bật **sau cùng**, khi host đã có script + cấu hình bút toán |
| `EPL_DONG_BO_NEN_PHUT` · `EPL_DONG_BO_NEN_GIOI_HAN` | tự đồng bộ nền (mặc định 5 phút, 50 bản ghi mỗi lượt; `0` = tắt) |
| `EPL_DONG_BO_CHI_LUONG` | `1` = báo cáo Tiền chuyến & nước đọc phiếu chi lương thật (cần API có `integrations/logistics/line-vouchers`) |
| `EPL_LAO_DANG_NHAP_MAU` | `1` = màn đăng nhập liệt kê tài khoản để bấm nhanh — chỉ máy thử; máy thật để `0` |
| `EPL_CHI_TAM_UNG` | `tai_cho` = dự phòng: tạm ứng chi tại trang này khi hệ anh Tune không dùng được |

Khi lên host / đổi máy API: làm theo **mục 7 «Đổi link phía trang điều xe»** trong tài liệu triển khai gửi anh Tune (từng khoá, thứ tự, cách kiểm — `tools/kiem_sau_trien_khai.py`, rồi Sếp gọi `POST /api/muc/qua-chi-ton` một lần).

## Cấu trúc — một module một bộ ba tệp

```
backend/app/
  main.py            FastAPI, phục vụ frontend ở / và API ở /api
  database.py        kết nối PostgreSQL, create_all (không migration)
  models.py          bảng — theo đúng Excel
  routes/            phieu (DO, mục, khoá) · de_nghi · phieu_linh · tat_toan · tat_toan_doi_tac · chu_xe · ban_giao (API cho Web anh Tune)
                     ho_so_do · kho_xem · kho_hang · can_mo · giao_nhan · vi_tri · theo_doi · bao_cao · dong_bo_nen · danh_muc · tuyen
                     hop_dong · the_cao_toc · nha_cung_cap · quy_trinh · dang_nhap · lien_thong
  services/          tinh_toan · phan_quyen · tai_khoan (định khoản) · but_toan_cho (bút toán lúc khoá) · chi_tune / chi_muc_tune /
                     chi_tat_toan_tune / chi_luong_tune (phiếu chi bên anh Tune) · gui_tune (SO) · so_nhien_lieu · kho_qlsx (kho) ·
                     ban_giao · chung_tu_dong_do · dong_bo_nen · kho_hang (hàng quặng ở bãi) · dem_bao_cao (bộ đệm báo cáo)
frontend/
  index.html         khung: đăng nhập, thanh điều hướng, nút ngôn ngữ, chỗ nạp module
  js/chung.js        gọi API, ngôn ngữ, đăng nhập, danh sách MODULES, nạp module theo #/ten-module
  js/ngon_ngu.js     từ điển Việt · Lào · Anh — thêm khoá thẳng ở đây (đủ vi · lo · en), kiểm bằng kiem/thu_khoa_dich.py
  vendor/            leaflet (bản đồ), chartjs (biểu đồ) để sẵn — KHÔNG gọi CDN
  modules/<tên>/     <tên>.html · <tên>.css · <tên>.js — sai đâu mở đúng thư mục đó
tools/
  kiem_sau_trien_khai.py   kiểm nối hai hệ sau khi lên host
  sinh_word.py             .md → .docx (ảnh ![chú thích](ảnh.png), font chữ Lào)
  may_thu/                 MÁY THỬ: khoi_dong_thu.ps1 (8011 trên DB bản sao d7) · don_sach_hai_ben.ps1 (dọn dữ liệu logistics
                           DB demo + d7 — chủ dự án chạy) · gieo_bo_sach.py (gieo bộ dữ liệu chuẩn qua HTTP, đúng vai) ·
                           don_du_lieu_loi.py (dò dữ liệu lỗi / thiếu trường) · don_may_thu.py
kiem/
  thu_*.py · test_*.py   bộ kiểm (đạt / hỏng) — nhóm và cách chạy ở mục «Kiểm» bên dưới
  thu_giao_dien.js       thử toàn giao diện trên jsdom, nối máy chủ thật (8011)
  ra_*.js                BÁO CÁO rà từng vai / màn Tổng quan / Xe / Tài xế (không phải đạt/hỏng)
  _khung_tien_trinh.py · _tien_trinh_tune.py · _d7_trong_gd.py   khung chạy TRONG TIẾN TRÌNH: TestClient + một giao dịch d7,
                         cuối ROLLBACK, chặn mọi lời gọi mạng (API anh Tune / kho QLSX / bút toán là bản giả)
  _bo_cu_0610.py + bo_cu_d7_0610.json   nạp lại bộ DO cũ (trước lần dọn 06/10) vào giao dịch thử cho 5 bộ cần nó
  do_*.py                đo tải trên DB epl_lao_tai (máy 8012) — đọc đầu tệp trước khi chạy
  loi_thoi/              bộ kiểm thứ đã bỏ (kho tạm 8031, máy 8010…) — giữ tra lịch sử, KHÔNG chạy; lý do ở loi_thoi/README.md
```

**24 module** (thấy màn nào tuỳ vai):
- **Vận tải:** Tổng quan · Theo dõi phiếu vận chuyển · Theo dõi tuyến (trung tâm điều hành: bản đồ, tiến độ chặng, sổ sự cố, duyệt báo hỏng) · Phiếu xuất xe · Phiếu đề nghị chi · Phiếu đề nghị xuất kho · Phiếu đề nghị thu · Đề nghị theo DO (hồ sơ DO hai bên) · Phiếu của tôi (app tài xế) · Xe liên kết · Tất toán tài xế · Tiền chuyến & tiền nước tài xế · Tất toán đối tác · Bút toán chờ gửi · Nhà cung cấp.
- **Kho:** Xem kho (tồn dầu / phụ tùng đọc từ kho anh Tune · hàng quặng gửi bãi theo lô, phiếu điều chỉnh).
- **Danh mục:** Khách hàng (bảng giá khách × tuyến, hợp đồng) · Xe · Tài xế · Thẻ cao tốc · Tỷ giá · Tuyến đường.
- **Hệ thống:** Quy trình & trách nhiệm · Tài khoản.

**Luồng chính.** Một chuyến quặng đi qua **hai DO**: *DO gom* (mỏ → bãi; xe tới thì máy tự lập phiếu nhập kho hàng quặng `PNK_HH` theo cân bãi) rồi *DO giao* (bãi → cảng; chọn lô, máy tự lập `PXK_HH`). Mỗi DO có sáu mục chi phí I–VI; Bãi nhập, kế toán từng mục **kiểm** rồi **ghi sổ**. Ghi sổ mục IV sinh phiếu chi tạm ứng bên anh Tune; thủ quỹ ghi sổ bên đó thì tài xế mới xuất phát được. Xe về, KT Thu/Chi **Khoá phiếu** (bút toán: thuê xe 621/4022 · phí 4022/715 · quá tải 4022/758 · nợ NCC …/4021 · cùng lương 625/4201 · xuất kho 625·614/1371 hoặc xuất bán 607/1371) rồi **Tạo SO** (cước 1211/708, SO nhiên liệu 1211/707). Xe thuê: tất toán đối tác tự cấn trừ SO nhiên liệu (4022/1211). Xe nhà: tất toán tài xế quyết toán tạm ứng (625/1601). Định khoản đầy đủ: [DOCS/md/RA_SOAT_DINH_KHOAN_30_09.md](DOCS/md/RA_SOAT_DINH_KHOAN_30_09.md) và tài liệu bàn giao.

**Tiền tệ.** Phiếu ghi đúng tiền của cước (USD · Kíp · Nhân dân tệ · Bath); Kíp là tiền gốc, tỷ giá khoá vào phiếu lúc lập (màn **Tỷ giá**), báo cáo quy về Kíp kèm dòng chia theo loại tiền.

**Ngôn ngữ:** Tiếng Việt · ພາສາລາວ · English · VI + ລາວ (nút góc trên phải và màn đăng nhập). Điều hướng hai kiểu xem: thanh bên / thanh trên.

## Kiểm

Python: `C:\Users\zinnn\miniconda3\envs\Auto\python.exe -X utf8 kiem\<tệp>`. Máy thử: 8011 (d7) · API anh Tune 5090 · Web 5014.

**1. Trong tiến trình — không cần máy nào bật, không ghi DB demo, d7 ROLLBACK** (chạy lúc nào cũng được):
```
test_tinh_toan · thu_khoa_dich · thu_ban_giao_trong_gd · thu_but_toan_cho · thu_can_tru_lam_lai · thu_chung_tu_dong_do
thu_doanh_thu_quay · thu_nut_muc_nhanh · thu_phi_qua_tai_thue_xe · thu_tai_xe_tat_toan · thu_tat_toan_doi_tac · thu_dem_bao_cao
thu_de_nghi · thu_no_ky_thuat · thu_no_tram_dau · thu_the_cao_toc · thu_vai_va_doi_xe · thu_vi_tri · thu_chu_xe
thu_chi_muc_tune · thu_tat_toan_tune · thu_gui_but_toan · thu_but_toan_xuat_kho
```
Cùng kiểu nhưng **đụng dòng đang có trên d7 trong giao dịch** — chạy khi KHÔNG ai đang bấm 8011 (không thì màn người bấm phải chờ):
```
thu_chi_luong_tune · thu_ty_gia · thu_dong_bo_nen · thu_kho_hang · thu_kho_qlsx · thu_ban_giao_dau · thu_ban_giao_trang_thai_chi
```

**2. Gọi 8011 đang chạy — chỉ ghi d7 và tự dọn** (8011 phải bật):
```
thu_kho_xem · thu_ban_giao · thu_nen_tep · thu_ky_nhan_dien_thoai · thu_quyen_de_nghi_kho · thu_bao_su_co_tai_xe · thu_can_mo
thu_chieu_ve · thu_goi_y_chi_phi · thu_giao_nhan · thu_hop_dong_pod · thu_khach_hang_moi · thu_luat_so_ben_tune (chỉ đọc)
python kiem\thu_xuat_bao_cao.py http://127.0.0.1:8011      # Playwright: nút Excel / PDF mọi màn
node kiem\thu_giao_dien.js http://127.0.0.1:8011           # toàn giao diện trên jsdom
node kiem\ra_vai.js · ra_tong_quan.js · ra_xe.js · ra_tai_xe.js   # BÁO CÁO rà, không phải đạt/hỏng
```

**3. GHI THẬT sang DB demo anh Tune** (phiếu Chi trước, SO, bút toán, chốt tất toán) — chỉ chạy khi chấp nhận thêm phiếu thử vào DB demo;
xong thì dọn + gieo lại (`tools\may_thu\don_sach_hai_ben.ps1` chủ dự án chạy → `tools\may_thu\gieo_bo_sach.py`):
```
thu_cach_tra · thu_dinh_khoan · thu_lo_hong_23_09 · thu_loai_xe · thu_kho_xe_23_09 · thu_tao_so · thu_tien_te · thu_luong_api
thu_phieu_linh (chốt tất toán THẬT một tài xế — không bỏ chốt được) · thu_chi_tam_ung_ke_toan · thu_tao_so_that · thu_xe_thue_ke_toan
```

Bộ lỗi thời ở `kiem/loi_thoi/` (đọc `loi_thoi/README.md`); công cụ đo tải `do_*.py` chỉ chạy trên DB `epl_lao_tai`.

## Thêm một module mới

1. Tạo `frontend/modules/<tên>/` với ba tệp `<tên>.html`, `<tên>.css`, `<tên>.js`.
2. Trong `.js`: `EPL.modules['<tên>'] = { init(root, ctx) {…}, onLang() {…} }`.
3. Thêm một dòng vào `MODULES` trong `js/chung.js` (id, nhóm, khoá tên, icon, vai được thấy).
4. Thêm khoá `nav_…`, `title_<tên_gạch_dưới>` và mọi chữ trên màn vào `frontend/js/ngon_ngu.js` (đủ `vi` · `lo` · `en`), chạy `kiem/thu_khoa_dich.py`.
5. API mới thì thêm một tệp `routes/<tên>.py` và đăng ký trong `main.py`; phân quyền cả API lẫn giao diện (`services/phan_quyen.py`).
6. Thêm module vào `MODULES` của `kiem/thu_giao_dien.js` và chạy bộ kiểm giao diện.
