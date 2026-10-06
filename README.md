# EPL Lào — Quản lý vận tải theo Excel của bên Lào

Bản làm lại của EPL_System cho khách Lào, **đúng theo tệp Excel họ đang dùng** (`DOCS/ຂົນສົ່ງ EPL.xlsx`) và bản giao diện họ đã duyệt (`EPL-Transport-UI.html`). Không Trip, không báo giá, không công thức giá thành — một tờ **phiếu xuất xe** là đơn vị làm việc duy nhất. Xem [DOCS/md/BAN_DO_CHUC_NANG.md](DOCS/md/BAN_DO_CHUC_NANG.md) (bản Word ở `DOCS/word/`) để biết từng chức năng của EPL_System đi đâu.

**Mô tả đầy đủ nghiệp vụ, cơ sở dữ liệu và API: [DOCS/md/NGHIEP_VU_DB_API.md](DOCS/md/NGHIEP_VU_DB_API.md)** (bản Word ở `DOCS/word/`).

**Tự thử phần mềm theo từng vai: [DOCS/md/HUONG_DAN_THU_TUNG_VAI.md](DOCS/md/HUONG_DAN_THU_TUNG_VAI.md)** — kịch bản một chuyến hàng đi qua 8 vai, kèm danh sách chỗ phải bị chặn.

## Chạy

```
cd D:\Demo_Lao\EPL_LAO_REAL
python backend\app\seed.py                       # lần đầu: dựng bảng + gieo dữ liệu mẫu từ Excel
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8010 --no-access-log
```
Hoặc bấm đúp `chay.bat`. Mở **http://localhost:8010** — giao diện và API cùng một cổng.

Tài khoản demo (mật khẩu tất cả là `1234`): `thabok` Admin Thà Bốc · `ketoan` KT Thu/Chi Viêng Chăn (xác nhận mục I–II) · `ketoancp` KT Chi phí VC (kiểm, ghi sổ mục IV–VI) · `khonl` KT kho xăng dầu VC · `quyvc` Thủ quỹ VC · `quytb` Quỹ tiền mặt cảng cạn · `doanhthu` KT Doanh thu VC · `admin` · `tx01` `tx02` `tx03` tài xế · `khotb` `khovc` thủ kho nhiên liệu.

Màn đăng nhập liệt kê sẵn mười tài khoản này — bấm một cái là vào thẳng, khỏi gõ.

Cấu hình trong `.env` (không commit): `DATABASE_URL` trỏ vào DB **`epl_lao`** — DB riêng, cùng máy chủ PostgreSQL với EPL_System; `EPL_LAO_SECRET` để ký phiên đăng nhập.

## Cấu trúc — một module một bộ ba tệp

