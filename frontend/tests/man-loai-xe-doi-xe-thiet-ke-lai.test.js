/**
 * Màn "Loại xe & Đội xe" — thiết kế lại 10/09 theo yêu cầu của chủ dự án (ảnh 5).
 *
 * Bản cũ: hai "thẻ thư mục" to, rồi bên dưới một tiêu đề dài lặp lại đúng chữ
 * trên thẻ — hai lớp tiêu đề cho một màn; bảng xe chỉ có 4 cột và cột trạng
 * thái so chuỗi nhãn; không có bộ lọc theo bãi / loại xe; không có số liệu.
 *
 * Bản mới: một dòng đầu trang + bộ chuyển tab gọn (kèm số đếm), một dải số liệu
 * đếm từ MÃ trạng thái thật (bấm vào để lọc), bảng loại xe có cột "xe thuộc
 * loại" bấm sang được, bảng đội xe có bãi / năng lực đầy đủ / trạng thái theo
 * mã / hạn pháp lý gần nhất, và bộ lọc bãi–loại–trạng thái. Mọi thứ đọc từ
 * máy chủ, không con số nào ghi cứng.
 */
const assert = require('assert');
const fs = require('fs');
const path = require('path');
const ROOT = path.join(__dirname, '..');
const app = fs.readFileSync(path.join(ROOT, 'js', 'app.js'), 'utf8');
const html = fs.readFileSync(path.join(ROOT, 'index.html'), 'utf8');
const css = fs.readFileSync(path.join(ROOT, 'css', 'styles.css'), 'utf8');
const lang = JSON.parse(fs.readFileSync(path.join(ROOT, 'js', 'lang.json'), 'utf8'));

function than(neo, ket) {
  const i = app.indexOf(neo); assert.ok(i >= 0, 'không thấy ' + neo);
  const j = ket ? app.indexOf(ket, i) : -1; return app.slice(i, j > 0 ? j : i + 9000);
}
const vung = html.slice(html.indexOf('<div id="md-tab-veh-types"'), html.indexOf('<div class="fiori-object-page" id="fiori-object-page"'));

// 1. Đầu trang một lớp: không còn tiêu đề dài lặp lại; có bộ chuyển tab kèm số đếm.
assert.ok(/class="fleet-head"/.test(vung), 'phải có đầu trang gọn');
assert.ok(/class="fleet-seg"/.test(vung) && /id="fleet-seg-types-count"/.test(vung) && /id="fleet-seg-fleet-count"/.test(vung),
  'bộ chuyển tab phải kèm số đếm');
assert.ok(!/title_manage_veh_types/.test(vung) && !/title_fleet_mgmt/.test(vung),
  'không còn hai tiêu đề dài lặp lại chữ trên thẻ');
assert.ok(/id="fleet-kpi-strip"/.test(vung), 'phải có dải số liệu');

// 2. Bảng loại xe: cột xe thuộc loại, tốc độ kế hoạch; hàng bấm sang tab Đội xe đã lọc.
assert.ok(/data-i18n="th_vt_vehicles"/.test(vung) && /data-i18n="th_vt_speed"/.test(vung));
{
  const t = than('function renderVehTypesTable(data) {', 'window.locDoiXeTheoLoai');
  assert.ok(/soXe\.set/.test(t), 'đếm xe thuộc loại từ đội xe thật, khớp mã hoặc tên');
  assert.ok(/locDoiXeTheoLoai\(/.test(t), 'số xe phải bấm sang được tab Đội xe');
  assert.ok(!/vName\.replace\(\/Xe tải thùng 10 tấn/.test(t), 'không còn dịch tên loại bằng regex chuỗi cứng');
}

// 3. Bảng đội xe: 7 cột, trạng thái theo mã, bãi, hạn pháp lý.
['th_license_plate', 'th_veh_type_col', 'th_fleet_depot', 'th_fleet_capacity', 'th_fleet_status', 'th_fleet_legal', 'th_actions']
  .forEach(k => assert.ok(vung.includes(`data-i18n="${k}"`), 'thiếu cột ' + k));
{
  const r = than('function renderFioriVehicles(data) {', 'function filterFioriVehicles');
  assert.ok(/fleet-badge s-\$\{maTT\}/.test(r), 'huy hiệu trạng thái theo mã');
  assert.ok(/hanPhapLyXe\(v\)/.test(r), 'phải tính hạn pháp lý gần nhất');
  assert.ok(/v\.depot_name \|\| v\.depot/.test(r), 'cột bãi ưu tiên tên bãi trong danh mục');
  assert.ok(/data-fallback=/.test(r), 'ảnh lỗi phải có phần thay thế');
  assert.ok(!/'Sẵn sàng'/.test(r), 'không so chuỗi nhãn tiếng Việt');
}

// 4. Bộ lọc: bãi từ /api/depots, loại từ vehTypes, trạng thái theo mã; dải số liệu bấm để lọc.
assert.ok(/id="fleet-filter-depot"/.test(vung) && /id="fleet-filter-type"/.test(vung));
assert.ok(/<option value="on_trip"/.test(vung) && !/<option value="Sẵn sàng"/.test(vung), 'ô trạng thái theo mã, không theo nhãn');
{
  const f = than('function filterFioriVehicles() {', 'window.filterFioriVehicles');
  assert.ok(/fleet-filter-depot/.test(f) && /fleet-filter-type/.test(f) && /operational_status/.test(f));
  const k = than('function veKpiDoiXe()', 'window.locKpiDoiXe');
  ['available', 'on_trip', 'maintenance', 'out_of_service'].forEach(m => assert.ok(k.includes(m), 'KPI thiếu ' + m));
  assert.ok(/hanPhapLyXe/.test(k), 'KPI phải đếm xe sắp hết hạn pháp lý');
  const b = than('async function napBoLocDoiXe()', 'function nhanDich');
  assert.ok(/\/api\/depots/.test(b), 'bộ lọc bãi đọc từ danh mục');
  assert.ok(/ngoài danh mục/.test(b), 'bãi lạ trên xe vẫn lọc được, không âm thầm bỏ');
}

// 5. Ba hàm mở/đóng/lọc form còn nguyên (từng bị cắt mất khi thay bảng — bài này giữ chỗ).
['window.openFioriVehicleForm = function', 'window.closeFioriVehicleForm = function', 'window.editFioriVehicle = function']
  .forEach(n => assert.ok(app.includes(n), 'thiếu ' + n));

// 6. Khoá dịch đủ ba tiếng cho mọi nhãn mới.
['fleet_title', 'fleet_seg_types', 'fleet_seg_fleet', 'kpi_fleet_total', 'kpi_fleet_legal_due', 'th_vt_vehicles',
  'th_fleet_depot', 'th_fleet_legal', 'legal_days', 'vt_untyped'].forEach(k => {
  assert.ok(lang[k], 'thiếu khoá ' + k);
  ['vi', 'en', 'la'].forEach(t => assert.ok(String(lang[k][t] || '').trim(), `${k} thiếu ${t}`));
});

// 7. CSS có thật cho các lớp mới.
['.fleet-head', '.fleet-seg', '.fleet-kpis', '.fleet-table', '.fleet-badge.s-on_trip', '.fleet-legal.l-expired']
  .forEach(c => assert.ok(css.includes(c), 'CSS thiếu ' + c));

console.log('man-loai-xe-doi-xe-thiet-ke-lai: OK');
