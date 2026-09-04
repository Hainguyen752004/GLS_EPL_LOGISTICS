/**
 * Hộp thoại tạo ca lặp theo tuần.
 *
 * Bản cũ ("Thiết lập lịch làm việc mặc định") hỏi 10 câu rồi im lặng ghi hàng
 * chục ca thật vào cơ sở dữ liệu. Với thiết lập mặc định của nó — Thứ Hai đến
 * Thứ Bảy, khoảng áp dụng 3 tháng — đó là khoảng 78 ca cho MỖI người, mà con số
 * này chỉ hiện ra sau khi đã ghi xong. Những kiểm tra dưới đây khóa lại đúng
 * điều đó: phép đếm phải nói trước, và nói đúng.
 */
const assert = require('assert');
const fs = require('fs');
const path = require('path');

const frontendRoot = path.join(__dirname, '..');
const SR = require(path.join(frontendRoot, 'js', 'shift-recurrence.js'));
const app = fs.readFileSync(path.join(frontendRoot, 'js', 'app.js'), 'utf8');
const html = fs.readFileSync(path.join(frontendRoot, 'index.html'), 'utf8');

// --- 1. Giờ và ca qua đêm ------------------------------------------------

assert.strictEqual(SR.toMinutes('06:00'), 360);
assert.strictEqual(SR.toMinutes('00:00'), 0);
assert.strictEqual(SR.toMinutes('23:59'), 1439);
// Giờ sai phải trả null chứ không âm thầm thành 0 — một ca "0 giờ" ghi vào cơ
// sở dữ liệu thì không ai nhìn ra là lỗi.
['24:00', '12:60', '6:0', 'abc', '', null, undefined].forEach(value => {
  assert.strictEqual(SR.toMinutes(value), null, `giờ không hợp lệ: ${value}`);
});

// Qua đêm được SUY RA, không hỏi người dùng như ô "Kết thúc sau" của bản cũ.
assert.strictEqual(SR.derivedEndDayOffset('22:00', '06:00'), 1, 'ca đêm phải tự nhận là qua đêm');
assert.strictEqual(SR.derivedEndDayOffset('06:00', '14:00'), 0);
assert.strictEqual(SR.derivedEndDayOffset('08:00', '08:00'), 1, 'cùng giờ nghĩa là tròn 24 tiếng, không phải 0');

assert.strictEqual(SR.shiftMinutes('06:00', '14:00'), 480);
assert.strictEqual(SR.shiftMinutes('22:00', '06:00'), 480, 'ca đêm cũng phải ra 8 tiếng');
assert.strictEqual(SR.shiftMinutes('08:00', '08:00'), 1440);
assert.strictEqual(SR.shiftMinutes('bậy', '14:00'), 0);

// --- 2. Ca sẵn quyết định giờ --------------------------------------------

// Bản cũ để "Giờ bắt đầu/kết thúc" và "Loại ca" thành hai ô rời, nên đặt được
// 06:00–14:00 mà vẫn gắn nhãn "Ca đêm".
const byKey = Object.fromEntries(SR.SHIFT_PRESETS.map(item => [item.key, item]));
assert.deepStrictEqual([byKey.morning.start, byKey.morning.end], ['06:00', '14:00']);
assert.deepStrictEqual([byKey.afternoon.start, byKey.afternoon.end], ['14:00', '22:00']);
assert.deepStrictEqual([byKey.night.start, byKey.night.end], ['22:00', '06:00']);
assert.strictEqual(byKey.custom.start, '', 'chỉ "Tùy chỉnh" mới cho tự đặt giờ');
// Ba ca liền nhau phủ kín 24 tiếng, không hở và không chồng.
assert.strictEqual(byKey.morning.end, byKey.afternoon.start);
assert.strictEqual(byKey.afternoon.end, byKey.night.start);
assert.strictEqual(byKey.night.end, byKey.morning.start);
assert.strictEqual(SR.preset('khong-co'), null);

// --- 3. Liệt kê ngày thật ------------------------------------------------

