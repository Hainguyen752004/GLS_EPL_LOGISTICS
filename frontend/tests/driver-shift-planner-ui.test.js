const assert = require('assert');
const fs = require('fs');
const path = require('path');

const frontendRoot = path.join(__dirname, '..');
const html = fs.readFileSync(path.join(frontendRoot, 'index.html'), 'utf8');
const appSource = fs.readFileSync(path.join(frontendRoot, 'js', 'app.js'), 'utf8');
const cockpit = require(path.join(frontendRoot, 'js', 'tms-cockpit-utils.js'));
const rosterSource = fs.readFileSync(path.join(frontendRoot, 'js', 'driver-roster.js'), 'utf8');

[
  'driver-shift-workbench',
  'driver-shift-roster',
  'driver-shift-calendar',
  'driver-shift-inspector',
  'driver-shift-tab-drivers',
  'driver-shift-tab-vehicles',
  'driver-shift-tab-alerts'
].forEach((id) => assert.match(html, new RegExp(`id=["']${id}["']`), `Missing #${id}`));

assert.match(appSource, /\/api\/tms\/scheduling\/driver-shifts/, 'Shift planner must use the real scheduling API.');
assert.match(appSource, /dragstart/, 'Desktop must support drag-and-drop scheduling.');
assert.match(appSource, /selectDriverForShift/, 'Touch devices need tap-to-select scheduling.');
assert.match(appSource, /renderDriverShiftPlanner/, 'Planner render function is required.');
assert.match(appSource, /selectDriverShiftDay/, 'The weekly summary must open a selected day.');
assert.match(appSource, /DRIVER_SHIFT_PAGE_SIZE\s*=\s*25/, 'The daily employee table must paginate large teams.');
assert.match(appSource, /driver-shift-day-search/, 'The daily employee table needs search.');
// Bang xep ca doi sang ma tran NGUOI x NGAY va bo hop thoai ngay: mo hop thoai
// lam mat ngu canh tuan, va dai 7 ngay cu chi hien so tong nen khong biet AI
// lam KHI NAO. Xem js/driver-roster.js.
assert.doesNotMatch(appSource, /let driverShiftDayDialogOpen/, 'The day modal state must be gone.');
assert.match(appSource, /let driverRosterView/, 'The roster needs a week/day view state instead of a modal flag.');
// Lich xe cung doi sang ma tran XE x NGAY, cung ly do nhu bang xep ca: dai 7
// ngay cu chi hien so tong ("3 ranh . 0 ban") nen khong biet XE NAO ranh ngay
// nao, va chi tiet thi nam trong hop thoai che kin man hinh.
assert.doesNotMatch(appSource, /driverVehicleDayDialogOpen/, 'The vehicle day modal state must be gone.');
assert.doesNotMatch(appSource, /DRIVER_VEHICLE_PAGE_SIZE/, 'A week matrix shows every vehicle, so pagination state is dead.');
assert.match(appSource, /vehicleMatrix/, 'The vehicle week must render as a matrix through the presentation module.');
assert.match(appSource, /selectVehicleDay/, 'Vehicle day headers must select a column instead of opening a modal.');
assert.match(appSource, /driver-vehicle-day-search/, 'The daily vehicle table needs search.');
assert.match(appSource, /filterWeeklyScheduleDrivers/, 'The recurring schedule dialog must support searching large employee lists.');
assert.match(appSource, /selectWeeklyScheduleDriver/, 'The recurring schedule dialog must retain the selected employee id.');
assert.match(appSource, /openDriverShiftQuickForm/, 'Unscheduled employees must open a compact shift form.');
assert.match(appSource, /openDriverDayScheduleView/, 'Each employee needs one read-only daily schedule view.');
assert.doesNotMatch(appSource, /<option value="">Xếp ca\.\.\.<\/option>/, 'The daily roster must not use a native shift dropdown as its primary action.');
assert.match(appSource, /saveWeeklyScheduleCompat/, 'Recurring schedules need a compatibility fallback for older running backends.');
assert.match(appSource, /showToast\(error\.message,\s*'error'\)/, 'Scheduling API failures must be shown as errors, not successful completion.');
assert.match(appSource, /window\.DriverRoster/, 'The roster must render through the testable presentation module.');
assert.match(appSource, /DriverRosterActions/, 'Roster cells need an action surface.');
// Gio ca nam trong module trinh bay, khong con noi suy trong app.js.
assert.match(rosterSource, /'06:00 – 14:00'/, 'Morning shift must carry its working hours.');
assert.match(rosterSource, /'14:00 – 22:00'/, 'Afternoon shift must carry its working hours.');
assert.match(rosterSource, /'22:00 – 06:00'/, 'Night shift must carry its overnight hours.');
assert.doesNotMatch(appSource, /<div class="driver-day-tabs">/, 'The daily employee dialog must not require switching between shift tabs.');
const dailyRendererStart = appSource.indexOf('function renderDriverShiftCalendarTable()');
const dailyRendererEnd = appSource.indexOf('window.renderDriverShiftPlanner', dailyRendererStart);
const dailyRenderer = appSource.slice(dailyRendererStart, dailyRendererEnd);
// Ba ca nam trong module, va ma tran hien ca TUAN chu khong mot ngay.
assert.deepStrictEqual(
  require(path.join(frontendRoot, 'js', 'driver-roster.js')).SHIFTS.map(s => s.key),
  ['morning', 'afternoon', 'night'],
  'All three shifts must stay in one place.'
);
assert.match(dailyRenderer, /weekMatrix/, 'The default view must be the week matrix.');
assert.match(dailyRenderer, /dayDetail/, 'A single-day view must stay available inline.');
assert.doesNotMatch(dailyRenderer, /driver-day-overlay/, 'The roster must not build a modal overlay.');
assert.doesNotMatch(dailyRenderer, /role="dialog"/, 'The roster must not build a dialog.');
// Ca hai tab da bo hop thoai ngay, nen lop phu va bang trong do la CSS chet.
// Rieng .driver-day-dialog-header thi con: hop thoai "xem lich mot tai xe"
// (driver-day-view-*) van dung lai phan dau de.
assert.doesNotMatch(html, /\.driver-day-overlay\s*\{/, 'The day modal overlay CSS is dead and must not linger.');
assert.doesNotMatch(html, /\.driver-day-table\s*\{/, 'The paginated day table CSS is dead and must not linger.');
assert.doesNotMatch(html, /\.driver-vehicle-week-day\s*\{/, 'The old 7-day summary strip CSS is dead and must not linger.');
assert.match(html, /\.driver-day-dialog-header\s*\{/, 'The read-only driver day view still reuses this header.');
assert.match(html, /\.driver-shift-layout\s*\{[^}]*min-height:\s*0/, 'The compact weekly calendar must not reserve an empty fixed-height area.');
assert.match(html, /name=["']viewport["'][^>]+viewport-fit=cover/, 'Viewport must follow the device width and safe area.');
assert.match(appSource, /window\.TmsCockpit\?\.buildDriverShiftPlanner/, 'Browser rendering must use the utility global exported by the UMD bundle.');
assert.doesNotMatch(appSource, /window\.TmsCockpitUtils/, 'The obsolete utility global must not be referenced.');
assert.match(appSource, /Promise\.allSettled\(/, 'A secondary scheduling API failure must not blank the whole workbench.');
assert.match(html, /@media \(max-width:1280px\)/, 'The shift workbench needs a tablet layout breakpoint.');
assert.match(html, /@media \(max-width:760px\)[\s\S]*?\.driver-shift-layout\s*\{[^}]*grid-template-columns:\s*minmax\(0,1fr\)/, 'The shift workbench needs a single-column mobile layout.');
assert.match(html, /\.driver-shift-layout\s*\{[^}]*grid-template-areas:\s*"calendar"\s*"inspector"/, 'Desktop must place the daily employee table above the shift inspector.');
assert.match(html, /id=["']driver-shift-inspector["'][^>]*hidden/, 'The empty shift inspector must not reserve calendar space.');
assert.match(appSource, /inspector\.hidden\s*=\s*!shift/, 'The inspector should only appear after a shift is selected.');
assert.match(appSource, /availability_kind/, 'Shift editing must distinguish work from leave, sick leave and off time.');
assert.match(appSource, /driverTripScheduleEntries/, 'The driver calendar must merge real Trip assignments with manual shifts.');
assert.match(appSource, /driver-shift-card--trip/, 'Real Trip assignments need a distinct locked schedule card.');
assert.match(appSource, /deleteDriverShiftById/, 'Manual shift cards need a direct delete action.');
assert.match(appSource, /openDriverTripScheduleInspector/, 'Real Trip cards need a read-only detail action.');
assert.match(html, /\.driver-profile-button\s*\{[^}]*display:\s*grid[^}]*place-items:\s*center[^}]*justify-self:\s*end[^}]*align-self:\s*center/is, 'Driver profile eye action must stay centered in its roster grid cell.');

const driverModalStart = html.indexOf('id="driver-modal-body"');
const driverModalEnd = html.indexOf('onclick="saveDriverModal()"', driverModalStart);
const driverModal = html.slice(driverModalStart, driverModalEnd);
assert.match(driverModal, /class="driver-profile-hero"/, 'Driver photo must use the compact profile header.');
assert.ok(driverModal.indexOf('id="drv-photo-preview-wrap"') < driverModal.indexOf('id="drv-id"'), 'Driver photo must appear before identity fields.');
assert.match(html, /@media \(max-width:760px\)[\s\S]*?\.driver-profile-hero\s*\{[^}]*grid-template-columns:\s*minmax\(0,1fr\)/, 'Driver profile header must stack on mobile.');
assert.match(driverModal, /id="drv-status-text"/, 'Driver operational status must be displayed as read-only system data.');
assert.doesNotMatch(driverModal, /<select[^>]+id="drv-status"/, 'Driver operational status must not be manually selectable.');
assert.doesNotMatch(appSource, /status:\s*document\.getElementById\(['"]drv-status['"]\)/, 'Driver profile save must not submit operational status.');

const calendar = cockpit.buildDriverShiftPlanner({
  drivers: [{ id: 'DRV-01', name: 'Lê Hoàng Nam', status: 'Rảnh' }],
  driver_shifts: [{
    id: 'SHIFT-01', driver_id: 'DRV-01', vehicle_id: null, shift_type: 'morning',
    shift_start: '2026-08-24T06:00:00Z', shift_end: '2026-08-24T14:00:00Z'
  }],
  transport_trips: [{
    id: 'TRIP-01', vehicle_id: 'VEH-01', driver_id: 'DRV-01',
    planned_departure_at: '2026-08-25T06:00:00Z',
    planned_arrival_at: '2026-08-25T09:00:00Z',
    available_at_destination: '2026-08-25T10:00:00Z',
    planned_return_at: '2026-08-25T13:00:00Z',
    return_distance_km: 120
  }]
}, new Date('2026-08-24T00:00:00Z'));

assert.strictEqual(calendar.driver_rows[0].driver_id, 'DRV-01');
assert.strictEqual(calendar.driver_rows[0].days[0].shifts[0].id, 'SHIFT-01');
assert.strictEqual(calendar.vehicle_timelines[0].availability_at_destination_label.includes('B'), true);
assert.strictEqual(calendar.vehicle_timelines[0].return_planned, true);

const vehicleCalendar = cockpit.buildDriverShiftPlanner({
  vehicles: [{ id: 'VEH-IDLE', status: 'available' }, { id: 'VEH-BUSY', status: 'busy' }],
  drivers: [],
  driver_shifts: [],
  vehicle_availability: [{
    trip_id: 'TRIP-BUSY', vehicle_id: 'VEH-BUSY', driver_id: 'DRV-01',
    planned_departure_at: '2026-08-24T06:00:00Z',
    available_at_destination: '2026-08-24T10:00:00Z'
  }]
}, new Date('2026-08-24T00:00:00Z'));
assert.strictEqual(vehicleCalendar.vehicle_rows.length, 2, 'Vehicle TKB must include idle vehicles without Trips.');
assert.strictEqual(vehicleCalendar.vehicle_rows.find(row => row.vehicle_id === 'VEH-IDLE').days[0].status, 'available');

const maintenanceCalendar = cockpit.buildDriverShiftPlanner({
  vehicles: [{ id: 'VEH-MAINT' }, { id: 'VEH-CONFLICT' }],
  drivers: [],
  driver_shifts: [],
  vehicle_availability: [{
    kind: 'maintenance', maintenance_request_id: 'MR-01', vehicle_id: 'VEH-MAINT',
    planned_departure_at: '2026-08-24T06:00:00Z', available_at_origin: '2026-08-24T14:00:00Z',
    maintenance_label: 'Thay phanh'
  }, {
    kind: 'maintenance', maintenance_request_id: 'MR-02', vehicle_id: 'VEH-CONFLICT',
    planned_departure_at: '2026-08-24T06:00:00Z', available_at_origin: '2026-08-24T14:00:00Z'
  }, {
    kind: 'trip', trip_id: 'TRIP-CONFLICT', vehicle_id: 'VEH-CONFLICT', driver_id: 'DRV-01',
    planned_departure_at: '2026-08-24T08:00:00Z', available_at_destination: '2026-08-24T12:00:00Z'
  }]
}, new Date('2026-08-24T00:00:00Z'));
assert.strictEqual(maintenanceCalendar.vehicle_rows.find(row => row.vehicle_id === 'VEH-MAINT').days[0].status, 'maintenance');
assert.strictEqual(maintenanceCalendar.vehicle_rows.find(row => row.vehicle_id === 'VEH-CONFLICT').days[0].status, 'conflict');
assert.ok(maintenanceCalendar.alerts.some(alert => alert.code === 'VEHICLE_MAINTENANCE_OVERLAP'), 'Trip overlapping maintenance must produce an actionable alert.');

const crewCalendar = cockpit.buildDriverShiftPlanner({
  vehicles: [{ id: 'VEH-TRIP', status: 'busy' }],
  drivers: [{ id: 'DRV-MAIN' }, { id: 'DRV-CO' }],
  driver_shifts: [],
  vehicle_availability: [{
    trip_id: 'TRIP-MULTI-DAY', vehicle_id: 'VEH-TRIP', driver_id: 'DRV-MAIN', co_driver_id: 'DRV-CO',
    planned_departure_at: '2026-08-24T01:00:00Z',
    available_at_origin: '2026-08-26T10:00:00Z'
  }]
}, new Date('2026-08-24T00:00:00Z'));
assert.strictEqual(crewCalendar.vehicle_timelines[0].co_driver_id, 'DRV-CO', 'Vehicle availability must retain the co-driver assignment.');
assert.deepStrictEqual(
  crewCalendar.driver_rows.find(row => row.driver_id === 'DRV-CO').days.slice(0, 3).map(day => day.trip_ids),
  [['TRIP-MULTI-DAY'], ['TRIP-MULTI-DAY'], ['TRIP-MULTI-DAY']],
  'A co-driver must remain blocked on every day covered by a multi-day Trip.'
);

console.log('driver-shift-planner-ui.test.js: all checks passed');
