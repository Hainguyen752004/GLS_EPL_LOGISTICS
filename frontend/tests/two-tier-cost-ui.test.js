/**
 * Giao diện giá thành hai tầng.
 *
 * Công thức thuộc về LOẠI xe; từng chiếc chỉ ghi đè vài con số. Điều quan trọng
 * nhất phải khóa lại: **ô để trống nghĩa là kế thừa**, và ô kế thừa KHÔNG được
 * gửi lên máy chủ như một giá trị đã đặt — nếu gửi, mọi xe sẽ có bản sao giá trị
 * của loại xe, và sửa công thức loại xe sẽ không còn tác dụng.
 *
 * Kèm theo một lỗi đã sửa: thẻ loại xe trước đây hiện `base_rate`, một trường
 * chỉ được ghi một lần lúc tạo loại xe và không hề được dùng để tính gì. Trong
 * khi đó nút "Lưu Cấu Hình Giá Thành" ghi vào bảng `cost_formulas` — hoàn toàn
 * khác. Nên sửa giá bên phải thì con số trên thẻ không bao giờ đổi.
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
  return app.slice(start, end > start ? end : start + 4000);
}

// --- 1. Ô để trống nghĩa là kế thừa ---------------------------------------

{
  const fn = bodyOf('window.saveVehicleCostOverrides = async function', String.fromCharCode(10) + '};');
  assert.match(fn, /String\(raw\)\.trim\(\) === ''/, 'phải nhận ra ô để trống');
  assert.match(fn, /return null/, 'ô để trống phải bị loại khỏi danh sách gửi lên');
  assert.match(fn, /\.filter\(Boolean\)/, 'chỉ gửi những mục thật sự đặt riêng');
  assert.match(fn, /method: 'PUT'/);
  assert.match(fn, /cost-overrides/, 'phải gọi đúng endpoint ghi đè');
  // Gửi mảng rỗng là quay về kế thừa hoàn toàn — phải nói rõ, không im lặng.
  assert.match(fn, /quay về kế thừa/);
  assert.match(fn, /'error'/, 'thất bại phải hiện như lỗi');
}

// --- 2. Phải thấy được con số gốc bên cạnh con số đã đổi ------------------

{
  const fn = bodyOf('function renderVehicleCostEditor()', String.fromCharCode(10) + '}');
  assert.match(fn, /row\.inherited/, 'phải hiện con số kế thừa từ loại xe');
  assert.match(fn, /is_overridden/, 'phải phân biệt mục đã đặt riêng');
  assert.match(fn, /placeholder="Kế thừa"/, 'ô trống phải nói rõ nó nghĩa là kế thừa');
  // Loại xe chưa có công thức thì nói ra, đừng để người dùng đặt giá riêng
  // chồng lên một nền không tồn tại.
  assert.match(fn, /has_type_formula/);
  assert.match(fn, /chưa có công thức/);
  // Tiền tệ linh hoạt, không viết cứng.
  assert.match(fn, /masterCostCurrencyCode\(\)/);
  assert.match(fn, /formatWorkflowCurrencyAmount/);
}

// --- 3. Thẻ loại xe không được nói dối ------------------------------------

{
  const fn = bodyOf('window.renderDynamicFormulaVehicleTypes', 'firstCard');
  const code = fn.split(String.fromCharCode(10))
    .filter(line => !/^\s*(\/\/|\/?\*)/.test(line))
    .join(String.fromCharCode(10));
  assert.ok(!/base_rate/.test(code), 'thẻ không được hiện base_rate');
  assert.match(code, /formula\.configured/, 'thẻ phải nói rõ đã cấu hình hay chưa');
}

// Lưu công thức xong thì thẻ phải vẽ lại — nếu không, con số trên thẻ vẫn là
// con số cũ và người dùng tưởng lưu không ăn.
{
  const fn = bodyOf('window.saveCostFormula = async function', String.fromCharCode(10) + '};');
  assert.match(fn, /renderDynamicFormulaVehicleTypes/, 'lưu công thức xong phải vẽ lại danh mục');
}

// Đổi tiền tệ cũng phải vẽ lại, vì thẻ hiện tiền.
{
  const fn = bodyOf('window.onMasterCostCurrencyChange', String.fromCharCode(10) + '};');
  assert.match(fn, /renderDynamicFormulaVehicleTypes/, 'đổi tiền tệ phải vẽ lại danh mục');
}

// --- 4. Ở đội 500 xe không được hỏi máy chủ 500 lần ----------------------

{
  const fn = bodyOf('window.loadVehicleOverrideCounts = async function', String.fromCharCode(10) + '};');
  assert.match(fn, /Promise\.allSettled/, 'phải gọi song song và chịu được lỗi lẻ');
  assert.match(fn, /\.slice\(0, 200\)/, 'phải có trần số lệnh gọi');
}

// --- 5. Khung chứa và CSS -------------------------------------------------

assert.match(html, /id="vehicle-cost-panel"/, 'phải có khung chứa bảng giá thành từng xe');
assert.match(html, /\.vc-table tr\.is-custom/, 'dòng đã đặt riêng phải có kiểu riêng');
// Kế thừa và đặt riêng phải khác nhau ở cả icon lẫn màu, không chỉ màu.
{
  const fn = bodyOf('window.openVehicleCostList = function', String.fromCharCode(10) + '};');
  assert.match(fn, /fa-pen/, 'xe đặt riêng phải có icon riêng');
  assert.match(fn, /fa-link/, 'xe kế thừa phải có icon riêng');
  assert.match(fn, /Kế thừa loại xe/);
}

// Mã xe do người dùng đặt nên phải thoát theo ngữ cảnh JavaScript.
{
  const fn = bodyOf('window.openVehicleCostList = function', String.fromCharCode(10) + '};');
  assert.match(fn, /escapeJsAttr\(v\.id\)/, 'mã xe vào onclick phải thoát theo ngữ cảnh JS');
  assert.match(fn, /escapeHtml\(v\.id\)/, 'mã xe vào innerHTML phải thoát');
}

console.log('two-tier-cost-ui: tất cả kiểm tra đã qua');
