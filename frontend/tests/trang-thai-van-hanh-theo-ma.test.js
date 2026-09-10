/**
 * Trạng thái vận hành của xe / tài xế hiện theo MÃ, chữ lấy từ lang.json.
 *
 * Chủ dự án: *"cái nhãn thì hardcode quá — thay bằng loại gì có thể update
 * được thông tin xe"*. Máy chủ nay trả `operational_status` là mã chuẩn
 * (available / on_trip / maintenance / out_of_service; tài xế thêm off_duty /
 * inactive). Giao diện KHÔNG được so chuỗi tiếng Việt nữa — bản tiếng Lào đọc
 * chuỗi đó ra tiếng Việt — mà đọc mã rồi tra lang.json.
 */
const assert = require('assert');
const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..');
const app = fs.readFileSync(path.join(ROOT, 'js', 'app.js'), 'utf8');
const lang = JSON.parse(fs.readFileSync(path.join(ROOT, 'js', 'lang.json'), 'utf8'));

function than(neo, ket) {
  const i = app.indexOf(neo);
  assert.ok(i >= 0, 'không thấy ' + neo);
  const j = ket ? app.indexOf(ket, i) : -1;
  return app.slice(i, j > 0 ? j : i + 6000);
}

// --- 1. Đủ khoá dịch cho mọi mã, cả ba tiếng -------------------------------
for (const k of ['veh_status_available', 'veh_status_on_trip', 'veh_status_maintenance',
  'veh_status_out_of_service', 'drv_status_available', 'drv_status_on_trip',
  'drv_status_off_duty', 'drv_status_inactive']) {
  assert.ok(lang[k], 'thiếu khoá ' + k);
  for (const t of ['vi', 'en', 'la']) assert.ok(String(lang[k][t] || '').trim(), `${k} thiếu ${t}`);
}

// --- 2. Hàm đọc nhãn theo mã, qua lang.json ---------------------------------
{
  const h = than('function nhanTrangThaiVanHanh(loai, ma, ref)', 'window.datTrangThaiXe');
  assert.ok(/appTranslations\[khoa\]/.test(h), 'phải tra lang.json theo khoá của mã');
  assert.ok(/veh_status_/.test(h) && /drv_status_/.test(h), 'khoá theo loại xe / tài xế');
}

// --- 3. Dòng xe và dòng tài xế đọc MÃ, không so nhãn ------------------------
{
  const xe = than('function renderFioriVehicles(data) {', 'window.editFioriVehicle');
  assert.ok(/String\(v\.operational_status \|\| 'available'\)/.test(xe), 'dòng xe phải đọc operational_status');
  assert.ok(!/rawStatus === 'Sẵn sàng'/.test(xe), 'không còn so chuỗi "Sẵn sàng"');
  assert.ok(!/rawStatus\.includes\('Bận'\)/.test(xe), 'không còn tìm chữ "Bận" trong nhãn');
  assert.ok(/datTrangThaiXe\('\$\{escapeHtml\(v\.id\)\}','out_of_service'\)/.test(xe),
    'phải có nút đưa xe ra khỏi đội');
  assert.ok(/datTrangThaiXe\('\$\{escapeHtml\(v\.id\)\}','available'\)/.test(xe),
    'phải có nút đưa xe lại hoạt động');

  const tx = than('function renderFioriDrivers(data) {', 'let driverShiftWeekStart');
  assert.ok(/String\(d\.operational_status \|\| 'available'\)/.test(tx), 'dòng tài xế phải đọc operational_status');
  assert.ok(!/cleanDriverStatus\(rawStatus\)/.test(tx), 'không còn dọn chuỗi nhãn để đoán trạng thái');
  assert.ok(/datTrangThaiTaiXe\(/.test(tx), 'phải có nút đặt tay trạng thái nhân sự');
}

// --- 4. Đặt tay đi đúng đường, lý do bắt buộc khi đưa ra khỏi đội ------------
{
  const h = than('window.datTrangThaiXe = async function', 'window.datTrangThaiTaiXe');
  assert.ok(/\/api\/vehicles\/\$\{encodeURIComponent\(ma\)\}\/operational-status/.test(h));
  assert.ok(/method:\s*'PUT'/.test(h));
  assert.ok(/Phải ghi lý do đưa xe ra khỏi đội/.test(h), 'thiếu lý do thì chặn tại chỗ');
  assert.ok(/loadAllData/.test(h), 'đặt xong phải đọc lại từ máy chủ');
}

// --- 5. Bộ đếm ở màn Điều phối cũng theo mã ---------------------------------
{
  const kpi = than('function renderDispatchKpis(', 'const xeRanh');
  assert.ok(/=== 'maintenance'/.test(kpi) && /=== 'out_of_service'/.test(kpi) && /=== 'on_trip'/.test(kpi),
    'thẻ Xe rảnh phải phân loại theo mã');
  assert.ok(!/bảo dưỡng\|bao duong/.test(kpi), 'không còn regex trên nhãn tiếng Việt');
}

console.log('trang-thai-van-hanh-theo-ma: OK');