{
  // 01/09/2026 là Thứ Ba. T2–T6 trong tháng 9 có 22 ngày làm việc.
  const dates = SR.expandRecurrence({ weekdays: [0, 1, 2, 3, 4], effectiveStart: '2026-09-01', effectiveEnd: '2026-09-30' });
  assert.strictEqual(dates.length, 22);
  assert.strictEqual(dates[0], '2026-09-01');
  assert.strictEqual(dates[dates.length - 1], '2026-09-30');
  // Không được lọt Thứ Bảy hay Chủ Nhật nào.
  dates.forEach(key => {
    const day = new Date(`${key}T00:00:00`).getDay();
    assert.ok(day >= 1 && day <= 5, `${key} không phải ngày trong tuần`);
  });
}

// Chọn đúng Chủ Nhật: quy ước Thứ Hai = 0 nên Chủ Nhật là 6, khớp với backend.
{
  const sundays = SR.expandRecurrence({ weekdays: [6], effectiveStart: '2026-09-01', effectiveEnd: '2026-09-30' });
  assert.deepStrictEqual(sundays, ['2026-09-06', '2026-09-13', '2026-09-20', '2026-09-27']);
}

// Ngày đầu và ngày cuối đều được tính, không bị hụt một đầu.
assert.deepStrictEqual(
  SR.expandRecurrence({ weekdays: [0, 1, 2, 3, 4, 5, 6], effectiveStart: '2026-09-01', effectiveEnd: '2026-09-01' }),
  ['2026-09-01']
);

// Backend từ chối khoảng quá 366 ngày, nên phía giao diện cũng phải chặn.
assert.deepStrictEqual(SR.expandRecurrence({ weekdays: [0], effectiveStart: '2026-01-01', effectiveEnd: '2027-06-01' }), []);
// Dữ liệu thiếu hoặc ngược thì trả rỗng, không ném lỗi làm vỡ hộp thoại.
assert.deepStrictEqual(SR.expandRecurrence({ weekdays: [], effectiveStart: '2026-09-01', effectiveEnd: '2026-09-30' }), []);
assert.deepStrictEqual(SR.expandRecurrence({ weekdays: [0], effectiveStart: '2026-09-30', effectiveEnd: '2026-09-01' }), []);
assert.deepStrictEqual(SR.expandRecurrence({ weekdays: [0], effectiveStart: 'bậy', effectiveEnd: '2026-09-01' }), []);
assert.deepStrictEqual(SR.expandRecurrence(null), []);
// Thứ ngoài 0–6 bị bỏ, không làm lệch phép đếm.
assert.deepStrictEqual(SR.expandRecurrence({ weekdays: [9, -1], effectiveStart: '2026-09-01', effectiveEnd: '2026-09-30' }), []);

// Ngày phải dựng theo giờ ĐỊA PHƯƠNG: dùng Date.parse cho "YYYY-MM-DD" thì
// chuỗi được hiểu là UTC nên ở múi giờ Việt Nam sẽ lùi mất một ngày.
assert.strictEqual(
  SR.expandRecurrence({ weekdays: [0, 1, 2, 3, 4, 5, 6], effectiveStart: '2026-03-01', effectiveEnd: '2026-03-01' })[0],
  '2026-03-01'
);

// --- 4. Phép đếm phải nói TRƯỚC ------------------------------------------

{
  // Đúng thiết lập mặc định của bản cũ: T2–T7, 31/08/2026 đến 01/12/2026.
  const plan = SR.planRecurrence({
    driverIds: ['NV-01'], weekdays: [0, 1, 2, 3, 4, 5],
    effectiveStart: '2026-08-31', effectiveEnd: '2026-12-01',
    startTime: '06:00', endTime: '14:00',
  });
  assert.ok(plan.valid);
  assert.strictEqual(plan.totalShifts, 80, 'thiết lập mặc định cũ ghi 80 ca cho một người');
  // Cùng thiết lập đó cho ba người là 240 bản ghi trong một lần bấm.
  const team = SR.planRecurrence({
    driverIds: ['NV-01', 'NV-02', 'NV-03'], weekdays: [0, 1, 2, 3, 4, 5],
    effectiveStart: '2026-08-31', effectiveEnd: '2026-12-01',
    startTime: '06:00', endTime: '14:00',
  });
  assert.strictEqual(team.totalShifts, 240);
  assert.strictEqual(team.perDriver.length, 3);
  team.perDriver.forEach(item => assert.strictEqual(item.shiftCount, 80));
}

