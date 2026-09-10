/**
 * Hồ sơ xe: loại xe hiện theo TÊN, chọn theo MÃ; bãi chọn từ DANH MỤC.
 *
 * Chủ dự án soi ảnh màn Đội xe: cột loại xe hiện `DEMO-VT-TRUCK10` (mã, không
 * phải tên); mở hồ sơ thì ô loại xe trống; "Bãi / Chi nhánh" và "Mã bãi" là hai
 * ô gõ tự do không có danh mục. Ba điều khoá lại ở giao diện.
 */
const assert = require('assert');
const fs = require('fs');
const path = require('path');
const ROOT = path.join(__dirname, '..');
const app = fs.readFileSync(path.join(ROOT, 'js', 'app.js'), 'utf8');
const html = fs.readFileSync(path.join(ROOT, 'index.html'), 'utf8');

function than(neo, ket) {
  const i = app.indexOf(neo); assert.ok(i >= 0, 'không thấy ' + neo);
  const j = ket ? app.indexOf(ket, i) : -1; return app.slice(i, j > 0 ? j : i + 8000);
}

// 1. Ô chọn loại xe: giá trị là MÃ, nhãn là tên.
{
  const nap = than("['qt-cargo-type', 'fiori-veh-type'].forEach", '// 6.7');
  assert.ok(/<option value="\$\{escapeHtml\(vt\.id\)\}">\$\{escapeHtml\(vt\.name\)\}/.test(nap),
    'option loại xe phải có value = mã, nhãn = tên');
  assert.ok(!/<option value="\$\{vt\.name\}"/.test(nap), 'không còn value theo tên');
}
// 2. Dòng xe hiện TÊN loại; mở hồ sơ chọn theo mã (xe cũ còn lưu tên thì tra mã).
{
  const ve = than('function renderFioriVehicles(data) {', 'window.editFioriVehicle');
  assert.ok(/v\.vehicle_type_name \|\|/.test(ve), 'dòng xe phải ưu tiên vehicle_type_name');
  const mo = than('window.editFioriVehicle = function', 'window.saveFioriVehicle');
  assert.ok(/veh\.vehicle_type_id/.test(mo), 'mở hồ sơ phải chọn theo vehicle_type_id');
  assert.ok(/napDanhMucBai\(veh\.depot_code/.test(mo), 'mở hồ sơ phải nạp danh mục bãi');
}
// 3. Bãi là ô chọn từ /api/depots; tên bãi tự điền theo mã; không còn ô gõ tay.
{
  assert.ok(/<select class="fiori-input" id="fiori-veh-depot-code">/.test(html), 'ô mã bãi phải là <select>');
  assert.ok(!/<input type="text" class="fiori-input" id="fiori-veh-depot"/.test(html), 'không còn ô gõ tên bãi');
  const nap = than('async function napDanhMucBai(', 'function renderFioriVehicles');
  assert.ok(/\/api\/depots/.test(nap), 'danh mục bãi đọc từ GET /api/depots');
  assert.ok(/không có trong danh mục/.test(nap), 'mã bãi lạ của xe cũ phải hiện ra, không âm thầm xoá');
  const luu = than('window.saveFioriVehicle', 'window.deleteFioriVehicle');
  assert.ok(/o\.dataset\.name \|\| o\.textContent/.test(luu), 'tên bãi lấy theo mã đã chọn');
}
// 4. Màn Điều phối gom và lọc theo tên bãi từ danh mục.
{
  assert.ok(/String\(v\.depot_name \|\| v\.depot \|\| ''\)\.trim\(\) \|\| '\(chưa gán bãi\)'/.test(app));
  assert.ok(/ds\.map\(v => v\.depot_name \|\| v\.depot\), 'Tất cả bãi'/.test(app));
}
console.log('loai-xe-va-bai-tren-ho-so-xe: OK');
