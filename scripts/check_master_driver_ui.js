const fs = require('fs');
const path = require('path');

const root = path.resolve(__dirname, '..');
const html = fs.readFileSync(path.join(root, 'frontend', 'index.html'), 'utf8');
const appJs = fs.readFileSync(path.join(root, 'frontend', 'js', 'app.js'), 'utf8');

function assert(condition, message) {
  if (!condition) {
    console.error(`FAIL: ${message}`);
    process.exitCode = 1;
  }
}

function sectionById(source, id) {
  const start = source.indexOf(`<div id="${id}"`);
  if (start === -1) return '';
  const next = source.indexOf('\n          <!-- Vietnamese source cleaned -->', start + 1);
  return source.slice(start, next === -1 ? source.length : next);
}

const drivers = sectionById(html, 'md-tab-vehicles');
const driverJsStart = appJs.indexOf('function renderFioriDrivers');
const driverJsEnd = appJs.indexOf('window.resetAllOrdersData', driverJsStart);
const driverJs = driverJsStart === -1 ? '' : appJs.slice(driverJsStart, driverJsEnd === -1 ? appJs.length : driverJsEnd);

assert(drivers, 'driver master-data tab should exist');
assert(driverJs, 'driver master-data JavaScript should exist');
[
  'Quản lý tài xế, phụ xe & ca làm việc',
  'Phân công ca trực, gán xe mặc định và quản lý trạng thái làm việc của đội ngũ tài xế.',
  'Thêm tài xế / phụ xe',
  'Mã / Tên tài xế',
  'Chức danh',
  'Hạng bằng lái',
  'Số điện thoại',
  'Xe gán',
  'Ca làm việc',
  'Trạng thái',
  'Thao tác',
  'Chưa có tài xế/phụ xe nào trong CSDL.',
  'Quản lý nhân sự tài xế & phụ xe',
  'Cấu hình thông tin hồ sơ, bằng lái, xe phân công và ca làm việc chi tiết',
  'Tải ảnh tài xế lên',
  'Xóa ảnh',
  'Lưu thông tin nhân sự'
].forEach(text => assert(drivers.includes(text), `driver tab should include clean Vietnamese text: ${text}`));

[
  'Qu?n',
  'TÃ',
  'TÃ i Xáº¿?',
  'Ph? X?',
  'Ch?c',
  'Tr?ng',
  'Thao T?c',
  'Ca Lm',
  'S? i?n',
  'LÆ°u Thng'
].forEach(text => assert(!drivers.includes(text), `driver tab should not include mojibake text: ${text}`));

[
  'Vui lòng chọn đúng file ảnh tài xế.',
  'Chỉnh sửa nhân sự tài xế / phụ xe',
  'Đã xóa nhân sự khỏi CSDL!',
  'Vui lòng nhập mã và họ tên nhân sự!',
  'Đã lưu nhân sự vào CSDL'
].forEach(text => assert(driverJs.includes(text), `driver JS should include clean Vietnamese text: ${text}`));

[
  'Vui lÃ²ng chá»n',
  'Chá»‰nh Sá»­a NhÃ¢n Sá»±',
  'Sáº¿p cÃ³ cháº¯c',
  'ÄÃ£ xÃ³a nhÃ¢n sá»±',
  'Vui lÃ²ng nháº­p MÃ£',
  'ÄÃ£ lÆ°u nhÃ¢n'
].forEach(text => assert(!driverJs.includes(text), `driver JS should not render mojibake text: ${text}`));

assert(drivers.includes('table-layout:fixed'), 'driver table should use fixed layout to avoid form overflow');
assert(drivers.includes('width:96px'), 'driver action column should fit both compact buttons');
assert(!drivers.includes('Xe phân công</th>'), 'driver table should use the shorter Xe gán header to avoid cramped text');
assert(!driverJs.includes('ph�n c�ng'), 'driver JS should not render replacement-character text');
assert(!drivers.includes('�'), 'driver tab should not contain replacement characters');
assert(!driverJs.includes('�'), 'driver JS should not contain replacement characters in the driver section');

if (!process.exitCode) {
  console.log('MASTER_DRIVER_UI_OK');
}