// Trùng mã nhân sự chỉ tính một lần, không nhân đôi số ca.
assert.strictEqual(
  SR.planRecurrence({
    driverIds: ['NV-01', 'NV-01', ' NV-01 ', ''], weekdays: [0],
    effectiveStart: '2026-09-01', effectiveEnd: '2026-09-30',
    startTime: '06:00', endTime: '14:00',
  }).driverIds.length,
  1
);

// --- 5. Nút lưu tự khóa khi thiếu ----------------------------------------

function firstError(overrides) {
  return SR.planRecurrence(Object.assign({
    driverIds: ['NV-01'], weekdays: [0, 1, 2, 3, 4],
    effectiveStart: '2026-09-01', effectiveEnd: '2026-09-30',
    startTime: '06:00', endTime: '14:00',
  }, overrides)).errors.join(' | ');
}

assert.strictEqual(firstError({}), '', 'thiết lập đủ thì không được báo lỗi');
assert.match(firstError({ driverIds: [] }), /nhân sự/);
assert.match(firstError({ weekdays: [] }), /ngày trong tuần/);
assert.match(firstError({ startTime: '' }), /giờ bắt đầu/i);
assert.match(firstError({ effectiveStart: '2026-12-01', effectiveEnd: '2026-09-01' }), /sau ngày bắt đầu/);
assert.match(firstError({ effectiveStart: '2026-01-01', effectiveEnd: '2027-06-01' }), /366/);
// Chọn Chủ Nhật nhưng khoảng áp dụng chỉ có Thứ Hai đến Thứ Sáu: hợp lệ về hình
// thức nhưng ra 0 ca — phải nói rõ thay vì tạo 0 bản ghi rồi báo "đã tạo 0 ca".
assert.match(firstError({ weekdays: [6], effectiveStart: '2026-09-01', effectiveEnd: '2026-09-04' }), /Không có ngày nào khớp/);
assert.strictEqual(SR.planRecurrence({}).valid, false);
assert.strictEqual(SR.planRecurrence(null).valid, false);

// --- 6. Cảnh báo ca đã có ------------------------------------------------

{
  const existing = [
    { driver_id: 'NV-01', shift_start: '2026-09-01T06:00:00Z', status: 'planned' },
    { driver_id: 'NV-01', shift_start: '2026-09-02T06:00:00Z', status: 'planned' },
    // Ca đã hủy không được tính là xung đột.
    { driver_id: 'NV-01', shift_start: '2026-09-03T06:00:00Z', status: 'cancelled' },
    // Người khác thì không liên quan.
    { driver_id: 'NV-02', shift_start: '2026-09-01T06:00:00Z', status: 'planned' },
    // Ngoài khoảng áp dụng thì cũng không tính.
    { driver_id: 'NV-01', shift_start: '2026-10-01T06:00:00Z', status: 'planned' },
  ];
  const plan = SR.planRecurrence({
    driverIds: ['NV-01'], weekdays: [0, 1, 2, 3, 4],
    effectiveStart: '2026-09-01', effectiveEnd: '2026-09-30',
    startTime: '06:00', endTime: '14:00',
    existingShifts: existing,
  });
  assert.strictEqual(plan.existingShifts, 2);
  assert.strictEqual(plan.perDriver[0].existingCount, 2);
  // Không truyền danh sách ca sẵn thì phải là 0, không phải lỗi.
  assert.strictEqual(SR.existingOverlaps('NV-01', ['2026-09-01'], null), 0);
}

// --- 7. Câu tóm tắt người dùng đọc ---------------------------------------

{
  const plan = SR.planRecurrence({
    driverIds: ['NV-01', 'NV-02'], weekdays: [0, 1, 2, 3, 4],
    effectiveStart: '2026-09-01', effectiveEnd: '2026-09-30',
    startTime: '22:00', endTime: '06:00',
  });
  const summary = SR.summarize(plan);
  assert.match(summary.headline, /44 ca/, 'câu tóm tắt phải mang đúng số ca');
  assert.match(summary.detail, /2 nhân sự × 22 ngày/);
  assert.match(summary.detail, /qua đêm/, 'ca qua đêm phải nói rõ');
  assert.match(summary.detail, /8 giờ mỗi ca/);
  // Ngày viết theo thứ tự người Việt đọc, không phải YYYY-MM-DD.
  assert.match(summary.detail, /01\/09\/2026/);
  assert.strictEqual(SR.viDate('2026-09-01'), '01/09/2026');
  // Chưa đủ thông tin thì không được bịa ra con số nào.
  assert.strictEqual(SR.summarize(SR.planRecurrence({})).detail, '');
}