```
backend/app/
  main.py            FastAPI, phục vụ frontend ở / và API ở /api
  database.py        kết nối PostgreSQL, create_all (không migration)
  models.py          bảng — theo đúng Excel, có gì khai đó
  seed.py            gieo dữ liệu mẫu (5 phiếu chép từ Excel + một cặp DO gom/giao của luồng mới)
  services/          tinh_toan.py (phép tính phiếu) · phan_quyen.py (ai làm gì) · bao_mat.py (đăng nhập)
                     kho_hang.py (kho hàng ở bãi, dây nối hai DO) · chung_tu.py (sổ chứng từ) · day_ke_toan.py (đẩy sang kế toán)
  routes/            dang_nhap · danh_muc · phieu · phieu_linh · tat_toan · theo_doi · vi_tri
                     tuyen · acc_code · bao_cao · kho · kho_hang · nha_cung_cap · quy_trinh · ban_hang
frontend/
  index.html         khung: đăng nhập, thanh điều hướng, nút ngôn ngữ, chỗ nạp module
  css/chung.css      bảng màu bên Lào đã duyệt, nút, bảng, ô nhập
  vendor/leaflet/    thư viện bản đồ để sẵn trong dự án, KHÔNG gọi CDN
  vendor/chartjs/    thư viện biểu đồ (Tổng quan) để sẵn trong dự án, KHÔNG gọi CDN
  js/chung.js        gọi API, ngôn ngữ, đăng nhập, nạp module theo #/ten-module
  js/ngon_ngu.js     từ điển Việt · Lào · Anh (1.282 khoá) — SINH TỰ ĐỘNG, đừng sửa tay
  modules/<tên>/     <tên>.html · <tên>.css · <tên>.js — sai đâu mở đúng thư mục đó
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

27 module: **Tổng quan** (bốn ô số kèm xu hướng 6 tháng, thanh xem nhanh, dòng thời gian từng chuyến, doanh thu và chi phí theo ngày, cơ cấu chi, hao hụt cân, hiệu suất xe) · Theo dõi phiếu vận chuyển · **Theo dõi tuyến** (trung tâm điều hành: dải ô số, danh sách chuyến, **bản đồ tuyến**, tiến độ từng chặng, sổ sự cố, duyệt báo hỏng) · Phiếu xuất xe · Hoá đơn vận chuyển · **Hoá đơn gộp tháng** (khách hợp đồng: một tờ cho cả tháng, thu tiền ở tờ và tự phân bổ về từng phiếu) · **Chứng từ** (phiếu tạm ứng · **phiếu lĩnh nhiên liệu có mã QR** · phiếu thu) · **Phiếu của tôi** (màn tài xế: tiền tạm ứng, xuất phát, báo hỏng, khai đổ dầu dọc đường, **chia sẻ vị trí GPS**) · **Cấp phát** (thủ kho cấp dầu, quỹ chi tạm ứng, quét mã QR) · **Xe liên kết** (kèm danh mục **chủ xe**: phí, ngưỡng tấn, cách trả riêng từng chủ; quỹ **trả gộp** nhiều phiếu một đợt) · Tiền chuyến & tiền nước tài xế · **Tất toán tài xế** (theo tháng) · Theo dõi nhà cung cấp · **Kho hàng** (tồn quặng ở bãi theo từng lô, sổ nhập xuất, kế toán **điều chỉnh tồn** có lý do) · Kho nhiên liệu · **Điểm đổ nhiên liệu** · Kho phụ tùng · **Thẻ cao tốc** (số dư thẻ, nạp tiền, cấn trừ cước) · **Lệnh sửa chữa** (xe nằm bãi sửa hoặc bảo dưỡng định kỳ, không gắn phiếu) · Khách hàng (kèm **bảng giá khách × tuyến**, phiếu tự điền đơn giá) · **Xe** (hai tab đầu kéo / rơ-moóc, chip lọc, thẻ hồ sơ, hộp hồ sơ bảy tab: chung · pháp lý · kỹ thuật · rơ-moóc lắp/tháo có lịch sử · **lịch xe theo tuần** · chi phí sửa chữa từ mục V · phiếu gần đây) · **Tài xế & bằng lái** (hồ sơ, bằng lái và lịch sử gia hạn, xe thường lái, lịch tuần, và cột **Kết luận** tự nói ai đủ điều kiện điều xe) · **Tỷ giá** (đặt tỷ giá quy về Kíp cho phiếu mới, có lịch sử và máy tính quy đổi) · **Tuyến đường** (chặng, km, BOT) · Quy trình & trách nhiệm · Tài khoản.

Quy tắc kho: nhiên liệu đổ ở kho Thà Bốc → khi kế toán kho ghi sổ mục III thì tự sinh dòng xuất kho; sửa xe lấy phụ tùng từ kho → trừ tồn ngay lúc khai; mua ngoài → công nợ. Xe nhà định khoản `625/…`, `614/…`; xe liên kết `4022/…`; kho `1371`, nhà cung cấp `4021`, tiền `1011/1012/1021/1022` theo mã anh Khampla cấp 22/09. Chi tiết trong [DOCS/md/BAN_DO_CHUC_NANG.md](DOCS/md/BAN_DO_CHUC_NANG.md) mục 4b.

Điều hướng có **hai kiểu xem**, đổi ở nút tên người dùng → Cài đặt giao diện: *thanh bên* (thấy hết chức năng, có số việc đang chờ cạnh từng mục, thu gọn còn biểu tượng được) và *thanh trên* hai tầng (nhường trọn chiều ngang cho bảng). Máy nào nhớ theo máy đó.

Một chuyến quặng đi qua **hai phiếu**: *DO gom hàng* (mỏ → bãi, có dòng hàng và cân tại mỏ, cước riêng cho chặng gom) rồi *DO giao hàng* (bãi → cảng, chọn lấy từ lô nào trong kho bãi, có cước và hoá đơn). Bãi Thà Bốc đứng giữa như một bưu cục: DO gom về thì **nhập kho hàng**, DO giao lấy đi thì **xuất kho hàng**, và dây nối hai phiếu chính là lô hàng đó. Xe hai chặng có thể khác nhau; hao hụt ghi thành một dòng ngay trên phiếu.

Xe về thì kế toán bấm **Khoá phiếu** (máy rà km, hao hụt, phiếu quặng đính kèm, mục chưa kiểm rồi mới cho khoá); khoá xong mới xuất hoá đơn và mới trả được chủ xe liên kết. Bán phụ tùng, xăng dầu cho bên ngoài ở màn **Bán hàng**. Nghiệp vụ còn vài chỗ chờ bên EPL xác nhận (mã tài khoản, tên người giữ từng tài khoản kế toán): danh sách việc đang treo ở [DOCS/md/CONG_VIEC_CHO_ANH_KHAMPLA_CHOT.md](DOCS/md/CONG_VIEC_CHO_ANH_KHAMPLA_CHOT.md), bộ câu hỏi gửi bên EPL ở [DOCS/md/CAU_HOI_NGHIEP_VU_EPL.md](DOCS/md/CAU_HOI_NGHIEP_VU_EPL.md), bản tiếng Lào `DOCS/md/ຄຳຖາມວິຊາການ_EPL.md` và tiếng Anh `DOCS/md/EPL_BUSINESS_QUESTIONS.md` cùng nội dung (tất cả có bản Word ở `DOCS/word/`).

Mỗi bước sinh ra tiền hoặc hàng để lại một tờ trong **Sổ chứng từ** (màn Chứng từ → tab Sổ chứng từ), và **đẩy được sang module kế toán của anh Khang** bằng một nút (Sếp đặt địa chỉ API + token ngay trong màn; hợp đồng JSON ở [DOCS/md/HOP_DONG_API_ANH_KHANG.md](DOCS/md/HOP_DONG_API_ANH_KHANG.md)): ai nhập ô nào, tờ nào sinh ở bước nào, định khoản gợi ý, mã còn thiếu — xem [DOCS/md/NGHIEP_VU_DB_API.md](DOCS/md/NGHIEP_VU_DB_API.md) mục A6, và hợp đồng nối kế toán ở [DOCS/md/HOP_DONG_API_ANH_KHANG.md](DOCS/md/HOP_DONG_API_ANH_KHANG.md).

**Tiền tệ.** Cước ký bằng tiền nào thì phiếu ghi tiền đó — USD · Kíp · Nhân dân tệ · Bath — và xe liên kết có thể thuê bằng tiền khác với tiền bán. Kíp là tiền gốc: tỷ giá đặt ở màn **Tỷ giá** rồi khoá vào phiếu lúc lập (sửa sau không đụng phiếu cũ), mọi con số tổng trong báo cáo quy về Kíp kèm dòng chia theo từng loại tiền. Khách trả tiền thì **mỗi lần thu là một dòng** có ngày, số tiền, tiền tệ và tỷ giá ngày thu (hoá đơn USD mà chuyển Kíp là chuyện thường); trạng thái *chưa thu · một phần · đủ* do tổng các dòng đó quyết định, không bấm tay. Chi tiết ở [DOCS/md/NGHIEP_VU_DB_API.md](DOCS/md/NGHIEP_VU_DB_API.md) mục A7.

Ngôn ngữ: **Tiếng Việt · ພາສາລາວ · English · VI + ລາວ** (nút ở góc trên phải và trên màn đăng nhập).

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
4. Thêm khoá `nav_…` và `title_<tên_gạch_dưới>` vào `KHOA_MOI` trong script sinh từ điển rồi sinh lại `ngon_ngu.js`.
5. API mới thì thêm một tệp `routes/<tên>.py` và đăng ký trong `main.py`.
