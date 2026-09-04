/**
 * Test cho bảng xếp ca tài xế (ma trận người × ngày).
 *
 * Kiểm cả hành vi lẫn các quy tắc thiết kế mà phần này cam kết: không dùng hộp
 * thoại, màu trạng thái luôn kèm chữ và icon, và ô trống phải bấm được để xếp
 * ca ngay cho đúng người.
 */
const assert = require('assert');
const fs = require('fs');
const path = require('path');

const roster = require(path.join(__dirname, '..', 'js', 'driver-roster.js'));
const DR = roster;

// --------------------------------------------------------------------------
// Dữ liệu mẫu
// --------------------------------------------------------------------------

const DATA = {
  days: [
    { key: '2026-08-31', label: 'T2, 31/08' },
    { key: '2026-09-01', label: 'T3, 01/09' },
    { key: '2026-09-02', label: 'T4, 02/09' },
  ],
  people: [
    {
      id: 'DRV-001',
      name: 'Nguyễn Văn Minh',
      role: 'Lái xe chính',
      license: 'Hạng FC',
      days: [
        {
          key: '2026-08-31',
          shifts: [{ id: 'S1', type: 'morning', kind: 'work', vehicle_id: '51C-123.45', start_label: '06:00', end_label: '14:00' }],
          trips: [],
        },
        {
          key: '2026-09-01',
          shifts: [{ id: 'S2', type: 'afternoon', kind: 'leave', vehicle_id: '', start_label: '14:00', end_label: '22:00' }],
          trips: [],
        },
        {
          key: '2026-09-02',
          shifts: [],
          trips: [{ trip_id: 'TRIP-77', role: 'driver', vehicle_id: '59D-678.90', shift_type: 'night' }],
        },
      ],
    },
    {
      id: 'DRV-002',
      name: 'Lê Hoàng Nam',
      role: 'Phụ xe',
      license: 'Hạng C',
      days: DATA_EMPTY_DAYS(),
    },
  ],
};

function DATA_EMPTY_DAYS() {
  return [
    { key: '2026-08-31', shifts: [], trips: [] },
    { key: '2026-09-01', shifts: [], trips: [] },
    { key: '2026-09-02', shifts: [], trips: [] },
  ];
}

// --------------------------------------------------------------------------
// 1. Thứ tự ưu tiên trạng thái của một ô
// --------------------------------------------------------------------------

// Khóa lịch từ Điều phối là sự thật không đổi được, nên nó thắng mọi thứ khác.
assert.strictEqual(roster.cellState({ trip: { trip_id: 'T1' }, shift: null }), 'locked');
assert.strictEqual(roster.cellState({ trip: { trip_id: 'T1' }, shift: { kind: 'work' } }), 'locked');
assert.strictEqual(roster.cellState({ shift: { kind: 'work' } }), 'assigned');
assert.strictEqual(roster.cellState({ shift: { kind: 'leave' } }), 'absence');
assert.strictEqual(roster.cellState({ shift: { kind: 'sick' } }), 'absence');
// Không có kind thì coi là đang làm việc, không phải nghỉ.
assert.strictEqual(roster.cellState({ shift: {} }), 'assigned');
assert.strictEqual(roster.cellState({}), 'free');
assert.strictEqual(roster.cellState(null), 'free');

// --------------------------------------------------------------------------
// 2. Ba ca mỗi ngày, đúng ô
// --------------------------------------------------------------------------

assert.deepStrictEqual(roster.SHIFTS.map(s => s.key), ['morning', 'afternoon', 'night']);
assert.deepStrictEqual(roster.SHIFTS.map(s => s.letter), ['S', 'C', 'Đ']);

{
  const cells = roster.personCells(DATA.people[0], '2026-08-31');
  assert.strictEqual(roster.cellState(cells.morning), 'assigned');
  assert.strictEqual(roster.cellState(cells.afternoon), 'free');
  assert.strictEqual(roster.cellState(cells.night), 'free');
}
{
  // Chuyến khóa lịch chỉ chiếm ĐÚNG ca của nó, không chiếm cả ngày.
  const cells = roster.personCells(DATA.people[0], '2026-09-02');
  assert.strictEqual(roster.cellState(cells.night), 'locked');
  assert.strictEqual(roster.cellState(cells.morning), 'free');
  assert.strictEqual(roster.cellState(cells.afternoon), 'free');
}
// Ngày không có trong dữ liệu người đó thì trả về ba ô trống, không vỡ.
{
  const cells = roster.personCells(DATA.people[0], '2099-01-01');
  assert.strictEqual(roster.cellState(cells.morning), 'free');
}
assert.doesNotThrow(() => roster.personCells({}, '2026-08-31'));

