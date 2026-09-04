/**
 * Hai bảng Master Data: Danh mục loại xe và Đội xe / Biển số.
 *
 * Rà từng nút Thêm / Sửa / Xóa của cả hai bảng bằng cách gọi thật lên máy chủ.
 * Kết quả: **mọi nút đều thật**, có gọi API và có ghi vào cơ sở dữ liệu — khác
 * với nút xóa loại xe ở màn Công thức giá thành trước đó, vốn chỉ gỡ thẻ khỏi
 * màn hình rồi báo thành công.
 *
 * Nhưng lộ ra ba lỗi trên chính hàng của bảng đội xe, đều thấy được trên dữ
 * liệu thật:
 *
 *   1. `image_url` trỏ tới tệp không còn tồn tại (404) nên thẻ `<img>` hiện
 *      ALT TEXT tràn vào giữa ô biển số — "Vehicle DEMO-61H-112.34".
 *   2. Xe không gán loại xe thì ô "Loại Phương Tiện" để trống trơn. Nhưng
 *      không có loại thì không có công thức giá thành, và năng lực chở của xe
 *      không đối chiếu được với chuẩn nào cả.
 *   3. Năng lực chở của XE và của LOẠI XE là hai con số riêng, và điều phối
 *      dùng con số của XE. Nên một chiếc gán loại "Xe tải 10 tấn" vẫn có thể
 *      khai 28 tấn mà không ai thấy.
 */
const assert = require('assert');
const fs = require('fs');
const path = require('path');

const frontendRoot = path.join(__dirname, '..');
const app = fs.readFileSync(path.join(frontendRoot, 'js', 'app.js'), 'utf8');
const html = fs.readFileSync(path.join(frontendRoot, 'index.html'), 'utf8');

function bodyOf(marker, stop) {
  const start = app.indexOf(marker);
  assert.ok(start > 0, `không tìm thấy ${marker}`);
  const end = app.indexOf(stop, start);
  return app.slice(start, end > start ? end : start + 6000);
}

// --- 1. Mọi nút của hai bảng đều phải gọi API thật ------------------------

const HANDLERS = [
  ['deleteVehType', 'DELETE', 'api/vehicle-types/'],
  ['saveVehType', 'POST', 'api/vehicle-types'],
  ['deleteFioriVehicle', 'DELETE', 'api/vehicles/'],
  ['saveFioriVehicle', 'POST', 'api/vehicles'],
];

HANDLERS.forEach(([name, method, endpoint]) => {
  const fn = bodyOf(`window.${name} = `, String.fromCharCode(10) + '};');
  assert.match(fn, /fetch\(/, `${name} phải gọi API, không chỉ sửa màn hình`);
  assert.ok(fn.includes(endpoint), `${name} phải gọi đúng ${endpoint}`);
  assert.ok(
    fn.includes(`method: '${method}'`) || fn.includes(`method: "${method}"`),
    `${name} phải dùng ${method}`
  );
});

// Xóa là việc không lùi lại được — phải hỏi lại trước.
['deleteVehType', 'deleteFioriVehicle'].forEach(name => {
  const fn = bodyOf(`window.${name} = `, String.fromCharCode(10) + '};');
  assert.match(fn, /confirm\(/, `${name} phải hỏi lại trước khi xóa`);
});

// Nút bút chì phải nạp được dữ liệu cũ vào form, nếu không "sửa" thành "tạo mới".
{
  const fn = bodyOf('window.openVehTypeForm = ', String.fromCharCode(10) + '};');
  assert.match(fn, /vehTypes\.find/, 'sửa loại xe phải nạp bản ghi cũ');
  assert.match(fn, /vt-max-weight/, 'phải điền lại tải trọng cũ');
}
{
  const fn = bodyOf('window.editFioriVehicle = ', String.fromCharCode(10) + '};');
  assert.match(fn, /fioriVehicles\.find/, 'sửa xe phải nạp bản ghi cũ');
  assert.match(fn, /fiori-veh-id'\)\.disabled = true/, 'biển số là khóa chính nên không cho sửa');
}

// --- 2. Ảnh 404 không được hiện alt text tràn vào bảng -------------------

{
  const fn = bodyOf('function renderFioriVehicles', String.fromCharCode(10) + '}');
  assert.match(fn, /onerror=/, 'ảnh lỗi phải tự đổi sang icon xe');
  assert.match(fn, /data-fallback=/, 'phải có sẵn phần thay thế');
  // alt rỗng: alt có chữ thì chính chữ đó tràn vào ô khi ảnh 404.
  assert.match(fn, /alt=""/, 'alt phải để rỗng, tên xe đưa vào title');
  assert.match(fn, /escapeHtml\(v\.image_url\)/, 'đường dẫn ảnh phải được thoát');
}

// --- 3. Xe chưa gán loại xe phải được nêu ra -----------------------------

{
  const fn = bodyOf('function renderFioriVehicles', String.fromCharCode(10) + '}');
  assert.match(fn, /hasType/, 'phải phân biệt xe chưa gán loại');
  assert.match(fn, /Chưa gán loại xe/, 'ô trống phải nói rõ vấn đề');
  assert.match(fn, /escapeHtml\(typeText\)/, 'tên loại xe phải được thoát');
}
assert.match(html, /\.fv-untyped\s*\{/, 'trạng thái chưa gán loại phải có kiểu riêng');

// --- 4. Năng lực xe vượt chuẩn loại xe phải được cảnh báo ---------------

{
  const fn = bodyOf('function renderFioriVehicles', String.fromCharCode(10) + '}');
  assert.match(fn, /typeCap/, 'phải đối chiếu với chuẩn của loại xe');
  assert.match(fn, /vehCap > typeCap/, 'chỉ cảnh báo khi xe khai VƯỢT chuẩn loại');
  assert.match(fn, /vượt chuẩn loại/);
  // Không được cảnh báo bừa khi thiếu dữ liệu để so.
  assert.match(fn, /hasType && typeCap && vehCap/, 'thiếu một trong hai con số thì không so được');
}
assert.match(html, /\.fv-cap-warn\s*\{/, 'cảnh báo vượt chuẩn phải có kiểu riêng');

console.log('master-data-fleet-ui: tất cả kiểm tra đã qua');
