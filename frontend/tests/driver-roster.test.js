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
// Phan trang GIO LA BAT BUOC (o 500 xe), nhung phai la cai trong module chu
// khong phai bien dem cu trong app.js.
assert.ok(!/DRIVER_VEHICLE_PAGE_SIZE/.test(app), 'khong dung lai bien phan trang cu cua hop thoai da do');
assert.ok(/VEHICLE_PAGE_SIZE/.test(app), 'phai dung kich thuoc trang do module quy dinh');
assert.ok(/vehicleMatrix\(/.test(app), 'lịch xe phải dựng qua module trình bày');
{
  const start = app.indexOf('function renderDriverVehicleWeek()');
  assert.ok(start > 0, 'phải còn hàm dựng lịch xe');
  const fn = app.slice(start, app.indexOf('\n}', start) + 2);
  assert.ok(!fn.includes('driver-vehicle-week-day'), 'không được quay lại dải 7 ngày chỉ có số tổng');
  assert.ok(!fn.includes('role="dialog"'), 'lịch xe không được dựng hộp thoại');
}

// --- 12. Đội xe LỚN: 500 xe -----------------------------------------------
//
// Chủ dự án vận hành khoảng 500 xe. Ma trận hiện HẾT mọi xe rất hợp lý với đội
// vài chục xe, nhưng ở quy mô đó nó sinh ra ~1,7 MB HTML và 3.500 nút trong một
// lần innerHTML — và mỗi lần gõ vào ô tìm kiếm lại dựng lại toàn bộ.

function bigFleet(count) {
  const days = [...Array(7)].map((_, i) => ({ key: `2026-09-0${i + 1}`, label: `T${i + 2}` }));
  const vehicles = [...Array(count)].map((_, i) => ({
    vehicle_id: `V-${i}`,
    label: `51C-${1000 + i}`,
    type: i % 2 ? 'Container 20FT' : 'Xe tải 10 tấn',
    days: days.map(day => ({
      key: day.key,
      // Chỉ 1/50 xe có xung đột: dùng tỷ lệ thật, để kiểm đúng việc "chọn 5 xe
      // có vấn đề giữa 495 xe bình thường".
      status: i % 50 === 0 ? 'conflict' : i % 7 === 0 ? 'maintenance' : i % 3 ? 'busy' : 'available',
      trip_ids: [`TR-${i}`],
      maintenances: [],
      shifts: [],
      driver_ids: [],
    })),
  }));
  return { days, vehicles };
}

{
  const data = bigFleet(500);
  const full = DR.vehicleMatrix(data, {});
  const cells = (full.match(/dr-vcell /g) || []).length;
  // Một trang mặc định là 50 xe × 7 ngày = 350 ô, không phải 3.500.
  assert.strictEqual(cells, DR.VEHICLE_PAGE_SIZE * 7, 'ma trận chỉ được dựng một trang xe');
  assert.ok(full.length < 400 * 1024, `ma trận một trang phải dưới 400 KB, đang là ${Math.round(full.length / 1024)} KB`);
  // Phải nói rõ đang xem bao nhiêu trên bao nhiêu, không để người dùng tưởng
  // 50 xe là tất cả.
  assert.match(full, /Đang xem <b>50<\/b> trên <b>500<\/b> xe/);
  assert.match(full, /showMoreVehicles/, 'phải có đường tải thêm');

  // Tải thêm thì ra đúng số.
  const more = DR.vehicleMatrix(data, { limit: 120 });
  assert.strictEqual((more.match(/dr-vcell /g) || []).length, 120 * 7);
  // Hết xe thì không còn nút tải thêm.
  const all = DR.vehicleMatrix(data, { limit: 500 });
  assert.ok(!all.includes('showMoreVehicles'), 'xem hết rồi thì không còn nút tải thêm');
  assert.match(all, /Đang xem đủ <b>500<\/b> xe/);
}

// Băng năng lực phải tính trên CẢ đội xe, không theo trang đang hiện.
{
  const data = bigFleet(500);
  const strip = DR.vehicleCapacityStrip(data, { selectedDay: '2026-09-03' });
  assert.strictEqual((strip.match(/class="dr-cap[ "]/g) || []).length, 7, 'một cột mỗi ngày');
  assert.match(strip, /\/ 500/, 'phải đối chiếu với tổng cả đội xe');
  assert.match(strip, /dr-cap is-selected/, 'ngày đang chọn phải nổi bật');
  // Màu không đứng một mình: mỗi cột đều có con số và nhãn chữ.
  assert.match(strip, /xe rảnh/);
  assert.match(strip, /đang dùng/);
  // Ngày có xung đột phải đeo cờ cảnh báo có cả icon lẫn chữ.
  assert.match(strip, /dr-cap-flag[^>]*><i class="fa-solid fa-triangle-exclamation"[^>]*><\/i> \d+ xung đột/);
}

