const assert = require('assert');
const fs = require('fs');
const path = require('path');

const frontendRoot = path.join(__dirname, '..');
const html = fs.readFileSync(path.join(frontendRoot, 'index.html'), 'utf8');
const appSource = fs.readFileSync(path.join(frontendRoot, 'js', 'app.js'), 'utf8');
const cockpit = require(path.join(frontendRoot, 'js', 'tms-cockpit-utils.js'));

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
assert.match(appSource, /driverShiftDayDialogOpen/, 'Daily employee details must open on demand instead of taking permanent page space.');
assert.match(appSource, /driverVehicleDayDialogOpen/, 'Daily vehicle details must open on demand instead of rendering the full fleet.');
assert.match(appSource, /DRIVER_VEHICLE_PAGE_SIZE\s*=\s*25/, 'The daily vehicle table must paginate large fleets.');
assert.match(appSource, /driver-vehicle-day-search/, 'The daily vehicle table needs search.');
assert.match(appSource, /filterWeeklyScheduleDrivers/, 'The recurring schedule dialog must support searching large employee lists.');
assert.match(appSource, /selectWeeklyScheduleDriver/, 'The recurring schedule dialog must retain the selected employee id.');
assert.match(appSource, /openDriverShiftQuickForm/, 'Unscheduled employees must open a compact shift form.');
assert.match(appSource, /openDriverDayScheduleView/, 'Each employee needs one read-only daily schedule view.');
assert.doesNotMatch(appSource, /<option value="">Xếp ca\.\.\.<\/option>/, 'The daily roster must not use a native shift dropdown as its primary action.');
assert.match(appSource, /saveWeeklyScheduleCompat/, 'Recurring schedules need a compatibility fallback for older running backends.');
assert.match(appSource, /showToast\(error\.message,\s*'error'\)/, 'Scheduling API failures must be shown as errors, not successful completion.');
assert.match(appSource, /driver-day-schedule-table/, 'The daily employee table must show all shifts without separate shift tabs.');
assert.match(appSource, /Ca sáng<small>06:00 - 14:00<\/small>/, 'Morning shift heading must show its working hours.');
assert.match(appSource, /Ca chiều<small>14:00 - 22:00<\/small>/, 'Afternoon shift heading must show its working hours.');
assert.match(appSource, /Ca đêm<small>22:00 - 06:00<\/small>/, 'Night shift heading must show its overnight hours.');
assert.doesNotMatch(appSource, /<div class="driver-day-tabs">/, 'The daily employee dialog must not require switching between shift tabs.');
const dailyRendererStart = appSource.indexOf('function renderDriverShiftCalendarTable()');
const dailyRendererEnd = appSource.indexOf('window.renderDriverShiftPlanner', dailyRendererStart);
const dailyRenderer = appSource.slice(dailyRendererStart, dailyRendererEnd);
assert.match(dailyRenderer, /shiftCell\('morning'\)/, 'Morning schedule must be visible in the same employee table.');
assert.match(dailyRenderer, /shiftCell\('afternoon'\)/, 'Afternoon schedule must be visible in the same employee table.');
assert.match(dailyRenderer, /shiftCell\('night'\)/, 'Night schedule must be visible in the same employee table.');
assert.match(dailyRenderer, /openDriverDayScheduleView/, 'The primary row action must open the employee schedule view.');
assert.doesNotMatch(dailyRenderer, /fa-solid fa-pen/, 'The daily employee table must not expose edit as the primary action.');
assert.doesNotMatch(dailyRenderer, /driver-day-status/, 'Ambiguous shift status must not be a separate column.');
assert.match(html, /\.driver-day-overlay\s*\{[^}]*position:\s*fixed/, 'The selected day must open in a modal overlay.');
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
