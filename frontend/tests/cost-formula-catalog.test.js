/**
 * Danh mục loại xe ở màn "Quản lý công thức giá thành theo loại xe".
 *
 * Ba vấn đề của bản cũ, mỗi cái là một kiểu nói dối khác nhau:
 *
 *   1. Badge ghi cứng "4 Mẫu" trong index.html, nên nó sai cả khi danh mục
 *      trống (hiện "4 Mẫu" ngay cạnh dòng "Chưa có Loại Xe trong CSDL") lẫn khi
 *      tải được (thật ra chỉ có 3).
 *   2. Nút xóa chỉ gỡ thẻ khỏi màn hình rồi báo "Đã xóa Loại Xe khỏi danh mục"
 *      — bản ghi vẫn nằm nguyên trong cơ sở dữ liệu, tải lại trang là nó hiện
 *      về. Endpoint DELETE /api/vehicle-types/{id} đã có sẵn, chỉ chưa bao giờ
 *      được gọi.
 *   3. Mỗi thẻ chỉ có tên xe cộng hai dòng chữ "Loại phương tiện CSDL" và
 *      "Cước định mức: CSDL" — không phải con số nào cả, chỉ là nhãn nói "lấy
 *      từ cơ sở dữ liệu".
 */
const assert = require('assert');
const fs = require('fs');
const path = require('path');

const frontendRoot = path.join(__dirname, '..');
const app = fs.readFileSync(path.join(frontendRoot, 'js', 'app.js'), 'utf8');
const html = fs.readFileSync(path.join(frontendRoot, 'index.html'), 'utf8');

// --- 1. Không còn thẻ mẫu viết cứng ---------------------------------------