// --- 8. Tích hợp trong app.js và index.html ------------------------------

assert.match(app, /window\.ShiftRecurrence/, 'hộp thoại phải dùng module tính toán');
assert.match(app, /renderRecurrencePreview/, 'phải có khung xem trước trước khi ghi');
assert.match(app, /Tạo \$\{plan\.totalShifts\} ca/, 'nhãn nút lưu phải mang số ca');
assert.match(app, /button\.disabled = !plan\.valid/, 'thiếu thông tin thì nút lưu phải khóa');
// Chọn NHIỀU người: việc thật là xếp ca cho cả đội.
assert.match(app, /toggleRecurrenceDriver/, 'phải chọn được nhiều nhân sự');
assert.match(app, /selectAllRecurrenceDrivers/, 'phải chọn nhanh được cả danh sách');
// Ô "Kết thúc sau" đã bị dỡ: qua đêm nay được suy ra từ giờ.
assert.doesNotMatch(app, /weekly-schedule-day-offset/, 'ô "Kết thúc sau" phải được dỡ');
// Tiêu đề hiện ra phải nói đúng thao tác. (Tên cũ còn trong ghi chú giải thích
// vì sao đổi, nên chỉ xét đúng thẻ tiêu đề.)
{
  const title = /<h3 id="weekly-schedule-title">([\s\S]*?)<\/h3>/.exec(app);
  assert.ok(title, 'phải còn thẻ tiêu đề');
  assert.ok(!title[1].includes('mặc định'), 'tiêu đề cũ nói sai việc hộp thoại này làm');
  assert.match(title[1], /Tạo ca lặp theo tuần/, 'tiêu đề phải nói đúng thao tác');
}
// Nút mở hộp thoại cũng phải đổi theo, không để hai chỗ gọi hai tên.
assert.doesNotMatch(html, /openWeeklyDriverSchedule\(\)[^>]*>[^<]*<i[^>]*><\/i> Lịch mặc định/, 'nút mở phải bỏ tên "Lịch mặc định"');
assert.match(html, /openWeeklyDriverSchedule\(\)[\s\S]{0,220}Tạo ca lặp</, 'nút mở phải mang tên mới');

// Lỗi thoát ký tự của bản cũ: escape rồi mới so khớp thì tìm tên có dấu "&"
// không bao giờ ra, và dán tên đã escape vào ô chữ thì người dùng thấy "&amp;".
{
  const start = app.indexOf('window.openWeeklyDriverSchedule = function ()');
  const end = app.indexOf('window.openAddDriverModal', start);
  const dialog = app.slice(start, end);
  assert.ok(!/escapeHtml\([^)]*\)[^;]*\.toLowerCase\(\)\.includes/.test(dialog), 'không được escape trước khi so khớp tìm kiếm');
  assert.ok(!/input\.value = `\$\{escapeHtml/.test(dialog), 'không được dán chuỗi đã escape vào ô chữ');
  // Tên nhân sự do người dùng nhập nên vẫn phải escape khi vào innerHTML.
  assert.match(dialog, /escapeHtml\(driver\.name \|\| id\)/);
  assert.match(dialog, /escapeJsAttr\(id\)/, 'mã nhân sự vào onclick phải thoát theo ngữ cảnh JavaScript');
}

// Một người lỗi không được làm mất kết quả của những người đã ghi xong.
assert.match(app, /const failed = \[\]/, 'lưu nhiều người phải báo cáo trung thực từng người');

assert.match(html, /js\/shift-recurrence\.js/, 'index.html phải nạp module');
assert.ok(
  html.indexOf('js/shift-recurrence.js') < html.indexOf('js/app.js'),
  'shift-recurrence.js phải nạp trước app.js'
);
assert.match(html, /\.sr-preview\s*\{/, 'index.html phải có CSS cho khung xem trước');
assert.match(html, /\.sr-person\s*\{/, 'index.html phải có CSS cho danh sách chọn nhiều người');
// Đã chọn phải có dấu tích, không chỉ đổi màu nền.
assert.match(html, /\.sr-person\.is-on \.sr-person-tick\s*\{[^}]*visible/);

console.log('shift-recurrence: tất cả kiểm tra đã qua');
