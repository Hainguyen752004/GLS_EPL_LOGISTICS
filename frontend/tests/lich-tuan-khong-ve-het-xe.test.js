/**
 * Màn lịch tuần không được vẽ một dòng cho MỖI xe.
 *
 * Bản cũ `renderDispatchWeekPlanner` dựng một ma trận xe × ngày. Đo bằng chính
 * khuôn dòng của nó:
 *
 *       3 xe  ->  0,01 MB HTML,    21 nút
 *      50 xe  ->  0,11 MB HTML,   350 nút
 *     200 xe  ->  0,43 MB HTML, 1.400 nút
 *     500 xe  ->  1,06 MB HTML, 3.500 nút   <-- quy mô vận hành thật
 *
 * Ba khối chứa của nó (`dispatch-week-planner-kpis`, `-grid`, `-guidance`)
 * chưa bao giờ được dựng trong index.html, nên nó chưa từng chạy — nhưng nó
 * nằm đó chờ ai đó "sửa cho nó hiện lên".
 *
 * Bản đang chạy là `renderDispatchWeekTimetable` và làm khác hẳn: một băng
 * năng lực theo ngày (7 thẻ, mỗi thẻ là con số rảnh/bận/sửa chữa/xung đột),
 * rồi mới lấy danh sách xe của ngày được chọn qua `buildDispatchDayFleet` —
 * hàm này chặn `page_size` ở 100 dòng, nên số dòng vẽ ra KHÔNG phụ thuộc vào
 * cỡ đội xe.
 *
 * Bài kiểm này khóa đúng nguyên tắc đó, chứ không khóa tên hàm.
 */
const assert = require('assert');
const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..');
const app = fs.readFileSync(path.join(ROOT, 'js', 'app.js'), 'utf8')
  .split(String.fromCharCode(13)).join('');
const html = fs.readFileSync(path.join(ROOT, 'index.html'), 'utf8');
const utils = require(path.join(ROOT, 'js', 'tms-cockpit-utils.js'));

// --- 1. Bản cũ đã gỡ, và đừng dựng lại khối chứa của nó ----------------

assert.ok(!/function renderDispatchWeekPlanner\s*\(/.test(app),
  'renderDispatchWeekPlanner là bản cũ vẽ ma trận xe × ngày — đã gỡ, đừng thêm lại');

['dispatch-week-planner-kpis', 'dispatch-week-planner-grid',
  'dispatch-week-planner-guidance'].forEach(id => {
  assert.ok(!html.includes(`id="${id}"`),
    `${id} là khối chứa của bản cũ — thêm nó vào là dựng lại ma trận 500 dòng`);
});

// --- 2. Đường đang chạy phải CHẶN số dòng, đo bằng hàm thật ------------
//
// Đây là phần đáng giá: chạy đúng hàm mà giao diện gọi, với 500 xe.

{
  const xe = [];
  for (let i = 0; i < 500; i += 1) {
    xe.push({ id: 'VEH-' + String(i).padStart(4, '0'), type: 'Xe tải', status: 'available' });
  }
  const state = { vehicles: xe, transport_trips: [], delivery_orders: [] };
  const week = utils.buildDispatchWeekPlanner(state, new Date('2026-09-07T00:00:00Z'));
  assert.strictEqual(week.vehicle_rows.length, 500,
    'tầng DỮ LIỆU vẫn giữ đủ 500 xe — chặn là việc của tầng VẼ');

  // Kể cả khi người gọi xin tất cả, hàm phải tự chặn.
  const tatCa = utils.buildDispatchDayFleet(week, week.days[0].iso_date,
    { page_size: Number.MAX_SAFE_INTEGER });
  assert.ok(tatCa.rows.length <= 100,
    `buildDispatchDayFleet phải chặn số dòng, trả về ${tatCa.rows.length}`);
  // Và tổng số vẫn phải nói ra, không thì người dùng tưởng đội xe chỉ có 100.
  assert.strictEqual(tatCa.summary.total, 500,
    'phải nói tổng thật, không chỉ số dòng đang hiện');

  const mac_dinh = utils.buildDispatchDayFleet(week, week.days[0].iso_date, {});
  assert.ok(mac_dinh.rows.length <= 100, mac_dinh.rows.length);
}

// --- 3. Băng năng lực phải là CON SỐ, không phải danh sách -------------

{
  const i = app.indexOf('function renderDispatchWeekTimetable');
  assert.ok(i > 0, 'phải có trình vẽ đang chạy');
  const than = app.slice(i, app.indexOf(String.fromCharCode(10) + '}' + String.fromCharCode(10), i));

  // Bảy thẻ ngày, mỗi thẻ dựng từ `weekDays.map` — bảy, không phải 500.
  assert.ok(/weekDays\.map\(/.test(than), 'băng năng lực dựng theo NGÀY');
  assert.ok(!/vehicle_rows\.map\(/.test(than),
    'không được dựng một phần tử cho mỗi xe trong trình vẽ này');
  // Số liệu mỗi ngày lấy từ `summary` (con số) chứ không phải danh sách xe.
  assert.ok(/fleet\.summary\.(available|busy|maintenance|conflict)/.test(than),
    'mỗi ngày phải hiện con số tổng hợp, không liệt kê xe');
  // Và danh sách chi tiết phải đi qua hàm có phân trang.
  assert.ok(/buildDispatchDayFleet\(/.test(than),
    'danh sách xe của ngày phải lấy qua hàm có chặn số dòng');
}

console.log('lich-tuan-khong-ve-het-xe: tất cả kiểm tra đã qua');