// Bốn thẻ "mẫu" viết cứng trong index.html chính là nguồn của badge "4 Mẫu":
// chúng không liên quan gì đến Master Data thật.
assert.ok(!/class="veh-type-card/.test(html), 'thẻ loại xe phải do JavaScript dựng từ cơ sở dữ liệu');
assert.ok(!/preset-1'/.test(html) || !/veh-type-card/.test(html), 'không được giữ lại thẻ mẫu preset');
assert.match(html, /id="formula-vehicle-types-list"/, 'phải còn khung để JavaScript dựng vào');

// --- 2. Nút xóa phải xóa THẬT ---------------------------------------------

{
  const start = app.indexOf('window.deleteVehicleTypeCard');
  assert.ok(start > 0, 'phải còn hàm xóa loại xe');
  const fn = app.slice(start, app.indexOf(String.fromCharCode(10) + '};', start));

  assert.match(fn, /method: 'DELETE'/, 'phải gọi API xóa, không chỉ gỡ thẻ khỏi màn hình');
  assert.match(fn, /api\/vehicle-types\//, 'phải gọi đúng endpoint');
  assert.match(fn, /encodeURIComponent/, 'mã loại xe phải được mã hóa khi ghép vào URL');
  // Gỡ thẻ khỏi DOM rồi báo thành công chính là lỗi cũ.
  assert.ok(!/card\.remove\(\)/.test(fn), 'không được tự gỡ thẻ; phải tải lại từ máy chủ');
  assert.match(fn, /renderDynamicFormulaVehicleTypes\(\)/, 'xóa xong phải vẽ lại từ dữ liệu mới');
  // Máy chủ trả 200 kèm "Không tìm thấy" khi bản ghi đã biến mất.
  assert.match(fn, /Không tìm thấy/, 'không được báo thành công cho một việc không xảy ra');
  assert.match(fn, /catch/, 'lỗi mạng phải được báo, không im lặng');
  assert.match(fn, /showToast\([^)]*'error'\)/, 'thất bại phải hiện như lỗi');
  // Xóa loại xe ảnh hưởng tới các xe đang gán — phải nói trước.
  assert.match(fn, /confirm\(/, 'phải hỏi lại trước khi xóa');
  assert.match(fn, /mất định mức giá thành/, 'lời hỏi phải nói rõ hệ quả');
}

// --- 3. Thẻ phải mang con số thật -----------------------------------------

{
  const start = app.indexOf('window.renderDynamicFormulaVehicleTypes');
  const fn = app.slice(start, app.indexOf(String.fromCharCode(10) + '};', app.indexOf('firstCard', start)));

  // Hai nhãn rỗng cũ phải biến mất. (Tên chúng còn trong ghi chú giải thích vì
  // sao đổi, nên chỉ xét phần dung hàm chứ không xét cả tệp.)
  assert.ok(!/subLabel/.test(fn), 'nhãn rỗng "Loại phương tiện CSDL" phải được dỡ');
  assert.ok(!/tariffLabel/.test(fn), 'nhãn rỗng "Cước định mức: CSDL" phải được dỡ');

  // Và được thay bằng số thật, có đơn vị.
  ['max_weight', 'volume_capacity_m3', 'pallet_capacity', 'base_rate'].forEach(field => {
    assert.ok(fn.includes(field), `thẻ phải hiện ${field}`);
  });
  assert.match(fn, /m³/, 'thể tích phải có đơn vị');
  assert.match(fn, /pallet/, 'số pallet phải có đơn vị');
  assert.match(fn, /đ\/km/, 'đơn giá phải có đơn vị');
  // Chưa đặt đơn giá là một sự thật cần thấy, không phải một ô trống.
  assert.match(fn, /Chưa đặt đơn giá nền/);
  // Icon lấy từ dữ liệu, chỉ dùng 🚚 khi thiếu.
  assert.match(fn, /vehicleType\.icon \|\| '🚚'/);
  // Tên loại xe do người dùng nhập nên phải thoát khi vào innerHTML.
  assert.match(fn, /escapeHtml\(vName\)/);
  assert.match(fn, /escapeHtml\(vehicleType\.id\)/);
}

// --- 4. Trạng thái rỗng phải chỉ được đường đi -----------------------------

// "Vui lòng thêm tại Tab 3!" — người dùng không đếm tab, và cũng không bấm được
// vào một dòng chữ.
{
  // Chỉ xét chuỗi THỰC SỰ hiện ra, bỏ các dòng ghi chú giải thích vì sao đổi.
  const code = app
    .split(String.fromCharCode(10))
    .filter(line => !/^\s*(\/\/|\/?\*)/.test(line))
    .join(String.fromCharCode(10));
  assert.ok(!/Tab 3/.test(code), 'không được nhắc "Tab 3"; phải gọi đúng tên tab');
}
assert.match(app, /3\. Loại Phương Tiện/, 'phải gọi đúng tên tab như trên màn hình');
assert.match(app, /openVehicleTypesTab/, 'phải mở thẳng được tab đó');
{
  const start = app.indexOf('window.openVehicleTypesTab');
  const fn = app.slice(start, app.indexOf(String.fromCharCode(10) + '};', start));
  assert.match(fn, /md-tab-veh-types/, 'phải mở đúng tab loại phương tiện');
}

// --- 5. Đếm số thật, và nói rõ khi đang lọc -------------------------------

{
  const cell = /id="formula-vehicle-types-count"[^>]*>([^<]*)</.exec(html);
  assert.ok(cell, 'phải có ô đếm số loại xe');
  assert.ok(!/\d/.test(cell[1]), `badge viết sẵn "${cell[1].trim()}" — con số phải lấy từ dữ liệu`);
  assert.match(app, /counter\.innerText = keyword/, 'đang lọc thì con số phải khác');
}

// --- 6. CSS: thẻ đang chọn phải khác cả hình dạng -------------------------

assert.match(html, /\.veh-type-card\s*\{/, 'thẻ phải có CSS riêng, không phải style nội tuyến');
assert.match(html, /\.veh-type-card\.active\s*\{[^}]*border-left-width/, 'thẻ đang chọn phải khác cả hình dạng, không chỉ khác màu');
assert.match(html, /\.vt-rate-missing\s*\{/, 'trạng thái thiếu đơn giá phải có kiểu riêng');

console.log('cost-formula-catalog: tất cả kiểm tra đã qua');
