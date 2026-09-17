# Trang đăng nhập EPL – HTML / CSS / JS thuần

Ba file độc lập, không phụ thuộc thư viện nào, ghép được vào bất kỳ module/web nào:

| File | Vai trò |
|---|---|
| `login.html` | Cấu trúc trang: nửa trái thương hiệu + sơ đồ tuyến, nửa phải form và khung chọn nhanh theo vai trò |
| `login.css` | Giao diện (màu xanh EPL, font Be Vietnam Pro + Noto Sans Lao từ Google Fonts), responsive xuống mobile |
| `login.js` | Chuyển ngôn ngữ (vi / lo / en / vi+lo), chọn nhanh tài khoản, hiện/ẩn mật khẩu, xử lý đăng nhập, lưu phiên |

## Cách ghép

1. Chép 3 file vào thư mục web của bạn (giữ cùng cấp hoặc sửa `href`/`src` trong `login.html`).
2. Trong `login.html`, sửa khối `window.EPL_LOGIN_CONFIG`:

```js
window.EPL_LOGIN_CONFIG = {
  redirect: "/app/index.html",                 // trang vào sau khi đăng nhập
  authenticate: async (username, password) => { // gọi API thật
    const r = await fetch("/api/login", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ username, password }) });
    if (!r.ok) return null;                      // null = sai tài khoản → hiện lỗi
    return await r.json();                       // { u, name, role, token }
  },
  showQuickPick: false,                          // ẩn danh sách tài khoản demo
  storageKey: "epl_user",                        // khóa lưu phiên
};
```

Không đặt `authenticate` → trang chạy chế độ demo: 12 tài khoản trong `USERS` (login.js), mật khẩu `1234`.

3. Sau khi đăng nhập, thông tin người dùng nằm ở `localStorage` (nếu tick Ghi nhớ) hoặc `sessionStorage` dưới khóa `storageKey`, dạng `{ u, name, role, token, lang }`. Module khác đọc bằng:

```js
const user = JSON.parse(localStorage.getItem("epl_user") || sessionStorage.getItem("epl_user") || "null");
if (!user) location.href = "login.html";
```

Đăng xuất: xóa khóa đó rồi chuyển về `login.html`.

## Tùy biến

- **Chuỗi ngữ**: đối tượng `STR` trong `login.js` (3 ngôn ngữ; chế độ `vi+lo` lấy `vi` làm chính, `lo` phụ). Bản Lào cần người bản ngữ rà lại.
- **Tài khoản chọn nhanh**: mảng `USERS` (hoặc truyền `users` trong config), nhóm theo `role`: `admin` · `acct` · `wh` · `cash` · `drv`.
- **Logo**: thay ô chữ `EPL` (`.hero__logo`) bằng `<img>`.
- **Sơ đồ tuyến**: khối `<svg class="route">` trong `login.html` — sửa tên điểm/tọa độ hoặc bỏ hẳn.
- **Màu**: biến `--g900 … --g100` đầu `login.css`.