// --------------------------------------------------------------------------
// 3. Tổng hợp một ngày
// --------------------------------------------------------------------------

{
  const load = roster.dayLoad(DATA.people, '2026-08-31');
  assert.strictEqual(load.assigned, 1);
  assert.strictEqual(load.absence, 0);
  assert.strictEqual(load.locked, 0);
  // 2 người × 3 ca = 6 chỗ có thể xếp.
  assert.strictEqual(load.capacity, 6);
}
{
  const load = roster.dayLoad(DATA.people, '2026-09-01');
  assert.strictEqual(load.absence, 1, 'nghỉ phép phải đếm vào absence, không phải assigned');
  assert.strictEqual(load.assigned, 0);
}
{
  const load = roster.dayLoad(DATA.people, '2026-09-02');
  assert.strictEqual(load.locked, 1);
}
// Không có người thì không chia cho 0.
assert.deepStrictEqual(
  roster.dayLoad([], '2026-08-31'),
  { assigned: 0, absence: 0, locked: 0, capacity: 0 }
);

// --------------------------------------------------------------------------
// 4. Ma trận tuần
// --------------------------------------------------------------------------

{
  const html = roster.weekMatrix(DATA, { selectedDay: '2026-09-01' });

  // 2 người + 1 hàng đầu = 3 hàng.
  assert.strictEqual((html.match(/class="dr-row/g) || []).length, 3);
  // 2 người × 3 ngày × 3 ca = 18 ô ca.
  assert.strictEqual((html.match(/class="dr-cell /g) || []).length, 18);

  // Số cột ngày truyền vào CSS để lưới tự giãn.
  assert.ok(html.includes('--dr-days:3'));
  // Ngày đang chọn được làm nổi bật, không cần mở hộp thoại.
  assert.ok(html.includes('is-selected'));

  // Tên và mã nhân sự đều hiện — mất tên thì cả bảng vô nghĩa.
  assert.ok(html.includes('Nguyễn Văn Minh'));
  assert.ok(html.includes('DRV-001'));
  assert.ok(html.includes('Hạng FC'));
}

// Không có dữ liệu thì nói rõ, không hiện bảng rỗng.
assert.ok(roster.weekMatrix({ days: [], people: [] }, {}).includes('dr-empty'));
assert.ok(roster.weekMatrix({ days: DATA.days, people: [] }, {}).includes('bộ lọc'));
assert.doesNotThrow(() => roster.weekMatrix(undefined, undefined));

// --------------------------------------------------------------------------
// 5. Màu KHÔNG bao giờ là tín hiệu duy nhất
// --------------------------------------------------------------------------

{
  const html = roster.weekMatrix(DATA, {});
  const cells = html.match(/<button type="button" class="dr-cell[\s\S]*?<\/button>/g) || [];
  assert.ok(cells.length >= 18);
  for (const cell of cells) {
    // Mỗi ô mang CHỮ ca (S/C/Đ) — đọc được kể cả khi không phân biệt được màu.
    assert.ok(/dr-cell-letter">[SCĐ]</.test(cell), `ô ca thiếu chữ: ${cell.slice(0, 90)}`);
    // Và có nhãn cho trình đọc màn hình, nói rõ trạng thái bằng lời.
    assert.ok(/aria-label="[^"]+/.test(cell), 'ô ca thiếu aria-label');
  }
  // Ô khóa lịch có thêm icon ổ khóa: khác HÌNH DẠNG, không chỉ khác màu.
  assert.ok(html.includes('fa-lock'));
}

// Mỗi trạng thái có icon riêng, không chỉ khác màu.
{
  const icons = Object.values(roster.STATE).map(entry => entry.icon);
  assert.strictEqual(new Set(icons).size, icons.length, 'mỗi trạng thái phải có icon riêng');
  // Khóa lịch dùng màu xanh của ứng dụng, KHÔNG dùng đỏ: nó là một sự thật từ
  // Điều phối, không phải lỗi cần sửa.
  assert.strictEqual(roster.STATE.locked.color, '#1d4ed8');
  assert.strictEqual(roster.STATE.assigned.color, '#059669');
  assert.strictEqual(roster.STATE.absence.color, '#d97706');
}

// Chú giải có đủ bốn trạng thái kèm chữ, và giải thích ba chữ viết tắt.
{
  const html = roster.legend();
  for (const label of ['Đã xếp ca', 'Nghỉ', 'Khóa lịch', 'Còn trống']) {
    assert.ok(html.includes(label), `chú giải thiếu "${label}"`);
  }
  assert.ok(html.includes('S = sáng'));
}

// --------------------------------------------------------------------------
// 6. Ô trống xếp ca cho ĐÚNG người của hàng đó
// --------------------------------------------------------------------------

// Bản cũ buộc chọn tài xế ở danh sách bên trái trước rồi mới bấm được vào ô.
// Trong ma trận, hàng đã là tài xế nên thao tác đó là dư.
{
  const html = roster.weekMatrix(DATA, {});
  assert.ok(
    html.includes("DriverRosterActions.assign('DRV-002', '2026-08-31', 'morning')"),
    'ô trống phải truyền đúng mã tài xế của hàng đó'
  );
  // Ô đã có ca thì mở chi tiết, không tạo trùng.
  assert.ok(html.includes("DriverRosterActions.openShift('S1')"));
  // Ô khóa lịch mở chuyến, không cho sửa ca.
  assert.ok(html.includes("DriverRosterActions.openTrip('TRIP-77', 'DRV-001')"));
}

// --------------------------------------------------------------------------
// 7. Chi tiết một ngày — trong trang, không phải hộp thoại
// --------------------------------------------------------------------------

{
  const html = roster.dayDetail(DATA, '2026-08-31');
  assert.ok(html.includes('dr-detail'));
  // KHÔNG được có lớp overlay hay vai trò dialog.
  assert.ok(!/role="dialog"/.test(html), 'chi tiết ngày không được là hộp thoại');
  assert.ok(!/overlay/.test(html), 'chi tiết ngày không được có lớp phủ');
  // Bảng dùng th cho hàng để trình đọc màn hình biết đâu là tiêu đề hàng.
  assert.ok(html.includes('<th scope="row"'));
  assert.ok(html.includes('Ca sáng') && html.includes('06:00 – 14:00'));
  // Ô trống trong bảng chi tiết cũng xếp ca được ngay.
  assert.ok(html.includes('dr-detail-free'));
}
assert.ok(roster.dayDetail(DATA, 'khong-ton-tai').includes('dr-empty'));

// --------------------------------------------------------------------------
// 8. Escape dữ liệu
// --------------------------------------------------------------------------

const ATTACK = '<img src=x onerror=alert(1)>';
{
  const evil = {
    days: [{ key: '2026-08-31', label: ATTACK }],
    people: [{
      id: ATTACK, name: ATTACK, role: ATTACK, license: ATTACK,
      days: [{ key: '2026-08-31', shifts: [{ id: ATTACK, type: 'morning', kind: 'work', vehicle_id: ATTACK, start_label: '06:00', end_label: '14:00' }], trips: [] }],
    }],
  };
  for (const [name, html] of [
    ['weekMatrix', roster.weekMatrix(evil, {})],
    ['dayDetail', roster.dayDetail(evil, '2026-08-31')],
  ]) {
    assert.ok(!html.includes('<img src=x'), `${name} chưa escape dữ liệu`);
    assert.ok(html.includes('&lt;img src=x'), `${name} phải escape thành thực thể HTML`);
  }
}

// Mã tài xế đi vào chuỗi JavaScript trong onclick, nên phải escape hai lớp.
{
  const evil = {
    days: [{ key: '2026-08-31', label: 'T2' }],
    people: [{ id: "');alert(1);('", name: 'X', days: [{ key: '2026-08-31', shifts: [], trips: [] }] }],
  };
  const html = roster.weekMatrix(evil, {});
  assert.ok(!/assign\('\);alert/.test(html), 'mã tài xế chưa được escape cho ngữ cảnh JavaScript');
}

// --------------------------------------------------------------------------
// 9. Nối vào ứng dụng: KHÔNG còn hộp thoại ngày
// --------------------------------------------------------------------------

const app = fs.readFileSync(path.join(__dirname, '..', 'js', 'app.js'), 'utf8');
const html = fs.readFileSync(path.join(__dirname, '..', 'index.html'), 'utf8');

assert.ok(html.includes('js/driver-roster.js'), 'index.html phải nạp driver-roster.js');
assert.ok(html.includes('css/driver-roster.css'), 'index.html phải nạp driver-roster.css');
assert.ok(
  html.indexOf('js/driver-roster.js') < html.indexOf('js/app.js'),
  'driver-roster.js phải nạp trước app.js'
);

// Hộp thoại ngày đã bị dỡ: đó là điều làm bản cũ mất ngữ cảnh tuần.
assert.ok(
  !/driver-shift-day-dialog['"]\s*;\s*$/m.test(app) || !/overlay\.className = 'driver-day-overlay'/.test(app),
  'không được dựng lại lớp phủ hộp thoại ngày'
);
assert.ok(
  !/let driverShiftDayDialogOpen/.test(app),
  'biến trạng thái hộp thoại phải được dỡ'
);
assert.ok(/let driverRosterView/.test(app), 'phải có biến góc nhìn week/day');

// renderDriverShiftCalendarTable chỉ điều phối, không tự dựng HTML dài.
{
  const start = app.indexOf('function renderDriverShiftCalendarTable()');
  const fn = app.slice(start, app.indexOf('\n}', start) + 2);
  assert.ok(fn.includes('window.DriverRoster'), 'phải dùng module trình bày');
  assert.ok(!fn.includes('<table class="driver-day-table'), 'không được quay lại tự dựng bảng');
}

// --- 10. Ma trận XE × NGÀY -------------------------------------------------

const VDAYS = [
  { key: '2026-03-02', label: 'T2 02/03' },
  { key: '2026-03-03', label: 'T3 03/03' },
];

function vehicleFixture() {
  return {
    days: VDAYS,
    vehicles: [
      {
        vehicle_id: 'V-01',
        label: '51C-123.45',
        type: 'Xe tải 5T',
        days: [
          { key: '2026-03-02', status: 'busy', trip_ids: ['TR-9'], maintenances: [], shifts: [], driver_ids: ['D-1'] },
          { key: '2026-03-03', status: 'available', trip_ids: [], maintenances: [], shifts: [], driver_ids: [] },
        ],
      },
      {
        vehicle_id: 'V-02',
        label: '51C-678.90',
        type: '',
        days: [
          { key: '2026-03-02', status: 'maintenance', trip_ids: [], maintenances: [{ label: 'Thay lốp' }], shifts: [], driver_ids: [] },
          { key: '2026-03-03', status: 'conflict', trip_ids: ['TR-1', 'TR-2'], maintenances: [], shifts: [], driver_ids: [] },
        ],
      },
    ],
  };
}

// Dòng chữ trong ô ưu tiên việc bảo dưỡng, rồi chuyến, rồi số ca dự kiến.
assert.strictEqual(DR.vehicleDayHint({ maintenances: [{ label: 'Thay lốp' }], trip_ids: ['TR-9'] }), 'Thay lốp');
assert.strictEqual(DR.vehicleDayHint({ maintenances: [], trip_ids: ['TR-9', 'TR-8'] }), 'TR-9, TR-8');
assert.strictEqual(DR.vehicleDayHint({ maintenances: [], trip_ids: [], shifts: [1, 2] }), '2 ca dự kiến');
assert.strictEqual(DR.vehicleDayHint({ maintenances: [], trip_ids: [], shifts: [] }), '—');
assert.strictEqual(DR.vehicleDayHint(undefined), '—', 'thiếu dữ liệu ngày vẫn phải ra ô trống, không vỡ');

// Đếm theo ngày.
{
  const data = vehicleFixture();
  assert.deepStrictEqual(DR.vehicleDayLoad(data.vehicles, '2026-03-02'), { available: 0, busy: 1, maintenance: 1, conflict: 0 });
  assert.deepStrictEqual(DR.vehicleDayLoad(data.vehicles, '2026-03-03'), { available: 1, busy: 0, maintenance: 0, conflict: 1 });
  // Ngày không có dữ liệu: mọi xe tính là rảnh chứ không rơi ra ngoài bảng.
  assert.deepStrictEqual(DR.vehicleDayLoad(data.vehicles, '2026-03-09'), { available: 2, busy: 0, maintenance: 0, conflict: 0 });
  // Trạng thái lạ từ backend cũng phải được đếm, không làm tổng bị hụt.
  const odd = [{ vehicle_id: 'V-9', days: [{ key: '2026-03-02', status: 'ngu_nhien' }] }];
  assert.strictEqual(DR.vehicleDayLoad(odd, '2026-03-02').available, 1);
}

// Cấu trúc: 1 hàng đầu + mỗi xe một hàng; mỗi hàng đủ 2 ô ngày.
{
  const out = DR.vehicleMatrix(vehicleFixture(), { selectedDay: '2026-03-03' });
  assert.ok(out.includes('dr-matrix--vehicles'), 'phải là ma trận xe');
  assert.strictEqual((out.match(/class="dr-row/g) || []).length, 3, '1 hàng đầu + 2 xe');
  assert.strictEqual((out.match(/class="dr-vcell /g) || []).length, 4, '2 xe × 2 ngày');
  // Cột tổng đếm số NGÀY RẢNH: V-01 rảnh 1 ngày, V-02 rảnh 0 ngày.
  assert.deepStrictEqual(
    [...out.matchAll(/<div class="dr-total"><b>(\d+)<\/b>/g)].map(m => m[1]),
    ['1', '0']
  );
  // Ngày đang chọn được làm nổi bật ở cả đầu cột và các ô.
  assert.ok(out.includes('dr-col-head is-selected'), 'đầu cột ngày đang chọn phải nổi bật');
  // KHÔNG được là hộp thoại: đó chính là thứ vừa dỡ bỏ.
  assert.ok(!out.includes('role="dialog"'), 'ma trận xe không được là hộp thoại');
  assert.ok(!out.includes('dr-overlay') && !out.includes('driver-day-overlay'), 'không được có lớp phủ');
  // Xe chưa cấu hình loại phải nói rõ, không để trống gây tưởng lỗi tải dữ liệu.
  assert.ok(out.includes('Chưa cấu hình loại xe'));
}

// Màu không bao giờ đứng một mình: mỗi ô có icon và nhãn cho trình đọc màn hình.
{
  const out = DR.vehicleMatrix(vehicleFixture(), {});
  const cells = [...out.matchAll(/<button type="button" class="dr-vcell[\s\S]*?<\/button>/g)].map(m => m[0]);
  assert.strictEqual(cells.length, 4);
  cells.forEach(cell => {
    assert.match(cell, /<i class="fa-solid fa-[a-z-]+"/, 'mỗi ô phải có icon');
    assert.match(cell, /aria-label="/, 'mỗi ô phải có nhãn đọc được');
    assert.match(cell, /class="dr-vcell-hint">/, 'mỗi ô phải có dòng chữ, không chỉ có màu');
  });
  const legend = DR.vehicleLegend();
  ['Rảnh', 'Đang có lịch', 'Bảo dưỡng / sửa chữa', 'Xung đột lịch'].forEach(label => {
    assert.ok(legend.includes(label), `chú giải thiếu "${label}"`);
  });
  assert.strictEqual((legend.match(/fa-solid/g) || []).length, 4, 'mỗi trạng thái trong chú giải phải có icon');
}

// Thoát ký tự — kể cả trong ngữ cảnh chuỗi JavaScript của onclick.
{
  const data = {
    days: [{ key: "2026-03-02", label: '<b>T2</b>' }],
    vehicles: [{
      vehicle_id: "V'-\"01", label: '<script>x</script>', type: '5T & 10T',
      days: [{ key: '2026-03-02', status: 'busy', trip_ids: ['<i>TR</i>'], maintenances: [], shifts: [], driver_ids: [] }],
    }],
  };
  const out = DR.vehicleMatrix(data, {});
  assert.ok(!out.includes('<script>'), 'không được nhả thẻ script');
  assert.ok(!out.includes('<b>T2</b>'), 'nhãn ngày phải được thoát');
  assert.ok(out.includes('&amp;'), 'ký tự & phải được thoát');
  // Dấu nháy trong biển số không được đóng sớm chuỗi JavaScript của onclick.
  const onclick = /onclick="DriverRosterActions\.openVehicle\('([^']*)'/.exec(out);
  assert.ok(onclick, 'ô xe phải mở được hồ sơ xe');
  assert.ok(!onclick[1].includes("'"), 'dấu nháy đơn phải được thoát trong ngữ cảnh JS');
}

// Bảng rỗng phải nói cách sửa, không để một khung trắng.
{
  assert.match(DR.vehicleMatrix({ days: VDAYS, vehicles: [] }, {}), /Xóa từ khóa/);
  assert.match(DR.vehicleMatrix({ days: [], vehicles: [] }, {}), /tuần/);
}

// --- 11. Tích hợp lịch xe trong app.js ------------------------------------

assert.ok(!/driverVehicleDayDialogOpen/.test(app), 'biến hộp thoại lịch xe phải được dỡ');
assert.ok(!/DRIVER_VEHICLE_PAGE_SIZE/.test(app), 'ma trận hiện đủ xe nên không còn phân trang');
assert.ok(/DriverRoster\.vehicleMatrix/.test(app), 'lịch xe phải dựng qua module trình bày');
{
  const start = app.indexOf('function renderDriverVehicleWeek()');
  assert.ok(start > 0, 'phải còn hàm dựng lịch xe');
  const fn = app.slice(start, app.indexOf('\n}', start) + 2);
  assert.ok(!fn.includes('driver-vehicle-week-day'), 'không được quay lại dải 7 ngày chỉ có số tổng');
  assert.ok(!fn.includes('role="dialog"'), 'lịch xe không được dựng hộp thoại');
}

console.log('driver-roster: tất cả kiểm tra đã qua');