// Ngoại lệ: xung đột lên trước bảo dưỡng, rồi đến ngày, rồi đến biển số.
{
  const data = {
    days: [{ key: '2026-09-01', label: 'T3' }, { key: '2026-09-02', label: 'T4' }],
    vehicles: [
      { vehicle_id: 'V-B', label: '51C-B', days: [
        { key: '2026-09-01', status: 'maintenance', maintenances: [{ label: 'Thay lốp' }], trip_ids: [], shifts: [] },
        { key: '2026-09-02', status: 'available', maintenances: [], trip_ids: [], shifts: [] }] },
      { vehicle_id: 'V-A', label: '51C-A', days: [
        { key: '2026-09-02', status: 'conflict', maintenances: [], trip_ids: ['TR-1', 'TR-2'], shifts: [] },
        { key: '2026-09-01', status: 'busy', maintenances: [], trip_ids: ['TR-9'], shifts: [] }] },
    ],
  };
  const rows = DR.vehicleExceptions(data);
  assert.strictEqual(rows.length, 2, 'chỉ lấy xung đột và bảo dưỡng, không lấy xe bình thường');
  assert.strictEqual(rows[0].status, 'conflict', 'xung đột lịch là lỗi phải sửa ngay, lên trước');
  assert.strictEqual(rows[1].status, 'maintenance');
  assert.strictEqual(rows[0].dayLabel, 'T4', 'phải đổi mã ngày ra nhãn đọc được');
  assert.strictEqual(rows[0].hint, 'TR-1, TR-2');
}

// Danh sách ngoại lệ: giới hạn số dòng hiện sẵn, và nói rõ còn bao nhiêu.
{
  const data = bigFleet(500);
  const rows = DR.vehicleExceptions(data);
  assert.ok(rows.length > 6, 'dữ liệu mẫu phải có đủ ngoại lệ để kiểm');
  const collapsed = DR.vehicleExceptionList(data, {});
  assert.strictEqual((collapsed.match(/class="dr-exception"/g) || []).length, 6, 'thu gọn thì chỉ hiện 6 dòng');
  assert.match(collapsed, new RegExp(`Xem tất cả ${rows.length} dòng`));
  const expanded = DR.vehicleExceptionList(data, { expanded: true });
  assert.strictEqual((expanded.match(/class="dr-exception"/g) || []).length, rows.length);
  assert.match(expanded, /Thu gọn/);
}

// Đội xe sạch thì phải nói rõ là sạch, không để một khung trống.
{
  const clean = {
    days: [{ key: '2026-09-01', label: 'T3' }],
    vehicles: [{ vehicle_id: 'V-1', label: '51C-1', days: [{ key: '2026-09-01', status: 'available', maintenances: [], trip_ids: [], shifts: [] }] }],
  };
  assert.deepStrictEqual(DR.vehicleExceptions(clean), []);
  const html = DR.vehicleExceptionList(clean, {});
  assert.match(html, /Không có việc cần xử lý/);
  assert.match(html, /fa-circle-check/, 'trạng thái sạch phải có icon riêng, không chỉ khác màu');
  assert.ok(!html.includes('dr-panel--alert'));
}

// Thoát ký tự trong cả hai khối mới.
{
  const nasty = {
    days: [{ key: '2026-09-01', label: '<b>T3</b>' }],
    vehicles: [{ vehicle_id: "V'-1", label: '<script>x</script>', type: 'A & B',
      days: [{ key: '2026-09-01', status: 'conflict', maintenances: [], trip_ids: ['<i>TR</i>'], shifts: [], driver_ids: [] }] }],
  };
  for (const html of [DR.vehicleCapacityStrip(nasty, {}), DR.vehicleExceptionList(nasty, {})]) {
    assert.ok(!html.includes('<script>'), 'không được nhả thẻ script');
    assert.ok(!html.includes('<b>T3</b>'), 'nhãn ngày phải được thoát');
  }
  const list = DR.vehicleExceptionList(nasty, {});
  const onclick = /openVehicle\('([^']*)'/.exec(list);
  assert.ok(onclick && !onclick[1].includes("'"), 'dấu nháy phải được thoát trong ngữ cảnh JavaScript');
}

// --- 13. Tích hợp màn lịch xe trong app.js --------------------------------

assert.ok(/vehicleCapacityStrip/.test(app), 'màn lịch xe phải mở ra bằng tình hình');
assert.ok(/vehicleExceptionList/.test(app), 'phải có danh sách việc cần xử lý');
assert.ok(/driverVehicleVisibleCount/.test(app), 'phải giới hạn số xe dựng một lần');
{
  const start = app.indexOf('function renderDriverVehicleWeek()');
  const fn = app.slice(start, app.indexOf('\nwindow.filterDriverVehicleType', start));
  // Băng năng lực và ngoại lệ phải tính trên CẢ đội xe: lọc mất 5 xe xung đột
  // đi thì cả màn hình báo "không có việc cần xử lý" — đúng kiểu nói dối mà
  // màn hình này sinh ra để tránh.
  assert.match(fn, /ignoreFilters: true/, 'tình hình và ngoại lệ phải tính trên cả đội xe');
  assert.match(fn, /vehicleCapacityStrip\(everything/);
  assert.match(fn, /vehicleExceptionList\(everything/);
  assert.match(fn, /vehicleMatrix\(filtered/, 'riêng ma trận chi tiết mới theo bộ lọc');
}
// Đổi bộ lọc phải quay về trang đầu, không giữ số xe đã tải thêm của bộ lọc cũ.
for (const fnName of ['filterDriverVehicleDay', 'filterDriverVehicleStatus', 'filterDriverVehicleType']) {
  const start = app.indexOf(`window.${fnName} = function`);
  assert.ok(start > 0, `phải có ${fnName}`);
  const fn = app.slice(start, app.indexOf('\n};', start));
  assert.match(fn, /driverVehicleVisibleCount = /, `${fnName} phải đặt lại số xe đang hiện`);
}

// --- 14. Bai / chi nhanh -------------------------------------------------
//
// Chu du an co 500 xe nam o nhieu bai. Truoc day bang `vehicles` khong co truong
// nao cho viec do (chi co inspection_place, la NOI DANG KIEM chu khong phai noi
// xe dau), nen khong the loc theo bai duoc. v025_vehicle_depot them cot.

assert.ok(/driverVehicleTableDepot/.test(app), 'phai co bo loc bai');
assert.ok(/filterDriverVehicleDepot/.test(app), 'phai co ham loc theo bai');
assert.ok(/depotOf\(/.test(app), 'phai tra cuu bai tu ho so xe');
{
  const start = app.indexOf('function renderDriverVehicleWeek()');
  const fn = app.slice(start, app.indexOf(String.fromCharCode(10) + 'window.filterDriverVehicleDepot', start));
  // Bai phai dung TRUOC loai xe tren thanh cong cu: o doi 500 xe day la bo loc
  // chinh, khong phai mot cot phu.
  assert.ok(
    fn.indexOf('driver-vehicle-day-depot') < fn.indexOf('driver-vehicle-day-type'),
    'o chon bai phai dat truoc o chon loai xe'
  );
  // Moi bai phai kem so xe: nguoi dieu phoi can biet truoc khi bam.
  assert.match(fn, /\$\{item\.count\}/, 'moi bai phai hien so xe');
  // "Chua gan bai" phai la mot lua chon that.
  assert.match(fn, /__none__/, 'phai loc duoc nhung xe chua gan bai');
}
{
  // Xoa bo loc phai xoa CA bai, khong bo sot.
  const start = app.indexOf('window.clearDriverVehicleFilters = function');
  const fn = app.slice(start, app.indexOf(String.fromCharCode(10) + '};', start));
  ['driverVehicleTableSearch', 'driverVehicleTableStatus', 'driverVehicleTableType', 'driverVehicleTableDepot'].forEach(name => {
    assert.ok(fn.includes(name), `xoa bo loc phai xoa ${name}`);
  });
}
// Doi bai cung phai quay ve trang dau.
{
  const start = app.indexOf('window.filterDriverVehicleDepot = function');
  const fn = app.slice(start, app.indexOf(String.fromCharCode(10) + '};', start));
  assert.match(fn, /driverVehicleVisibleCount = /);
}

// --- 15. Đội tài xế LỚN: 400 người ----------------------------------------
//
// Cùng lý do như đội xe, nhưng nặng hơn: mỗi người chiếm 21 ô (7 ngày × 3 ca),
// nên 400 người là 8.400 nút và khoảng 3,3 MB HTML trong một lần innerHTML.

function bigCrew(count, coverAllShifts) {
  const days = [...Array(7)].map((_, i) => ({ key: `2026-09-0${i + 1}`, label: `T${i + 2}` }));
  const people = [...Array(count)].map((_, i) => ({
    id: `NV-${i}`,
    name: `Nhân viên ${i}`,
    role: i % 4 ? 'Lái xe' : 'Phụ xe',
    license: 'FC',
    days: days.map(day => ({
      key: day.key,
      // Cứ 5 người thì 1 người không có ca nào — đúng kiểu "năng lực chưa dùng".
      shifts: i % 5 === 0 ? [] : [{
        id: `S-${i}-${day.key}`,
        type: coverAllShifts ? ['morning', 'afternoon', 'night'][i % 3] : 'morning',
        kind: 'work',
        vehicle_id: '',
        start_label: '06:00',
        end_label: '14:00',
      }],
      trips: [],
    })),
  }));
  return { days, people };
}

{
  const data = bigCrew(400, true);
  const matrix = DR.weekMatrix(data, {});
  // Một trang mặc định là 50 người × 7 ngày × 3 ca = 1.050 ô, không phải 8.400.
  assert.strictEqual((matrix.match(/dr-cell /g) || []).length, DR.PERSON_PAGE_SIZE * 7 * 3);
  assert.ok(matrix.length < 600 * 1024, `một trang phải dưới 600 KB, đang là ${Math.round(matrix.length / 1024)} KB`);
  assert.match(matrix, /Đang xem <b>50<\/b> trên <b>400<\/b> nhân sự/);
  assert.match(matrix, /showMorePeople/);

  const all = DR.weekMatrix(data, { limit: 400 });
  assert.ok(!all.includes('showMorePeople'), 'xem hết rồi thì không còn nút tải thêm');
  assert.match(all, /Đang xem đủ <b>400<\/b> nhân sự/);
}

// Băng phủ ca: đếm số người trực từng ca, từng ngày.
{
  const data = bigCrew(400, true);
  const counts = DR.shiftCoverage(data.people, '2026-09-01');
  assert.deepStrictEqual(Object.keys(counts).sort(), ['afternoon', 'morning', 'night']);
  const total = counts.morning + counts.afternoon + counts.night;
  // 400 người, cứ 5 người 1 người không có ca -> 320 người có ca.
  assert.strictEqual(total, 320);

  const strip = DR.crewCoverageStrip(data, { selectedDay: '2026-09-03' });
  assert.strictEqual((strip.match(/class="dr-cap[ "]/g) || []).length, 7, 'một cột mỗi ngày');
  assert.strictEqual((strip.match(/class="dr-shift-count[ "]/g) || []).length, 21, 'ba ca mỗi ngày');
  assert.match(strip, /dr-cap is-selected/);
  // Màu không đứng một mình: mỗi ca có chữ cái và con số.
  assert.match(strip, /<em>S<\/em>/);
  assert.match(strip, /lượt trực/);
}

// Nghỉ phép KHÔNG được tính là có người trực.
{
  const days = [{ key: '2026-09-01', label: 'T3' }];
  const onLeave = {
    days,
    people: [{ id: 'NV-1', name: 'A', days: [{ key: '2026-09-01', shifts: [{ id: 'S1', type: 'morning', kind: 'leave' }], trips: [] }] }],
  };
  assert.strictEqual(DR.shiftCoverage(onLeave.people, '2026-09-01').morning, 0, 'người nghỉ phép không phải là người trực');
}

// Chỗ hổng: ca không có ai trực lên TRƯỚC người rảnh cả tuần.
{
  const days = [{ key: '2026-09-01', label: 'T3' }];
  const data = {
    days,
    people: [
      { id: 'NV-RANH', name: 'Người rảnh', role: 'Lái xe', days: [{ key: '2026-09-01', shifts: [], trips: [] }] },
      { id: 'NV-SANG', name: 'Người trực sáng', role: 'Lái xe', days: [{ key: '2026-09-01', shifts: [{ id: 'S1', type: 'morning', kind: 'work' }], trips: [] }] },
    ],
  };
  const gaps = DR.crewGaps(data);
  // Ca chiều và ca đêm trống, cộng một người rảnh cả tuần.
  assert.strictEqual(gaps.length, 3);
  assert.strictEqual(gaps[0].kind, 'uncovered', 'ca trống là lỗ hổng vận hành, lên trước');
  assert.strictEqual(gaps[1].kind, 'uncovered');
  assert.strictEqual(gaps[2].kind, 'idle');
  assert.strictEqual(gaps[2].person_id, 'NV-RANH');
  assert.ok(!gaps.some(row => row.person_id === 'NV-SANG'), 'người đã có ca thì không phải chỗ hổng');
}

// Tuần đã kín ca thì nói rõ, không để một khung trống.
{
  const days = [{ key: '2026-09-01', label: 'T3' }];
  const full = {
    days,
    people: ['morning', 'afternoon', 'night'].map((type, i) => ({
      id: `NV-${i}`, name: `Người ${i}`,
      days: [{ key: '2026-09-01', shifts: [{ id: `S${i}`, type, kind: 'work' }], trips: [] }],
    })),
  };
  assert.deepStrictEqual(DR.crewGaps(full), []);
  const html = DR.crewGapList(full, {});
  assert.match(html, /đã kín ca/);
  assert.match(html, /fa-circle-check/, 'trạng thái sạch phải có icon riêng, không chỉ khác màu');
  assert.ok(!html.includes('dr-panel--alert'));
}

// Danh sách chỗ hổng: thu gọn, và nói rõ còn bao nhiêu.
{
  const data = bigCrew(400, false);
  const gaps = DR.crewGaps(data);
  assert.ok(gaps.length > 6);
  const collapsed = DR.crewGapList(data, {});
  assert.strictEqual((collapsed.match(/class="dr-exception"/g) || []).length, 6);
  assert.match(collapsed, new RegExp(`Xem tất cả ${gaps.length} dòng`));
  assert.match(DR.crewGapList(data, { expanded: true }), /Thu gọn/);
}

// Thoát ký tự.
{
  const nasty = {
    days: [{ key: '2026-09-01', label: '<b>T3</b>' }],
    people: [{ id: "NV'-1", name: '<script>x</script>', role: 'A & B', days: [{ key: '2026-09-01', shifts: [], trips: [] }] }],
  };
  for (const html of [DR.crewCoverageStrip(nasty, {}), DR.crewGapList(nasty, {})]) {
    assert.ok(!html.includes('<script>'), 'không được nhả thẻ script');
    assert.ok(!html.includes('<b>T3</b>'), 'nhãn ngày phải được thoát');
  }
  const onclick = /focusPerson\('([^']*)'/.exec(DR.crewGapList(nasty, {}));
  assert.ok(onclick && !onclick[1].includes("'"), 'dấu nháy phải được thoát trong ngữ cảnh JavaScript');
}

// --- 16. Tích hợp màn xếp ca trong app.js ---------------------------------

assert.ok(/crewCoverageStrip/.test(app), 'màn xếp ca phải mở ra bằng bảng phủ ca');
assert.ok(/crewGapList/.test(app), 'phải có danh sách chỗ hổng');
assert.ok(/driverShiftVisibleCount/.test(app), 'phải giới hạn số nhân sự dựng một lần');
{
  const start = app.indexOf('function renderDriverShiftCalendarTable()');
  const fn = app.slice(start, app.indexOf(String.fromCharCode(10) + '}', start));
  // Lọc còn 3 người thì màn hình không được báo "tuần này đã kín ca" trong khi
  // ca đêm thứ Năm vẫn không có ai trực.
  assert.match(fn, /ignoreFilters: true/, 'phủ ca và chỗ hổng phải tính trên cả đội');
  assert.match(fn, /crewCoverageStrip\(everyone/);
  assert.match(fn, /crewGapList\(everyone/);
  assert.match(fn, /weekMatrix\(data/, 'riêng ma trận chi tiết mới theo bộ lọc');
}
for (const fnName of ['filterDriverShiftDay', 'filterDriverShiftRole']) {
  const start = app.indexOf(`window.${fnName} = function`);
  const fn = app.slice(start, app.indexOf(String.fromCharCode(10) + '};', start));
  assert.match(fn, /driverShiftVisibleCount = /, `${fnName} phải đặt lại số nhân sự đang hiện`);
}

// --- 17. Hộp thoại tạo ca lặp với hàng trăm người -------------------------
//
// Bản trước cắt cứng `people.slice(0, 60)` mà không nói gì, nên người thứ 61
// trở đi biến mất hoàn toàn — và người dùng không có cách nào biết.
assert.ok(!/people\.slice\(0, 60\)/.test(app), 'không được cắt cứng ở 60 người');
assert.ok(/visibleCount/.test(app), 'phải có bộ đếm số dòng đang hiện');
assert.ok(/showMoreRecurrenceDrivers/.test(app), 'phải tải thêm được');
assert.ok(/hiddenPeople/.test(app), 'phải nói rõ còn bao nhiêu người chưa hiện');
{
  const start = app.indexOf('window.filterWeeklyScheduleDrivers = function');
  const fn = app.slice(start, app.indexOf(String.fromCharCode(10) + '};', start));
  assert.match(fn, /visibleCount = 60/, 'tìm kiếm mới phải quay về trang đầu');
}
// "Chọn tất cả" phải chọn CẢ danh sách khớp, không chỉ số dòng đang hiện —
// nhãn cũ "Chọn N người đang hiện" nói sai việc nút đó làm.
assert.ok(!/người đang hiện<\/button>/.test(app), 'nhãn nút chọn tất cả phải nói đúng phạm vi');
assert.match(app, /Chọn cả \$\{people\.length\} người khớp/);

console.log('driver-roster: tất cả kiểm tra đã qua');
